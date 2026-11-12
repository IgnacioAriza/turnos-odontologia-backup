/**
 * Landing pública `/` (C-06): catálogo, fecha y búsqueda de horarios.
 *
 * Sin sesión y sin login: el paciente elige práctica y día, ve los huecos libres
 * y continúa al formulario con el horario elegido en `location.state`.
 */

import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchPracticas, fetchSlots } from '@/features/booking/api';
import { formatearFecha, formatearHora, hoyISO } from '@/features/booking/formato';
import type { PracticaPublica, SlotsResponse } from '@/features/booking/types';
import '@/features/booking/booking.css';

export default function HomePage() {
  const [practicas, setPracticas] = useState<PracticaPublica[] | null>(null);
  const [errorCatalogo, setErrorCatalogo] = useState(false);
  const [practicaId, setPracticaId] = useState('');
  const [fecha, setFecha] = useState(hoyISO);
  const [resultado, setResultado] = useState<SlotsResponse | null>(null);
  const [buscando, setBuscando] = useState(false);
  const [errorBusqueda, setErrorBusqueda] = useState(false);
  const [inicioElegido, setInicioElegido] = useState<string | null>(null);

  const cargarCatalogo = useCallback(async () => {
    setErrorCatalogo(false);
    try {
      const lista = await fetchPracticas();
      setPracticas(lista);
      setPracticaId((actual) =>
        actual !== '' && lista.some((practica) => practica.id === actual)
          ? actual
          : (lista[0]?.id ?? ''),
      );
    } catch {
      setPracticas(null);
      setErrorCatalogo(true);
    }
  }, []);

  useEffect(() => {
    void cargarCatalogo();
  }, [cargarCatalogo]);

  const buscar = async () => {
    if (practicaId === '') {
      return;
    }
    setBuscando(true);
    setErrorBusqueda(false);
    setInicioElegido(null);
    try {
      setResultado(await fetchSlots({ practicaId, fecha }));
    } catch {
      setResultado(null);
      setErrorBusqueda(true);
    } finally {
      setBuscando(false);
    }
  };

  const practicaElegida = practicas?.find((practica) => practica.id === practicaId) ?? null;
  const slots = resultado?.slots ?? [];

  if (errorCatalogo) {
    return (
      <div className="booking-public">
        <div className="bk-alert bk-alert--danger" role="alert">
          <div>
            <strong>No pudimos cargar las prácticas</strong>
            Revisá tu conexión e intentá de nuevo. Si el problema sigue, llamá a la clínica.
          </div>
        </div>
        <button type="button" className="bk-btn bk-btn--primary bk-btn--block" onClick={cargarCatalogo}>
          Reintentar
        </button>
      </div>
    );
  }

  if (practicas === null) {
    return (
      <div className="booking-public">
        <p className="bk-loading" role="status">
          <span className="bk-spinner" aria-hidden="true" />
          Cargando prácticas…
        </p>
      </div>
    );
  }

  if (practicas.length === 0) {
    return (
      <div className="booking-public">
        <div className="bk-empty">
          <h1>No hay prácticas disponibles</h1>
          <p>
            Todavía no hay prácticas cargadas para reservar online. Llamá a la clínica para
            coordinar tu turno.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="booking-public booking-public--split">
      <div className="booking-public__col">
        <div className="bk-hero">
          <h1>Reservá tu turno</h1>
          <p>Elegí la práctica y el día. No hace falta crear una cuenta.</p>
        </div>

        <form
          className="bk-card"
          noValidate
          onSubmit={(event) => {
            event.preventDefault();
            void buscar();
          }}
        >
          <div className="bk-field">
            <label className="bk-label" htmlFor="bk-practica">
              Práctica
            </label>
            <select
              className="bk-select"
              id="bk-practica"
              value={practicaId}
              onChange={(event) => {
                setPracticaId(event.target.value);
                setResultado(null);
                setInicioElegido(null);
              }}
            >
              {practicas.map((practica) => (
                <option key={practica.id} value={practica.id}>
                  {`${practica.nombre} · ${practica.duracion_min} min`}
                </option>
              ))}
            </select>
          </div>

          <div className="bk-field">
            <label className="bk-label" htmlFor="bk-fecha">
              Fecha
            </label>
            <input
              className="bk-input"
              id="bk-fecha"
              type="date"
              value={fecha}
              min={hoyISO()}
              onChange={(event) => {
                setFecha(event.target.value);
                setResultado(null);
                setInicioElegido(null);
              }}
            />
            <span className="bk-help">Los horarios se muestran en hora de Buenos Aires.</span>
          </div>

          <button type="submit" className="bk-btn bk-btn--primary bk-btn--block" disabled={buscando}>
            {errorBusqueda ? 'Reintentar' : 'Buscar horarios'}
          </button>
        </form>

        <p className="bk-help">
          ¿Ya reservaste? Usá el enlace de gestión que te enviamos por WhatsApp.
        </p>
      </div>

      <div className="booking-public__col">
        {buscando && (
          <p className="bk-loading" role="status">
            <span className="bk-spinner" aria-hidden="true" />
            Buscando horarios disponibles…
          </p>
        )}

        {errorBusqueda && !buscando && (
          <div className="bk-alert bk-alert--danger" role="alert">
            <div>
              <strong>No pudimos buscar horarios</strong>
              Revisá tu conexión e intentá de nuevo. Si el problema sigue, llamá a la clínica.
            </div>
          </div>
        )}

        {resultado !== null && !buscando && slots.length === 0 && (
          <div className="bk-empty">
            <h2>No hay horarios disponibles</h2>
            <p>
              No quedan horarios libres para {formatearFecha(resultado.fecha)}. Probá con otra
              fecha o elegí otra práctica.
            </p>
          </div>
        )}

        {resultado !== null && slots.length > 0 && practicaElegida !== null && (
          <>
            <div className="bk-card-head">
              <div>
                <h2 className="bk-card-title">Horarios libres</h2>
                <p className="bk-meta">
                  {formatearFecha(resultado.fecha)} · {practicaElegida.nombre} ·{' '}
                  {resultado.duracion_min} min
                </p>
              </div>
            </div>

            <div
              className="bk-slots"
              role="group"
              aria-label={`Horarios disponibles del ${formatearFecha(resultado.fecha)}`}
            >
              {slots.map((slot) => {
                const elegido = slot.inicio === inicioElegido;
                return (
                  <button
                    key={slot.inicio}
                    type="button"
                    className="bk-slot"
                    aria-pressed={elegido}
                    onClick={() => setInicioElegido(slot.inicio)}
                  >
                    {elegido && <span aria-hidden="true">✓</span>}
                    {formatearHora(slot.inicio)}
                  </button>
                );
              })}
            </div>

            {inicioElegido !== null && (
              <div className="bk-card">
                <div className="bk-card-head">
                  <div>
                    <div className="bk-card-title">Turno elegido</div>
                    <p className="bk-meta">
                      {formatearFecha(resultado.fecha)} · {formatearHora(inicioElegido)}
                    </p>
                  </div>
                  <span className="bk-badge bk-badge--muted">{practicaElegida.nombre}</span>
                </div>
                <p className="bk-help">Al reservar se pide una seña. El detalle aparece en el siguiente paso.</p>
                <Link
                  className="bk-btn bk-btn--primary bk-btn--block"
                  to="/reservar"
                  state={{
                    practicaId: practicaElegida.id,
                    practicaNombre: practicaElegida.nombre,
                    duracionMin: resultado.duracion_min,
                    senaPct: practicaElegida.sena_pct,
                    fecha: resultado.fecha,
                    inicio: inicioElegido,
                  }}
                >
                  Continuar
                </Link>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
