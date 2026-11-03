# Spec — C-03 auth-interno-rbac

## Purpose

Autenticación JWT + RBAC para roles internos. Establece login, refresh, logout, guards por rol, y confinamiento de odontólogos. Login paciente queda para C-11 (v1.1).

## Requirements

### R1 — Auth endpoints
The backend SHALL expose:

- `POST /api/auth/login` — accepts email + password, returns JWT access + refresh tokens. Rate limiting 5/60s per IP+email.
- `POST /api/auth/refresh` — accepts refresh token, returns new access + refresh (rotation + blacklist previous).
- `POST /api/auth/logout` — blacklists the refresh token.
- `GET /api/auth/me` — returns current user profile from JWT claims.

**Acceptance criteria:**
- All endpoints exist under `/api/auth/`.
- Login validates credentials against `users` table.
- Refresh rotation invalidates previous refresh token.
- Logout blacklists refresh token.
- Rate limiting: 5 requests per 60 seconds per IP+email.

### R2 — JWT claims
JWT access token SHALL include claims:
- `sub` (user ID), `clinic_id`, `rol`, `email`, `jti`, `type` ("access" or "refresh"), `iat`, `exp`

**Acceptance criteria:**
- Access token expiration: `JWT_EXPIRES_MIN` (default 480 min, but 30 in current config — see deviation)
- Refresh token expiration: longer than access (e.g., 7 days)
- `jti` is unique per token for blacklisting

### R3 — Refresh token in HttpOnly cookie
Refresh token SHALL be stored in an HttpOnly cookie:
- `secure` flag (HTTPS only in production)
- `samesite=lax`
- Read-only via JavaScript (mitigates XSS)

**Acceptance criteria:**
- Refresh token is set as HttpOnly cookie on login/refresh
- Cookie is cleared on logout
- Access token is returned in response body (not cookie)

### R4 — RBAC guards
Router guards SHALL enforce:
- `require_role("recepcion"|"odonto"|"admin")` on internal routes
- Odontólogo confined to their `odontologo_id` (can only see their own appointments/patients)
- `admin` has explicit total permissions (no inheritance)

**Acceptance criteria:**
- `require_role` dependency exists and rejects unauthorized roles with 403
- Odontólogo queries filter by their `odontologo_id`
- Admin can access all internal routes

### R5 — Migration 003
Alembic migration SHALL add:
- `password_hash` column to `users` (already in C-02 model, add via migration)
- `activo` column to `users` (already in C-02 model, add via migration)
- Refresh token blacklist table

**Acceptance criteria:**
- Migration file exists under `backend/app/infrastructure/db/migrations/versions/`
- `password_hash` is NOT NULL
- `activo` defaults to True
- Blacklist table has `jti` (unique) and `expires_at`

### R6 — Frontend auth
Frontend SHALL provide:
- `/login` page with email/password form
- Route guard for protected routes (redirects to `/login` if not authenticated)
- Base pages by role (shell only, no features)

**Acceptance criteria:**
- `/login` route exists in frontend router
- Protected routes redirect unauthenticated users to `/login`
- Role-based page shells exist for recepcion, odonto, admin

### R7 — Tests
Tests SHALL cover:
- Login correcto (valid credentials → 200 + tokens)
- Token expirado → 401
- Refresh rotation (old refresh invalidated after use)
- Rate limit (5/60s per IP+email → 429)
- Acceso cruzado: odonto A no puede ver datos de odonto B → 403

**Acceptance criteria:**
- Test files exist under `backend/tests/` and/or frontend test files
- All tests pass

## Constraints

- Login paciente NO entra (va en C-11, v1.1)
- `JWT_SECRET` and `JWT_EXPIRES_MIN` via environment variables
- Refresh cookie: HttpOnly, secure, samesite=lax
- Stack: Python/FastAPI/JWT/SQLAlchemy/PostgreSQL/Redis/Docker-Compose + React/TypeScript/Vite

## Edge Cases

1. Login with wrong password → 401, no token issued
2. Refresh token already blacklisted → 401, reject rotation
3. Concurrent logins from same IP+email → rate limit after 5 requests
4. Odontólogo accessing another odontólogo's patients → 403
5. Admin accessing all routes → 200 (no restrictions)

## Scenarios

### Scenario: Successful login
- **WHEN** POST /api/auth/login with valid credentials
- **THEN** response 200 with access_token and refresh_token

### Scenario: Invalid credentials
- **WHEN** POST /api/auth/login with wrong password
- **THEN** response 401

### Scenario: Refresh token rotation
- **WHEN** POST /api/auth/refresh with valid refresh token
- **THEN** new access_token + new refresh_token; old refresh_token blacklisted

### Scenario: Rate limiting
- **WHEN** 6 login requests from same IP+email within 60 seconds
- **THEN** 6th request returns 429

### Scenario: RBAC — odontólogo confinement
- **WHEN** user with rol='odonto' accesses protected route
- **THEN** can only see their own data (filtered by odontologo_id)

### Scenario: RBAC — admin total access
- **WHEN** user with rol='admin' accesses any internal route
- **THEN** access granted (200)
