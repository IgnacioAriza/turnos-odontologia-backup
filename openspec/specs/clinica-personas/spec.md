# Spec — clinica-personas

## Purpose

Core domain models for the SaaS Odontología project: Clinic, User, Paciente, Sillon and Bloqueo, plus AuditMixin, BaseRepository[T] and UnitOfWork patterns, with clinic_id multi-tenancy from day one.

## Requirements

### Requirement: Clinic model

`Clinic` SHALL store `id` (UUID PK), `nombre`, `timezone`, `wa_sender`, `mp_account`, `is_active`, `created_at` and `updated_at`.

#### Scenario: Clinic creation

- **WHEN** a Clinic is created with nombre and timezone
- **THEN** the record is stored with `is_active=true` and both timestamps populated

### Requirement: User model

`User` SHALL store `id` (UUID PK), `clinic_id` (FK NOT NULL), `email` (UNIQUE per clinic), `password_hash`, `rol` (recepcion|odonto|admin), `activo`, optional `odontologo_id` and the audit fields.

#### Scenario: Email uniqueness per clinic

- **WHEN** two users with the same email are inserted in the same clinic
- **THEN** the second insert raises an IntegrityError

#### Scenario: Same email in different clinics

- **WHEN** two users with the same email are inserted in different clinics
- **THEN** both inserts succeed

#### Scenario: Passwords are never stored in plain text

- **WHEN** a user is persisted
- **THEN** `password_hash` contains a bcrypt or argon2 hash, never the plain password

### Requirement: Paciente and Sillon models

`Paciente` SHALL store `clinic_id`, `nombre`, `telefono` (E.164 AR), nullable `dni` and audit fields. `Sillon` SHALL store `clinic_id`, `nombre`, `activo` and audit fields.

#### Scenario: Patient search indexes exist

- **WHEN** migration 002 runs
- **THEN** the `(clinic_id, telefono)` and `(clinic_id, dni)` indexes exist on `pacientes`

#### Scenario: Sillon belongs to a clinic

- **WHEN** a Sillon is created
- **THEN** it requires a non-null `clinic_id`

### Requirement: Bloqueo model

`Bloqueo` SHALL store `clinic_id`, `paciente_id`, `desde`, `hasta`, `motivo`, `created_by` and the audit fields.

#### Scenario: Bloqueo requires patient and clinic

- **WHEN** a Bloqueo is created without `paciente_id` or `clinic_id`
- **THEN** the database rejects it with a NOT NULL violation

### Requirement: Audit mixin

Business models SHALL include `AuditMixin` with `is_active` (default true), `created_at` and `updated_at` managed by the ORM.

#### Scenario: Audit fields are automatic

- **WHEN** a business model is created and later updated
- **THEN** `created_at` is set once and `updated_at` changes on update

### Requirement: Repository and Unit of Work

The backend SHALL provide a generic `BaseRepository[T]` with get, list, create, update and soft-delete, plus a `UnitOfWork` exposing `commit()` and `rollback()` over an async session.

#### Scenario: Repository CRUD works

- **WHEN** a repository is constructed with a session
- **THEN** get, list, create, update and soft-delete operate on its model

#### Scenario: Unit of Work rolls back

- **WHEN** an operation fails inside a UnitOfWork
- **THEN** `rollback()` leaves the database unchanged

### Requirement: Mandatory clinic_id isolation

Every business table SHALL require a non-null `clinic_id` FK to `clinic.id`, and queries SHALL filter by it.

#### Scenario: Missing clinic_id is rejected

- **WHEN** a business row is inserted without `clinic_id`
- **THEN** the database raises a NOT NULL violation

#### Scenario: Cross-clinic rows are filtered

- **WHEN** a table holds rows for two clinics and a query filters by one `clinic_id`
- **THEN** only the rows of that clinic are returned

### Requirement: Migration 002

Alembic migration 002 SHALL create `clinic`, `users`, `pacientes`, `sillones` and `bloqueos`, with the email uniqueness constraint and the patient indexes.

#### Scenario: Upgrade creates all tables

- **WHEN** `alembic upgrade head` runs
- **THEN** all five tables exist with their constraints

#### Scenario: Downgrade drops all tables

- **WHEN** `alembic downgrade base` runs
- **THEN** all five tables are dropped without error

### Requirement: Idempotent seed

The seed SHALL create one Clinic, one admin, one recepción, one odontólogo and two to three active sillones, and SHALL be safe to run twice.

#### Scenario: Seed creates the baseline

- **WHEN** the seed runs on an empty database
- **THEN** one clinic, three users and at least two sillones exist

#### Scenario: Seed is idempotent

- **WHEN** the seed runs twice
- **THEN** no duplicate clinics, users or sillones are created

### Requirement: Domain test coverage

Tests SHALL cover email uniqueness, clinic_id filtering, seed idempotency and migration upgrade/downgrade.

#### Scenario: Domain suite passes

- **WHEN** `pytest` runs
- **THEN** the model, migration and seed tests pass

## Constraints

- `clinic_id` FK obligatorio en todas las tablas de negocio (excepto `Clinic`)
- Timezone: `America/Argentina/Buenos_Aires`
- 1 clínica en v1 (sin multi-sede, pero `clinic_id` desde el día 1 como preparación — DD-06)
- Stack: Python/FastAPI/SQLAlchemy/PostgreSQL/Redis/Docker-Compose
