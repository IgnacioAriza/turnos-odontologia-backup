# Design — C-04 catálogo de sillones y prácticas

## Context

Ver `proposal.md` — Why. Estado relevante del repo:

- C-02 ya define `Clinic`, `Sillon`, `User`, `Paciente`, `Bloqueo` en `backend/app/domain/clinica` y `backend/app/domain/personas`, todos con `AuditMixin` y `clinic_id` obligatorio.
- C-03 ya expone `get_current_user`, `require_role(...)` y `require_odonto_confinement(...)` en `app/domain/auth/dependencies.py`.
- La revisión Alembic `003` ya está tomada por `003_auth.py`; la última migración es 003.
- `backend/scripts/seed.py` ya crea clínica, usuarios y sillones de forma idempotente.
- Los tests corren contra SQLite (`sqlite+aiosqlite:///./test.db`) salvo los que consultan catálogos de Postgres, que se saltean con `skipif`.
- KB 08 ubica prácticas y aranceles dentro del dominio `clinica` ("clinic, sillones, prácticas, aranceles"), por lo que no se crea un dominio nuevo.

## Goals / Non-Goals

**Goals:**

- Persistir prácticas y aranceles con constraints reales en base (no solo en Pydantic).
- Dejar una única fuente de verdad para el `% seña` en v1.0.
- Exponer lecturas internas estables para C-05/C-06 y una escritura auditada acotada para admin.
- Permitir que el frontend admin deje de mostrar datos mock.
- Preparar la foto de precio de C-05 sin implementarla acá.

**Non-Goals:**

- ABM de prácticas, altas/bajas de aranceles y versionado de precios (C-13).
- Asignación sillón↔odontólogo y horarios de atención (C-05).
- Endpoints públicos de catálogo (los agrega C-06 sobre el mismo servicio).
- Tocar `Turno`, `monto_sena` o cualquier lógica de reservas (C-05).
- Migrar la autenticación del frontend a cookies HttpOnly (deuda de C-03).

## Decisions

### D1 — Modelos en `domain/clinica`, servicio en `catalogo_service.py`

`TipoPractica`, `Arancel` y `AuditoriaSena` se agregan a `backend/app/domain/clinica/models.py`, junto a `Clinic`/`Sillon`, porque KB 08 asigna prácticas y aranceles a ese dominio y así se reutiliza la relación con `Clinic`.

La lógica de resolución de precio y de actualización auditada vive en `backend/app/domain/clinica/catalogo_service.py`; los routers quedan finos. Alternativa descartada: un dominio `catalogo` nuevo, que contradice la estructura fijada en el spec de C-01 sin aportar límites reales.

### D2 — Migración `004_catalogo_practicas`

Se usa la revisión `004` con `down_revision = "003"`. `CHANGES.md` dice "Migración 003", pero ese número ya lo ocupa `003_auth.py`; crear una segunda revisión 003 rompería la cadena de Alembic. Se documenta la discrepancia y se corrige `CHANGES.md` al archivar C-04.

Tablas:

| Tabla | Columnas | Constraints |
|---|---|---|
| `tipos_practica` | `id` UUID PK, `clinic_id` FK, `nombre`, `duracion_min`, `precio_base`, `sena_pct`, `activa` + `AuditMixin` | `CHECK duracion_min > 0`, `CHECK precio_base >= 0`, `CHECK sena_pct BETWEEN 0 AND 100`, `UNIQUE (clinic_id, nombre)`, índice `(clinic_id, activa)` |
| `aranceles` | `id` UUID PK, `tipo_practica_id` FK, `precio`, `sena_pct`, `vigente_desde` + `AuditMixin` | `UNIQUE (tipo_practica_id)`, `CHECK precio >= 0`, `CHECK sena_pct BETWEEN 0 AND 100` |
| `auditorias_sena` | `id` UUID PK, `clinic_id` FK, `tipo_practica_id` FK, `usuario_id` FK a `users` (`SET NULL`), `valor_anterior`, `valor_nuevo` + `AuditMixin` | índice `(clinic_id, tipo_practica_id, created_at)` |

`precio_base` y `precio` son `Numeric(12,2)`; `sena_pct` y los valores de auditoría son `Integer`, porque el contrato v1.0 acepta porcentajes enteros.

### D3 — `TipoPractica.sena_pct` es la única fuente de verdad del porcentaje

`Arancel.sena_pct` existe porque el modelo de KB lo pide y porque C-13 lo va a versionar, pero en v1.0 **no se lee para calcular la seña**. El seed lo copia desde la práctica para que no quede nulo, y el PATCH de C-04 actualiza solo `TipoPractica.sena_pct`. Alternativa descartada: escribir el `%` en ambas tablas, que crea dos fuentes que se pueden desincronizar sin un flujo de sincronización.

### D4 — Precio efectivo como función de dominio pura

`precio_efectivo(tipo, arancel, fecha)` devuelve `arancel.precio` cuando existe un arancel con `vigente_desde <= fecha`; si no, `tipo.precio_base`. Trabaja con `Decimal` y es una función pura, testeable sin base.

La foto definitiva (`Turno.monto_sena`) se implementa en C-05: C-04 solo garantiza que el precio de referencia sea determinístico. El `monto_sena` se calculará como `round(precio_efectivo * sena_pct / 100)`.

### D5 — Auditoría append-only en tabla propia

Cada PATCH inserta una fila en `auditorias_sena` con `clinic_id`, `tipo_practica_id`, `usuario_id` (claim `sub`), `valor_anterior`, `valor_nuevo` y `created_at`. No se actualiza ni se borra nunca; se hereda `AuditMixin` solo por consistencia con el resto de las tablas de negocio.

Alternativa descartada: log estructurado, que no es consultable ni sirve como evidencia funcional de RN-ADMIN-01. Alternativa descartada: tabla de auditoría genérica, sobrerrediseño para una sola entidad en v1.0.

### D6 — Routers separados por superficie de permiso

- `app/api/internal/catalogo.py`, montado en `/api/internal`: `GET /tipos-practica` y `GET /sillones`, ambos con `require_role(["recepcion", "odonto", "admin"])`.
- `app/api/admin/aranceles.py`, montado en `/api/admin`: `GET /aranceles` y `PATCH /tipos-practica/{id}/sena-pct`, ambos con `require_role(["admin"])`.
- Se agrega `app/api/admin/__init__.py` y se registran ambos routers en `main.py` junto a los modelos nuevos.

`clinic_id` y `sub` salen siempre del JWT; nunca del body ni del path. Un `tipo_practica_id` de otra clínica responde 404, no 403, para no filtrar existencia.

### D7 — Dependencia de sesión por request

Se agrega `get_session()` en `app/infrastructure/db/session.py` como generador async que abre y cierra `async_session()` por request. Los routers nuevos lo usan con `Depends`. No se reutiliza el patrón de `get_auth_service` (que crea una sesión propia) porque acá la sesión debe compartirse entre repositorio y servicio dentro de la misma transacción.

### D8 — Precios en `Decimal` internamente, número en la API

La persistencia y los cálculos usan `Decimal`. Los schemas `Out` exponen `precio` como `float` redondeado a dos decimales para que el frontend lo formatee sin parsear strings. Esto es aceptable porque el redondeo ocurre en el borde de salida y la aritmética de seña se hace en C-05 con `Decimal`.

### D9 — Seed provisorio documentado

Se siembran las cinco prácticas con estos valores iniciales, tomados de la tabla mock del admin y sujetos a la pregunta P-Alta de `10_preguntas_abiertas.md`:

| Práctica | `duracion_min` | `precio_base` | `sena_pct` |
|---|---|---|---|
| Limpieza | 30 | 15.000 | 30 |
| Arreglo | 45 | 25.000 | 40 |
| Endodoncia | 60 | 45.000 | 30 |
| Extracción | 30 | 20.000 | 30 |
| Ortodoncia control | 20 | 12.000 | 20 |

Cada práctica se crea con su `Arancel` 1:1 (`precio = precio_base`, mismo `sena_pct`, `vigente_desde = hoy`). El seed busca por `(clinic_id, nombre)` antes de insertar, igual que el seed actual.

### D10 — Frontend: feature `admin/aranceles` + selector compartido

`AdminPage.tsx` deja de tener filas hardcodeadas y consume `GET /api/admin/aranceles` con `apiClient` (que ya inyecta el Bearer desde `localStorage`). La tabla muestra nombre, duración, precio, `% seña` y activo; el botón de edición abre un input acotado a `admin` que llama al PATCH y refresca la fila.

El selector de práctica se extrae a `frontend/src/features/admin/aranceles/components/PracticaSelector.tsx` para que C-06 lo reutilice. La pantalla admin le pasa la lista ya cargada; el componente no hace fetch propio (así sirve tanto al endpoint admin como al futuro público).

## Risks / Trade-offs

- **`CHANGES.md` dice migración 003 y el código usa 004** → se documenta acá y se corrige el índice al archivar C-04; las tareas lo incluyen como paso explícito.
- **Degradación de mensajes de constraint en SQLite** → los tests de modelo verifican los CHECK ejecutando el insert; los tests de migración con `information_schema`/`pg_constraint` se marcan `skipif` para SQLite, siguiendo el patrón de `test_migration_002.py`.
- **`Arancel.sena_pct` puede quedar desactualizado** → se ignora en v1.0 y C-13 define el flujo de versionado; el seed lo mantiene igual a la práctica.
- **Valores de seed provisorios** → quedan aislados en una constante del seed y documentados; cambiarlos no requiere migración.
- **Duplicación `precio_base`/`precio`** → el precio efectivo prioriza `Arancel` y cae a `precio_base`, evitando dos caminos de cálculo distintos.
- **El token vive en `localStorage`** → deuda heredada de C-03; no se resuelve en C-04.
- **El login no devuelve `user` y `useAuth` lo espera** → bug preexistente de C-03; fuera de alcance, se anota para un change de corrección.

## Migration Plan

1. `alembic upgrade head` aplica `004` después de `003`.
2. Correr `python backend/scripts/seed.py` para sembrar prácticas y aranceles (idempotente).
3. Rollback: `alembic downgrade -1` elimina `auditorias_sena`, `aranceles` y `tipos_practica`, volviendo a 003. El seed no se revierte automáticamente.
4. Al archivar, actualizar la línea de C-04 en `CHANGES.md` (migración 004) y marcar las tareas.

## Open Questions

- ¿Los `% seña` definitivos por práctica? Bloquea solo los valores del seed, no el diseño; se usan los provisorios de D9 hasta que Admin responda la pregunta Alta de `10_preguntas_abiertas.md`.
- ¿`Arancel.precio` reemplaza a `TipoPractica.precio_base` en C-13? Se resuelve en el diseño de C-13; en v1.0 conviven con la precedencia de D4.
