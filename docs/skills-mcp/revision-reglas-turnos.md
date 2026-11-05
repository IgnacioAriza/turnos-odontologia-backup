# Reporte de revisión de reglas de turnos — C-02 core-models-clinica-personas

Generado por la skill propia `reglas-turnos-review` (ubicada en `skills/reglas-turnos-review/SKILL.md`).
Metodología aplicada: 6 pasos del skill-creator (capturar intención → leer fundación → extraer reglas → detectar ambigüedades → detectar casos de borde → generar escenarios verificables → producir reporte).

Fuentes consultadas mediante MCP filesystem (`read_text_file` sobre `knowledge-base/`):
- `knowledge-base/04_modelo_de_datos.md`
- `knowledge-base/05_reglas_de_negocio.md`
- `knowledge-base/09_decisiones_y_supuestos.md`
- `CHANGES.md` (alcance y dependencias de C-02)

---

## Resumen ejecutivo

- Cambio revisado: **C-02 `core-models-clinica-personas`**
- Reglas de negocio encontradas: 23
- Reglas ambiguas detectadas: 4
- Casos de borde faltantes: 6
- Escenarios verificables generados: 3 (funcionamiento esperado, error de negocio, caso de borde)

---

## Reglas de negocio extraídas (aplicables a C-02)

| ID | Texto | Entidades | Estado |
|---|---|---|---|
| RN-RES-01 | Un sillón no puede tener dos turnos superpuestos | Turno, Sillon | Relevante (C-05, no C-02) |
| RN-RES-03 | La reserva pública no exige login; emite manage_token | Turno, Paciente | Relevante (C-06) |
| RN-RES-04 | Todo turno nace en pendiente_sena con expiración TTL | Turno | Relevante (C-05) |
| RN-AUS-01 | 2 faltas → bloqueo de reserva por 30 días | Paciente, Bloqueo | Relevante (C-02, C-07) |
| RN-AUS-02 | Paciente bloqueado no puede crear reservas | Paciente, Bloqueo | Relevante (C-02, C-06) |
| RN-PAGO-01 | Seña en % del precio según TipoPractica.sena_pct | TipoPractica, Turno | Relevante (C-02, C-04) |
| RN-PAGO-02 | monto_sena = round(precio_base * sena_pct / 100) al crear reserva | Turno, TipoPractica | Relevante (C-02, C-05) |
| RN-ADMIN-01 | Solo admin modifica % seña y aranceles; auditoría quien/cuando/antes/después | TipoPractica, Arancel | Relevante (C-02, C-04, C-13) |
| RN-ADMIN-02 | En v1.0 aranceles son lectura + seed inicial | Arancel, TipoPractica | Relevante (C-02, C-04) |

---

## Reglas ambiguas detectadas

| Regla | Problema | Ejemplo de interpretación alternativa | Sugerencia |
|---|---|---|---|
| RN-ADMIN-01 | "todo cambio audita quien/cuando/antes/después" no especifica dónde se guarda la auditoría | ¿Tabla `arancel_historial` nueva? | Definir en el design de C-02/C-04 si la auditoría es tabla propia o jsonb. |
| RN-AUS-01 | "2 faltas" no especifica si faltas vencidas se acumulan indefinidamente | ¿Una falta de hace 6 meses cuenta para el bloqueo actual? | Especificar ventana de acumulación o que faltas son permanentes. |
| RN-PAGO-02 | "foto del monto" no especifica redondeo (round vs floor vs ceil) ni moneda | ¿monto_sena se guarda en ARS con 2 decimales? | Especificar `round()` aritmético y 2 decimales en ARS. |
| RN-ADMIN-02 | "seed inicial" no especifica valores de sena_pct por práctica | ¿Limpieza 20%, endodoncia 30%? | Documentar valores provisorios en seed de C-04; marcar como pendiente de Admin. |

---

## Casos de borde faltantes

| Caso | ¿Cubierto por regla existente? | Requerimiento |
|---|---|---|
| Email duplicado en otra clínica | Parcial — `email UNIQUE` por clínica | No hay regla explícita de que email es único **por clínica**, no global. |
| `sena_pct` fuera de 0-100 en TipoPractica | Parcial — CHECK constraint | No hay regla RN que lo mencione explícitamente. |
| Turno creado sin `clinic_id` | No — DD-06 dice clinic_id obligatorio desde día 1 | Falta regla RN que rechace turno sin clinic_id. |
| `manage_token` adivinable/secuencial | No | Falta regla de que manage_token debe ser unguessable (UUID aleatorio). |
| Paciente con `bloqueado_hasta` en el pasado | No — no hay regla de desbloqueo automático | ¿Se permite reservar después de 30 días? |
| Usuario `odonto` creando turno para otro odontólogo | No — RBAC confina a odontologo_id propio | Falta regla explícita de confinamiento. |

---

## Escenarios verificables (generados para C-02)

### Escenario 1 — Funcionamiento esperado: creación de entidad con clinic_id

- **Contexto:** Se crea un `User` rol `recepcion` asociado a la clínica seed (clinic_id = C1).
- **Acción:** `INSERT INTO users (clinic_id, email, password_hash, rol, nombre, activo) VALUES ('C1', 'recepcion@clinica.com', 'hash...', 'recepcion', 'María Recepción', true)`.
- **Resultado esperado:** Fila insertada con `id` UUID generado, `created_at` con timestamp, `clinic_id = 'C1'`.
- **Regla de referencia:** DD-06 (clinic_id obligatorio desde día 1), 04_modelo_de_datos.md §User.
- **Verificable:** sí — test de inserción verifica `clinic_id` no nulo y correo único por clínica.

### Escenario 2 — Error de negocio: email duplicado dentro de la misma clínica

- **Contexto:** Ya existe un `User` con email `admin@clinica.com` y `clinic_id = 'C1'`.
- **Acción:** Intentar `INSERT` de otro `User` con mismo email y mismo `clinic_id`.
- **Resultado esperado:** Base de datos rechaza con error de constraint UNIQUE (`email UNIQUE` por `clinic_id`). Código 23505 (PostgreSQL unique_violation).
- **Regla de referencia:** 04_modelo_de_datos.md §User (email UNIQUE por clínica), RN-ADMIN-01.
- **Verificable:** sí — test espera error 409/conflict o unique_violation de DB.

### Escenario 3 — Caso de borde: sena_pct fuera de rango 0-100

- **Contexto:** `TipoPractica` con `sena_pct` debe estar entre 0 y 100 (CHECK constraint).
- **Acción:** Intentar `INSERT` de `TipoPractica` con `sena_pct = 150` (fuera de rango).
- **Resultado esperado:** Base de datos rechaza con error de CHECK constraint (`sena_pct BETWEEN 0 AND 100`).
- **Regla de referencia:** 04_modelo_de_datos.md §TipoPractica (Constraints: sena_pct BETWEEN 0 AND 100).
- **Verificable:** sí — test espera error de constraint de DB.

---

## Recomendaciones para el spec de C-02

1. En `design.md`, especificar que `email` es UNIQUE **por `clinic_id`** (no global).
2. Agregar regla RN explícita: "Todo turno debe tener `clinic_id` no nulo" (DD-06).
3. Agregar regla RN explícita: "`manage_token` debe ser UUID v4 unguessable".
4. Agregar regla RN explícita: "`sena_pct` en TipoPractica tiene CHECK 0-100".
5. Considerar desbloqueo automático después de 30 días — definir en C-07.

---

## Evidencia de uso de la skill y el MCP

- **Skill propia:** `reglas-turnos-review` aplicada siguiendo su SKILL.md (6 pasos). Reporte generado en este archivo.
- **MCP:** Servidor `mcp-server-filesystem` ejecutado vía npx; herramientas `list_directory` y `read_text_file` invocadas sobre `knowledge-base/05_reglas_de_negocio.md`. Evidencia en `docs/skills-mcp/evidencias/mcp-evidencia.md`.
- **Defecto detectado y corregido:** El skill-creator indicaba usar `read_file`, pero ese método está deprecado; se corrigió a `read_text_file`.
