# Spec — panel-dia

## Purpose

Define el panel operativo de la jornada: la lista de turnos del día con su estado de seña y contacto, el marcado de llegadas y ausencias por parte de recepción u odontólogo, y el bloqueo automático de 30 días que dispara la segunda falta.

## Requirements

### Requirement: Panel del día ordenado por hora

El backend SHALL exponer `GET /api/internal/panel/dia?fecha=` devolviendo los turnos operables de esa fecha ordenados por `inicio` ascendente, con paciente, práctica, sillón, odontólogo, estado del turno y estado de seña.

#### Scenario: Jornada con turnos

- **WHEN** recepción pide el panel de un día con turnos a las 09:00, 10:30 y 11:00
- **THEN** recibe los tres turnos en ese orden con el nombre del paciente, la práctica, el sillón y el odontólogo

#### Scenario: Turnos cancelados fuera del panel

- **WHEN** un turno del día está en estado `cancelado` o `reprogramado`
- **THEN** no aparece en el panel del día

#### Scenario: Día sin turnos

- **WHEN** no hay turnos operables en la fecha pedida
- **THEN** la respuesta es 200 con lista vacía y un resumen en cero

#### Scenario: Resumen de la jornada

- **WHEN** el panel devuelve los turnos del día
- **THEN** incluye un resumen con total, pendientes de seña, confirmados, completados y ausentes

### Requirement: Estado de seña visible en el panel

El panel SHALL informar por turno un `estado_sena` con los valores `pendiente`, `aprobada`, `perdida` o `no_requerida`, junto con `monto_sena`.

#### Scenario: Turno pendiente de seña

- **WHEN** el turno está en `pendiente_sena` con `monto_sena` mayor a cero
- **THEN** el panel lo muestra con `estado_sena=pendiente`

#### Scenario: Turno confirmado con seña

- **WHEN** el turno está en `confirmado` con `monto_sena` mayor a cero
- **THEN** el panel lo muestra con `estado_sena=aprobada`

#### Scenario: Seña perdida

- **WHEN** el turno tiene `sena_perdida=true`
- **THEN** el panel lo muestra con `estado_sena=perdida` y no promete devolución

#### Scenario: Práctica sin seña

- **WHEN** el turno tiene `monto_sena=0`
- **THEN** el panel lo muestra con `estado_sena=no_requerida`

### Requirement: Contacto de WhatsApp en el panel

El panel SHALL incluir el teléfono del paciente para permitir el contacto por WhatsApp, y SHALL limitarlo a los turnos que el usuario puede operar.

#### Scenario: Recepción ve el contacto

- **WHEN** recepción abre el panel del día
- **THEN** cada turno incluye el teléfono del paciente en formato internacional para abrir un chat de WhatsApp

#### Scenario: Odontólogo ve solo su contacto

- **WHEN** un usuario `odonto` abre el panel del día
- **THEN** solo recibe teléfonos de los turnos donde `odontologo_id` es el suyo

#### Scenario: Aviso de segunda falta antes de marcar

- **WHEN** recepción abre el panel de un paciente con `faltas_count=1`
- **THEN** el turno incluye `faltas_count` y `bloqueado_hasta` para que la UI avise que la próxima ausencia bloquea 30 días

### Requirement: Marcado de completado y ausente

El backend SHALL exponer `PATCH /api/internal/panel/turnos/{id}` aceptando únicamente `completado` o `ausente` como estado destino, para roles `recepcion`, `admin` y `odonto` confinado a sus turnos.

#### Scenario: Marcar llegada

- **WHEN** recepción marca un turno `confirmado` como `completado`
- **THEN** el turno queda en `completado` y no modifica `faltas_count`

#### Scenario: Marcar ausencia

- **WHEN** recepción marca un turno `confirmado` como `ausente`
- **THEN** el turno queda en `ausente` y el contador de faltas del paciente aumenta en uno

#### Scenario: Estado destino no permitido

- **WHEN** se intenta marcar un turno como `cancelado` o `confirmado` por este endpoint
- **THEN** la respuesta es 422 y el turno no cambia

#### Scenario: Turno de otra clínica

- **WHEN** un usuario interno intenta marcar un turno de otra clínica
- **THEN** la respuesta es 404 y no se modifica nada

#### Scenario: Odontólogo marca un turno ajeno

- **WHEN** un usuario `odonto` intenta marcar un turno que no es suyo
- **THEN** la respuesta es 404 y no se modifica nada

### Requirement: Idempotencia del marcado

El marcado SHALL ser idempotente para el mismo estado destino: repetir la misma operación SHALL devolver 200 sin volver a contar la falta ni crear otro bloqueo.

#### Scenario: Ausente repetido

- **WHEN** se marca dos veces el mismo turno como `ausente`
- **THEN** la segunda respuesta es 200 con el mismo turno y `faltas_count` no aumenta de nuevo

#### Scenario: Completado repetido

- **WHEN** se marca dos veces el mismo turno como `completado`
- **THEN** la segunda respuesta es 200 y el turno conserva su estado

#### Scenario: Transición entre estados finales

- **WHEN** se intenta pasar un turno `ausente` a `completado` o viceversa
- **THEN** la respuesta es 409 con `codigo=estado_no_actualizable` y el turno no cambia

#### Scenario: Turno cancelado, reprogramado o pendiente de seña

- **WHEN** se intenta marcar un turno `cancelado`, `reprogramado` o `pendiente_sena`
- **THEN** la respuesta es 409 con `codigo=estado_no_actualizable` y el turno no cambia

### Requirement: La falta siempre la marca una persona

El sistema SHALL NOT marcar `ausente` de forma automática: el estado solo cambia por una acción explícita de recepción, admin u odontólogo desde el panel.

#### Scenario: Turno vencido sin marcado

- **WHEN** pasa la hora de un turno y nadie lo marca
- **THEN** el turno conserva su estado y `faltas_count` no cambia

#### Scenario: Expiración de seña no cuenta falta

- **WHEN** un turno `pendiente_sena` expira por falta de pago
- **THEN** queda en `cancelado` y no suma una falta al paciente

### Requirement: Bloqueo automático por segunda falta

Al registrarse la segunda falta vigente de un paciente, el sistema SHALL crear un `Bloqueo` de 30 días, actualizar `Paciente.bloqueado_hasta` y reiniciar `faltas_count`, en la misma transacción que el `ausente`.

#### Scenario: Segunda falta dispara el bloqueo

- **WHEN** un paciente con `faltas_count=1` recibe su segunda `ausente`
- **THEN** se crea un `Bloqueo` con `motivo="2_faltas"`, `desde=now`, `hasta=now+30 días` y `created_by` del usuario que marcó, y `bloqueado_hasta` queda en esa fecha

#### Scenario: Primera falta no bloquea

- **WHEN** un paciente con `faltas_count=0` recibe una `ausente`
- **THEN** queda con `faltas_count=1` y sin bloqueo

#### Scenario: Contador reiniciado tras el bloqueo

- **WHEN** se crea el bloqueo por segunda falta
- **THEN** `faltas_count` vuelve a 0 para que la próxima falta no bloquee de inmediato

#### Scenario: Falla la creación del bloqueo

- **WHEN** el registro del `Bloqueo` falla
- **THEN** el turno no queda marcado como `ausente` y el contador no avanza

#### Scenario: Falta estando bloqueado

- **WHEN** un paciente ya bloqueado vuelve a acumular dos faltas
- **THEN** se registra un nuevo `Bloqueo` y `bloqueado_hasta` se extiende a 30 días desde ese momento

### Requirement: Trazabilidad del bloqueo automático

El sistema SHALL registrar en el log de dominio cada bloqueo automático con `clinic_id`, `paciente_id`, `turno_id`, `usuario_id` y `bloqueado_hasta`, sin datos de otros pacientes.

#### Scenario: Log del bloqueo

- **WHEN** la segunda falta crea un bloqueo
- **THEN** el log contiene el evento de bloqueo con esos campos y el `motivo="2_faltas"`

### Requirement: Interfaz del panel del día

El frontend SHALL ofrecer en `/panel` un panel mobile-first con las llegadas del día, el estado de seña, el contacto por WhatsApp y las acciones de `completado` y `ausente` con confirmación.

#### Scenario: Operar la jornada

- **WHEN** recepción abre `/panel`
- **THEN** ve los turnos del día por hora con estado de seña y puede abrir WhatsApp del paciente

#### Scenario: Confirmar una ausencia

- **WHEN** recepción marca `ausente`
- **THEN** se pide confirmación explícita antes de enviar y, si es la segunda falta, se avisa que el paciente queda bloqueado 30 días

#### Scenario: Error de estado no actualizable

- **WHEN** el marcado devuelve 409 `codigo=estado_no_actualizable`
- **THEN** el panel refresca el turno y explica que ya estaba en otro estado final

#### Scenario: Vista odontólogo del panel

- **WHEN** un usuario `odonto` abre el panel
- **THEN** ve solo sus turnos del día y puede marcar sus propias llegadas y ausencias, sin acciones de ABM

### Requirement: Cobertura de tests del panel del día

La suite SHALL cubrir el orden y los filtros del panel, el estado de seña, el marcado idempotente, la segunda falta con bloqueo, la falta sin marcado, el confinamiento del odontólogo y el aislamiento por clínica.

#### Scenario: Suite del panel pasa

- **WHEN** se ejecuta `pytest` y `vitest`
- **THEN** pasan los tests del panel del día y de su interfaz
