"""Script de seed idempotente para C-02.

Inserta:
- 1 Clínica (timezone AR, wa_sender Twilio, cuenta MP)
- 1 admin, 1 recepción, 1 odontólogo
- 2-3 sillones activos

Idempotente: ejecutar dos veces no duplica datos.
Contraseñas hasheadas con bcrypt (no texto plano).
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.domain.clinica.models import Clinic, Sillon
from app.domain.personas.models import User
from app.infrastructure.db.base import Base


async def seed() -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)

    async with engine.begin() as conn:
        # Asegurar que las tablas existan (idem potencia con Alembic)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        # --- Clinic ---
        result = await session.execute(select(Clinic).limit(1))
        clinic = result.scalar_one_or_none()
        if clinic is None:
            clinic = Clinic(
                id=uuid4(),
                nombre="Clínica Odontológica Central",
                timezone="America/Argentina/Buenos_Aires",
                wa_sender="whatsapp:+5491100000000",
                mp_account="APP_USR-SEED-ACCOUNT",
                is_active=True,
            )
            session.add(clinic)
            await session.flush()

        # --- Users: admin, recepcion, odontólogo ---
        for email, password, rol in [
            ("admin@clinica.com", "Admin1234!", "admin"),
            ("recepcion@clinica.com", "Recepcion1234!", "recepcion"),
            ("odontologo@clinica.com", "Odonto1234!", "odonto"),
        ]:
            result = await session.execute(
                select(User).where(
                    User.clinic_id == clinic.id,  # type: ignore[attr-defined]
                    User.email == email,
                )
            )
            if result.scalar_one_or_none() is None:
                session.add(
                    User(
                        id=uuid4(),
                        clinic_id=clinic.id,
                        email=email,
                        password_hash=hash_password(password),
                        rol=rol,
                        activo=True,
                        is_active=True,
                    )
                )

        await session.flush()

        # --- Sillones: 2-3 activos ---
        for nombre in ["Sillón 1", "Sillón 2", "Sillón 3"]:
            result = await session.execute(
                select(Sillon).where(
                    Sillon.clinic_id == clinic.id,  # type: ignore[attr-defined]
                    Sillon.nombre == nombre,
                )
            )
            if result.scalar_one_or_none() is None:
                session.add(
                    Sillon(
                        id=uuid4(),
                        clinic_id=clinic.id,
                        nombre=nombre,
                        activo=True,
                        is_active=True,
                    )
                )

        await session.commit()
        print("✅ Seed completado: clínica, usuarios y sillones insertados (idempotente).")


if __name__ == "__main__":
    asyncio.run(seed())
