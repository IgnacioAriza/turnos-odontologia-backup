import { claseEstado, etiquetaEstado, horaDe } from '../formato';
import type { AgendaSillon, AgendaTurno } from '../types';

interface AgendaDiaProps {
  fecha: string;
  turnos: AgendaTurno[];
  sillones: AgendaSillon[];
}

/** Sillones de la grilla: los configurados primero, más cualquier sillón con turnos. */
function columnasDe(turnos: AgendaTurno[], sillones: AgendaSillon[]): AgendaSillon[] {
  const columnas = [...sillones];
  for (const turno of turnos) {
    if (!columnas.some((sillon) => sillon.id === turno.sillon.id)) {
      columnas.push(turno.sillon);
    }
  }
  return columnas;
}

export default function AgendaDia({ fecha, turnos, sillones }: AgendaDiaProps) {
  if (turnos.length === 0) {
    return (
      <div className="agenda-dia agenda-dia--vacio" data-testid="agenda-dia">
        <div className="agenda-vacio">
          <h3>No hay turnos para este día</h3>
          <p>Probá con otra fecha o creá un turno interno.</p>
        </div>
      </div>
    );
  }

  const columnas = columnasDe(turnos, sillones);
  const horas = [...new Set(turnos.map((turno) => horaDe(turno.inicio)))].sort((a, b) =>
    a.localeCompare(b),
  );
  // El mockup aprobado ajusta las columnas al ancho disponible: sin scroll
  // horizontal en mobile. La columna de horas es fija.
  const grilla = { gridTemplateColumns: `72px repeat(${columnas.length}, minmax(0, 1fr))` };

  return (
    <div className="agenda-dia" data-testid="agenda-dia">
      <div className="agenda-dia__tabla" role="table" aria-label={`Turnos del ${fecha}`}>
        <div className="agenda-dia__fila agenda-dia__fila--head" role="row" style={grilla}>
          <div className="agenda-dia__hora" role="columnheader">
            Hora
          </div>
          {columnas.map((sillon) => (
            <div className="agenda-dia__sillon" role="columnheader" key={sillon.id}>
              {sillon.nombre}
            </div>
          ))}
        </div>

        {horas.map((hora) => (
          <div className="agenda-dia__fila" role="row" key={hora} style={grilla}>
            <div className="agenda-dia__hora" role="rowheader">
              {hora}
            </div>
            {columnas.map((sillon) => {
              const enCelda = turnos.filter(
                (turno) => horaDe(turno.inicio) === hora && turno.sillon.id === sillon.id,
              );
              return (
                <div
                  className="agenda-dia__celda"
                  role="cell"
                  data-testid={`celda-${sillon.id}-${hora}`}
                  key={sillon.id}
                >
                  {enCelda.map((turno) => (
                    <article
                      className={`agenda-turno agenda-turno--${claseEstado(turno.estado)}`}
                      key={turno.id}
                    >
                      <span className="agenda-turno__hora">
                        {hora} · {sillon.nombre}
                      </span>
                      <strong>{turno.paciente.nombre}</strong>
                      <span className="agenda-turno__meta">{turno.practica.nombre}</span>
                      <span className="agenda-turno__meta">{turno.odontologo.email}</span>
                      <span className={`agenda-badge agenda-badge--${claseEstado(turno.estado)}`}>
                        {etiquetaEstado(turno.estado)}
                      </span>
                    </article>
                  ))}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}
