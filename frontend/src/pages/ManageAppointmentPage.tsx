/**
 * Pantalla de gestión por token `/gestionar/:token` (C-06).
 *
 * El enlace de WhatsApp es la única credencial del paciente: la vista nunca
 * manda a `/login` y las acciones que pierden la seña piden confirmación.
 */

import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ConfirmDialog } from '@/components/ConfirmDialog';
import { cancelarTurno, fetchGestion, fetchSlots, reprogramarTurno } from '@/features/booking/api';
import { codigoDeErrorPublico, problemaDeErrorPublico } from '@/features/booking/errores';
import { fechaLocalDe, formatearFecha, formatearHora, formatearMonto } from '@/features/booking/formato';
import type { EstadoTurno, GestionTurno, SlotPublico } from '@/features/booking/types';
import '@/features/booking/booking.css';

const ESTADOS_NO_GESTIONABLES: EstadoTurno[] = ['cancelado', 'completado', 'ausente'];

const ETIQUETA_ESTADO: Record<EstadoTurno, string> = {
  pendiente_sena: 'Pendiente de seña',
  confirmado: 'Confirmado',
  cancelado: 'Cancelado',
  reprogramado: 'Reprogramado',
  completado: 'Completado',
  ausente: 'Ausente',
};

const CLASE_BADGE: Record<EstadoTurno, string> = {
  pendiente_sena: 'bk-badge--pending',
  confirmado: 'bk-badge--success',
  cancelado: 'bk-badge--muted',
  reprogramado: 'bk-badge--muted',
  completado: 'bk-badge--muted',
  ausente: 'bk-badge--muted',
};

type Dialogo =
  | { tipo: 'cancelar'; titulo: string; descripcion: string }
  | { tipo: 'reprogramar'; titulo: string; descripcion: string; nuevoInicio: string };

export default function ManageAppointmentPage() {
  const { token = '' } = useParams();

  const [turno, setTurno] = useState<GestionTurno | null>(null);
  const [cargando, setCargando] = useState(true);
  const [enlaceInvalido, setEnlaceInvalido] = useState(false);
  const [codigoError, setCodigoError] = useState<string | null>(null);
  const [errorGeneral, setErrorGeneral] = useState(false);

  const [procesando, setProcesando] = useState(false);
  const [dialogo, setDialogo] = useState<Dialogo | null>(null);

  const [reprogramando, setReprogramando] = useState(false);
  const [fechaNueva, setFechaNueva] = useState('');
  const [slots, setSlots] = useState<SlotPublico[] | null>(null);
  const [slotElegido, setSlotElegido] = useState('');
  const [cargandoSlots, setCargandoSlots] = useState(false);
  const [errorAccion, setErrorAccion] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    setCargando(true);
    setEnlaceInvalido(false);
    setErrorGeneral(false);
    try {
      setTurno(await fetchGestion(token));
    } catch (error) {
      const problema = problemaDeErrorPublico(error);
      const codigo = problema?.codigo ?? null;
      if (codigo === 'token_invalido' || codigo === 'turno_no_encontrado') {
        setEnlaceInvalido(true);
        setCodigoError(codigo);
      } else {
        setErrorGeneral(true);
      }
    } finally {
      setCargando(false);
    }
  }, [token]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  const cargarSlots = async (practicaId: string, fecha: string) => {
    setCargandoSlots(true);
    try {
      const respuesta = await fetchSlots({ practicaId, fecha });
      setSlots(respuesta.slots);
    } catch {
      setSlots([]);
    } finally {
      setCargandoSlots(false);
    }
  };

  const pedirCancelacion = async () => {
    if (procesando) {
      return;
    }
    setProcesando(true);
    setErrorAccion(null);
    try {
      setTurno(
        await cancelarTurno(token, { manage_token: token, confirmar_perdida_sena: false }),
      );
    } catch (error) {
      if (codigoDeErrorPublico(error) === 'requiere_confirmacion') {
        const problema = problemaDeErrorPublico(error);
        setDialogo({
          tipo: 'cancelar',
          titulo: problema?.detail ?? 'Cancelar dentro de las 12 horas hace perder la seña',
          descripcion: 'Faltan menos de 12 horas para tu turno.',
        });
      } else {
        setErrorAccion('No pudimos cancelar el turno. Intentá de nuevo.');
      }
    } finally {
      setProcesando(false);
    }
  };

  const abrirReprogramacion = () => {
    if (turno === null) {
      return;
    }
    const fecha = fechaLocalDe(turno.inicio);
    setFechaNueva(fecha);
    setSlotElegido('');
    setSlots(null);
    setErrorAccion(null);
    setReprogramando(true);
    void cargarSlots(turno.practica.id, fecha);
  };

  const enviarReprogramacion = async () => {
    if (turno === null || slotElegido === '' || procesando) {
      return;
    }
    setProcesando(true);
    setErrorAccion(null);
    try {
      setTurno(
        await reprogramarTurno(token, {
          manage_token: token,
          nuevo_inicio: slotElegido,
          confirmar_perdida_sena: false,
        }),
      );
      setReprogramando(false);
      setSlotElegido('');
    } catch (error) {
      const codigo = codigoDeErrorPublico(error);
      if (codigo === 'requiere_nueva_sena') {
        const problema = problemaDeErrorPublico(error);
        setDialogo({
          tipo: 'reprogramar',
          titulo: problema?.detail ?? 'La segunda reprogramación exige una seña nueva',
          descripcion:
            'Ya usaste el cambio sin costo. El turno actual se cancela con la seña perdida y se crea uno nuevo pendiente de seña.',
          nuevoInicio: slotElegido,
        });
      } else if (codigo === 'solape') {
        setErrorAccion('Ese horario se acaba de ocupar. Elegí otro de la lista.');
        void cargarSlots(turno.practica.id, fechaNueva);
      } else {
        setErrorAccion('No pudimos reprogramar el turno. Intentá de nuevo.');
      }
    } finally {
      setProcesando(false);
    }
  };

  const confirmarDialogo = async () => {
    if (dialogo === null || turno === null) {
      return;
    }
    setProcesando(true);
    try {
      if (dialogo.tipo === 'cancelar') {
        setTurno(
          await cancelarTurno(token, { manage_token: token, confirmar_perdida_sena: true }),
        );
      } else {
        setTurno(
          await reprogramarTurno(token, {
            manage_token: token,
            nuevo_inicio: dialogo.nuevoInicio,
            confirmar_perdida_sena: true,
          }),
        );
        setReprogramando(false);
        setSlotElegido('');
      }
      setDialogo(null);
    } catch {
      setDialogo(null);
      setErrorAccion('No pudimos completar la gestión. Intentá de nuevo.');
    } finally {
      setProcesando(false);
    }
  };

  if (cargando) {
    return (
      <div className="booking-public">
        <p className="bk-loading" role="status">
          <span className="bk-spinner" aria-hidden="true" />
          Cargando tu turno…
        </p>
      </div>
    );
  }

  if (enlaceInvalido) {
    return (
      <div className="booking-public">
        <h1 className="bk-card-title">No pudimos abrir el turno</h1>
        <div className="bk-alert bk-alert--danger" role="status" aria-live="polite">
          <div>
            <strong>El enlace de gestión no es válido</strong>
            Puede estar incompleto o haber sido reemplazado. Revisá que el mensaje de WhatsApp esté
            completo. <span className="bk-badge bk-badge--muted">{codigoError}</span>
          </div>
        </div>
        <div className="bk-card">
          <div className="bk-card-title">Qué podés hacer</div>
          <ul className="bk-help">
            <li>Abrí el enlace completo desde el WhatsApp de confirmación.</li>
            <li>Si el enlace está cortado, pedí uno nuevo a la clínica.</li>
          </ul>
          <Link className="bk-btn bk-btn--primary bk-btn--block" to="/">
            Reservar un turno nuevo
          </Link>
        </div>
        <p className="bk-help">
          Por seguridad no confirmamos si el turno existe ni mostramos datos parciales.
        </p>
      </div>
    );
  }

  if (errorGeneral || turno === null) {
    return (
      <div className="booking-public">
        <div className="bk-alert bk-alert--danger" role="alert">
          <div>
            <strong>No pudimos cargar tu turno</strong>
            Revisá tu conexión e intentá de nuevo.
          </div>
        </div>
        <button type="button" className="bk-btn bk-btn--primary bk-btn--block" onClick={cargar}>
          Reintentar
        </button>
      </div>
    );
  }

  const gestionable = !ESTADOS_NO_GESTIONABLES.includes(turno.estado);
  const fecha = fechaLocalDe(turno.inicio);
  const usadas = turno.reprogramaciones_count;
  const textoReprogramaciones =
    turno.reprogramaciones_restantes > 0
      ? `${usadas} usadas · queda ${turno.reprogramaciones_restantes} sin seña nueva`
      : `${usadas} usada${usadas === 1 ? '' : 's'} · no quedan`;
  const sufijoSena =
    turno.estado === 'pendiente_sena' ? ' · pendiente de pago' : turno.sena_perdida ? ' · retenida' : ' · pagada';

  return (
    <div className="booking-public">
      <div>
        <h1 className="bk-card-title">Tu turno</h1>
        <p className="bk-meta">
          {formatearFecha(fecha)} · {formatearHora(turno.inicio)} a {formatearHora(turno.fin)}
        </p>
      </div>

      <div className="bk-card">
        <div className="bk-card-head">
          <div>
            <div className="bk-card-title">{turno.practica.nombre}</div>
            <p className="bk-meta">{turno.practica.duracion_min} min</p>
          </div>
          <span className={`bk-badge ${CLASE_BADGE[turno.estado]}`}>
            {ETIQUETA_ESTADO[turno.estado]}
          </span>
        </div>
        <dl className="bk-details">
          <div>
            <dt>Fecha y hora</dt>
            <dd>
              {formatearFecha(fecha)} · {formatearHora(turno.inicio)}
            </dd>
          </div>
          <div>
            <dt>Seña</dt>
            <dd>
              <span>{formatearMonto(turno.monto_sena)}</span>
              {sufijoSena}
            </dd>
          </div>
          <div>
            <dt>Reprogramaciones</dt>
            <dd>{textoReprogramaciones}</dd>
          </div>
        </dl>
      </div>

      {errorAccion !== null && (
        <div className="bk-alert bk-alert--danger" role="alert">
          <div>{errorAccion}</div>
        </div>
      )}

      {gestionable && !reprogramando && (
        <div className="bk-card">
          <div className="bk-card-title">¿Necesitás cambiarlo?</div>
          <p className="bk-help">
            Podés cancelar o reprogramar hasta 12 horas antes del turno sin perder la seña.
          </p>
          <div className="bk-actions">
            <button
              type="button"
              className="bk-btn bk-btn--primary bk-btn--block"
              onClick={abrirReprogramacion}
              disabled={procesando}
            >
              Reprogramar turno
            </button>
            <button
              type="button"
              className="bk-btn bk-btn--danger bk-btn--block"
              onClick={() => void pedirCancelacion()}
              disabled={procesando}
            >
              Cancelar turno
            </button>
          </div>
        </div>
      )}

      {gestionable && reprogramando && (
        <div className="bk-card">
          <div className="bk-card-head">
            <div>
              <div className="bk-card-title">Elegí el horario nuevo</div>
              <p className="bk-meta">
                Tu turno actual: {formatearFecha(fecha)} · {formatearHora(turno.inicio)}
              </p>
            </div>
            <button
              type="button"
              className="bk-btn bk-btn--ghost bk-btn--sm"
              onClick={() => setReprogramando(false)}
            >
              Cancelar
            </button>
          </div>

          <div className="bk-field">
            <label className="bk-label" htmlFor="bk-fecha-nueva">
              Fecha
            </label>
            <input
              className="bk-input"
              id="bk-fecha-nueva"
              type="date"
              value={fechaNueva}
              onChange={(event) => {
                setFechaNueva(event.target.value);
                setSlotElegido('');
                void cargarSlots(turno.practica.id, event.target.value);
              }}
            />
          </div>

          {cargandoSlots && (
            <p className="bk-loading" role="status">
              <span className="bk-spinner" aria-hidden="true" />
              Buscando horarios…
            </p>
          )}

          {!cargandoSlots && slots !== null && slots.length === 0 && (
            <p className="bk-help">No hay horarios libres ese día. Probá con otra fecha.</p>
          )}

          {!cargandoSlots && slots !== null && slots.length > 0 && (
            <div className="bk-slots" role="group" aria-label="Horarios disponibles para reprogramar">
              {slots.map((slot) => (
                <button
                  key={slot.inicio}
                  type="button"
                  className="bk-slot"
                  aria-pressed={slot.inicio === slotElegido}
                  onClick={() => setSlotElegido(slot.inicio)}
                >
                  {formatearHora(slot.inicio)}
                </button>
              ))}
            </div>
          )}

          <button
            type="button"
            className="bk-btn bk-btn--primary bk-btn--block"
            onClick={() => void enviarReprogramacion()}
            disabled={slotElegido === '' || procesando}
          >
            Confirmar cambio
          </button>
        </div>
      )}

      {!gestionable && (
        <div className="bk-alert bk-alert--warning" role="status" aria-live="polite">
          <div>
            <strong>Este turno ya no se puede gestionar</strong>
            Si querés otro horario, reservá uno nuevo.
          </div>
        </div>
      )}

      {gestionable && (
        <p className="bk-help">
          ¿No reconocés este turno? No compartas este enlace: cualquiera que lo tenga puede
          gestionarlo.
        </p>
      )}

      {dialogo !== null && (
        <ConfirmDialog
          titulo={dialogo.titulo}
          descripcion={dialogo.descripcion}
          confirmarLabel={
            dialogo.tipo === 'cancelar' ? 'Cancelar y perder la seña' : 'Aceptar y pagar seña nueva'
          }
          onConfirmar={() => void confirmarDialogo()}
          onCerrar={() => setDialogo(null)}
        >
          <div className="bk-alert bk-alert--warning">
            <div>
              <strong>
                {dialogo.tipo === 'cancelar'
                  ? `Seña en riesgo: ${formatearMonto(turno.monto_sena)}`
                  : `Se pierde la seña actual: ${formatearMonto(turno.monto_sena)}`}
              </strong>
              {dialogo.tipo === 'cancelar'
                ? 'Si cancelás ahora, la seña no se devuelve.'
                : 'El turno nuevo pide una seña nueva, calculada con el arancel vigente.'}
            </div>
          </div>
        </ConfirmDialog>
      )}
    </div>
  );
}
