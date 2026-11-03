# Design — C-02 core-models-clinica-personas

## Context

Builds on C-01 foundation (FastAPI app, Pydantic settings, SQLAlchemy base, Alembic, structlog, exception handlers). Follows KB 04_modelo_de_datos.md ERD, KB 08_arquitectura_propuesta.md patterns, KB 09_decisiones_y_supuestos.md decisions (DD-02, DD-06), KB 03_actores_y_roles.md RBAC matrix.

## Architecture Decisions

### 1. Multi-tenancy by clinic_id from day 1 (DD-06)
**Decision**: All business tables carry `clinic_id` as a mandatory FK referencing `clinic.id`. Clinic itself has no clinic_id.
**Rationale**: Prepares for multi-sede in v2 without schema migration. Cost today is one column + index; remodelling later is painful.
**Alternatives**: Model without clinic_id and migrate in v2 (rejected — migration pain).

### 2. AuditMixin pattern
**Decision**: All business models inherit from `AuditMixin` providing `is_active`, `created_at`, `updated_at`.
**Rationale**: Soft deletes + audit trail without ad-hoc columns per model.
**Alternatives**: Add columns individually per model (rejected — inconsistency).

### 3. Repository + UnitOfWork pattern
**Decision**: `BaseRepository[T]` generic CRUD + `UnitOfWork` managing session boundaries.
**Rationale**: Decouples business logic from persistence; enables atomic transactions across multiple repositories.
**Alternatives**: Direct SQLAlchemy in service layer (rejected — harder to test, tightly coupled).

### 4. Soft delete vs hard delete
**Decision**: `is_active=False` soft delete for models with AuditMixin; hard delete only for models without it.
**Rationale**: Preserves referential integrity and audit history.
**Alternatives**: Hard delete everywhere (rejected — loses audit trail, breaks FK references).

### 5. Password hashing with bcrypt
**Decision**: Use `passlib[bcrypt]` for password hashing (already in pyproject.toml).
**Rationale**: Industry standard, already available as dependency, secure.
**Alternatives**: argon2 (good but not in dependencies yet), plaintext (rejected — security violation).

### 6. UUID primary keys
**Decision**: All models use `UUID` primary keys with `uuid4()` default.
**Rationale**: Prevents ID enumeration, supports distributed generation, matches KB 04.
**Alternatives**: Integer auto-increment (rejected — security through obscurity issues).

### 7. Odontólogo confinement via odontologo_id
**Decision**: `User.odontologo_id` is a self-referential FK (nullable), used to confine odontólogos to their own appointments/patients.
**Rationale**: Matches KB 03 RBAC matrix — odontólogo sees only their own data.
**Alternatives**: Separate Odontólogo table (rejected — over-engineering for v1).

## Entity Relationship Diagram (textual)

```
Clinic 1──* User (clinic_id FK)
Clinic 1──* Paciente (clinic_id FK)
Clinic 1──* Sillon (clinic_id FK)
Clinic 1──* Bloqueo (clinic_id FK)
User(odonto) 1──* Turno (via odontologo_id — C-05)
Sillon 1──* Turno (via sillon_id — C-05)
Paciente 1──* Turno (via paciente_id — C-05)
Paciente 1──* Bloqueo (via paciente_id — C-07)
User 1──* Bloqueo (created_by — C-07)
```

## Directory Structure

```
backend/app/domain/clinica/
├── __init__.py
├── models.py          # Clinic, Sillon, Bloqueo
├── schemas.py         # Pydantic schemas (create/update/out)
└── repository.py      # ClinicRepository, SillonRepository, BloqueoRepository

backend/app/domain/personas/
├── __init__.py
├── models.py          # User, Paciente
├── schemas.py         # Pydantic schemas
└── repository.py      # UserRepository, PacienteRepository

backend/app/core/
├── mixins.py          # AuditMixin (new)
├── repository.py      # BaseRepository[T] + UnitOfWork (new)
└── security.py        # Password hashing utilities (new)

backend/app/infrastructure/db/migrations/versions/
├── 002_clinica_personas.py  # Migration 001 for C-02 (numbered 002 since 001 is C-01 baseline)

backend/scripts/
└── seed.py            # Idempotent seed script

backend/tests/
├── test_models.py
├── test_audit_mixin.py
├── test_repository.py
├── test_clinic_id.py
├── test_migration_002.py
└── test_seed.py
```

## Files to Create

| File | Purpose |
|------|---------|
| `backend/app/core/mixins.py` | `AuditMixin` with is_active, created_at, updated_at |
| `backend/app/core/repository.py` | `BaseRepository[T]` + `UnitOfWork` |
| `backend/app/core/security.py` | `hash_password`, `verify_password` (bcrypt) |
| `backend/app/domain/clinica/models.py` | `Clinic`, `Sillon`, `Bloqueo` models |
| `backend/app/domain/clinica/schemas.py` | Pydantic schemas for clinica domain |
| `backend/app/domain/clinica/repository.py` | Repositories for clinica domain |
| `backend/app/domain/personas/models.py` | `User`, `Paciente` models |
| `backend/app/domain/personas/schemas.py` | Pydantic schemas for personas domain |
| `backend/app/domain/personas/repository.py` | Repositories for personas domain |
| `backend/app/infrastructure/db/migrations/versions/002_clinica_personas.py` | Migration 002 (C-02 initial schema) |
| `backend/scripts/seed.py` | Idempotent seed script |
| `backend/tests/test_models.py` | Model field/type tests |
| `backend/tests/test_audit_mixin.py` | AuditMixin behavior |
| `backend/tests/test_repository.py` | Repository CRUD + UnitOfWork |
| `backend/tests/test_clinic_id.py` | clinic_id NOT NULL + FK constraints |
| `backend/tests/test_migration_002.py` | Alembic migration 002 |
| `backend/tests/test_seed.py` | Seed idempotency |

## Files to Modify

| File | Change |
|------|--------|
| `backend/app/domain/clinica/__init__.py` | Already exists (empty) — no change needed |
| `backend/app/domain/personas/__init__.py` | Already exists (empty) — no change needed |
| `backend/app/infrastructure/db/base.py` | Already exists — `Base` already defined |

## Verification Strategy

Each requirement has corresponding tests:
- R1 (models) → `test_models.py`
- R2 (AuditMixin) → `test_audit_mixin.py`
- R3 (Repository + UnitOfWork) → `test_repository.py`
- R4 (clinic_id mandatory) → `test_clinic_id.py`
- R5 (migration 002) → `test_migration_002.py`
- R6 (seed) → `test_seed.py`

Edge cases to verify:
- Duplicate email per clinic → UNIQUE constraint error
- Seed run twice → no duplicates (idempotent)
- Missing clinic_id on insert → NOT NULL constraint violation
- Deleting clinic with related users → FK cascade/restrict
