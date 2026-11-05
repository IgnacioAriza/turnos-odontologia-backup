# Ficha de investigación — Skills y MCP para el proyecto Odontología

## 1. Necesidad detectada

Al preparar el change **C-02 `core-models-clinica-personas`** (modelos base: Clinic, User, Paciente, Sillon, Bloqueo; migración 001; seed mínimo), se identificaron dos necesidades repetibles:

1. **Revisión de reglas de negocio y modelo de datos** antes de implementar: detectar reglas ambiguas (¿email UNIQUE es global o por clinic_id?), casos de borde faltantes (sena_pct fuera de 0-100, 2ª falta → bloqueo 30d, manage_token adivinable) y generar escenarios verificables (funcionamiento esperado, error de negocio, borde) para los specs SDD. Esta tarea es repetible en cada change de dominio (C-02, C-05, C-06, C-07).

2. **Acceso a información del proyecto sin salir del flujo**: consultar archivos de la fundación (KB, CHANGES.md, specs, modelado) y verificar que las reglas implementadas coincidan con lo documentado. Un servidor MCP de lectura de archivos permitiría inspeccionar el repositorio desde el agente sin cambiar de contexto.

## 2. Change elegido

**C-02 `core-models-clinica-personas`** (FASE 1 — Auth + Catálogo).
- Depende solo de C-01 (ya completada: foundation-setup).
- No requiere funcionalidades inexistentes.
- Es el primer cambio del camino crítico; preparar bien sus specs sienta la base para todo lo demás.
- Alcance: modelos Clinic, User, Paciente, Sillon, Bloqueo; `AuditMixin`; `BaseRepository[T]` + `UnitOfWork`; `clinic_id` FK obligatorio; migración 001; seed idempotente; constraints UNIQUE; tests de filtros `clinic_id`.

## 3. Skill creadora investigada

**Nombre:** `skill-creator`
**Fuente oficial / repositorio:** `https://github.com/anthropics/skills` (paquete npm `skills@1.7.4`, skill `skill-creator`)
**Compatibilidad:** Compatible con agentes que ejecuten `npx skills use`. No requiere instalación permanente; se ejecuta vía npx y descarga los archivos de soporte (SKILL.md, agents/, scripts/, eval-viewer/, references/) a directorio temporal.

**Cómo se usó:**
1. Ejecutado `npx skills use "https://github.com/anthropics/skills" --skill "skill-creator"`.
2. Leído su `SKILL.md` completo (procedimiento de 6 etapas: capturar intención → escribir borrador → crear casos de prueba → ejecutar/evaluar → iterar → empaquetar).
3. Seguido ese procedimiento para crear la skill propia `reglas-turnos-review`.

## 4. Diseño de la skill propia

**Nombre:** `reglas-turnos-review`
**Ubicación:** `skills/reglas-turnos-review/SKILL.md`

| Componente | Definición |
|---|---|
| Propósito | Revisar reglas de negocio y modelo de datos de turnos para detectar reglas ambiguas, casos de borde faltantes y generar escenarios verificables antes de implementar un change de dominio de turnos. |
| Cuándo se dispara | Al preparar un change de turnos (C-02, C-05, C-06, C-07), revisar KB de dominio, definir specs SDD o generar escenarios de prueba. |
| Entradas | Ruta al KB/change o texto libre de reglas. Por defecto lee `knowledge-base/04`, `05`, `09` y `CHANGES.md`. |
| Procedimiento | 6 pasos: leer fundación → extraer reglas RN-XX → detectar ambigüedades → detectar casos de borde → generar 3+ escenarios verificables → producir reporte markdown. |
| Salida esperada | Reporte markdown listo para copiar a `proposal.md`, `design.md` y `tasks.md`. |
| Criterios de revisión | Cada escenario: contexto, acción, resultado esperado, regla de referencia, verificable. Mínimo 3 escenarios (esperado, error, borde). No inventar reglas fuera del KB. |

## 5. Comparación de dos servidores MCP

### Opción A — `mcp-server-postgres` (oficial, `modelcontextprotocol/servers`)
- **Propósito:** Consultar y gestionar bases de datos PostgreSQL.
- **Capacidades:** listar tablas, ver esquemas, ejecutar consultas SQL, inspeccionar constraints e índices.
- **Requisitos:** PostgreSQL corriendo, connection string, credenciales de DB.
- **Compatibilidad:** Oficial de Anthropic, requiere Node.js + `@modelcontextprotocol/sdk`.
- **Permisos/credenciales:** Usuario y contraseña de DB; sensibles.
- **Costo:** Gratis (software libre); infraestructura de DB aparte.
- **Aporte a C-02:** Alto — permite inspeccionar el esquema creado en migración 001, validar `clinic_id`, CHECK constraints, UNIQUE constraints, índices.

### Opción B — `mcp-server-filesystem` (oficial, `modelcontextprotocol/servers`)
- **Propósito:** Leer y escribir archivos en el sistema de archivos local.
- **Capacidades:** listar directorios, leer archivos, crear/escribir archivos, buscar.
- **Requisitos:** Acceso al sistema de archivos local; directorios permitidos explícitos.
- **Compatibilidad:** Oficial de Anthropic, requiere Node.js + `@modelcontextprotocol/sdk`.
- **Permisos/credenciales:** Ninguna credencial; solo rutas de directorio autorizadas.
- **Costo:** Gratis (software libre).
- **Aporte a C-02:** Medio-Alto — permite leer KB, CHANGES.md, specs y verificar consistencia entre documentación y código.

### Elección justificada: `mcp-server-filesystem`

Se elige **filesystem** porque no hay Docker ni PostgreSQL disponible en este entorno, por lo que `mcp-server-postgres` no se puede instalar ni ejecutar. Además, aporta directamente a C-02 permitiendo leer y verificar los archivos de la fundación.

## 6. Pasos de instalación y configuración (MCP filesystem)

1. Instalar: `npm install -g @modelcontextprotocol/server-filesystem`
2. Configurar cliente MCP (ej. `.mcp.json`):
   ```json
   {
     "mcpServers": {
       "filesystem": {
         "command": "npx",
         "args": ["-y", "@modelcontextprotocol/server-filesystem", "<ruta-repo>"]
       }
     }
   }
   ```
3. Comprobar conexión: listar directorio raíz del proyecto.
4. Ejecutar herramienta real: leer `knowledge-base/05_reglas_de_negocio.md`.
5. Límites: solo directorio del proyecto; solo lectura; no incluir rutas con secretos.

## 7. Archivos de la fundación que se prevén actualizar

| Archivo | Modificación prevista | Motivo |
|---|---|---|
| `skills/reglas-turnos-review/SKILL.md` | Crear | Skill propia del TP. |
| `.atl/skill-registry.md` | Registrar skill propia + mapeo a cambios + compact rules | Registro obligatorio. |
| `AGENTS.md` | Documentar `reglas-turnos-review` | Instrucciones del agente. |
| `CLAUDE.md` | Documentar `reglas-turnos-review` | Copia de AGENTS.md. |
| `docs/skills-mcp/investigacion.md` | Crear | Ficha de investigación (Parte 1). |
| `docs/skills-mcp/aplicacion.md` | Crear | Informe de aplicación (Parte 2). |
| `openspec/changes/c-02-core-models-clinica-personas/` | Crear proposal.md, design.md, specs, tasks.md | Change C-02 preparado con SDD. |
| `CHANGES.md` | No marcar C-02 como `[x]` | Queda preparado, no implementado. |

## 8. Fuentes consultadas

| Fuente | URL | Fecha |
|---|---|---|
| Repositorio oficial de skills de Anthropic | https://github.com/anthropics/skills | 2026-10-29 |
| Servidores MCP oficiales de Anthropic | https://github.com/modelcontextprotocol/servers | 2026-10-29 |
| knowledge-base del proyecto (repo local) | `knowledge-base/` | 2026-10-29 |
| CHANGES.md del proyecto (repo local) | `CHANGES.md` | 2026-10-29 |
