# Tasks — C-03 auth-interno-rbac

**Change:** C-03 auth-interno-rbac  
**Schema:** spec-driven  
**Status:** implemented ✅

---

## Task 1 — Create auth domain models, schemas, and service ✅ DONE

Archivos creados:
- `backend/app/domain/auth/__init__.py`
- `backend/app/domain/auth/models.py` — RefreshTokenBlacklist
- `backend/app/domain/auth/schemas.py` — LoginRequest, TokenResponse, UserMe, RefreshRequest
- `backend/app/domain/auth/service.py` — AuthService (authenticate, create tokens, blacklist, decode)
- `backend/app/domain/auth/dependencies.py` — require_role, get_current_user, require_odonto_confinement

**Verificación:** test_auth_login.py, test_auth_refresh.py, test_auth_me.py, test_jwt_claims.py

**Checkbox:** `- [x]`

---

## Task 2 — Create RBAC dependencies and guards ✅ DONE

Archivo: `backend/app/domain/auth/dependencies.py`
- `require_role(["recepcion"|"odonto"|"admin"])` — rejects with 403 if not match
- `get_current_user` — extracts JWT from Authorization header
- `require_odonto_confinement` — confines odontólogo to their sub (user id)

**Verificación:** test_rbac_guards.py

**Checkbox:** `- [x]`

---

## Task 3 — Create auth API router ✅ DONE

Archivos creados:
- `backend/app/api/auth/__init__.py`
- `backend/app/api/auth/router.py` — POST /login, /refresh, /logout, GET /me
- `backend/app/main.py` — auth router included with prefix /api/auth

**Verificación:** Endpoints respond correctly

**Checkbox:** `- [x]`

---

## Task 4 — Create migration 003 ✅ DONE

Archivo: `backend/app/infrastructure/db/migrations/versions/003_auth.py`
- Adds `password_hash` and `activo` to table `users`
- Creates table `refresh_token_blacklist` with jti UNIQUE, user_id FK, expires_at

**Checkbox:** `- [x]`

---

## Task 5 — Implement rate limiting on login ✅ DONE

Archivo: `backend/app/core/rate_limit.py`
- `check_rate_limit(ip, email)` — 5 requests per 60s
- Redis-backed with in-memory fallback

**Verificación:** test_rate_limit.py

**Checkbox:** `- [x]`

---

## Task 6 — Create frontend auth pages and route guard ✅ DONE

Archivos creados:
- `frontend/src/pages/Login.tsx` — login form
- `frontend/src/components/RouteGuard.tsx` — route protection
- `frontend/src/pages/role/RecepcionShell.tsx` — recepcion shell
- `frontend/src/pages/role/OdontoShell.tsx` — odonto shell
- `frontend/src/pages/role/AdminShell.tsx` — admin shell
- `frontend/src/router/index.tsx` — ruta /login ya existía

**Checkbox:** `- [x]`

---

## Task 7 — Tests suite ✅ DONE

Archivos creados:
- `backend/tests/test_auth_login.py` — login correcto, contraseña incorrecta, usuario inexistente, inactivo
- `backend/tests/test_auth_refresh.py` — rotación invalida anterior
- `backend/tests/test_auth_logout.py` — limpia cookie
- `backend/tests/test_auth_me.py` — sin token 401, con token válido 200
- `backend/tests/test_jwt_claims.py` — claims requeridos, tipo refresh
- `backend/tests/test_refresh_cookie.py` — cookie HttpOnly, samesite=lax
- `backend/tests/test_rbac_guards.py` — rol recepcion, admin, odonto no admin
- `backend/tests/test_rate_limit.py` — 5 permitidos, 6to rechazado

**Checkbox:** `- [x]`

---

## Edge Case Verification ✅ DONE

| Edge case | Task | Verification |
|-----------|------|--------------|
| Wrong password login | Task 1 | 401, no token (test_auth_login.py) |
| Blacklisted refresh token | Task 1 | 401, rotation rejected (test_auth_refresh.py) |
| Rate limit exceeded | Task 5 | 429 after 5 requests/60s (test_rate_limit.py) |
| Odonto accessing another odonto's data | Task 2 | 403 via require_role (test_rbac_guards.py) |
| Admin accessing all routes | Task 2 | rol admin permitido (test_rbac_guards.py) |

**Checkbox:** `- [x]`

---

## Implementation order

Tasks 1 → 2 → 3 → 4 → 5 → 6 → 7. Todos completados ✅
