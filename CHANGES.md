# CHANGES — Secuencia de Implementación

> Índice canónico de todos los changes del proyecto **SaaS Odontología (turnos 24/7 + seña MP + WA Twilio)**.
> Cada change es atómico: un agente puede implementarlo en una sesión (~4-6 horas).
> **Leer este archivo antes de ejecutar cualquier `/opsx:propose`.**

> Oleadas: **v1.0 MVP lanzable (US-001–009)** = reserva 24/7 + agenda multi-sillón + cancel/reprog + panel día + seña % MP real + WA Twilio 24hs. **v1.1 fast-follow (US-010–012)** = login paciente + odontograma + ABM aranceles. Respeta **IN-01** (`knowledge-base/10_preguntas_abiertas.md`): Discovery pedía todo en v1, ronda 1 3b lo partió en dos oleadas.

---

## Cómo usar este documento

1. Identificar el change a implementar (verificar que sus dependencias están en `openspec/changes/archive/`).
2. Leer los docs de la knowledge-base indicados en "Leer antes".
3. Ejecutar `/opsx:propose <nombre-del-change>`.
4. Al terminar el change, archivarlo con `/opsx:archive <nombre-del-change>`.
5. Marcar el checkbox `[x]` en este archivo.

---

## Árbol de dependencias

```
C-01 foundation-setup
  └── C-02 core-models-clinica-personas
        └── C-03 auth-interno-rbac                ← desbloquea TODO lo interno
              └── C-04 catalogo-sillones-practicas
                    └── C-05 motor-reservas-slots-turnos     ← corazón del dominio
                          │
                          ├── C-06 reserva-publica-cancel-reprog
                          │     │
                          │     └── (junto con C-09) → C-10 notificaciones-whatsapp
                          │
                          ├── C-07 agenda-panel-dia              ← paralelo con C-06
                          │     │
                          │     └── (v1.1) → C-12 odontograma-historia
                          │
                          └── C-08 checkout-sena-mercadopago     ← paralelo con C-06/C-07
                                └── C-09 webhook-conciliacion
                                      └── C-10 notificaciones-whatsapp-twilio *

C-10 + C-07 ✓ = v1.0 lanzable *
  ├── C-11 login-paciente-historial      (v1.1)
  ├── C-12 odontograma-historia-clinica  (v1.1, + C-07)
  └── C-13 abm-aranceles-admin           (v1.1, + C-04)
```

> `*` — C-10 es el último del camino crítico; C-07 es el otro extremo indispensable del MVP (agenda). Ambos deben estar ✓ para el go-live v1.0.

### Paralelismo por fase

> Cada "gate" es un punto de sincronización. Los changes dentro de un grupo pueden ejecutarse en paralelo.

```
GATE 0: ninguna
  → C-01 foundation-setup (solo)

GATE 1: C-01 ✓
  → C-02 core-models-clinica-personas (solo)

GATE 2: C-02 ✓
  → C-03 auth-interno-rbac (solo)

GATE 3: C-03 ✓
  → C-04 catalogo-sillones-practicas (solo)

GATE 4: C-04 ✓
  → C-05 motor-reservas-slots-turnos (solo — cuello de botella del dominio)

GATE 5: C-05 ✓                     ← PRIMER FORK (3 paralelos)
  → C-06 reserva-publica-cancel-reprog   [Agente C — Frontend + pública]
  → C-07 agenda-panel-dia                [Agente A — Backend Core]
  → C-08 checkout-sena-mercadopago       [Agente B — Backend Aux / integraciones]

GATE 6: C-08 ✓
  → C-09 webhook-conciliacion            [Agente B]

GATE 7: C-06 + C-09 ✓               ← converge reserva + pagos
  → C-10 notificaciones-whatsapp-twilio  [Agente B — si C-07 ✓ para cancelar job]

GATE 8: v1.0 completo (C-06 + C-07 + C-10 ✓)    ← FORK v1.1 (3 paralelos)
  → C-11 login-paciente-historial        [Agente A]
  → C-12 odontograma-historia-clinica    [Agente C — si C-07 ✓]
  → C-13 abm-aranceles-admin             [Agente B — si C-04 ✓]
```

### Camino crítico (8 changes — mínimo irreducible)

```
C-01 → C-02 → C-03 → C-04 → C-05 → C-08 → C-09 → C-10
```

> No incluye C-06/C-07 (ramas paralelas indispensables pero no lineales) ni nada de v1.1. Para el go-live real se exige además C-06 ✓ y C-07 ✓ (ver asteriscos del árbol).

### Plan óptimo con 3 agentes

```
Paso │ Agente A (Backend Core)              │ Agente B (Backend Aux)               │ Agente C (Frontend)
─────┼──────────────────────────────────────┼──────────────────────────────────────┼────────────────────────────────────
  1  │ C-01 foundation-setup                │         —                            │         —
  2  │ C-02 core-models-clinica-personas    │         —                            │         —
  3  │ C-03 auth-interno-rbac               │         —                            │         —
  4  │ C-04 catalogo-sillones-practicas     │         —                            │         —
  5  │ C-05 motor-reservas-slots-turnos     │         —                            │         —
  6  │ C-07 agenda-panel-dia                │ C-08 checkout-sena-mercadopago       │ C-06 reserva-publica-cancel-reprog
  7  │ — (apoya review C-09)                │ C-09 webhook-conciliacion            │ — (apoya review C-09)
  8  │ —                                    │ C-10 notificaciones-whatsapp-twilio  │ — (estabiliza booking/agenda)
  9  │ C-11 login-paciente-historial        │ C-13 abm-aranceles-admin             │ C-12 odontograma-historia-clinica
```

---

## FASE 0 — Cimientos

### [C-01] `foundation-setup`
- **Estado**: `[x]` implementado y archivado
- **Scope**: Scaffolding completo del monolito modular + infra base (DD-01, DD-02 escalabilidad)
  - Estructura `backend/app/{main.py, core/, domain/{turnos,pagos,notificaciones,clinica,personas}, infrastructure/{db,queue,integrations}, api/{public,internal,webhooks}}` + `frontend/src/{features/{booking,agenda,panel-dia,admin}, shared/, pages/}` según `08`
  - `backend`: FastAPI app mínima + `GET /api/health`, Alembic inicializado, `core/` con settings (Pydantic), logger, `TZ_CLINICA=America/Argentina/Buenos_Aires`, exceptions RFC (409 solape)
  - `frontend`: Vite + React 18 + TS 5 scaffolding, router (públicas vs protegidas), api-client, UI mobile-first base
  - `docker-compose.yml`: `api + postgres:16 + redis:7 (+ worker)`; `.env.example` en cada sub-proyecto con las 12 vars de `08` (`DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `MP_*`, `TWILIO_*`, `GCAL_*`, `SMTP_URL`, `FRONTEND_URL`); secrets solo `${VAR}`, nunca hardcodeados
  - GitHub Actions CI: jobs paralelos backend (ruff + pytest) y frontend (tsc + build)
  - Tests: health check, import de routers, compose up smoke
- **Dependencias**: ninguna
- **Governance**: BAJO
- **Leer antes**:
  - `knowledge-base/01_vision_y_objetivos.md` §Alcance v1.0
  - `knowledge-base/02_descripcion_general.md` §Stack tecnológico
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-01, §DD-02

---

### [C-02] `core-models-clinica-personas`
- **Estado**: `[x]` implementado y archivado 2026-11-10 (SDD: proposal, design, tasks; código real en backend/app/domain/{clinica,personas}, backend/app/core/{mixins,repository,security}, backend/scripts/seed.py, backend/tests/test_*, backend/app/infrastructure/db/migrations/versions/002_clinica_personas.py)
- **Scope**: Modelos base + migraciones iniciales + seed mínimo (DD-06 `clinic_id` día 1)
  - Modelos: `Clinic`, `User` (rol recepcion|odonto|admin), `Paciente`, `Sillon`, `Bloqueo` (estructura; lógica en C-07)
  - `AuditMixin` (`is_active`, `created_at`, `updated_at`); `BaseRepository[T]` + `UnitOfWork`; `clinic_id` FK obligatorio en todas las tablas de negocio
  - Migración 002: tablas `clinic`, `users` (email UNIQUE por clínica), `pacientes` (índices `(clinic_id,telefono)`, `(clinic_id,dni)`), `sillones`, `bloqueos`
  - Seed mínimo: 1 `Clinic` (timezone AR, `wa_sender` Twilio, cuenta MP), 1 admin + 1 recepción + 1 odontólogo, 2-3 sillones activos
  - Tests: constraints UNIQUE, filtros `clinic_id` omnipresentes, seed idempotente
- **Dependencias**: C-01
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §Clinic, §User, §Paciente, §Sillon, §Bloqueo
  - `knowledge-base/08_arquitectura_propuesta.md` §Patrones aplicados
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-02, §DD-06
  - `knowledge-base/03_actores_y_roles.md` §Actores del sistema

---

## FASE 1 — Auth interno + Catálogo clínico

> C-03 desbloquea todo lo interno. C-04 deja aranceles en lectura + seed (RN-ADMIN-02, IN-01).

### [C-03] `auth-interno-rbac`
- **Estado**: `[x]` implementado y archivado 2026-11-10 (SDD: proposal, design, tasks; código real en backend/app/domain/auth, backend/app/api/auth, backend/app/core/rate_limit.py, backend/app/main.py, backend/app/infrastructure/db/migrations/versions/003_auth.py, backend/tests/test_auth_*, frontend/src/pages/Login.tsx, frontend/src/components/RouteGuard.tsx, frontend/src/pages/role/*.tsx)
- **Scope**: Autenticación JWT + RBAC para roles internos (recepción/odontólogo/admin). Login paciente NO entra (v1.1 C-11)
  - `POST /api/auth/login` — JWT access + refresh, rate limiting 5/60s por IP+email; `POST /api/auth/refresh` (rotación + blacklist anterior); `POST /api/auth/logout` (blacklist); `GET /api/auth/me`
  - Claims JWT: `sub`, `clinic_id`, `rol`, `email`, `jti`, `type`, `iat`, `exp`; refresh en cookie HttpOnly (secure, samesite=lax); `JWT_SECRET`, `JWT_EXPIRES_MIN=480` via env
  - Guards por router: `require_role("recepcion"|"odonto"|"admin")`; odontólogo confinado a su `odontologo_id`; `admin` con permisos explícitos totales (sin herencia)
  - Migración 002: `password_hash`, `activo`, blacklist de refresh (Redis o tabla)
  - Frontend: `/login` + guardia de rutas protegidas + páginas base por rol (solo shell, sin features)
  - Tests: login correcto, token expirado, refresh rotation, rate limit, acceso cruzado odonto→otro odonto 403
- **Dependencias**: C-02
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md` §RBAC — Matriz de permisos, §Rutas públicas
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Excepciones globales
  - `knowledge-base/08_arquitectura_propuesta.md` §Seguridad
  - `knowledge-base/07_flujos_principales.md` §Flujo 3

---

### [C-04] `catalogo-sillones-practicas`
- **Estado**: `[x]` completado (archivado 2026-11-09; tarea 6.5 diferida a C-05)
- **Scope**: Catálogo clínico + aranceles en LECTURA (v1.0) con seed de `% seña` por práctica (DD-05, RN-ADMIN-02)
  - Modelos: `TipoPractica` (`nombre`, `duracion_min > 0`, `precio_base`, `sena_pct 0-100`), `Arancel` (`tipo_practica_id UNIQUE`, `precio`, `sena_pct`, `vigente_desde`)
  - Endpoints internos (JWT): `GET /api/internal/tipos-practica`, `GET /api/internal/sillones`, `GET /api/admin/aranceles` (lectura v1.0); CRUD admin de `% seña` global por práctica (RN-ADMIN-01 con auditoría quien/cuando/antes/después); ABM completo queda para C-13
  - Migración 004: tablas `tipos_practica`, `aranceles` y `auditorias_sena`; seed: limpieza/arreglo/endodoncia/extracción/ortodoncia-control con `duracion_min`, `precio_base`, `sena_pct` inicial (pregunta Alta P-Alta pendiente de Admin — seed con valores provisorios documentados)
  - Frontend: pantalla admin lectura de aranceles/precios + selector de práctica (reusado por booking C-06)
  - Tests: CHECK `sena_pct`, foto de precio no muta (prepara RN-PAGO-02), RBAC lectura vs escritura
- **Dependencias**: C-03
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §TipoPractica, §Arancel, §Seed data inicial
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Pagos, §Dominio: Administración
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-05
  - `knowledge-base/10_preguntas_abiertas.md` §Preguntas abiertas (seed % seña)

---

## FASE 2 — Motor de turnos + Reserva pública

> C-05 es el cuello de botella del dominio (anti-solape + estados + TTL). C-06 consume su API.

### [C-05] `motor-reservas-slots-turnos`
- **Estado**: `[x]` implementado 2026-11-10 y archivado 2026-11-11 en `openspec/changes/archive/2026-11-11-c-05-motor-reservas-slots-turnos/` (SDD: proposal, design, tasks; código real en backend/app/domain/turnos/{models,slots,repository,service,schemas}.py, backend/app/api/public/, backend/app/api/internal/turnos.py, backend/app/infrastructure/queue/worker.py, backend/app/infrastructure/db/migrations/versions/005_motor_turnos.py, backend/scripts/seed.py, backend/tests/test_{turnos_models,slots,turnos_service,reservas_publicas,turnos_api,worker,seed,personas_schemas}.py)
  - Verificación: `pytest` 145 passed / 30 skipped, cobertura 81.8%; `ruff check` + `ruff format --check` + `mypy app` (56 archivos) limpios; `openspec validate --strict` OK; OpenAPI lista `/api/public/slots`, `/api/public/reservas` y `/api/internal/turnos`
  - Migración 005 (`005 (head)`): tablas `turnos` + `horarios_atencion`, `btree_gist`, `EXCLUDE USING gist` por sillón y odontólogo sobre estados vigentes, CHECKs, UNIQUE `manage_token` y `(clinic_id, telefono)` de pacientes, `pacientes.dni` nullable + `faltas_count` + `bloqueado_hasta`
  - Pendiente de verificación real en Postgres: tarea 1.5 (upgrade/downgrade 004→005→004→005). Bloqueada en este entorno por falta de Docker y credenciales del PostgreSQL local; los tests de migración usan `skipif` y quedan listos para CI con Postgres
  - Desvío documentado: el escenario de `specs/motor-turnos/spec.md` listaba 3 slots para una práctica de 30 min en 08:00–10:00; la implementación devuelve 4 (08:00, 08:30, 09:00 y 09:30) porque el fin del turno puede coincidir con `hora_hasta` (design D4). Escenario corregido en el spec del change antes de archivar
- **Scope**: Núcleo de turnos: slots + creación `pendiente_sena` + anti-solape + expiración (US-001, US-002 parcial; RN-RES-01–05)
  - Modelo `Turno`: `clinic_id`, `paciente_id`, `sillon_id`, `odontologo_id`, `tipo_practica_id`, `inicio/fin timestamptz`, `estado: pendiente_sena|confirmado|cancelado|reprogramado|completado|ausente`, `manage_token UNIQUE`, `reprogramaciones_count=0`, `monto_sena` (foto `round(precio_base*sena_pct/100)`), índices `(clinic_id,inicio)`, `(sillon_id,inicio)`, `(odontologo_id,inicio)`, `(paciente_id,inicio)`, `(estado)`
  - Anti-solape: `EXCLUDE USING gist (tstzrange)` o UNIQUE + validación transaccional en `TurnoService`; `CHECK (fin > inicio)`; todo en `America/Argentina/Buenos_Aires`; concurrente → 409 + alternativos
  - `GET /api/public/slots?fecha=&practica=` — huecos por `duracion_min`, respeta horarios de atención, sin datos de otros pacientes, carga < 2s (cache Redis TTL corto)
  - `POST /api/public/reservas` (sin JWT): valida bloqueo 30d (403 con `bloqueado_hasta`), crea `Turno(pendiente_sena)` + `manage_token` + `monto_sena` + job Redis expiración `MP_TTL_MIN=30` (RN-RES-04; libera slot si no hay pago)
  - `POST /api/internal/turnos` — creación interna (mostrador/teléfono, mismo motor, sin `manage_token` público)
  - Migración 005: tabla `turnos` + constraints; worker expiración `pendiente_sena`
  - Tests: solape sillón 409, solape odontólogo 409, TTL libera slot, bloqueo rechaza, `manage_token` unguessable; verificar que cambiar el `% seña` de una práctica no muta el `monto_sena` de turnos existentes (tarea 6.5 diferida de C-04)
- **Dependencias**: C-04
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §Turno, §Paciente
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Reservas, §Dominio: Ausentismo
  - `knowledge-base/07_flujos_principales.md` §Flujo 1
  - `knowledge-base/06_funcionalidades.md` §US-001, §US-002

---

### [C-06] `reserva-publica-cancel-reprog`
- **Estado**: `[x]` implementado 2026-11-11 y archivado 2026-11-11 en `openspec/changes/archive/2026-11-11-c-06-reserva-publica-cancel-reprog/`. Suite backend 242 passed / 33 skipped, cobertura 83.94%; `ruff check`, `ruff format --check` y `mypy` limpios; frontend 68 tests, `npm run build` y `npm run lint` sin errores. Specs sincronizados a `openspec/specs/booking-publico/` y `openspec/specs/gestion-turnos/`. Pendiente: verificación real de upgrade/downgrade de la migración 006 en Postgres (sin Docker ni credenciales en este entorno).
- **Migración**: `006` (`006_gestion_turnos`) — agrega `turnos.sena_perdida BOOLEAN NOT NULL DEFAULT false` y `turnos.reprogramado_de_id UUID NULL` con FK a `turnos.id`. `alembic heads` reporta `006` como única cabeza.
- **Desvíos respecto del plan original**:
  - Las rutas públicas de gestión son **token-addressed**: `GET /api/public/gestion/{token}`, `POST /api/public/gestion/{token}/cancelar` y `/reprogramar`, con `manage_token` también en el body. Reemplazan a `POST /api/public/reservas/{id}/cancelar|reprogramar`: el paciente nunca conoce el `turno_id`, y un `{id}` en la URL filtraría la existencia del turno. Token inválido → 403 `token_invalido`; turno inexistente o inactivo → 404 `turno_no_encontrado`.
  - Se agregó `GET /api/public/practicas` (solo `id`, `nombre`, `duracion_min`, `sena_pct`, sin `precio_base` ni `clinic_id`) porque el selector de la landing no podía construir UUIDs. El resumen de `/reservar` no puede mostrar el monto absoluto de la seña antes del 201: `monto_sena` se conoce recién en la respuesta de la reserva.
  - `codigo` estable en los problem+json: `solape` en el 409 de `POST /api/public/reservas`, además de los códigos de gestión (`requiere_confirmacion`, `requiere_nueva_sena`, `estado_no_gestionable`, `slot_invalido`, `token_invalido`, `turno_no_encontrado`).
- **Scope**: Reserva pública E2E + gestión con token + cancelar/reprogramar (US-001, US-002 parcial, US-003; RN-CANCEL-01–04)
  - Gestión pública con `manage_token` + ventana ≥ 12hs (`inicio - now() >= 12h`); 1.ª repro migra seña (`reprogramaciones_count=1`, reprograma job WA); 2.ª/tardía exige nueva seña y libera slot; tardía = seña no reembolsable (política visible)
  - Misma reglas para recepción vía API interna (JWT `recepcion|admin`, `motivo` obligatorio); cancelar libera horario inmediatamente para re-reserva
  - Frontend `features/booking/`: `/` landing con catálogo + buscador de slots, `/reservar` (nombre + teléfono E.164 AR + entrega al checkout), `/gestionar/:token` (ver/cancelar/reprogramar con confirmación explícita de pérdida de seña), mobile-first
  - Tests: ventana 12hs, 1.ª repro migra seña, 2.ª pierde seña, token inválido 403, slot liberado re-reservable, catálogo público sin datos internos, 409 por `codigo` en el frontend
- **Dependencias**: C-05
- **Governance**: MEDIO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §US-002, §US-003
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Cancelación
  - `knowledge-base/07_flujos_principales.md` §Flujo 2
  - `knowledge-base/08_arquitectura_propuesta.md` §Seguridad (`manage_token`)

---

## FASE 3 — Operación diaria

### [C-07] `agenda-panel-dia`
- **Estado**: `[ ]` pendiente
- **Scope**: Agenda multi-sillón + panel del día + vista odontólogo + bloqueos 30d (US-004, US-005, US-006; RN-AUS-01–03)
  - `GET /api/agenda?vista=dia|semana&sillon=&odontologo=&estado=` — multi-sillón día/semana, filtros por sillón/odontólogo/estado; crear turno interno usa motor C-05 (solape → 409 claro)
  - `GET /api/panel/dia?fecha=` — lista por hora con estado de seña + contacto WA; `PATCH /api/panel/turnos/{id}` marcar `completado`/`ausente`; 2.ª falta → `Bloqueo(desde, hasta=now()+30d, motivo="2_faltas", created_by)` automático (DD-04)
  - Excepción a bloqueo por recepción con motivo obligatorio auditado (RN-AUS-02); falta la marca recepción/odontólogo, nunca automática
  - Frontend `features/agenda/` (día/semana multi-sillón) + `features/panel-dia/` (llegadas, señas, faltas) + vista `odonto` filtrada por `odontologo_id = yo` sin ABM
  - Tests: agenda sin solape, `ausente` x2 dispara bloqueo 30d, bloqueado → 403 con `bloqueado_hasta`, excepción auditada
- **Dependencias**: C-05, C-03
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §US-004, §US-005, §US-006
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Ausentismo
  - `knowledge-base/07_flujos_principales.md` §Flujo 3
  - `knowledge-base/04_modelo_de_datos.md` §Bloqueo, §Turno
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-04

---

## FASE 4 — Dinero y mensajes (MP real + WA real)

> Integraciones externas al final (regla 6): dependen del dominio ya creado. Sin simulados: MP y Twilio REALES en v1.0.

### [C-08] `checkout-sena-mercadopago`
- **Estado**: `[ ]` pendiente
- **Scope**: Checkout de seña % con Mercado Pago REAL (US-007; RN-PAGO-01/02/04)
  - `mp_client` en `infrastructure/integrations/`; `POST /api/public/reservas/{id}/pagar` crea preference: `external_reference=turno_id`, `metadata={clinic_id, turno_id, idempotency_key}`, `monto_sena` exacto fotografiado, moneda ARS
  - Estados `pendiente/aprobado/rechazado` visibles + reintento de pago (link reenviable por recepción); un solo `aprobado` vigente por turno (índice parcial)
  - Env `MP_ACCESS_TOKEN`, `MP_WEBHOOK_SECRET`, `MP_TTL_MIN`; credenciales rotables, nunca en repo
  - Frontend: pantalla checkout (redirección MP + estado + reintento)
  - Tests: monto exacto RN-PAGO-02, cambios de arancel no alteran turnos existentes, reintento genera preference nueva sin duplicar turno
- **Dependencias**: C-05
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/11_pagos_mercadopago.md` §Configuración
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Pagos
  - `knowledge-base/06_funcionalidades.md` §US-007
  - `knowledge-base/08_arquitectura_propuesta.md` §Variables de entorno

---

### [C-09] `webhook-conciliacion`
- **Estado**: `[ ]` pendiente
- **Scope**: Webhook MP idempotente + conciliación diaria (US-008; RN-PAGO-03)
  - `POST /api/webhooks/mercadopago`: valida firma (`MP_WEBHOOK_SECRET`), busca `mp_payment_id` → si existe 200 sin efectos; solo `aprobado` mueve `pendiente_sena → confirmado` y dispara WA + job T-24hs (llama a C-10); guarda `raw_webhook jsonb`
  - Modelo `Pago`: `turno_id`, `mp_payment_id UNIQUE`, `mp_preference_id`, `monto`, `moneda="ARS"`, `estado`, `idempotency_key UNIQUE`
  - Migración 007: tabla `pagos` (006 ya la usa C-06 para `sena_perdida` y `reprogramado_de_id`); worker de reproceso de webhooks pendientes (idempotente)
  - `GET /api/admin/conciliacion?fecha=` — reporte turnos confirmados vs señas aprobadas; reembolsos solo según RN-CANCEL-02/03 (1.ª repro migra; tardía no reembolsa; manual solo Admin auditado)
  - Tests: webhook duplicado 200 sin doble confirmación, firma inválida 401, reproceso seguro, reporte cuadra
- **Dependencias**: C-08
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/11_pagos_mercadopago.md` §Webhook, §Reembolsos
  - `knowledge-base/07_flujos_principales.md` §Flujo 4, §Flujo 1
  - `knowledge-base/06_funcionalidades.md` §US-008
  - `knowledge-base/04_modelo_de_datos.md` §Pago

---

### [C-10] `notificaciones-whatsapp-twilio`
- **Estado**: `[ ]` pendiente
- **Scope**: WhatsApp REAL vía Twilio + respaldo email/Calendar (US-009; RN-NOTIF-01–04, DD-07)
  - `twilio_client` + `gcal_client` + SMTP en `infrastructure/integrations/`; plantillas `confirmacion_reserva` (inmediata) y `recordatorio_24h` (1 envío); `TWILIO_WA_FROM=whatsapp:+54911...`, links `FRONTEND_URL/gestionar/:token`
  - Al confirmar (C-09): envío WA inmediato + job Redis `scheduled_for = inicio - 24h`; al cancelar/reprogramar (C-06) antes de T-24hs: cancela job (RN-NOTIF-03), repro reprograma job nuevo
  - Modelo `Notificacion`: `turno_id`, `canal`, `tipo`, `proveedor="twilio"`, `provider_sid`, `estado: encolado|enviado|entregado|fallido`, `scheduled_for`, `sent_at`; índice parcial UNIQUE un `recordatorio_24h` whatsapp por turno; fallo → backoff + email, turno no cambia de estado
  - `POST /api/webhooks/twilio` (opcional v1.0): estados de entrega; respaldo evento Google Calendar + email (US-009)
  - Migración 008: tabla `notificaciones` + scheduler Redis (006 = C-06, 007 = C-09)
  - Tests: exactamente 1 recordatorio por turno, cancelación cancela job, fallo Twilio → `fallido` + reintento sin mutar turno
- **Dependencias**: C-06, C-09
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/12_whatsapp_twilio.md` (completo)
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Notificaciones
  - `knowledge-base/06_funcionalidades.md` §US-009
  - `knowledge-base/04_modelo_de_datos.md` §Notificacion
  - `knowledge-base/09_decisiones_y_supuestos.md` §DD-07, §SU-04

---

## FASE 5 — v1.1 fast-follow (NO MVP)

> Fuera del corte lanzable por 3b/IN-01. Requiere v1.0 completo (C-06 + C-07 + C-10 ✓). Los tres changes son paralelizables entre sí.

### [C-11] `login-paciente-historial`
- **Estado**: `[ ]` pendiente
- **Scope**: Login paciente OPCIONAL + historial (US-010; reserva sigue sin login)
  - Extiende `User` rol `paciente` + link `Paciente.user_id nullable`; `POST /api/auth/paciente/registro|login`; JWT rol `paciente` con RBAC (solo su historial)
  - `GET /api/paciente/mis-turnos` — historial + próximos + links gestionar con token; reserva pública intacta (login solo añade historial)
  - Migración 008: `pacientes.user_id`, rol `paciente`; vinculación por teléfono+DNI al registrarse
  - Frontend: `/login-paciente` + `/mis-turnos` (mobile-first)
  - Tests: reserva sin login sigue funcionando, paciente A no ve turnos de B, vinculación por teléfono
- **Dependencias**: C-03, C-05
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §US-010
  - `knowledge-base/03_actores_y_roles.md` §RBAC — Matriz de permisos
  - `knowledge-base/04_modelo_de_datos.md` §User, §Paciente
  - `knowledge-base/01_vision_y_objetivos.md` §v1.1 fast-follow

---

### [C-12] `odontograma-historia-clinica`
- **Estado**: `[ ]` pendiente
- **Scope**: Odontograma + historia clínica básica con auditoría (US-011)
  - Modelos: `OdontogramaPieza` (paciente, pieza FDI, estado, notas) + `HistoriaEvento` (turno/paciente, tipo, detalle, `created_by`, `created_at` inmutable); lectura + carga básica por turno/paciente desde panel odontólogo
  - Endpoints (JWT `odonto|admin`): `GET /api/pacientes/{id}/odontograma`, `PUT /api/pacientes/{id}/odontograma`, `GET/POST /api/pacientes/{id}/historia`; auditoría de cambios (quien/cuando/antes/después)
  - Migración 009: tablas odontograma + historia
  - Frontend: visor/editor odontograma en ficha paciente (dentro de agenda/panel C-07)
  - Tests: odonto solo edita sus pacientes, auditoría registra cambios, lectura no filtra datos sensibles cruzados
- **Dependencias**: C-07
- **Governance**: CRITICO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §US-011
  - `knowledge-base/04_modelo_de_datos.md` §Entidades
  - `knowledge-base/03_actores_y_roles.md` §RBAC — Matriz de permisos
  - `knowledge-base/01_vision_y_objetivos.md` §v1.1 fast-follow

---

### [C-13] `abm-aranceles-admin`
- **Estado**: `[ ]` pendiente
- **Scope**: ABM de aranceles/nomenclador por Admin con vigencia y auditoría (US-012; RN-ADMIN-01/02)
  - CRUD `POST/PATCH/DELETE /api/admin/aranceles` + `POST /api/admin/tipos-practica` (solo `admin`); `vigente_desde`, auditoría completa; **no altera turnos existentes** (foto `monto_sena` intacta, RN-PAGO-02)
  - Frontend `features/admin/`: tabla aranceles + editor `% seña` por práctica + historial de vigencia
  - Migración 010: auditoría aranceles (`arancel_historial`)
  - Tests: cambio de precio no muta turnos pasados, no-admin 403, vigencia futura no afecta reservas actuales
- **Dependencias**: C-04
- **Governance**: ALTO
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` §US-012
  - `knowledge-base/05_reglas_de_negocio.md` §Dominio: Administración, §Dominio: Pagos
  - `knowledge-base/04_modelo_de_datos.md` §Arancel, §TipoPractica
  - `knowledge-base/10_preguntas_abiertas.md` §IN-01

---
