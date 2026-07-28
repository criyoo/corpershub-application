FROM python:3.12-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ENV HOME=/tmp
ENV XDG_RUNTIME_DIR=/tmp

RUN apt-get update \
  && apt-get install -y --no-install-recommends build-essential libpq-dev curl postgresql-client vim nano wget \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app
RUN chmod +x /app/docker-entrypoint.sh /app/docker.cloudflare.sh /app/manage.py || true
ENTRYPOINT ["/app/docker-entrypoint.sh"]

RUN mkdir -p /app/media /app/logs

EXPOSE 8000

FROM base AS development
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.asgi:application", "-k", "uvicorn.workers.UvicornWorker", "--no-control-socket"]


FROM base AS production
RUN addgroup --system app && adduser --system --ingroup app app \
  && chown -R app:app /app
USER app
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.asgi:application", "-k", "uvicorn.workers.UvicornWorker", "--no-control-socket"]
