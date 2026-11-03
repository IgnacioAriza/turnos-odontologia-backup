# Spec Delta

## Purpose

Provides Docker Compose orchestration with PostgreSQL, Redis, and worker services, plus environment variable management for all 12 required configuration variables.

## ADDED Requirements

### Requirement: Docker Compose with four services
The infrastructure SHALL provide a `docker-compose.yml` with services: `api` (FastAPI backend), `postgres` (PostgreSQL 16), `redis` (Redis 7), and `worker` (background job processor).

#### Scenario: All services start successfully
- **WHEN** running `docker-compose up -d`
- **THEN** all four services report healthy status

#### Scenario: Services communicate via Docker network
- **WHEN** the `api` service connects to `postgres` and `redis`
- **THEN** connections succeed using service names as hostnames

#### Scenario: Postgres data persists
- **WHEN** stopping and restarting `docker-compose`
- **THEN** PostgreSQL data is preserved in a named volume

#### Scenario: Redis data persists
- **WHEN** stopping and restarting `docker-compose`
- **THEN** Redis data is preserved in a named volume

### Requirement: Environment variable files
The infrastructure SHALL provide `.env.example` files for both backend and frontend with all 12 required variables documented.

#### Scenario: Backend .env.example exists
- **WHEN** checking `backend/.env.example`
- **THEN** file contains all required variables: `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `JWT_EXPIRES_MIN`, `TZ_CLINICA`, `MP_ACCESS_TOKEN`, `MP_WEBHOOK_SECRET`, `MP_TTL_MIN`, `TWILIO_SID`, `TWILIO_TOKEN`, `TWILIO_WA_FROM`, `GCAL_CALENDAR_ID`, `SMTP_URL`, `FRONTEND_URL`

#### Scenario: Frontend .env.example exists
- **WHEN** checking `frontend/.env.example`
- **THEN** file contains `VITE_API_URL` and `VITE_FRONTEND_URL`

#### Scenario: No secrets in repository
- **WHEN** checking git history
- **THEN** no `.env` files with real values are committed

### Requirement: PostgreSQL 16 configuration
The PostgreSQL service SHALL use version 16 with appropriate settings for the application.

#### Scenario: Postgres accepts connections
- **WHEN** `api` service connects to `postgres:5432`
- **THEN** connection succeeds with configured credentials

#### Scenario: Timezone set to UTC in container
- **WHEN** checking Postgres container
- **THEN** system timezone is UTC (application handles AR timezone)

### Requirement: Redis 7 configuration
The Redis service SHALL use version 7 with persistence enabled for job queue reliability.

#### Scenario: Redis accepts connections
- **WHEN** `api` and `worker` services connect to `redis:6379`
- **THEN** connections succeed

#### Scenario: Redis persistence configured
- **WHEN** checking Redis configuration
- **THEN** AOF persistence is enabled

### Requirement: Worker service for background jobs
The worker service SHALL run the same codebase as `api` but with a different entry point for processing background jobs (WA reminders, appointment expiration).

#### Scenario: Worker processes jobs
- **WHEN** a job is enqueued in Redis
- **THEN** worker picks up and processes the job

#### Scenario: Worker shares code with API
- **WHEN** comparing `api` and `worker` images
- **THEN** both use the same Dockerfile with different CMD