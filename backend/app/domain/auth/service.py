"""AuthService: lógica de negocio de autenticación JWT."""

from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import verify_password
from app.domain.auth.models import RefreshTokenBlacklist
from app.domain.personas.models import User


class AuthService:
    """Servicio de autenticación con JWT access + refresh tokens."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def authenticate_user(self, email: str, password: str) -> User | None:
        """Verificar credenciales y retornar el usuario si son válidas."""
        result = await self.session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            return None
        if not verify_password(password, user.password_hash):
            return None
        if not user.activo:
            return None
        return user

    def create_access_token(
        self,
        user: User,
        expires_delta: timedelta | None = None,
    ) -> str:
        """Crear JWT access token con claims: sub, clinic_id, rol, email, jti, type, iat, exp."""
        if expires_delta is None:
            expires_delta = timedelta(minutes=settings.jwt_expires_min)

        now = datetime.now(UTC)
        expire = now + expires_delta
        jti = str(uuid4())

        to_encode: dict[str, Any] = {
            "sub": str(user.id),
            "clinic_id": str(user.clinic_id),
            "rol": user.rol,
            "email": user.email,
            "jti": jti,
            "type": "access",
            "iat": now,
            "exp": expire,
        }
        encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm="HS256")
        return cast(str, encoded_jwt)

    def create_refresh_token(
        self,
        user: User,
        expires_delta: timedelta | None = None,
    ) -> str:
        """Crear JWT refresh token (expiración más larga que access)."""
        if expires_delta is None:
            expires_delta = timedelta(days=7)

        now = datetime.now(UTC)
        expire = now + expires_delta
        jti = str(uuid4())

        to_encode: dict[str, Any] = {
            "sub": str(user.id),
            "clinic_id": str(user.clinic_id),
            "rol": user.rol,
            "email": user.email,
            "jti": jti,
            "type": "refresh",
            "iat": now,
            "exp": expire,
        }
        encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm="HS256")
        return cast(str, encoded_jwt)

    async def blacklist_refresh_token(self, jti: str, user_id: UUID, expires_at: datetime) -> None:
        """Agregar un refresh token a la lista negra."""
        self.session.add(
            RefreshTokenBlacklist(
                jti=jti,
                user_id=user_id,
                expires_at=expires_at,
                is_active=True,
            )
        )
        await self.session.flush()

    async def is_refresh_token_blacklisted(self, jti: str) -> bool:
        """Verificar si un refresh token está en la lista negra."""
        result = await self.session.execute(
            select(RefreshTokenBlacklist).where(RefreshTokenBlacklist.jti == jti)
        )
        return result.scalar_one_or_none() is not None

    async def decode_token(self, token: str) -> dict[str, Any] | None:
        """Decodificar y validar un JWT token."""
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
            return cast(dict[str, Any], payload)
        except JWTError:
            return None
