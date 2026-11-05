# Design — C-02 core-models-clinica-personas

## Context

C-01 ya estableció el scaffoundation: estructura modular `app/{core, domain/{turnos,pagos,notificaciones,clinica,personas}, infrastructure/{db,queue,integrations}, api/{public,internal,webhooks}}`, `core/config.py` (12 vars), `core/exceptions.py` (RFC 7807), `core/logging.py` (structlog), `infrastructure/db/base.py` (SQLAlchemy async), `main.py` con `/api/health`, Alembic inicializado. C-02 añade los primeros modelos de negocio y la migración 001.

## Goals / Non-Goals

**Goals:**
- Modelos SQLAlchemy 2.0 para Clinic, User, Paciente, Sillon, Bloqueo.
- `AuditMixin` con `is_active`, `created_at`, `updated_at`.
- `BaseRepository[T]` + `UnitOfWork` patrón.
- `clinic_id` FK obligatorio en todas las tablas de negocio (DD-06).
- Migración 001: tablas clinic, users, pacientes, sillones, bloqueos.
- Índices: `(clinic_id, telefono)`, `(clinic_id, dni)` en pacientes; email UNIQUE por clínica en users.
- Seed mínimo idempotente: 1 clinic, 1 admin + 1 recepción + 1 odontólogo, 2-3 sillones.
- Tests: constraints UNIQUE, filtros clinic_id, seed idempotente.

**Non-Goals:**
- No endpoints API (llegan en C-03+).
- No lógica de anti-solape (C-05).
- No auth JWT (C-03).
- No catálogo de prácticas/aranceles (C-04).
- No lógica de bloqueo por 2 faltas (C-07); Bloqueo solo estructura.

## Decisions

### 1. Modelos SQLAlchemy 2.0 declarativos (async)
**Decision:** Usar `sqlalchemy.orm.DeclarativeBase` con `Mapped[mapped_column]` en `app/domain/{clinica,personas}/models.py`. Sesión async (`AsyncSession`) en `infrastructure/db/base.py`.

**Rationale:** Coherente con C-01 (SQLAlchemy 2.0 async). FastAPI es async-native.

**Alternatives:** SQLAlchemy sync (bloquea event loop); otro ORM (no está en el stack dado).

### 2. `clinic_id` obligatorio desde día 1 (DD-06)
**Decision:** Todas las tablas de negocio llevan `clinic_id` como FK no nulo, aunque v1 sea 1 clínica.

**Rationale:** Costo bajo hoy (una columna + índice); re-modelar multi-sede después es doloroso.

**Alternatives:** Sin clinic_id y migrar en v2 (rechazado por DD-06).

### 3. `AuditMixin`
**Decision:** Mixin con `is_active: bool = True`, `created_at: DateTime`, `updated_at: DateTime`. Heredado por todos los modelos de negocio.

**Rationale:** Soft delete y trazabilidad de creación/modificación en todas las entidades.

**Alternatives:** Columnas duplicadas en cada modelo (más boilerplate).

### 4. `BaseRepository[T]` + `UnitOfWork`
**Decision:** Repositorio genérico con métodos CRUD async (`get`, `list`, `create`, `update`, `delete`, `exists`). UnitOfWork coordina múltiples repos en una transacción.

**Rationale:** Separación de acceso a datos y lógica de negocio; facilita testing con mocks.

**Alternatives:** Queries directas en services (acoplamiento).

### 5. Índices y constraints
**Decision:**
- `users.email` UNIQUE con `clinic_id` (único por clínica, no global).
- `pacientes`: índice `(clinic_id, telefono)`, índice `(clinic_id, dni)`.
- `TipoPractica.sena_pct` CHECK 0-100 y `Turno.fin > inicio` CHECK son reglas de dominio documentadas aquí como referencia futura, pero las tablas `TipoPractica` y `Turno` se crean en C-04 y C-05 respectivamente, no en C-02.

**Rationale:** Cumple 04_modelo_de_datos.md y reglas RN. Las constraints de tablas ajenas a C-02 se documentan como referencia pero no se implementan en esta migración.

**Alternatives:** Sin índices (consultas lentas por clinic_id).

### 6. Seed idempotente
**Decision:** El seed usa `INSERT ... ON CONFLICT DO NOTHING` (o equivalente con `exists()` check) para que volver a ejecutarlo no duplique datos.

**Rationale:** Permite re-seed en desarrollo sin corrupto datos.

**Alternatives:** Seed que falla si ya existen datos (menos flexible en dev).

### 7. Alembic migración 001
**Decision:** Migración autogenerada desde los modelos, revisada manualmente. `upgrade()` crea tablas e índices; `downgrade()` los elimina en orden inverso.

**Rationale:** Estándar Alembic. Permite rollback limpio.

**Alternatives:** Migración SQL a mano (más propensa a errores).

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| Alembic autogenerate ignora cambios | Revisar migración generada antes de commitear; probar `alembic upgrade head` y `downgrade` |
| `clinic_id` olvidado en alguna tabla | Test que filtra todas las tablas de negocio tienen clinic_id; revisión de PR |
| Seed no idempotente | Probar ejecutar seed dos veces; verificar no duplicados |
| Email único global en lugar de por clínica | Constraint named `uq_users_clinic_id_email`; test de email repetido en diferente clinic_id debe permitir |

## Migration Plan

1. Crear `app/domain/clinica/models.py` (Clinic, Sillon).
2. Crear `app/domain/personas/models.py` (User, Paciente, Bloqueo).
3. Crear `app/domain/clinica/repository.py` y `app/domain/personas/repository.py` (BaseRepository).
4. Crear `app/domain/uow.py` (UnitOfWork).
5. Crear `app/domain/__init__.py` exports.
6. Generar migración 001 con `alembic revision --autogenerate`.
7. Revisar migración 001; aplicar `alembic upgrade head`.
8. Crear script de seed idempotente.
9. Escribir tests (constraints, clinic_id, seed idempotente).
10. Ejecutar `pytest` completo; verificar verde.

**Rollback:** `alembic downgrade -1` elimina las tablas de C-02; no hay datos de producción aún.

## Open Questions

- Valores iniciales de `sena_pct` por práctica (P-Alta-02 pendiente) — valores provisorios en C-04.
- Tabla de horarios de atención — definir en C-04/C-05.
