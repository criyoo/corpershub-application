#!/bin/sh
set -eu

if [ -n "${POSTGRES_HOST:-}" ]; then
  echo "Waiting for PostgreSQL at ${POSTGRES_HOST}:${POSTGRES_PORT:-5432}..."
  tries=0
  until python -c "import socket; s=socket.create_connection(('${POSTGRES_HOST}', int('${POSTGRES_PORT:-5432}')), 3); s.close()" >/dev/null 2>&1; do
    tries=$((tries + 1))
    if [ "${tries}" -ge 30 ]; then
      echo "PostgreSQL did not become ready in time." >&2
      exit 1
    fi
    sleep 1
  done
fi

python manage.py makemigrations
python manage.py migrate
python manage.py seed_demo_data
exec gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --no-control-socket
