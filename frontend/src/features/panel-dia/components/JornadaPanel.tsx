import { useEffect, useMemo, useState } from 'react';
import { fetchPanelDia } from '../api';
import MarcarEstadoDialog from './MarcarEstadoDialog';
import PanelLista from './PanelLista';
import type { EstadoMarcable, PanelDia, PanelTurno } from '../types';
import '../panel.css';

const TZ_CLINICA = 'America/Argentina/Buenos_Aires';

/** Fecha de hoy en la zona de la clínica, no en la del navegador. */
function hoyEnClinica(): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: TZ_CLINICA }).format(new Date());
}

interface JornadaPanelProps {
  titulo: string;
  subtitulo: string;
}

/**
 * Jornada operable compartida por recepción/admin (`/panel`) y por el
 * odontólogo (`/agenda`): lista por hora, marcado de llegada/ausencia y
 * contacto por WhatsApp. El confinamiento del odontólogo es server-side.
 */
export default function JornadaPanel({ titulo, subtitulo }: JornadaPanelProps) {
  const [fecha, setFecha] = useState(hoyEnClinica);
  const [panel, setPanel] = useState<PanelDia | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(false);
  const [recarga, setRecarga] = useState(0);
  const [marcado, setMarcado] = useState<{ turno: PanelTurno; destino: EstadoMarcable } | null>(
    null,
  );

  useEffect(() => {
    let activo = true;
    setCargando(true);
    setError(false);

    fetchPanelDia(fecha)
      .then((respuesta) => {
        if (!activo) return;
        setPanel(respuesta);
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
  }, [fecha, recarga]);

  const resumen = useMemo(
    () =>
      panel?.resumen ?? {
        total: 0,
        pendientes_sena: 0,
        confirmados: 0,
        completados: 0,
        ausentes: 0,
      },
    [panel],
  );

  return (
    <div className="panel-page">
      <div className="page-header">
        <div>
          <h1>{titulo}</h1>
          <p className="page-subtitle">{subtitulo}</p>
        </div>

        <div className="agenda-campo">
          <label htmlFor="panel-fecha">Fecha</label>
          <input
            id="panel-fecha"
            className="agenda-input"
            type="date"
            value={fecha}
            onChange={(event) => setFecha(event.target.value)}
          />
        </div>
      </div>

      {cargando && <p className="panel-estado">Cargando jornada…</p>}

      {!cargando && error && (
        <div className="panel-alerta panel-alerta--danger" role="alert">
          <strong>No se pudo cargar el panel.</strong>
          <button
            type="button"
            className="panel-btn"
            onClick={() => setRecarga((valor) => valor + 1)}
          >
            Reintentar
          </button>
        </div>
      )}

      {!cargando && !error && panel && (
        <PanelLista
          turnos={panel.turnos}
          resumen={resumen}
          onMarcar={(turno, destino) => setMarcado({ turno, destino })}
        />
      )}

      {marcado && (
        <MarcarEstadoDialog
          turno={marcado.turno}
          destino={marcado.destino}
          onCerrar={() => setMarcado(null)}
          onRefrescar={() => {
            setMarcado(null);
            setRecarga((valor) => valor + 1);
          }}
          onMarcado={() => {
            setMarcado(null);
            setRecarga((valor) => valor + 1);
          }}
        />
      )}
    </div>
  );
}
