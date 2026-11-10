# Tasks — C-03 auth-interno-rbac

> Estado final: implementado, verificado y archivado el 2026-11-10.

## 1. Dominio de auth

- [x] 1.1 Crear `backend/app/domain/auth/models.py` con `RefreshTokenBlacklist`.
- [x] 1.2 Crear `backend/app/domain/auth/schemas.py` con `LoginRequest`, `TokenResponse`, `UserMe` y `RefreshRequest`.
- [x] 1.3 Crear `backend/app/domain/auth/service.py` con `AuthService` (authenticate, creación de tokens, blacklist y decode).
- [x] 1.4 Crear `backend/app/domain/auth/dependencies.py` con `require_role`, `get_current_user` y `require_odonto_confinement`.

## 2. RBAC y guards

- [x] 2.1 Implementar `require_role(["recepcion"|"odonto"|"admin"])`, que rechaza con 403 cuando el rol no coincide.
- [x] 2.2 Implementar `get_current_user`, que extrae el JWT del header `Authorization`.
- [x] 2.3 Implementar `require_odonto_confinement`, que confina al odontólogo a su propio `sub` (user id) — verificado en `tests/test_rbac_guards.py`.

## 3. API de auth

- [x] 3.1 Crear `backend/app/api/auth/router.py` con `POST /login`, `POST /refresh`, `POST /logout` y `GET /me`.
- [x] 3.2 Registrar el router en `backend/app/main.py` con prefijo `/api/auth`.
- [x] 3.3 Verificar que los endpoints responden correctamente.

## 4. Migración 003

- [x] 4.1 Crear `backend/app/infrastructure/db/migrations/versions/003_auth.py` con la tabla `refresh_token_blacklist` (`jti` UNIQUE, `user_id` FK, `expires_at`).
- [x] 4.2 Corregir la migración para no duplicar `users.password_hash` ni `users.activo`, que ya crea la migración 002.

## 5. Rate limiting

- [x] 5.1 Crear `backend/app/core/rate_limit.py` con `check_rate_limit(ip, email)`: 5 requests por 60s, respaldado por Redis con fallback en memoria.
- [x] 5.2 Verificar el límite en `tests/test_rate_limit.py` (5 permitidos, el 6.º rechazado con 429).

## 6. Frontend

- [x] 6.1 Crear `frontend/src/pages/Login.tsx` con el formulario de login.
- [x] 6.2 Crear `frontend/src/components/RouteGuard.tsx` para protección de rutas.
- [x] 6.3 Crear `frontend/src/pages/role/RecepcionShell.tsx`, `OdontoShell.tsx` y `AdminShell.tsx`.
- [x] 6.4 Verificar la ruta `/login` en el router.

## 7. Suite de tests

- [x] 7.1 `backend/tests/test_auth_login.py` — login correcto, contraseña incorrecta, usuario inexistente e inactivo.
- [x] 7.2 `backend/tests/test_auth_refresh.py` — la rotación invalida el token anterior.
- [x] 7.3 `backend/tests/test_auth_logout.py` — limpia la cookie.
- [x] 7.4 `backend/tests/test_auth_me.py` — sin token 401, con token válido 200.
- [x] 7.5 `backend/tests/test_jwt_claims.py` — claims requeridos y tipo refresh.
- [x] 7.6 `backend/tests/test_refresh_cookie.py` — cookie HttpOnly y `samesite=lax`.
- [x] 7.7 `backend/tests/test_rbac_guards.py` — rol recepción, admin y odonto no admin.

## 8. Verificación de casos borde

- [x] 8.1 Contraseña incorrecta → 401 sin token (`test_auth_login.py`).
- [x] 8.2 Refresh token en blacklist → 401 y rotación rechazada (`test_auth_refresh.py`).
- [x] 8.3 Rate limit excedido → 429 después de 5 requests/60s (`test_rate_limit.py`).
- [x] 8.4 Odontólogo accediendo a datos de otro odontólogo → 403 vía `require_role` (`test_rbac_guards.py`).
- [x] 8.5 Admin accediendo a todas las rutas → rol admin permitido (`test_rbac_guards.py`).
