# Ficha de investigación — Skills y MCP para pagos (C-08)

## 1. Necesidad detectada

Al preparar el change **C-08 `checkout-sena-mercadopago`** (preference de seña en Mercado Pago, endpoint público de pago y pantalla de checkout; sin tabla `pagos` ni webhook, que son de C-09), se identificaron dos necesidades repetibles:

1. **Revisión de seguridad de pagos antes de implementar**: detectar reglas ambiguas (¿el monto de la seña se redondea? ¿en qué moneda? ¿qué pasa con un pago rechazado previo?), casos de borde faltantes (webhook duplicado, firma inválida, token hardcodeado, monto recalculado, dos pagos aprobados por turno) y generar escenarios verificables (funcionamiento esperado, error de negocio, borde) para el spec SDD. La revisión se repite en C-08 y C-09, y en cualquier change que toque `Pago` o `Turno.monto_sena`.

2. **Acceso a la documentación de pagos sin salir del flujo**: leer `knowledge-base/11_pagos_mercadopago.md`, `05_reglas_de_negocio.md` (RN-PAGO), `08_arquitectura_propuesta.md` (variables `MP_*`) y `CHANGES.md`, y verificar qué existe hoy en `backend/app/domain/pagos/` y `backend/app/api/webhooks/`. Un servidor MCP de lectura de archivos permite hacerlo desde el agente, sin cambiar de contexto ni copiar rutas.

## 2. Change elegido

**C-08 `checkout-sena-mercadopago`** (FASE 4 — Dinero y mensajes).

- Depende de C-01 (fundación) y C-05 (motor de reservas con `Turno.monto_sena`).
- Es parte del camino crítico (`C-05 → C-08 → C-09 → C-10`).
- Alcance acotado a la creación de la preference y el checkout: no crea tabla `pagos`, no implementa el webhook (C-09).
- Prepara el terreno para C-09, donde la idempotencia y la conciliación son el riesgo principal.

## 3. Skill creadora investigada

**Nombre:** `skill-creator`
**Fuente oficial / repositorio:** `https://github.com/anthropics/skills` (paquete npm `skills@1.7.4`, skill `skill-creator`)
**Compatibilidad:** Compatible con agentes que ejecuten `npx skills use`. No requiere instalación permanente; se ejecuta vía npx y descarga los archivos de soporte (SKILL.md, agents/, scripts/, eval-viewer/, references/) a un directorio temporal.

**Cómo se usó:**

1. Ejecutado `npx skills use "https://github.com/anthropics/skills" --skill "skill-creator"`.
2. Leído su `SKILL.md` completo (procedimiento de 6 etapas: capturar intención → escribir borrador → crear casos de prueba → ejecutar/evaluar → iterar → empaquetar).
3. Seguido ese procedimiento para crear la skill propia `pagos-seguridad-review`, reutilizando la estructura de `reglas-turnos-review` pero cambiando el dominio (pagos en vez de turnos).

## 4. Diseño de la skill propia

**Nombre:** `pagos-seguridad-review`
**Ubicación:** `skills/pagos-seguridad-review/SKILL.md`

| Componente | Definición |
|---|---|
| Propósito | Revisar la seguridad de pagos y señas con Mercado Pago para detectar reglas ambiguas, casos de borde de webhooks/idempotencia/secretos y generar escenarios verificables antes de implementar un change. |
| Cuándo se dispara | Al preparar o revisar C-08/C-09, tocar la integración MP, definir montos de seña, idempotencia, firma de webhook o credenciales `MP_*`. |
| Entradas | Ruta al KB/change o texto libre del flujo de pago. Por defecto lee `knowledge-base/11`, `05`, `08`, `04`, `07` y `CHANGES.md`. |
| Procedimiento | 6 pasos: leer fundación de pagos → extraer reglas RN-PAGO y reglas duras → detectar ambigüedades → detectar casos de borde → generar 3+ escenarios verificables → producir reporte markdown. |
| Salida esperada | Reporte markdown listo para copiar a `proposal.md`, `design.md` y `tasks.md`. |
| Criterios de revisión | Cada escenario: contexto, acción, resultado esperado, regla de referencia, verificable. Mínimo 3 escenarios (esperado, error, borde). Cubrir webhook duplicado, firma inválida, secreto hardcodeado, monto recalculado y dos aprobados por turno. No inventar reglas fuera del KB. |
| Límites | No reemplaza un pentest ni llama a la API de MP; solo revisa documentación y código local. |

## 5. Comparación de dos servidores MCP

### Opción A — `mcp-server-postgres` (oficial, `modelcontextprotocol/servers`)

- **Propósito:** consultar y gestionar bases de datos PostgreSQL.
- **Capacidades:** listar tablas, ver esquemas, ejecutar SQL, inspeccionar constraints e índices.
- **Requisitos:** PostgreSQL corriendo, connection string y credenciales.
- **Compatibilidad:** oficial de Anthropic, requiere Node.js + `@modelcontextprotocol/sdk`.
- **Permisos/credenciales:** usuario y contraseña de DB; sensibles.
- **Costo:** gratis (software libre); la infraestructura de DB corre aparte.
- **Aporte a C-08:** alto en teoría (validar `monto_sena`, constraints de `pagos`), pero no hay PostgreSQL ni Docker disponible en este entorno, y C-08 todavía no crea tablas.

### Opción B — `mcp-server-filesystem` (oficial, `modelcontextprotocol/servers`)

- **Propósito:** leer y escribir archivos del sistema de archivos local.
- **Capacidades:** listar directorios, leer archivos, crear/escribir, buscar.
- **Requisitos:** acceso al filesystem; directorios permitidos explícitos.
- **Compatibilidad:** oficial de Anthropic, requiere Node.js + `@modelcontextprotocol/sdk`.
- **Permisos/credenciales:** ninguna credencial; solo rutas autorizadas.
- **Costo:** gratis (software libre).
- **Aporte a C-08:** alto y ejecutable hoy — permite leer la KB de pagos, verificar que `domain/pagos/` y `api/webhooks/` estén vacíos (confirmando que C-08 no está implementado) y cruzar reglas con `CHANGES.md`.

### Elección justificada: `mcp-server-filesystem`

Se elige **filesystem** porque no hay Docker ni PostgreSQL disponible en este entorno, porque C-08 todavía no tiene esquema que inspeccionar, y porque el riesgo de este change está en las reglas y el contrato de pago (documentados en la KB), no en el esquema. Además no requiere credenciales, a diferencia del MCP de Postgres.

## 6. Pasos de instalación y configuración (MCP filesystem)

1. Instalar: `npm install -g @modelcontextprotocol/server-filesystem`
2. Configurar el cliente MCP (ej. `.mcp.json`):
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
3. Comprobar conexión: listar el directorio raíz del proyecto.
4. Ejecutar una herramienta real: `read_text_file` sobre `knowledge-base/11_pagos_mercadopago.md` y `list_directory` sobre `backend/app/domain/pagos/` y `backend/app/api/webhooks/`.
5. Límites: solo directorio del proyecto; solo lectura; no incluir rutas con secretos ni el `.env`.

## 7. Archivos de la fundación que se prevén actualizar

| Archivo | Modificación prevista | Motivo |
|---|---|---|
| `skills/pagos-seguridad-review/SKILL.md` | Crear | Skill propia del TP (pagos). |
| `.atl/skill-registry.md` | Registrar skill propia + mapeo a C-08/C-09 + compact rules | Registro obligatorio. |
| `AGENTS.md` | Documentar `pagos-seguridad-review` (sección "Skills propias") | Instrucciones del agente. |
| `CLAUDE.md` | Documentar `pagos-seguridad-review` (copia de AGENTS.md) | Instrucciones del agente. |
| `docs/skills-mcp/investigacion-c08-seguridad.md` | Crear | Ficha de investigación (Parte 1, C-08). |
| `docs/skills-mcp/aplicacion-c08.md` | Crear | Informe de aplicación (Parte 2, C-08). |
| `docs/skills-mcp/revision-pagos-seguridad.md` | Crear | Reporte de la skill propia sobre C-08. |
| `docs/skills-mcp/evidencias/mcp-evidencia-c08.md` | Crear | Evidencia de uso real del MCP. |
| `openspec/changes/c-08-checkout-sena-mercadopago/` | Crear proposal, design, tasks | Change C-08 preparado con SDD. |
| `CHANGES.md` | No marcar C-08 como `[x]` | Queda preparado, no implementado. |

## 8. Fuentes consultadas

| Fuente | URL | Fecha |
|---|---|---|
| Repositorio oficial de skills de Anthropic | https://github.com/anthropics/skills | 2026-10-29 |
| Servidores MCP oficiales de Anthropic | https://github.com/modelcontextprotocol/servers | 2026-10-29 |
| knowledge-base del proyecto (repo local) | `knowledge-base/` | 2026-10-29 |
| CHANGES.md del proyecto (repo local) | `CHANGES.md` | 2026-10-29 |
