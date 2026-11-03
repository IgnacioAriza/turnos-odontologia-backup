"""Database session module.

Re-exports the async session factory from base for use in auth and other domains.
"""

from app.infrastructure.db.base import async_session_factory

# Export as async_session for convenient use with `async with async_session() as session:`
async_session = async_session_factory

__all__ = ["async_session"]
