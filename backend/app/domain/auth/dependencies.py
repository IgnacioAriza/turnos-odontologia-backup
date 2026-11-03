"""Dependencias de RBAC y autenticación para rutas internas."""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status, Request
from jose import jwt, JWTError

from app.core.config import settings
from app.domain.auth.service import AuthService


async def get_auth_service(request: Request) -> AuthService:
    """Obtener instancia de AuthService con la sesión de BD de la request."""
    from app.infrastructure.db.session import async_session

    async with async_session() as session:
        return AuthService(session)


async def get_current_user(
    request: Request,
) -> Optional[dict]:
    """Extraer y validar el usuario actual desde el JWT Bearer token."""
    from app.infrastructure.db.session import async_session

    authorization = request.headers.get("authorization")
    if not authorization:
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=["HS256"],
        )
        return payload
    except JWTError:
        return None


def require_role(allowed_roles: list[str]):
    """Dependency factory para exigir un rol específico en rutas internas.

    Uso:
        @router.get("/admin/aranceles", dependencies=[Depends(require_role(["admin"]))])
    """

    async def role_checker(
        current_user: Annotated[Optional[dict], Depends(get_current_user)]
    ):
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No autenticado",
            )
        rol = current_user.get("rol")
        if rol not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rol requerido: {', '.join(allowed_roles)}",
            )
        return current_user

    return role_checker


def require_odonto_confinement(
    current_user: Annotated[Optional[dict], Depends(get_current_user)]
):
    """Confinar odontólogo a su propio odontologo_id.

    Si el rol es odonto, retorna el odontologo_id para filtrar consultas.
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
        )
    if current_user.get("rol") == "odonto":
        return current_user.get("sub")  # odontologo_id = user id
    return None
