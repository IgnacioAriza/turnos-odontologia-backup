# Spec Delta — motor-turnos

## MODIFIED Requirements

### Requirement: Bloqueo por faltas

El backend SHALL rechazar la creación de reservas de un paciente con `bloqueado_hasta` posterior al momento actual, respondiendo 403 con `codigo=bloqueado` y `bloqueado_hasta` en ISO-8601; el alta interna SHALL admitir una excepción con motivo auditado.

#### Scenario: Paciente bloqueado

- **WHEN** un paciente con `bloqueado_hasta` futuro intenta reservar por el canal público o interno sin motivo de excepción
- **THEN** recibe 403 con `codigo=bloqueado` y la fecha de desbloqueo en `bloqueado_hasta`, y no se crea ningún turno

#### Scenario: Paciente habilitado

- **WHEN** `bloqueado_hasta` es nulo o anterior al momento de la reserva
- **THEN** la reserva se permite sin exigir motivo

#### Scenario: Excepción interna con motivo

- **WHEN** recepción crea un turno para un paciente bloqueado enviando un `motivo_excepcion` no vacío
- **THEN** el turno se crea y la excepción queda registrada con el motivo y el usuario

#### Scenario: El motivo no habilita el canal público

- **WHEN** una reserva pública incluye un motivo de excepción en el cuerpo
- **THEN** el backend lo ignora y responde 403 `codigo=bloqueado`

#### Scenario: Bloqueo vencido

- **WHEN** el paciente tuvo un bloqueo que ya venció
- **THEN** puede reservar por ambos canales y no se crea una excepción
