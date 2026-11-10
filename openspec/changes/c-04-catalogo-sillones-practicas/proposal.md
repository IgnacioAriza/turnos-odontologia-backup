# Proposal — C-04 catálogo de sillones y prácticas

## Why

C-05 (motor de reservas) necesita saber cuánto dura una práctica, cuánto sale y qué porcentaje de seña corresponde para calcular slots, `monto_sena` y expiración. Hoy no existe ningún modelo de práctica ni de arancel, y el panel admin muestra precios hardcodeados. Sin este catálogo el motor de turnos y el checkout de Mercado Pago (C-08) no tienen de dónde leer un precio confiable ni una foto consistente de la seña.

En v1.0 el catálogo es **lectura + seed**: el ABM completo (US-012) queda para C-13. Lo único editable es el `% seña` global por práctica, que el Admin necesita ajustar sin tocar precios (DD-05, RN-ADMIN-01/02).

## What Changes

- **Modelos nuevos** en `domain/clinica` (según KB 08: "clinic, sillones, prácticas, aranceles"):
  - `TipoPractica`: `clinic_id`, `nombre`, `duracion_min`, `precio_base`, `sena_pct`, `activa` + auditoría. Constraints `duracion_min > 0` y `0 <= sena_pct <= 100`.
  - `Arancel`: `tipo_practica_id` (UNIQUE), `precio`, `sena_pct`, `vigente_desde` + auditoría. FK a `tipos_practica`.
  - `AuditoriaSena`: registro append-only de cada cambio de `% seña` (`quien/cuando/antes/después`).
- **Migración `004_catalogo_practicas`** (no 003: `003_auth.py` ya ocupa esa revisión). Crea `tipos_practica`, `aranceles`, `auditorias_sena` con CHECKs e índices por `clinic_id`.
- **Seed idempotente** de 5 prácticas (limpieza, arreglo, endodoncia, extracción, ortodoncia control) con `duracion_min`, `precio_base` y `sena_pct` provisorios documentados; cada práctica con su `Arancel` 1:1.
- **Endpoints de lectura (JWT)**:
  - `GET /api/internal/tipos-practica` — recepción, odontólogo y admin.
  - `GET /api/internal/sillones` — recepción, odontólogo y admin (solo activos, filtrado por `clinic_id`).
  - `GET /api/admin/aranceles` — solo admin; devuelve práctica + arancel + `% seña`.
- **Único endpoint de escritura en v1.0**: `PATCH /api/admin/tipos-practica/{id}/sena-pct` (solo admin). Valida rango, escribe `AuditoriaSena` y no toca turnos existentes.
- **Precio efectivo**: función de dominio `precio_efectivo(tipo, arancel, fecha)` que devuelve `Arancel.precio` si hay arancel vigente y, si no, `TipoPractica.precio_base`. El `%` siempre sale de `TipoPractica.sena_pct` (única fuente de verdad en v1.0).
- **Frontend**: pantalla admin de aranceles pasa de datos mock a datos reales (tabla + selector de práctica reutilizable por el booking de C-06). La edición de `% seña` se habilita solo para `admin`.
- **Tests**: constraints CHECK de `sena_pct` y `duracion_min`, unicidad de `Arancel.tipo_practica_id`, aislamiento `clinic_id`, RBAC lectura vs escritura, auditoría de cambios y resolución de precio efectivo (la foto del turno se prueba en C-05).

## Capabilities

### New Capabilities

- `catalogo-practicas`: catálogo de prácticas odontológicas, aranceles y configuración del `% seña` por práctica, con lectura interna y administración acotada del porcentaje.

### Modified Capabilities

_(ninguna: `clinica-personas` cubre Clinic/User/Paciente/Sillon/Bloqueo; las entidades nuevas forman su propia capability)._

## Impact

- **Backend**: `app/domain/clinica/models.py` (+`TipoPractica`, `Arancel`, `AuditoriaSena`), `repository.py`, `schemas.py`, nuevo `service.py` con resolución de precio; routers nuevos en `app/api/internal/` y `app/api/admin/`; registro en `app/main.py`; migración `004`; `backend/scripts/seed.py`.
- **Base de datos**: 3 tablas nuevas, 2 CHECKs, 1 UNIQUE, índices `(clinic_id, activa)` y `(clinic_id, nombre)`.
- **API**: 3 endpoints de lectura + 1 PATCH admin. No rompe contratos existentes (no hay endpoints de catálogo hoy).
- **Frontend**: `pages/AdminPage.tsx` + feature `admin/aranceles`; nuevo componente selector de práctica para C-06.
- **Dependencias**: C-03 (JWT + `require_role`) ya está implementado. Habilita C-05 (slots y `monto_sena`) y C-08 (precio de referencia).
- **Fuera de alcance**: ABM de precios/aranceles con vigencia (C-13), alta/edición de prácticas, CRUD de sillones, horarios de atención y asignación sillón↔odontólogo.
