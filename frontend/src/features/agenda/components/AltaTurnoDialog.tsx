import { useState } from 'react';
import { problemaDeError } from '@/shared/api-client/problema';
import { buscarPacientes, crearTurnoInterno } from '../api';
import { inicioIso } from '../formato';
import ExcepcionBloqueoDialog from './ExcepcionBloqueoDialog';
import type {
  AltaTurnoInput,
  Odontologo,
  PacienteBusqueda,
  PracticaInterna,
  Sillon,
  TurnoInterno,
} from '../types';

interface AltaTurnoDialogProps {
  fechaInicial: string;
  odontologos: Odontologo[];
  sillones: Sillon[];
  practicas: PracticaInterna[];
  puedeExceptuar: boolean;
  onCreado: (turno: TurnoInterno) => void;
  onCerrar: () => void;
}

export default function AltaTurnoDialog({
  fechaInicial,
  odontologos,
  sillones,
  practicas,
  puedeExceptuar,
  onCreado,
  onCerrar,
}: AltaTurnoDialogProps) {
  const [busqueda, setBusqueda] = useState('');
  const [resultados, setResultados] = useState<PacienteBusqueda[]>([]);
  const [paciente, setPaciente] = useState<PacienteBusqueda | null>(null);
  const [buscando, setBuscando] = useState(false);

  const [practicaId, setPracticaId] = useState('');
  const [sillonId, setSillonId] = useState('');
  const [odontologoId, setOdontologoId] = useState('');
  const [fecha, setFecha] = useState(fechaInicial);
  const [hora, setHora] = useState('');

  const [error, setError] = useState<string | null>(null);
  const [bloqueo, setBloqueo] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function handleBuscar() {
    setBuscando(true);
    setError(null);
    try {
      setResultados(await buscarPacientes(busqueda));
    } catch {
      setError('No se pudo buscar pacientes. Intentá de nuevo.');
    } finally {
      setBuscando(false);
    }
  }

  async function enviar(motivoExcepcion?: string) {
    if (!paciente || !practicaId || !sillonId || !odontologoId || !hora) {
      setError('Completá paciente, práctica, sillón, odontólogo y hora.');
      return;
    }

    const input: AltaTurnoInput = {
      paciente_id: paciente.id,
      sillon_id: sillonId,
      odontologo_id: odontologoId,
      tipo_practica_id: practicaId,
      inicio: inicioIso(fecha, hora),
    };
    if (motivoExcepcion !== undefined) {
      input.motivo_excepcion = motivoExcepcion;
    }

    setEnviando(true);
    setError(null);
    try {
      onCreado(await crearTurnoInterno(input));
    } catch (fallo) {
      const problema = problemaDeError(fallo);
      if (problema?.codigo === 'bloqueado') {
        setBloqueo(problema.bloqueado_hasta ?? '');
      } else if (problema?.codigo === 'solape') {
        setError('Ese horario se acaba de ocupar. Elegí otro horario disponible.');
      } else if (problema?.codigo === 'motivo_requerido') {
        setError('El motivo de la excepción es obligatorio.');
      } else {
        setError('No se pudo crear el turno. Intentá de nuevo.');
      }
    } finally {
      setEnviando(false);
    }
  }

  if (bloqueo !== null) {
    if (puedeExceptuar) {
      return (
        <div className="agenda-dialog-fondo">
          <ExcepcionBloqueoDialog
            bloqueadoHasta={bloqueo}
            onCancel={() => setBloqueo(null)}
            onConfirm={(motivo) => {
              setBloqueo(null);
              void enviar(motivo);
            }}
          />
        </div>
      );
    }

    return (
      <div className="agenda-dialog-fondo">
        <div className="agenda-dialog" role="dialog" aria-modal="true">
          <h3>Paciente bloqueado</h3>
          <div className="agenda-alerta agenda-alerta--danger" role="alert">
            El paciente tiene un bloqueo por ausentismo vigente y tu rol no puede exceptuarlo.
          </div>
          <div className="agenda-dialog__acciones">
            <button type="button" className="agenda-btn" onClick={onCerrar}>
              Volver
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="agenda-dialog-fondo">
      <div
        className="agenda-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="alta-titulo"
      >
        <h3 id="alta-titulo">Nuevo turno</h3>
        <p className="agenda-ayuda">
          Paciente existente de la clínica. La seña se calcula con el arancel vigente.
        </p>

        {error && (
          <div className="agenda-alerta agenda-alerta--danger" role="alert">
            {error}
          </div>
        )}

        <div className="agenda-campo">
          <label htmlFor="alta-buscar">Buscar paciente</label>
          <div className="agenda-campo__fila">
            <input
              id="alta-buscar"
              className="agenda-input"
              type="search"
              value={busqueda}
              placeholder="Nombre, teléfono o DNI"
              onChange={(event) => setBusqueda(event.target.value)}
            />
            <button
              type="button"
              className="agenda-btn"
              onClick={() => void handleBuscar()}
              disabled={buscando || busqueda.trim().length < 2}
            >
              {buscando ? 'Buscando…' : 'Buscar'}
            </button>
          </div>
          {paciente && <span className="agenda-elegido">Paciente: {paciente.nombre}</span>}
          {resultados.length > 0 && (
            <ul className="agenda-resultados">
              {resultados.map((resultado) => (
                <li key={resultado.id}>
                  <button
                    type="button"
                    className={`agenda-resultado${
                      paciente?.id === resultado.id ? ' agenda-resultado--elegido' : ''
                    }`}
                    aria-pressed={paciente?.id === resultado.id}
                    onClick={() => setPaciente(resultado)}
                  >
                    {resultado.nombre}
                    {resultado.dni ? ` · DNI ${resultado.dni}` : ''}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="agenda-form-grid">
          <div className="agenda-campo">
            <label htmlFor="alta-practica">Práctica</label>
            <select
              id="alta-practica"
              className="agenda-select"
              value={practicaId}
              onChange={(event) => setPracticaId(event.target.value)}
            >
              <option value="">Elegí una práctica</option>
              {practicas.map((practica) => (
                <option value={practica.id} key={practica.id}>
                  {practica.nombre} · {practica.duracion_min} min
                </option>
              ))}
            </select>
          </div>

          <div className="agenda-campo">
            <label htmlFor="alta-sillon">Sillón</label>
            <select
              id="alta-sillon"
              className="agenda-select"
              value={sillonId}
              onChange={(event) => setSillonId(event.target.value)}
            >
              <option value="">Elegí un sillón</option>
              {sillones.map((sillon) => (
                <option value={sillon.id} key={sillon.id}>
                  {sillon.nombre}
                </option>
              ))}
            </select>
          </div>

          <div className="agenda-campo">
            <label htmlFor="alta-odontologo">Odontólogo</label>
            <select
              id="alta-odontologo"
              className="agenda-select"
              value={odontologoId}
              onChange={(event) => setOdontologoId(event.target.value)}
            >
              <option value="">Elegí un odontólogo</option>
              {odontologos.map((odontologo) => (
                <option value={odontologo.id} key={odontologo.id}>
                  {odontologo.email}
                </option>
              ))}
            </select>
          </div>

          <div className="agenda-campo">
            <label htmlFor="alta-fecha">Fecha</label>
            <input
              id="alta-fecha"
              className="agenda-input"
              type="date"
              value={fecha}
              onChange={(event) => setFecha(event.target.value)}
            />
          </div>

          <div className="agenda-campo">
            <label htmlFor="alta-hora">Hora</label>
            <input
              id="alta-hora"
              className="agenda-input"
              type="time"
              value={hora}
              onChange={(event) => setHora(event.target.value)}
            />
          </div>
        </div>

        <div className="agenda-dialog__acciones">
          <button type="button" className="agenda-btn" onClick={onCerrar}>
            Cancelar
          </button>
          <button
            type="button"
            className="agenda-btn agenda-btn--primary"
            onClick={() => void enviar()}
            disabled={enviando}
          >
            {enviando ? 'Creando…' : 'Crear turno'}
          </button>
        </div>
      </div>
    </div>
  );
}
