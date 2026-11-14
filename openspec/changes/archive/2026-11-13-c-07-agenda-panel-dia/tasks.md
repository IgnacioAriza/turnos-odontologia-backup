# Tasks — C-07 agenda-panel-dia

> **TDD ley de hierro**: cada tarea de implementación se escribe como test que falla primero (RED por la razón correcta), luego el cambio mínimo para pasar (GREEN) y al final la suite `pytest` completa en verde. Las tareas de test y de implementación van separadas a propósito para que el ciclo quede auditable.

## 1. Preparación y gates

- [x] 1.1 Revisión humana de governance ALTO: confirmar con el responsable la regla de bloqueo por 2 faltas (30 días, reinicio de `faltas_count`, extensión si falta estando bloqueado) y la excepción de recepción (roles, motivo obligatorio, sin tope). Verificación: decisión registrada en `design.md` §Open Questions con fecha y responsable; sin esto no se escribe código.
- [x] 1.2 Verificar el estado real de partida: `alembic heads` = `006`, existen `Paciente.faltas_count`, `Paciente.bloqueado_hasta`, tabla `bloqueos`, `Turno` con `sena_perdida` y `require_odonto_confinement`. Verificación: `pytest backend/tests/test_turnos_models.py backend/tests/test_gestion_interna.py` pasa antes de tocar nada.
- [x] 1.3 Escribir un test de contrato que falle si el 403 de bloqueo no trae `codigo=bloqueado` ni `bloqueado_hasta`. Verificación: el test falla hoy contra `_verificar_bloqueo` y queda en `backend/tests/test_bloqueo_contrato.py`.

## 2. Migración 007 y modelo de excepción

- [x] 2.1 Escribir `backend/tests/test_migration_007.py` (`skipif` Postgres): upgrade crea `excepciones_bloqueo` con columnas, FK e índices; downgrade la elimina. Verificación: el test falla porque la migración no existe.
- [x] 2.2 Crear `backend/app/infrastructure/db/migrations/versions/007_excepciones_bloqueo.py` (`down_revision="006"`). Verificación: `test_migration_007.py` pasa y `alembic upgrade head` deja `heads = 007`.
- [x] 2.3 Escribir `backend/tests/test_excepciones_bloqueo.py`: modelo con `clinic_id`, `paciente_id`, `turno_id` único, `usuario_id`, `motivo`, `created_at`, `is_active`; `clinic_id` NOT NULL. Verificación: el test falla porque el modelo no existe.
- [x] 2.4 Crear `ExcepcionBloqueo` en `backend/app/domain/clinica/models.py` y `ExcepcionBloqueoRepository` en `repository.py`. Verificación: `test_excepciones_bloqueo.py` pasa.

## 3. Bloqueo en el alta y excepción auditada

- [x] 3.1 Escribir en `backend/tests/test_turnos_service.py` los casos: público bloqueado → 403 `bloqueado` con `bloqueado_hasta`; interno sin motivo → 403; interno con motivo → turno creado + fila de excepción; motivo vacío → 422 `motivo_requerido`; motivo en el cuerpo público → ignorado. Verificación: los casos fallan por el contrato actual.
- [x] 3.2 Agregar `CODIGO_BLOQUEADO` y `CODIGO_MOTIVO_REQUERIDO` en `backend/app/domain/turnos/gestion.py` y cambiar `_verificar_bloqueo` para lanzar `ForbiddenError(code=..., extra={"bloqueado_hasta": iso})`. Verificación: los casos públicos e internos sin motivo pasan.
- [x] 3.3 Extender `crear_turno_interno` con `motivo_excepcion` y `usuario_id`: validar motivo, crear el turno y la `ExcepcionBloqueo` en la misma transacción, y loguear `excepcion_bloqueo`. Verificación: los casos con motivo y motivo vacío pasan; un test fuerza el fallo del turno y comprueba que no queda excepción huérfana.
- [x] 3.4 Extender `TurnoInternoIn` con `motivo_excepcion` opcional y `POST /api/internal/turnos` para pasar `usuario_id` y el motivo. Verificación: `backend/tests/test_turnos_api.py` cubre 201 con motivo, 403 sin motivo y 422 con motivo vacío; OpenAPI muestra el campo.

## 4. Agenda backend

- [x] 4.1 Escribir `backend/tests/test_agenda.py`: vista día, vista semana (lunes a domingo), rango por zona de la clínica, filtros por sillón/odontólogo/estado, `cancelado` excluido por defecto e incluido con `estado=cancelado`, orden estable, día vacío. Verificación: los tests fallan porque el endpoint no existe.
- [x] 4.2 Agregar `list_agenda` al `TurnoRepository` con filtros y orden, y `AgendaService` en `backend/app/domain/turnos/service.py` con el cálculo de rango día/semana. Verificación: los tests de rango, filtros y orden pasan.
- [x] 4.3 Escribir los tests de aislamiento y confinamiento: turnos de otra clínica nunca aparecen, filtro con sillón ajeno devuelve lista vacía, `odonto` solo ve su `sub` aunque envíe otro `odontologo`, `recepcion`/`admin` ven todo. Verificación: fallan antes de implementar el confinamiento.
- [x] 4.4 Crear `backend/app/api/internal/agenda.py` con `GET /api/internal/agenda`, `response_model` y `require_odonto_confinement`, y registrarlo en `app/main.py` bajo `/api/internal`. Verificación: los tests de agenda y confinamiento pasan; `/openapi.json` lista el endpoint con sus query params.
- [x] 4.5 Escribir el test de `GET /api/internal/odontologos` (roles, aislamiento por clínica, solo activos) y crear el endpoint en `backend/app/api/internal/catalogo.py`. Verificación: el test pasa y el filtro del frontend tiene fuente real.
- [x] 4.6 Escribir un test Postgres `skipif` que corre `EXPLAIN (ANALYZE, BUFFERS)` sobre la consulta de agenda de una semana y falla si aparece un `Seq Scan` sobre `turnos`. Verificación: el test documenta el plan antes/después en el mensaje y pasa en Postgres.

## 5. Panel del día backend

- [x] 5.1 Escribir `backend/tests/test_panel_dia.py`: lista ordenada por hora, estados `cancelado`/`reprogramado` fuera, resumen de la jornada, día vacío. Verificación: fallan porque el endpoint no existe.
- [x] 5.2 Implementar `GET /api/internal/panel/dia` en `backend/app/api/internal/panel.py` con el servicio de panel, `response_model` y RBAC `recepcion|admin|odonto` confinado. Verificación: los tests de listado y confinamiento pasan.
- [x] 5.3 Escribir los tests de `estado_sena` (`pendiente`, `aprobada`, `perdida`, `no_requerida`) y de teléfono visible solo para turnos operables. Verificación: fallan antes del helper.
- [x] 5.4 Implementar el helper único de `estado_sena` en el dominio de turnos, documentado como contrato reemplazable por C-09. Verificación: los cuatro casos pasan y el frontend recibe un enum estable.
- [x] 5.5 Escribir los tests de `PATCH /api/internal/panel/turnos/{id}`: `confirmado→completado`, `confirmado→ausente`, destino inválido 422, `pendiente_sena`/`cancelado`/`reprogramado` → 409 `estado_no_actualizable`, otra clínica 404, turno de otro odontólogo 404. Verificación: fallan porque el endpoint no existe.
- [x] 5.6 Implementar el marcado con la máquina de estados de `design.md` D5, idempotente para el mismo destino y sin efectos en el reintento. Verificación: los tests de estado e idempotencia pasan (`ausente` repetido no vuelve a sumar falta).
- [x] 5.7 Escribir los tests de ausentismo: 1.ª falta no bloquea; 2.ª falta crea `Bloqueo` con `motivo="2_faltas"`, `hasta=now+30d`, `created_by` y reinicia `faltas_count`; fallo del bloqueo revierte el `ausente`; falta estando bloqueado extiende `bloqueado_hasta`; expiración de seña no suma falta. Verificación: fallan antes de implementar el conteo.
- [x] 5.8 Implementar el conteo de faltas y el bloqueo transaccional con `SELECT ... FOR UPDATE` sobre el paciente y log `bloqueo_automatico`. Verificación: los tests de ausentismo pasan.
- [x] 5.9 Escribir un test Postgres `skipif` de dos marcados `ausente` concurrentes del mismo paciente y verificar que se crea un solo `Bloqueo`. Verificación: pasa en Postgres y queda `skipif` documentado para SQLite.

## 6. Gate de diseño UI (bloquea 7.x y 8.x)

- [x] 6.1 Crear `openspec/changes/c-07-agenda-panel-dia/mockups/` con `agenda.html`, `panel-dia.html`, `odonto.html` y `README.md`, importando `design-system/tokens.css`, `brand.js` y `assets/logo.svg`, con los estados listados en `design.md` §UI Mockups. Verificación: los cuatro archivos existen y no tienen colores ni espaciados hardcodeados.
- [x] 6.2 Renderizar cada mockup a 390×844 y 1440×900 y guardar las capturas en `mockups/previews/`. Verificación: las imágenes existen, fueron inspeccionadas y no hay scroll horizontal ni controles táctiles menores a 44 px.
- [x] 6.3 Presentar los mockups al usuario y registrar la aprobación. Verificación: `mockups/README.md` y `design.md` §UI Mockups pasan a `Approval: approved (<fecha>, by user)`; sin esto no se implementa 7.x ni 8.x.

## 7. Frontend — agenda

- [x] 7.1 Crear `frontend/src/features/agenda/types.ts` y `api.ts` con los contratos de agenda, odontólogos y alta interna, sin `any`. Verificación: `npx tsc --noEmit` pasa y los tipos cubren `solape`, `bloqueado` y `motivo_requerido`.
- [x] 7.2 Escribir tests vitest de `AgendaDia` y `AgendaSemana`: render por hora y sillón, cambio día/semana, filtros, día vacío y error de red con reintento. Verificación: fallan porque los componentes no existen.
- [x] 7.3 Implementar `AgendaDia`, `AgendaSemana` y `FiltrosAgenda` mobile-first consumiendo la API real, con estados de carga, vacío y error. Verificación: los tests de 7.2 pasan.
- [x] 7.4 Escribir tests de `AltaTurnoDialog` y `ExcepcionBloqueoDialog`: 201 cierra y refresca, 409 `solape` conserva datos, 403 `bloqueado` muestra `bloqueado_hasta` y pide motivo solo a `recepcion|admin`. Verificación: fallan antes de los componentes.
- [x] 7.5 Implementar el alta de turno interno y el diálogo de excepción con confirmación accesible. Verificación: los tests de 7.4 pasan.
- [x] 7.6 Actualizar `frontend/src/pages/AgendaPage.tsx` para componer la feature según el rol y `router.tsx` para admitir `recepcion` en `/agenda`, conservando `ProtectedRoute`/`PublicRoute`. Verificación: test de router confirma que `recepcion` entra a `/agenda` y `odonto` no ve acciones de alta.

## 8. Frontend — panel del día y vista odontólogo

- [x] 8.1 Crear `frontend/src/features/panel-dia/types.ts` y `api.ts` con panel, marcado y `estado_sena`, sin `any`. Verificación: `npx tsc --noEmit` pasa.
- [x] 8.2 Escribir tests vitest de `PanelLista` y `ContactoWhatsApp`: orden por hora, badge de seña con texto (no solo color), link `wa.me` con el teléfono, resumen de jornada. Verificación: fallan porque los componentes no existen.
- [x] 8.3 Implementar `PanelLista`, `ContactoWhatsApp` y el resumen mobile-first. Verificación: los tests de 8.2 pasan.
- [x] 8.4 Escribir tests de `MarcarEstadoDialog`: confirmación de `ausente`, aviso de bloqueo de 30 días cuando corresponde, idempotencia visible y 409 `estado_no_actualizable` que refresca el turno. Verificación: fallan antes del diálogo.
- [x] 8.5 Implementar `MarcarEstadoDialog` y conectar `frontend/src/pages/PanelPage.tsx` a la API real. Verificación: los tests de 8.4 pasan.
- [x] 8.6 Escribir el test de la vista odontólogo: solo su día, sin alta, sin cancelar/reprogramar, con acciones de llegada/ausencia sobre sus turnos. Verificación: falla contra la página actual.
- [x] 8.7 Ajustar `AgendaPage`/`PanelPage` y `OdontoShell` para el modo odontólogo sin ABM. Verificación: el test de 8.6 pasa y no aparece ningún botón de alta/cancelar/reprogramar con rol `odonto`.

## 9. Documentación y roadmap

- [x] 9.1 Verificar la renumeración en `CHANGES.md`: C-07 usa la migración `007`, C-09 `008`, C-10 `009`, y la nota de migraciones está corregida. Verificación: `Select-String "Migración 00" CHANGES.md` muestra la secuencia 005, 006, 007, 008, 009 sin duplicados.
- [x] 9.2 Documentar en `knowledge-base/04_modelo_de_datos.md` §Bloqueo la tabla `excepciones_bloqueo` y la regla de reinicio de `faltas_count`. Verificación: el documento menciona ambas y coincide con `design.md` D6/D7.
- [x] 9.3 Actualizar `AGENTS.md`/`CLAUDE.md` solo si cambia una regla dura o una convención de error; si no cambia, dejar constancia en `design.md`. Verificación: revisión manual de que no hay reglas desactualizadas.

## 10. Integración y calidad

- [x] 10.1 `ruff check backend/app backend/tests` y `ruff format --check` limpios. Verificación: ambos comandos terminan con código 0.
- [x] 10.2 `mypy backend/app` limpio. Verificación: sin errores nuevos respecto de la línea base.
- [x] 10.3 `pytest` completo con cobertura > 80 % (incluye `test_agenda`, `test_panel_dia`, `test_excepciones_bloqueo`, `test_migration_007`). Verificación: suite completa en verde y reporte de cobertura por encima del umbral.
- [x] 10.4 `npx tsc --noEmit`, `npm run build` y `vitest` completos en `frontend/`. Verificación: build sin errores de tipos y todos los tests de frontend en verde.
- [x] 10.5 Verificar OpenAPI completa de los endpoints nuevos (`response_model`, query params documentados, códigos de error). Verificación: `/openapi.json` contiene `agenda`, `panel/dia`, `panel/turnos/{id}` y `odontologos`.
- [x] 10.6 Verificación visual contra los mockups aprobados en 6.3 (agenda día, agenda semana, panel, odonto y diálogos de alta/excepción/ausencia) en 390×844 y 1440×900, claro y oscuro, con consola y red sin errores. Verificación: 14 capturas en `mockups/verify/`, 0 px de overflow, contraste AA y diferencias reportadas por prioridad en `mockups/verify/resumen.md`.

## Workflow follow-up

- Marcar C-07 como implementado en `CHANGES.md` solo al archivar.
- Archivar el change con `/opsx:archive c-07-agenda-panel-dia` después de la revisión de governance y de la verificación visual.
- Revisar que C-09 y C-10 sigan usando las migraciones `008` y `009` cuando se propongan.
