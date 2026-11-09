# Skill Registry

**Delegator use only.** Any agent that launches sub-agents reads this registry to resolve compact rules, then injects them directly into sub-agent prompts. Sub-agents do NOT read this registry or individual SKILL.md files.

Project: turnos-odontologia (SaaS odontologia: FastAPI + PostgreSQL/Redis + React/Vite). Stack pin: Backend Python/FastAPI/JWT/SQLAlchemy/PostgreSQL/Redis/Docker-Compose, Frontend React/TypeScript/Vite, mobile-first, 1 clinica en v1.

## User Skills (installed)

| Trigger | Skill | Path |
|---------|-------|------|
| Writing, reviewing, or refactoring React/Next.js code; React components, Next.js pages, data fetching, bundle optimization, performance | vercel-react-best-practices | C:\Users\USUARIO\.agents\skills\vercel-react-best-practices\SKILL.md |
| Building new UI or reshaping existing one; aesthetic direction, typography, non-templated visual design | frontend-design | C:\Users\USUARIO\.agents\skills\frontend-design\SKILL.md |
| BEFORE writing/changing anything in Postgres: tables, columns, schema, migrations, RLS, indexes, triggers, functions, pg_cron/pgmq, pgvector, dumps; or diagnosing slow queries, EXPLAIN, connections, locking, bloat, wrong-tenant rows | supabase-postgres-best-practices | C:\Users\USUARIO\.agents\skills\supabase-postgres-best-practices\SKILL.md |
| Implementing any feature or bugfix, before writing implementation code | test-driven-development | C:\Users\USUARIO\.agents\skills\test-driven-development\SKILL.md |
| Implementing auth systems, securing APIs, OAuth2/social login, RBAC, session management, auth migration, auth debugging, SSO/multi-tenancy | auth-implementation-patterns | C:\Users\USUARIO\.agents\skills\auth-implementation-patterns\SKILL.md |
| Building FastAPI REST APIs, async Python backends, SQLAlchemy integration, API auth, microservices | python-fastapi-development | C:\Users\USUARIO\.agents\skills\python-fastapi-development\SKILL.md |

## Project Skills (own, repo-local)

| Trigger | Skill | Path |
|---------|-------|------|
| Preparing/reviewing turnos changes (C-02, C-05, C-06, C-07); ambiguous business rules, missing edge cases, verifiable scenarios | reglas-turnos-review | skills/reglas-turnos-review/SKILL.md |
| Preparing/reviewing payments changes (C-08, C-09); sena monto, MP webhook idempotency, signature, MP_* secrets, payment edge cases | pagos-seguridad-review | skills/pagos-seguridad-review/SKILL.md |

## Project Workflow Skills (openspec, read on demand)

| Trigger | Skill | Path |
|---------|-------|------|
| "openspec propose" / "opsx propose" — new change with design+specs+tasks | openspec-propose | .opencode/skills/openspec-propose/SKILL.md |
| "openspec explore" / "opsx explore" — think through idea before/during a change | openspec-explore | .opencode/skills/openspec-explore/SKILL.md |
| "openspec apply" / "opsx apply" — implement tasks from a change | openspec-apply-change | .opencode/skills/openspec-apply-change/SKILL.md |
| "openspec update" / "opsx update" — revise a change's plan (never edits code) | openspec-update-change | .opencode/skills/openspec-update-change/SKILL.md |
| "openspec sync" / "opsx sync" — sync delta specs to main specs | openspec-sync-specs | .opencode/skills/openspec-sync-specs/SKILL.md |
| "openspec archive" / "opsx archive" — finalize and archive a completed change | openspec-archive-change | .opencode/skills/openspec-archive-change/SKILL.md |

## Skill → Change Mapping (CHANGES.md, 13 changes)

| Skill | Changes |
|-------|---------|
| vercel-react-best-practices | C-06, C-07, C-12 (booking/agenda/panel-dia) |
| frontend-design | C-06, C-07 (landing/reserva, panel dia distintivo) |
| supabase-postgres-best-practices | C-02, C-05 (EXCLUDE gist anti-solape, indices turnos, RLS clinic_id) |
| test-driven-development | C-05, C-06, C-09 (solape 409, TTL 30min, ventana 12hs, webhook idempotente) |
| auth-implementation-patterns | C-03, C-11 (login JWT + RBAC recepcion/odonto/admin) |
| python-fastapi-development | C-01, C-02, C-05 (routers public/internal/webhooks, Pydantic settings) |
| reglas-turnos-review | C-02, C-05, C-06, C-07 (ambiguedades de reglas, casos de borde, escenarios verificables) |
| pagos-seguridad-review | C-08, C-09 (monto de sena, idempotencia de webhook, firma, secretos MP) |

## Compact Rules

Pre-digested rules per skill. Delegators copy matching blocks into sub-agent prompts as `## Project Standards (auto-resolved)`.

### vercel-react-best-practices
- Eliminate waterfalls: parallelize independent ops with Promise.all, defer await into branches, check cheap sync conditions before awaiting
- Stream with Suspense boundaries; start promises early, await late in API routes
- Import directly (no barrel files); next/dynamic for heavy components; load analytics/logging after hydration; preload on hover/focus
- Server: React.cache() per-request dedup, LRU cross-request, hoist static I/O to module level, minimize RSC→client serialization, never module-level mutable request state
- Re-renders: derive state during render (not effects), primitive effect deps, functional setState, startTransition/useDeferredValue for non-urgent work, never define components inside components
- Full rule detail lives in per-rule files (`rules/<rule>.md`); compiled guide in skill AGENTS.md

### frontend-design
- Ground every design in the brief's subject (odontologia: clinica/paciente/recepcion) — never generic SaaS-card kit, cream+terracotta default, or acid-on-black default
- One display family max + one body family, clearly distinct; line length <80 chars; no single-accent-word headlines, no ALL-CAPS labels, no meta "A · B · C" strings
- Structural devices (borders, numbering 01/02/03, eyebrows, dividers) only when they encode real info — numbers only for true sequences
- One orchestrated motion moment max; motion answers user action (open/expand/confirm), never scattered fade-slide entrances
- Two-pass process: compact token plan (4-6 hex palette, type roles, layout+ASCII wireframe, principles) → uniqueness review vs brief → build; spend boldness in one element
- Copy: user vocabulary (not system terms), active-voice CTAs naming the exact outcome, errors explain fix without apologizing, sentence case

### supabase-postgres-best-practices
- Load BEFORE any Postgres change — even one column or one query; read the specific `references/<rule>.md` file for the applicable rule
- Query: missing/partial indexes first suspect for slow queries; prove with EXPLAIN before/after
- Connections: pool everything (PgBouncer/Supabase pooler); never per-request connections; watch for exhaustion under worker+API concurrency
- Security: RLS on every tenant table (clinic_id), test policies with wrong-tenant reads; least-privilege roles for API/worker/migrations
- Schema: right-sized types, CHECKs for invariants, gist EXCLUDE for no-overlap (turnos por sillon/odontologo), FK indexes on hot join paths
- Concurrency: short transactions, advisory locks or SKIP LOCKED for job claims (scheduler T-24h, expiracion pendiente_sena 30min), never long-held locks in request path

### test-driven-development
- IRON LAW: no production code without a failing test first; code written before the test gets deleted, not adapted
- RED must fail for the right reason (feature missing, not typo/error); GREEN is minimal code only — no extra features, no drive-by refactors
- Verify both transitions by running tests (RED fail → GREEN pass); refactor only on green, keep suite green
- Full project suite (`pytest`, not just your file) must pass before done; any red test — even uncaused — is named in the report
- Tests assert real behavior with real code (mocks only if unavoidable); one behavior per test, name describes behavior
- Bug fix = failing reproduction test first; hard-to-test = simplify design (DI, smaller surface), never skip

### auth-implementation-patterns
- Separate AuthN (who) from AuthZ (what); enforce RBAC server-side on every endpoint — never client-side checks only
- Passwords: bcrypt/argon2 only, strong policy, secure expiring reset tokens; never plaintext
- JWT: short-lived access (15-30 min), rotated refresh in httpOnly+secure+sameSite cookies; never JWT in localStorage (XSS)
- Claims must include sub/clinic_id/rol/jti; validate all three per request (tenant isolation = clinic_id match)
- Rate-limit auth endpoints (login 5/60s per IP+email via Redis); log login attempts/failed auth; rotate secrets regularly
- OAuth2/OIDC for social/SSO — delegate, don't reimplement; CSRF protection for session-based flows; MFA where possible

### python-fastapi-development
- Stack: Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, Alembic, pytest; config via Pydantic settings, 12 env vars, never hardcode
- Structure: modular domain/infra/api; routers split public/internal/webhooks; response_model on every endpoint; request validation via Pydantic schemas
- DB: session per request with proper close/rollback; migrations via Alembic only; test DB isolated with fixtures
- Auth: JWT strategy + hashing + middleware per auth-implementation-patterns; pick one strategy per service
- Errors: custom exceptions + handlers with consistent error envelope; request logging; no stack traces to clients
- Quality gates: pytest >80% coverage, mypy clean, ruff/black clean, OpenAPI docs complete, Dockerfile+compose for api/postgres/redis/worker

### reglas-turnos-review
- Trigger before any turnos change; read KB 04/05/09 + CHANGES.md first, then the change's openspec artifacts
- Output 3+ verifiable scenarios (happy path, business error, edge) each with a KB rule reference; never invent rules not in the KB
- Always check: email-unique scope per clinic_id, sena_pct 0-100, 2nd no-show → 30d block, cancel <12h, 2nd reschedule, manage_token guessability, sillón/odontólogo overlap, duplicate webhook
- Report lands in `docs/skills-mcp/revision-reglas-turnos.md`, copy-ready for proposal/design/tasks

### pagos-seguridad-review
- Trigger before C-08/C-09 or any change touching Pago / Turno.monto_sena; read KB 11/05/08/04/07 + CHANGES.md
- Enforce: monto_sena is a snapshot at booking (never recalculate), ARS with explicit rounding, one approved payment per turno
- Webhook: verify signature (401 on invalid), idempotent replay (200 no-op), store raw_webhook for audit without leaking PII
- Secrets: MP_ACCESS_TOKEN / MP_WEBHOOK_SECRET / MP_TTL_MIN only from env; add a test/CI scan for hardcoded MP token patterns
- Report lands in `docs/skills-mcp/revision-pagos-seguridad.md`, copy-ready for proposal/design/tasks

## Project Conventions

| File | Path | Notes |
|------|------|-------|
| AGENTS.md / CLAUDE.md | AGENTS.md, CLAUDE.md | Project agent instructions: stack, KB navigation, skills by role, 10 hard rules, workflow |
| Skill registry | .atl/skill-registry.md | Versioned; source of truth for skill→role mapping and compact rules |
| Project skills | skills/reglas-turnos-review/, skills/pagos-seguridad-review/ | Repo-local domain review skills (turnos rules, payments security) |

KB reference for domain rules (read on demand, not injected): `knowledge-base/05_reglas_de_negocio.md` (solape, 12hs, 1 reprogramacion, bloqueo 2 faltas, sena %), `knowledge-base/04_modelo_de_datos.md`, `knowledge-base/08_arquitectura_propuesta.md`, `knowledge-base/11_pagos_mercadopago.md`, `knowledge-base/12_whatsapp_twilio.md`.

Catalog note: `~/.agents/skills/` holds additional on-demand skills (postgres, redis-*, testing, java/spring, golang, microservices, code-review, etc.) and `~/.config/opencode/skills/` holds SDD workflow skills (kb-creator, roadmap-generator, discovery-research, web-scraper, skill-creator, find-skill). Resolve from this registry first; consult catalog only if no installed skill matches.
