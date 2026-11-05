# Reporte de revisión de seguridad de pagos — C-08 checkout-sena-mercadopago

Generado por la skill propia `pagos-seguridad-review` (ubicada en `skills/pagos-seguridad-review/SKILL.md`).
Metodología aplicada: 6 pasos del skill-creator (capturar intención → leer fundación → extraer reglas → detectar ambigüedades → detectar casos de borde → generar escenarios verificables → producir reporte).

Fuentes consultadas mediante MCP filesystem (`read_text_file` sobre `knowledge-base/`):
- `knowledge-base/11_pagos_mercadopago.md`
- `knowledge-base/05_reglas_de_negocio.md`
- `knowledge-base/08_arquitectura_propuesta.md`
- `CHANGES.md` (alcance y dependencias de C-08)

---

## Resumen ejecutivo

- Cambio revisado: **C-08 `checkout-sena-mercadopago`**
- Reglas de seguridad encontradas: 8 (RN-PAGO-01..04, reglas de env vars, regla dura 9, reglas de webhook)
- Reglas ambiguas detectadas: 4
- Casos de borde faltantes: 5
- Escenarios verificables generados: 3 (funcionamiento esperado, error de negocio, caso de borde)

---

## Reglas de seguridad extraídas (aplicables a C-08)

| ID | Texto | Entidades | Estado |
|---|---|---|---|
| RN-PAGO-01 | Seña en % del precio según TipoPractica.sena_pct | TipoPractica, Turno | Relevante (C-04, C-08) |
| RN-PAGO-02 | monto_sena = round(precio_base * sena_pct / 100) al crear reserva (foto del monto) | Turno, TipoPractica | Relevante (C-02, C-05, C-08) |
| RN-PAGO-03 | Webhook MP idempotente (mp_payment_id / idempotency_key UNIQUE) | Pago, Webhook | Relevante (C-08, C-09) |
| RN-PAGO-04 | Un solo pago aprobado vigente por turno | Pago, Turno | Relevante (C-08, C-09) |
| Regla dura 9 | Secrets/Infra — NUNCA hardcodear → Pydantic settings, 12 env vars, nunca en repo | Todos | Relevante (C-08) |
| Regla webhook | Solo estado=aprobado confirma el turno (pendiente_sena → confirmado) | Turno, Pago | Relevante (C-08, C-09) |

---

## Reglas ambiguas detectadas

| Regla | Problema | Ejemplo de interpretación alternativa | Sugerencia |
|---|---|---|---|
| RN-PAGO-02 | "foto del monto" no especifica redondeo (round vs floor vs ceil) ni moneda | ¿monto_sena se guarda en ARS con 2 decimales? | Especificar `round()` aritmético y 2 decimales en ARS. |
| Regla dura 9 | "nunca en repo" no especifica qué hacer si un desarrollador commitea un .env con token | ¿Se usa pre-commit hook? ¿Se escanea en CI? | Agregar pre-commit o escaneo de secrets en CI. |
| Regla webhook | "valida firma" no especifica qué algoritmo de firma MP usa | ¿HMAC-SHA256? ¿Header específico? | Documentar algoritmo y header de firma MP. |
| RN-PAGO-04 | "Un solo pago aprobado vigente por turno" no especifica qué pasa con pagos rechazados previos | ¿Se borran rechazados? ¿Se mantienen? | Especificar ciclo de vida de pagos rechazados. |

---

## Casos de borde faltantes

| Caso | ¿Cubierto por regla existente? | Requerimiento de seguridad |
|---|---|---|
| Webhook MP duplicado | Parcial — RN-PAGO-03 menciona idempotencia | No hay regla explícita de 200 sin efectos para webhook duplicado. |
| Firma MP inválida | No | Falta regla de rechazo 401 ante firma inválida. |
| MP_ACCESS_TOKEN hardcodeado | No — regla dura 9 lo prohíbe pero no hay detección | Falta mecanismo de detección (pre-commit/CI scan). |
| Monto de seña recalculado al pagar | No — RN-PAGO-02 dice foto, pero no hay regla que impida recalcular | Falta regla de que checkout usa monto_sena fotografiado, no recalculado. |
| Dos pagos aprobados por turno | Parcial — RN-PAGO-04 lo prohíbe | Falta índice parcial en tabla `pagos` (C-09) para enforzarlo en BD. |

---

## Escenarios verificables (generados para C-08)

### Escenario 1 — Funcionamiento esperado: preference MP con monto exacto

- **Contexto:** Turno en `pendiente_sena` con `monto_sena = 2000` (ARS), `precio_base = 10000`, `sena_pct = 20`.
- **Acción:** `POST /api/public/reservas/{turno_id}/pagar` crea preference MP.
- **Resultado esperado:** Preference creada con `monto = 2000`, `moneda = ARS`, `external_reference = turno_id`, `metadata = {clinic_id, turno_id, idempotency_key}`.
- **Regla de referencia:** RN-PAGO-02, `11_pagos_mercadopago.md` §Configuración.
- **Verificable:** sí — test verifica que la preference tenga monto correcto y metadata completa.

### Escenario 2 — Error de negocio: turno ya confirmado

- **Contexto:** Turno ya tiene `estado = confirmado` (pago aprobado previo).
- **Acción:** `POST /api/public/reservas/{turno_id}/pagar` intenta crear nueva preference.
- **Resultado esperado:** Endpoint rechaza con `409 Conflict` (turno ya confirmado, no se permite segundo pago).
- **Regla de referencia:** RN-PAGO-04, RN-RES-05.
- **Verificable:** sí — test espera respuesta 409 y que no se cree preference duplicada.

### Escenario 3 — Caso de borde: secreto MP expuesto en código

- **Contexto:** Se busca en el código fuentes strings tipo `APP_USR-` o `TEST-` (patrón de token MP).
- **Acción:** Test de escaneo de secrets sobre `app/infrastructure/integrations/mp_client.py` y `app/api/public/pagos.py`.
- **Resultado esperado:** Test falla si encuentra cualquier hardcodeo de token; pasa solo si los tokens vienen de `os.getenv` / Pydantic settings.
- **Regla de referencia:** Regla dura 9 (secrets/infra), `08_arquitectura_propuesta.md` §Variables de entorno.
- **Verificable:** sí — test automatizado escanea código fuentes y falla si encuentra secretos hardcodeados.

---

## Recomendaciones para el spec de C-08

1. En `design.md`, especificar que `monto_sena` es una foto del monto al crear el turno; C-08 no lo recalcula (RN-PAGO-02).
2. Especificar que `MP_ACCESS_TOKEN`, `MP_WEBHOOK_SECRET`, `MP_TTL_MIN` vienen solo de env vars (regla dura 9).
3. Agregar regla de seguridad explícita: "Webhook MP con firma inválida rechaza con 401".
4. Agregar regla de seguridad explícita: "Webhook MP duplicado (mp_payment_id existente) devuelve 200 sin efectos" (RN-PAGO-03).
5. Considerar pre-commit o CI scan para detectar secretos hardcodeados.

---

## Evidencia de uso de la skill y el MCP

- **Skill propia:** `pagos-seguridad-review` aplicada siguiendo su SKILL.md (6 pasos). Reporte generado en este archivo.
- **MCP:** Servidor `mcp-server-filesystem` ejecutado vía npx; herramientas `read_text_file` y `list_directory` invocadas sobre archivos de pagos (`11_pagos_mercadopago.md`, `05_reglas_de_negocio.md`, `08_arquitectura_propuesta.md`, `CHANGES.md`, `backend/app/domain/pagos/`, `backend/app/api/webhooks/`). Evidencia en `docs/skills-mcp/evidencias/mcp-evidencia-c08.md`.
- **Defecto detectado y corregido:** En el `design.md` inicial de C-08 se mencionaba la tabla `pagos` como parte de C-08, pero `pagos` se crea en C-09. Corregido para dejar claro que C-08 solo define el contrato de preference MP.
- **Defecto en el MCP:** el script de prueba intentó escribir la evidencia en el Desktop (ruta anterior del proyecto). Se corrigió la ruta para escribir en el repo correcto (`Documents\GitHub\turnos-odontologia\docs\skills-mcp\evidencias\`).
