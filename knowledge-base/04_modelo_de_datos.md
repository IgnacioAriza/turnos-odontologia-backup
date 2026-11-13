# Modelo de Datos

## Dominios

- **Clínica**: 1 clínica en v1 (`clinic_id` omnipresente como preparación, no como feature).
- **Personas**: pacientes (con/sin cuenta), usuarios internos (recepción/odontólogo/admin).
- **Recursos**: sillones, odontólogos, tipos de práctica, aranceles.
- **Turnos**: reserva, estados, reprogramación, faltas/bloqueos.
- **Pagos**: seña % MP, estados, webhook idempotente.
- **Notificaciones**: recordatorio WA 24hs (un envío) + respaldo email/Calendar.

## ERD (textual)

```
Clinic 1──* Sillon | Clinic 1──* User (rol: recepcion/odonto/admin)
User(odonto) 1──* Turno | Sillon 1──* Turno | Paciente 1──* Turno
TipoPractica 1──* Turno | TipoPractica 1──1 Arancel (% seña, precio)
Turno 1──* Pago (seña) | Turno 1──* Notificacion | Paciente 1──* Bloqueo
Paciente *──* User (v1.1, login opcional → historial)

Constraints clave: UNIQUE (sillon_id, inicio, fin) anti-solape + UNIQUE (odontologo_id, inicio, fin);
CHECK (fin > inicio); EXCLUDE por rango si Postgres range (recomendado).
```

## Entidades

### Clinic
- Atributos: `id (uuid/pk)`, `nombre`, `timezone="America/Argentina/Buenos_Aires"`, `wa_sender`, `mp_account`, `activa`.
- Relaciones: 1──* Sillon, User, TipoPractica, Turno (vía `clinic_id` en todas).
- Índices: `pk(id)`.
- **Suposición:** `clinic_id` obligatorio en todas las tablas de negocio desde día 1 aunque v1 sea 1 clínica (ver DD-06).

### User (interno + login paciente v1.1)
- Atributos: `id`, `clinic_id (fk)`, `email UNIQUE`, `password_hash`, `rol: recepcion|odonto|admin|paciente`, `nombre`, `activo`, `created_at`.
- Relaciones: Odontólogo User──* Turno; Paciente User──1 Paciente (v1.1, nullable).
- Constraints: email único por clínica; rol inmutable salvo admin.

### Paciente
- Atributos: `id`, `clinic_id`, `nombre`, `telefono (E.164 AR, índice)`, `dni (nullable, índice)`, `user_id (nullable, v1.1)`, `faltas_count`, `bloqueado_hasta (nullable)`, `created_at`.
- Relaciones: 1──* Turno, 1──* Bloqueo.
- Índices: `(clinic_id, telefono)`, `(clinic_id, dni)`.

### Sillon
- Atributos: `id`, `clinic_id`, `nombre ("Sillón 1")`, `activo`.
- Relaciones: 1──* Turno.

### TipoPractica
- Atributos: `id`, `clinic_id`, `nombre`, `duracion_min`, `precio_base`, `sena_pct (configura Admin)`, `activa`.
- Relaciones: 1──* Turno; 1──1 Arancel.
- Constraints: `sena_pct BETWEEN 0 AND 100`; `duracion_min > 0`.

### Arancel (lectura v1.0, CRUD v1.1)
- Atributos: `id`, `tipo_practica_id (fk UNIQUE)`, `precio`, `sena_pct`, `vigente_desde`.
- Relaciones: *──1 TipoPractica.

### Turno
- Atributos: `id`, `clinic_id`, `paciente_id`, `sillon_id`, `odontologo_id (User)`, `tipo_practica_id`, `inicio (timestamptz)`, `fin`, `estado: pendiente_sena|confirmado|cancelado|reprogramado|completado|ausente`, `manage_token (UNIQUE, público)`, `reprogramaciones_count DEFAULT 0`, `monto_sena`, `created_at`.
- Relaciones: *──1 cada fk; 1──* Pago, Notificacion.
- Constraints: `fin > inicio`; anti-solape sillón y odontólogo (EXCLUDE USING gist con tstzrange o UNIQUE + validación transaccional); `inicio` en zona horaria clínica.
- Índices: `(clinic_id, inicio)`, `(sillon_id, inicio)`, `(odontologo_id, inicio)`, `(paciente_id, inicio)`, `(estado)`.

### Pago (seña MP)
- Atributos: `id`, `turno_id`, `mp_payment_id (UNIQUE, nullable hasta webhook)`, `mp_preference_id`, `monto`, `moneda="ARS"`, `estado: pendiente|aprobado|rechazado|reembolsado`, `idempotency_key (UNIQUE)`, `raw_webhook (jsonb)`, `created_at`.
- Relaciones: *──1 Turno.
- Constraints: un solo `aprobado` vigente por turno (índice parcial).

### Notificacion
- Atributos: `id`, `turno_id`, `canal: whatsapp|email`, `tipo: confirmacion|recordatorio_24h`, `proveedor="twilio"`, `provider_sid (nullable)`, `estado: encolado|enviado|entregado|fallido`, `scheduled_for`, `sent_at`.
- Constraints: un solo `recordatorio_24h` whatsapp por turno (índice parcial UNIQUE).

### Bloqueo
- Atributos: `id`, `clinic_id`, `paciente_id`, `motivo="2_faltas"`, `desde`, `hasta (+30 días)`, `created_by`, `is_active`.
- Relaciones: *──1 Paciente, *──1 Clinic.
- Regla (C-07): al crear el bloqueo, `Paciente.faltas_count` vuelve a `0` para que "2 faltas" signifique "2 faltas desde el último bloqueo". Si el paciente vuelve a acumular dos faltas estando bloqueado, se registra un nuevo `Bloqueo` y `bloqueado_hasta` se extiende a `now + 30 días` desde esa última falta.

### ExcepcionBloqueo
- Atributos: `id`, `clinic_id`, `paciente_id`, `turno_id (UNIQUE)`, `usuario_id`, `motivo`, `created_at`, `is_active`.
- Relaciones: *──1 Clinic, *──1 Paciente, *──1 Turno, *──1 User.
- Regla (C-07, RN-AUS-02): una fila por turno creado con `motivo_excepcion`; registra quién autorizó reservar a un paciente bloqueado y por qué. Se escribe en la misma transacción que el turno (migración 007).

## Seed data inicial

- 1 `Clinic` (nombre real, timezone AR, `wa_sender` Twilio, cuenta MP).
- Roles/usuarios: 1 admin, 1 recepción, N odontólogos con sillón asignado.
- 2-3 `Sillon` activos; `TipoPractica` base (limpieza, arreglo, endodoncia, extracción, ortodoncia control) con `duracion_min`, `precio_base`, `sena_pct` inicial.
- Horarios de atención por sillón/odontólogo (tabla o config — definir en diseño; ver `10_preguntas_abiertas.md`).
