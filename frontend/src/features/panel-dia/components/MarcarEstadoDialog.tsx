import { useState } from 'react';
import { problemaDeError } from '@/shared/api-client/problema';
import { marcarTurno } from '../api';
import { horaDe } from '@/features/agenda/formato';
import type { EstadoMarcable, PanelTurno } from '../types';

interface MarcarEstadoDialogProps {
  turno: PanelTurno;
  destino: EstadoMarcable;
  onMarcado: (turno: PanelTurno) => void;
  onCerrar: () => void;
  onRefrescar: () => void;
}

const ETIQUETA: Record<EstadoMarcable, string> = {
  completado: 'Marcar llegada',
  ausente: 'Confirmar ausencia',
};

/**
 * Confirmación del marcado del panel (C-07 D5/D6).
 *
 * La falta la marca una persona y el backend es idempotente por destino. Si el
 * turno ya cambió de estado (409) o desapareció (404), la jornada se refresca
 * en lugar de mostrar un dato viejo.
 */
export default function MarcarEstadoDialog({
  turno,
  destino,
  onMarcado,
  onCerrar,
  onRefrescar,
}: MarcarEstadoDialogProps) {
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const yaMarcado = turno.estado === destino;
  const segundaFalta = destino === 'ausente' && turno.paciente.faltas_count >= 1;

  async function confirmar() {
    setEnviando(true);
    setError(null);
    try {
      onMarcado(await marcarTurno(turno.id, destino));
    } catch (fallo) {
      const problema = problemaDeError(fallo);
      if (problema?.codigo === 'estado_no_actualizable') {
        setError('El turno cambió de estado. Actualizamos la jornada.');
        onRefrescar();
      } else if (problema?.codigo === 'turno_no_encontrado') {
        setError('El turno ya no está en la jornada. Actualizamos la lista.');
        onRefrescar();
      } else {
        setError('No se pudo registrar el marcado. Intentá de nuevo.');
      }
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="panel-dialog-fondo">
      <div
        className="panel-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="marcar-titulo"
      >
        <h3 id="marcar-titulo">{ETIQUETA[destino]}</h3>

        <p>
          <strong>{turno.paciente.nombre}</strong> · {horaDe(turno.inicio)} ·{' '}
          {turno.practica.nombre}
        </p>

        {error && (
          <div className="panel-alerta panel-alerta--danger" role="alert">
            {error}
          </div>
        )}

        {yaMarcado && (
          <p className="panel-ayuda">
            Ya está marcado como {destino === 'ausente' ? 'ausente' : 'atendido'}: no se suma otra
            falta.
          </p>
        )}

        {!yaMarcado && segundaFalta && (
          <div className="panel-alerta panel-alerta--warning" role="note">
            Esta es la segunda falta: el paciente queda bloqueado 30 días.
          </div>
        )}

        <div className="panel-dialog__acciones">
          <button type="button" className="panel-btn" onClick={onCerrar}>
            {yaMarcado ? 'Cerrar' : 'Volver'}
          </button>
          {!yaMarcado && (
            <button
              type="button"
              className={`panel-btn ${destino === 'ausente' ? 'panel-btn--danger' : 'panel-btn--ok'}`}
              onClick={() => void confirmar()}
              disabled={enviando}
            >
              {enviando ? 'Guardando…' : ETIQUETA[destino]}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
