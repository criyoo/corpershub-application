#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/common.sh"

set_environment_defaults "${1:-dev}"
set_aws_auth_mode

require_cmd aws
require_cmd python3
require_cmd tr
ensure_aws_auth

ADMIN_EMAIL="${ADMIN_EMAIL:-admin@corpershub.ng}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-ifG0dbi4mi}"
ADMIN_TASK_CONTAINER_NAME="${ADMIN_TASK_CONTAINER_NAME:-migration}"
ECS_CLUSTER_NAME="${NAME_PREFIX}-cluster"
ADMIN_TASK_DEFINITION="${NAME_PREFIX}-migration"

[ -n "${ADMIN_PASSWORD}" ] || fail "ADMIN_PASSWORD is required."

build_overrides_json() {
  ADMIN_EMAIL="${ADMIN_EMAIL}" \
  ADMIN_PASSWORD="${ADMIN_PASSWORD}" \
  ADMIN_TASK_CONTAINER_NAME="${ADMIN_TASK_CONTAINER_NAME}" \
    python3 - <<'PY'
import json
import os

command = (
    'cd /app && python manage.py shell -c "'
    "from django.contrib.auth import get_user_model; import os; "
    "User = get_user_model(); "
    "email = os.environ['ADMIN_EMAIL']; "
    "password = os.environ['ADMIN_PASSWORD']; "
    "user, created = User.objects.get_or_create(email=email, defaults={'role': 'admin'}); "
    "user.role = 'admin'; "
    "user.email_verified = True; "
    "user.is_staff = True; "
    "user.is_superuser = True; "
    "user.is_active = True; "
    "user.set_password(password); "
    "user.save(); "
    "print('Superuser ready: ' + email + (' (created)' if created else ' (updated)'))"
    '"'
)

print(json.dumps({
    "containerOverrides": [
        {
            "name": os.environ["ADMIN_TASK_CONTAINER_NAME"],
            "command": ["sh", "-lc", command],
            "environment": [
                {"name": "ADMIN_EMAIL", "value": os.environ["ADMIN_EMAIL"]},
                {"name": "ADMIN_PASSWORD", "value": os.environ["ADMIN_PASSWORD"]},
            ],
        }
    ]
}))
PY
}

resolve_public_subnets
resolve_app_security_group

task_definition_arn="$(aws_with_auth ecs describe-task-definition \
  --region "${AWS_REGION}" \
  --task-definition "${ADMIN_TASK_DEFINITION}" \
  --query 'taskDefinition.taskDefinitionArn' \
  --output text)"

[ -n "${task_definition_arn}" ] && [ "${task_definition_arn}" != "None" ] || fail "Could not resolve ECS task definition ${ADMIN_TASK_DEFINITION}."

subnet_csv="$(printf '%s' "${PUBLIC_SUBNET_IDS}" | tr '\t ' ',')"
network_configuration="awsvpcConfiguration={subnets=[${subnet_csv}],securityGroups=[${APP_SECURITY_GROUP_ID}],assignPublicIp=ENABLED}"
overrides_json="$(build_overrides_json)"

task_arn="$(aws_with_auth ecs run-task \
  --region "${AWS_REGION}" \
  --cluster "${ECS_CLUSTER_NAME}" \
  --launch-type FARGATE \
  --task-definition "${task_definition_arn}" \
  --network-configuration "${network_configuration}" \
  --overrides "${overrides_json}" \
  --started-by "admin-user-noninteractive" \
  --query 'tasks[0].taskArn' \
  --output text)"

[ -n "${task_arn}" ] && [ "${task_arn}" != "None" ] || fail "Failed to start the admin user task."

aws_with_auth ecs wait tasks-stopped \
  --region "${AWS_REGION}" \
  --cluster "${ECS_CLUSTER_NAME}" \
  --tasks "${task_arn}"

task_exit_code="$(aws_with_auth ecs describe-tasks \
  --region "${AWS_REGION}" \
  --cluster "${ECS_CLUSTER_NAME}" \
  --tasks "${task_arn}" \
  --query 'tasks[0].containers[0].exitCode' \
  --output text)"

[ "${task_exit_code}" = "0" ] || fail "Admin user task failed."
