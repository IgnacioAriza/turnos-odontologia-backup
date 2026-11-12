# Tasks

## 1. Prerrequisitos de C-05

- [x] 1.1 Verificar que C-05 está implementado: `Turno` con `manage_token`, `generar_slots`, `crear_turno_publico`, endpoints `GET /api/public/slots` y `POST /api/public/reservas`, y migración `005` en `alembic heads`; documentar el resultado en `tasks.md` y no avanzar si falta algo.
- [x] 1.2 Correr `pytest`, `ruff check` y `mypy` antes de tocar nada y guardar la línea base de resultados para distinguir fallas nuevas de fallas heredadas.

## 2. Migración 006

- [x] 2.1 Escribir `backend/tests/test_migration_006.py` con el patrón `skipif` de Postgres de `test_migration_004.py`: `turnos.sena_perdida` existe con default `false` y `NOT NULL`, `turnos.reprogramado_de_id` existe con FK a `turnos.id` y es nullable; confirmar que falla por ausencia de la migración.
- [x] 2.2 Crear `backend/app/infrastructure/db/migrations/versions/006_gestion_turnos.py` con `revision="006"`, `down_revision="005"`, las dos columnas y su FK; verificar que los tests de 2.1 pasan y que `alembic heads` reporta `006` como única cabeza.
- [ ] 2.3 Verificar upgrade y downgrade reales en Postgres (`005 → 006 → 005 → 006`) y confirmar que las columnas y la FK se crean y se eliminan sin error.
- [x] 2.4 Agregar `sena_perdida` y `reprogramado_de_id` al modelo `Turno` (mapeo y relación `reprogramado_de`) y verificar que `test_turnos_models.py` de C-05 sigue pasando.

## 3. Dominio: ventana, estados y cancelación

- [x] 3.1 Escribir `backend/tests/test_gestion_ventana.py` con la función pura de ventana: 12h exactas se acepta, 11h59 se rechaza, se evalúa en `America/Argentina/Buenos_Aires`; confirmar que falla por ausencia del módulo.
- [x] 3.2 Implementar `backend/app/domain/turnos/gestion.py` con `dentro_de_ventana(inicio, now, tz)` y las constantes de estado gestionable; verificar que los tests de 3.1 pasan.
- [x] 3.3 Escribir tests de `cancelar_turno`: turno vigente dentro de ventana, turno `pendiente_sena`, turno `cancelado`/`completado`/`ausente` rechazado con `estado_no_gestionable`, cancelación tardía sin confirmar rechazada y con confirmar ejecutada; confirmar que fallan.
- [x] 3.4 Implementar `cancelar_turno` en `backend/app/domain/turnos/service.py`: pasa a `cancelado`, marca `sena_perdida` solo si había seña aprobada y la cancelación fue tardía, y emite la señal de recordatorio; verificar que los tests de 3.3 pasan.
- [x] 3.5 Escribir un test de integración que cancele un turno y confirme que el horario vuelve a `GET /api/public/slots` y que una reserva nueva sobre ese horario devuelve 201; confirmar que falla antes de 3.4 y pasa después.

## 4. Dominio: reprogramación

- [x] 4.1 Escribir tests de la 1.ª reprogramación: mismo `turno_id`, `monto_sena` intacto, `inicio` nuevo, `reprogramaciones_count=1`, `manage_token` intacto, `expira_at` sin extender si seguía `pendiente_sena`; confirmar que fallan.
- [x] 4.2 Implementar `reprogramar_turno` para el caso `reprogramaciones_count=0` en `backend/app/domain/turnos/service.py`, reutilizando el motor de slots y la validación de solape de C-05; verificar que los tests de 4.1 pasan.
- [x] 4.3 Escribir tests del rechazo del caso ocupado y del caso fuera de franja: 409 `solape` y 422 `slot_invalido`, con el turno original sin cambios; confirmar que fallan y luego pasan con la implementación de 4.2.
- [x] 4.4 Escribir tests de la 2.ª reprogramación: sin confirmar devuelve 409 `requiere_nueva_sena` sin crear ni modificar nada; con `confirmar_perdida_sena=true` deja el turno anterior en `cancelado` con `sena_perdida=true`, crea el nuevo en `pendiente_sena` con `reprogramado_de_id`, `reprogramaciones_count=1`, `monto_sena` recalculado y `manage_token` distinto; confirmar que fallan.
- [x] 4.5 Implementar la rama de segunda reprogramación en `reprogramar_turno`; verificar que los tests de 4.4 pasan y que el turno nuevo expira igual que cualquier `pendiente_sena`.
- [x] 4.6 Escribir el test de que el horario liberado por la segunda reprogramación es re-reservable y que el nuevo turno no hereda el `manage_token` anterior; verificar que pasa.

## 5. Señal de recordatorio

- [x] 5.1 Escribir tests del puerto de recordatorio: `cancelar` se llama al cancelar, `reprogramar` se llama con el nuevo `inicio` al reprogramar y la gestión completa sin error con la implementación no-op; confirmar que fallan.
- [x] 5.2 Implementar `RecordatorioPort` y `NoOpRecordatorio` en `backend/app/domain/notificaciones/` e inyectarlos en el servicio de turnos; verificar que los tests de 5.1 pasan.

## 6. API pública de gestión

- [x] 6.1 Escribir `backend/tests/test_gestion_publica.py`: `GET /api/public/gestion/{token}` devuelve 200 con estado, inicio, fin, práctica, `monto_sena` y `reprogramaciones_count`, sin `manage_token` en el cuerpo y con `Cache-Control: no-store`; confirmar que falla.
- [x] 6.2 Implementar `backend/app/api/public/gestion.py` con el `GET` y los schemas en `backend/app/domain/turnos/schemas.py`; montar el router en `backend/app/main.py` y verificar que los tests de 6.1 pasan y el endpoint aparece en `GET /openapi.json`.
- [x] 6.3 Escribir tests de token inválido (403 `token_invalido`, nunca 401), turno inexistente (404) y token de un turno de otra clínica (404), verificando que la respuesta no revela existencia; confirmar que fallan y luego pasan.
- [x] 6.4 Escribir el test de redacción: el `manage_token` no aparece en el log del request de gestión y sí el `turno_id`; implementar el logger estructurado del canal público y verificar que el test pasa.
- [x] 6.5 Escribir tests de los `POST` públicos: cancelar y reprogramar con token válido, 409 `requiere_confirmacion` con `perdida_sena=true` dentro de la ventana, y 409 `requiere_nueva_sena` en la segunda reprogramación; implementar los endpoints y verificar que los tests pasan.
- [x] 6.6 Generalizar `backend/app/core/rate_limit.py` a `check_rate_limit(scope, key, limit, window)` conservando login en 5/60s; verificar que `test_rate_limit.py` sigue pasando y agregar el test de gestión por IP y por token devolviendo 429 con `Retry-After`.
- [x] 6.7 Aplicar el limitador a las rutas públicas de gestión (`gestion_ip` 30/60s, `gestion_token` 10/60s) y verificar con test que el exceso devuelve 429.

## 7. API interna de gestión

- [x] 7.1 Escribir `backend/tests/test_gestion_interna.py`: `recepcion` cancela con `motivo` y recibe 200, `admin` puede, `odonto` recibe 403, un turno de otra clínica da 404 y la cancelación sin `motivo` da 422; confirmar que fallan.
- [x] 7.2 Implementar `cancelar` y `reprogramar` en `backend/app/api/internal/turnos.py` con `require_role("recepcion", "admin")`, `clinic_id` del JWT y `motivo` obligatorio; verificar que los tests de 7.1 pasan y que el motivo queda en el log de dominio con `usuario_id`.
- [x] 7.3 Escribir el test de que la gestión interna aplica las mismas reglas de ventana y de 2.ª reprogramación que el canal público, y verificar que pasa.

## 8. Frontend: base compartida del canal público

- [x] 8.1 Escribir tests de `normalizarTelefonoAR` en `frontend/src/features/booking/normalizarTelefono.test.ts`: `11 5555 1234` → `+5491155551234`, entrada con `+54 9`, entrada corta → `null`; confirmar que fallan.
- [x] 8.2 Implementar `frontend/src/features/booking/normalizarTelefono.ts` y verificar que los tests de 8.1 pasan.
- [x] 8.3 Crear `frontend/src/shared/api-client/public-client.ts` sin el interceptor de 401 y sin `Authorization`, y un test que verifique que no agrega el header aunque exista `access_token` en `localStorage`.
- [x] 8.4 Definir `frontend/src/features/booking/types.ts` con los contratos de slot, reserva y gestión, y verificar que `npm run build` compila sin `any` y sin errores de tipos.

## 8b. Catálogo público de prácticas (ampliación aprobada 2026-11-11)

- [x] 8b.1 Escribir `backend/tests/test_practicas_publicas.py`: sin sesión devuelve 200 solo con prácticas `activa = true` ordenadas por nombre y campos `id, nombre, duracion_min, sena_pct`; no expone `precio_base`, `clinic_id` ni inactivas; catálogo vacío devuelve lista vacía; confirmar que fallan.
- [x] 8b.2 Implementar `GET /api/public/practicas` en `backend/app/api/public/practicas.py` con schema público propio y `response_model`; verificar que 8b.1 pasa.
- [x] 8b.3 Agregar `codigo: solape` al 409 de solape de `POST /api/public/reservas`, con test que lo verifique (el frontend identifica el caso por `codigo`, no por el texto).
- [x] 8b.4 Agregar `PracticaPublica` a `frontend/src/features/booking/types.ts` y el query del catálogo en `frontend/src/features/booking/api.ts`; verificar typecheck.

## 9. Frontend: landing y reserva

- [x] 9.1 Escribir tests de la landing `/` con Testing Library: muestra prácticas y fechas, lista slots, muestra mensaje cuando no hay horarios y muestra error con reintento cuando la API falla; confirmar que fallan.
- [x] 9.2 Implementar la búsqueda de horarios en `features/booking/api.ts` y los componentes `SlotList` y el selector de práctica/fecha; reemplazar el stub de `HomePage` y verificar que los tests de 9.1 pasan en 390x844 sin scroll horizontal.
- [x] 9.3 Escribir tests del formulario de `/reservar`: teléfono inválido bloquea el envío con mensaje en el campo, teléfono válido envía normalizado, 201 muestra turno pendiente de seña con enlace de gestión y 409 por solape refresca slots conservando los datos; confirmar que fallan.
- [x] 9.4 Implementar `ReservaForm` y la pantalla de reserva reemplazando el stub de `BookingPage`; verificar que los tests de 9.3 pasan.
- [x] 9.5 Implementar la entrega al checkout: si la respuesta trae URL de pago redirige, y si no la trae muestra el turno como pendiente de seña sin simular pago aprobado; verificar con test ambos caminos.

## 10. Frontend: gestión por token

- [x] 10.1 Escribir tests de `/gestionar/:token`: muestra fecha, hora, práctica, estado de seña y reprogramaciones restantes; token inválido muestra enlace inválido y **no** navega a `/login`; turno `cancelado` oculta las acciones; confirmar que fallan.
- [x] 10.2 Implementar `GestionTurno` reemplazando el stub de `ManageAppointmentPage` usando `public-client`; verificar que los tests de 10.1 pasan y que un 403 del backend no dispara el interceptor de sesión.
- [x] 10.3 Escribir tests de las dos confirmaciones: cancelación tardía advierte la pérdida de seña y solo ejecuta al confirmar, la 2.ª reprogramación advierte que necesita seña nueva, y cerrar la advertencia no modifica el turno; confirmar que fallan.
- [x] 10.4 Implementar `ConfirmDialog` accesible (foco atrapado, `Escape`, retorno de foco) disparado por el `codigo` de la respuesta; verificar que los tests de 10.3 pasan.

## 11. Guard público y navegación

- [x] 11.1 Escribir un test de regresión del `PublicRoute`: un usuario autenticado que abre `/` termina en el panel de su rol y no en un ciclo de redirecciones; confirmar que falla con el router actual.
- [x] 11.2 Corregir el destino del guard en `frontend/src/router.tsx` y verificar que el test de 11.1 pasa y que el resto de las rutas conserva su comportamiento.
- [x] 11.3 Corregir el header público para que coincida con el mockup aprobado (solo "Inicio" y "Reservar turno", sin "Iniciar sesión") y subir el brand a 44 px de alto; cubierto por `frontend/src/layouts/PublicLayout.test.tsx` (RED verificado revirtiendo el menú).

## 12. Integración y documentación

- [x] 12.1 Correr la suite completa del backend (`pytest`) con cobertura y confirmar que no hay fallas nuevas respecto de la línea base de 1.2 y que la cobertura de los archivos nuevos supera el 80%.
- [x] 12.2 Correr `ruff check`, `ruff format --check` y `mypy` sobre el backend y confirmar que todo pasa en los archivos tocados.
- [x] 12.3 Correr `npm run test`, `npm run lint` y `npm run build` en `frontend/` y confirmar que pasan sin `any` ni errores de tipos.
- [x] 12.4 Actualizar `CHANGES.md`: marcar el estado de C-06, registrar la migración `006` y reemplazar las rutas públicas `{id}` por `{token}` con la nota del desvío de `design.md` D2; verificar leyendo el archivo.
- [x] 12.5 Verificar `openspec validate c-06-reserva-publica-cancel-reprog --strict` y confirmar que no reporta errores ni advertencias.
- [x] 12.6 Resolver la política visual del proyecto antes de la implementación de pantallas: correr `/active-orchestrator:design` y actualizar `## UI Mockups` de `design.md` con la decisión y, si corresponde, los mockups aprobados de `/`, `/reservar` y `/gestionar/:token`. Hecho: política `system-and-mockups`, sistema rev. 1 aprobado 2026-11-10 y los 3 mockups aprobados 2026-11-11.

## Workflow follow-up

- [x] Ejecutar la verificación visual contra los mockups aprobados si el modo del proyecto es `system-and-mockups`. Hecho 2026-11-11: `vite preview` + API mock, medición a 390×844 y 1440×900 en `/`, `/reservar` y `/gestionar/:token`; sin overflow, sin controles < 44 px, 0 errores de consola. Las capturas de `mockups/verify/` no se generaron porque este entorno no permite adjuntar imágenes al modelo: la comparación fue por métricas del DOM y revisión del HTML construido.
- Archivar el change con `/opsx:archive c-06-reserva-publica-cancel-reprog` una vez satisfechos los requisitos de revisión del proyecto.
- Al archivar, `gestion-turnos` y `booking-publico` pasan a `openspec/specs/`; a partir de ahí cualquier cambio del motor de turnos debe declarar `motor-turnos` como capacidad modificada.
