/**
 * Formulario de reserva `/reservar` (C-06): datos del paciente, seña y entrega
 * al checkout.
 *
 * El horario elegido llega por `location.state` desde la landing. El teléfono se
 * normaliza a E.164 antes de enviar y, ante un 409 por solape, se refrescan los
 * horarios conservando los datos cargados.
 */

import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { crearReserva, fetchSlots } from '@/features/booking/api';
import { redirigirACheckout, urlDeCheckout } from '@/features/booking/checkout';
import { codigoDeErrorPublico } from '@/features/booking/errores';
import { formatearFecha, formatearHora, formatearMonto } from '@/features/booking/formato';
import { normalizarTelefonoAR } from '@/features/booking/normalizarTelefono';
import type { ReservaPublica, SlotPublico } from '@/features/booking/types';
import '@/features/booking/booking.css';

interface EstadoReserva {
  practicaId: string;
  practicaNombre: string;
  duracionMin: number;
  senaPct: number;
  fecha: string;
  inicio: string;
}

function esEstadoReserva(valor: unknown): valor is EstadoReserva {
  if (typeof valor !== 'object' || valor === null) {
    return false;
  }
  const estado = valor as Partial<EstadoReserva>;
  return (
    typeof estado.practicaId === 'string' &&
    estado.practicaId !== '' &&
    typeof estado.practicaNombre === 'string' &&
    typeof estado.duracionMin === 'number' &&
    typeof estado.senaPct === 'number' &&
    typeof estado.fecha === 'string' &&
    typeof estado.inicio === 'string' &&
    estado.inicio !== ''
  );
}

export default function BookingPage() {
  const location = useLocation();
  const estado = esEstadoReserva(location.state) ? location.state : null;

  const [nombre, setNombre] = useState('');
  const [telefono, setTelefono] = useState('');
  const [inicio, setInicio] = useState(estado?.inicio ?? '');
  const [enviando, setEnviando] = useState(false);
  const [errorGeneral, setErrorGeneral] = useState(false);
  const [conflicto, setConflicto] = useState(false);
  const [slotsRefrescados, setSlotsRefrescados] = useState<SlotPublico[]>([]);
  const [reserva, setReserva] = useState<ReservaPublica | null>(null);

  if (estado === null) {
    return (
      <div className="booking-public">
        <div className="bk-empty">
          <h1>Elegí un horario primero</h1>
          <p>Para reservar necesitás elegir una práctica y un horario disponible.</p>
          <Link className="bk-btn bk-btn--primary" to="/">
            Elegir horario
          </Link>
        </div>
      </div>
    );
  }

  if (reserva !== null) {
    return <ReservaConfirmada reserva={reserva} estado={estado} />;
  }

  const telefonoNormalizado = normalizarTelefonoAR(telefono);
  const telefonoInvalido = telefono.trim() !== '' && telefonoNormalizado === null;
  const puedeEnviar = nombre.trim() !== '' && telefonoNormalizado !== null && !enviando;

  const confirmar = async () => {
    if (!puedeEnviar || telefonoNormalizado === null) {
      return;
    }
    setEnviando(true);
    setErrorGeneral(false);
    setConflicto(false);
    try {
      const creada = await crearReserva({
        nombre: nombre.trim(),
        telefono: telefonoNormalizado,
        practica_id: estado.practicaId,
        inicio,
      });
      const checkout = urlDeCheckout(creada);
      if (checkout !== null) {
        redirigirACheckout(checkout);
        return;
      }
      setReserva(creada);
    } catch (error) {
      if (codigoDeErrorPublico(error) === 'solape') {
        setConflicto(true);
        setInicio('');
        try {
          const refresco = await fetchSlots({ practicaId: estado.practicaId, fecha: estado.fecha });
          setSlotsRefrescados(refresco.slots);
        } catch {
          setSlotsRefrescados([]);
        }
      } else {
        setErrorGeneral(true);
      }
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="booking-public">
      <h1 className="bk-card-title">Confirmá tus datos</h1>

      <ol className="bk-stepper" aria-label="Pasos de la reserva">
        <li className="bk-step bk-step--done">
          <span className="bk-step-num" aria-hidden="true">
            ✓
          </span>
          Práctica<span className="bk-sr-only"> (completado)</span>
        </li>
        <li className="bk-step bk-step--done">
          <span className="bk-step-num" aria-hidden="true">
            ✓
          </span>
          Horario<span className="bk-sr-only"> (completado)</span>
        </li>
        <li className="bk-step bk-step--active" aria-current="step">
          <span className="bk-step-num" aria-hidden="true">
            3
          </span>
          Datos<span className="bk-sr-only"> (paso actual)</span>
        </li>
        <li className="bk-step">
          <span className="bk-step-num" aria-hidden="true">
            4
          </span>
          Seña
        </li>
      </ol>

      <div className="bk-card">
        <div className="bk-card-head">
          <div>
            <div className="bk-card-title">
              {estado.practicaNombre} · {estado.duracionMin} min
            </div>
            <p className="bk-meta">
              {formatearFecha(estado.fecha)} · {inicio === '' ? 'elegí un horario' : formatearHora(inicio)}
            </p>
          </div>
          <Link className="bk-btn bk-btn--ghost bk-btn--sm" to="/">
            Cambiar
          </Link>
        </div>
        <div className="bk-foot">
          <span className="bk-meta">Seña ({estado.senaPct} %)</span>
          <span className="bk-price">Se calcula al confirmar</span>
        </div>
      </div>

      {conflicto && (
        <div className="bk-alert bk-alert--warning" role="alert">
          <div>
            <strong>Ese horario se acaba de ocupar</strong>
            Elegí otro de la lista actualizada: tus datos siguen cargados.
          </div>
        </div>
      )}

      {errorGeneral && (
        <div className="bk-alert bk-alert--danger" role="alert">
          <div>
            <strong>No pudimos confirmar tu turno</strong>
            Revisá tu conexión e intentá de nuevo. Si el problema sigue, llamá a la clínica.
          </div>
        </div>
      )}

      {conflicto && (
        <div className="bk-card">
          <div className="bk-card-head">
            <div>
              <div className="bk-card-title">Horarios actualizados</div>
              <p className="bk-meta">{formatearFecha(estado.fecha)}</p>
            </div>
          </div>
          {slotsRefrescados.length === 0 ? (
            <p className="bk-help">
              No quedan horarios libres para ese día. Volvé a elegir práctica y fecha.
            </p>
          ) : (
            <div
              className="bk-slots"
              role="group"
              aria-label={`Horarios disponibles actualizados del ${formatearFecha(estado.fecha)}`}
            >
              {slotsRefrescados.map((slot) => (
                <button
                  key={slot.inicio}
                  type="button"
                  className="bk-slot"
                  aria-pressed={slot.inicio === inicio}
                  onClick={() => {
                    setInicio(slot.inicio);
                    setConflicto(false);
                  }}
                >
                  {formatearHora(slot.inicio)}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      <form
        className="bk-card"
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          void confirmar();
        }}
      >
        <div className="bk-field">
          <label className="bk-label" htmlFor="bk-nombre">
            Nombre y apellido
          </label>
          <input
            className="bk-input"
            id="bk-nombre"
            name="nombre"
            type="text"
            autoComplete="name"
            placeholder="Juana Pérez"
            value={nombre}
            onChange={(event) => setNombre(event.target.value)}
          />
        </div>

        <div className="bk-field">
          <label className="bk-label" htmlFor="bk-telefono">
            WhatsApp
          </label>
          <input
            className="bk-input"
            id="bk-telefono"
            name="telefono"
            type="tel"
            inputMode="tel"
            autoComplete="tel"
            placeholder="11 5555 1234"
            aria-invalid={telefonoInvalido}
            aria-describedby={telefonoInvalido ? 'bk-telefono-error' : 'bk-telefono-help'}
            value={telefono}
            onChange={(event) => setTelefono(event.target.value)}
          />
          {telefonoInvalido ? (
            <span className="bk-error" id="bk-telefono-error" role="status" aria-live="polite">
              Ingresá un número de 10 dígitos, sin 0 ni 15. Ejemplo: 11 5555 1234.
            </span>
          ) : (
            <span className="bk-help" id="bk-telefono-help">
              Código de área y número, sin 0 ni 15. Ejemplo: 11 5555 1234.
            </span>
          )}
        </div>

        <button
          type="submit"
          className="bk-btn bk-btn--primary bk-btn--block"
          disabled={!puedeEnviar}
          aria-busy={enviando}
        >
          {enviando ? (
            <>
              <span className="bk-spinner" aria-hidden="true" />
              Confirmando turno…
            </>
          ) : (
            'Confirmar turno'
          )}
        </button>
        <p className="bk-help">
          En el paso siguiente se paga la seña. Si no se acredita, el horario se libera.
        </p>
      </form>
    </div>
  );
}

function ReservaConfirmada({
  reserva,
  estado,
}: {
  reserva: ReservaPublica;
  estado: EstadoReserva;
}) {
  return (
    <div className="booking-public">
      <h1 className="bk-card-title">Turno reservado</h1>

      <div className="bk-alert bk-alert--warning" role="status" aria-live="polite">
        <div>
          <strong>El pago online todavía no está disponible</strong>
          Tu turno quedó reservado como pendiente de seña. No se acreditó ningún pago.
        </div>
      </div>

      <div className="bk-card">
        <div className="bk-card-head">
          <div>
            <div className="bk-card-title">
              {estado.practicaNombre} · {estado.duracionMin} min
            </div>
            <p className="bk-meta">
              {formatearFecha(estado.fecha)} · {formatearHora(reserva.inicio)}
            </p>
          </div>
          <span className="bk-badge bk-badge--pending">Pendiente de seña</span>
        </div>
        <div className="bk-foot">
          <span className="bk-meta">Seña a coordinar</span>
          <span className="bk-price">{formatearMonto(reserva.monto_sena)}</span>
        </div>
      </div>

      <Link
        className="bk-btn bk-btn--primary bk-btn--block"
        to={`/gestionar/${reserva.manage_token}`}
      >
        Gestionar mi turno
      </Link>
      <p className="bk-help">
        Guardá este enlace: es la única forma de cancelar o reprogramar sin llamar. El estado va a
        seguir siendo “pendiente de seña” hasta que se acredite el pago.
      </p>
    </div>
  );
}
