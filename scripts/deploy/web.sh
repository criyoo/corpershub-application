#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

set_environment_defaults "${1:-dev}"
set_aws_auth_mode

[ -d "${WEB_DIR}" ] || fail "Missing web directory: ${WEB_DIR}"

INSTALL_DEPS="${INSTALL_DEPS:-1}"
BUILD_WEB="${BUILD_WEB:-1}"
INVALIDATE_CLOUDFRONT="${INVALIDATE_CLOUDFRONT:-1}"
INVALIDATE_ONLY="${INVALIDATE_ONLY:-0}"

invalidate_cloudfront() {
  local distribution_id

  distribution_id="$(aws_with_auth cloudfront list-distributions \
    --query "DistributionList.Items[?Aliases.Items!=null && contains(Aliases.Items, '${WEB_DOMAIN}')].Id | [0]" \
    --output text)"

  [ -n "${distribution_id}" ] && [ "${distribution_id}" != "None" ] || fail "Could not find CloudFront distribution for ${WEB_DOMAIN}."

  aws_with_auth cloudfront create-invalidation \
    --distribution-id "${distribution_id}" \
    --paths "/*" >/dev/null
}


if [ "${INVALIDATE_ONLY}" = "1" ]; then
  invalidate_cloudfront
  exit 0
fi

require_cmd aws

if [ "${INSTALL_DEPS}" = "1" ] || [ "${BUILD_WEB}" = "1" ]; then
  require_cmd npm
  require_cmd node
fi

ACCOUNT_ID="$(aws_with_auth sts get-caller-identity --query 'Account' --output text)"
BUCKET_NAME="${BUCKET_NAME:-${PROJECT_NAME}-${ENVIRONMENT}-web-${ACCOUNT_ID}}"

aws_with_auth s3api head-bucket --region "${AWS_REGION}" --bucket "${BUCKET_NAME}" >/dev/null 2>&1 \
  || fail "Web bucket not found: ${BUCKET_NAME}"

if [ "${INSTALL_DEPS}" = "1" ]; then
  (
    cd "${APPLICATION_ROOT}"
    npm ci
  )
fi

if [ "${BUILD_WEB}" = "1" ]; then
  (
    cd "${APPLICATION_ROOT}"
    NEXT_PUBLIC_API_BASE_URL="https://${API_DOMAIN}/api" \
    NEXT_PUBLIC_WS_URL="wss://${API_DOMAIN}" \
    NEXT_PUBLIC_HOME_BACKGROUNDS_MANIFEST_URL="https://${API_DOMAIN}/api/home-backgrounds/" \
    npm run build --workspace web
  )
fi

[ -d "${WEB_DIR}/out" ] || fail "Next export output not found."

if grep -R -q "localhost:" "${WEB_DIR}/out"; then
  fail "Web build contains localhost URLs. Rebuild with NEXT_PUBLIC_API_BASE_URL=https://${API_DOMAIN}/api and NEXT_PUBLIC_WS_URL=wss://${API_DOMAIN}."
fi

if [ -d "${WEB_DIR}/out/_next/static" ]; then
  aws_with_auth s3 sync "${WEB_DIR}/out/_next/static/" "s3://${BUCKET_NAME}/_next/static/" \
    --region "${AWS_REGION}" \
    --delete \
    --only-show-errors \
    --cache-control "public,max-age=31536000,immutable"
fi

for html_file in index.html 404.html; do
  if [ -f "${WEB_DIR}/out/${html_file}" ]; then
    aws_with_auth s3 cp "${WEB_DIR}/out/${html_file}" "s3://${BUCKET_NAME}/${html_file}" \
      --region "${AWS_REGION}" \
      --only-show-errors \
      --cache-control "public,max-age=0,s-maxage=60,must-revalidate"
  fi
done

aws_with_auth s3 sync "${WEB_DIR}/out/" "s3://${BUCKET_NAME}/" \
  --region "${AWS_REGION}" \
  --delete \
  --only-show-errors \
  --exclude "_next/static/*" \
  --cache-control "public,max-age=0,s-maxage=60,must-revalidate"

if [ "${INVALIDATE_CLOUDFRONT}" = "1" ]; then
  invalidate_cloudfront
fi
