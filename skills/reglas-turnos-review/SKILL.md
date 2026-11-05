---
name: reglas-turnos-review
description: Revisa escenarios de reglas de negocio y modelo de datos de turnos odontológicos para detectar reglas ambiguas, casos de borde faltantes y escenarios verificables antes de implementar un change. Usá esta skill siempre que vayas a preparar un change de turnos (C-02, C-05, C-06, C-07, etc.), revises KB de dominio, definas specs SDD o necesites generar escenarios de prueba (funcionamiento esperado, error de negocio, caso de borde). La skill lee la knowledge-base del proyecto, identifica gaps en las reglas y produce un reporte estructurado listo para incorporar a proposal.md/design.md/tasks.md.
compatibility: Proyecto turnos-odontologia (Python/FastAPI + Postgres + Redis + React/TS). Requiere acceso a knowledge-base/ y CHANGES.md del repo.
---

# reglas-turnos-review — Skill de revisión de reglas de negocio de turnos

## Propósito

Esta skill permite revisar, de forma sistemática, las reglas de negocio y el modelo de datos del dominio de turnos de una clínica odontológica, con el objetivo de:

1. Detectar **reglas ambiguas** (reglas del KB que admiten varias interpretaciones).
2. Detectar **casos de borde faltantes** (situaciones no cubiertas por las reglas documentadas).
3. Generar **escenarios verificables** (funcionamiento esperado, error de negocio, caso de borde) listos para incluir en specs SDD y tasks de implementación.

Está diseñada para usarse al preparar un change pendiente del roadmap (`CHANGES.md`), en particular C-02 `core-models-clinica-personas`, C-05 `motor-reservas-slots-turnos`, C-06 `reserva-publica-cancel-reprog` y C-07 `agenda-panel-dia`.

## Cuándo disparar esta skill

Usá esta skill cuando el usuario diga, por ejemplo:

- "prepará el spec de C-02"
- "revisá las reglas de negocio de turnos"
- "detectá casos de borde en el modelo de datos"
- "generá escenarios verificables para el change de reservas"
- "analizá si hay reglas ambiguas en knowledge-base/05_reglas_de_negocio.md"
- "qué falta en las reglas de cancelación/reprogramación"

No usar para: implementar código, escribir endpoints, configurar infraestructura, o tareas ajenas al dominio de turnos.

## Entradas necesarias

La skill espera al menos una de las siguientes entradas:

- Ruta al archivo de reglas de negocio (ej. `knowledge-base/05_reglas_de_negocio.md`).
- Ruta al archivo de modelo de datos (ej. `knowledge-base/04_modelo_de_datos.md`).
- Ruta al change en `CHANGES.md` o su carpeta en `openspec/changes/`.
- Texto libre describiendo las reglas o el change a revisar.

Si no se proporciona ninguna, la skill leerá por defecto los archivos KB del proyecto.

## Procedimiento (paso a paso)

Seguí este orden cada vez que se invoque la skill:

### Paso 1 — Leer la fundación del proyecto

Leer en este orden:

1. `knowledge-base/04_modelo_de_datos.md` — entidades, restricciones clave, seed data.
2. `knowledge-base/05_reglas_de_negocio.md` — reglas codificadas (RN-XX).
3. `knowledge-base/09_decisiones_y_supuestos.md` — decisiones DD-XX y supuestos SU-XX.
4. `CHANGES.md` — alcance y dependencias del change a preparar.
5. `openspec/changes/<cambio>/` (si existe) — proposal/design/tasks previos.

### Paso 2 — Extraer reglas de negocio vigentes

Identificar y listar todas las reglas RN-XX aplicables al change. Para cada regla, anotar:

- Identificador (ej. RN-RES-01).
- Texto de la regla.
- Entidades involucradas (Turno, Paciente, Sillon, etc.).
- Campo o restricción afectada.

### Paso 3 — Detectar reglas ambiguas

Para cada regla, preguntar:

- ¿Hay términos subjetivos ("suficiente", "rápido", "adecuado") sin umbral definido?
- ¿Hay dependencias de otras reglas no cruzadas?
- ¿El comportamiento ante errores (409, 403, 200) está explícito?
- ¿Qué pasa con datos nulos o fuera de rango?

Registrar cada ambigüedad detectada con: regla, problema, ejemplo de interpretación alternativa, sugerencia de corrección.

### Paso 4 — Detectar casos de borde faltantes

Revisar específicamente estos escenarios (mínimo):

| Caso de borde | Qué verificar |
|---|---|
| Email duplicado en otra clínica | ¿`email UNIQUE` es global o por `clinic_id`? |
| `sena_pct` fuera de 0-100 | ¿CHECK constraint lo rechaza? |
| Turno sin `clinic_id` | ¿Se permite o rechaza (DD-06)? |
| 2ª falta de paciente | ¿Dispara bloqueo 30d automático? |
| Cancelar < 12hs | ¿Rechaza con 403? |
| 2ª reprogramación | ¿Exige nueva seña y libera slot? |
| `manage_token` adivinable | ¿Es unguessable? |
| Webhook MP duplicado | ¿Es idempotente (200 sin efectos)? |
| Turno con `fin <= inicio` | ¿CHECK lo rechaza? |
| Solape sillón y odontólogo | ¿EXCLUDE/UNIQUE lo previene? |

Para cada caso, determinar si está cubierto por una regla existente o falta.

### Paso 5 — Generar escenarios verificables

Para cada cambio del spec, generar **al menos tres escenarios**:

1. **Funcionamiento esperado** — camino feliz, qué se espera que ocurra.
2. **Error de negocio** — regla violada, código de error y mensaje esperados.
3. **Caso de borde** — situación límite, comportamiento esperado.

Formato de cada escenario:

```
## Escenario: <nombre>
- Contexto: ...
- Acción: ...
- Resultado esperado: ...
- Regla de referencia: RN-XX / DD-XX / SU-XX
- Verificable: sí (assertion o test)
```

### Paso 6 — Producir el reporte

Generar un reporte en markdown con esta estructura:

```
# Reporte de revisión de reglas de turnos — <change>

## Resumen ejecutivo
- Cambio revisado: ...
- Reglas encontradas: N
- Reglas ambiguas detectadas: N
- Casos de borde faltantes: N
- Escenarios verificables generados: N

## Reglas de negocio extraídas
| ID | Texto | Entidades | Estado |
|---|---|---|---|

## Reglas ambiguas detectadas
| Regla | Problema | Ejemplo alternativo | Sugerencia |

## Casos de borde faltantes
| Caso | ¿Cubierto? | Requerimiento |

## Escenarios verificables
### 1. Funcionamiento esperado
...
### 2. Error de negocio
...
### 3. Caso de borde
...

## Recomendaciones para el spec
...
```

## Salida esperada

El resultado de la skill es un **reporte markdown** (guardado en `docs/skills-mcp/revision-reglas-turnos.md` o similar) que contenga:

- Lista de reglas RN-XX aplicables.
- Reglas ambiguas con sugerencia de corrección.
- Casos de borde faltantes identificados.
- Al menos 3 escenarios verificables (funcionamiento esperado, error de negocio, borde).
- Referencias explícitas a la KB (`04`, `05`, `09`) y a `CHANGES.md`.

El reporte debe estar listo para copiar y pegar en `proposal.md`, `design.md` y `tasks.md` del change.

## Criterios de revisión (checklist antes de entregar)

- [ ] Cada escenario tiene: contexto, acción, resultado esperado, regla de referencia.
- [ ] Hay al menos 1 escenario de funcionamiento esperado, 1 de error de negocio, 1 de borde.
- [ ] Cada regla cita su origen en KB (`04_modelo_de_datos.md`, `05_reglas_de_negocio.md`, `09_decisiones_y_supuestos.md`).
- [ ] Las ambigüedades tienen ejemplo concreto de interpretación alternativa.
- [ ] Los casos de borde incluyen al menos: email duplicado, `sena_pct` fuera de rango, falta 2ª, cancelar < 12hs, webhook duplicado.
- [ ] El reporte no inventa reglas de dominio que no estén en el KB.

## Ejemplo de uso

**Entrada del usuario:** "Prepará los escenarios verificables para C-02 core-models-clinica-personas"

**Salida de la skill:** Reporte markdown con reglas de Clinic/User/Paciente/Sillon, detección de que `sena_pct` necesita CHECK constraint, caso de borde de email duplicado entre clínicas, y 3 escenarios verificables listos para `tasks.md`.

---

> Esta skill fue creada con el procedimiento del `skill-creator` (repositorio `anthropics/skills`). No es un servidor MCP: no accede a sistemas externos, solo lee archivos locales del proyecto y produce reportes en markdown.