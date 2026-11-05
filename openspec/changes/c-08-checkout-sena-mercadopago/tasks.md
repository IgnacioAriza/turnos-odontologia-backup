# Tasks — C-08 checkout-sena-mercadopago

## 1. Integración Mercado Pago

- [ ] 1.1 Crear `app/infrastructure/integrations/mp_client.py`: cliente SDK MP para crear preference (`create_preference`) con `external_reference`, `metadata`, `monto_sena`, moneda ARS, `MP_TTL_MIN`.
- [ ] 1.2 Crear `app/api/public/pagos.py` con endpoint `POST /api/public/reservas/{id}/pagar`:
  - Valida que el turno exista y esté en `pendiente_sena`.
  - Crea preference MP con `external_reference=turno_id`, `metadata={clinic_id, turno_id, idempotency_key}`, `monto_sena` (foto del turno).
  - Retorna `preference_id` y `init_point` (URL de pago MP).
- [ ] 1.3 Agregar router `pagos` a `app/api/public/__init__.py` con prefijo `/api/public`.
- [ ] 1.4 Verificar imports: `from app.api.public import pagos` funciona.

## 2. Frontend checkout

- [ ] 2.1 Crear `features/booking/checkout/` con pantalla de pago (redirección MP, estado pendiente/aprobado/rechazado, botón reintento).
- [ ] 2.2 Conectar con endpoint `POST /api/public/reservas/{id}/pagar`.
- [ ] 2.3 Verificar navegación desde `/reservar` a `/checkout/:turno_id`.

## 3. Tests (TDD — RED primero)

### 3.1 Test: monto exacto según RN-PAGO-02
- **Escenario 1 — Funcionamiento esperado:** Turno con `precio_base=10000`, `sena_pct=20`, `monto_sena=2000`. Preference MP creada con monto=2000 ARS.
- **Escenario 2 — Error de negocio:** Turno con `monto_sena=0` (sena_pct=0). Preference con monto=0 (válido, seña 0%).
- **Escenario 3 — Caso de borde:** Cambiar arancel de la práctica DESPUÉS de crear el turno. El checkout sigue usando `monto_sena` fotografiado (2000), no el nuevo precio.

### 3.2 Test: reintento de pago sin duplicar turno
- **Escenario 1 — Funcionamiento esperado:** Usuario paga, preference expira, hace reintento → se crea preference nueva con mismo `turno_id` pero diferente `idempotency_key`. Turno no se duplica.
- **Escenario 2 — Error de negocio:** Dos preferences activas para el mismo turno (una expirada, una activa). Solo la activa se usa para pagar.
- **Escenario 3 — Caso de borde:** Pago aprobado en preference antigua, luego se intenta reintento en preference nueva → el turno ya está `confirmado`, endpoint rechaza con 409.

### 3.3 Test: secretos no hardcodeados
- **Escenario 1 — Funcionamiento esperado:** `mp_client` lee `MP_ACCESS_TOKEN` de `os.getenv` / Pydantic settings. No hay strings de token en el código.
- **Escenario 2 — Error de negocio:** Test busca en código fuentes strings tipo `APP_USR-` o `TEST-` (patrón de token MP) y falla si encuentra alguno.
- **Escenario 3 — Caso de borde:** `MP_ACCESS_TOKEN` vacío → endpoint de pago devuelve error de configuración (500) sin exponer el token.

## 4. Verificación de calidad

- [ ] 4.1 `ruff check backend/app` limpio.
- [ ] 4.2 `ruff format --check backend/app` limpio.
- [ ] 4.3 `mypy backend/app` limpio.
- [ ] 4.4 `pytest backend/app --cov=app --cov-fail-under=80` pasa completo.

## 5. Workflow follow-up

- [ ] No marcar C-08 como implementado/verificado/archivado (queda preparado para implementar en instancia posterior).
- [ ] Referenciar C-08 en CHANGES.md como preparado (no marcar `[x]`).

## Escenarios verificables (resumen para el spec)

| # | Tipo | Contexto | Acción | Resultado esperado | Regla de referencia |
|---|------|----------|--------|-------------------|--------------------|
| 1 | Funcionamiento esperado | Turno pendiente_sena con monto_sena=2000 | POST /pagar crea preference MP | Preference con monto=2000 ARS, external_reference=turno_id | RN-PAGO-02, 11_pagos_mercadopago.md |
| 2 | Error de negocio | Turno ya confirmado (pago aprobado previo) | POST /pagar intenta nueva preference | Endpoint rechaza con 409 (turno ya confirmado) | RN-PAGO-04, RN-RES-05 |
| 3 | Caso de borde | Secreto MP_ACCESS_TOKEN hardcodeado en código | Test de búsqueda de patrones de token | Test falla (secreto expuesto detectado) | Regla dura 9 (secrets/infra) |
