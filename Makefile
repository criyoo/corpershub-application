ENVIRONMENT ?= dev
SHELL := /bin/bash
BASH_CMD := $(AWS_RUN) bash

.PHONY: local-api-check local-api-test local-migrate local-seed local-frontend-lint local-frontend-build deploy-api-dev deploy-web-dev invalidate-web-dev migrate-aws-dev


# Bear OS Local Environment
local-api-check:
	@cd apps/api && python3 manage.py check --settings=config.settings.local

local-api-test:
	@cd apps/api && python3 manage.py test --settings=config.settings.test

local-migrate:
	@cd apps/api && python3 manage.py migrate

local-seed:
	@cd apps/api && python3 manage.py seed_demo_data

local-frontend-lint:
	@npm run lint --workspace apps/web

local-frontend-build:
	@npm run build --workspace apps/web

api:
	@bash scripts/deploy/api.sh $(ENVIRONMENT)

web:
	@bash scripts/deploy/web.sh $(ENVIRONMENT)

invalidate:
	INVALIDATE_ONLY=1 bash scripts/deploy/web.sh $(ENVIRONMENT)

migrate:
	@bash scripts/migrate.sh $(ENVIRONMENT)

admin:
	@bash scripts/admin.sh $(ENVIRONMENT)

