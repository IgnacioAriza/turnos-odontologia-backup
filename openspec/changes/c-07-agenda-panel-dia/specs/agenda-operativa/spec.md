# Spec Delta — agenda-operativa

## Purpose

Define la agenda interna multi-sillón de la clínica: qué turnos se leen en una vista día o semana, cómo se filtran por recurso y estado, cómo se confina al odontólogo a su propio día y cómo recepción crea turnos internos con el mismo motor de reglas, incluida la excepción auditada al bloqueo por ausentismo.

## ADDED Requirements

### Requirement: Agenda multi-sillón por día y por semana

El backend SHALL exponer `GET /api/internal/agenda` para roles internos autenticados, devolviendo los turnos de la clínica del JWT comprendidos en el rango pedido, en la zona horaria de la clínica.

#### Scenario: Vista de un día

- **WHEN** un usuario interno pide `vista=dia&fecha=2026-11-12`
- **THEN** recibe los turnos cuyo `inicio` cae entre las 00:00 y las 24:00 de ese día en `America/Argentina/Buenos_Aires`

#### Scenario: Vista de una semana

- **WHEN** un usuario interno pide `vista=semana&fecha=2026-11-12`
- **THEN** recibe los turnos del lunes a domingo de la semana que contiene esa fecha, con `desde` y `hasta` informados en la respuesta

#### Scenario: Orden estable de la agenda

- **WHEN** la agenda devuelve varios turnos en el mismo horario
- **THEN** se ordenan por `inicio`, luego por nombre de sillón y luego por identificador de odontólogo, de forma reproducible entre requests

#### Scenario: Día sin turnos

- **WHEN** no hay turnos en el rango pedido
- **THEN** la respuesta es 200 con la lista vacía y el rango consultado, sin error

### Requirement: Filtros de agenda por sillón, odontólogo y estado

El backend SHALL aceptar los filtros opcionales `sillon`, `odontologo` y `estado`, combinables entre sí, y SHALL excluir por defecto los turnos en estado `cancelado`.

#### Scenario: Filtro por sillón

- **WHEN** se pide la agenda con `sillon=<uuid>`
- **THEN** solo se devuelven turnos de ese sillón

#### Scenario: Filtro por odontólogo

- **WHEN** se pide la agenda con `odontologo=<uuid>`
- **THEN** solo se devuelven turnos de ese odontólogo

#### Scenario: Filtro por estado

- **WHEN** se pide la agenda con `estado=confirmado`
- **THEN** solo se devuelven turnos confirmados del rango

#### Scenario: Cancelados solo cuando se piden

- **WHEN** se pide la agenda sin `estado` y existe un turno `cancelado` en el rango
- **THEN** ese turno no aparece; si se pide `estado=cancelado`, sí aparece

#### Scenario: Filtros combinados sin resultados

- **WHEN** se combinan filtros que no tienen ningún turno en común
- **THEN** la respuesta es 200 con lista vacía

### Requirement: Aislamiento por clínica en la agenda

La agenda SHALL limitar turnos, sillones y odontólogos a la clínica derivada del JWT y SHALL NOT revelar la existencia de recursos de otra clínica.

#### Scenario: Turnos de otra clínica fuera de la respuesta

- **WHEN** existe un turno de otra clínica en el mismo rango de fechas
- **THEN** la respuesta de la agenda no lo incluye ni expone datos de su paciente

#### Scenario: Filtro con un sillón de otra clínica

- **WHEN** se filtra por el identificador de un sillón que pertenece a otra clínica
- **THEN** la respuesta es 200 con lista vacía y no confirma si el sillón existe

### Requirement: Confinamiento de la vista odontólogo

El backend SHALL confinar la agenda de un usuario con rol `odonto` a los turnos cuyo `odontologo_id` coincide con el `sub` de su JWT, ignorando cualquier `odontologo` distinto recibido en el query.

#### Scenario: Odontólogo ve solo su día

- **WHEN** un usuario `odonto` pide la agenda de un día con turnos propios y de otro odontólogo
- **THEN** recibe únicamente los turnos donde `odontologo_id` es el suyo

#### Scenario: Intento de ver a otro odontólogo

- **WHEN** un usuario `odonto` envía `odontologo=<uuid de otro>`
- **THEN** la respuesta sigue limitada a sus propios turnos y no devuelve los del otro

#### Scenario: Recepción y admin sin confinamiento

- **WHEN** un usuario `recepcion` o `admin` pide la agenda
- **THEN** recibe los turnos de todos los odontólogos de la clínica

### Requirement: Alta de turno interno desde la agenda

La agenda SHALL reutilizar `POST /api/internal/turnos` para crear turnos presenciales o telefónicos, aplicando el mismo motor de reglas que la reserva pública y sin emitir `manage_token`.

#### Scenario: Alta exitosa desde la agenda

- **WHEN** recepción crea un turno interno con sillón, odontólogo, práctica y horario libres
- **THEN** la respuesta es 201 con el turno en estado `confirmado` y sin `manage_token`

#### Scenario: Solape al crear desde la agenda

- **WHEN** recepción intenta crear un turno interno en un horario ya ocupado
- **THEN** la respuesta es 409 con `codigo=solape`, mensaje claro y ningún turno creado

#### Scenario: Odontólogo sin alta

- **WHEN** un usuario con rol `odonto` intenta crear un turno interno
- **THEN** la respuesta es 403 y no se crea nada

### Requirement: Excepción auditada al bloqueo de recepción

El alta de turno interno SHALL aceptar un `motivo_excepcion` opcional; si el paciente está bloqueado y el motivo está presente, SHALL crear el turno y registrar la excepción, y si falta el motivo SHALL rechazar con 403 `codigo=bloqueado`.

#### Scenario: Excepción con motivo

- **WHEN** recepción crea un turno para un paciente con `bloqueado_hasta` futuro enviando `motivo_excepcion` no vacío
- **THEN** el turno se crea y queda registrada una excepción con ese motivo, el usuario y el turno

#### Scenario: Paciente bloqueado sin motivo

- **WHEN** recepción crea un turno para un paciente bloqueado sin `motivo_excepcion`
- **THEN** la respuesta es 403 con `codigo=bloqueado` y `bloqueado_hasta` en ISO-8601, y no se crea nada

#### Scenario: Motivo vacío

- **WHEN** se envía `motivo_excepcion` vacío o solo con espacios
- **THEN** la respuesta es 422 y no se crea ni el turno ni la excepción

#### Scenario: El canal público nunca exceptúa

- **WHEN** un paciente bloqueado reserva por `POST /api/public/reservas`
- **THEN** la respuesta es 403 `codigo=bloqueado` aunque el cuerpo incluya un motivo

### Requirement: Persistencia de la excepción de bloqueo

El sistema SHALL persistir cada excepción con `clinic_id`, `paciente_id`, `turno_id`, `usuario_id`, `motivo` y `created_at`, en la misma transacción que el turno creado.

#### Scenario: Excepción y turno son atómicos

- **WHEN** falla la creación del turno después de validarse la excepción
- **THEN** no queda ninguna fila de excepción huérfana

#### Scenario: Excepción aislada por clínica

- **WHEN** se consultan las excepciones de una clínica
- **THEN** solo se ven las de esa clínica y su paciente y turno asociados

### Requirement: Migración 007 de excepciones de bloqueo

La migración `007_excepciones_bloqueo` SHALL crear la tabla `excepciones_bloqueo` con sus claves foráneas e índices, sin reutilizar la revisión `006`.

#### Scenario: Upgrade crea la tabla

- **WHEN** `alembic upgrade head` corre sobre una base en revisión 006
- **THEN** existe `excepciones_bloqueo` con `clinic_id`, `paciente_id`, `turno_id`, `usuario_id`, `motivo` y `created_at`

#### Scenario: Downgrade revierte la tabla

- **WHEN** `alembic downgrade -1` corre desde 007
- **THEN** la tabla se elimina sin error y la base vuelve a 006

### Requirement: Interfaz de agenda día y semana

El frontend SHALL ofrecer en `/agenda` una vista mobile-first de día y semana con filtros por sillón, odontólogo y estado, y SHALL decidir los mensajes de error por el `codigo` de la respuesta, nunca por el texto.

#### Scenario: Agenda de recepción

- **WHEN** recepción abre `/agenda`
- **THEN** ve los turnos del día por sillón, puede cambiar a semana, filtrar y abrir el alta de turno interno

#### Scenario: Error de solape en el alta

- **WHEN** el alta devuelve 409 `codigo=solape`
- **THEN** el formulario conserva los datos cargados y muestra que el horario se ocupó, sin recargar la página

#### Scenario: Error de bloqueo en el alta

- **WHEN** el alta devuelve 403 `codigo=bloqueado`
- **THEN** se muestra la fecha de `bloqueado_hasta` y se ofrece el campo de motivo solo a `recepcion` y `admin`

#### Scenario: Vista odontólogo sin acciones de ABM

- **WHEN** un usuario `odonto` abre `/agenda`
- **THEN** ve solo su día, sin selector de odontólogo, sin alta, sin cancelar y sin reprogramar

### Requirement: Cobertura de tests de agenda operativa

La suite SHALL cubrir los rangos día y semana, los filtros, el aislamiento por clínica, el confinamiento del odontólogo, el alta interna con solape y la excepción de bloqueo con y sin motivo.

#### Scenario: Suite de agenda pasa

- **WHEN** se ejecuta `pytest` y `vitest`
- **THEN** pasan los tests de agenda, de excepción de bloqueo, de la migración 007 y de la interfaz de agenda
