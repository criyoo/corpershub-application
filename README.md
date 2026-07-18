# Corpershub

Corpershub is a modular-monolith platform for the NYSC ecosystem. It connects companies and organizations with corps members looking for PPA and service placements, while enforcing privacy rules around company discovery and sensitive corper data.

## Repository Structure

```text
Corpershub/
├── apps/
│   ├── api/              # Django Api
│   ├── packages/         # Shared workspace packages
│   ├── web/              # Next.js frontend
│   └── worker/           # Reserved for dedicated background job code
├── infra/
│   ├── cloudflared/      # Local Cloudflare Quick Tunnel container
│   ├── docs/             # Infrastructure planning and deployment docs
│   ├── kubernetes/       # Reserved for future Kubernetes manifests
│   ├── scripts/          # Bootstrap, deploy, migration, and secrets helpers
│   ├── docker-compose.yml
│   └── terraform/        # Terraform root module, envs, files, and reusable modules
├── .github/
├── Makefile
└── README.md
```

## Stack

- Frontend: Next.js + React + TypeScript + Tailwind CSS
- Api: Django + Django REST Framework + Simple JWT
- Realtime: Django Channels + WebSockets
- Data: PostgreSQL
- Cache and broker: Redis
- Background jobs: Celery
- Object storage: S3-compatible storage with MinIO locally and S3 in AWS
- Containers: Docker + Docker Compose

## Local Development

### Docker

1. Copy `apps/api/.env.example` to `apps/api/.env` if you want local overrides.
2. Copy `apps/web/.env.example` to `apps/web/.env.local` if you want local overrides.
3. Add your Flutterwave credentials in `apps/api/.env`:
   `FLUTTERWAVE_PUBLIC_KEY`, `FLUTTERWAVE_SECRET_KEY`, `FLUTTERWAVE_CLIENT_ID`, `FLUTTERWAVE_CLIENT_SECRET`, `FLUTTERWAVE_ENCRYPTION_KEY`, and `FLUTTERWAVE_WEBHOOK_SECRET_HASH`.
4. Run `make up` from the repository root, or run `docker compose -f infra/docker-compose.yml up`.
5. Open `http://localhost:3200` for the frontend and `http://localhost:8200/api/docs/swagger/` for the API docs.
6. Open `http://localhost:9201` if you want the MinIO console for local media objects.
7. execute `docker compose -f infra/docker-compose.yml exec api python3 manage.py createsuperuser` to create an admin user in django
8. execute `docker compose -f infra/docker-compose.yml exec api python3 manage.py seed_demo_data` to seed the database with demo data
9. execute `docker compose -f infra/docker-compose.yml exec postgres psql -U db_user -d corpershub_db` to log into the postgres database using docker
10. execute `psql -h localhost -p 5200 -U db_user -d corpershub_db` to log into the postgres database through Docker Compose

### Without Docker

1. Install Api dependencies from `apps/api/requirements.txt`.
2. Install Web dependencies from `apps/web/package.json`.
3. Start PostgreSQL and Redis locally.
4. Run Api commands:

```bash
cd apps/api
python3 manage.py migrate
python3 manage.py seed_demo_data
python3 manage.py runserver
```

1. In another shell run the frontend:

```bash
cd apps
npm install --workspace web
npm run dev --workspace web
```

1. For realtime and async workers, also run:

```bash
cd apps/api
celery -A config worker -l info
```

## Testing

Backend tests:

```bash
cd apps/api
python3 manage.py test --settings=config.settings.test
```

Frontend tests:

```bash
cd apps
npm install --workspace web
npm run test --workspace web
```

## Deployment Notes

- Use `config.settings.development` for AWS `dev` and `config.settings.production` for AWS `prod`.
- `apps/api/seed_demo_data/` is the source of truth for default seeded accounts and their bundled images when seeding is enabled.
- Local development writes generated media output to MinIO through the Docker Compose `minio` service.
- AWS development and AWS production write generated media output to the configured S3 `media` bucket.
- Default account seeding is enabled for local development and AWS `dev`, and disabled for AWS `prod`.
- Do not treat `apps/api/media/` as authoritative seed input; it is only a local filesystem artifact from older runs before the MinIO-backed media storage path.
- Run Gunicorn with the ASGI app so websocket traffic and HTTP traffic share the same app entrypoint.
- Put Redis behind both Channels and Celery.
- Configure S3 credentials and bucket values for production file storage.
- Terminate TLS at the load balancer and forward `X-Forwarded-Proto`.
- Run Celery workers as ECS services and use EventBridge Scheduler for periodic payment-expiry cleanup in AWS.
- Keep frontend and backend environment variables separate so the public bundle only exposes `NEXT_PUBLIC_*` values.
