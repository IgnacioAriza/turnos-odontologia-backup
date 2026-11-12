"""Tests de la función pura `generar_slots` (C-05)."""

from datetime import UTC, date, datetime, time, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.domain.turnos.slots import generar_slots

TZ = "America/Argentina/Buenos_Aires"
LUNES = date(2026, 1, 5)  # lunes
SABADO = date(2026, 1, 10)  # sábado


def _local(fecha: date, hora: time) -> datetime:
    from zoneinfo import ZoneInfo

    return datetime.combine(fecha, hora).replace(tzinfo=ZoneInfo(TZ))


def _horario(fecha: date, desde: time, hasta: time) -> SimpleNamespace:
    return SimpleNamespace(
        dia_semana=fecha.weekday(),
        hora_desde=desde,
        hora_hasta=hasta,
        activo=True,
    )


def _sillon(nombre: str = "S1") -> SimpleNamespace:
    return SimpleNamespace(id=uuid4(), nombre=nombre, activo=True)


def _odonto(nombre: str = "odonto") -> SimpleNamespace:
    return SimpleNamespace(id=uuid4(), email=f"{nombre}@x.com", activo=True)


def _turno(
    inicio: datetime,
    fin: datetime,
    sillon_id,
    odontologo_id,
    estado: str = "confirmado",
) -> SimpleNamespace:
    return SimpleNamespace(
        inicio=inicio,
        fin=fin,
        sillon_id=sillon_id,
        odontologo_id=odontologo_id,
        estado=estado,
    )


def test_sin_horario_para_el_dia_no_devuelve_slots() -> None:
    horario = _horario(LUNES + timedelta(days=1), time(8, 0), time(12, 0))

    slots = generar_slots(
        fecha=LUNES,
        duracion_min=30,
        horarios=[horario],
        turnos_vigentes=[],
        sillones=[_sillon()],
        odontologos=[_odonto()],
        tz=TZ,
    )

    assert slots == []


def test_slots_alineados_y_ultimo_slot_no_termina_en_el_cierre() -> None:
    slots = generar_slots(
        fecha=LUNES,
        duracion_min=30,
        horarios=[_horario(LUNES, time(8, 0), time(10, 0))],
        turnos_vigentes=[],
        sillones=[_sillon()],
        odontologos=[_odonto()],
        tz=TZ,
    )

    inicio_local = [slot.inicio.astimezone(_local(LUNES, time(0, 0)).tzinfo) for slot in slots]
    assert [dt.strftime("%H:%M") for dt in inicio_local] == ["08:00", "08:30", "09:00", "09:30"]
    assert all(slot.fin > slot.inicio for slot in slots)


def test_sabado_termina_a_mas_tardar_13() -> None:
    slots = generar_slots(
        fecha=SABADO,
        duracion_min=60,
        horarios=[_horario(SABADO, time(8, 0), time(13, 0))],
        turnos_vigentes=[],
        sillones=[_sillon()],
        odontologos=[_odonto()],
        tz=TZ,
    )

    fin_local = slots[-1].fin.astimezone(_local(SABADO, time(0, 0)).tzinfo)
    assert fin_local.time() <= time(13, 0)


def test_varias_franjas_por_dia() -> None:
    slots = generar_slots(
        fecha=LUNES,
        duracion_min=60,
        horarios=[
            _horario(LUNES, time(8, 0), time(10, 0)),
            _horario(LUNES, time(16, 0), time(18, 0)),
        ],
        turnos_vigentes=[],
        sillones=[_sillon()],
        odontologos=[_odonto()],
        tz=TZ,
    )

    horas = [
        slot.inicio.astimezone(_local(LUNES, time(0, 0)).tzinfo).strftime("%H:%M") for slot in slots
    ]
    assert horas == ["08:00", "09:00", "16:00", "17:00"]


def test_slot_ocupado_por_sillon_se_excluye() -> None:
    sillon = _sillon()
    odonto = _odonto()
    turno = _turno(_local(LUNES, time(9, 0)), _local(LUNES, time(9, 30)), sillon.id, odonto.id)

    slots = generar_slots(
        fecha=LUNES,
        duracion_min=30,
        horarios=[_horario(LUNES, time(8, 0), time(10, 0))],
        turnos_vigentes=[turno],
        sillones=[sillon],
        odontologos=[odonto],
        tz=TZ,
    )

    horas = [
        slot.inicio.astimezone(_local(LUNES, time(0, 0)).tzinfo).strftime("%H:%M") for slot in slots
    ]
    assert horas == ["08:00", "08:30", "09:30"]


def test_busca_el_primer_par_libre() -> None:
    sillon1 = _sillon("S1")
    sillon2 = _sillon("S2")
    odonto1 = _odonto("odonto1")
    odonto2 = _odonto("odonto2")
    turno = _turno(_local(LUNES, time(10, 0)), _local(LUNES, time(10, 30)), sillon1.id, odonto1.id)

    slots = generar_slots(
        fecha=LUNES,
        duracion_min=30,
        horarios=[_horario(LUNES, time(10, 0), time(10, 30))],
        turnos_vigentes=[turno],
        sillones=[sillon1, sillon2],
        odontologos=[odonto1, odonto2],
        tz=TZ,
    )

    assert len(slots) == 1
    assert slots[0].sillon_id == sillon2.id
    assert slots[0].odontologo_id == odonto2.id


def test_odontologo_ocupado_no_ofrece_slot() -> None:
    sillon = _sillon()
    odonto = _odonto()
    turno = _turno(_local(LUNES, time(9, 0)), _local(LUNES, time(10, 0)), uuid4(), odonto.id)

    slots = generar_slots(
        fecha=LUNES,
        duracion_min=30,
        horarios=[_horario(LUNES, time(9, 0), time(10, 0))],
        turnos_vigentes=[turno],
        sillones=[sillon],
        odontologos=[odonto],
        tz=TZ,
    )

    assert slots == []


def test_sin_sillones_activos_no_hay_slots() -> None:
    sillon = _sillon()
    sillon.activo = False

    slots = generar_slots(
        fecha=LUNES,
        duracion_min=30,
        horarios=[_horario(LUNES, time(8, 0), time(10, 0))],
        turnos_vigentes=[],
        sillones=[sillon],
        odontologos=[_odonto()],
        tz=TZ,
    )

    assert slots == []


def test_devuelve_utc_respetando_timezone_clinica() -> None:
    slots = generar_slots(
        fecha=LUNES,
        duracion_min=60,
        horarios=[_horario(LUNES, time(8, 0), time(10, 0))],
        turnos_vigentes=[],
        sillones=[_sillon()],
        odontologos=[_odonto()],
        tz=TZ,
    )

    assert slots[0].inicio.tzinfo is not None
    assert slots[0].inicio == datetime(2026, 1, 5, 11, 0, tzinfo=UTC)
    assert slots[0].fin - slots[0].inicio == timedelta(minutes=60)


def test_turno_cancelado_no_bloquea() -> None:
    sillon = _sillon()
    odonto = _odonto()
    cancelado = _turno(
        _local(LUNES, time(9, 0)),
        _local(LUNES, time(9, 30)),
        sillon.id,
        odonto.id,
        estado="cancelado",
    )

    slots = generar_slots(
        fecha=LUNES,
        duracion_min=30,
        horarios=[_horario(LUNES, time(9, 0), time(10, 0))],
        turnos_vigentes=[cancelado],
        sillones=[sillon],
        odontologos=[odonto],
        tz=TZ,
    )

    assert len(slots) == 2


def test_duracion_invalida_es_error() -> None:
    with pytest.raises(ValueError):
        generar_slots(
            fecha=LUNES,
            duracion_min=0,
            horarios=[],
            turnos_vigentes=[],
            sillones=[],
            odontologos=[],
            tz=TZ,
        )


def _alineado(inicio: datetime, duracion_min: int = 30) -> bool:
    from app.domain.turnos.slots import esta_alineado

    return esta_alineado(
        inicio=inicio,
        fecha=LUNES,
        duracion_min=duracion_min,
        horarios=[_horario(LUNES, time(8, 0), time(10, 0))],
        tz=TZ,
    )


def test_alineado_en_la_grilla() -> None:
    assert _alineado(_local(LUNES, time(8, 0))) is True
    assert _alineado(_local(LUNES, time(9, 30))) is True


def test_no_alineado_entre_slots() -> None:
    assert _alineado(_local(LUNES, time(8, 15))) is False


def test_no_alineado_fuera_de_franja() -> None:
    assert _alineado(_local(LUNES, time(10, 0))) is False
    assert _alineado(_local(LUNES, time(7, 30))) is False


def test_no_alineado_otro_dia() -> None:
    from app.domain.turnos.slots import esta_alineado

    assert (
        esta_alineado(
            inicio=_local(SABADO, time(8, 0)),
            fecha=SABADO,
            duracion_min=30,
            horarios=[_horario(LUNES, time(8, 0), time(10, 0))],
            tz=TZ,
        )
        is False
    )


def test_alineado_duracion_invalida_es_error() -> None:
    from app.domain.turnos.slots import esta_alineado

    with pytest.raises(ValueError):
        esta_alineado(
            inicio=_local(LUNES, time(8, 0)),
            fecha=LUNES,
            duracion_min=0,
            horarios=[],
            tz=TZ,
        )
