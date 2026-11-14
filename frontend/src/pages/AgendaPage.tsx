import { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '@/features/auth/hooks/useAuth';
import { fetchAgenda, fetchOdontologos, fetchPracticas, fetchSillones } from '@/features/agenda/api';
import { fechaDe } from '@/features/agenda/formato';
import AgendaDia from '@/features/agenda/components/AgendaDia';
import AgendaSemana from '@/features/agenda/components/AgendaSemana';
import AltaTurnoDialog from '@/features/agenda/components/AltaTurnoDialog';
import FiltrosAgenda from '@/features/agenda/components/FiltrosAgenda';
import JornadaPanel from '@/features/panel-dia/components/JornadaPanel';
import type {
  AgendaResponse,
  CambiosFiltros,
  FiltrosAgenda as Filtros,
  Odontologo,
  PracticaInterna,
  Sillon,
  VistaAgenda,
} from '@/features/agenda/types';
import './AgendaPage.css';

const TZ_CLINICA = 'America/Argentina/Buenos_Aires';

/** Fecha de hoy en la zona de la clínica, no en la del navegador. */
function hoyEnClinica(): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: TZ_CLINICA }).format(new Date());
}

/**
 * El odontólogo no ve la agenda multi-sillón ni el alta: su pantalla es su
 * propia jornada, con marcado de llegada/ausencia y sin ABM (C-07 8.6/8.7).
 */
export default function AgendaPage() {
  const { user } = useAuth();

  if (user?.role === 'odonto') {
    return (
      <JornadaPanel
        titulo="Mi agenda"
        subtitulo="Tus turnos de hoy: marcá llegadas y ausencias propias"
      />
    );
  }

  return <AgendaOperativa />;
}

function AgendaOperativa() {
  const { user } = useAuth();
  const puedeCrear = user?.role === 'recepcion' || user?.role === 'admin';

  const [filtros, setFiltros] = useState<Filtros>(() => ({
    vista: 'dia',
    fecha: hoyEnClinica(),
  }));
  const [agenda, setAgenda] = useState<AgendaResponse | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(false);
  const [recarga, setRecarga] = useState(0);

  const [sillones, setSillones] = useState<Sillon[]>([]);
  const [odontologos, setOdontologos] = useState<Odontologo[]>([]);
  const [practicas, setPracticas] = useState<PracticaInterna[]>([]);
  const [altaAbierta, setAltaAbierta] = useState(false);

  const hoy = useMemo(() => hoyEnClinica(), []);

  useEffect(() => {
    let activo = true;

    Promise.all([fetchSillones(), fetchOdontologos(), puedeCrear ? fetchPracticas() : []])
      .then(([listaSillones, listaOdontologos, listaPracticas]) => {
        if (!activo) return;
        setSillones(listaSillones);
        setOdontologos(listaOdontologos);
        setPracticas(listaPracticas);
      })
      .catch(() => {
        // El catálogo es solo para filtros y alta: la agenda sigue siendo usable.
      });

    return () => {
      activo = false;
    };
  }, [puedeCrear]);

  useEffect(() => {
    let activo = true;
    setCargando(true);
    setError(false);

    fetchAgenda(filtros)
      .then((respuesta) => {
        if (!activo) return;
        setAgenda(respuesta);
      })
      .catch(() => {
        if (!activo) return;
        setError(true);
      })
      .finally(() => {
        if (activo) setCargando(false);
      });

    return () => {
      activo = false;
    };
  }, [filtros, recarga]);

  const cambiarFiltros = useCallback((cambios: CambiosFiltros) => {
    setFiltros((previos) => {
      const siguientes: Filtros = {
        vista: cambios.vista ?? previos.vista,
        fecha: cambios.fecha ?? previos.fecha,
      };

      // Un filtro presente con valor vacío/undefined se limpia; ausente se conserva.
      const sillonId = 'sillonId' in cambios ? cambios.sillonId : previos.sillonId;
      if (sillonId) siguientes.sillonId = sillonId;

      const odontologoId = 'odontologoId' in cambios ? cambios.odontologoId : previos.odontologoId;
      if (odontologoId) siguientes.odontologoId = odontologoId;

      const estado = 'estado' in cambios ? cambios.estado : previos.estado;
      if (estado) siguientes.estado = estado;

      return siguientes;
    });
  }, []);

  const cambiarVista = useCallback((vista: VistaAgenda) => {
    setFiltros((previos) => ({ ...previos, vista }));
  }, []);

  const turnos = agenda?.turnos ?? [];
  const hayFiltrosActivos = Boolean(filtros.sillonId || filtros.odontologoId || filtros.estado);

  return (
    <div className="agenda-page">
      <div className="page-header">
        <div>
          <h1>Agenda</h1>
          <p className="page-subtitle">
            Turnos por sillón, con alta interna y control de ausentismo
          </p>
        </div>
        {puedeCrear && (
          <button
            type="button"
            className="agenda-btn agenda-btn--primary"
            onClick={() => setAltaAbierta(true)}
          >
            Nuevo turno
          </button>
        )}
      </div>

      <FiltrosAgenda
        filtros={filtros}
        odontologos={odontologos}
        sillones={sillones}
        mostrarOdontologo
        onCambiar={cambiarFiltros}
        onVista={cambiarVista}
      />

      {hayFiltrosActivos && (
        <div className="agenda-filtros-activos">
          <span>Filtros activos</span>
          <button
            type="button"
            className="agenda-btn agenda-btn--ghost"
            onClick={() => {
              setFiltros({ vista: filtros.vista, fecha: filtros.fecha });
            }}
          >
            Limpiar filtros
          </button>
        </div>
      )}

      {cargando && <p className="agenda-estado">Cargando agenda…</p>}

      {!cargando && error && (
        <div className="agenda-alerta agenda-alerta--danger" role="alert">
          <strong>No se pudo cargar la agenda.</strong>
          <button
            type="button"
            className="agenda-btn"
            onClick={() => setRecarga((valor) => valor + 1)}
          >
            Reintentar
          </button>
        </div>
      )}

      {!cargando && !error && agenda && (
        <>
          {filtros.vista === 'dia' ? (
            <AgendaDia fecha={filtros.fecha} sillones={sillones} turnos={turnos} />
          ) : (
            <AgendaSemana fecha={filtros.fecha} turnos={turnos} hoy={hoy} />
          )}

          <p className="agenda-resumen" aria-live="polite">
            {turnos.length} {turnos.length === 1 ? 'turno' : 'turnos'} en la{' '}
            {filtros.vista === 'dia' ? 'jornada' : 'semana'} · zona {TZ_CLINICA}
          </p>
        </>
      )}

      {altaAbierta && puedeCrear && (
        <AltaTurnoDialog
          fechaInicial={filtros.fecha}
          odontologos={odontologos}
          sillones={sillones}
          practicas={practicas}
          puedeExceptuar={puedeCrear}
          onCerrar={() => setAltaAbierta(false)}
          onCreado={(turno) => {
            setAltaAbierta(false);
            setFiltros((previos) => ({ ...previos, fecha: fechaDe(turno.inicio) }));
            setRecarga((valor) => valor + 1);
          }}
        />
      )}
    </div>
  );
}
