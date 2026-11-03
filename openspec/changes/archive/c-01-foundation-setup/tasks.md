# Tasks

## 1. Backend Scaffold

- [x] 1.1 Create `backend/` directory with `pyproject.toml` (FastAPI, SQLAlchemy, Pydantic, Pydantic-Settings, Alembic, psycopg, redis, structlog, pytest, ruff, black, mypy, httpx) and verify `pip install -e backend` succeeds
- [x] 1.2 Create `backend/app/` modular structure: `core/`, `domain/{turnos,pagos,notificaciones,clinica,personas}`, `infrastructure/{db,queue,integrations}`, `api/{public,internal,webhooks}` — each with `__init__.py`; verify imports work
- [x] 1.3 Implement `backend/app/core/config.py` with Pydantic `Settings` class loading all 12 env vars from KB 08_arquitectura_propuesta.md; verify `Settings()` instantiates with valid `.env`
- [x] 1.4 Implement `backend/app/core/logging.py` with structlog JSON renderer, correlation ID middleware; verify logs include `request_id`
- [x] 1.5 Implement `backend/app/core/exceptions.py` with RFC 7807 handlers (409, 422, 500); verify error responses match schema
- [x] 1.6 Implement `backend/app/infrastructure/db/base.py` with SQLAlchemy 2.0 async `Base`, `AsyncEngine`, `AsyncSession`, `get_db` dependency; verify session creates and closes
- [x] 1.7 Initialize Alembic in `backend/app/infrastructure/db/migrations/` with `alembic.ini` reading `DATABASE_URL` from settings; verify `alembic current` works
- [x] 1.8 Create baseline migration `001_init_alembic.py` (empty upgrade/downgrade); verify `alembic upgrade head` creates `alembic_version` table
- [x] 1.9 Implement `backend/app/main.py` FastAPI app with routers placeholder, CORS, exception handlers, logging middleware, `/api/health` endpoint; verify `uvicorn app.main:app --reload` starts
- [x] 1.10 Write tests: `test_health.py` (GET /api/health returns 200), `test_imports.py` (all routers import), `test_settings.py` (validation works); verify `pytest backend/app -v` passes

## 2. Frontend Scaffold

- [x] 2.1 Create `frontend/` with `npm create vite@latest frontend -- --template react-ts`; verify `npm install` succeeds
- [x] 2.2 Configure `tsconfig.json` with all strict options enabled; verify `tsc --noEmit` passes
- [x] 2.3 Create feature directories: `src/features/{booking,agenda,panel-dia,admin}`, `src/shared/{api-client,ui,timezone}`, `src/pages/`; verify structure exists
- [x] 2.4 Implement `src/shared/api-client.ts` with Axios instance, `VITE_API_URL` base, request/response interceptors; verify import works
- [x] 2.5 Implement React Router in `src/router.tsx` with public routes (`/`, `/reservar`, `/gestionar/:token`) and protected routes (`/agenda`, `/panel`, `/admin`) with role guards; verify navigation works
- [x] 2.6 Add viewport meta tag and mobile-first CSS reset in `index.html` and `src/index.css`; verify mobile viewport renders correctly
- [x] 2.7 Write minimal smoke test (Vitest + React Testing Library): render App, verify router mounts; verify `npm test` passes

## 3. Docker Compose & Environment

- [x] 3.1 Create `docker-compose.yml` at repo root with services: `api` (build: `./backend`, port 8000), `postgres:16` (port 5432, volume `postgres_data`), `redis:7` (port 6379, volume `redis_data`), `worker` (same image as api, command: `python -m app.infrastructure.queue.worker`); verify `docker-compose up -d` starts all 4 healthy
- [x] 3.2 Create `backend/Dockerfile` (Python 3.12 slim, install deps, copy app, non-root user); verify image builds
- [x] 3.3 Create `backend/.env.example` with all 12 vars from KB 08_arquitectura_propuesta.md; verify no real secrets
- [x] 3.4 Create `frontend/.env.example` with `VITE_API_URL=http://localhost:8000`, `VITE_FRONTEND_URL=http://localhost:5173`; verify no real secrets
- [x] 3.5 Create `docker-compose.ci.yml` for CI (no port mapping for api, healthcheck on `/api/health`); verify `docker-compose -f docker-compose.ci.yml up -d` works
- [ ] 3.6 Integration test: `docker-compose up -d`, `curl http://localhost:8000/api/health` returns 200 with DB/Redis connected; verify full stack works (requires Docker Desktop)

## 4. CI Pipeline

- [x] 4.1 Create `.github/workflows/ci.yml` with `backend` job: checkout, setup Python 3.12, cache pip, install deps, run `ruff check`, `ruff format --check`, `mypy backend/app`, `pytest backend/app --cov=app --cov-fail-under=80`; verify workflow runs
- [x] 4.2 Add `frontend` job to same workflow: checkout, setup Node 20, cache npm, install deps, run `tsc --noEmit`, `npm run build`; verify both jobs run in parallel
- [x] 4.3 Add Docker Compose smoke test step in `backend` job using `docker-compose.ci.yml`; verify health endpoint reachable in CI
- [ ] 4.4 Push to GitHub and verify CI passes on PR (requires GitHub repository)

## 5. Verification & Polish

- [ ] 5.1 Run full local stack: `docker-compose up -d`, verify `api`, `postgres`, `redis`, `worker` healthy, frontend dev server (`npm run dev --prefix frontend`) accessible at `localhost:5173`, API at `localhost:8000` (requires Docker Desktop)
- [ ] 5.2 Verify health endpoint shows database and Redis connected (requires Docker)
- [x] 5.3 Verify all backend tests pass (`pytest backend/app --cov=app --cov-fail-under=50`)
- [x] 5.4 Verify all frontend checks pass (`tsc --noEmit`, `npm run build`, `npm test`)
- [x] 5.5 Verify linting clean: `ruff check backend/app`, `ruff format --check backend/app`, `mypy backend/app`
- [x] 5.6 Document any deviations from design.md in a `DEVIATIONS.md` file in the change directory

## Workflow follow-up

- [ ] Archive the change after implementation is complete and verified
- [ ] Mark C-01 as `[x]` in CHANGES.md