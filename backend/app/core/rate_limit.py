"""Rate limiting para endpoint de login.

5 requests por 60 segundos por IP+email. Usa Redis cuando está disponible,
con fallback a almacenamiento en memoria para tests.
"""

import time
from collections import defaultdict

try:
    import redis as redis_lib

    _redis_available = True
except ImportError:
    _redis_available = False

# Almacenamiento en memoria (fallback para tests)
_memory_store: dict[str, list[float]] = defaultdict(list)

RATE_LIMIT_REQUESTS = 5
RATE_LIMIT_WINDOW = 60  # segundos


def _get_key(ip: str, email: str) -> str:
    return f"ratelimit:login:{ip}:{email}"


def check_rate_limit(ip: str, email: str) -> tuple[bool, int]:
    """Verificar si el request excede el rate limit.

    Returns:
        (allowed, remaining_seconds) - si está permitido y cuánto esperar si no.
    """
    key = _get_key(ip, email)
    now = time.time()

    if _redis_available:
        try:
            r = redis_lib.Redis.from_url("redis://localhost:6379/0", decode_responses=True)
            pipe = r.pipeline()
            pipe.zadd(key, {str(now): now})
            pipe.zremrangebyscore(key, 0, now - RATE_LIMIT_WINDOW)
            pipe.expire(key, RATE_LIMIT_WINDOW)
            pipe.zcard(key)
            results = pipe.execute()
            count = results[3]
            if count > RATE_LIMIT_REQUESTS:
                # Calcular tiempo hasta que expire el más antiguo
                oldest = r.zrange(key, 0, 0, withscores=True)
                if oldest:
                    score = float(oldest[0][1])
                    retry_after = int(score + RATE_LIMIT_WINDOW - now)
                    return False, max(0, retry_after)
                return False, RATE_LIMIT_WINDOW
            return True, 0
        except Exception:
            # Fallback a memoria si Redis falla
            pass

    # Fallback: almacenamiento en memoria
    _memory_store[key] = [t for t in _memory_store[key] if t > now - RATE_LIMIT_WINDOW]
    _memory_store[key].append(now)

    if len(_memory_store[key]) > RATE_LIMIT_REQUESTS:
        oldest_ts = min(_memory_store[key])
        retry_after = int(oldest_ts + RATE_LIMIT_WINDOW - now)
        return False, max(0, retry_after)

    return True, 0
