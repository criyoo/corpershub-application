#!/usr/bin/env bash

set -euo pipefail

ENVIRONMENT="${1:-dev}"

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/deploy/common.sh"

set_environment_defaults "${ENVIRONMENT}"
set_aws_auth_mode

require_cmd aws
require_cmd python3
require_cmd tr

if [ "${ENVIRONMENT}" = "dev" ]; then
  ADMIN_EMAIL="admin@dev.corpershub.ng"
  ADMIN_PASSWORD="ifG0dbi4mi"
else
  ADMIN_EMAIL="admin@corpershub.ng"
  ADMIN_PASSWORD="$(openssl rand -hex 16)"
fi

ADMIN_START_DB_INSTANCE="${ADMIN_START_DB_INSTANCE:-1}"
ADMIN_TASK_CONTAINER_NAME="${ADMIN_TASK_CONTAINER_NAME:-migration}"
ECS_CLUSTER_NAME="${NAME_PREFIX}-cluster"
ADMIN_TASK_DEFINITION="${NAME_PREFIX}-migration"
DB_INSTANCE_IDENTIFIER="${NAME_PREFIX}-postgres"
ADMIN_LOG_GROUP="/ecs/${NAME_PREFIX}-migration"

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

ensure_db_available() {
  echo "ensure database is available..."
  local db_status

  db_status="$(aws_with_auth rds describe-db-instances \
    --region "${AWS_REGION}" \
    --db-instance-identifier "${DB_INSTANCE_IDENTIFIER}" \
    --query 'DBInstances[0].DBInstanceStatus' \
    --output text)"

  [ -n "${db_status}" ] && [ "${db_status}" != "None" ] || fail "Could not resolve RDS instance ${DB_INSTANCE_IDENTIFIER}."

  case "${db_status}" in
    available)
      ;;
    starting|backing-up|configuring-enhanced-monitoring|configuring-iam-database-auth|maintenance|modifying|rebooting|renaming|resetting-master-credentials|storage-optimization|upgrading)
      aws_with_auth rds wait db-instance-available \
        --region "${AWS_REGION}" \
        --db-instance-identifier "${DB_INSTANCE_IDENTIFIER}"
      ;;
    stopped)
      [ "${ADMIN_START_DB_INSTANCE}" = "1" ] || fail "RDS instance ${DB_INSTANCE_IDENTIFIER} is stopped."
      aws_with_auth rds start-db-instance \
        --region "${AWS_REGION}" \
        --db-instance-identifier "${DB_INSTANCE_IDENTIFIER}" >/dev/null
      aws_with_auth rds wait db-instance-available \
        --region "${AWS_REGION}" \
        --db-instance-identifier "${DB_INSTANCE_IDENTIFIER}"
      ;;
    stopping)
      fail "RDS instance ${DB_INSTANCE_IDENTIFIER} is stopping. Retry after it has stopped or become available."
      ;;
    *)
      fail "RDS instance ${DB_INSTANCE_IDENTIFIER} is not ready for admin provisioning: ${db_status}"
      ;;
  esac
}

print_task_failure_summary() {
  echo "printing task failure..."
  local task_arn="$1"

  aws_with_auth ecs describe-tasks \
    --region "${AWS_REGION}" \
    --cluster "${ECS_CLUSTER_NAME}" \
    --tasks "${task_arn}" \
    --query 'tasks[0].{stopCode:stopCode,stoppedReason:stoppedReason,containerName:containers[0].name,containerReason:containers[0].reason,exitCode:containers[0].exitCode}' \
    --output json >&2 || true
}

print_task_logs() {
  echo "printing logs.."
  local task_arn="$1"
  local task_id="${task_arn##*/}"
  local log_stream_name

  log_stream_name="$(aws_with_auth logs describe-log-streams \
    --region "${AWS_REGION}" \
    --log-group-name "${ADMIN_LOG_GROUP}" \
    --log-stream-name-prefix "migration/${ADMIN_TASK_CONTAINER_NAME}/${task_id}" \
    --query 'logStreams[0].logStreamName' \
    --output text 2>/dev/null || true)"

  if [ -z "${log_stream_name}" ] || [ "${log_stream_name}" = "None" ]; then
    return
  fi

  aws_with_auth logs get-log-events \
    --region "${AWS_REGION}" \
    --log-group-name "${ADMIN_LOG_GROUP}" \
    --log-stream-name "${log_stream_name}" \
    --limit 200 \
    --query 'events[*].message' \
    --output text 2>/dev/null | tr '\t' '\n' >&2 || true
}

ensure_db_available
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

if [ "${task_exit_code}" != "0" ]; then
  print_task_failure_summary "${task_arn}"
  print_task_logs "${task_arn}"
  fail "Admin user task failed."
fi

if [ "${task_exit_code}" == "0" ]; then
  print_task_logs "${task_arn}"
  echo "Admin user with email ${ADMIN_EMAIL} created successfully..."
fi

# Save Password in SSM Paramater Store
save_admin_password() {
  aws_with_auth ssm put-parameter \
    --region "${AWS_REGION}" \
    --name "/corpershub/secret/${ENVIRONMENT}/DJANGO_ADMIN_PASSWORD" \
    --value "${ADMIN_PASSWORD}" \
    --type "SecureString" \
    --overwrite
}

save_admin_password
