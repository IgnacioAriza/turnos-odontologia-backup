# Design

## Context

Ver `proposal.md` para el porqué. Estado real verificado del repo, no del roadmap:

- **C-05 no está implementado**: `openspec/changes/c-05-motor-reservas-slots-turnos/` tiene `proposal.md`, `design.md`, `tasks.md` (0 de 31 tareas) y `specs/motor-turnos/spec.md`, pero `backend/app/domain/turnos/` solo contiene `__init__.py`. No existen modelo `Turno`, `generar_slots`, endpoints públicos, `manage_token` ni migración `005`. Cualquier tarea de C-06 depende de que esas piezas existan.
- Lo que sí está implementado y se consume: `Clinic`, `User`, `Paciente`, `Bloqueo`, `TipoPractica`, `Arancel`, `AuditoriaSena`, `precio_efectivo()`, `get_session()`, JWT con `require_role`, `AuditMixin` y `app/core/rate_limit.py` (limitador específico de login, 5/60s, con fallback a memoria).
- Frontend: `router.tsx` ya declara `/`, `/reservar` y `/gestionar/:token`; `HomePage`, `BookingPage` y `ManageAppointmentPage` son stubs del scaffold sin lógica. Existe `shared/api-client/api-client.ts` con un interceptor que ante **401** borra el token y redirige a `/login`.
- La base es PostgreSQL 16+ en desarrollo; la suite corre en SQLite salvo los tests `skipif` de migración.

Restricciones que mandan sobre el diseño:

- Toda comparación de ventana, horario y solape se evalúa en `America/Argentina/Buenos_Aires` (RN-CANCEL y excepciones globales de `05_reglas_de_negocio.md`).
- `manage_token` es la única credencial del canal público (RN-RES-03); no hay login de paciente en v1.0 (IN-01).
- La seña es una foto al crear el turno (RN-PAGO-02): una reprogramación que conserva la seña no puede recalcular `monto_sena`.
- `clinic_id` obligatorio en todo acceso a datos de negocio (DD-06).

## Goals / Non-Goals

**Goals:**

- Una sola implementación de las reglas de gestión (ventana, estados, seña, solape) compartida por el canal público y el interno.
- Que la pérdida de seña quede registrada de forma durable y consultable, sin depender de logs.
- Que el canal público no pueda confundirse con el autenticado: token inválido nunca produce 401.
- Que el frontend público exista, sea usable desde un teléfono y no herede el comportamiento de sesión del panel.

**Non-Goals:**

- Cobro real, preferencia y webhook de Mercado Pago (C-08). C-06 entrega la reserva al checkout pero no cobra.
- Envío de WhatsApp y ciclo de vida del job T-24hs (C-10). C-06 solo emite la señal.
- Marcado de `ausente`/`completado` y bloqueo automático por faltas (C-07).
- Reprogramar a un odontólogo específico elegido por el paciente (v1.0 asigna recursos como C-05).
- Login de paciente y historial (v1.1).

## Decisions

### D1 — Dos superficies de API, un solo servicio de dominio

`app/domain/turnos/service.py` expone `cancelar_turno` y `reprogramar_turno`; las consumen dos routers distintos:

- `app/api/public/gestion.py`: autenticado por `manage_token`, sin JWT.
- `app/api/internal/turnos.py`: autenticado por JWT `recepcion|admin`, con `motivo` obligatorio.

**Por qué**: es el mismo dominio pero con dos modelos de confianza incompatibles. Un endpoint único con "token o JWT" obliga a que la ruta pública acepte un `Authorization` header y abre la puerta a confusión de identidad (un JWT de recepción de otra clínica presentado en una ruta pública). Separar los routers mantiene el RBAC server-side y el aislamiento por `clinic_id` explícitos, y coincide con la estructura ya existente (`api/public`, `api/internal`, `api/webhooks`).

**Alternativas descartadas**: endpoint único con auth dual (peor superficie, peor auditoría); lógica duplicada en cada router (dos fuentes de verdad para la ventana de 12hs).

### D2 — Las rutas públicas se direccionan por token, no por id

```text
GET  /api/public/gestion/{token}
POST /api/public/gestion/{token}/cancelar
POST /api/public/gestion/{token}/reprogramar
```

**Por qué**: el paciente recibe un único enlace, `/gestionar/:token`, y no conoce ningún `turno_id`. Direccionar por token deja una sola credencial en el request, evita un id enumerable en la URL y ahorra el viaje ida-y-vuelta que exigiría "resolver el id a partir del token para después llamar a `/reservas/{id}/...`". También hace que un token robado no habilite a navegar ids ajenos.

**Desvío respecto del roadmap**: `CHANGES.md` C-06 describe literalmente `POST /api/public/reservas/{id}/cancelar` y `/reprogramar`. Se ajusta a `{token}` por lo anterior y se actualiza `CHANGES.md` como tarea del change. La capacidad observable no cambia: mismas acciones, mismo actor, mismas reglas.

**Alternativas descartadas**: mantener `{id}` y resolverlo con un `GET` previo (dos identificadores, más superficie); token por query string (queda en logs de proxy e historial).

### D3 — La primera reprogramación muta el turno en el lugar; la segunda crea uno nuevo

| Caso | Turno original | Turno nuevo |
|---|---|---|
| 1.ª reprogramación (dentro de ventana, `reprogramaciones_count=0`) | mismo registro, nuevo `inicio`/`fin`/recursos, `reprogramaciones_count=1`, `monto_sena` intacto, `manage_token` intacto | — |
| 2.ª reprogramación confirmada | `cancelado` + `sena_perdida=true` | `pendiente_sena`, `reprogramado_de_id` → original, `reprogramaciones_count=1`, `monto_sena` recalculado, `manage_token` propio, `expira_at` nuevo |
| Cancelación dentro de ventana | `cancelado` | — |
| Cancelación tardía confirmada | `cancelado` + `sena_perdida=true` | — |

**Por qué mutar en el lugar en la primera**: la seña "viaja" sola. El `Pago` que cree C-08 apunta a un `turno_id`; si la reprogramación creara un turno nuevo habría que repuntar el pago o duplicarlo, y RN-PAGO-04 exige un solo pago aprobado vigente por turno. Mutando, `monto_sena` se conserva por construcción (RN-PAGO-02) y no hace falta tocar la tabla de pagos.

**Por qué crear un turno nuevo en la segunda**: la seña anterior está perdida y la nueva hay que cobrarla. Un `pendiente_sena` nuevo activa el mismo TTL y el mismo flujo de expiración de C-05 sin inventar un estado intermedio. El turno anterior queda enlazado por `reprogramado_de_id`.

**Por qué el turno anterior termina en `cancelado` y no en `reprogramado`**: el `EXCLUDE` de C-05 declara `reprogramado` como estado **vigente** (junto con `pendiente_sena` y `confirmado`). Si el turno anterior se dejara en `reprogramado` conservando su rango viejo, ese rango quedaría bloqueado para siempre: el horario liberado nunca podría re-reservarse, violando RN-CANCEL-04. `cancelado` + `sena_perdida=true` dice la verdad del caso (se liberó el horario y se perdió la seña) y la cadena queda en `reprogramado_de_id`. Consecuencia: el estado `reprogramado` que define C-05 no lo usa v1.0; queda reservado y anotado como pregunta abierta para C-05.

**Alternativas descartadas**: crear un turno nuevo en cada reprogramación (rompe la migración de seña y duplica pagos); dejar el anterior en `reprogramado` (bloquea el horario liberado, ver arriba).

### D4 — Contrato de errores del canal público

| Situación | HTTP | `codigo` |
|---|---|---|
| Token inválido o que no corresponde al turno | **403** | `token_invalido` |
| Turno inexistente | 404 | `turno_no_encontrado` |
| Estado final (`cancelado`, `completado`, `ausente`) | 409 | `estado_no_gestionable` |
| Ventana < 12hs sin confirmar | 409 | `requiere_confirmacion` (+ `perdida_sena: true`) |
| 2.ª reprogramación sin confirmar | 409 | `requiere_nueva_sena` |
| Horario nuevo ocupado | 409 | `solape` |
| Horario nuevo no alineado / fuera de franja | 422 | `slot_invalido` |
| Rate limit | 429 | `rate_limited` (+ `Retry-After`) |

**Por qué 403 y nunca 401**: el `api-client` del frontend tiene un interceptor que ante 401 borra el token y manda a `/login`. Un 401 en el canal público expulsaría al paciente a una pantalla de login que no existe para él. El 403 es además el código correcto: hay credencial, es inválida.

**Por qué `codigo` estable además del mensaje**: el frontend decide qué diálogo mostrar (advertencia de seña, refresco de slots) sin parsear texto libre, y los tests verifican comportamiento sin acoplarse a la redacción.

### D5 — Transporte y trato del `manage_token`

- En `GET` viaja en el path (el enlace lo impone); en los `POST`, en el cuerpo como `manage_token`. **Nunca** en query string.
- Comparación con `secrets.compare_digest`, nunca `==`, para no filtrar información por tiempo.
- La vista pública responde `Cache-Control: no-store` y `Referrer-Policy: no-referrer`; el token no se devuelve en el cuerpo.
- El token no se loguea: el logger estructurado registra `turno_id`, `clinic_id` y `accion`, y un test verifica que el token no aparece en el output de log del request.
- El token no se invalida al cancelar: sigue sirviendo para consultar el turno en estado `cancelado` (el paciente tiene derecho a ver lo que pasó). Las mutaciones se rechazan por estado, no por token.

**Alternativa descartada**: invalidar el token al cancelar (el paciente pierde la única forma de leer su propio turno, y el panel de C-07 no necesita esta restricción).

### D6 — `sena_perdida` y `reprogramado_de_id` como columnas, no como tabla de eventos

Migración `006_gestion_turnos`:

```sql
ALTER TABLE turnos ADD COLUMN sena_perdida BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE turnos ADD COLUMN reprogramado_de_id UUID NULL
  REFERENCES turnos(id) ON DELETE SET NULL;
```

**Por qué columnas**: lo que el sistema necesita responder es binario y frecuente — "¿esta seña es reembolsable?" y "¿de qué turno viene este?" — y ambas respuestas se consultan en el panel y en el flujo de reembolsos. Una tabla de eventos obliga a un agregado por fila para responder lo mismo. `sena_perdida` es evidencia durable de una decisión con impacto en dinero, no un log.

**Alternativa descartada**: tabla `eventos_turno` (auditoría completa). Se descarta por proporción: RN-AUS-02 exige auditoría de excepciones de bloqueo recién en C-07, y ese es el momento de introducir un registro de eventos si hace falta. Hoy los eventos de dominio van al logger con `turno_id`, `clinic_id`, `usuario_id` y `motivo`.

### D7 — La señal de notificación es un puerto con implementación no-op

`app/domain/notificaciones/` expone un puerto `RecordatorioPort` con `cancelar(turno_id)` y `reprogramar(turno_id, inicio)`; en v1.0 hay un `NoOpRecordatorio` que solo registra la llamada. C-10 reemplaza la implementación por el job real de Redis/Twilio sin tocar el dominio de turnos.

**Por qué**: RN-NOTIF-03 exige cancelar el recordatorio de un turno muerto, pero el mecanismo todavía no existe. Un puerto mantiene la regla visible en el código y testeable (`test` verifica que se llamó), y evita que C-06 tenga que hacer `if redis is not None` disperso por el servicio.

**Alternativa descartada**: postergar la señal a C-10 (el servicio de gestión tendría que modificarse después, y la regla quedaría sin trazabilidad en este change).

### D8 — Rate limiting parametrizable reutilizando el limitador existente

Se generaliza `app/core/rate_limit.py` a `check_rate_limit(scope, key, limit, window)` manteniendo el comportamiento actual de login (`login`, `ip+email`, 5/60s) y agregando `gestion_ip` (30/60s) y `gestion_token` (10/60s). El fallback en memoria para tests se conserva.

**Por qué**: adivinar un `token_urlsafe(32)` es inviable criptográficamente, pero sin límite un atacante puede quemar CPU y ensuciar métricas; además la KB ya exige rate limiting en el canal público como deuda. Parametrizar evita un segundo limitador paralelo con su propia copia de la lógica de Redis.

**Alternativa descartada**: un módulo nuevo solo para gestión pública (duplica pipeline Redis, expiración y fallback).

### D9 — Frontend: `features/booking/` sobre las rutas ya existentes

- Se conservan las rutas ya declaradas en `router.tsx` (`/`, `/reservar`, `/gestionar/:token`) y se reemplaza el contenido de los stubs.
- `features/booking/api.ts` (llamadas), `features/booking/types.ts` (contratos), `features/booking/components/` (`SlotList`, `ReservaForm`, `GestionTurno`, `ConfirmDialog`).
- `shared/api-client/public-client.ts`: instancia Axios **sin** el interceptor de 401, con `baseURL` de `VITE_API_URL`. El canal público no manda `Authorization` aunque haya un token en `localStorage` (un recepcionista logueado en la misma máquina no debe reservar como paciente).
- Normalización de teléfono en un módulo puro `normalizarTelefonoAR(input): string | null` (`+54` + 9 + área + número, 10 dígitos nacionales) para poder testearla sin render.
- Confirmación de pérdida de seña con un `ConfirmDialog` accesible (foco atrapado, `Escape` cierra, retorno de foco), disparado por el `codigo` de la respuesta y no por el texto.

**Por qué reusar las rutas**: ya están en el router y en `CHANGES.md`; renombrarlas obliga a tocar enlaces y `ManageAppointmentPage`. Reemplazar el contenido es suficiente.

### D10 — Defecto preexistente del guard público

`router.tsx` envuelve `/` en `PublicRoute`, que redirige a `/` cuando hay usuario: un usuario autenticado entra en un ciclo de redirecciones. C-06 reescribe el contenido de `/`, así que se corrige el destino del guard en este change (a la raíz del panel del rol) y se agrega un test de regresión.

**Por qué acá**: el defecto se manifiesta justo en la pantalla que C-06 posee; dejarlo documentado sin arreglarlo haría que la landing pública nueva herede un bug visible.

## Risks / Trade-offs

- **C-05 no implementado bloquea todo** → la primera tarea es una verificación de contrato que falla ruidosamente si `Turno`, `manage_token`, `generar_slots` o la migración `005` no existen. No se implementa C-06 sobre un motor inventado.
- **Mutar el turno en la primera reprogramación no deja historia del horario anterior** → se acepta: `reprogramaciones_count` acota el caso a una vez y la cadena completa solo importa en la segunda, que sí crea registro enlazado.
- **`estado='reprogramado'` queda sin uso en v1.0** → documentado como pregunta abierta para C-05; no rompe el `EXCLUDE` porque nunca se deja un turno vivo en ese estado.
- **El token viaja en el path del `GET`** → mitigado con `no-store`, `no-referrer`, ausencia de logs del token y rate limit; no hay alternativa sin cambiar la forma del enlace.
- **`sena_perdida=true` puede quedar desactualizado si C-08 aprueba un pago después** → C-08 debe rechazar el pago de un turno `cancelado`; se deja anotado como contrato para ese change.
- **La segunda reprogramación crea un turno nuevo sin cobrar** → el turno nace `pendiente_sena` con TTL, así que si no se cobra expira y libera el horario igual que cualquier reserva.
- **Zona horaria y horario de verano** → la ventana se calcula sobre instantes UTC con `ZoneInfo(settings.tz_clinica)`; Argentina no aplica DST hoy pero el cálculo no asume offset fijo.
- **Frontend sin `api-client` autenticado** → un cambio futuro en el interceptor no debe afectar al canal público; por eso son instancias separadas y no una opción del mismo cliente.

## Migration Plan

1. `alembic upgrade head` aplica `006_gestion_turnos` después de `005`: dos columnas y un FK. Sin backfill (`sena_perdida` default `false` es correcto para todo turno existente).
2. Rollback: `alembic downgrade 005` elimina ambas columnas. Pierde la evidencia de señas perdidas y la cadena de reprogramaciones; aceptable antes del go-live.
3. Despliegue sin orden especial entre backend y frontend: las rutas nuevas no reemplazan ninguna existente y el frontend tolera la ausencia del checkout de C-08.
4. No se modifica ni se reescribe la migración `005`.

## UI Mockups

- Design system revision: 1 — `design-system/README.md`, `Approval: approved (2026-11-10, by user)`.
- Decision: yes (política de proyecto `system-and-mockups` elegida por el usuario), 2026-11-10.
- Mockups: `openspec/changes/c-06-reserva-publica-cancel-reprog/mockups/`.
- Approval: approved (2026-11-11, by user).
- Preview: rendered (2026-11-11) — `mockups/previews/{home,reservar,gestionar}-{mobile-390,desktop-1440}.png`.
- Visual verify: passed (2026-11-11) — app construida servida con `vite preview` + API mock en `:8000`; `/`, `/reservar` y `/gestionar/:token` medidos a 390×844 y 1440×900. Sin scroll horizontal, sin controles táctiles < 44 px, 0 errores de consola y 0 enlaces a `/login` en el canal público. Diferencias corregidas: el header público mostraba "Iniciar sesión" (el mockup aprobado solo tiene "Inicio" y "Reservar turno") y el brand medía 26 px de alto. Ambas corregidas y cubiertas por `frontend/src/layouts/PublicLayout.test.tsx`.

**Alcance**: tres pantallas, con los estados que el change introduce.

| Pantalla | Ruta | Estados mockupeados |
|---|---|---|
| `home.html` | `/` | búsqueda inicial, horarios cargados con slot seleccionado, día sin horarios, error de API con reintento |
| `reservar.html` | `/reservar` | formulario vacío con resumen, teléfono inválido, envío en curso, 201 pendiente de seña, 201 con URL de pago, 409 por solape que conserva los datos |
| `gestionar.html` | `/gestionar/:token` | turno vigente, token inválido (403 sin derivar a `/login`), turno `cancelado`, diálogo de cancelación tardía (pierde seña), diálogo de 2.ª reprogramación (seña nueva), selector de nuevo horario |

Los mockups son HTML/CSS estático: importan `design-system/tokens.css` y
`design-system/brand.js`, usan `design-system/assets/logo.svg` y no hacen
peticiones de red. La copia de errores usa los `codigo` reales del backend, no
textos inventados.

## Open Questions

- ¿`motor-turnos` (C-05) debe dejar de considerar `reprogramado` como estado vigente en su `EXCLUDE`? Con el modelo de C-06 ese estado no se usa; si C-05 lo mantiene, queda inofensivo pero engañoso para quien lea la migración.
- ¿C-08 debe rechazar un pago sobre un turno `cancelado` con `sena_perdida=true`, o permitir el pago y convertir la seña perdida en seña vigente? Se resuelve en C-08; C-06 solo provee el dato.
- ¿El enlace de gestión debe reenviarse por WhatsApp desde la pantalla de gestión ("reenviar mi enlace")? No está en US-003 y C-06 no lo implementa; queda para C-10.
