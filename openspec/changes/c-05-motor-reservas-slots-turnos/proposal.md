# Proposal

## Why

El MVP necesita que un paciente pueda reservar 24/7 sin login y que la clínica no venda dos veces el mismo horario. Hoy existen catálogo y auth, pero no hay modelo de turnos, generación de slots ni reserva: sin este motor no se puede cobrar la seña (C-08) ni operar la agenda (C-07).

## What Changes

- Nuevo modelo `Turno` con estados `pendiente_sena|confirmado|cancelado|reprogramado|completado|ausente`, `manage_token` público único y `monto_sena` fotografiado al crear la reserva.
- Nuevo modelo `HorarioAtencion` por clínica (día de semana, hora desde/hasta) para calcular slots.
- Migración `005` con tabla `turnos`, tabla `horarios_atencion`, índices y constraints anti-solape a nivel DB (`EXCLUDE` por `sillon_id` y por `odontologo_id`).
- `GET /api/public/slots?fecha=&practica=` — huecos por `duracion_min`, en timezone de la clínica, sin datos de otros pacientes.
- `POST /api/public/reservas` — reserva sin login: busca/crea paciente por teléfono, valida bloqueo 30 días, crea `Turno(pendiente_sena)` con `manage_token` y `monto_sena`, y encola la expiración.
- `POST /api/internal/turnos` — creación interna (mostrador/teléfono) con el mismo motor y RBAC `recepcion|admin`, sin `manage_token`.
- Expiración de `pendiente_sena` a los 30 minutos (`MP_TTL_MIN`): libera el slot y pasa el turno a `cancelado`.
- Asignación automática del primer sillón activo libre y de un odontólogo disponible; el paciente no elige odontólogo en v1.0.
- Seed de horarios: lunes a viernes 08:00-20:00 y sábado 08:00-13:00.
- Tests de anti-solape, TTL, bloqueo, `manage_token`, foto de `monto_sena` y de la tarea 6.5 diferida de C-04.

**Fuera de alcance**: cancelar/reprogramar con token (C-06), preferencia y webhook de Mercado Pago (C-08), notificaciones WhatsApp (C-10) y panel del día (C-07). C-05 deja el turno en `pendiente_sena`; no cobra ni confirma pagos.

## Capabilities

### New Capabilities

- `motor-turnos`: generación de slots por horario de atención, creación de turnos públicos e internos, anti-solape por sillón y odontólogo, foto de la seña y expiración de reservas sin pago.

### Modified Capabilities

- Ninguna. `catalogo-practicas`, `clinica-personas` y `auth-rbac` se consumen sin cambiar sus requisitos.

## Impact

- **Backend**: nuevo dominio `app/domain/turnos` (modelos, schemas, servicio y repositorio), routers `app/api/public` y `app/api/internal`, worker de expiración, migración `005` y seed.
- **Base de datos**: nuevas tablas `turnos` y `horarios_atencion`; requiere la extensión `btree_gist` para los constraints `EXCLUDE`.
- **APIs**: `GET /api/public/slots`, `POST /api/public/reservas`, `POST /api/internal/turnos`.
- **Dependencias**: usa `TipoPractica`, `Sillon`, `Paciente`, `Bloqueo`, `User` y el catálogo de C-04; no agrega paquetes externos.
- **Configuración**: reutiliza `MP_TTL_MIN=30`, `TZ_CLINICA` y `DATABASE_URL`.
