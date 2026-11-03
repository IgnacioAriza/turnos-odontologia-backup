"""Utilidades de seguridad compartidas: hash de contraseñas.

Usado por C-02 (seed de usuarios) y C-03 (login/registro).
"""

import bcrypt


def hash_password(password: str) -> str:
    """Generar hash bcrypt de una contraseña."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verificar que una contraseña en texto plano coincida con su hash."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
