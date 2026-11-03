# Spec — C-02 core-models-clinica-personas

## Purpose

Core domain models for the SaaS Odontología project: Clinic, User, Paciente, Sillon, Bloqueo, plus AuditMixin, BaseRepository[T], UnitOfWork patterns, and clinic_id multi-tenancy from day 1.

## Requirements

### R1 — Domain models
The backend SHALL define SQLAlchemy 2.0 models:

- `Clinic`: id (UUID PK), nombre, timezone, wa_sender, mp_account, is_active, created_at, updated_at
- `User`: id (UUID PK), clinic_id (FK NOT NULL), email (UNIQUE per clinic_id), password_hash, rol (recepcion|odonto|admin), activo, odontologo_id (nullable FK to users), is_active, created_at, updated_at
- `Paciente`: id (UUID PK), clinic_id (FK NOT NULL), nombre, telefono (E.164 AR), dni (nullable), is_active, created_at, updated_at
- `Sillon`: id (UUID PK), clinic_id (FK NOT NULL), nombre, activo, is_active, created_at, updated_at
- `Bloqueo`: id (UUID PK), clinic_id (FK NOT NULL), paciente_id (FK NOT NULL), desde, hasta, motivo, created_by, is_active, created_at, updated_at

**Acceptance criteria:**
- All models inherit from `Base` (SQLAlchemy declarative base from C-01)
- All business models inherit from `AuditMixin`
- `clinic_id` is NOT NULL FK on all tables except `Clinic`
- `User.email` has UNIQUE constraint scoped to `clinic_id`
- `Paciente` has indexes on `(clinic_id, telefono)` and `(clinic_id, dni)`

### R2 — AuditMixin
All business models SHALL include `AuditMixin` with:
- `is_active` (boolean, default True, NOT NULL)
- `created_at` (timestamp, server_default now(), NOT NULL)
- `updated_at` (timestamp, server_default now(), onupdate now(), NOT NULL)

**Acceptance criteria:**
- `AuditMixin` is a SQLAlchemy mixin class
- All models except `Clinic` inherit from `AuditMixin`
- `created_at` and `updated_at` managed automatically by ORM

### R3 — Repository pattern + UnitOfWork
The backend SHALL provide:
- `BaseRepository[T]` generic class with CRUD: get, list, create, update, delete (soft)
- `UnitOfWork` class with `commit()` and `rollback()` methods

**Acceptance criteria:**
- `BaseRepository` is generic over model type `T`
- `UnitOfWork` accepts AsyncSession and provides commit/rollback
- Repositories accept a database session in constructor

### R4 — clinic_id mandatory on all business tables
All business tables SHALL have `clinic_id` as mandatory FK (except `Clinic`).

**Acceptance criteria:**
- `clinic_id` column is NOT NULL on `users`, `pacientes`, `sillones`, `bloqueos`
- `clinic_id` references `clinic.id`
- Queries filter by `clinic_id` for multi-tenant isolation

### R5 — Migration 002
Alembic migration SHALL create:
- Table `clinic`
- Table `users` (email UNIQUE per clinic_id)
- Table `pacientes` (indexes `(clinic_id, telefono)`, `(clinic_id, dni)`)
- Table `sillones`
- Table `bloqueos`

**Acceptance criteria:**
- Migration file exists under `backend/app/infrastructure/db/migrations/versions/`
- `alembic upgrade head` creates all tables successfully
- `alembic downgrade base` drops all tables successfully

### R6 — Seed mínimo (idempotente)
Seed SHALL include:
- 1 `Clinic` (timezone America/Argentina/Buenos_Aires, wa_sender Twilio, cuenta MP)
- 1 `User` rol `admin`
- 1 `User` rol `recepcion`
- 1 `User` rol `odonto`
- 2-3 `Sillon` activos

**Acceptance criteria:**
- Seed script exists and is idempotent (running twice doesn't duplicate data)
- Seed uses `clinic_id` FK consistently
- Seed passwords are hashed (not plain text)

### R7 — Tests
Tests SHALL cover:
- UNIQUE constraints on `clinic.users.email` per clinic
- `clinic_id` filters present on all queries
- Seed is idempotent
- Migration 002 upgrade/downgrade

**Acceptance criteria:**
- Test files exist under `backend/tests/`
- All tests pass with `pytest`

## Constraints

- `clinic_id` FK obligatorio en todas las tablas de negocio (excepto `Clinic`)
- Timezone: `America/Argentina/Buenos_Aires`
- 1 clínica en v1 (sin multi-sede, pero `clinic_id` desde día 1 como preparación — DD-06)
- Stack: Python/FastAPI/SQLAlchemy/PostgreSQL/Redis/Docker-Compose

## Edge Cases

1. Duplicate email per clinic → UNIQUE constraint violation (409)
2. Seed run twice → idempotent, no duplicates
3. Missing clinic_id on insert → NOT NULL constraint violation
4. Deleting clinic with related users → FK cascade behavior
5. Password stored as bcrypt hash, never plaintext

## Scenarios

### Scenario: Model creation with all required fields
- **WHEN** creating a Clinic with nombre and timezone
- **THEN** record is created with is_active=True, created_at/updated_at populated

### Scenario: Email uniqueness per clinic
- **WHEN** inserting two users with same email in same clinic
- **THEN** second insert raises IntegrityError

### Scenario: clinic_id NOT NULL constraint
- **WHEN** inserting a User without clinic_id
- **THEN** database raises NOT NULL violation

### Scenario: Seed idempotency
- **WHEN** running seed script twice
- **THEN** no duplicate clinics, users, or sillones

### Scenario: Migration upgrade/downgrade
- **WHEN** running `alembic upgrade head` then `alembic downgrade base`
- **THEN** all tables created then dropped without error
