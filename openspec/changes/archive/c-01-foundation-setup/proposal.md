# Proposal

## Why

This is the foundational change (C-01) that establishes the complete scaffolding for the SaaS Odontología project. It creates the modular monolith architecture with Docker Compose infrastructure, FastAPI backend structure, React frontend scaffolding, and CI pipeline. This is the first change in the critical path and has no dependencies — all subsequent changes (C-02 through C-13) depend on this foundation.

## What Changes

- **Backend scaffolding**: Modular FastAPI app structure under `backend/app/` with domain-separated modules (turnos, pagos, notificaciones, clinica, personas), infrastructure layer (db, queue, integrations), and API routers (public, internal, webhooks)
- **Frontend scaffolding**: Vite + React 18 + TypeScript 5 project under `frontend/src/` with feature-based structure (booking, agenda, panel-dia, admin), shared utilities, and role-based routing
- **Infrastructure**: Docker Compose with 4 services (api, postgres:16, redis:7, worker) + `.env.example` files with all 12 required environment variables
- **Configuration**: Pydantic Settings for type-safe config, timezone `America/Argentina/Buenos_Aires`, structured logging, RFC-compliant exceptions (409 for conflicts)
- **Database**: Alembic initialized for migrations
- **CI Pipeline**: GitHub Actions with parallel backend (ruff, black, mypy, pytest) and frontend (tsc, build) jobs
- **Tests**: Health check endpoint, router import tests, Docker Compose smoke tests

## Capabilities

### New Capabilities

- `foundation/backend-structure`: Modular FastAPI application structure with domain-driven separation, Pydantic settings, and health check endpoint
- `foundation/frontend-structure`: Vite React TypeScript SPA with mobile-first architecture, feature-based organization, and role-based routing
- `foundation/infrastructure`: Docker Compose orchestration with PostgreSQL, Redis, and worker services; environment variable management
- `foundation/ci-pipeline`: GitHub Actions CI with linting, type checking, and testing for both backend and frontend
- `foundation/database-migrations`: Alembic initialized for PostgreSQL schema evolution

### Modified Capabilities

(None — this is the first change, no existing capabilities to modify)

## Impact

- **Code**: Creates entire project structure for both backend and frontend
- **APIs**: Establishes `/api/health` endpoint; defines router organization pattern (public/internal/webhooks)
- **Dependencies**: Adds FastAPI, SQLAlchemy, Pydantic, Alembic, Redis, pytest, ruff, black, mypy, Vite, React, TypeScript
- **Systems**: Docker Compose for local development; GitHub Actions for CI
- **Configuration**: 12 environment variables defined (DATABASE_URL, REDIS_URL, JWT_SECRET, JWT_EXPIRES_MIN, TZ_CLINICA, MP_ACCESS_TOKEN, MP_WEBHOOK_SECRET, MP_TTL_MIN, TWILIO_SID, TWILIO_TOKEN, TWILIO_WA_FROM, GCAL_CALENDAR_ID, SMTP_URL, FRONTEND_URL)