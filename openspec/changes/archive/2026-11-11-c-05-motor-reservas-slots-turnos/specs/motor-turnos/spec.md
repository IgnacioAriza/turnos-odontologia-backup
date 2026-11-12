# Spec Delta — motor-turnos

## Purpose

Define la generación de horarios disponibles y el ciclo de vida inicial de los turnos: reserva pública sin login, reserva interna, anti-solape por sillón y odontólogo, foto de la seña y expiración de turnos sin pago.

## ADDED Requirements

### Requirement: Registro de turno

El sistema SHALL persistir cada turno con `clinic_id`, `paciente_id`, `sillon_id`, `odontologo_id`, `tipo_practica_id`, `inicio`, `fin`, `estado`, `manage_token`, `reprogramaciones_count` y `monto_sena`, aislado por clínica.

#### Scenario: Alta de turno pendiente de seña

- **WHEN** se crea un turno con una práctica de 30 minutos que empieza a las 10:00
- **THEN** se guarda en estado `pendiente_sena` con `fin=10:30`, `reprogramaciones_count=0` y `monto_sena` calculado

#### Scenario: Token de gestión único

- **WHEN** se crean dos turnos públicos
- **THEN** cada uno recibe un `manage_token` distinto y no adivinable

### Requirement: Horario de atención por clínica

El sistema SHALL persistir franjas de atención por clínica con día de semana, hora de inicio y hora de fin, y SHALL generar slots únicamente dentro de esas franjas.

#### Scenario: Día sin atención

- **WHEN** la clínica no tiene franja configurada para un día
- **THEN** ese día no devuelve slots

#### Scenario: Franja de sábado

- **WHEN** la clínica atiende el sábado de 08:00 a 13:00 y se consultan slots para un sábado
- **THEN** los slots generados terminan a más tardar a las 13:00

### Requirement: Generación de slots por duración de práctica

El backend SHALL exponer `GET /api/public/slots?fecha=&practica=` devolviendo huecos alineados a la duración de la práctica, en la timezone de la clínica y sin datos de otros pacientes.

#### Scenario: Slots alineados a la duración

- **WHEN** se piden slots para una práctica de 30 minutos en una franja de 08:00 a 10:00
- **THEN** se devuelven los inicios 08:00, 08:30, 09:00 y 09:30, sin que ningún turno termine después del fin de la franja

#### Scenario: Slot ocupado excluido

- **WHEN** existe un turno vigente que ocupa las 09:00
- **THEN** el slot de las 09:00 no se devuelve

#### Scenario: Datos de otros pacientes

- **WHEN** un paciente consulta los slots
- **THEN** la respuesta solo contiene horarios y recursos, sin nombre, teléfono ni DNI de otros pacientes

### Requirement: Asignación automática de sillón y odontólogo

El backend SHALL asignar automáticamente el primer sillón activo libre y un odontólogo disponible para el slot; si no hay combinación libre, el slot no se ofrece.

#### Scenario: Asignación en slot libre

- **WHEN** hay dos sillones activos y un odontólogo libre a las 10:00
- **THEN** la reserva se crea con un sillón activo y ese odontólogo

#### Scenario: Sin recursos libres

- **WHEN** todos los sillones u odontólogos están ocupados en un horario
- **THEN** ese horario no aparece como slot disponible

### Requirement: Anti-solape por sillón

El sistema SHALL rechazar dos turnos superpuestos para el mismo `sillon_id` cuando al menos uno está vigente, respondiendo 409 con un mensaje claro.

#### Scenario: Solape de sillón

- **WHEN** se intenta reservar un sillón ya ocupado de 10:00 a 10:30 con otro turno de 10:15 a 10:45
- **THEN** la operación falla con 409 y no se crea el segundo turno

#### Scenario: Turnos cancelados no bloquean

- **WHEN** el turno existente en ese sillón está cancelado
- **THEN** el horario puede reservarse

### Requirement: Anti-solape por odontólogo

El sistema SHALL rechazar dos turnos superpuestos para el mismo `odontologo_id` cuando al menos uno está vigente, respondiendo 409.

#### Scenario: Solape de odontólogo

- **WHEN** se intenta asignar un odontólogo ya ocupado de 10:00 a 11:00 a otro turno de 10:30 a 11:15
- **THEN** la operación falla con 409

#### Scenario: Reserva concurrente

- **WHEN** dos requests intentan reservar el mismo sillón y horario a la vez
- **THEN** solo una reserva se crea y la otra recibe 409

### Requirement: Reserva pública sin login

El backend SHALL exponer `POST /api/public/reservas` aceptando nombre, teléfono, práctica y horario, sin requerir JWT, y SHALL crear o reutilizar el paciente por `clinic_id` y teléfono.

#### Scenario: Reserva exitosa

- **WHEN** un paciente nuevo envía nombre, teléfono, práctica y un slot libre
- **THEN** se crea el paciente, el turno en `pendiente_sena` y se devuelve 201 con `manage_token`

#### Scenario: Paciente existente

- **WHEN** el teléfono ya pertenece a un paciente de la clínica
- **THEN** se reutiliza ese paciente y no se duplica

### Requirement: Foto del monto de seña

El sistema SHALL calcular `monto_sena` al crear el turno como `round(precio_efectivo * sena_pct / 100)` y SHALL conservarlo aunque luego cambie el porcentaje o el arancel de la práctica.

#### Scenario: Cálculo al reservar

- **WHEN** la práctica tiene precio efectivo 10000 y `sena_pct=20`
- **THEN** el turno se guarda con `monto_sena=2000`

#### Scenario: Cambio posterior de seña

- **WHEN** el admin cambia el `% seña` de la práctica después de crear el turno
- **THEN** el `monto_sena` del turno existente no cambia

### Requirement: Bloqueo por faltas

El backend SHALL rechazar la creación de reservas de un paciente con `bloqueado_hasta` posterior al momento actual, respondiendo 403 e informando `bloqueado_hasta`.

#### Scenario: Paciente bloqueado

- **WHEN** un paciente con `bloqueado_hasta` futuro intenta reservar por el canal público o interno
- **THEN** recibe 403 con la fecha de desbloqueo

#### Scenario: Paciente habilitado

- **WHEN** `bloqueado_hasta` es nulo o anterior al momento de la reserva
- **THEN** la reserva se permite

### Requirement: Expiración de turnos pendientes de seña

El sistema SHALL expirar un turno en `pendiente_sena` que no recibió pago dentro de 30 minutos, pasándolo a `cancelado` y liberando el slot.

#### Scenario: Turno expirado

- **WHEN** pasan 30 minutos desde la creación sin pago aprobado
- **THEN** el turno pasa a `cancelado` y deja de bloquear el horario

#### Scenario: Slot liberado

- **WHEN** un turno expirado ocupaba las 10:00
- **THEN** las 10:00 vuelven a aparecer como slot disponible

### Requirement: Reserva interna con RBAC

El backend SHALL exponer `POST /api/internal/turnos` solo para roles `recepcion` y `admin`, aplicando el mismo motor de reglas y sin emitir `manage_token` público.

#### Scenario: Recepción crea turno

- **WHEN** un usuario con rol `recepcion` crea un turno interno con un slot libre
- **THEN** recibe 201 con el turno creado y sin `manage_token`

#### Scenario: Rol no autorizado

- **WHEN** un usuario con rol `odonto` llama al endpoint interno
- **THEN** recibe 403

### Requirement: Aislamiento por clínica en turnos

El sistema SHALL limitar los slots, turnos y horarios a la clínica correspondiente, derivada de la práctica en el canal público y del JWT en el canal interno.

#### Scenario: Práctica de otra clínica

- **WHEN** se piden slots con el id de una práctica de otra clínica
- **THEN** la respuesta no expone turnos ni horarios de esa otra clínica

#### Scenario: Reserva interna de otra clínica

- **WHEN** un usuario interno intenta crear un turno con un sillón de otra clínica
- **THEN** recibe 404 y no se crea nada

### Requirement: Migración 005 del motor de turnos

La migración `005_motor_turnos` SHALL crear `turnos` y `horarios_atencion` con índices, CHECKs y constraints anti-solape, sin reutilizar la revisión `004`.

#### Scenario: Upgrade crea el motor

- **WHEN** `alembic upgrade head` corre sobre una base en revisión 004
- **THEN** existen `turnos` y `horarios_atencion` con sus índices y constraints

#### Scenario: Downgrade revierte el motor

- **WHEN** `alembic downgrade -1` corre desde 005
- **THEN** las dos tablas se eliminan sin error y la base vuelve a 004

### Requirement: Seed de horarios de atención

El seed SHALL crear de forma idempotente las franjas de lunes a viernes de 08:00 a 20:00 y sábado de 08:00 a 13:00 para la clínica inicial.

#### Scenario: Seed en base vacía

- **WHEN** el seed corre sobre una base sin horarios
- **THEN** existen las franjas de lunes a sábado con sus horas

#### Scenario: Seed ejecutado dos veces

- **WHEN** el seed corre dos veces
- **THEN** no se duplican franjas

### Requirement: Cobertura de tests del motor de turnos

La suite SHALL cubrir solape por sillón y odontólogo, reserva concurrente, expiración, bloqueo, `manage_token`, foto de `monto_sena`, RBAC interno, aislamiento por clínica y generación de slots.

#### Scenario: Suite del motor pasa

- **WHEN** se ejecuta `pytest`
- **THEN** pasan los tests del motor de turnos, la migración 005 y el seed de horarios
