# Tasks — C-02 core-models-clinica-personas

**Change:** C-02 core-models-clinica-personas  
**Schema:** spec-driven  
**Status:** implemented ✅

---

## Task 1 — Create AuditMixin, BaseRepository[T], UnitOfWork, and security ✅ DONE

Archivos creados:
- `backend/app/core/mixins.py` — `AuditMixin` con is_active, created_at, updated_at
- `backend/app/core/repository.py` — `BaseRepository[T]` + `UnitOfWork`
- `backend/app/core/security.py` — `hash_password`, `verify_password` (bcrypt)

**Verificación:** test_audit_mixin.py, test_repository.py

**Checkbox:** `- [x]`

---

## Task 2 — Create domain models (Clinic, User, Paciente, Sillon, Bloqueo) ✅ DONE

Archivos creados:
- `backend/app/domain/clinica/models.py` — Clinic, Sillon, Bloqueo
- `backend/app/domain/personas/models.py` — User, Paciente

Todos heredan de `Base` + `AuditMixin`, con `clinic_id` FK NOT NULL excepto Clinic.

**Verificación:** test_models.py, test_clinic_id.py

**Checkbox:** `- [x]`

---

## Task 3 — Create Pydantic schemas and repositories ✅ DONE

Archivos creados:
- `backend/app/domain/clinica/schemas.py` — schemas Clinic, Sillon, Bloqueo
- `backend/app/domain/personas/schemas.py` — schemas User, Paciente
- `backend/app/domain/clinica/repository.py` — ClinicRepository, SillonRepository, BloqueoRepository
- `backend/app/domain/personas/repository.py` — UserRepository, PacienteRepository

**Verificación:** test_repository.py

**Checkbox:** `- [x]`

---

## Task 4 — Create migration 002 (initial schema) ✅ DONE

Archivo creado:
- `backend/app/infrastructure/db/migrations/versions/002_clinica_personas.py` — tablas clinic, users, pacientes, sillones, bloqueos con constraints UNIQUE e índices compuestos

**Verificación:** test_migration_002.py

**Checkbox:** `- [x]`

---

## Task 5 — Create idempotent seed script ✅ DONE

Archivo creado:
- `backend/scripts/seed.py` — 1 Clinic, 1 admin + 1 recepción + 1 odontólogo, 3 sillones activos

**Verificación:** test_seed.py

**Checkbox:** `- [x]`

---

## Task 6 — Tests suite ✅ DONE

Archivos creados:
- `backend/tests/test_models.py` — modelos de dominio
- `backend/tests/test_audit_mixin.py` — AuditMixin
- `backend/tests/test_repository.py` — Repository + UnitOfWork
- `backend/tests/test_clinic_id.py` — clinic_id obligatorio
- `backend/tests/test_migration_002.py` — migración 002
- `backend/tests/test_seed.py` — seed idempotente

**Checkbox:** `- [x]`

---

## Edge Case Verification ✅ DONE

| Edge case | Task | Verification |
|-----------|------|--------------|
| Duplicate email per clinic | Task 2 | UNIQUE constraint raises error (test_models.py) |
| Seed run twice | Task 5 | No duplicates, idempotent (test_seed.py) |
| Missing clinic_id on insert | Task 2 | NOT NULL constraint violation (test_clinic_id.py) |
| Deleting clinic with related users | Task 4 | FK restrict/cascade (migración 002) |

**Checkbox:** `- [x]`

---

## Implementation order

Tasks 1 → 2 → 3 → 4 → 5 → 6. Todos completados ✅
