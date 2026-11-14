import type {
  CambiosFiltros,
  EstadoTurno,
  FiltrosAgenda as Filtros,
  Odontologo,
  Sillon,
  VistaAgenda,
} from '../types';

interface FiltrosAgendaProps {
  filtros: Filtros;
  odontologos: Odontologo[];
  sillones: Sillon[];
  mostrarOdontologo: boolean;
  onCambiar: (cambios: CambiosFiltros) => void;
  onVista: (vista: VistaAgenda) => void;
}

const ESTADOS: Array<{ valor: EstadoTurno; etiqueta: string }> = [
  { valor: 'pendiente_sena', etiqueta: 'Pendiente de seña' },
  { valor: 'confirmado', etiqueta: 'Confirmado' },
  { valor: 'completado', etiqueta: 'Atendido' },
  { valor: 'ausente', etiqueta: 'Ausente' },
  { valor: 'cancelado', etiqueta: 'Cancelado' },
];

export default function FiltrosAgenda({
  filtros,
  odontologos,
  sillones,
  mostrarOdontologo,
  onCambiar,
  onVista,
}: FiltrosAgendaProps) {
  return (
    <div className="agenda-filtros">
      <div className="agenda-filtros__campos">
        <div className="agenda-campo">
          <label htmlFor="agenda-fecha">Fecha</label>
          <input
            id="agenda-fecha"
            className="agenda-input"
            type="date"
            value={filtros.fecha}
            onChange={(event) => onCambiar({ fecha: event.target.value })}
          />
        </div>

        <div className="agenda-campo">
          <label htmlFor="agenda-sillon">Sillón</label>
          <select
            id="agenda-sillon"
            className="agenda-select"
            value={filtros.sillonId ?? ''}
            onChange={(event) => {
              const valor = event.target.value;
              onCambiar(valor === '' ? { sillonId: '' } : { sillonId: valor });
            }}
          >
            <option value="">Todos los sillones</option>
            {sillones.map((sillon) => (
              <option value={sillon.id} key={sillon.id}>
                {sillon.nombre}
              </option>
            ))}
          </select>
        </div>

        {mostrarOdontologo && (
          <div className="agenda-campo">
            <label htmlFor="agenda-odontologo">Odontólogo</label>
            <select
              id="agenda-odontologo"
              className="agenda-select"
              value={filtros.odontologoId ?? ''}
              onChange={(event) => {
                const valor = event.target.value;
                onCambiar(valor === '' ? { odontologoId: '' } : { odontologoId: valor });
              }}
            >
              <option value="">Todos los odontólogos</option>
              {odontologos.map((odontologo) => (
                <option value={odontologo.id} key={odontologo.id}>
                  {odontologo.email}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="agenda-campo">
          <label htmlFor="agenda-estado">Estado</label>
          <select
            id="agenda-estado"
            className="agenda-select"
            value={filtros.estado ?? ''}
            onChange={(event) => {
              const valor = event.target.value;
              if (valor === '') {
                onCambiar({ estado: undefined });
                return;
              }
              onCambiar({ estado: valor as EstadoTurno });
            }}
          >
            <option value="">Todos (sin cancelados)</option>
            {ESTADOS.map((estado) => (
              <option value={estado.valor} key={estado.valor}>
                {estado.etiqueta}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="agenda-vista" role="group" aria-label="Vista de la agenda">
        <button
          type="button"
          aria-pressed={filtros.vista === 'dia'}
          onClick={() => onVista('dia')}
        >
          Día
        </button>
        <button
          type="button"
          aria-pressed={filtros.vista === 'semana'}
          onClick={() => onVista('semana')}
        >
          Semana
        </button>
      </div>
    </div>
  );
}
