# Design — C-07 agenda-panel-dia

## Context

Ver `proposal.md` para el porqué. Estado real verificado del repo (no del roadmap):

- **C-05 implementado**: `backend/app/domain/turnos/` tiene `Turno`, `HorarioAtencion`, `TurnoRepository` (`list_vigentes_en_rango`, `get_solape_sillon`, `get_solape_odontologo`), `service.crear_turno_publico` / `crear_turno_interno`, `gestion.py` con los `codigo` estables y `_verificar_bloqueo`, y la migración `005_motor_turnos` (`alembic heads` = `006`).
- **C-06 implementado y archivado**: gestión pública por token y gestión interna de cancelar/reprogramar. `Turno` ya tiene `sena_perdida` y `reprogramado_de_id` (migración `006`).
- **Modelo de ausentismo ya existe**: `Paciente.faltas_count` y `Paciente.bloqueado_hasta` (C-02/C-05) y la tabla `bloqueos` (`clinic_id`, `paciente_id`, `desde`, `hasta`, `motivo`, `created_by`) desde `002`. No hace falta migrar esas estructuras.
- **RBAC**: `require_role([...])` y `require_odonto_confinement` ya existen en `app/domain/auth/dependencies.py`; `clinic_id_from_token` y `usuario_id_from_token` se reutilizan desde `app/api/internal/`.
- **Catálogo interno**: `GET /api/internal/tipos-practica` y `GET /api/internal/sillones` existen. **No hay endpoint de odontólogos**; `UserRepository.list_odontologos` sí existe.
- **Frontend**: `router.tsx` declara `/agenda` con `allowedRoles=['odonto','admin']` y `/panel` con `['recepcion','admin']`. `AgendaPage` y `PanelPage` son stubs estáticos con datos hardcodeados. `features/agenda/` y `features/panel-dia/` no existen todavía.
- **Tests**: pytest sobre SQLite en local; los tests de migración y de concurrencia son `skipif` Postgres. Factories en `backend/tests/turnos_factories.py`. Frontend con vitest + Testing Library.

Restricciones que mandan:

- `clinic_id` obligatorio en toda consulta de negocio (DD-06).
- La falta la marca una persona, nunca el sistema (RN-AUS-03); el bloqueo sí es automático al llegar a 2 (RN-AUS-01, DD-04).
- Toda comparación de fechas y horarios se evalúa en `America/Argentina/Buenos_Aires` (excepciones globales de `05_reglas_de_negocio.md`).
- Errores problem+json con `codigo` estable; nunca traces ni datos de otra clínica.

## Goals / Non-Goals

**Goals:**

- Una única definición de "turnos de la agenda" y de "turnos del panel" en el dominio, consumida por routers internos con RBAC.
- Que el estado de seña que muestra el panel sea un contrato explícito y reemplazable por C-09 sin tocar el frontend.
- Que el bloqueo por 2 faltas sea transaccional, idempotente frente a reintentos y auditable.
- Que la excepción de recepción sea durable y consultable, no solo un renglón de log.
- Que el odontólogo tenga una vista útil y estrictamente confinada, sin abrir superficie de ABM.

**Non-Goals:**

- Cobro, preferencia y webhook MP (C-08/C-09).
- Notificaciones reales (C-10).
- Nombre visible del odontólogo: `User` no tiene `nombre`; se muestra `email` (pregunta abierta).
- Edición de horarios de atención, sillones o prácticas desde la agenda.
- Un calendario drag-and-drop: el alta y la reprogramación usan los endpoints existentes.

## Decisions

### D1 — Endpoints internos bajo `/api/internal`

```text
GET   /api/internal/agenda?vista=dia|semana&fecha=&sillon=&odontologo=&estado=
GET   /api/internal/panel/dia?fecha=
PATCH /api/internal/panel/turnos/{id}
POST  /api/internal/turnos            (existente; se le agrega `motivo_excepcion`)
```

**Por qué**: `CHANGES.md` C-07 escribe `/api/agenda` y `/api/panel/dia`, pero la regla dura 4 exige routers `public/internal/webhooks` y el proyecto ya monta todo lo autenticado bajo `/api/internal` (C-03/C-04/C-05/C-06). Montar rutas autenticadas fuera de ese prefijo rompe la convención y el agrupado de OpenAPI. La capacidad observable no cambia: mismas operaciones, mismo RBAC, mismo `clinic_id`.

**Alternativas descartadas**: crear `/api/agenda` en la raíz (rompe la separación por superficie de confianza); reutilizar `/api/internal/turnos` como listado (mezcla lectura de agenda con gestión de un turno y pierde los filtros).

### D2 — La agenda lee por rango con una sola consulta filtrada

- `vista=dia` → `[00:00, 24:00)` del `fecha` en la zona de la clínica, convertido a UTC.
- `vista=semana` → lunes a domingo de la semana ISO que contiene `fecha`, mismo criterio.
- `fecha` ausente → hoy en la zona de la clínica.
- Filtros opcionales `sillon`, `odontologo`, `estado`; por defecto se excluye `cancelado` (el horario ya está libre y no es parte de la operación), y `estado=cancelado` lo incluye explícitamente.
- Orden: `inicio`, `Sillon.nombre`, `odontologo_id`.
- La respuesta incluye `vista`, `desde`, `hasta` y `turnos[]` con ids, horas, estado, paciente (id + nombre), práctica (id + nombre), sillón (id + nombre) y odontólogo (id + email). El teléfono **no** viaja en la agenda: vive en el panel, que es la pantalla de contacto.

**Por qué una consulta y no N por sillón**: la agenda día/semana es una lectura acotada por `clinic_id` + rango y ya está cubierta por `ix_turnos_clinic_inicio`, `ix_turnos_sillon_inicio`, `ix_turnos_odontologo_inicio` e `ix_turnos_estado` de la migración `005`. No se agregan índices ni se cambia el esquema; igual se verifica con `EXPLAIN (ANALYZE, BUFFERS)` en Postgres antes y después (test `skipif`) que la consulta use un índice y no un seq scan.

**Alternativas descartadas**: devolver slots vacíos para dibujar la grilla (mucho payload y una segunda fuente de verdad de disponibilidad); agrupar por sillón en el backend (el frontend necesita filtrar y ordenar igual, y el contrato se vuelve rígido).

### D3 — El confinamiento del odontólogo es server-side y silencioso

`require_odonto_confinement` devuelve el `sub` cuando el rol es `odonto`. El servicio fuerza `odontologo_id = sub` y descarta cualquier `odontologo` distinto recibido. No se responde 403 por pedir a otro odontólogo: se devuelve su propio día, que es lo que US-006 pide y no revela la existencia de agendas ajenas.

**Por qué**: un 403 con "no podés ver a otro" confirma que ese odontólogo existe y tiene agenda. El filtro forzado mantiene la vista útil sin superficie de enumeración.

**Alternativas descartadas**: confiar en que el frontend no mande el filtro (viola RBAC server-side); 403 ante cualquier intento (filtra existencia y rompe la vista si el frontend manda un default).

### D4 — `estado_sena` es un contrato derivado hasta que exista `Pago`

`Pago` no existe (C-08 crea la preference, C-09 la tabla). El panel necesita mostrar "estado de seña" ya (US-005). Se define un helper único de dominio:

| Condición | `estado_sena` |
|---|---|
| `monto_sena = 0` | `no_requerida` |
| `sena_perdida = true` | `perdida` |
| `estado` en `confirmado`, `completado` o `ausente` (con `monto_sena > 0`) | `aprobada` |
| `estado = pendiente_sena` (con `monto_sena > 0`) | `pendiente` |

Los turnos `cancelado` y `reprogramado` no aparecen en el panel, así que no necesitan rama propia. Un turno solo puede llegar a `completado`/`ausente` desde `confirmado` (D5), por lo que su seña estaba aprobada.

**Por qué**: el frontend consume un enum estable y C-09 solo cambia la implementación del helper por la consulta a `Pago` (`aprobado` vigente), sin tocar contratos ni pantallas. Es el mismo criterio que C-06 ya usa en `_tiene_sena_aprobada` para decidir la pérdida de seña.

**Alternativas descartadas**: no mostrar seña hasta C-09 (incumple US-005); exponer `monto_sena` crudo y dejar que el frontend infiera (tres fuentes de verdad y UI acoplada a estados internos).

### D5 — Máquina de estados del marcado e idempotencia

| Estado origen | Destino permitido | Resultado |
|---|---|---|
| `confirmado` | `completado` | 200, no toca faltas |
| `confirmado` | `ausente` | 200, suma falta (y puede bloquear) |
| `completado` | `completado` | 200 idempotente, sin efectos |
| `ausente` | `ausente` | 200 idempotente, sin sumar otra falta |
| `ausente` ↔ `completado` | otro final | 409 `estado_no_actualizable` |
| `pendiente_sena`, `cancelado`, `reprogramado` | cualquiera | 409 `estado_no_actualizable` |
| inexistente u otra clínica | — | 404 `turno_no_encontrado` |
| turno de otro odontólogo (rol `odonto`) | — | 404 `turno_no_encontrado` |

**Por qué `pendiente_sena` no se marca**: un turno sin seña aprobada no está confirmado; marcarlo `ausente` contaría una falta por un turno que el paciente nunca aseguró, y RN-RES-05 dice que solo `confirmado` implica seña aprobada. La expiración de C-05 ya lo pasa a `cancelado` sin sumar falta.

**Por qué idempotente**: el panel es una pantalla de mostrador con doble click y reintentos de red. Repetir la misma acción no puede duplicar una falta ni crear un segundo `Bloqueo`. La idempotencia se resuelve por estado destino, sin tabla de eventos ni `Idempotency-Key`.

**Alternativas descartadas**: aceptar cualquier transición (un `ausente` accidental no se podría corregir y bloquearía pacientes); exigir `If-Match`/versión (complejidad sin requisito).

### D6 — Bloqueo automático transaccional con reinicio de contador

Dentro de la misma transacción del `ausente`:

1. Bloquear la fila del paciente (`SELECT ... FOR UPDATE`) para serializar dos marcados concurrentes.
2. `faltas_count += 1`.
3. Si `faltas_count >= 2`:
   - `Bloqueo(clinic_id, paciente_id, desde=now, hasta=now+30d, motivo="2_faltas", created_by=str(usuario_id))`.
   - `paciente.bloqueado_hasta = hasta` (si ya había un bloqueo futuro, se extiende a `now+30d`).
   - `paciente.faltas_count = 0`.
   - Log estructurado `bloqueo_automatico` con `clinic_id`, `paciente_id`, `turno_id`, `usuario_id`, `bloqueado_hasta`.
4. Commit único con el cambio del turno.

**Por qué reiniciar**: la KB no define el alcance del contador. Si no se reinicia, la tercera falta vuelve a bloquear de inmediato (el contador nunca baja) y el paciente queda bloqueado de por vida. Reiniciar hace que "2 faltas" signifique "2 faltas desde el último bloqueo". Se registra como decisión abierta para confirmación del Admin.

**Por qué `FOR UPDATE`**: dos recepcionistas marcando dos turnos del mismo paciente a la vez podrían leer `faltas_count=1` ambos y crear dos bloqueos. El lock por paciente lo evita; se testea con Postgres (`skipif` en SQLite, que no soporta el mismo aislamiento).

**Alternativas descartadas**: job nocturno que cuenta faltas (rompe "al marcar la 2.ª falta" y agrega latencia); `UNIQUE` parcial sobre `bloqueos` por paciente y ventana (no expresa "30 días desde la segunda falta" y complica la extensión).

### D7 — Migración 007: `excepciones_bloqueo`

```sql
CREATE TABLE excepciones_bloqueo (
  id UUID PRIMARY KEY,
  clinic_id UUID NOT NULL REFERENCES clinic(id) ON DELETE CASCADE,
  paciente_id UUID NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
  turno_id UUID NOT NULL UNIQUE REFERENCES turnos(id) ON DELETE CASCADE,
  usuario_id UUID NOT NULL REFERENCES users(id),
  motivo TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX ix_excepciones_bloqueo_clinic_created ON excepciones_bloqueo (clinic_id, created_at);
CREATE INDEX ix_excepciones_bloqueo_paciente ON excepciones_bloqueo (paciente_id);
```

**Por qué una tabla y no solo log**: RN-AUS-02 exige auditoría de una decisión que afecta el acceso del paciente y C-06 (D6) dejó explícito que C-07 era el momento de introducir un registro de eventos si hacía falta. Un log se rota y no se consulta desde el panel ni desde una futura pantalla de admin; una fila sí. El `UNIQUE(turno_id)` expresa "una excepción por turno creado" y evita duplicados por reintento.

**Por qué no una tabla genérica de eventos**: hoy el único evento de dominio que necesita consulta durable es la excepción; `Bloqueo` y `Turno` ya son registros. Una tabla genérica sin segundo caso de uso agrega esquema y consultas sin valor.

**Numeración**: C-07 toma `007`; C-09 pasa a `008` y C-10 a `009` en `CHANGES.md`. Se actualiza el texto de ambos changes y la nota de migraciones para que el roadmap no quede mintiendo.

### D8 — La excepción se persiste en el servicio de alta, no en el router

`crear_turno_interno` recibe `motivo_excepcion: str | None` y `usuario_id: UUID`. Si el paciente está bloqueado:

- motivo `None` → `ForbiddenError(code="bloqueado", extra={"bloqueado_hasta": iso})`.
- motivo presente pero vacío tras `strip()` → `UnprocessableError(code="motivo_requerido")`.
- motivo válido → crea el turno y la fila de `excepciones_bloqueo` antes del commit.

**Por qué en el servicio**: la regla es de dominio y debe valer para cualquier caller interno futuro (importador, integración), no solo para el router de agenda. El router solo traduce HTTP.

**Alternativas descartadas**: validar en el router (regla duplicada y evitable); crear el turno y auditar en un segundo commit (deja turnos sin excepción si falla el segundo).

### D9 — Contrato de errores nuevo

| Situación | HTTP | `codigo` |
|---|---|---|
| Paciente bloqueado al crear turno | 403 | `bloqueado` (+ `bloqueado_hasta`) |
| Excepción pedida con motivo vacío | 422 | `motivo_requerido` |
| Estado del turno no admite el marcado | 409 | `estado_no_actualizable` |
| Solape al crear desde agenda | 409 | `solape` (existente) |
| Turno inexistente / otra clínica / otro odontólogo | 404 | `turno_no_encontrado` (existente) |

**Por qué `bloqueado` y no reutilizar `token_invalido`/`estado_no_gestionable`**: el frontend necesita distinguir "no podés reservar por ausentismo" de "el enlace no sirve" y de "ese turno ya terminó". Un `codigo` por causa mantiene el `switch` del cliente chico y los tests estables.

### D10 — Frontend: dos features y páginas role-aware

- `features/agenda/`: `api.ts`, `types.ts`, `AgendaDia.tsx`, `AgendaSemana.tsx`, `FiltrosAgenda.tsx`, `AltaTurnoDialog.tsx`, `ExcepcionBloqueoDialog.tsx`.
- `features/panel-dia/`: `api.ts`, `types.ts`, `PanelLista.tsx`, `MarcarEstadoDialog.tsx`, `ContactoWhatsApp.tsx`.
- `AgendaPage` y `PanelPage` pasan a componer esas features según `user.role` de `useAuth`; no se duplican páginas por rol.
- `/agenda` admite `recepcion`, `odonto` y `admin`; `/panel` queda `recepcion|admin`; el home del odonto sigue siendo `/agenda` (`HOME_POR_ROL`).
- Se usa el `api-client` autenticado existente (interceptor 401 → `/login`); no se toca el `public-client`.
- Sin `any`, sin barrel files, PascalCase, mobile-first: la grilla de semana colapsa a lista por día en 390 px.

**Por qué una sola página por pantalla**: el odontólogo y la recepción miran el mismo dato con permisos distintos; separar páginas duplica layout, estilos y fetch. La diferencia es de acciones, y se resuelve con el rol.

**Alternativas descartadas**: ruta `/odonto` nueva (rompe `HOME_POR_ROL` y el guard ya probado); reutilizar `PanelPage` para el odontólogo (US-006 pide su día, no la operación de recepción).

### D11 — Se expone la lista de odontólogos para los filtros

Se agrega `GET /api/internal/odontologos` (roles `recepcion|odonto|admin`) devolviendo `id` y `email` de los odontólogos activos de la clínica. Es la única fuente para poblar el filtro; no se hardcodea.

**Por qué**: el filtro por odontólogo de US-004 no puede pedirle al usuario un UUID. `UserRepository.list_odontologos` ya existe y el endpoint es de solo lectura.

**Alternativas descartadas**: derivar la lista de los turnos del día (un odontólogo sin turnos desaparece del filtro); hardcodear (rompe con cualquier alta de personal).

## Risks / Trade-offs

- **Doble bloqueo por marcados concurrentes** → `SELECT ... FOR UPDATE` sobre el paciente y test Postgres `skipif`; en SQLite el caso no se puede reproducir.
- **`faltas_count` reiniciado oculta el historial de faltas** → el historial queda en `turnos.estado='ausente'` y en `bloqueos`; el contador es solo el gatillo, no la verdad histórica.
- **El bloqueo se extiende si el paciente falta estando bloqueado** → decisión conservadora; se documenta y se pide confirmación (governance ALTO). La alternativa (ignorar faltas durante el bloqueo) premia al paciente que ya faltó.
- **`estado_sena` es un proxy** → C-09 debe reemplazar el helper; se deja anotado como contrato y test del enum para que el cambio sea localizado.
- **La agenda no muestra el teléfono** → recepción lo necesita para llamar; vive en el panel, que es la pantalla de contacto. Si se pide en agenda, se agrega al contrato sin cambiar permisos.
- **`User` sin `nombre`** → la agenda y el panel muestran `email`. Agregar `nombre` es una migración de personas fuera de C-07; se registra como pregunta abierta.
- **Cambiar el 403 de bloqueo afecta al canal público de C-06** → el cuerpo gana `codigo` y `bloqueado_hasta` sin quitar `detail`; el frontend público actual sigue funcionando y se agrega un test de contrato.
- **Migración 007 desplaza a C-09/C-10** → se actualiza `CHANGES.md` en el mismo change y se verifica que `alembic heads` siga siendo lineal.
- **SQLite no soporta `EXCLUDE` ni el mismo locking** → los tests de concurrencia, `EXPLAIN` y migración son `skipif` Postgres, como ya hace C-05.

## Migration Plan

1. `alembic upgrade head` aplica `007_excepciones_bloqueo` después de `006`. Sin backfill: la tabla nace vacía y es correcta para todo turno existente.
2. Rollback: `alembic downgrade 006` elimina la tabla. Se pierde la evidencia de excepciones; aceptable antes del go-live.
3. Orden de despliegue: backend primero (endpoints nuevos y `motivo_excepcion` opcional), frontend después. El contrato 403 gana campos, no los quita, así que un frontend viejo sigue funcionando.
4. `CHANGES.md`: C-09 pasa de migración `007` a `008`, C-10 de `008` a `009`, y se corrige la nota "006 = C-06, 007 = C-09" a "006 = C-06, 007 = C-07, 008 = C-09, 009 = C-10".
5. No se reescriben las migraciones `002`, `005` ni `006`.

## UI Mockups

- Design system revision: 1 — `design-system/README.md`, `Approval: approved (2026-11-10, by user)`.
- Decision: yes (política de proyecto `system-and-mockups`), 2026-11-11.
- Mockups: `openspec/changes/c-07-agenda-panel-dia/mockups/` (a producir en la etapa de diseño; gate bloqueante antes de implementar UI).
- Approval: pending.
- Preview: pending (no renderizado todavía).
- Visual verify: pending (se completa en verify contra la implementación).

**Alcance previsto**: tres pantallas con los estados que introduce el change.

| Pantalla | Ruta | Estados a maquetar |
|---|---|---|
| `agenda.html` | `/agenda` | día multi-sillón, semana, filtros activos, día vacío, alta de turno, 409 `solape`, 403 `bloqueado` con motivo, vista odontólogo sin ABM |
| `panel-dia.html` | `/panel` | lista por hora con seña y WhatsApp, marcar `completado`, confirmar `ausente`, aviso de segunda falta/bloqueo 30 d, 409 `estado_no_actualizable` |
| `odonto.html` | `/agenda` (rol odonto) | solo lectura del propio día, marcar llegada/ausencia propia, sin alta ni cancelar |

Los mockups deberán importar `design-system/tokens.css` y `brand.js`, usar `design-system/assets/logo.svg` y copiar los `codigo` reales del backend.

## Open Questions

**Resueltas por el usuario el 2026-11-12 (gate de governance ALTO, tarea 1.1):**

- **Tope de excepciones / doble aprobación**: no se implementa tope. `recepcion|admin` pueden exceptuar con `motivo_excepcion` obligatorio; una excepción equivale a un turno y queda auditada en `excepciones_bloqueo`. La política de doble aprobación queda como decisión operativa sin enforcement.
- **`faltas_count`**: se reinicia a `0` al crear el `Bloqueo`. Si el paciente vuelve a llegar a 2 faltas estando bloqueado, se extiende `bloqueado_hasta` a `now + 30d` (cada bloqueo dura 30 días desde la última falta).
- **Contrato del 403**: se acepta el cambio a problem+json con `codigo=bloqueado` y `bloqueado_hasta`. Implica ajustar el manejo de errores del canal público de C-06 para reconocer ese código (tarea del grupo 3).

**Siguen abiertas (no bloquean la implementación):**

- ¿Se agrega `User.nombre` para mostrar al odontólogo por nombre y apellido en lugar de `email`? ¿En qué change?
- ¿La agenda debe incluir turnos `cancelado` por defecto para que recepción vea los huecos liberados del día, o alcanza con pedirlos por filtro? (El diseño actual los excluye por defecto y los incluye con `estado=cancelado`.)
- ¿El odontólogo debe poder marcar `ausente` desde su vista o solo recepción? RN-AUS-03 dice "recepción/odontólogo"; este diseño lo habilita confinado a sus turnos.
