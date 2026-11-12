"""Router público de gestión de turnos por `manage_token` (C-06).

Sin JWT y sin aceptar el token por query string (design D2/D5). Un token
inválido responde 403 y nunca 401: el canal público no debe disparar el
interceptor de sesión del panel.
"""

import hashlib
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, RateLimitError
from app.core.logging import get_logger
from app.core.rate_limit import check_rate_limit
from app.domain.turnos import service
from app.domain.turnos.gestion import CODIGO_TOKEN_INVALIDO
from app.domain.turnos.schemas import (
    CancelarGestionIn,
    GestionTurnoOut,
    PracticaResumenOut,
    ReprogramarGestionIn,
)
from app.infrastructure.db.session import get_session

router = APIRouter(tags=["public"])
logger = get_logger(__name__)

LIMITE_GESTION_IP = 30
LIMITE_GESTION_TOKEN = 10
VENTANA_GESTION_RATE = 60

HEADERS_PRIVADOS = {
    "Cache-Control": "no-store",
    "Referrer-Policy": "no-referrer",
}


def _ip(request: Request) -> str:
    return request.client.host if request.client else "desconocida"


def _fingerprint(token: str) -> str:
    """Hash estable del token: se limita por token sin guardar el token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _verificar_limites(request: Request, token: str) -> None:
    """Aplicar los límites por IP y por token del canal público (D8)."""
    allowed, retry_after = check_rate_limit(
        "gestion_ip",
        _ip(request),
        limit=LIMITE_GESTION_IP,
        window=VENTANA_GESTION_RATE,
    )
    if not allowed:
        raise RateLimitError(retry_after=retry_after)

    allowed, retry_after = check_rate_limit(
        "gestion_token",
        _fingerprint(token),
        limit=LIMITE_GESTION_TOKEN,
        window=VENTANA_GESTION_RATE,
    )
    if not allowed:
        raise RateLimitError(retry_after=retry_after)


def _verificar_token_del_cuerpo(token: str, manage_token: str) -> None:
    if not secrets.compare_digest(token, manage_token):
        raise ForbiddenError("El enlace de gestión no es válido", code=CODIGO_TOKEN_INVALIDO)


def _vista(gestion: service.GestionPublica) -> GestionTurnoOut:
    turno = gestion.turno
    return GestionTurnoOut(
        turno_id=turno.id,
        estado=turno.estado,
        inicio=turno.inicio,
        fin=turno.fin,
        practica=PracticaResumenOut(
            id=gestion.practica.id,
            nombre=gestion.practica.nombre,
            duracion_min=gestion.practica.duracion_min,
        ),
        monto_sena=turno.monto_sena,
        sena_perdida=turno.sena_perdida,
        reprogramaciones_count=turno.reprogramaciones_count,
        reprogramaciones_restantes=gestion.reprogramaciones_restantes,
        dentro_de_ventana=gestion.dentro_de_ventana,
    )


async def _resolver(session: AsyncSession, token: str) -> service.GestionPublica:
    """Resolver y registrar sin exponer el token en el log (D5)."""
    gestion = await service.resolver_gestion_publica(session, token=token)
    logger.info(
        "gestion_publica",
        turno_id=str(gestion.turno.id),
        clinic_id=str(gestion.turno.clinic_id),
        accion="ver",
    )
    return gestion


@router.get("/gestion/{token}", response_model=GestionTurnoOut)
async def ver_gestion(
    token: str,
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> GestionTurnoOut:
    """Devolver la vista pública del turno sin datos de otros pacientes."""
    _verificar_limites(request, token)
    gestion = await _resolver(session, token)
    response.headers.update(HEADERS_PRIVADOS)
    return _vista(gestion)


@router.post("/gestion/{token}/cancelar", response_model=GestionTurnoOut)
async def cancelar_gestion(
    token: str,
    payload: CancelarGestionIn,
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> GestionTurnoOut:
    """Cancelar el turno por token; dentro de 12hs exige confirmación."""
    _verificar_limites(request, token)
    _verificar_token_del_cuerpo(token, payload.manage_token)
    gestion = await _resolver(session, token)

    turno = await service.cancelar_turno(
        session,
        turno=gestion.turno,
        clinic=gestion.clinic,
        confirmar_perdida_sena=payload.confirmar_perdida_sena,
    )
    logger.info(
        "gestion_publica",
        turno_id=str(turno.id),
        clinic_id=str(turno.clinic_id),
        accion="cancelar",
    )

    actualizada = await service.resolver_gestion_publica(session, token=turno.manage_token or token)
    response.headers.update(HEADERS_PRIVADOS)
    return _vista(actualizada)


@router.post("/gestion/{token}/reprogramar", response_model=GestionTurnoOut)
async def reprogramar_gestion(
    token: str,
    payload: ReprogramarGestionIn,
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> GestionTurnoOut:
    """Mover el turno a otro slot; la segunda vez exige una seña nueva."""
    _verificar_limites(request, token)
    _verificar_token_del_cuerpo(token, payload.manage_token)
    gestion = await _resolver(session, token)

    turno = await service.reprogramar_turno(
        session,
        turno=gestion.turno,
        clinic=gestion.clinic,
        nuevo_inicio=payload.nuevo_inicio,
        confirmar_perdida_sena=payload.confirmar_perdida_sena,
    )
    logger.info(
        "gestion_publica",
        turno_id=str(turno.id),
        clinic_id=str(turno.clinic_id),
        accion="reprogramar",
    )

    actualizada = await service.resolver_gestion_publica(session, token=turno.manage_token or token)
    response.headers.update(HEADERS_PRIVADOS)
    return _vista(actualizada)


__all__ = ["router"]
