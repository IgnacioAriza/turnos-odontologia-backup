import re
from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

logger = get_logger(__name__)

# El token de gestión viaja en el path (design D5): jamás debe llegar a logs
# ni al campo `instance` del problem+json.
_TOKEN_EN_URL = re.compile(r"(/api/public/gestion/)[^/?#]+")


def redactar_url(url: str) -> str:
    """Reemplazar el `manage_token` de una URL pública de gestión."""
    return _TOKEN_EN_URL.sub(r"\1[redactado]", url)


class AppError(Exception):
    def __init__(
        self,
        status_code: int,
        title: str,
        detail: str,
        type_: str = "about:blank",
        instance: str | None = None,
        *,
        code: str | None = None,
        extra: Mapping[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ):
        self.status_code = status_code
        self.title = title
        self.detail = detail
        self.type = type_
        self.instance = instance
        self.code = code
        self.extra = dict(extra) if extra else None
        self.headers = headers
        super().__init__(detail)


class ConflictError(AppError):
    def __init__(
        self,
        detail: str,
        instance: str | None = None,
        *,
        code: str | None = None,
        extra: Mapping[str, Any] | None = None,
    ):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            title="Conflict",
            detail=detail,
            instance=instance,
            code=code,
            extra=extra,
        )


class NotFoundError(AppError):
    def __init__(
        self,
        detail: str,
        instance: str | None = None,
        *,
        code: str | None = None,
        extra: Mapping[str, Any] | None = None,
    ):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Not Found",
            detail=detail,
            instance=instance,
            code=code,
            extra=extra,
        )


class UnauthorizedError(AppError):
    def __init__(
        self,
        detail: str = "Unauthorized",
        instance: str | None = None,
        *,
        code: str | None = None,
        extra: Mapping[str, Any] | None = None,
    ):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Unauthorized",
            detail=detail,
            instance=instance,
            code=code,
            extra=extra,
        )


class ForbiddenError(AppError):
    def __init__(
        self,
        detail: str = "Forbidden",
        instance: str | None = None,
        *,
        code: str | None = None,
        extra: Mapping[str, Any] | None = None,
    ):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            title="Forbidden",
            detail=detail,
            instance=instance,
            code=code,
            extra=extra,
        )


class UnprocessableError(AppError):
    def __init__(
        self,
        detail: str,
        instance: str | None = None,
        *,
        code: str | None = None,
        extra: Mapping[str, Any] | None = None,
    ):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            title="Unprocessable Entity",
            detail=detail,
            instance=instance,
            code=code,
            extra=extra,
        )


class RateLimitError(AppError):
    def __init__(
        self,
        detail: str = "Demasiados intentos, probá de nuevo más tarde",
        *,
        retry_after: int,
        code: str = "rate_limited",
    ):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            title="Too Many Requests",
            detail=detail,
            code=code,
            headers={"Retry-After": str(retry_after)},
        )


def create_problem_response(
    request: Request,
    status_code: int,
    title: str,
    detail: str,
    type_: str = "about:blank",
    *,
    code: str | None = None,
    extra: Mapping[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    content: dict[str, Any] = {
        "type": type_,
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": redactar_url(str(request.url)),
    }
    if code is not None:
        content["codigo"] = code
    if extra:
        content.update(extra)
    return JSONResponse(
        status_code=status_code,
        content=content,
        media_type="application/problem+json",
        headers=headers,
    )


async def app_exception_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.warning(
        "application_exception",
        status_code=exc.status_code,
        title=exc.title,
        detail=exc.detail,
        codigo=exc.code,
        path=redactar_url(str(request.url)),
    )
    return create_problem_response(
        request,
        exc.status_code,
        exc.title,
        exc.detail,
        exc.type,
        code=exc.code,
        extra=exc.extra,
        headers=exc.headers,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    logger.warning(
        "http_exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=redactar_url(str(request.url)),
    )
    return create_problem_response(
        request,
        exc.status_code,
        exc.detail if isinstance(exc.detail, str) else "HTTP Error",
        str(exc.detail) if isinstance(exc.detail, str) else "HTTP Error",
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    logger.warning("validation_exception", errors=exc.errors(), path=redactar_url(str(request.url)))
    details = []
    for error in exc.errors():
        loc = " -> ".join(str(x) for x in error["loc"])
        details.append(f"{loc}: {error['msg']}")
    return create_problem_response(
        request, status.HTTP_422_UNPROCESSABLE_CONTENT, "Validation Error", "; ".join(details)
    )


async def pydantic_validation_exception_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    logger.warning(
        "pydantic_validation_exception", errors=exc.errors(), path=redactar_url(str(request.url))
    )
    details = []
    for error in exc.errors():
        loc = " -> ".join(str(x) for x in error["loc"])
        details.append(f"{loc}: {error['msg']}")
    return create_problem_response(
        request, status.HTTP_422_UNPROCESSABLE_CONTENT, "Validation Error", "; ".join(details)
    )


async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    logger.warning(
        "integrity_error",
        error=str(exc.orig) if exc.orig else str(exc),
        path=redactar_url(str(request.url)),
    )
    return create_problem_response(
        request,
        status.HTTP_409_CONFLICT,
        "Conflict",
        "Resource conflict - possibly duplicate entry",
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", error=str(exc), path=redactar_url(str(request.url)))
    return create_problem_response(
        request,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "Internal Server Error",
        "An unexpected error occurred",
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ValidationError, pydantic_validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(IntegrityError, integrity_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, generic_exception_handler)
