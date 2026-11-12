# Proposal

## Why

C-05 deja el turno creado en `pendiente_sena` pero el paciente no tiene forma de gestionarlo: si le surge un imprevisto solo puede escribir por WhatsApp, que es exactamente el canal que el producto viene a reemplazar. Sin cancelación y reprogramación con token, un turno cancelado sigue bloqueando el sillón (pierde plata la clínica) y el paciente que avisa con tiempo no tiene incentivo para hacerlo. Además, la cara pública del producto (buscar horario, reservar, gestionar) no existe: `HomePage` y `BookingPage` son stubs del scaffold, y `ManageAppointmentPage` solo muestra un input sin lógica.

## What Changes

- `GET /api/public/gestion/{token}` — vista del turno por `manage_token`, con `Cache-Control: no-store` y sin exponer datos de otros pacientes.
- `POST /api/public/gestion/{token}/cancelar` — cancela con `manage_token`; libera el horario inmediatamente (RN-CANCEL-04); dentro de la ventana de 12hs devuelve 409 con la advertencia de pérdida de seña y solo ejecuta con `confirmar_perdida_sena=true` (RN-CANCEL-01/03).
- `POST /api/public/gestion/{token}/reprogramar` — mueve el turno dentro de la ventana; la 1.ª reprogramación migra la seña en el mismo turno (`reprogramaciones_count=1`, RN-CANCEL-02); la 2.ª exige seña nueva y libera el horario anterior (RN-CANCEL-03).
- Las tres rutas públicas se direccionan por `manage_token` y no por id de turno: el enlace que recibe el paciente (`/gestionar/:token`) solo lleva el token, y así el token queda como única credencial sin agregar un identificador enumerable (ver `design.md` D2, que ajusta la forma literal `{id}` de `CHANGES.md`).
- `POST /api/internal/turnos/{id}/cancelar` y `/reprogramar` — misma lógica de dominio para `recepcion|admin` con JWT, sin `manage_token`, con `motivo` obligatorio.
- Servicio de dominio compartido `cancelar_turno` / `reprogramar_turno` con validación única de ventana 12hs, estados mutables, solape y liberación de horario; traduce `IntegrityError` a 409 igual que C-05.
- Migración `006_gestion_turnos`: `turnos.sena_perdida` (evidencia durable de seña perdida, insumo de reembolsos y del panel) y `turnos.reprogramado_de_id` (cadena de trazabilidad cuando la 2.ª reprogramación crea un turno nuevo).
- Frontend `features/booking/`: `/` landing con buscador de slots, `/reservar` (slots + formulario nombre + teléfono E.164 AR + entrega al checkout de C-08), `/gestionar/:token` (ver/cancelar/reprogramar), mobile-first y con un cliente HTTP público sin interceptor de JWT.
- Limpieza de la capa pública: el endpoint de gestión responde **403** —nunca 401— para token inválido o vencido, y el frontend público usa un cliente sin el interceptor que redirige a `/login`.
- Tests de ventana, migración de seña, 2.ª reprogramación, token inválido, liberación del horario, RBAC interno, aislamiento por clínica y redacción del token en logs.

**Fuera de alcance**: preferencia y webhook de Mercado Pago (C-08), envío real de WhatsApp y cancelación del job T-24hs (C-10; C-06 deja el punto de extensión), panel del día y marcado de `ausente` (C-07), bloqueo automático por faltas (C-07), opción de reprogramación a un odontólogo distinto elegido por el paciente.

## Capabilities

### New Capabilities

- `gestion-turnos`: ventana de 12hs, cancelación, reprogramación con y sin migración de seña, gestión pública por `manage_token`, gestión interna por JWT con motivo auditado, y liberación inmediata del horario.
- `booking-publico`: experiencia pública mobile-first de búsqueda de horarios, reserva con teléfono E.164 y entrega al checkout, y pantalla de gestión por token, incluyendo el manejo explícito de token inválido y de seña no reembolsable.

### Modified Capabilities

- Ninguna. `motor-turnos` (C-05) todavía no está en `openspec/specs/`: vive como delta dentro de `openspec/changes/c-05-motor-reservas-slots-turnos/`. C-06 agrega columnas a `turnos` y consume su API sin cambiar requisitos ya sincronizados. Cuando C-05 se archive, la próxima evolución del motor sí deberá declarar `motor-turnos` como modificada.

## Impact

- **Backend**: nuevo `app/domain/turnos/gestion.py` (reglas de ventana y transiciones) y ampliación de `app/domain/turnos/service.py`; routers `app/api/public/gestion.py` y `app/api/internal/turnos.py`; ampliación de `app/core/rate_limit.py` a un limitador parametrizable (login conserva 5/60s).
- **Base de datos**: migración `006_gestion_turnos` que agrega `sena_perdida BOOLEAN NOT NULL DEFAULT FALSE` y `reprogramado_de_id UUID NULL` (FK a `turnos.id`, `ON DELETE SET NULL`). Sin tablas nuevas.
- **APIs**: `GET /api/public/gestion/{token}`, `POST /api/public/gestion/{token}/cancelar`, `POST /api/public/gestion/{token}/reprogramar`, `POST /api/internal/turnos/{id}/cancelar`, `POST /api/internal/turnos/{id}/reprogramar`.
- **Frontend**: `frontend/src/features/booking/` (api, types, componentes), reemplazo de `HomePage`, `BookingPage` y `ManageAppointmentPage`, cliente `shared/api-client/public-client.ts` y navegación de `/gestionar/:token`.
- **Dependencias**: requiere C-05 implementado (modelo `Turno`, `manage_token`, `generar_slots`, estados y anti-solape) y C-04 (`precio_efectivo`, `sena_pct`). No agrega paquetes externos.
- **Riesgos heredados de C-05 que conviene resolver antes de aplicar C-06**: el proposal de C-05 pide `dni` opcional en la reserva pública mientras `Paciente.dni` es `nullable=False`; y el `EXCLUDE` de C-05 incluye `reprogramado` como estado vigente, decisión que C-06 evita usar (ver `design.md` D3).
