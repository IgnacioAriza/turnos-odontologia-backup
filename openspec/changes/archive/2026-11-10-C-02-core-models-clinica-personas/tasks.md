# Tasks — C-02 core-models-clinica-personas

> Estado final: implementado, verificado y archivado el 2026-11-10.

## 1. Modelos de dominio

- [x] 1.1 Crear `app/domain/clinica/models.py`: `Clinic` (id uuid, nombre, timezone, wa_sender, mp_account, activa, created_at, updated_at), `Sillon` (id, clinic_id fk, nombre, activo, created_at, updated_at) y `Bloqueo`. Heredan de `AuditMixin`.
- [x] 1.2 Crear `app/domain/personas/models.py`: `User` (id, clinic_id fk, email UNIQUE por clinic_id, password_hash, rol, activo, odontologo_id, created_at), `Paciente` (id, clinic_id fk, nombre, telefono E.164 AR, dni nullable, user_id nullable, faltas_count default 0, bloqueado_hasta nullable, created_at).
- [x] 1.3 Crear `AuditMixin` (`is_active`, `created_at`, `updated_at`) en `app/core/mixins.py`.
- [x] 1.4 Crear `BaseRepository[T]` (get, list, create, update, delete, exists async) en `app/core/repository.py`.
- [x] 1.5 Crear `UnitOfWork` (coordina repos en una transacción async) en `app/core/repository.py`.
- [x] 1.6 Verificar imports: `from app.domain import clinica, personas` funciona (`tests/test_imports.py`).

## 2. Migración 002 y seed

- [x] 2.1 Crear la migración `002_clinica_personas.py` con las tablas del esquema inicial.
- [x] 2.2 Revisar la migración: tablas `clinic`, `users`, `pacientes`, `sillones`, `bloqueos`; índices `(clinic_id, telefono)` y `(clinic_id, dni)`; constraint `uq_users_clinic_id_email`. El CHECK `sena_pct` se difirió a C-04.
- [x] 2.3 Ejecutar `alembic upgrade head` y verificar que se crean las tablas.
- [x] 2.4 Ejecutar `alembic downgrade -1` y verificar rollback limpio.
- [x] 2.5 Crear script de seed idempotente: 1 Clinic (timezone AR, wa_sender, mp_account), 1 admin + 1 recepción + 1 odontólogo, sillones activos. Usa `exists()`/búsqueda idempotente.
- [x] 2.6 Verificar seed idempotente: ejecutarlo dos veces no duplica filas (`tests/test_seed.py`).

## 3. Tests (TDD — RED primero)

- [x] 3.1 Test: `clinic_id` obligatorio en todas las tablas de negocio (DD-06) — `tests/test_clinic_id.py`.
- [x] 3.2 Test: email UNIQUE por clínica (no global): mismo email en dos clínicas se acepta; mismo email y misma clínica falla (`tests/test_models.py`).
- [x] 3.3 Test: CHECK `sena_pct` 0-100 de `TipoPractica` (creado en C-04) — `tests/test_catalogo_models.py`.
- [x] 3.4 Test: seed idempotente, sin duplicados — `tests/test_seed.py`.
- [x] 3.5 Test: filtros `clinic_id` omnipresentes con dos clínicas en la DB de test — `tests/test_clinic_id.py` y `tests/test_repository.py`.
- [x] 3.6 Test: `AuditMixin` puebla `is_active`, `created_at` y `updated_at` — `tests/test_audit_mixin.py`.

## 4. Verificación de calidad

- [x] 4.1 `ruff check backend/app` limpio en la implementación de C-02.
- [x] 4.2 `ruff format --check backend/app` limpio en la implementación de C-02.
- [x] 4.3 `mypy backend/app/domain` limpio.
- [x] 4.4 `pytest` pasa completo con el umbral de cobertura vigente del CI (`--cov-fail-under=50`; el 80% original fue reemplazado por la config de CI).

## 5. Workflow follow-up

- [x] C-02 implementado, verificado y archivado el 2026-11-10 (la directiva original de dejarlo "preparado" quedó superada).
- [x] `CHANGES.md` referencia C-02 como implementado `[x]`.

## Escenarios verificables (resumen para el spec)

| # | Tipo | Contexto | Acción | Resultado esperado | Regla de referencia |
|---|------|----------|--------|-------------------|--------------------|
| 1 | Funcionamiento esperado | Dos clínicas, mismo email en cada una | Insertar 2 usuarios mismo email, diferente clinic_id | Ambos insertados OK | 04_modelo_de_datos §User |
| 2 | Error de negocio | Una clínica, usuario existente con email X | Insertar otro usuario mismo email, mismo clinic_id | DB rechaza unique_violation | RN-ADMIN-01, 04_modelo_de_datos §User |
| 3 | Caso de borde | TipoPractica con sena_pct fuera de rango | Insertar sena_pct=150 | DB rechaza CHECK violation | 04_modelo_de_datos §TipoPractica (CHECK 0-100) |
