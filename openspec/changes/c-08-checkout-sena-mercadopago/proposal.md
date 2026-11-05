# Proposal — C-08 checkout-sena-mercadopago

## Why

C-08 es el cambio de checkout de seña % con Mercado Pago REAL en el camino crítico (`C-01 → C-02 → C-03 → C-04 → C-05 → C-08 → C-09 → C-10`). Depende de C-05 (motor de reservas con turno en `pendiente_sena` y `monto_sena` fotografiado). Sin C-08 no hay pago de seña, por lo que no hay confirmación de turno, no hay recordatorio WA T-24hs (C-10), y el MVP no es lanzable.

## What Changes

### Backend — checkout de seña MP
- `mp_client` en `app/infrastructure/integrations/`: cliente de Mercado Pago SDK para crear preferences.
- `POST /api/public/reservas/{id}/pagar`: crea preference MP con:
  - `external_reference = turno_id`
  - `metadata = {clinic_id, turno_id, idempotency_key}`
  - `monto_sena` exacto fotografiado del turno (ARS)
  - `MP_TTL_MIN` para expiración de la preference
- Estados de pago: `pendiente` / `aprobado` / `rechazado`.
- Un solo `aprobado` vigente por turno (índice parcial en tabla `pagos`).
- Reintento de pago: genera preference nueva sin duplicar turno.
- Env vars: `MP_ACCESS_TOKEN`, `MP_WEBHOOK_SECRET`, `MP_TTL_MIN` (nunca hardcodeadas).

### Frontend — pantalla checkout
- Pantalla de checkout con redirección a MP.
- Estado de pago (pendiente/aprobado/rechazado).
- Botón de reintento de pago.

### Tests
- Monto exacto según RN-PAGO-02 (foto del monto, no se recalcula).
- Cambios de arancel no alteran turnos existentes.
- Reintento genera preference nueva sin duplicar turno.

## Capabilities

### New Capabilities
- `pagos/checkout`: creación de preference MP para seña %.
- `pagos/estado`: seguimiento de estados de pago (pendiente/aprobado/rechazado).
- `pagos/idempotencia`: un solo pago aprobado vigente por turno.
- `frontend/checkout`: pantalla de pago con redirección MP y estado.

### Modified Capabilities
- `domain/turnos`: `Turno.monto_sena` ya existe (C-05); se usa como foto del monto de seña.
- `infrastructure/integrations`: se añade `mp_client`.

## Impact

- **Code:** Nueva integración con Mercado Pago SDK. Endpoint público de pago. Tabla `pagos` (C-09 crea la tabla; C-08 define el contrato de preference).
- **APIs:** `POST /api/public/reservas/{id}/pagar` (público, sin JWT).
- **Dependencies:** Mercado Pago SDK (ya en C-01 como dependencia opcional).
- **Systems:** Mercado Pago sandbox para tests; MP real en producción.
- **Configuration:** `MP_ACCESS_TOKEN`, `MP_WEBHOOK_SECRET`, `MP_TTL_MIN` via env vars (nunca en repo).

## Dependencies

- C-05 `motor-reservas-slots-turnos` (turno con `pendiente_sena` y `monto_sena`).
- C-01 `foundation-setup` (infraestructura base).

## Leer antes

- `knowledge-base/11_pagos_mercadopago.md` §Configuración
- `knowledge-base/05_reglas_de_negocio.md` §Dominio: Pagos (RN-PAGO-01..04)
- `knowledge-base/06_funcionalidades.md` §US-007
- `knowledge-base/08_arquitectura_propuesta.md` §Variables de entorno
- `docs/skills-mcp/revision-pagos-seguridad.md` (reporte de la skill propia `pagos-seguridad-review` sobre C-08)

## Open Questions

- ¿Usar MP sandbox o production para tests de C-08? (definir en diseño)
- URL de webhook MP en entorno local (ngrok o similar).
