# Spec Delta

## Purpose

Initializes Alembic for PostgreSQL schema evolution with a baseline migration and configuration for the modular monolith.

## ADDED Requirements

### Requirement: Alembic initialized and configured
The backend SHALL have Alembic initialized with `alembic.ini` and `migrations/` directory under `backend/app/infrastructure/db/`.

#### Scenario: Alembic configuration exists
- **WHEN** checking `backend/app/infrastructure/db/alembic.ini`
- **THEN** file exists with correct `sqlalchemy.url` placeholder

#### Scenario: Migrations directory exists
- **WHEN** checking `backend/app/infrastructure/db/migrations/`
- **THEN** directory exists with `env.py`, `script.py.mako`, and `versions/`

### Requirement: Baseline migration for initial schema
The project SHALL include an initial migration (revision 001) that creates the baseline tables for the foundation (no business tables yet — those come in C-02).

#### Scenario: Initial migration creates alembic_version table
- **WHEN** running `alembic upgrade head` on empty database
- **THEN** `alembic_version` table is created with the revision identifier

#### Scenario: Migration is idempotent
- **WHEN** running `alembic upgrade head` twice
- **THEN** second run reports "Already at head" with no errors

### Requirement: Alembic uses application models
The Alembic `env.py` SHALL import the SQLAlchemy `Base` from the application's database module to autogenerate migrations from models.

#### Scenario: Autogenerate detects model changes
- **WHEN** running `alembic revision --autogenerate -m "message"` after adding a model
- **THEN** a new migration file is created with the detected changes

#### Scenario: Models use declarative base
- **WHEN** checking `app/infrastructure/db/base.py`
- **THEN** a `Base = declarative_base()` is exported for models to inherit

### Requirement: Migration naming convention
Migrations SHALL follow the naming convention `NNN_description.py` where NNN is a zero-padded sequence number.

#### Scenario: First migration numbered 001
- **WHEN** listing migrations with `alembic history`
- **THEN** first migration starts with `001_`

### Requirement: Database URL from settings
Alembic SHALL read the database URL from the application's Pydantic Settings rather than hardcoding in `alembic.ini`.

#### Scenario: Alembic uses runtime DATABASE_URL
- **WHEN** running `alembic upgrade head` with `DATABASE_URL` set
- **THEN** migration connects to the configured database