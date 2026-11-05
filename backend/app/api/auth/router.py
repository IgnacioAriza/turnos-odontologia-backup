"""Router de autenticación: login, refresh, logout, me."""

from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from jose import jwt

from app.core.config import settings
from app.domain.auth.dependencies import get_auth_service, get_current_user
from app.domain.auth.schemas import LoginRequest, TokenResponse, UserMe
from app.domain.auth.service import AuthService
from app.infrastructure.db.session import async_session

router = APIRouter(tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    login_data: LoginRequest,
    response: Response,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    """Autenticar usuario y devolver access + refresh tokens.

    Rate limiting: 5 requests por 60s por IP+email (implementado en middleware/dependency).
    """
    user = await auth_service.authenticate_user(login_data.email, login_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )

    access_token = auth_service.create_access_token(user)
    refresh_token = auth_service.create_refresh_token(user)

    # Decodificar refresh token para obtener jti y expiración
    jwt.decode(
        refresh_token,
        settings.JWT_SECRET,
        algorithms=["HS256"],
    )

    # Establecer refresh token en cookie HttpOnly
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,  # True en producción (HTTPS)
        samesite="lax",
        path="/api/auth",
        max_age=int(timedelta(days=7).total_seconds()),
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=int(timedelta(minutes=settings.JWT_EXPIRES_MIN).total_seconds()),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    refresh_token: Annotated[str | None, Cookie()] = None,
    auth_service: Annotated[AuthService, Depends(get_auth_service)] = None,
):
    """Rotar refresh token y devolver nuevo access + refresh."""
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token requerido",
        )

    payload = await auth_service.decode_token(refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido",
        )

    jti = payload.get("jti")
    if await auth_service.is_refresh_token_blacklisted(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revocado",
        )

    user_id = UUID(payload.get("sub"))
    # Blacklist del refresh token anterior
    refresh_exp = datetime.fromtimestamp(payload.get("exp", 0), tz=UTC)
    await auth_service.blacklist_refresh_token(jti, user_id, refresh_exp)

    # Obtener usuario completo para crear nuevos tokens
    from sqlalchemy import select

    from app.domain.personas.models import User

    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
        )

    access_token = auth_service.create_access_token(user)
    new_refresh_token = auth_service.create_refresh_token(user)

    new_payload = jwt.decode(
        new_refresh_token,
        settings.JWT_SECRET,
        algorithms=["HS256"],
    )
    new_jti = new_payload.get("jti")
    new_exp = datetime.fromtimestamp(new_payload.get("exp", 0), tz=UTC)
    await auth_service.blacklist_refresh_token(new_jti, user_id, new_exp)

    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        path="/api/auth",
        max_age=int(timedelta(days=7).total_seconds()),
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=int(timedelta(minutes=settings.JWT_EXPIRES_MIN).total_seconds()),
    )


@router.post("/logout")
async def logout(
    response: Response,
    refresh_token: Annotated[str | None, Cookie()] = None,
    auth_service: Annotated[AuthService, Depends(get_auth_service)] = None,
):
    """Blacklistear refresh token y limpiar cookie."""
    if refresh_token:
        payload = await auth_service.decode_token(refresh_token)
        if payload:
            jti = payload.get("jti")
            user_id = UUID(payload.get("sub"))
            exp = datetime.fromtimestamp(payload.get("exp", 0), tz=UTC)
            await auth_service.blacklist_refresh_token(jti, user_id, exp)

    response.delete_cookie(key="refresh_token", path="/api/auth")
    return {"detail": "Sesión cerrada"}


@router.get("/me", response_model=UserMe)
async def me(
    current_user: Annotated[dict | None, Depends(get_current_user)] = None,
):
    """Obtener perfil del usuario autenticado."""
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
        )

    return UserMe(
        id=UUID(current_user.get("sub")),
        email=current_user.get("email"),
        rol=current_user.get("rol"),
        clinic_id=UUID(current_user.get("clinic_id")),
        activo=True,
    )
