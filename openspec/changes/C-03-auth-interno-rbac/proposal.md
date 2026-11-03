# Proposal — C-03 auth-interno-rbac

## Why

C-03 is Gate 2 in the critical path, depends on C-02, and unlocks ALL internal routes (C-04 catálogo, C-05 motor, C-06/C-07/C-08). Without authentication and RBAC, no internal endpoint can be protected. Login paciente (v1.1 C-11) is explicitly out of scope.

## What Changes

### Backend auth domain
- `RefreshTokenBlacklist` model — jti, user_id, expires_at, is_active
- `AuthService` — authenticate_user, create_access_token, create_refresh_token, blacklist_refresh_token, is_refresh_token_blacklisted, decode_token
- Auth schemas — LoginRequest, TokenResponse, UserMe, RefreshRequest
- Auth dependencies — `get_current_user`, `require_role([...])`, `require_odonto_confinement`

### Backend API router
- `POST /api/auth/login` — JWT access + refresh, rate limiting 5/60s per IP+email
- `POST /api/auth/refresh` — rotation + blacklist previous refresh token
- `POST /api/auth/logout` — blacklist refresh token
- `GET /api/auth/me` — current user from JWT claims

### Frontend auth
- `/login` page with email/password form
- `RouteGuard` component — protects routes, redirects to /login
- Role shells: RecepcionShell, OdontoShell, AdminShell
- Router: /login route added, protected routes with role guards

### Migration 003
- `password_hash` column on `users` (NOT NULL)
- `activo` column on `users` (default true)
- `refresh_token_blacklist` table (jti UNIQUE, user_id FK, expires_at)

### Rate limiting
- 5 requests per 60 seconds per IP+email on login endpoint
- Redis-backed with in-memory fallback

### Tests
- Login correcto, contraseña incorrecta, usuario inexistente, usuario inactivo
- Refresh rotation invalidates previous token
- Logout clears cookie
- GET /me without token → 401, with valid token → 200
- JWT claims: sub, clinic_id, rol, email, jti, type, iat, exp
- Refresh cookie: HttpOnly, secure, samesite=lax
- RBAC guards: require_role, odonto confinement, admin total access
- Rate limit: 5 allowed, 6th rejected (429)

## Capabilities

### New Capabilities

- `auth-rbac/auth-service`: JWT access + refresh token lifecycle with rotation
- `auth-rbac/rbac-guards`: Role-based access control with odontólogo confinement
- `auth-rbac/auth-api`: Login/refresh/logout/me endpoints with rate limiting
- `auth-rbac/frontend-auth`: Login page, route guard, role-based shells

### Modified Capabilities

- `backend/app/main.py` — auth router included with prefix /api/auth
- `backend/app/domain/personas/models.py` — User model already has password_hash, rol, odontologo_id from C-02

## Impact

- **Code**: New auth domain, auth API router, migration 003, rate limiter, frontend auth pages
- **APIs**: POST /api/auth/login, /refresh, /logout; GET /api/auth/me
- **Dependencies**: python-jose[cryptography] (already in pyproject.toml)
- **Systems**: Redis for rate limiting and refresh token blacklist (already in C-01)

## Dependencies

- C-02 core-models-clinica-personas (User model with password_hash, rol, clinic_id)

## Out of Scope

- Login paciente (C-11, v1.1)
- OAuth2/social login
- MFA
- Password reset flow
