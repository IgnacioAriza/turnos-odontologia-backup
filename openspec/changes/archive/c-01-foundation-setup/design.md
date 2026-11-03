# Design

## Context

See proposal.md for motivation. This is the first change (C-01) in the project — no existing codebase. The knowledge base (KB) defines the stack, architecture, and decisions:
- Stack: Python 3.12, FastAPI 0.115+, SQLAlchemy 2.0, PostgreSQL 16, Redis 7, Docker Compose v2, React 18/TS/Vite
- Architecture: Modular monolith with domain separation (DD-02)
- 12 environment variables (08_arquitectura_propuesta.md)
- Timezone: America/Argentina/Buenos_Aires (DD-04, DD-06)

## Goals / Non-Goals

**Goals:**
- Scaffold complete backend structure with domain-driven modular organization
- Scaffold complete frontend structure with mobile-first feature-based organization
- Provide Docker Compose for local development with all required services
- Establish CI pipeline with linting, type checking, testing for both backend and frontend
- Initialize Alembic for database migrations
- Create health check endpoint for observability
- Configure Pydantic Settings for type-safe configuration
- Set up structured logging with correlation IDs

**Non-Goals:**
- No business logic implementation (turnos, pagos, notificaciones, etc.) — those are C-02+
- No authentication implementation — that's C-03
- No database models beyond what's needed for health checks — C-02 creates models
- No API endpoints beyond `/api/health` — C-02+ add domain endpoints
- No frontend UI components beyond routing shell — C-04+ build features
- No production deployment configuration — local/dev only

## Decisions

### 1. Backend: Modular monolith structure (DD-02)
**Decision**: Organize `backend/app/` as `core/`, `domain/{turnos,pagos,notificaciones,clinica,personas}`, `infrastructure/{db,queue,integrations}`, `api/{public,internal,webhooks}`.

**Rationale**: Matches KB 08_arquitectura_propuesta.md exactly. Domain separation from day 1 enables future service extraction without microservices overhead (DD-02).

**Alternatives**: Flat structure (faster initial scaffolding but painful later); microservices (premature complexity).

### 2. Configuration: Pydantic Settings with `.env` files
**Decision**: Use `pydantic-settings` BaseSettings with `model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")`.

**Rationale**: Type-safe, validates required fields at startup, supports `.env` for local dev, 12-factor compliant.

**Alternatives**: `python-dotenv` + manual validation (more boilerplate); `dynaconf` (heavier dependency).

### 3. Database: SQLAlchemy 2.0 async with Alembic
**Decision**: Use `sqlalchemy.ext.asyncio.AsyncEngine`, `AsyncSession`, declarative base in `app/infrastructure/db/base.py`. Alembic configured to read `DATABASE_URL` from settings at runtime.

**Rationale**: FastAPI is async-native; SQLAlchemy 2.0 async API is stable. Alembic standard for migrations.

**Alternatives**: Sync SQLAlchemy (blocks event loop); Tortoise ORM (less mature); Prisma (not Python).

### 4. Health check: `/api/health` with dependency checks
**Decision**: Endpoint returns `{"status": "ok", "service": "turnos-odontologia-api", "database": "connected|disconnected", "redis": "connected|disconnected"}`.

**Rationale**: Load balancers and orchestrators need dependency-aware health checks. Fast to implement, high value.

**Alternatives**: Simple `{"status": "ok"}` (doesn't detect DB/Redis issues); Kubernetes liveness/readiness probes (overkill for Compose).

### 5. Exception handling: RFC 7807 Problem Details
**Decision**: Custom exception handlers returning `application/problem+json` with `type`, `title`, `status`, `detail`, `instance`. 409 for conflicts (scheduling overlaps per RN-RES-*).

**Rationale**: Standard format, machine-readable, matches KB requirement for 409 on solape.

**Alternatives**: FastAPI default 422/500 (less informative); custom JSON without RFC standard.

### 6. Logging: Structured JSON with correlation IDs
**Decision**: Use `structlog` with `structlog.stdlib.add_logger_name`, `add_log_level`, `TimeStamper(fmt="iso")`, `JSONRenderer()`. Middleware generates `request_id` (UUID) per request and binds to logger context.

**Rationale**: Observability best practice, enables log aggregation and tracing.

**Alternatives**: Standard library logging (harder to parse); `loguru` (less structured).

### 7. Frontend: Vite + React 18 + TypeScript 5 strict
**Decision**: `npm create vite@latest frontend -- --template react-ts`, then enable all strict TypeScript options.

**Rationale**: Matches KB stack. Vite fast HMR, React 18 concurrent features, strict TS catches bugs early.

**Alternatives**: Next.js (SSR not needed for SPA); Create React Act (deprecated); plain Webpack (slower).

### 8. Frontend: Feature-based architecture with role routing
**Decision**: `src/features/{booking,agenda,panel-dia,admin}/`, `src/shared/{api-client,ui,timezone}/`, `src/pages/` for route components. Router with public routes (`/`, `/reservar`, `/gestionar/:token`) and protected routes (`/agenda`, `/panel`, `/admin`) guarded by JWT + role claims.

**Rationale**: Matches KB 08_arquitectura_propuesta.md structure. Mobile-first booking is primary user flow.

**Alternatives**: Page-based (colocates unrelated code); atomic design (over-engineered for this scope).

### 9. API Client: Axios with interceptors
**Decision**: `axios.create({ baseURL: import.meta.env.VITE_API_URL })` with request interceptor for JWT, response interceptor for 401 handling.

**Rationale**: Industry standard, interceptors handle auth cleanly, TypeScript support.

**Alternatives**: `fetch` + wrapper (more boilerplate); `ky` (less familiar); TanStack Query (good but adds complexity for scaffolding).

### 10. Docker Compose: 4 services with named volumes
**Decision**: `docker-compose.yml` with `api`, `postgres`, `redis`, `worker`. Named volumes `postgres_data`, `redis_data`. `api` and `worker` share Dockerfile, different `command`. `.env.example` files in `backend/` and `frontend/`.

**Rationale**: Matches KB exactly. Worker separate from API for job processing (WA reminders, appointment expiration). Named volumes persist data across restarts.

**Alternatives**: Single service with background threads (blocks API); separate Dockerfiles (duplication); no volumes (data loss on restart).

### 11. CI: GitHub Actions with parallel jobs
**Decision**: `.github/workflows/ci.yml` with `backend` job (ruff, black, mypy, pytest --cov-fail-under=80) and `frontend` job (tsc --noEmit, npm run build) running in parallel. Docker Compose smoke test in backend job.

**Rationale**: Fast feedback, catches issues early, matches KB quality rules (ruff/black/mypy/pytest >80%, tsc/build).

**Alternatives**: Sequential jobs (slower); GitLab CI / CircleCI (not GitHub); no CI (violates quality rules).

### 12. Timezone handling: Application-level AR timezone
**Decision**: Store all timestamps in UTC in PostgreSQL. Application layer converts to/from `America/Argentina/Buenos_Aires` using `zoneinfo` (Python 3.9+) or `pytz`. `TZ_CLINICA` setting drives conversion.

**Rationale**: UTC in DB is standard best practice. AR timezone only for display/business logic. Avoids DST issues.

**Alternatives**: Store in AR timezone (DST bugs); UTC everywhere (confusing for clinic staff).

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Alembic autogenerate misses changes | Require manual review of generated migrations; test with `alembic check` in CI |
| Docker Compose networking differs from prod | Document differences; use same image tags; test locally before deploy |
| Frontend/backend version drift | Shared TypeScript types via `openapi-typescript` in future changes (C-02+) |
| Worker and API share code but diverge | Keep entry points minimal; share `app.core`, `app.infrastructure` only |
| CI false positives from flaky tests | Quarantine flaky tests; fix root cause; don't disable |
| Environment variable sprawl | Centralize in `app.core.config.Settings`; document all 12 vars in `.env.example` |
| Mobile-first CSS complexity | Use CSS custom properties + container queries; avoid heavy frameworks |

## Migration Plan

1. Create `backend/` and `frontend/` directories with scaffolded projects
2. Write `docker-compose.yml` and `.env.example` files
3. Create GitHub Actions workflow
4. Run `docker-compose up -d` locally to verify
5. Run CI pipeline manually via `act` or push to trigger
6. Verify all services healthy and tests pass

**Rollback**: Delete `backend/`, `frontend/`, `docker-compose.yml`, `.github/workflows/ci.yml` — no data migration needed (fresh project).

## Open Questions

- None — all technical decisions resolved by KB and stack requirements.