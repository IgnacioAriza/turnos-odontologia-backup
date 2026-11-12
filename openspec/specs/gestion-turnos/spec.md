# Spec — gestion-turnos

## Purpose

Define cómo un paciente con su `manage_token` y cómo la recepción con JWT cancelan o reprograman un turno, qué pasa con la seña en cada caso y cómo se libera el horario para re-reservarlo.

## Requirements

### Requirement: Ventana de gestión de 12 horas

El sistema SHALL comparar `inicio - now()` contra 12 horas en `America/Argentina/Buenos_Aires` antes de ejecutar una cancelación o reprogramación sin pérdida de seña.

#### Scenario: Gestión dentro de la ventana

- **WHEN** el turno empieza en 30 horas y el paciente pide cancelar
- **THEN** la operación se ejecuta sin pedir confirmación adicional por pérdida de seña

#### Scenario: Gestión dentro de las 12 horas

- **WHEN** el turno empieza en 5 horas y el paciente pide cancelar
- **THEN** la respuesta es 409 con `codigo=requiere_confirmacion` y `perdida_sena=true`, y el turno no cambia

#### Scenario: Límite exacto de la ventana

- **WHEN** el turno empieza exactamente en 12 horas
- **THEN** la operación se considera dentro de la ventana y se ejecuta sin pérdida de seña

### Requirement: Cancelación con liberación inmediata del horario

El sistema SHALL pasar el turno a `cancelado` al confirmarse la cancelación y SHALL liberar el horario para que vuelva a ofrecerse en `GET /api/public/slots`.

#### Scenario: Horario liberado

- **WHEN** se cancela un turno confirmado de 10:00 a 10:30
- **THEN** el turno queda en `cancelado` y el slot de las 10:00 vuelve a aparecer como disponible

#### Scenario: Re-reserva del horario liberado

- **WHEN** otro paciente reserva el mismo horario después de la cancelación
- **THEN** la reserva se crea con 201 y sin conflicto de solape

#### Scenario: Cancelación de un turno pendiente de seña

- **WHEN** se cancela un turno en `pendiente_sena` que todavía no pagó
- **THEN** el turno queda en `cancelado`, la seña no se marca como perdida y el horario se libera

### Requirement: Pérdida de seña por cancelación tardía

El sistema SHALL permitir la cancelación dentro de las 12 horas solo con confirmación explícita, y en ese caso SHALL registrar la seña como no reembolsable.

#### Scenario: Cancelación tardía confirmada

- **WHEN** el paciente cancela a 5 horas del inicio enviando `confirmar_perdida_sena=true`
- **THEN** el turno queda en `cancelado` con `sena_perdida=true` y el horario se libera

#### Scenario: Pérdida de seña sin pago aprobado

- **WHEN** el turno nunca recibió una seña aprobada
- **THEN** la cancelación tardía no marca `sena_perdida` y no genera obligación de reembolso

### Requirement: Primera reprogramación conserva la seña

El sistema SHALL mover el turno a un horario libre dentro de la ventana sin cambiar `turno_id` ni `monto_sena`, e incrementando `reprogramaciones_count` a 1.

#### Scenario: Reprogramación con seña migrada

- **WHEN** un turno confirmado con `reprogramaciones_count=0` y `monto_sena=2000` se reprograma a un slot libre
- **THEN** el mismo turno queda con el nuevo `inicio`, `monto_sena=2000` y `reprogramaciones_count=1`

#### Scenario: Reprogramación a un horario ocupado

- **WHEN** el paciente elige un horario que ya está tomado
- **THEN** la respuesta es 409 con `codigo=solape` y el turno conserva su horario original

#### Scenario: Reprogramación en las dos direcciones de la ventana

- **WHEN** el turno original o el horario nuevo quedan a menos de 12 horas
- **THEN** la respuesta es 409 con `codigo=requiere_confirmacion` y `perdida_sena=true`

### Requirement: Segunda reprogramación exige seña nueva

El sistema SHALL rechazar una segunda reprogramación sin pérdida de seña, y con confirmación explícita SHALL cerrar el turno anterior como `cancelado` con la seña perdida y crear un turno nuevo en `pendiente_sena`.

#### Scenario: Segunda reprogramación sin confirmación

- **WHEN** un turno con `reprogramaciones_count=1` pide reprogramarse sin `confirmar_perdida_sena`
- **THEN** la respuesta es 409 con `codigo=requiere_nueva_sena` y no se crea ni modifica ningún turno

#### Scenario: Segunda reprogramación confirmada

- **WHEN** el mismo turno se reprograma enviando `confirmar_perdida_sena=true`
- **THEN** el turno anterior queda en `cancelado` con `sena_perdida=true`, el horario original se libera y se crea un turno nuevo en `pendiente_sena` con `reprogramado_de_id` apuntando al anterior, `reprogramaciones_count=1`, `monto_sena` recalculado y `manage_token` propio

#### Scenario: Seña nueva no pagada

- **WHEN** el turno creado por la segunda reprogramación no se paga dentro del TTL
- **THEN** expira igual que cualquier `pendiente_sena` y el horario se libera

### Requirement: Gestión pública por token de gestión

El sistema SHALL exponer la vista y las acciones de gestión del turno a quien presente su `manage_token`, sin requerir JWT y sin aceptar el token por query string.

#### Scenario: Vista del turno con token válido

- **WHEN** se consulta el turno con su `manage_token`
- **THEN** la respuesta incluye estado, inicio, fin, práctica, `monto_sena` y `reprogramaciones_count`, sin datos de otros pacientes ni el token

#### Scenario: Token inválido

- **WHEN** se consulta o se intenta gestionar con un token que no corresponde
- **THEN** la respuesta es 403 y nunca 401

#### Scenario: Turno inexistente o de otra clínica

- **WHEN** se consulta un turno que no existe
- **THEN** la respuesta es 404 sin revelar si el identificador existe en otra clínica

#### Scenario: Token fuera de caché

- **WHEN** se sirve la vista del turno por token
- **THEN** la respuesta lleva `Cache-Control: no-store`

#### Scenario: Token no aparece en logs

- **WHEN** se registra cualquier request de gestión
- **THEN** el log contiene el `turno_id` y no el `manage_token`

### Requirement: Estados de turno no gestionables

El sistema SHALL rechazar toda cancelación o reprogramación sobre turnos en estado final, sin alterar el registro.

#### Scenario: Turno ya cancelado

- **WHEN** se intenta cancelar o reprogramar un turno en `cancelado`
- **THEN** la respuesta es 409 con `codigo=estado_no_gestionable`

#### Scenario: Turno completado o ausente

- **WHEN** se intenta gestionar un turno en `completado` o `ausente`
- **THEN** la respuesta es 409 con `codigo=estado_no_gestionable`

### Requirement: Gestión interna por recepción

El sistema SHALL permitir cancelar y reprogramar por canal interno a roles `recepcion` y `admin` con JWT, sin `manage_token`, exigiendo un `motivo` y aplicando las mismas reglas de ventana y solape.

#### Scenario: Recepción cancela un turno

- **WHEN** un usuario con rol `recepcion` cancela un turno con `motivo` no vacío
- **THEN** el turno se cancela y el motivo queda registrado en el log de dominio con `turno_id`, `clinic_id` y `usuario_id`

#### Scenario: Cancelación interna sin motivo

- **WHEN** la recepción intenta cancelar sin `motivo`
- **THEN** la respuesta es 422 y el turno no cambia

#### Scenario: Rol sin permiso

- **WHEN** un usuario con rol `odonto` llama a la gestión interna
- **THEN** la respuesta es 403

#### Scenario: Turno de otra clínica

- **WHEN** la recepción intenta gestionar un turno de otra clínica
- **THEN** la respuesta es 404 y no se modifica nada

### Requirement: Señal para cancelar el recordatorio programado

El sistema SHALL emitir la señal de cancelación o reprogramación del recordatorio del turno para que la capa de notificaciones cancele el job de T-24hs.

#### Scenario: Señal al cancelar

- **WHEN** un turno se cancela
- **THEN** se emite la señal de cancelación del recordatorio asociado a ese turno

#### Scenario: Señal al reprogramar

- **WHEN** un turno se reprograma
- **THEN** se emite la señal de reprogramación con el nuevo `inicio`

#### Scenario: Notificaciones todavía no implementadas

- **WHEN** el adaptador de notificaciones es el no-op de v1.0
- **THEN** la gestión del turno se completa igual, sin error

### Requirement: Migración 006 de gestión de turnos

La migración `006_gestion_turnos` SHALL agregar `sena_perdida` y `reprogramado_de_id` a `turnos` sin reutilizar la revisión `005`.

#### Scenario: Upgrade agrega las columnas

- **WHEN** `alembic upgrade head` corre sobre una base en revisión 005
- **THEN** `turnos` tiene `sena_perdida` con default `false` y `reprogramado_de_id` nulo con FK a `turnos.id`

#### Scenario: Downgrade revierte las columnas

- **WHEN** `alembic downgrade -1` corre desde 006
- **THEN** ambas columnas se eliminan y la base vuelve a 005

### Requirement: Límite de intentos en el canal público de gestión

El sistema SHALL limitar los intentos de gestión pública por IP y por token para dificultar la adivinación de tokens.

#### Scenario: Intentos por encima del límite

- **WHEN** una misma IP supera el límite configurado de intentos de gestión en la ventana
- **THEN** la respuesta es 429 con `Retry-After`

### Requirement: Cobertura de tests de gestión de turnos

La suite SHALL cubrir la ventana de 12hs en sus dos límites, la migración de seña, la segunda reprogramación, la pérdida de seña, el token inválido, la liberación del horario, el RBAC interno, el aislamiento por clínica y la redacción del token en logs.

#### Scenario: Suite de gestión pasa

- **WHEN** se ejecuta `pytest`
- **THEN** pasan los tests de gestión, de la migración 006 y de los clientes públicos
