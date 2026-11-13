"""Tests de la migración 007 (`excepciones_bloqueo`) y su modelo (C-07).

Los tests de esquema son `skipif` Postgres, como 002/004/005/006: la suite local
crea el esquema desde `Base.metadata` sobre SQLite. El test de cadena de
revisiones corre en cualquier motor porque solo importa el módulo de Alembic.
"""

import importlib
from types import ModuleType

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

pg_only = pytest.mark.skipif(
    "sqlite" in settings.database_url,
    reason="Requires PostgreSQL for information_schema/pg_catalog queries",
)

MODULE_NAME = "app.infrastructure.db.migrations.versions.007_excepciones_bloqueo"


def _migracion() -> ModuleType:
    return importlib.import_module(MODULE_NAME)


def test_migracion_declara_revision_007_despues_de_006() -> None:
    """La migración existe, es lineal y no reutiliza la revisión 006."""
    migracion = _migracion()

    assert migracion.revision == "007"
    assert migracion.down_revision == "006"
    assert callable(migracion.upgrade)
    assert callable(migracion.downgrade)


@pg_only
@pytest.mark.asyncio
async def test_tabla_excepciones_bloqueo_existe(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    )
    assert "excepciones_bloqueo" in {row[0] for row in result.fetchall()}


@pg_only
@pytest.mark.asyncio
async def test_columnas_y_nullability(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text(
            "SELECT column_name, is_nullable FROM information_schema.columns "
            "WHERE table_name = 'excepciones_bloqueo'"
        )
    )
    columnas = {row[0]: row[1] for row in result.fetchall()}

    assert columnas["id"] == "NO"
    assert columnas["clinic_id"] == "NO"
    assert columnas["paciente_id"] == "NO"
    assert columnas["turno_id"] == "NO"
    assert columnas["usuario_id"] == "NO"
    assert columnas["motivo"] == "NO"
    assert columnas["created_at"] == "NO"
    assert columnas["is_active"] == "NO"


@pg_only
@pytest.mark.asyncio
async def test_fks_y_unique_de_turno(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conrelid = 'excepciones_bloqueo'::regclass AND contype = 'f'"
        )
    )
    definiciones = [row[0] for row in result.fetchall()]
    assert any("REFERENCES clinic(id)" in d for d in definiciones)
    assert any("REFERENCES pacientes(id)" in d for d in definiciones)
    assert any("REFERENCES turnos(id)" in d for d in definiciones)
    assert any("REFERENCES users(id)" in d for d in definiciones)

    result = await db_session.execute(
        text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conrelid = 'excepciones_bloqueo'::regclass AND contype = 'u'"
        )
    )
    uniques = [row[0] for row in result.fetchall()]
    assert any("turno_id" in u for u in uniques)


@pg_only
@pytest.mark.asyncio
async def test_indices_de_excepciones(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text("SELECT indexname FROM pg_indexes WHERE tablename = 'excepciones_bloqueo'")
    )
    indices = {row[0] for row in result.fetchall()}

    assert "ix_excepciones_bloqueo_clinic_created" in indices
    assert "ix_excepciones_bloqueo_paciente" in indices


@pg_only
@pytest.mark.asyncio
async def test_downgrade_elimina_y_upgrade_recrea(db_session: AsyncSession) -> None:
    """Ejecutar `downgrade()` borra la tabla y `upgrade()` la vuelve a crear."""
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    migracion = _migracion()

    def _bajar_y_subir(sync_conn) -> tuple[bool, bool]:
        migracion.op = Operations(MigrationContext.configure(sync_conn))
        migracion.downgrade()
        tras_downgrade = inspect(sync_conn).has_table("excepciones_bloqueo")
        migracion.upgrade()
        tras_upgrade = inspect(sync_conn).has_table("excepciones_bloqueo")
        return tras_downgrade, tras_upgrade

    tras_downgrade, tras_upgrade = await db_session.run_sync(_bajar_y_subir)

    assert tras_downgrade is False
    assert tras_upgrade is True
