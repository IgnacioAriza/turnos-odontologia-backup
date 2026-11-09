# turnos-odontologia — Instrucciones para Agentes

> Este archivo (y su copia `CLAUDE.md`) es lo PRIMERO que todo agente lee al entrar al repo.
> Generado a partir de `knowledge-base/` y `CHANGES.md`. No editar a mano sin re-sincronizar ambos archivos.
>
> SaaS mobile-first para 1 clínica: reserva 24/7 sin login + agenda multi-sillón sin solapes + seña % MP real + recordatorio WA Twilio 24hs (un envío). Login paciente, odontograma y ABM aranceles van a v1.1 fast-follow (IN-01).

---

## Stack Tecnológico

| Capa | Tecnologías | Versión mínima |
|------|--------------|----------------|
| Backend | Python + FastAPI + SQLAlchemy ORM | Python 3.12, FastAPI 0.115+ |
| Auth | JWT (Bearer) | — |
| Base de datos | PostgreSQL | 16+ |
| Async / colas | Redis (cola + scheduler recordatorios) | 7+ |
| Infra local/dev | Docker + Docker Compose | Compose v2 |
| Frontend | React + TypeScript + Vite | React 18+, TS 5+ |
| UI | Mobile-first (mayoría reserva desde teléfono) | — |
| Pagos | Mercado Pago SDK + webhooks | API v1 vigente |
| Notificaciones | Twilio WhatsApp (Cloud API) | — |
| Respaldo | Google Calendar API + email (SMTP) | — |

Detalle completo: [knowledge-base/02_descripcion_general.md](knowledge-base/02_descripcion_general.md)

---

## Base de Conocimiento

La fuente de verdad del dominio vive en `knowledge-base/`. **Leé el archivo relevante ANTES de implementar.**

| Archivo | Cuándo leerlo |
|---------|---------------|
| [README.md](knowledge-base/README.md) | Índice + resumen ejecutivo del proyecto |
| [01_vision_y_objetivos.md](knowledge-base/01_vision_y_objetivos.md) | Entender propósito y alcance v1.0 + v1.1 |
| [02_descripcion_general.md](knowledge-base/02_descripcion_general.md) | Stack, arquitectura, integraciones, API REST |
| [03_actores_y_roles.md](knowledge-base/03_actores_y_roles.md) | Auth, RBAC, permisos |
| [04_modelo_de_datos.md](knowledge-base/04_modelo_de_datos.md) | Entidades, ERD, migraciones |
| [05_reglas_de_negocio.md](knowledge-base/05_reglas_de_negocio.md) | Reglas codificadas (RN-XX) |
| [06_funcionalidades.md](knowledge-base/06_funcionalidades.md) | Historias de usuario por épica (US-001..012) |
| [07_flujos_principales.md](knowledge-base/07_flujos_principales.md) | Flujos E2E |
| [08_arquitectura_propuesta.md](knowledge-base/08_arquitectura_propuesta.md) | Patrones, estructura, env vars |
| [09_decisiones_y_supuestos.md](knowledge-base/09_decisiones_y_supuestos.md) | Decisiones DD-01..07 + supuestos SU-01..04 |
| [10_preguntas_abiertas.md](knowledge-base/10_preguntas_abiertas.md) | ⚠️ Inconsistencias a resolver ANTES de codear |
| [11_pagos_mercadopago.md](knowledge-base/11_pagos_mercadopago.md) | Seña %, webhook idempotente, reembolsos |
| [12_whatsapp_twilio.md](knowledge-base/12_whatsapp_twilio.md) | Twilio, 1 envío 24hs, fallback |

> ⚠️ IN-01 (Alta): Discovery pedía login + odontograma + ABM en v1, ronda 1 3b lo partió a v1.1 fast-follow. Resolver las preguntas de prioridad **Alta** de `10_preguntas_abiertas.md` antes de codear C-11..C-13.

---

## Skills Disponibles

Fuente de verdad: `.atl/skill-registry.md` (6 user skills + 2 project skills + 6 workflow openspec). No re-escanear.

| Agente | Rol | Skills que carga |
|--------|-----|------------------|
| Backend Core | FastAPI / Postgres / TDD | `python-fastapi-development`, `supabase-postgres-best-practices`, `test-driven-development` |
| Backend Aux | Auth JWT / RBAC / seguridad | `auth-implementation-patterns` |
| Frontend | React 18+ / TS 5+ / Vite / mobile-first | `vercel-react-best-practices`, `frontend-design` |
| Revisión de dominio | Reglas de turnos / seguridad de pagos | `reglas-turnos-review`, `pagos-seguridad-review` |
| Orquestación | SDD / OPSX / docs | `openspec-propose`, `openspec-explore`, `openspec-apply-change`, `openspec-update-change`, `openspec-sync-specs`, `openspec-archive-change` |

Cargá la skill correspondiente al contexto ANTES de escribir código.

### Skills propias del proyecto

Viven en `skills/` (no en el catálogo global) y se disparan por dominio, no por rol:

| Skill | Ruta | Cuándo usarla |
|-------|------|---------------|
| `reglas-turnos-review` | `skills/reglas-turnos-review/SKILL.md` | Antes de preparar o revisar C-02, C-05, C-06 y C-07: detecta reglas ambiguas, casos de borde faltantes y genera escenarios verificables. |
| `pagos-seguridad-review` | `skills/pagos-seguridad-review/SKILL.md` | Antes de preparar o revisar C-08 y C-09: revisa montos de seña, idempotencia, firma de webhook y secretos MP. |

Cada skill produce un reporte markdown en `docs/skills-mcp/revision-*.md` listo para copiar a `proposal.md`, `design.md` y `tasks.md`.

> Los compact rules de cada skill los resuelve el orquestador desde `.atl/skill-registry.md` (generado por `skill-registry` y versionado en el repo). Esta tabla solo mapea skill→rol.

---

## Roadmap de Changes

El plan de implementación completo está en [CHANGES.md](CHANGES.md). Resumen:

- **Total**: 13 changes (C-01..C-13) en 6 fases (0 Cimientos, 1 Auth+Catálogo, 2 Motor+Reserva, 3 Operación diaria, 4 Dinero y mensajes, 5 v1.1 fast-follow).
- **v1.0 MVP lanzable (C-01..C-10, US-001..009)**: reserva 24/7 + agenda multi-sillón + cancel/reprog + panel día + seña % MP real + WA Twilio 24hs.
- **v1.1 fast-follow (C-11..C-13, US-010..012)**: login paciente + odontograma + ABM aranceles (requiere v1.0 completo).
- **Camino crítico (8)**: `C-01 → C-02 → C-03 → C-04 → C-05 → C-08 → C-09 → C-10`.
- **Primer change**: `C-01-foundation-setup` → arrancar con `/opsx:propose C-01-foundation-setup`.

**Antes de cualquier `/opsx:propose`**: leé [CHANGES.md](CHANGES.md), identificá las dependencias del change y los archivos de "Leer antes".

---

## Reglas Duras

Son contrato; romperlas es un defecto. Formato `NUNCA X → hacer Y`:

1. TDD ley de hierro — NUNCA código prod sin test fallando primero → RED por razón correcta, GREEN mínimo, suite pytest completa verde
2. Postgres — NUNCA tocar DB sin leer supabase-postgres-best-practices → RLS clinic_id, EXCLUDE anti-solape, EXPLAIN antes/después
3. Auth — NUNCA auth solo cliente → JWT 15-30min + refresh httpOnly+secure+sameSite, claims sub/clinic_id/rol/jti, RBAC server-side, rate-limit 5/60s Redis
4. FastAPI — NUNCA endpoint sin response_model → routers public/internal/webhooks, sesión por request, Alembic only, envelope consistente sin traces
5. Calidad Python — NUNCA merge sin ruff/black + mypy + pytest >80% + OpenAPI completa
6. Frontend — NUNCA any → PascalCase, tsconfig estricto, mobile-first, sin barrel files
7. Pagos/Notif — NUNCA confiar en callback front MP → webhook idempotente + conciliación; WA Twilio un envío 24hs con log/backoff
8. Negocio — NUNCA solape ni cancel <12hs ni 2da repro misma seña → bloqueo 30d, seña % por práctica, ABM NUNCA muta turnos
9. Secrets/Infra — NUNCA hardcodear → Pydantic settings, 12 env vars, compose api+postgres+redis+worker
10. Commits — conventional commits (feat:/fix:/docs:/chore: etc.)

---

## Flujo de Trabajo

```
1. Leer la KB relevante (knowledge-base/)        → entender el dominio
2. Identificar el change en CHANGES.md           → respetar dependencias
3. /opsx:propose C-NN-nombre                     → proposal + design + specs + tasks
4. /opsx:apply C-NN-nombre (cargando skills)     → implementar respetando las reglas duras
5. /opsx:archive C-NN-nombre + marcar [x]        → cerrar el change
```

Aplicar TODAS las reglas duras en cada paso. Ante conflicto entre la KB y este archivo, las reglas duras prevalecen.
