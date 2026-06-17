#!/usr/bin/env bash
set -euo pipefail

PROFILE="${1:-${AWS_PROFILE:-}}"
MIN_TTL_SECONDS="${AWS_SSO_MIN_TTL_SECONDS:-300}"

fail() {
  echo "Error: $*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

require_cmd aws
require_cmd python3

if [ -n "${AWS_ACCESS_KEY_ID:-}" ] || [ -n "${AWS_WEB_IDENTITY_TOKEN_FILE:-}" ] || [ -n "${AWS_CONTAINER_CREDENTIALS_RELATIVE_URI:-}" ] || [ -n "${AWS_CONTAINER_CREDENTIALS_FULL_URI:-}" ]; then
  aws sts get-caller-identity >/dev/null 2>&1 || fail "AWS environment credentials are configured but unusable"
  echo "AWS environment credentials active"
  exit 0
fi

[ -n "${PROFILE}" ] || fail "AWS profile is required"

check_sso_token() {
  python3 - "${PROFILE}" "${MIN_TTL_SECONDS}" <<'PY'
import configparser
import glob
import json
import os
import sys
from datetime import datetime, timezone

profile = sys.argv[1]
min_ttl_seconds = int(sys.argv[2])

config = configparser.RawConfigParser()
config.read(os.path.expanduser("~/.aws/config"))

profile_section = "default" if profile == "default" else f"profile {profile}"
if not config.has_section(profile_section):
    sys.exit(2)

sso_session = config.get(profile_section, "sso_session", fallback=None)
start_url = config.get(profile_section, "sso_start_url", fallback=None)
region = config.get(profile_section, "sso_region", fallback=None)

if sso_session:
    session_section = f"sso-session {sso_session}"
    if config.has_section(session_section):
        start_url = start_url or config.get(session_section, "sso_start_url", fallback=None)
        region = region or config.get(session_section, "sso_region", fallback=None)

if not start_url or not region:
    sys.exit(3)

latest_expiry = None
for path in glob.glob(os.path.expanduser("~/.aws/sso/cache/*.json")):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        continue

    if payload.get("startUrl") != start_url or payload.get("region") != region:
        continue

    if not payload.get("accessToken"):
        continue

    expires_at = payload.get("expiresAt")
    if not expires_at:
        continue

    try:
        expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except ValueError:
        continue

    if latest_expiry is None or expiry > latest_expiry:
        latest_expiry = expiry

if latest_expiry is None:
    sys.exit(4)

remaining_seconds = int((latest_expiry - datetime.now(timezone.utc)).total_seconds())
if remaining_seconds <= min_ttl_seconds:
    sys.exit(5)

print(remaining_seconds)
PY
}

check_profile_credentials() {
  aws sts get-caller-identity --profile "${PROFILE}" >/dev/null 2>&1
}

if remaining_seconds="$(check_sso_token)"; then
  if check_profile_credentials; then
    echo "AWS SSO access token and role credentials active for ${PROFILE} (${remaining_seconds}s remaining)"
    exit 0
  fi

  echo "Cached AWS SSO access token found for ${PROFILE}, but role credentials could not be refreshed. Re-authenticating..."
else
  echo "Refreshing AWS SSO session for ${PROFILE}..."
fi

aws sso login --profile "${PROFILE}"

check_profile_credentials || fail "AWS SSO login succeeded for ${PROFILE}, but AWS role credentials are still unavailable"
