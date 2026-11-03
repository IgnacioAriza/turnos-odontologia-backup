# Deviations from Design

## C-01 Foundation Setup Deviations

### 1. Worker Implementation (Task 3.1)
**Design**: Worker service runs `python -m app.infrastructure.queue.worker`
**Implementation**: Created minimal worker placeholder that logs heartbeat every 60 seconds. Actual job processing (WA reminders, appointment expiration) will be implemented in C-04+.

### 2. Database Migrations (Tasks 1.7-1.8)
**Design**: Alembic initialized with baseline migration `001_init_alembic.py`
**Implementation**: Created baseline migration but it's empty (no tables created). Business tables (turnos, pagos, notificaciones, clinica, personas) will be created in C-02 as per design non-goals.

### 3. Frontend TypeScript Strict Mode (Task 2.2)
**Design**: Enable all strict TypeScript options
**Implementation**: Enabled `strict: true` plus additional strict options (`noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `noImplicitReturns`, `noImplicitOverride`, `noPropertyAccessFromIndexSignature`). Disabled `noUnusedLocals`, `noUnusedParameters`, `erasableSyntaxOnly` for test files to avoid noise.

### 4. Path Aliases (Task 2.3-2.5)
**Design**: Feature-based directory structure
**Implementation**: Added `@/*` path alias in both Vite and TypeScript configs for cleaner imports.

### 5. CSS Module Declarations (Task 2.6)
**Design**: Mobile-first CSS reset in `index.html` and `src/index.css`
**Implementation**: Added CSS module declarations in `src/global.d.ts` to satisfy TypeScript's `verbatimModuleSyntax` and CSS imports.

### 6. Vitest Configuration (Task 2.7)
**Design**: Minimal smoke test with Vitest + React Testing Library
**Implementation**: Created separate `tsconfig.test.json` for test files with proper types for `@testing-library/jest-dom` matchers. Vitest globals (`describe`, `it`, `expect`, `vi`) used without imports.

### 7. Docker Compose CI (Task 3.5)
**Design**: `docker-compose.ci.yml` without port mapping for api
**Implementation**: Created CI compose file with same services but healthcheck on `/api/health`. Note: GitHub Actions runner has Docker Compose v2.

### 8. GitHub Actions CI (Task 4.1-4.3)
**Design**: Parallel backend and frontend jobs with Docker Compose smoke test
**Implementation**: Created `.github/workflows/ci.yml` with parallel jobs. Backend job includes Docker Compose smoke test with 30s wait for services to be healthy.

### 9. Integration Test (Task 3.6)
**Design**: `docker-compose up -d`, verify health endpoint with DB/Redis connected
**Status**: Not verified locally due to Docker Desktop not running. Configuration files are complete and ready for verification when Docker is available.

### 10. Frontend Router (Task 2.5)
**Design**: Role-based routing with public and protected routes
**Implementation**: Used wrapper components (`ProtectedRoute`, `PublicRoute`) with React Router v7's `createBrowserRouter`. Layouts accept `children` prop instead of using `Outlet` since we're not using nested route definitions.

### 11. Backend Health Check (Task 1.9)
**Design**: `/api/health` returns database and Redis status
**Implementation**: Health check attempts to connect to both services and returns `connected`/`disconnected` status. Gracefully handles connection failures.

### 12. Exception Handling (Task 1.5)
**Design**: RFC 7807 Problem Details with 409 for conflicts
**Implementation**: Created `AppError` base class and specific error classes (`ConflictError`, `NotFoundError`, `UnauthorizedError`, `ForbiddenError`). All handlers return `application/problem+json` with proper structure.

### 13. Logging (Task 1.4)
**Design**: Structured JSON logging with correlation IDs
**Implementation**: Used `structlog` with JSON renderer. Request ID middleware generates UUID per request and binds to logger context via `contextvars`.

### 14. Configuration (Task 1.3)
**Design**: Pydantic Settings with 12 environment variables
**Implementation**: All 12 vars from KB 08_arquitectura_propuesta.md loaded with type validation. `.env.example` files created for both backend and frontend with no real secrets.

## Notes
- All deviations are documented and do not affect the core functionality or architecture.
- Items marked as "will be implemented in C-02+" are explicitly deferred per design non-goals.
- Docker integration test (3.6) and GitHub Actions verification (4.4) require external services not available in local environment.