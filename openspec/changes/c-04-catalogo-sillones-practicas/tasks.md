# Tasks — C-04 catálogo de sillones y prácticas

## 1. Modelos de catálogo y constraints

- [x] 1.1 Escribir en `backend/tests/test_catalogo_models.py` los tests que fallan para `TipoPractica` y `Arancel` (creación, `UNIQUE (clinic_id, nombre)`, `UNIQUE (tipo_practica_id)`, FK a clínica) y confirmar que fallan por ausencia de modelos
- [x] 1.2 Agregar `TipoPractica`, `Arancel` y `AuditoriaSena` a `backend/app/domain/clinica/models.py` con `BigInteger`/`Numeric`/`Integer` según design D2 y relaciones `Clinic.tipos_practica`/`Arancel.tipo_practica`; verificar que los tests de 1.1 pasan
- [x] 1.3 Agregar los CHECKs `duracion_min > 0`, `precio_base >= 0`, `precio >= 0` y `sena_pct BETWEEN 0 AND 100` a los modelos y escribir tests que inserten `duracion_min=0`, `sena_pct=-1` y `sena_pct=101` esperando `IntegrityError`; verificar que pasan y que `sena_pct=0`/`100` se aceptan
- [x] 1.4 Verificar aislamiento por `clinic_id` con un test que cree prácticas en dos clínicas y consulte solo una; `pytest backend/tests/test_catalogo_models.py` verde

## 2. Migración 004

- [x] 2.1 Crear `backend/app/infrastructure/db/migrations/versions/004_catalogo_practicas.py` con `revision="004"`, `down_revision="003"` y las tres tablas, CHECKs, UNIQUE e índices de design D2; verificar que `alembic heads` reporta 004 como única cabeza
- [x] 2.2 Escribir `backend/tests/test_migration_004.py` siguiendo el patrón `skipif` de `test_migration_002.py` (tablas, CHECKs, UNIQUE de arancel e índices en Postgres); verificar que corre y se saltea en SQLite sin fallar
- [x] 2.3 Verificar upgrade y downgrade reales contra Postgres con `alembic upgrade head` y `alembic downgrade -1`; confirmar que la base vuelve a 003 sin error

## 3. Seed inicial de prácticas

- [x] 3.1 Extender `backend/tests/test_seed.py` con tests que exijan cinco prácticas con sus cinco aranceles y que una segunda corrida no duplique nada; confirmar que fallan antes de tocar el seed
- [x] 3.2 Agregar al seed las cinco prácticas y aranceles de design D9 en una constante `PRACTICAS_SEED`, con búsqueda idempotente por `(clinic_id, nombre)`; verificar que los tests de 3.1 pasan en Postgres
- [x] 3.3 Documentar en el docstring del seed que los valores de `% seña` son provisorios hasta la respuesta de la pregunta Alta de `knowledge-base/10_preguntas_abiertas.md`; verificar leyendo el docstring y que `python backend/scripts/seed.py` corre dos veces sin duplicar

## 4. Repositorios y regla de precio efectivo

- [x] 4.1 Escribir en `backend/tests/test_catalogo_service.py` los tests de `precio_efectivo` (arancel vigente, arancel futuro, sin arancel) y confirmar que fallan
- [x] 4.2 Implementar `precio_efectivo(tipo, arancel, fecha)` en `backend/app/domain/clinica/catalogo_service.py` con `Decimal` y la precedencia de design D4; verificar que los tests de 4.1 pasan
- [x] 4.3 Agregar `TipoPracticaRepository`, `ArancelRepository` y `AuditoriaSenaRepository` en `backend/app/domain/clinica/repository.py` con listados filtrados por `clinic_id`; verificar con tests de repositorio que no devuelven filas de otra clínica

## 5. Lecturas internas de catálogo y sillones

- [x] 5.1 Escribir tests de API en `backend/tests/test_catalogo_api.py` para `GET /api/internal/tipos-practica` y `GET /api/internal/sillones` (200 con JWT de recepción/odonto/admin, 401 sin token, solo activos y solo de la clínica del token) y confirmar que fallan
- [x] 5.2 Agregar `get_session()` en `backend/app/infrastructure/db/session.py` y crear `backend/app/api/internal/catalogo.py` con ambos GET, `response_model` y `require_role(["recepcion","odonto","admin"])`; verificar que los tests de 5.1 pasan
- [x] 5.3 Registrar el router en `backend/app/main.py` junto a la importación de los modelos nuevos; verificar que `GET /openapi.json` lista los dos endpoints con sus schemas

## 6. Admin de aranceles y auditoría de seña

- [x] 6.1 Escribir tests de API para `GET /api/admin/aranceles` (200 admin, 403 recepción/odonto, forma de la respuesta con precio efectivo y `% seña`) y confirmar que fallan
- [x] 6.2 Crear `backend/app/api/admin/aranceles.py` y `backend/app/api/admin/__init__.py` con el GET admin y montarlo en `/api/admin`; verificar que los tests de 6.1 pasan
- [x] 6.3 Escribir los tests que fallan para `PATCH /api/admin/tipos-practica/{id}/sena-pct`: 200 admin, 422 fuera de rango, 403 no admin, 404 práctica de otra clínica y fila de auditoría con `usuario_id`/antes/después
- [x] 6.4 Implementar el PATCH y `actualizar_sena_pct(...)` en `catalogo_service.py` leyendo `clinic_id` y `sub` del JWT y escribiendo `auditorias_sena` en la misma transacción; verificar que los tests de 6.3 pasan
- [ ] 6.5 Verificar que el PATCH no altera turnos existentes con un test que cree un turno de prueba con `monto_sena` y confirme que el valor queda intacto tras el cambio de `%` — **diferido a C-05** (requiere el modelo `Turno`, que no existe todavía; decisión confirmada por el usuario)

## 7. Frontend admin de aranceles

- [x] 7.1 Reemplazar los datos mock de `frontend/src/pages/AdminPage.tsx` por una consulta a `GET /api/admin/aranceles` con `apiClient`, con estados de carga y error; verificar con `npm run build` y una prueba manual de la tabla contra el backend
- [x] 7.2 Extraer `frontend/src/features/admin/aranceles/components/PracticaSelector.tsx` como componente controlado que reciba la lista de prácticas; verificar que `AdminPage` lo usa y que el build pasa
- [x] 7.3 Conectar la edición de `% seña` al PATCH con validación de rango en el input y refresco de la fila; verificar que un cambio refleja el valor devuelto por el backend

## 8. Integración y cierre técnico

- [x] 8.1 Correr la suite completa (`pytest`) y las herramientas de calidad (`ruff`, `black --check`, `mypy`) sobre el backend; verificar que todo pasa sin errores nuevos
- [x] 8.2 Verificar `openspec validate c-04-catalogo-sillones-practicas` y que `openspec spec validate catalogo-practicas` queda consistente; registrar el resultado
- [x] 8.3 Actualizar la línea de C-04 en `CHANGES.md` para reflejar la migración `004` en lugar de `003`; verificar que la referencia coincide con la revisión real de Alembic

## Workflow follow-up

- Archivar el change recién cuando el usuario lo pida explícitamente; no archivar C-02/C-03 en este flujo.
- Al archivar, sincronizar el delta `catalogo-practicas` al spec principal y marcar C-04 como `[x]` en `CHANGES.md`.
- **Bloqueante preexistente (C-03)**: `003_auth.py` vuelve a agregar `users.password_hash`, que `002_clinica_personas.py` ya crea; `alembic upgrade head` falla en una base nueva con `DuplicateColumnError`. La verificación de 2.3 se hizo aplicando `002` + `alembic stamp 003` en una base temporal y luego `upgrade head`/`downgrade -1` sobre 004. Corregir 003 (quitar el `add_column` duplicado) queda fuera del alcance de C-04.
- **6.5 diferida a C-05**: el test de "el PATCH no muta turnos" necesita el modelo `Turno`.
