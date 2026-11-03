# Spec Delta

## Purpose

Provides a GitHub Actions CI pipeline with parallel backend and frontend jobs for linting, type checking, and testing.

## ADDED Requirements

### Requirement: GitHub Actions workflow file
The CI SHALL be defined in `.github/workflows/ci.yml` with jobs for backend and frontend that run in parallel.

#### Scenario: Workflow triggers on push and PR
- **WHEN** code is pushed to any branch or a PR is opened
- **THEN** the CI workflow runs automatically

#### Scenario: Jobs run in parallel
- **WHEN** workflow starts
- **THEN** `backend` and `frontend` jobs start simultaneously

### Requirement: Backend linting and formatting checks
The backend job SHALL run `ruff check`, `ruff format --check`, and `mypy` on the `backend/app` directory.

#### Scenario: Ruff check passes
- **WHEN** running `ruff check backend/app`
- **THEN** exit code is 0 (no linting errors)

#### Scenario: Ruff format check passes
- **WHEN** running `ruff format --check backend/app`
- **THEN** exit code is 0 (code is formatted)

#### Scenario: Mypy type check passes
- **WHEN** running `mypy backend/app`
- **THEN** exit code is 0 (no type errors)

### Requirement: Backend tests with coverage
The backend job SHALL run `pytest` with coverage reporting, requiring >80% coverage.

#### Scenario: Pytest suite passes
- **WHEN** running `pytest backend/app --cov=app --cov-fail-under=80`
- **THEN** all tests pass and coverage is >= 80%

#### Scenario: Health check test exists
- **WHEN** running pytest
- **THEN** a test for `GET /api/health` is included and passes

#### Scenario: Router import test exists
- **WHEN** running pytest
- **THEN** a test verifying all routers can be imported is included and passes

### Requirement: Frontend type checking and build
The frontend job SHALL run `tsc --noEmit` for type checking and `npm run build` for production build verification.

#### Scenario: TypeScript check passes
- **WHEN** running `tsc --noEmit` in frontend directory
- **THEN** exit code is 0 (no type errors)

#### Scenario: Production build succeeds
- **WHEN** running `npm run build` in frontend directory
- **THEN** build completes without errors and outputs to `dist/`

### Requirement: Docker Compose smoke test
The CI SHALL include a step that starts Docker Compose and verifies services are healthy.

#### Scenario: Compose up in CI
- **WHEN** running `docker-compose -f docker-compose.ci.yml up -d`
- **THEN** all services start and report healthy within 60 seconds

#### Scenario: Health endpoint reachable
- **WHEN** services are up in CI
- **THEN** `curl http://localhost:8000/api/health` returns 200 OK