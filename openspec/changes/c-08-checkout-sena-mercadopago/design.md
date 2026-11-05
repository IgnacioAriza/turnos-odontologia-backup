# Design — C-08 checkout-sena-mercadopago

## Context

C-05 ya tiene el modelo `Turno` con estado `pendiente_sena` y `monto_sena` (foto del monto de seña). C-08 añade el checkout real con Mercado Pago: crea una preference de pago, el paciente paga, y el webhook (C-09) confirma el turno. C-08 solo crea la preference y el endpoint de pago; C-09 crea la tabla `pagos` y el webhook.

## Goals / Non-Goals

**Goals:**
- `mp_client` en `app/infrastructure/integrations/` para crear preferences MP.
- `POST /api/public/reservas/{id}/pagar` — crea preference MP con `external_reference=turno_id`, `metadata={clinic_id, turno_id, idempotency_key}`, `monto_sena` exacto, moneda ARS.
- Estados de pago: `pendiente` / `aprobado` / `rechazado`.
- Un solo `aprobado` vigente por turno (índice parcial, se define en C-09).
- Reintento de pago: preference nueva, sin duplicar turno.
- Env vars: `MP_ACCESS_TOKEN`, `MP_WEBHOOK_SECRET`, `MP_TTL_MIN` (nunca hardcodeadas).
- Frontend: pantalla checkout con redirección MP, estado de pago, botón reintento.
- Tests: monto exacto RN-PAGO-02, arancel no altera turnos existentes, reintento sin duplicar turno.

**Non-Goals:**
- No webhook MP (C-09).
- No tabla `pagos` (C-09).
- No lógica de reembolso (C-09/C-13).
- No login de pagos (reserva pública sigue sin login).

## Decisions

### 1. `monto_sena` como foto del monto (RN-PAGO-02)
**Decision:** `monto_sena = round(precio_base * sena_pct / 100)` se fotografía al crear el turno (C-05). C-08 usa ese valor fotografiado para la preference MP; no lo recalcula.

**Rationale:** Cambios posteriores de arancel no deben alterar turnos existentes (RN-PAGO-02).

**Alternatives:** Recalcular monto al pagar (rechazado: rompería la foto de precio).

### 2. Preference MP con metadata de idempotencia
**Decision:** La preference incluye `metadata = {clinic_id, turno_id, idempotency_key}` donde `idempotency_key` es un UUID generado por reserva.

**Rationale:** Permite rastrear el pago y evitar duplicados en el webhook (C-09).

**Alternatives:** Sin metadata (rechazado: dificultaría la conciliación).

### 3. Un solo `aprobado` vigente por turno
**Decision:** Se define en C-09 como índice parcial en tabla `pagos`. C-08 respeta este contrato: solo crea preference; no permite dos pagos aprobados.

**Rationale:** RN-PAGO-04.

**Alternatives:** Múltiples aprobados (rechazado: ambiguity en estado de turno).

### 4. Secretos solo por env vars
**Decision:** `MP_ACCESS_TOKEN`, `MP_WEBHOOK_SECRET`, `MP_TTL_MIN` se leen solo de variables de entorno. Nunca se hardcodean en código ni en specs.

**Rationale:** Regla dura 9 del proyecto (secrets/Infra).

**Alternatives:** Archivo de config en repo (rechazado: expone secretos).

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| MP sandbox no disponible en CI | Usar mock de mp_client en tests; marcar como integración que requiere MP real |
| Preference expirada antes de pagar | `MP_TTL_MIN=30`; job de expiración libera slot (C-05) |
| Webhook MP llega antes de que frontend redirija | C-09 maneja estado independiente del frontend |
| Doble pago por race condition | Índice parcial en `pagos` (C-09) + idempotency_key |

## Migration Plan

1. Crear `app/infrastructure/integrations/mp_client.py` (cliente MP SDK).
2. Crear `app/api/public/pagos.py` con endpoint `POST /api/public/reservas/{id}/pagar`.
3. Agregar router `pagos` a `app/api/public/__init__.py`.
4. Crear pantalla checkout en frontend (`features/booking/checkout/`).
5. Escribir tests (monto exacto, reintento, arancel no altera turnos).
6. Correr `ruff check`, `ruff format --check`, `mypy`, `pytest`.

**Rollback:** Eliminar archivos creados; no hay migración de BD en C-08 (tabla `pagos` viene en C-09).

## Open Questions

- MP sandbox vs production para tests de integración.
- URL de callback webhook en desarrollo local.
