#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")/deploy" && pwd)/common.sh"

set_environment_defaults "${1:-dev}"
set_aws_auth_mode

require_cmd python3
require_cmd tr
# ensure_aws_auth

ECS_CLUSTER_NAME="${NAME_PREFIX}-cluster"
MIGRATION_TASK_DEFINITION="${NAME_PREFIX}-migration"
DB_INSTANCE_IDENTIFIER="${NAME_PREFIX}-postgres"
MIGRATION_LOG_GROUP="/ecs/${NAME_PREFIX}-migration"
RUN_SEED_DEMO_DATA="${RUN_SEED_DEMO_DATA:-0}"

resolve_public_subnets
resolve_app_security_group

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
  stopped|stopping)
    exit 0
    ;;
  *)
    fail "RDS instance ${DB_INSTANCE_IDENTIFIER} is not ready for migrations: ${db_status}"
    ;;
esac

task_overrides() {
  local command="$1"

  python3 - "$command" <<'PY'
import json
import sys

print(json.dumps({
    "containerOverrides": [
        {
            "name": "migration",
            "command": ["sh", "-lc", sys.argv[1]],
        }
    ]
}))
PY
}

app_command() {
  local command="$1"
  printf 'cd /app && %s' "${command}"
}

print_task_logs() {
  local task_arn="$1"
  local task_id="${task_arn##*/}"
  local log_stream_name

  log_stream_name="$(aws_with_auth logs describe-log-streams \
    --region "${AWS_REGION}" \
    --log-group-name "${MIGRATION_LOG_GROUP}" \
    --log-stream-name-prefix "migration/migration/${task_id}" \
    --query 'logStreams[0].logStreamName' \
    --output text 2>/dev/null || true)"

  if [ -z "${log_stream_name}" ] || [ "${log_stream_name}" = "None" ]; then
    return
  fi

  aws_with_auth logs get-log-events \
    --region "${AWS_REGION}" \
    --log-group-name "${MIGRATION_LOG_GROUP}" \
    --log-stream-name "${log_stream_name}" \
    --limit 200 \
    --query 'events[*].message' \
    --output text 2>/dev/null | tr '\t' '\n' >&2 || true
}

run_task() {
  local command="$1"
  local overrides
  local task_arn
  local exit_code
  local task_definition_arn

  overrides="$(task_overrides "${command}")"
  network_configuration="awsvpcConfiguration={subnets=[$(printf '%s' "${PUBLIC_SUBNET_IDS}" | tr '\t ' ',')],securityGroups=[${APP_SECURITY_GROUP_ID}],assignPublicIp=ENABLED}"
  task_definition_arn="$(aws_with_auth ecs describe-task-definition \
    --region "${AWS_REGION}" \
    --task-definition "${MIGRATION_TASK_DEFINITION}" \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text)"

  [ -n "${task_definition_arn}" ] && [ "${task_definition_arn}" != "None" ] ||
    fail "Could not resolve ECS task definition ${MIGRATION_TASK_DEFINITION}."

  task_arn="$(aws_with_auth ecs run-task \
    --region "${AWS_REGION}" \
    --cluster "${ECS_CLUSTER_NAME}" \
    --launch-type FARGATE \
    --task-definition "${task_definition_arn}" \
    --network-configuration "${network_configuration}" \
    --overrides "${overrides}" \
    --query 'tasks[0].taskArn' \
    --output text)"

  [ -n "${task_arn}" ] && [ "${task_arn}" != "None" ] || fail "Failed to start migration task."

  aws_with_auth ecs wait tasks-stopped \
    --region "${AWS_REGION}" \
    --cluster "${ECS_CLUSTER_NAME}" \
    --tasks "${task_arn}"

  exit_code="$(aws_with_auth ecs describe-tasks \
    --region "${AWS_REGION}" \
    --cluster "${ECS_CLUSTER_NAME}" \
    --tasks "${task_arn}" \
    --query 'tasks[0].containers[0].exitCode' \
    --output text)"

  if [ "${exit_code}" = "0" ]; then
    return 0
  fi

  if [ "${exit_code}" = "10" ]; then
    return 10
  fi

  print_task_logs "${task_arn}"
  fail "Task failed for command: ${command}"
}

if run_task "$(app_command "python manage.py has_pending_migrations")"; then
  pending_migrations=0
else
  status=$?
  if [ "${status}" = "10" ]; then
    pending_migrations=1
  else
    exit "${status}"
  fi
fi

if [ "${pending_migrations}" = "1" ]; then
  run_task "$(app_command "python manage.py migrate --noinput")"
fi

run_task "$(app_command "python manage.py sync_subscription_plans")"

if [ "${RUN_SEED_DEMO_DATA}" = "1" ]; then
  run_task "$(app_command "python manage.py seed_demo_data")"
fi
