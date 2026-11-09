---
name: pagos-seguridad-review
description: "Revisa la seguridad de pagos y señas con Mercado Pago antes de implementar o revisar un change: detecta reglas RN-PAGO ambiguas, casos de borde de webhooks, idempotencia, montos fotografiados y secretos, y genera escenarios verificables para el spec SDD. Usá esta skill siempre que prepares o revises C-08 (checkout de seña) o C-09 (webhook y conciliación), toques la integración MP, definas montos de seña, idempotencia o firma de webhook, manejes credenciales MP_ACCESS_TOKEN / MP_WEBHOOK_SECRET, o necesites escenarios de prueba de seguridad de pagos. Lee knowledge-base/11_pagos_mercadopago.md, 05_reglas_de_negocio.md y 08_arquitectura_propuesta.md, y produce un reporte estructurado listo para proposal.md/design.md/tasks.md."
compatibility: "Proyecto turnos-odontologia (Python/FastAPI + PostgreSQL + Redis). Requiere acceso a knowledge-base/ y CHANGES.md del repo. No llama a la API de Mercado Pago ni necesita sandbox: trabaja sobre la documentación y el código local."
---

# pagos-seguridad-review — Skill de revisión de seguridad de pagos

## Propósito

Esta skill revisa de forma sistemática la seguridad de la integración de pagos (seña con Mercado Pago) de una clínica odontológica, con el objetivo de:

1. Detectar **reglas ambiguas** de pago (reglas RN-PAGO que admiten más de una interpretación).
2. Detectar **casos de borde de seguridad faltantes** (webhooks duplicados o falsificados, montos recalculados, secretos expuestos, pagos cruzados entre turnos).
3. Generar **escenarios verificables** (funcionamiento esperado, error de negocio, caso de borde) listos para `proposal.md`, `design.md` y `tasks.md`.

El foco no es "¿funciona el checkout?", sino "¿qué puede salir mal con plata real y cómo lo detectamos antes de codear?". Por eso revisa montos, idempotencia, credenciales, firma de webhook y estado del turno, que son los puntos donde un error cuesta dinero o duplica confirmaciones.

Está pensada para los changes C-08 `checkout-sena-mercadopago` y C-09 `webhook-conciliacion`, y para cualquier change futuro que toque `Pago`, `Turno.monto_sena` o la integración MP.

## Cuándo disparar esta skill

Usá esta skill cuando el usuario diga, por ejemplo:

- "prepará el spec de C-08 / C-09"
- "revisá la seguridad de la integración con Mercado Pago"
- "detectá casos de borde en el webhook de MP"
- "generá escenarios verificables para el checkout de la seña"
- "analizá si hay reglas ambiguas en knowledge-base/11_pagos_mercadopago.md"
- "qué pasa si llega dos veces el mismo webhook"
- "cómo validamos que el monto de la seña no se recalcule"

No usar para: implementar el cliente MP, escribir endpoints, configurar la cuenta de Mercado Pago, ni tareas ajenas a pagos (para reglas de turnos usá `reglas-turnos-review`).

## Entradas necesarias

La skill espera al menos una de estas entradas:

- Ruta a `knowledge-base/11_pagos_mercadopago.md` (fuente principal).
- Ruta a `knowledge-base/05_reglas_de_negocio.md` (RN-PAGO-01..04 y RN-RES-05).
- Ruta a `knowledge-base/08_arquitectura_propuesta.md` (variables de entorno y 12-factor).
- Ruta al change en `CHANGES.md` o su carpeta en `openspec/changes/`.
- Texto libre describiendo el flujo de pago a revisar.

Si no se proporciona ninguna, la skill lee por defecto los archivos KB del proyecto.

## Procedimiento (paso a paso)

### Paso 1 — Leer la fundación de pagos

Leer en este orden:

1. `knowledge-base/11_pagos_mercadopago.md` — preference, webhook, reembolsos, riesgos.
2. `knowledge-base/05_reglas_de_negocio.md` — RN-PAGO-01..04 y RN-RES-05.
3. `knowledge-base/08_arquitectura_propuesta.md` — variables `MP_*`, separación de routers, workers.
4. `knowledge-base/04_modelo_de_datos.md` — tabla `Pago` y `Turno.monto_sena`.
5. `knowledge-base/07_flujos_principales.md` — flujo de reserva + pago (Flujos 1 y 4).
6. `CHANGES.md` y el change en `openspec/changes/` — alcance real (C-08 no crea la tabla `pagos`; C-09 sí).

### Paso 2 — Extraer las reglas de seguridad vigentes

Listar todas las reglas aplicables. Para cada una anotar:

- Identificador (RN-PAGO-XX, regla dura 7/9, RN-RES-05).
- Texto de la regla.
- Entidades involucradas (`Turno`, `Pago`, `TipoPractica`).
- Dónde se enforza: aplicación, base de datos o webhook.

### Paso 3 — Detectar reglas ambiguas

Preguntar por cada regla:

- ¿Define el **redondeo y la moneda** del monto, o queda a interpretación?
- ¿Distingue **preference** de **pago** (C-08 vs C-09)?
- ¿Qué pasa con pagos **rechazados o expirados** previos del mismo turno?
- ¿La **firma del webhook** tiene algoritmo y header explícitos?
- ¿"No hardcodear" tiene un mecanismo de detección (test, pre-commit, CI)?
- ¿El estado del turno se valida **antes** de crear la preference (evitar pagar dos veces)?

Registrar cada ambigüedad con: regla, problema, ejemplo de interpretación alternativa y sugerencia de corrección.

### Paso 4 — Detectar casos de borde faltantes

Revisar como mínimo:

| Caso de borde | Qué verificar |
|---|---|
| Webhook duplicado | `mp_payment_id`/`idempotency_key` UNIQUE → 200 sin efectos (RN-PAGO-03) |
| Firma de webhook inválida | Rechazo 401, sin tocar el turno |
| `MP_ACCESS_TOKEN` hardcodeado | Detección por test/CI; solo env vars (regla dura 9) |
| Monto recalculado al pagar | Checkout usa `Turno.monto_sena` fotografiado, nunca el arancel actual (RN-PAGO-02) |
| Dos pagos aprobados por turno | Índice parcial UNIQUE en `pagos` + validación de estado (RN-PAGO-04) |
| Turno ya confirmado | `POST /pagar` responde 409, no crea preference nueva |
| Preference expirada + reintento | Nueva preference, mismo `turno_id`, nueva `idempotency_key`, sin duplicar turno |
| Pago de un turno ajeno | `external_reference` y `metadata.clinic_id` deben coincidir con el turno |
| Monto 0 o negativo | Seña 0% válida; monto negativo debe rechazarse |
| Moneda distinta de ARS | Rechazar o convertir explícitamente, nunca asumir |
| `raw_webhook` con datos sensibles | Guardar para auditoría sin exponerlo en logs ni respuestas |

Para cada caso, determinar si está cubierto por una regla existente o si falta.

### Paso 5 — Generar escenarios verificables

Para cada comportamiento del spec, generar **al menos tres escenarios**:

1. **Funcionamiento esperado** — camino feliz, con montos y estados concretos.
2. **Error de negocio** — regla violada, código HTTP esperado y sin efectos colaterales.
3. **Caso de borde** — situación límite de seguridad (replay, secreto, monto, concurrencia).

Formato de cada escenario:

```
## Escenario: <nombre>
- Contexto: ...
- Acción: ...
- Resultado esperado: ...
- Regla de referencia: RN-PAGO-XX / regla dura N / DD-XX
- Verificable: sí (assertion o test)
```

### Paso 6 — Producir el reporte

Generar un reporte markdown con esta estructura:

```
# Reporte de revisión de seguridad de pagos — <change>

## Resumen ejecutivo
- Cambio revisado: ...
- Reglas encontradas: N
- Reglas ambiguas detectadas: N
- Casos de borde faltantes: N
- Escenarios verificables generados: N

## Reglas de seguridad extraídas
| ID | Texto | Entidades | Estado |

## Reglas ambiguas detectadas
| Regla | Problema | Ejemplo alternativo | Sugerencia |

## Casos de borde faltantes
| Caso | ¿Cubierto? | Requerimiento |

## Escenarios verificables
### 1. Funcionamiento esperado
### 2. Error de negocio
### 3. Caso de borde

## Recomendaciones para el spec
```

## Salida esperada

Un **reporte markdown** (por defecto `docs/skills-mcp/revision-pagos-seguridad.md`) con:

- Reglas RN-PAGO y reglas duras aplicables.
- Ambigüedades con sugerencia concreta.
- Casos de borde de seguridad, marcando cuáles ya cubre el KB.
- Al menos 3 escenarios verificables con regla de referencia.
- Referencias explícitas a `11_pagos_mercadopago.md`, `05_reglas_de_negocio.md`, `08_arquitectura_propuesta.md` y `CHANGES.md`.

El reporte debe poder copiarse a `proposal.md`, `design.md` y `tasks.md` sin reescribir el dominio.

## Criterios de revisión (checklist antes de entregar)

- [ ] Cada escenario tiene contexto, acción, resultado esperado y regla de referencia.
- [ ] Hay al menos 1 escenario de funcionamiento esperado, 1 de error de negocio y 1 de borde.
- [ ] Cada regla cita su origen en la KB.
- [ ] Las ambigüedades incluyen un ejemplo concreto de interpretación alternativa.
- [ ] Los casos de borde cubren como mínimo: webhook duplicado, firma inválida, secreto hardcodeado, monto recalculado y dos aprobados por turno.
- [ ] El reporte no inventa reglas que no estén en la KB ni asume comportamiento de la API de MP no documentado.

## Límites

- No reemplaza una auditoría de seguridad real ni un pentest.
- No ejecuta llamadas a Mercado Pago: revisa documentación y código local.
- Si falta una regla en la KB, la marca como faltante; no la inventa.

## Ejemplo de uso

**Entrada del usuario:** "Prepará los escenarios de seguridad para C-08 checkout-sena-mercadopago"

**Salida de la skill:** Reporte con las 4 reglas RN-PAGO, detección de que RN-PAGO-02 no fija redondeo/moneda, caso de borde de webhook duplicado sin regla explícita de 200, y 3 escenarios verificables (preference con monto exacto, turno confirmado → 409, token MP hardcodeado detectado por test).

---

> Esta skill fue creada con el procedimiento del `skill-creator` (repositorio `anthropics/skills`). No es un servidor MCP: no accede a sistemas externos, solo lee archivos locales del proyecto y produce reportes en markdown.
