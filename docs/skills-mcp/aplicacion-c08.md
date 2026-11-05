# Informe de aplicación — Skill de seguridad y MCP para C-08

## Resumen

Se preparó el change **C-08 `checkout-sena-mercadopago`** con Spec-Driven Development (SDD), integrando una **skill propia** (`pagos-seguridad-review`) y un **servidor MCP** (`mcp-server-filesystem`). El change queda **preparado para implementar** (no implementado, no verificado, no archivado), listo para una instancia posterior.

## Parte 1 — Investigación (clase)

Ficha: `docs/skills-mcp/investigacion-c08-seguridad.md`

- **Necesidad detectada:** revisión de seguridad de transacciones y pagos antes de implementar (detectar reglas ambiguas, casos de borde en webhooks/secrets/idempotencia); y acceso a archivos de pagos y KB sin salir del flujo del agente.
- **Change elegido:** C-08 `checkout-sena-mercadopago` (depende de C-05 y C-01; camino crítico).
- **Skill creadora investigada:** `skill-creator` (repositorio `https://github.com/anthropics/skills`, paquete `skills@1.7.4`). Ejecutado vía `npx skills use`; se siguió su procedimiento de 6 etapas.
- **Comparación de MCP:** `mcp-server-postgres` (más relevante para esquema de BD, pero requiere PostgreSQL no disponible) vs `mcp-server-filesystem` (elegido: probatable localmente, sin credenciales, lectura de KB de pagos y código de webhooks).
- **Archivos de fundación previstos:** `.atl/skill-registry.md`, `AGENTS.md`, `CLAUDE.md`, `docs/skills-mcp/`, `openspec/changes/c-08-checkout-sena-mercadopago/`.

## Parte 2 — Integración y aplicación

### Skill propia: `pagos-seguridad-review`

- **Ubicación:** `skills/pagos-seguridad-review/SKILL.md`
- **Registrada en:** `.atl/skill-registry.md` (tabla User Skills, mapeo a cambios C-08/C-09, Compact Rules).
- **Documentada en:** `AGENTS.md` y `CLAUDE.md` (sección "Skill propia: `pagos-seguridad-review`").
- **Evidencia de uso:** `docs/skills-mcp/revision-pagos-seguridad.md` (por crear — reporte con 6 pasos del skill-creator: lectura de fundación de pagos, extracción de reglas RN-PAGO, detección de reglas ambiguas y casos de borde de seguridad, 3 escenarios verificables).

### MCP: `mcp-server-filesystem`

- **Servidor:** `@modelcontextprotocol/server-filesystem` (oficial, `modelcontextprotocol/servers`).
- **Instalación:** `npm install -g @modelcontextprotocol/server-filesystem` + `@modelcontextprotocol/sdk` para el cliente de prueba.
- **Configuración:** servidor apuntando al directorio raíz del proyecto, solo lectura, sin credenciales.
- **Comprobación de conexión:** ejecutado script cliente MCP que se conectó, listó 13 herramientas y ejecutó `read_text_file` sobre `knowledge-base/11_pagos_mercadopago.md`, `knowledge-base/05_reglas_de_negocio.md`, `knowledge-base/08_arquitectura_propuesta.md`, `CHANGES.md`; y `list_directory` sobre `backend/app/domain/pagos/` y `backend/app/api/webhooks/`.
- **Evidencia:** `docs/skills-mcp/evidencias/mcp-evidencia-c08.md` (solicitud realizada, resultado obtenido, herramientas disponibles, contenido de KB leído, listado de directorios vacíos de pagos/webhooks confirmando que C-08 no está implementado).
- **Documentación:** `README.md` (pendiente de agregar sección MCP — ver limitaciones).
- **Límites de acceso:** solo directorio del proyecto; solo lectura; no incluir rutas con secretos.

### Change C-08 preparado (SDD)

Artefactos en `openspec/changes/c-08-checkout-sena-mercadopago/`:
- `proposal.md`: por qué, qué cambia, capacidades, impacto, dependencias (C-01, C-05), leer antes.
- `design.md`: decisiones (monto_sena como foto, preference MP con metadata de idempotencia, un solo aprobado por turno, secretos solo por env vars), riesgos, plan de migración.
- `tasks.md`: 5 grupos de tareas (integración MP, frontend checkout, tests TDD con 3 escenarios verificables, calidad, follow-up). Los 3 escenarios: (1) funcionamiento esperado — preference con monto exacto; (2) error de negocio — turno ya confirmado rechaza 409; (3) caso de borde — secreto MP hardcodeado detectado por test.
- `.openspec.yaml`: metadatos del change (status: prepared, phase: 4, depends_on: C-01, C-05).

El change **no está marcado como `[x]` en CHANGES.md** ni archivado, per alcance del TP.

## Revisión crítica

**Defecto detectado y corregido:** En el `design.md` inicial de C-08 mencioné la tabla `pagos` como si ya existiera o se creara en C-08. Sin embargo, `pagos` se crea en C-09 (`webhook-conciliacion`). C-08 solo define el contrato de la preference MP y el endpoint de pago; la tabla `pagos` y el webhook vienen en C-09. Corregido para dejar claro que C-08 no crea tabla `pagos` ni webhook.

**Cómo se detectó:** al revisar el alcance de C-08 contra `CHANGES.md` (C-09 crea tabla `pagos`) y `05_reglas_de_negocio.md` (RN-PAGO-03 es del webhook, C-09).

**Defecto en el MCP:** al ejecutar el script de prueba contra el repo en `Documents\GitHub\turnos-odontologia`, el script intentó escribir la evidencia en el Desktop (ruta anterior del proyecto). Se corrigió la ruta de salida para escribir en el repo correcto (`Documents\GitHub\turnos-odontologia\docs\skills-mcp\evidencias\`).

**Limitación detectada en los tests:** En `tasks.md` el escenario 3 de "secretos no hardcodeados" menciona buscar patrones de token MP en código, pero no especifica la herramienta exacta (¿grep? ¿bandit? ¿test unitario?). Esto se deja como detalle de implementación; se sugiere usar `grep` o un test que escanee fuentes.

## Limitaciones

- No se pudo probar `mcp-server-postgres` porque no hay PostgreSQL ni Docker disponible en este entorno. Se documentó como pendiente en la ficha de investigación.
- El `README.md` del proyecto aún no incluye una sección dedicada al MCP; se recomienda agregarla en una instancia posterior.
- El change C-08 queda preparado; su implementación, verificación y archivado quedan para una instancia posterior (fuera del alcance de este TP).
- Los tests de C-08 requieren MP sandbox para integración real; los tests unitarios usan mock de `mp_client`.

## Archivos modificados y motivo (C-08)

| Archivo | Motivo |
|---|---|
| `skills/pagos-seguridad-review/SKILL.md` | Crear skill propia de seguridad de pagos (Parte 2, paso 5 del TP). |
| `.atl/skill-registry.md` | Registrar skill propia + mapeo a C-08/C-09 + compact rules. |
| `AGENTS.md` | Documentar `pagos-seguridad-review` (instrucciones del agente). |
| `CLAUDE.md` | Documentar `pagos-seguridad-review` (copia de AGENTS.md). |
| `docs/skills-mcp/investigacion-c08-seguridad.md` | Ficha de investigación C-08 (Parte 1 del TP). |
| `docs/skills-mcp/revision-pagos-seguridad.md` | Reporte de uso de la skill propia sobre C-08 (por crear). |
| `docs/skills-mcp/evidencias/mcp-evidencia-c08.md` | Evidencia de invocación real del MCP sobre archivos de pagos. |
| `docs/skills-mcp/aplicacion-c08.md` | Informe de aplicación C-08 (Parte 2 del TP, este archivo). |
| `openspec/changes/c-08-checkout-sena-mercadopago/proposal.md` | Artefacto SDD del change C-08. |
| `openspec/changes/c-08-checkout-sena-mercadopago/design.md` | Artefacto SDD del change C-08. |
| `openspec/changes/c-08-checkout-sena-mercadopago/tasks.md` | Artefacto SDD del change C-08 con 3 escenarios verificables. |
| `openspec/changes/c-08-checkout-sena-mercadopago/.openspec.yaml` | Metadatos del change C-08. |

## Fuentes con URL y fecha de consulta

| Fuente | URL | Fecha |
|---|---|---|
| Repositorio oficial de skills de Anthropic | https://github.com/anthropics/skills | 2026-10-29 |
| Servidores MCP oficiales de Anthropic | https://github.com/modelcontextprotocol/servers | 2026-10-29 |
| knowledge-base del proyecto (repo local) | `knowledge-base/` | 2026-10-29 |
| CHANGES.md del proyecto (repo local) | `CHANGES.md` | 2026-10-29 |
