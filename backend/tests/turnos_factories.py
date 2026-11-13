"""Factories compartidas para los tests del motor de turnos (C-05)."""

from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.clinica.models import Arancel, Clinic, Sillon, TipoPractica
from app.domain.personas.models import Paciente, User
from app.domain.turnos.models import HorarioAtencion, Turno

LUNES = date(2026, 1, 5)
SABADO = date(2026, 1, 10)
TZ = "America/Argentina/Buenos_Aires"


def local(fecha: date, hora: time) -> datetime:
    from zoneinfo import ZoneInfo

    return datetime.combine(fecha, hora).replace(tzinfo=ZoneInfo(TZ))


async def crear_clinica(
    db: AsyncSession, *, nombre: str | None = None, timezone: str = TZ
) -> Clinic:
    clinic = Clinic(
        nombre=nombre or f"Clínica {uuid4().hex[:6]}", timezone=timezone, is_active=True
    )
    db.add(clinic)
    await db.flush()
    return clinic


async def crear_practica(
    db: AsyncSession,
    clinic: Clinic,
    *,
    nombre: str = "Limpieza",
    duracion_min: int = 30,
    precio: Decimal = Decimal("10000.00"),
    sena_pct: int = 20,
    activa: bool = True,
    con_arancel: bool = True,
) -> TipoPractica:
    practica = TipoPractica(
        clinic_id=clinic.id,
        nombre=nombre,
        duracion_min=duracion_min,
        precio_base=precio,
        sena_pct=sena_pct,
        activa=activa,
        is_active=True,
    )
    db.add(practica)
    await db.flush()
    if con_arancel:
        db.add(
            Arancel(
                tipo_practica_id=practica.id,
                precio=precio,
                sena_pct=sena_pct,
                vigente_desde=date(2020, 1, 1),
                is_active=True,
            )
        )
        await db.flush()
    return practica


async def crear_sillon(db: AsyncSession, clinic: Clinic, nombre: str = "Sillón 1") -> Sillon:
    sillon = Sillon(clinic_id=clinic.id, nombre=nombre, activo=True, is_active=True)
    db.add(sillon)
    await db.flush()
    return sillon


async def crear_odontologo(db: AsyncSession, clinic: Clinic) -> User:
    odonto = User(
        clinic_id=clinic.id,
        email=f"odonto-{uuid4().hex[:8]}@clinica.com",
        password_hash="x",
        rol="odonto",
        activo=True,
        is_active=True,
    )
    db.add(odonto)
    await db.flush()
    return odonto


async def crear_paciente(
    db: AsyncSession,
    clinic: Clinic,
    *,
    telefono: str | None = None,
    nombre: str = "Ana Paciente",
    dni: str | None = None,
    bloqueado_hasta: datetime | None = None,
    faltas_count: int = 0,
) -> Paciente:
    paciente = Paciente(
        clinic_id=clinic.id,
        nombre=nombre,
        telefono=telefono or f"+54911{uuid4().hex[:8]}",
        dni=dni,
        bloqueado_hasta=bloqueado_hasta,
        faltas_count=faltas_count,
        is_active=True,
    )
    db.add(paciente)
    await db.flush()
    return paciente


async def crear_horarios_lv(db: AsyncSession, clinic: Clinic) -> list[HorarioAtencion]:
    horarios = []
    for dia in range(5):
        horario = HorarioAtencion(
            clinic_id=clinic.id,
            dia_semana=dia,
            hora_desde=time(8, 0),
            hora_hasta=time(20, 0),
            activo=True,
            is_active=True,
        )
        db.add(horario)
        horarios.append(horario)
    await db.flush()
    return horarios


async def crear_horario(
    db: AsyncSession,
    clinic: Clinic,
    *,
    dia_semana: int,
    desde: time,
    hasta: time,
) -> HorarioAtencion:
    horario = HorarioAtencion(
        clinic_id=clinic.id,
        dia_semana=dia_semana,
        hora_desde=desde,
        hora_hasta=hasta,
        activo=True,
        is_active=True,
    )
    db.add(horario)
    await db.flush()
    return horario


async def crear_turno(
    db: AsyncSession,
    *,
    clinic: Clinic,
    paciente: Paciente,
    sillon: Sillon,
    odontologo: User,
    practica: TipoPractica,
    inicio: datetime,
    duracion_min: int | None = None,
    estado: str = "confirmado",
    manage_token: str | None = None,
    expira_at: datetime | None = None,
    monto_sena: Decimal = Decimal("0.00"),
    reprogramaciones_count: int = 0,
    sena_perdida: bool = False,
) -> Turno:
    fin = inicio + timedelta(minutes=duracion_min or practica.duracion_min)
    turno = Turno(
        clinic_id=clinic.id,
        paciente_id=paciente.id,
        sillon_id=sillon.id,
        odontologo_id=odontologo.id,
        tipo_practica_id=practica.id,
        inicio=inicio.astimezone(UTC),
        fin=fin.astimezone(UTC),
        estado=estado,
        manage_token=manage_token,
        monto_sena=monto_sena,
        expira_at=expira_at,
        reprogramaciones_count=reprogramaciones_count,
        sena_perdida=sena_perdida,
        is_active=True,
    )
    db.add(turno)
    await db.flush()
    return turno


def utc(fecha: date, hora: time) -> datetime:
    return local(fecha, hora).astimezone(UTC)
