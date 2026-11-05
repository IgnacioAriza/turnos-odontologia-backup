# Informe de aplicación — Skills y MCP para C-02

## Resumen

Se preparó el change **C-02 `core-models-clinica-personas`** con Spec-Driven Development (SDD), integrando una **skill propia** (`reglas-turnos-review`) y un **servidor MCP** (`mcp-server-filesystem`). El change queda **preparado para implementar** (no implementado, no verificado, no archivado), listo para una instancia posterior.

## Parte 1 — Investigación (clase)

Ficha: `docs/skills-mcp/investigacion.md`

- **Necesidad detectada:** revisión sistemática de reglas de negocio y modelo de datos antes de implementar; y acceso a archivos de la fundación sin salir del flujo del agente.
- **Change elegido:** C-02 `core-models-clinica-personas` (depende solo de C-01, ya completada; primer cambio del camino crítico).
- **Skill creadora investigada:** `skill-creator` (repositorio `https://github.com/anthropics/skills`, paquete `skills@1.7.4`). Ejecutado vía `npx skills use`.
- **Comparación de MCP:** `mcp-server-postgres` vs `mcp-server-filesystem` (elegido filesystem: probatable localmente, sin credenciales).

## Parte 2 — Integración y aplicación

### Skill propia: `reglas-turnos-review`

- **Ubicación:** `skills/reglas-turnos-review/SKILL.md`
- **Registrada en:** `.atl/skill-registry.md` (tabla User Skills, mapeo a cambios C-02/C-05/C-06/C-07, Compact Rules).
- **Documentada en:** `AGENTS.md` y `CLAUDE.md`.
- **Evidencia de uso:** `docs/skills-mcp/revision-reglas-turnos.md` — reporte con 6 pasos del skill-creator: detección de 4 reglas ambiguas y 6 casos de borde faltantes, 3 escenarios verificables.

### MCP: `mcp-server-filesystem`

- **Servidor:** `@modelcontextprotocol/server-filesystem` (oficial, `modelcontextprotocol/servers`).
- **Instalación:** `npm install -g @modelcontextprotocol/server-filesystem`.
- **Comprobación de conexión:** script cliente MCP conectó, listó 12 herramientas, ejecutó `list_directory` y `read_text_file` sobre `knowledge-base/05_reglas_de_negocio.md`.
- **Evidencia:** `docs/skills-mcp/evidencias/mcp-evidencia.md`.

### Change C-02 preparado (SDD)

Artefactos en `openspec/changes/c-02-core-models-clinica-personas/`:
- `proposal.md`, `design.md`, `tasks.md`, `.openspec.yaml` (status: prepared, phase: 1, depends_on: C-01).
- `tasks.md` con 3 escenarios verificables: (1) funcionamiento esperado — mismo email diferente clinic_id se inserta; (2) error de negocio — mismo email mismo clinic_id rechaza unique_violation; (3) caso de borde — sena_pct=150 rechaza CHECK violation.

El change **no está marcado como `[x]` en CHANGES.md** ni archivado, per alcance del TP.

## Revisión crítica

**Defecto detectado y corregido:** En el `design.md` inicial de C-02 incluí el `CHECK sena_pct 0-100` de `TipoPractica` en la sección de índices/constraints, pero `TipoPractica` se crea en **C-04**, no en C-02. Corregido para dejarlo como referencia futura.

**Defecto en el MCP:** el `skill-creator` indicaba usar `read_file`, pero está deprecado; se corrigió a `read_text_file`.

## Limitaciones

- No se pudo probar `mcp-server-postgres` (no hay PostgreSQL ni Docker disponible).
- El `README.md` del proyecto aún no incluye una sección dedicada al MCP.
- El change C-02 queda preparado; su implementación y archivado quedan para una instancia posterior.

## Archivos modificados y motivo

| Archivo | Motivo |
|---|---|
| `skills/reglas-turnos-review/SKILL.md` | Crear skill propia. |
| `.atl/skill-registry.md` | Registrar skill propia + mapeo + compact rules. |
| `AGENTS.md` | Documentar skill propia. |
| `CLAUDE.md` | Documentar skill propia (copia de AGENTS.md). |
| `docs/skills-mcp/investigacion.md` | Ficha de investigación. |
| `docs/skills-mcp/revision-reglas-turnos.md` | Reporte de uso de la skill. |
| `docs/skills-mcp/evidencias/mcp-evidencia.md` | Evidencia de invocación real del MCP. |
| `docs/skills-mcp/aplicacion.md` | Informe de aplicación. |
| `openspec/changes/c-02-core-models-clinica-personas/` | Artefactos SDD del change C-02. |

## Fuentes con URL y fecha de consulta

| Fuente | URL | Fecha |
|---|---|---|
| Repositorio oficial de skills de Anthropic | https://github.com/anthropics/skills | 2026-10-29 |
| Servidores MCP oficiales de Anthropic | https://github.com/modelcontextprotocol/servers | 2026-10-29 |
| knowledge-base del proyecto (repo local) | `knowledge-base/` | 2026-10-29 |
| CHANGES.md del proyecto (repo local) | `CHANGES.md` | 2026-10-29 |
