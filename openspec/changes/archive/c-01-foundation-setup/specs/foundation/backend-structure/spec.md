# Spec Delta

## Purpose

Provides a modular FastAPI application structure with domain-driven separation, Pydantic settings management, and a health check endpoint for observability.

## ADDED Requirements

### Requirement: Modular backend directory structure
The backend SHALL be organized as a modular monolith with clear domain boundaries under `backend/app/` following the structure: `core/`, `domain/{turnos,pagos,notificaciones,clinica,personas}`, `infrastructure/{db,queue,integrations}`, and `api/{public,internal,webhooks}`.

#### Scenario: Directory structure exists
- **WHEN** the backend project is scaffolded
- **THEN** all domain directories exist with `__init__.py` files

#### Scenario: Domain modules are importable
- **WHEN** importing from `app.domain.turnos`, `app.domain.pagos`, `app.domain.notificaciones`, `app.domain.clinica`, `app.domain.personas`
- **THEN** imports succeed without circular dependencies

### Requirement: Pydantic Settings for configuration
The backend SHALL use Pydantic Settings (`BaseSettings`) for type-safe configuration management with environment variable loading from `.env` files.

#### Scenario: Settings load from environment
- **WHEN** the application starts with valid `.env` file
- **THEN** all settings are loaded with correct types (strings, integers, booleans)

#### Scenario: Required settings validation
- **WHEN** a required setting (e.g., `DATABASE_URL`, `JWT_SECRET`) is missing
- **THEN** application fails fast with clear error message

### Requirement: Health check endpoint
The backend SHALL expose a `GET /api/health` endpoint that returns service status for load balancers and monitoring.

#### Scenario: Health check returns OK
- **WHEN** GET request to `/api/health`
- **THEN** response is 200 OK with JSON `{"status": "ok", "service": "turnos-odontologia-api"}`

#### Scenario: Health check includes dependencies
- **WHEN** GET request to `/api/health` with database and Redis available
- **THEN** response includes `{"database": "connected", "redis": "connected"}`

### Requirement: Structured logging
The backend SHALL use structured JSON logging with correlation IDs for request tracing.

#### Scenario: Logs include correlation ID
- **WHEN** a request is processed
- **THEN** all log entries for that request include the same `request_id`

#### Scenario: Log level configurable
- **WHEN** `LOG_LEVEL` environment variable is set
- **THEN** logger respects the configured level (DEBUG, INFO, WARNING, ERROR)

### Requirement: RFC-compliant exception handling
The backend SHALL return consistent error responses following RFC 7807 (Problem Details) with appropriate HTTP status codes, including 409 Conflict for resource conflicts (e.g., scheduling overlaps).

#### Scenario: 409 Conflict for scheduling overlap
- **WHEN** a request creates a conflicting appointment
- **THEN** response is 409 with `{"type": "about:blank", "title": "Conflict", "status": 409, "detail": "Slot overlaps with existing appointment"}`

#### Scenario: 422 Validation error for invalid input
- **WHEN** request body fails Pydantic validation
- **THEN** response is 422 with structured validation errors

### Requirement: Timezone-aware operations
The backend SHALL operate in `America/Argentina/Buenos_Aires` timezone for all business logic involving dates and times.

#### Scenario: Timezone configured correctly
- **WHEN** `TZ_CLINICA` is set to `America/Argentina/Buenos_Aires`
- **THEN** all datetime operations use this timezone

#### Scenario: Timezone used in slot generation
- **WHEN** generating available slots for a date
- **THEN** slots are calculated in the configured timezone