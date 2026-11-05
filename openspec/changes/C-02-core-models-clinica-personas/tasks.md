# Tasks — C-02 core-models-clinica-personas

## 1. Modelos de dominio

- [ ] 1.1 Crear `app/domain/clinica/models.py`: `Clinic` (id uuid, nombre, timezone, wa_sender, mp_account, activa, created_at, updated_at), `Sillon` (id, clinic_id fk, nombre, activo, created_at, updated_at). Heredan de `AuditMixin`.
- [ ] 1.2 Crear `app/domain/personas/models.py`: `User` (id, clinic_id fk, email UNIQUE por clinic_id, password_hash, rol, nombre, activo, created_at), `Paciente` (id, clinic_id fk, nombre, telefono E.164 AR, dni nullable, user_id nullable, faltas_count default 0, bloqueado_hasta nullable, created_at), `Bloqueo` (id, paciente_id fk, motivo, desde, hasta, created_by, created_at).
- [ ] 1.3 Crear `app/domain/audit.py` con `AuditMixin` (`is_active`, `created_at`, `updated_at`).
- [ ] 1.4 Crear `app/domain/base_repository.py` con `BaseRepository[T]` (get, list, create, update, delete, exists async).
- [ ] 1.5 Crear `app/domain/uow.py` con `UnitOfWork` (coordina repos en una transacción async).
- [ ] 1.6 Verificar imports: `from app.domain import clinica, personas` funciona.

## 2. Migración 001 y seed

- [ ] 2.1 Generar migración 001 con `alembic revision --autogenerate -m "init clinic users pacientes sillones bloqueos"`.
- [ ] 2.2 Revisar migración 001: tablas clinic, users, pacientes, sillones, bloqueos; índices `(clinic_id, telefono)`, `(clinic_id, dni)`; constraint `uq_users_clinic_id_email`; CHECK `sena_pct` (documentar, se crea en C-04).
- [ ] 2.3 Ejecutar `alembic upgrade head` y verificar que se crean las tablas.
- [ ] 2.4 Ejecutar `alembic downgrade -1` y verificar rollback limpio.
- [ ] 2.5 Crear script de seed idempotente: 1 Clinic (timezone AR, wa_sender, mp_account), 1 admin + 1 recepción + 1 odontólogo, 2-3 Sillon activos. Usar `ON CONFLICT DO NOTHING` o check `exists()`.
- [ ] 2.6 Verificar seed idempotente: ejecutar dos veces, no hay duplicados.

## 3. Tests (TDD — RED primero)

### 3.1 Test: clinic_id obligatorio en todas las tablas de negocio (DD-06)
- RED: test falla porque falta clinic_id en algún modelo.
- GREEN: agregar clinic_id a todos los modelos.
- Verificable: consulta `information_schema.columns` filtra tablas sin clinic_id.

### 3.2 Test: email UNIQUE por clínica (no global)
- **Escenario 1 — Funcionamiento esperado:** Crear dos usuarios con mismo email pero diferente clinic_id → ambos se insertan correctamente.
- **Escenario 2 — Error de negocio:** Crear dos usuarios con mismo email y mismo clinic_id → DB rechaza con unique_violation (23505).
- **Escenario 3 — Caso de borde:** Intentar insertar usuario con email NULL → permitido (nullable) o rechazado según diseño; documentar decisión.

### 3.3 Test: sena_pct CHECK 0-100 (regla de dominio TipoPractica)
- **Escenario 1 — Funcionamiento esperado:** TipoPractica con sena_pct=20 se inserta.
- **Escenario 2 — Error de negocio:** TipoPractica con sena_pct=150 → DB rechaza con CHECK violation.
- **Escenario 3 — Caso de borde:** TipoPractica con sena_pct=0 y sena_pct=100 → ambos se insertan (límites inclusivos).

### 3.4 Test: seed idempotente
- Ejecutar seed dos veces; contar filas de Clinic, User, Sillon;assert que no se duplican.

### 3.5 Test: filtros clinic_id omnipresentes
- Query de Paciente sin filtro clinic_id → debe retornar solo filas de la clinic esperada (test con 2 clínicas en DB de test).

## 4. Verificación de calidad

- [ ] 4.1 `ruff check backend/app` limpio.
- [ ] 4.2 `ruff format --check backend/app` limpio.
- [ ] 4.3 `mypy backend/app/domain` limpio.
- [ ] 4.4 `pytest backend/app --cov=app --cov-fail-under=80` pasa completo.

## 5. Workflow follow-up

- [ ] No marcar C-02 como implementado/verificado/archivado (queda preparado para implementar en instancia posterior).
- [ ] Referenciar C-02 en CHANGES.md como preparado (no marcar `[x]`).

## Escenarios verificables (resumen para el spec)

| # | Tipo | Contexto | Acción | Resultado esperado | Regla de referencia |
|---|------|----------|--------|-------------------|--------------------|
| 1 | Funcionamiento esperado | Dos clínicas, mismo email en cada una | Insertar 2 usuarios mismo email, diferente clinic_id | Ambos insertados OK | 04_modelo_de_datos §User |
| 2 | Error de negocio | Una clínica, usuario existente con email X | Insertar otro usuario mismo email, mismo clinic_id | DB rechaza unique_violation | RN-ADMIN-01, 04_modelo_de_datos §User |
| 3 | Caso de borde | TipoPractica con sena_pct fuera de rango | Insertar sena_pct=150 | DB rechaza CHECK violation | 04_modelo_de_datos §TipoPractica (CHECK 0-100) |
