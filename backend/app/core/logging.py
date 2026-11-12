import logging
import re
import sys
import uuid
from contextvars import ContextVar
from typing import Any

import structlog
from structlog.types import EventDict

from app.core.config import settings

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

# El token de gestión viaja en el path (design D5): ningún logger —propio o de
# terceros, como httpx o uvicorn— debe escribir el valor completo.
_TOKEN_EN_URL = re.compile(r"(/api/public/gestion/)[^/\s\"'?#]+")


class _RedactarTokenFilter(logging.Filter):
    """Borrar el `manage_token` de cualquier mensaje antes de escribirlo."""

    def filter(self, record: logging.LogRecord) -> bool:
        mensaje = record.getMessage()
        if "/api/public/gestion/" in mensaje:
            record.msg = _TOKEN_EN_URL.sub(r"\1[redactado]", mensaje)
            record.args = ()
        return True


class _StdoutHandler(logging.StreamHandler[Any]):
    """Handler que resuelve `sys.stdout` en cada emisión.

    Un `StreamHandler` normal fija el stream al construirse; si luego algo
    reemplaza `sys.stdout` (pytest/capsys), los logs se pierden. Resolverlo en
    `emit` mantiene el destino real del proceso y permite capturar la salida.
    """

    def emit(self, record: logging.LogRecord) -> None:
        self.stream = sys.stdout
        super().emit(record)


def add_request_id(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    request_id = request_id_var.get()
    if request_id:
        event_dict["request_id"] = request_id
    return event_dict


def configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            add_request_id,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)
    if not any(isinstance(handler, _StdoutHandler) for handler in root.handlers):
        handler = _StdoutHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        handler.addFilter(_RedactarTokenFilter())
        root.addHandler(handler)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)  # type: ignore[no-any-return]


def set_request_id(request_id: str | None = None) -> str:
    if request_id is None:
        request_id = str(uuid.uuid4())
    request_id_var.set(request_id)
    return request_id


def clear_request_id() -> None:
    request_id_var.set(None)
