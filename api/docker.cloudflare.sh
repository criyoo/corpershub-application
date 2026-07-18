#!/bin/sh
set -eu

TUNNEL_FILE="${CLOUDFLARE_TUNNEL_URL_FILE:-/data/cloudflared/tunnel-url}"
WEBHOOK_PATH="${FLUTTERWAVE_WEBHOOK_PATH:-/api/v1/payments/webhook/flutterwave}"
ORIGINAL_ENTRYPOINT="/app/docker-entrypoint.sh"

echo "Waiting for Cloudflare tunnel URL..."

attempt=0
max_attempts="${CLOUDFLARE_WAIT_ATTEMPTS:-60}"

while [ ! -s "$TUNNEL_FILE" ]; do
  attempt=$((attempt + 1))

  if [ "$attempt" -ge "$max_attempts" ]; then
    echo "Cloudflare tunnel URL was not available at $TUNNEL_FILE; starting API without tunnel URL."
    exec "$ORIGINAL_ENTRYPOINT" "$@"
  fi

  sleep 1
done

CLOUDFLARE_TUNNEL_URL="$(
  tr -d '\r\n' < "$TUNNEL_FILE"
)"

case "$CLOUDFLARE_TUNNEL_URL" in
  https://*.trycloudflare.com)
    ;;
  *)
    echo "Invalid Cloudflare Quick Tunnel URL; starting API without tunnel URL:"
    echo "$CLOUDFLARE_TUNNEL_URL"
    exec "$ORIGINAL_ENTRYPOINT" "$@"
    ;;
esac

WEBHOOK_PATH="/${WEBHOOK_PATH#/}"

export CLOUDFLARE_TUNNEL_URL

echo "Cloudflare tunnel URL: $CLOUDFLARE_TUNNEL_URL"
echo "Flutterwave webhook URL: ${CLOUDFLARE_TUNNEL_URL%/}${WEBHOOK_PATH}"

exec "$ORIGINAL_ENTRYPOINT" "$@"
