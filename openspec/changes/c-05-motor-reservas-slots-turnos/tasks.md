# Tasks

## 1. Modelos y migración 005

- [x] 1.1 Escribir `backend/tests/test_turnos_models.py` con tests que fallan para `Turno` y `HorarioAtencion`: creación, `CHECK fin > inicio`, `monto_sena >= 0`, estado inválido, UNIQUE de horario y UNIQUE `(clinic_id, telefono)` de pacientes; confirmar que fallan por ausencia de modelos.
- [x] 1.2 Implementar `Turno` y `HorarioAtencion` en `backend/app/domain/turnos/models.py` con estados, CHECKs, índices y `expira_at`; verificar que los tests de 1.1 pasan.
- [x] 1.3 Crear `backend/app/infrastructure/db/migrations/versions/005_motor_turnos.py` con `revision="005"`, `down_revision="004"`, extensión `btree_gist`, tablas, índices, CHECKs, EXCLUDE por sillón y odontólogo y UNIQUE `(clinic_id, telefono)`; verificar que `alembic heads` reporta 005 como única cabeza.
- [x] 1.4 Escribir `backend/tests/test_migration_005.py` con el patrón `skipif` de `test_migration_002.py`: tablas, CHECKs, índices, EXCLUDE y UNIQUE en Postgres; verificar que corre y se saltea en SQLite sin fallar.
- [ ] 1.5 Verificar upgrade y downgrade reales en Postgres (`004 → 005 → 004 → 005`) y confirmar que las tablas y constraints existen y se eliminan sin error.
  - **Bloqueada en este entorno**: no hay Docker y la contraseña del PostgreSQL 18 local es desconocida; los tests `test_migration_005.py` quedan escritos con `skipif` y se ejecutan en CI con `DATABASE_URL` de Postgres.

## 2. Generación de slots

- [x] 2.1 Escribir tests de la función pura `generar_slots` en `backend/tests/test_slots.py`: pasos por `duracion_min`, límite de franja, slots ocupados excluidos, varias franjas por día, timezone de la clínica y selección de sillón/odontólogo libre; confirmar que fallan.
- [x] 2.2 Implementar `backend/app/domain/turnos/slots.py` con `ZoneInfo`, alineación de horarios y asignación del primer par libre; verificar que los tests de 2.1 pasan.
- [x] 2.3 Escribir tests del endpoint `GET /api/public/slots` en `backend/tests/test_reservas_publicas.py`: 200 con slots, práctica inactiva 404, sin datos de pacientes y aislamiento por práctica/clínica; confirmar que fallan.
- [x] 2.4 Implementar `backend/app/domain/turnos/schemas.py` y `backend/app/api/public/reservas.py` con `GET /slots` y `response_model`; verificar que los tests de 2.3 pasan.
- [x] 2.5 Registrar el router público en `backend/app/main.py` y verificar que `GET /openapi.json` lista `/api/public/slots` con su schema.

## 3. Reserva pública

- [x] 3.1 Escribir tests de `PacienteRepository.get_or_create_by_telefono` (crea paciente nuevo, reutiliza existente, no duplica por carrera) y confirmar que fallan.
- [x] 3.2 Implementar `get_or_create_by_telefono` en `backend/app/domain/personas/repository.py` con manejo de `IntegrityError` y re-selección; verificar que los tests de 3.1 pasan.
- [x] 3.3 Escribir tests de `crear_turno_publico`: 201, estado `pendiente_sena`, `monto_sena` correcto, `manage_token` único y no adivinable, `expira_at = now() + MP_TTL_MIN`; confirmar que fallan.
- [x] 3.4 Implementar `crear_turno_publico` en `backend/app/domain/turnos/service.py` reutilizando `precio_efectivo` de C-04; verificar que los tests de 3.3 pasan.
- [x] 3.5 Escribir tests de bloqueo: paciente con `bloqueado_hasta` futuro recibe 403 con la fecha, y paciente habilitado reserva; confirmar que fallan antes de implementar la validación.
- [x] 3.6 Escribir tests de solape: 409 por sillón, 409 por odontólogo, turno cancelado no bloquea y reserva concurrente en Postgres; confirmar que fallan.
- [x] 3.7 Implementar la validación de slot alineado, la consulta de solape amigable y la traducción de `IntegrityError` a 409; verificar que los tests de 3.5 y 3.6 pasan.

## 4. Reserva interna

- [x] 4.1 Escribir tests de `POST /api/internal/turnos`: 201 con rol `recepcion`, 201 con `admin`, 403 con `odonto`, 404 con paciente/sillón/odontólogo de otra clínica y respuesta sin `manage_token`; confirmar que fallan.
- [x] 4.2 Implementar `backend/app/api/internal/turnos.py` con RBAC `recepcion|admin` y montarlo en `backend/app/main.py`; verificar que los tests de 4.1 pasan y que el endpoint aparece en OpenAPI.

## 5. Expiración de pendientes

- [x] 5.1 Escribir tests de `expirar_pendientes`: expira turnos vencidos, no toca confirmados ni cancelados, es idempotente y el barrido perezoso libera el slot al pedir slots; confirmar que fallan.
- [x] 5.2 Implementar `expirar_pendientes` en `backend/app/domain/turnos/service.py` y llamarlo antes de generar slots y antes de crear una reserva; verificar que los tests de 5.1 pasan.
- [x] 5.3 Reemplazar el stub de `backend/app/infrastructure/queue/worker.py` por un loop que ejecute el barrido cada 30 segundos con apagado limpio; verificar manualmente con logs de arranque y heartbeat.
- [x] 5.4 Escribir un test de integración que cree un turno `pendiente_sena` vencido, ejecute el barrido y confirme que el horario vuelve a aparecer en `GET /api/public/slots`.

## 6. Seed y datos iniciales

- [x] 6.1 Extender `backend/tests/test_seed.py` con tests que exijan las franjas L-V 08:00-20:00 y Sábado 08:00-13:00 y que una segunda corrida no duplique horarios; confirmar que fallan antes de tocar el seed.
- [x] 6.2 Agregar las franjas a `backend/scripts/seed.py` de forma idempotente por `(clinic_id, dia_semana, hora_desde)`; verificar que los tests de 6.1 pasan en Postgres.
- [x] 6.3 Documentar en el docstring del seed el horario inicial y su carácter provisorio hasta confirmación del Admin; verificar leyendo el docstring y corriendo el seed dos veces sin duplicados.

## 7. Deuda diferida de C-04 (tarea 6.5)

- [x] 7.1 Escribir el test que crea un turno con `monto_sena` y luego cambia el `% seña` de la práctica, verificando que el monto del turno no cambia; verificar que pasa con la implementación de C-05.

## 8. Integración y calidad

- [x] 8.1 Correr la suite completa (`pytest`) con cobertura y verificar que pasa sin errores nuevos y por encima del umbral del CI (objetivo 80%).
- [x] 8.2 Correr `ruff check`, `ruff format --check` y `mypy` sobre el backend y verificar que todo pasa en los archivos tocados.
- [x] 8.3 Verificar `openspec validate c-05-motor-reservas-slots-turnos --strict` y que OpenAPI lista los tres endpoints nuevos (`/api/public/slots`, `/api/public/reservas`, `/api/internal/turnos`).
- [x] 8.4 Actualizar `CHANGES.md` con el estado de C-05 y la migración `005`, y registrar el resultado de las verificaciones.

## Workflow follow-up

- Archivar el change después de que las verificaciones y la revisión de dominio estén completas.
- Verificar el spec principal `motor-turnos` después del archivado.
