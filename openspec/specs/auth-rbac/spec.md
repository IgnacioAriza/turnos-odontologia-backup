# Spec — auth-rbac

## Purpose

Autenticación JWT + RBAC para roles internos. Establece login, refresh, logout, guards por rol y confinamiento de odontólogos. Login de paciente queda para C-11 (v1.1).

## Requirements

### Requirement: Auth endpoints

The backend SHALL expose `POST /api/auth/login`, `POST /api/auth/refresh`, `POST /api/auth/logout` and `GET /api/auth/me` under `/api/auth`, validating credentials against the `users` table.

#### Scenario: Successful login

- **WHEN** `POST /api/auth/login` receives a valid email and password
- **THEN** the response is 200 with an access token and a refresh token

#### Scenario: Invalid credentials

- **WHEN** `POST /api/auth/login` receives a wrong password
- **THEN** the response is 401 and no token is issued

#### Scenario: All auth endpoints are mounted

- **WHEN** the application starts
- **THEN** `POST /login`, `POST /refresh`, `POST /logout` and `GET /me` are available under `/api/auth/`

### Requirement: JWT access token claims

Access tokens SHALL include `sub`, `clinic_id`, `rol`, `email`, `jti`, `type`, `iat` and `exp`, and access expiry SHALL be shorter than refresh expiry.

#### Scenario: Access token carries the required claims

- **WHEN** a user logs in successfully
- **THEN** the access token includes `sub`, `clinic_id`, `rol`, `email`, `jti`, `type`, `iat` and `exp`

#### Scenario: Access token expires before the refresh token

- **WHEN** both tokens are issued
- **THEN** the `exp` of the access token is earlier than the `exp` of the refresh token

#### Scenario: Unique jti per token

- **WHEN** two tokens are issued to the same user
- **THEN** each token has a different `jti`

### Requirement: Refresh token in HttpOnly cookie

The refresh token SHALL travel in an HttpOnly cookie with `secure` enabled in production and `samesite=lax`, so JavaScript cannot read it.

#### Scenario: Refresh cookie flags

- **WHEN** the user logs in or refreshes the session
- **THEN** the refresh token is set in an HttpOnly cookie with `samesite=lax`

#### Scenario: Access token stays out of the cookie

- **WHEN** login succeeds
- **THEN** the access token is returned in the response body, not in the cookie

#### Scenario: Logout clears the cookie and blacklists the token

- **WHEN** `POST /api/auth/logout` is called
- **THEN** the refresh cookie is cleared and the refresh token is blacklisted

### Requirement: RBAC guards

Internal routes SHALL enforce role-based access with `require_role`, confine odontólogos to their own `odontologo_id`, and give `admin` explicit total access without inheritance.

#### Scenario: Unauthorized role is rejected

- **WHEN** a user without the required role calls a guarded internal route
- **THEN** the response is 403

#### Scenario: Odontólogo is confined to own data

- **WHEN** a user with `rol='odonto'` queries appointments or patients
- **THEN** results are filtered by their `odontologo_id`

#### Scenario: Admin has total access

- **WHEN** a user with `rol='admin'` calls any internal route
- **THEN** access is granted (200)

### Requirement: Auth migration 003

Alembic migration 003 SHALL add `password_hash` and `activo` to `users`, and create a refresh-token blacklist table with unique `jti` and `expires_at`.

#### Scenario: Migration creates the auth schema

- **WHEN** `alembic upgrade head` runs
- **THEN** `users.password_hash` is NOT NULL, `users.activo` defaults to true, and the blacklist table has unique `jti` and `expires_at`

#### Scenario: Migration rolls back

- **WHEN** `alembic downgrade -1` runs after migration 003
- **THEN** the blacklist table is dropped and the columns are removed without error

### Requirement: Frontend authentication

The frontend SHALL provide a `/login` page, a route guard that redirects unauthenticated users to `/login`, and role shells for recepción, odontólogo and admin.

#### Scenario: Login route exists

- **WHEN** the frontend router is loaded
- **THEN** the `/login` route renders the email/password form

#### Scenario: Protected route redirects

- **WHEN** an unauthenticated user opens a protected route
- **THEN** the app redirects to `/login`

#### Scenario: Role shells exist

- **WHEN** a user with each role signs in
- **THEN** the corresponding recepción, odontólogo or admin shell is available

### Requirement: Auth test coverage

Tests SHALL cover login, expired tokens, refresh rotation, rate limiting and cross-odontólogo access.

#### Scenario: Auth suite passes

- **WHEN** `pytest` runs
- **THEN** the auth tests for login, expiry, rotation, rate limit and RBAC pass

#### Scenario: Rate limit is enforced

- **WHEN** six login attempts arrive from the same IP+email within 60 seconds
- **THEN** the sixth request returns 429

## Constraints

- Login de paciente NO entra (va en C-11, v1.1)
- `JWT_SECRET` y `JWT_EXPIRES_MIN` via environment variables
- Refresh cookie: HttpOnly, secure, samesite=lax
- Stack: Python/FastAPI/JWT/SQLAlchemy/PostgreSQL/Redis/Docker-Compose + React/TypeScript/Vite
