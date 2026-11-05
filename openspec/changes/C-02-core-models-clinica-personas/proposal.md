# Proposal — C-02 core-models-clinica-personas

## Why

C-02 es el segundo change en el camino crítico (`C-01 → C-02 → C-03 → ...`). Depende solo de C-01 (foundation-setup, ya completada). Establece los modelos base de dominio (Clinic, User, Paciente, Sillon, Bloqueo), el patrón `AuditMixin`, `BaseRepository[T]` + `UnitOfWork`, la columna `clinic_id` obligatoria en todas las tablas de negocio (DD-06), la migración 001 y un seed mínimo idempotente. Sin C-02 no hay modelo de datos sobre el cual construir C-03 (auth), C-04 (catálogo), C-05 (motor de turnos) y el resto.

## What Changes

### Backend — modelos y migraciones
- **Modelos:** `Clinic`, `User` (rol recepcion|odonto|admin), `Paciente`, `Sillon`, `Bloqueo` (estructura; lógica de bloqueo en C-07).
- **Patrones:** `AuditMixin` (`is_active`, `created_at`, `updated_at`); `BaseRepository[T]` + `UnitOfWork`; `clinic_id` FK obligatorio en todas las tablas de negocio.
- **Migración 001:** tablas `clinic`, `users` (email UNIQUE por clínica), `pacientes` (índices `(clinic_id,telefono)`, `(clinic_id,dni)`), `sillones`, `bloqueos`.
- **Seed mínimo:** 1 `Clinic` (timezone AR, `wa_sender` Twilio, cuenta MP), 1 admin + 1 recepción + 1 odontólogo, 2-3 `Sillon` activos. Seed idempotente.

### Backend — tests
- Constraints UNIQUE (email por clínica). sena_pct rango 0-100 es regla de TipoPractica (C-04), no entra en C-02.
- Filtros `clinic_id` omnipresentes en queries.
- Seed idempotente (volver a ejecutar no duplica datos).

### Frontend
- Ninguno en C-02 (frontend shell ya existe de C-01; pantallas de modelo se añaden en C-04+).

## Capabilities

### New Capabilities
- `domain/clinic`: entidad clínica con timezone AR, wa_sender, mp_account, activa.
- `domain/user`: usuario interno con rol, email único por clínica, password_hash, activo.
- `domain/paciente`: paciente con teléfono E.164 AR, DNI nullable, faltas_count, bloqueado_hasta.
- `domain/sillon`: sillón con nombre, activo.
- `domain/bloqueo`: bloqueo de paciente (motivo, desde, hasta +30d, created_by).
- `infrastructure/db`: SQLAlchemy 2.0 async Base, AsyncEngine, AsyncSession, get_db; Alembic migración 001.

### Modified Capabilities
- `core/config`: sin cambios (ya tiene las 12 vars de C-01).
- `infrastructure/db/base`: se añaden los modelos declarativos y el patrón de sesión.

## Impact

- **Code:** Nueva capa `app/domain/clinica/` y `app/domain/personas/` con modelos SQLAlchemy, repositorios y UnitOfWork. Migración 001 en `app/infrastructure/db/migrations/`.
- **APIs:** Ningún endpoint nuevo (endpoints llegan en C-03+). Solo modelos internos.
- **Dependencies:** SQLAlchemy 2.0, Alembic, psycopg/asyncpg (ya en C-01).
- **Systems:** PostgreSQL 16 via Docker Compose (ya en C-01).
- **Configuration:** `clinic_id` como columna obligatoria en todas las tablas de negocio (DD-06).

## Dependencies

- C-01 `foundation-setup` (completada y archivada).

## Leer antes

- `knowledge-base/04_modelo_de_datos.md` §Clinic, §User, §Paciente, §Sillon, §Bloqueo
- `knowledge-base/08_arquitectura_propuesta.md` §Patrones aplicados, §Estructura de directorios
- `knowledge-base/09_decisiones_y_supuestos.md` §DD-02, §DD-06
- `knowledge-base/03_actores_y_roles.md` §Actores del sistema
- `docs/skills-mcp/revision-reglas-turnos.md` (reporte de la skill propia `reglas-turnos-review` sobre C-02)

## Open Questions

- Valores iniciales de `sena_pct` por práctica en el seed (pregunta P-Alta-02 en `10_preguntas_abiertas.md`) — definir como valores provisorios documentados en C-04.
- Tabla de horarios de atención por sillón/odontólogo — definir en diseño (ver `10_preguntas_abiertas.md`); no entra en C-02.
