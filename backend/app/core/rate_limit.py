"""Rate limiting parametrizable por scope y clave.

Usa Redis cuando está disponible, con fallback a almacenamiento en memoria para
tests. El login conserva su política de 5 requests por 60 segundos por IP+email;
la gestión pública usa un scope y un límite por IP y por token (design.md D8).
"""

import time
from collections import defaultdict

from app.core.config import settings

try:
    import redis as redis_lib
    from redis.exceptions import RedisError

    _redis_available = True
except ImportError:
    redis_lib = None  # type: ignore
    RedisError = Exception  # type: ignore
    _redis_available = False

# Almacenamiento en memoria (fallback para tests)
_memory_store: dict[str, list[float]] = defaultdict(list)

RATE_LIMIT_REQUESTS = 5
RATE_LIMIT_WINDOW = 60  # segundos

REDIS_URL = settings.redis_url
# Timeouts cortos: si Redis no está, el fallback en memoria no debe colgar requests.
REDIS_TIMEOUT_SEG = 0.2


def _redis_key(scope: str, key: str) -> str:
    return f"ratelimit:{scope}:{key}"


def reset_rate_limit_store() -> None:
    """Vaciar el fallback en memoria (tests y reinicios de proceso)."""
    _memory_store.clear()


def check_rate_limit(scope: str, key: str, limit: int, window: int) -> tuple[bool, int]:
    """Verificar si el request excede el límite del scope.

    Args:
        scope: familia del límite (`login`, `gestion_ip`, `gestion_token`…).
        key: identificador dentro del scope (IP, token, email…).
        limit: cantidad máxima de requests permitidos en la ventana.
        window: ventana en segundos.

    Returns:
        (allowed, remaining_seconds) - si está permitido y cuánto esperar si no.
    """
    if limit <= 0:
        raise ValueError("limit debe ser mayor a cero")
    if window <= 0:
        raise ValueError("window debe ser mayor a cero")

    redis_key = _redis_key(scope, key)
    now = time.time()

    if _redis_available and settings.rate_limit_backend != "memory":
        try:
            r = redis_lib.Redis.from_url(
                REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=REDIS_TIMEOUT_SEG,
                socket_timeout=REDIS_TIMEOUT_SEG,
            )
            pipe = r.pipeline()
            pipe.zadd(redis_key, {str(now): now})
            pipe.zremrangebyscore(redis_key, 0, now - window)
            pipe.expire(redis_key, window)
            pipe.zcard(redis_key)
            results = pipe.execute()
            count = results[3]
            if count > limit:
                # Calcular tiempo hasta que expire el más antiguo
                oldest = r.zrange(redis_key, 0, 0, withscores=True)
                if oldest:
                    score = float(oldest[0][1])
                    retry_after = int(score + window - now)
                    return False, max(0, retry_after)
                return False, window
            return True, 0
        except RedisError:
            # Fallback a memoria si Redis no está disponible
            pass

    # Fallback: almacenamiento en memoria
    _memory_store[redis_key] = [t for t in _memory_store[redis_key] if t > now - window]
    _memory_store[redis_key].append(now)

    if len(_memory_store[redis_key]) > limit:
        oldest_ts = min(_memory_store[redis_key])
        retry_after = int(oldest_ts + window - now)
        return False, max(0, retry_after)

    return True, 0


def check_login_rate_limit(ip: str, email: str) -> tuple[bool, int]:
    """Política de login: 5 requests por 60 segundos por IP+email."""
    return check_rate_limit(
        "login", f"{ip}:{email}", limit=RATE_LIMIT_REQUESTS, window=RATE_LIMIT_WINDOW
    )


__all__ = [
    "RATE_LIMIT_REQUESTS",
    "RATE_LIMIT_WINDOW",
    "check_login_rate_limit",
    "check_rate_limit",
    "reset_rate_limit_store",
]
