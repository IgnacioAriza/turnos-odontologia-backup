# Design — C-03 auth-interno-rbac

## Context

Builds on C-02 (User model with password_hash, rol, clinic_id, odontologo_id) and C-01 (FastAPI app, Pydantic settings, Redis, structlog, exception handlers). Follows KB 03_actores_y_roles.md RBAC matrix, KB 05_reglas_de_negocio.md exceptions, KB 08_arquitectura_propuesta.md security section.

## Architecture Decisions

### 1. JWT Bearer for internal routes
**Decision**: All `/api/internal/` routes require JWT Bearer token. Public routes (`/api/public/`) do not require JWT (used by patient booking in C-06).
**Rationale**: Separation of concerns — public booking needs no friction, internal panel needs auth.
**Alternatives**: JWT on all routes (rejected — breaks public booking).

### 2. Refresh token in HttpOnly cookie
**Decision**: Refresh token stored in HttpOnly, secure, samesite=lax cookie. Access token returned in response body.
**Rationale**: Mitigates XSS theft of refresh tokens while allowing access token via Authorization header.
**Alternatives**: Both tokens in localStorage (rejected — XSS vulnerability); both in cookies (rejected — CSRF complexity).

### 3. Refresh token rotation
**Decision**: On each refresh, previous refresh token's jti is blacklisted. New refresh token with new jti issued.
**Rationale**: Prevents refresh token reuse attacks. If a refresh token is stolen, it can only be used once.
**Alternatives**: No rotation (rejected — security risk).

### 4. Rate limiting on login
**Decision**: 5 requests per 60 seconds per IP+email on `/api/auth/login`. Uses Redis for production, in-memory fallback for tests.
**Rationale**: Prevents brute force attacks on login. Redis allows distributed rate limiting across API instances.
**Alternatives**: In-memory only (rejected — doesn't work with multiple API instances); no rate limiting (rejected — security violation).

### 5. Refresh token blacklist (SQL table)
**Decision**: Blacklist stored in SQL table `refresh_token_blacklist` (not Redis).
**Rationale**: Simpler than managing Redis keys for blacklist; persists across Redis restarts; consistent with SQLAlchemy pattern.
**Alternatives**: Redis-based blacklist (rejected — adds complexity, needs TTL management).

### 6. Odontólogo confinement via odontologo_id
**Decision**: `User.odontologo_id` self-referential FK. When rol='odonto', queries filter by this ID.
**Rationale**: Matches KB 03 RBAC — odontólogo sees only their own appointments/patients.
**Alternatives**: Separate Odontólogo table (rejected — over-engineering).

### 7. Admin has explicit total permissions (no inheritance)
**Decision**: Admin role has all permissions explicitly, no role hierarchy/inheritance.
**Rationale**: Simpler to audit, matches KB 03 "admin con permisos explícitos totales (sin herencia)".
**Alternatives**: Role inheritance (rejected — harder to audit).

## Directory Structure

```
backend/app/domain/auth/
├── __init__.py
├── models.py          # RefreshTokenBlacklist
├── schemas.py         # LoginRequest, TokenResponse, UserMe, RefreshRequest
├── service.py         # AuthService (login, refresh, logout, me, blacklist)
└── dependencies.py    # require_role, get_current_user, require_odonto_confinement

backend/app/api/auth/
├── __init__.py
└── router.py          # POST /login, /refresh, /logout, GET /me

backend/app/core/security.py
├── Already exists (password hashing from C-02)

backend/app/infrastructure/db/migrations/versions/
├── 003_auth.py        # Migration 003: password_hash, activo, blacklist table

backend/tests/
├── test_auth_login.py
├── test_auth_refresh.py
├── test_auth_logout.py
├── test_auth_me.py
├── test_jwt_claims.py
├── test_refresh_cookie.py
├── test_rbac_guards.py
└── test_rate_limit.py

frontend/src/pages/Login.tsx
frontend/src/components/RouteGuard.tsx
frontend/src/pages/role/RecepcionShell.tsx
frontend/src/pages/role/OdontoShell.tsx
frontend/src/pages/role/AdminShell.tsx
frontend/src/router/index.tsx  (modified — add /login route)
```

## Files to Create

| File | Purpose |
|------|---------|
| `backend/app/domain/auth/__init__.py` | Auth domain init |
| `backend/app/domain/auth/models.py` | RefreshTokenBlacklist model |
| `backend/app/domain/auth/schemas.py` | Pydantic request/response schemas |
| `backend/app/domain/auth/service.py` | AuthService business logic |
| `backend/app/domain/auth/dependencies.py` | require_role, get_current_user |
| `backend/app/api/auth/__init__.py` | Auth API init |
| `backend/app/api/auth/router.py` | Auth API routes |
| `backend/app/infrastructure/db/migrations/versions/003_auth.py` | Migration 003 |
| `backend/tests/test_auth_login.py` | Login tests |
| `backend/tests/test_auth_refresh.py` | Refresh rotation tests |
| `backend/tests/test_auth_logout.py` | Logout blacklist tests |
| `backend/tests/test_auth_me.py` | Get current user tests |
| `backend/tests/test_jwt_claims.py` | JWT claims verification |
| `backend/tests/test_refresh_cookie.py` | Cookie attributes tests |
| `backend/tests/test_rbac_guards.py` | Role guard tests |
| `backend/tests/test_rate_limit.py` | Rate limiting tests |
| `frontend/src/pages/Login.tsx` | Login page |
| `frontend/src/components/RouteGuard.tsx` | Route protection guard |
| `frontend/src/pages/role/RecepcionShell.tsx` | Recepcion role shell |
| `frontend/src/pages/role/OdontoShell.tsx` | Odonto role shell |
| `frontend/src/pages/role/AdminShell.tsx` | Admin role shell |

## Files to Modify

| File | Change |
|------|--------|
| `backend/app/main.py` | Add auth router inclusion (`app.include_router(auth_router, prefix="/api/auth", tags=["auth"])`) |
| `frontend/src/router/index.tsx` | Add /login route |

## Verification Strategy

Each requirement in spec.md has corresponding tests:
- R1 (auth endpoints) → test_auth_login.py, test_auth_refresh.py, test_auth_logout.py, test_auth_me.py
- R2 (JWT claims) → test_jwt_claims.py
- R3 (refresh cookie) → test_refresh_cookie.py
- R4 (RBAC guards) → test_rbac_guards.py
- R5 (migration 003) → test_migration_003.py (implicit in auth tests)
- R6 (frontend auth) → Frontend build + route guard tests
- R7 (tests suite) → Full test suite

Edge cases to verify:
- Wrong password → 401, no token
- Blacklisted refresh token → 401, rotation rejected
- Rate limit exceeded → 429 after 5 requests/60s
- Odontólogo accessing another odontólogo's data → 403
- Admin accessing all routes → 200
