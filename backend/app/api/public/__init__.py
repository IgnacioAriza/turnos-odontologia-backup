"""Routers públicos. Sin autenticación: nunca deben responder 401."""

from fastapi import APIRouter

from app.api.public.reservas import router as reservas_router

router = APIRouter()
router.include_router(reservas_router)

__all__ = ["router"]
