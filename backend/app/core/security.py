"""Utilidades de seguridad compartidas: hash de contraseñas.

Usado por C-02 (seed de usuarios) y C-03 (login/registro).
"""

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Generar hash bcrypt de una contraseña."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verificar que una contraseña en texto plano coincida con su hash."""
    return pwd_context.verify(plain_password, hashed_password)
