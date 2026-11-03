# Proposal — C-02 core-models-clinica-personas

## Why

This is the second change in the critical path (Gate 1, depends on C-01). It establishes the core domain models for the SaaS Odontología project: Clinic, User, Paciente, Sillon, Bloqueo, plus the foundational patterns (AuditMixin, BaseRepository[T], UnitOfWork) and `clinic_id` multi-tenancy from day 1 (DD-06). Without these models, no subsequent change (C-03 auth, C-04 catálogo, C-05 motor turnos) can be built.

## What Changes

### Backend domain models
- `Clinic` — 1 clínica en v1, timezone AR, wa_sender Twilio, cuenta MP
- `User` — rol recepcion|odonto|admin, email UNIQUE por clínica, password_hash, odontologo_id (confinamiento)
- `Paciente` — nombre, teléfono E.164 AR, DNI, índices (clinic_id, teléfono), (clinic_id, DNI)
- `Sillon` — nombre, activo, clinic_id FK
- `Bloqueo` — paciente_id, desde, hasta, motivo, created_by (estructura; lógica completa en C-07)

### Patterns
- `AuditMixin` — is_active, created_at, updated_at en todos los modelos de negocio
- `BaseRepository[T]` — CRUD genérico tipado
- `UnitOfWork` — límites de transacción atómicos (commit/rollback)
- `clinic_id` FK obligatorio en todas las tablas de negocio excepto Clinic

### Migration 001
- Tablas: `clinic`, `users`, `pacientes`, `sillones`, `bloqueos`
- Constraints: email UNIQUE por clinic_id; índices compuestos (clinic_id, telefono), (clinic_id, dni)

### Seed mínimo (idempotente)
- 1 Clinic (timezone AR, wa_sender, mp_account)
- 1 admin + 1 recepción + 1 odontólogo
- 2-3 Sillones activos

### Tests
- Constraints UNIQUE (email por clínica)
- Filtros clinic_id omnipresentes
- Seed idempotente

## Capabilities

### New Capabilities

- `clinica-personas/domain-models`: SQLAlchemy models for clinic, users, pacientes, sillones, bloqueos with AuditMixin
- `clinica-personas/repository-pattern`: BaseRepository[T] generic + UnitOfWork for transaction boundaries
- `clinica-personas/migration-001`: Alembic migration 001 creating initial schema
- `clinica-personas/seed-data`: Idempotent seed script with clinic, users, sillones

### Modified Capabilities

- None — C-02 builds on C-01 foundation but does not modify existing capabilities.

## Impact

- **Code**: New domain models, repositories, migration 001, seed script, ~7 test files
- **APIs**: None (no endpoints in C-02 — those come in C-03+)
- **Dependencies**: SQLAlchemy 2.0, Alembic, psycopg/asyncpg, passlib[bcrypt] (already in pyproject.toml)
- **Systems**: PostgreSQL 16 via Docker Compose (already in C-01)

## Dependencies

- C-01 foundation-setup (must be complete and archived)

## Out of Scope

- Authentication/JWT (C-03)
- Appointment/Turno model (C-05)
- Aranceles/TipoPractica CRUD (C-04/C-13)
- Login paciente (C-11, v1.1)
- Bloqueo lógica de 2 faltas (C-07)
