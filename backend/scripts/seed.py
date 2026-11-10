"""Script de seed idempotente para C-02 y C-04.

Inserta:
- 1 Clínica (timezone AR, wa_sender Twilio, cuenta MP)
- 1 admin, 1 recepción, 1 odontólogo
- 2-3 sillones activos
- 5 prácticas base con su arancel 1:1 (C-04)

Los porcentajes de seña del seed son PROVISORIOS hasta que el Admin de la
clínica responda la pregunta de prioridad Alta de
`knowledge-base/10_preguntas_abiertas.md` (seed de % seña en v1.0 sin ABM).
Cambiarlos no requiere migración: se ajustan en `PRACTICAS_SEED`.

Idempotente: ejecutar dos veces no duplica datos.
Contraseñas hasheadas con bcrypt (no texto plano).
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.domain.clinica.models import Arancel, Clinic, Sillon, TipoPractica
from app.domain.personas.models import User
from app.infrastructure.db.base import Base

PRACTICAS_SEED: list[dict[str, object]] = [
    {"nombre": "Limpieza", "duracion_min": 30, "precio_base": Decimal("15000.00"), "sena_pct": 30},
    {"nombre": "Arreglo", "duracion_min": 45, "precio_base": Decimal("25000.00"), "sena_pct": 40},
    {
        "nombre": "Endodoncia",
        "duracion_min": 60,
        "precio_base": Decimal("45000.00"),
        "sena_pct": 30,
    },
    {
        "nombre": "Extracción",
        "duracion_min": 30,
        "precio_base": Decimal("20000.00"),
        "sena_pct": 30,
    },
    {
        "nombre": "Ortodoncia control",
        "duracion_min": 20,
        "precio_base": Decimal("12000.00"),
        "sena_pct": 20,
    },
]


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
                    User.clinic_id == clinic.id,
                    User.email == email,  # type: ignore[attr-defined]
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
                        id=uuid4(), clinic_id=clinic.id, nombre=nombre, activo=True, is_active=True
                    )
                )

        await session.flush()

        # --- Prácticas y aranceles (C-04) ---
        for practica_data in PRACTICAS_SEED:
            nombre = str(practica_data["nombre"])
            result = await session.execute(
                select(TipoPractica).where(
                    TipoPractica.clinic_id == clinic.id,  # type: ignore[attr-defined]
                    TipoPractica.nombre == nombre,
                )
            )
            practica = result.scalar_one_or_none()
            if practica is None:
                practica = TipoPractica(
                    id=uuid4(),
                    clinic_id=clinic.id,
                    nombre=nombre,
                    duracion_min=int(practica_data["duracion_min"]),  # type: ignore[arg-type]
                    precio_base=practica_data["precio_base"],  # type: ignore[arg-type]
                    sena_pct=int(practica_data["sena_pct"]),  # type: ignore[arg-type]
                    activa=True,
                    is_active=True,
                )
                session.add(practica)
                await session.flush()

            result = await session.execute(
                select(Arancel).where(Arancel.tipo_practica_id == practica.id)
            )
            if result.scalar_one_or_none() is None:
                session.add(
                    Arancel(
                        id=uuid4(),
                        tipo_practica_id=practica.id,
                        precio=practica.precio_base,
                        sena_pct=practica.sena_pct,
                        vigente_desde=date.today(),
                        is_active=True,
                    )
                )

        await session.commit()
        print(
            "✅ Seed completado: clínica, usuarios, sillones, "
            "prácticas y aranceles insertados (idempotente)."
        )


if __name__ == "__main__":
    asyncio.run(seed())
