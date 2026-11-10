"""Database session module.

Re-exports the async session factory from base for use in auth and other domains.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.base import async_session_factory

# Export as async_session for convenient use with `async with async_session() as session:`
async_session = async_session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependencia FastAPI: una sesión por request, cerrada al finalizar."""
    async with async_session() as session:
        yield session


__all__ = ["async_session", "get_session"]
