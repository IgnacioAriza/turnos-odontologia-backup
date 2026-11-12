# Proposal — C-07 agenda-panel-dia

## Why

C-05 dejó el motor de reservas (slots, alta de turno, anti-solape) y C-06 la gestión pública por token, pero la clínica todavía no tiene dónde operar el día: recepción no puede ver la agenda multi-sillón ni el panel de llegadas, y el odontólogo no tiene una vista de su propio día. Sin C-07 no se puede marcar `completado`/`ausente`, no se aplica nunca el bloqueo por 2 faltas (DD-04, RN-AUS-01..03) y la regla de ausentismo queda escrita en la KB pero inerte en el producto. C-07 es el otro extremo indispensable del go-live v1.0 junto con C-10.

## What Changes

### Backend — agenda multi-sillón

- `GET /api/internal/agenda?vista=dia|semana&fecha=&sillon=&odontologo=&estado=`: turnos de la clínica del JWT en un rango día o semana (lunes a domingo de la semana de `fecha`), con filtros por sillón, odontólogo y estado. Orden estable por `inicio`, `sillon`, `odontologo`.
- La vista `odonto` queda confinada server-side a `odontologo_id = sub` del JWT: aunque envíe otro `odontologo` en el query, solo ve sus turnos. Recepción y admin ven toda la clínica.
- El alta de turno interno (`POST /api/internal/turnos`, ya existente) se reutiliza tal cual desde la agenda: el frontend no reimplementa reglas y un solape sigue devolviendo 409 con `codigo=solape`.
- Alta de turno interno con excepción de bloqueo: si el paciente está bloqueado y la request trae `motivo_excepcion`, recepción/admin puede crear el turno y la excepción queda auditada de forma durable. Sin motivo, la respuesta es 403 con `codigo=bloqueado` y `bloqueado_hasta`.

### Backend — panel del día y ausentismo

- `GET /api/internal/panel/dia?fecha=`: lista por hora con paciente, contacto WhatsApp, práctica, sillón, odontólogo, estado del turno y estado de seña, más un resumen de la jornada.
- `PATCH /api/internal/panel/turnos/{id}`: marca `completado` o `ausente`. Es idempotente para el mismo estado destino y rechaza transiciones desde estados finales distintos con `codigo=estado_no_actualizable`.
- La falta la marca una persona (recepción, admin u odontólogo sobre sus propios turnos), nunca el sistema (RN-AUS-03).
- 2.ª falta: se incrementa `Paciente.faltas_count`; al llegar a 2 se crea `Bloqueo(desde=now, hasta=now+30d, motivo="2_faltas", created_by=<usuario>)`, se actualiza `Paciente.bloqueado_hasta` y se reinicia el contador. Todo en la misma transacción que el `ausente`.
- El rechazo por bloqueo en el alta (público e interno) pasa a un contrato estable: 403 `codigo=bloqueado` + `bloqueado_hasta` ISO-8601. Hoy el servicio lanza 403 con el texto embebido y sin `codigo`; se corrige en `motor-turnos`.
- Migración `007_excepciones_bloqueo`: tabla `excepciones_bloqueo` para la excepción auditada de recepción. C-09 y C-10 se renumeran a `008` y `009` en `CHANGES.md`.

### Frontend — agenda, panel y vista odontólogo

- `features/agenda/`: agenda día/semana multi-sillón, filtros por sillón/odontólogo/estado, alta de turno interno (con diálogo de motivo cuando el paciente está bloqueado) y estados de error `solape`/`bloqueado`.
- `features/panel-dia/`: llegadas, estado de seña, contacto WhatsApp y acciones `completado`/`ausente` con confirmación y aviso de bloqueo automático.
- Vista `odonto` en la misma ruta `/agenda`: solo lectura de su día, sin filtro de odontólogo, sin alta, sin cancelar/reprogramar; puede marcar `completado`/`ausente` de sus turnos desde el panel.
- `router.tsx`: `/agenda` pasa a admitir `recepcion` además de `odonto` y `admin`; los guards `ProtectedRoute`/`PublicRoute` se conservan. `/panel` queda `recepcion|admin` y `/agenda` es el home del odontólogo (ya lo es).

### Tests

- Agenda: rango día/semana, filtros, aislamiento por `clinic_id`, confinamiento del odontólogo, 409 por solape al crear desde agenda.
- Panel: orden por hora, estado de seña, `completado`/`ausente`, idempotencia, `ausente` ×2 dispara bloqueo 30 d, bloqueado → 403 con `bloqueado_hasta`, excepción con motivo auditado, excepción sin motivo → 403.
- Migración 007 con `skipif` Postgres; contrato de error `bloqueado` y redacción de datos.

## Capabilities

### New Capabilities

- `agenda-operativa`: lectura de la agenda multi-sillón día/semana con filtros, confinamiento del rol odontólogo y alta de turno interno desde la agenda, incluida la excepción auditada al bloqueo de recepción.
- `panel-dia`: panel operativo de la jornada (llegadas, señas, contacto), marcado de `completado`/`ausente` idempotente, disparo automático del bloqueo por 2 faltas y su persistencia.

### Modified Capabilities

- `motor-turnos`: el requirement «Bloqueo por faltas» cambia su contrato observable (403 con `codigo=bloqueado` y `bloqueado_hasta`) y el alta interna admite excepción auditada con motivo obligatorio.

## Impact

- **Código backend**: `app/domain/turnos/{models,repository,service,schemas}.py`, `app/domain/turnos/gestion.py` (códigos), `app/api/internal/{agenda,panel,turnos}.py`, `app/domain/clinica/{models,repository}.py` (excepción), `app/main.py` (routers).
- **Código frontend**: `frontend/src/router.tsx`, `frontend/src/pages/{AgendaPage,PanelPage}.tsx`, `frontend/src/pages/role/*.tsx`, `frontend/src/features/agenda/`, `frontend/src/features/panel-dia/`.
- **Datos**: migración `007_excepciones_bloqueo` (nueva tabla). No se toca `turnos`, `pacientes` ni `bloqueos`: `faltas_count`, `bloqueado_hasta` y `bloqueos` ya existen desde C-02/C-05.
- **APIs**: `GET /api/internal/agenda`, `GET /api/internal/panel/dia`, `PATCH /api/internal/panel/turnos/{id}`, y `POST /api/internal/turnos` con campo opcional `motivo_excepcion`.
- **Dependencias**: C-05 (motor de reservas y `Turno`), C-03 (JWT/RBAC). No depende de C-06 ni de C-08/C-09/C-10.
- **Sistemas**: ninguno externo. La seña se muestra con un proxy de estado hasta que C-09 introduzca `Pago` (ver design).

## Governance — ALTO

Requieren revisión humana explícita **antes de escribir código**:

1. **Bloqueo automático por 2 faltas** (RN-AUS-01, DD-04): duración de 30 días, reinicio del contador y extensión del bloqueo si el paciente vuelve a faltar estando bloqueado. Afecta el acceso del paciente a reservar.
2. **Excepción auditada de recepción** (RN-AUS-02): quién puede exceptuar (`recepcion|admin`), motivo obligatorio, persistencia durable en `excepciones_bloqueo` y ausencia de tope mensual. La KB deja el tope/doble aprobación como pregunta abierta de prioridad Media.
3. **Contrato 403 `bloqueado`**: cambiar el cuerpo del error es un cambio observable para el frontend público ya implementado en C-06.

## Dependencias y lectura previa

- `CHANGES.md` §[C-07] y árbol de dependencias (GATE 5, paralelo con C-06/C-08).
- `knowledge-base/06_funcionalidades.md` §US-004, §US-005, §US-006.
- `knowledge-base/05_reglas_de_negocio.md` §Dominio: Ausentismo (RN-AUS-01..03).
- `knowledge-base/07_flujos_principales.md` §Flujo 3.
- `knowledge-base/04_modelo_de_datos.md` §Bloqueo, §Turno.
- `knowledge-base/09_decisiones_y_supuestos.md` §DD-04.
- `openspec/specs/{motor-turnos,gestion-turnos,auth-rbac,clinica-personas}/spec.md`.

## Preguntas abiertas y desvíos registrados

| # | Tipo | Tema | Tratamiento en este change |
|---|---|---|---|
| 1 | Pregunta abierta (KB, prioridad Media) | ¿Tope de excepciones por mes o doble aprobación para la excepción de bloqueo? | No se implementa tope: una excepción = un turno, con motivo y auditoría. Queda para decisión del Admin. |
| 2 | Pregunta abierta (nueva) | La KB no define si `faltas_count` se reinicia al bloquear ni qué pasa si el paciente falta estando bloqueado. | Se propone reiniciar a 0 al crear el `Bloqueo` y extender `bloqueado_hasta` a `now+30d` si vuelve a llegar a 2. Requiere confirmación. |
| 3 | Pregunta abierta (nueva) | `User` no tiene `nombre`: solo `email`. La agenda y el panel necesitan mostrar al odontólogo. | v1 muestra `email` como identificador. Agregar `nombre` a `users` es una decisión de producto fuera de C-07. |
| 4 | Desvío de contrato | `CHANGES.md` escribe `GET /api/agenda` y `GET /api/panel/dia`. | Se montan como `/api/internal/agenda` y `/api/internal/panel/...` para respetar la regla dura de routers `public/internal/webhooks` y el prefijo ya usado por C-03/C-05. Capacidad observable idéntica. |
| 5 | Desvío de datos | `CHANGES.md` reserva la migración 007 para C-09. | C-07 necesita persistir la excepción auditada: toma `007_excepciones_bloqueo`; C-09 pasa a `008` y C-10 a `009` en `CHANGES.md`. |
| 6 | Dependencia futura | El estado de seña real depende de `Pago` (C-09), que no existe. | C-07 expone `estado_sena` derivado de `Turno` con un helper único y documenta el contrato para que C-09 lo reemplace por la consulta real. |
| 7 | Riesgo | `EXCLUDE` anti-solape de C-05 corre solo en Postgres; la suite local usa SQLite. | Los tests de concurrencia/EXCLUDE quedan `skipif` Postgres, como ya hace C-05. |

## Fuera de alcance

- Cobro de seña, preferencias y webhook MP (C-08/C-09).
- Envío real de WhatsApp y job T-24hs (C-10); el panel solo muestra el contacto.
- Login de paciente, odontograma e historia clínica (v1.1, C-11/C-12).
- ABM de aranceles, prácticas o sillones (C-13/C-04).
- Reprogramar o cancelar desde la vista odontólogo (sigue siendo de recepción).
