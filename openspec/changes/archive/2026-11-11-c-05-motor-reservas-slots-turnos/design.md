# Design

## Context

Ver `proposal.md`. El backend ya tiene `TipoPractica`, `Sillon`, `Paciente`, `Bloqueo`, `User`, `get_session()` y `precio_efectivo()` de C-04. No existe modelo de turnos ni horarios, y el worker actual es un stub con heartbeat. La base de desarrollo es PostgreSQL 16+; los tests corren en SQLite salvo los marcados para Postgres.

Restricciones relevantes:
- Toda evaluación de horarios y solapes se hace en `America/Argentina/Buenos_Aires` (`TZ_CLINICA`).
- `clinic_id` obligatorio en todas las tablas de negocio (DD-06).
- `monto_sena` es una foto al crear el turno (RN-PAGO-02).
- TTL de `pendiente_sena`: 30 minutos (`MP_TTL_MIN`).

## Goals / Non-Goals

**Goals:**
- Modelar `Turno` y `HorarioAtencion` con integridad de solape garantizada por la base.
- Generar slots determinísticos y testeables sin depender de la base para la lógica pura.
- Permitir reserva pública sin login e interna con RBAC reutilizando el mismo servicio.
- Liberar slots vencidos de forma confiable aunque Redis no esté disponible.

**Non-Goals:**
- Cobro, preferencia MP, webhook y confirmación de pago (C-08).
- Cancelación y reprogramación con token (C-06).
- Notificaciones WhatsApp y recordatorios (C-10).
- Panel del día y marcado de `ausente`/`completado` (C-07).
- Rate limiting específico del endpoint público (se reutiliza la infraestructura existente más adelante).

## Decisions

### D1 — Modelo `Turno`

Tabla `turnos` con `id`, `clinic_id`, `paciente_id`, `sillon_id`, `odontologo_id` (FK a `users`), `tipo_practica_id`, `inicio` y `fin` (`timestamptz`), `estado` (`String(32)` + CHECK), `manage_token` (`String(64)`, UNIQUE parcial, nullable), `reprogramaciones_count` (`Integer`, default 0), `monto_sena` (`Numeric(12,2)`), `expira_at` (`timestamptz`, nullable) y campos de `AuditMixin`.

- `estado` usa `String` + CHECK, consistente con `users.rol`, en lugar de un `Enum` nativo que complica migraciones.
- `expira_at` se agrega al modelo aunque la KB no lo liste: hace la expiración determinística y consultable. `NULL` para turnos ya confirmados.
- Índices: `(clinic_id, inicio)`, `(sillon_id, inicio)`, `(odontologo_id, inicio)`, `(paciente_id, inicio)`, `(estado)` y `(estado, expira_at)` para el barrido.
- CHECKs: `fin > inicio`, `monto_sena >= 0`, `estado IN (...)`.

**Alternativas descartadas**: estado como `Enum` nativo (migrar valores en v1.1 es más caro); guardar solo fecha sin hora (rompe multi-sillón).

### D2 — `HorarioAtencion`

Tabla `horarios_atencion` con `clinic_id`, `dia_semana` (`SmallInteger`, 0=lunes … 6=domingo), `hora_desde`, `hora_hasta` (`Time`), `activo` y `AuditMixin`.

- UNIQUE `(clinic_id, dia_semana, hora_desde)` para que el seed sea idempotente.
- CHECK `hora_hasta > hora_desde`.
- Permite varias franjas por día (mañana/tarde) sin cambiar el modelo.

**Alternativas descartadas**: configuración fija en `settings` (requiere deploy para cambiar horarios); hardcode en el servicio (no auditable ni editable).

### D3 — Anti-solape en PostgreSQL con `EXCLUDE`

La migración 005 ejecuta `CREATE EXTENSION IF NOT EXISTS btree_gist` y agrega dos constraints de exclusión:

```sql
ALTER TABLE turnos ADD CONSTRAINT ex_turnos_sillon_solape
EXCLUDE USING gist (sillon_id WITH =, tstzrange(inicio, fin, '[)') WITH &&)
WHERE (estado IN ('pendiente_sena', 'confirmado', 'reprogramado'));

ALTER TABLE turnos ADD CONSTRAINT ex_turnos_odontologo_solape
EXCLUDE USING gist (odontologo_id WITH =, tstzrange(inicio, fin, '[)') WITH &&)
WHERE (estado IN ('pendiente_sena', 'confirmado', 'reprogramado'));
```

- El servicio hace además una consulta de solape antes de insertar para devolver un 409 amigable; el `EXCLUDE` es la garantía ante concurrencia.
- Se captura `IntegrityError` y se traduce a 409.
- SQLite no soporta `EXCLUDE`: los tests unitarios validan la lógica del servicio y los tests de migración se marcan `skipif` para Postgres, igual que `test_migration_002/004`.

**Alternativas descartadas**: UNIQUE + validación transaccional sola (vulnerable a dos requests concurrentes que validan antes de insertar).

### D4 — Generación de slots

`app/domain/turnos/slots.py` expone una función pura:

```text
generar_slots(fecha, duracion_min, horarios, turnos_vigentes, sillones, odontologos) -> list[Slot]
```

- Convierte la fecha local a un rango UTC usando `ZoneInfo(settings.tz_clinica)`.
- Recorre cada franja del día en pasos de `duracion_min`; el último slot debe terminar antes o en `hora_hasta`.
- Descarta slots que intersectan turnos vigentes (`pendiente_sena|confirmado|reprogramado`).
- Para cada inicio libre, busca el primer par (sillón activo, odontólogo activo) cuyos rangos no estén ocupados. El primero libre gana.
- Devuelve `{inicio, fin, sillon_id, odontologo_id}`; nunca datos del paciente.

`GET /api/public/slots` resuelve la clínica desde `practica_id` (valida que la práctica exista y esté activa), carga horarios, turnos del día y recursos, y llama a la función pura.

**Alternativas descartadas**: generar slots en SQL (difícil de testear y de mantener); devolver solo horas sin recursos (obliga a una segunda llamada y permite reservar un recurso ya tomado).

### D5 — Reserva pública

`POST /api/public/reservas` recibe `nombre`, `telefono`, `dni` opcional, `practica_id` e `inicio`.

Flujo transaccional:
1. Resolver práctica y clínica; validar que `inicio` esté alineado a un slot generado.
2. `get_or_create` del paciente por `(clinic_id, telefono)`. La migración agrega UNIQUE `(clinic_id, telefono)`; si hay carrera, se captura `IntegrityError` y se re-selecciona.
3. Rechazar 403 si `bloqueado_hasta > now`.
4. Calcular `monto_sena = round(precio_efectivo(...) * tipo.sena_pct / 100)`.
5. Insertar `Turno(pendiente_sena, manage_token=secrets.token_urlsafe(32), expira_at=now()+MP_TTL_MIN)`.
6. Devolver 201 con `turno_id`, `manage_token`, `inicio`, `fin`, `monto_sena` y `estado`.

`inicio` sin offset se interpreta en la timezone de la clínica; con offset se respeta y se valida que caiga en un slot.

**Alternativas descartadas**: aceptar `sillon_id`/`odontologo_id` del cliente (permite forzar recursos y complica la validación); crear el paciente solo cuando paga (rompe la foto de la seña y el bloqueo por faltas).

### D6 — Reserva interna

`POST /api/internal/turnos` recibe `paciente_id`, `sillon_id`, `odontologo_id`, `tipo_practica_id` e `inicio`. Requiere rol `recepcion|admin` y `clinic_id` del JWT.

- Reutiliza el mismo servicio de creación y anti-solape.
- No emite `manage_token` (`NULL`).
- `paciente_id`, `sillon_id` y `odontologo_id` deben pertenecer a la clínica del token; si no, 404.

**Alternativa descartada**: que el endpoint interno también cree el paciente (C-07 lo resolverá con su propia pantalla); en C-05 el paciente debe existir.

### D7 — Expiración DB-first

El worker pasa a ejecutar cada 30 segundos:

```sql
UPDATE turnos SET estado = 'cancelado'
WHERE estado = 'pendiente_sena' AND expira_at <= now();
```

Además, el servicio llama al mismo barrido de forma perezosa antes de generar slots y antes de crear una reserva, para liberar horarios sin esperar el tick.

- La base es la fuente de verdad: si Redis cae, los slots igual se liberan.
- `worker.py` deja de ser un stub; el barrido se omite de cobertura como el resto del worker.
- Redis queda disponible para acelerar en el futuro, pero no se usa como scheduler en C-05.

**Alternativas descartadas**: sorted set de Redis como scheduler primario (si se pierde el job o Redis está caído, el slot queda bloqueado para siempre); `DELETE` del turno (pierde trazabilidad y la foto de la seña).

### D8 — Estructura de código

- `app/domain/turnos/models.py`: `Turno`, `HorarioAtencion`.
- `app/domain/turnos/schemas.py`: `SlotOut`, `SlotsResponse`, `ReservaPublicaIn`, `ReservaOut`, `TurnoInternoIn`.
- `app/domain/turnos/slots.py`: generación pura y timezone.
- `app/domain/turnos/service.py`: `crear_turno_publico`, `crear_turno_interno`, `expirar_pendientes`.
- `app/domain/turnos/repository.py`: `TurnoRepository`, `HorarioAtencionRepository`.
- `app/api/public/reservas.py`: `GET /slots` y `POST /reservas`.
- `app/api/internal/turnos.py`: `POST /turnos`.
- `app/api/public/__init__.py` y `app/main.py`: montaje de routers.
- `app/domain/personas/repository.py`: `PacienteRepository.get_or_create_by_telefono`.

## Risks / Trade-offs

- **`EXCLUDE` solo en Postgres** → la suite común no lo ejercita; se agregan tests `skipif` de migración y tests de servicio para el 409.
- **UNIQUE `(clinic_id, telefono)` puede fallar con datos duplicados preexistentes** → la base v1 está vacía de pacientes; la migración documenta la precondición.
- **Barrido cada 30 s deja una ventana corta de slot bloqueado** → el barrido perezoso en slots/reservas la reduce a la duración de un request.
- **DST en `America/Argentina/Buenos_Aires`** → se usa `ZoneInfo` y rangos UTC; Argentina no aplica DST actualmente, pero el cálculo no asume offset fijo.
- **Abuso del endpoint público** → fuera de alcance de C-05; se deja preparado para rate limiting en una iteración posterior.
- **`manage_token` en logs** → no se loguea el token; solo el `turno_id`.

## Migration Plan

1. `alembic upgrade head` aplica 005: extensión `btree_gist`, tablas `turnos` y `horarios_atencion`, índices y constraints.
2. El seed agrega las franjas L-V 08:00-20:00 y Sábado 08:00-13:00 de forma idempotente.
3. Rollback: `alembic downgrade 004` elimina ambas tablas (pérdida de turnos aceptada pre-MVP); la extensión se conserva.
4. No hay migración de datos: no existen turnos previos.

## Open Questions

- Ninguna que bloquee el diseño. Quedan para iteraciones posteriores: aceleración con Redis, rate limiting del canal público y excepciones de bloqueo auditadas (C-07).
