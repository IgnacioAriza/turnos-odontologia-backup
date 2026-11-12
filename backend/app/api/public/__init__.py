"""Routers públicos. Sin autenticación: nunca deben responder 401."""

from fastapi import APIRouter

from app.api.public.gestion import router as gestion_router
from app.api.public.practicas import router as practicas_router
from app.api.public.reservas import router as reservas_router

router = APIRouter()
router.include_router(practicas_router)
router.include_router(reservas_router)
router.include_router(gestion_router)

__all__ = ["router"]
