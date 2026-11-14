import { etiquetaDia, fechaDe, horaDe, semanaDe } from '../formato';
import type { AgendaTurno } from '../types';

interface AgendaSemanaProps {
  fecha: string;
  turnos: AgendaTurno[];
  hoy?: string;
}

export default function AgendaSemana({ fecha, turnos, hoy }: AgendaSemanaProps) {
  const dias = semanaDe(fecha);

  return (
    <div className="agenda-semana" data-testid="agenda-semana">
      {dias.map((dia) => {
        const delDia = turnos
          .filter((turno) => fechaDe(turno.inicio) === dia)
          .sort((a, b) => a.inicio.localeCompare(b.inicio));
        const esHoy = hoy === dia;

        return (
          <article
            className={`agenda-semana__dia${esHoy ? ' agenda-semana__dia--hoy' : ''}`}
            data-testid={`dia-${dia}`}
            key={dia}
          >
            <header>
              <strong>{etiquetaDia(dia)}</strong>
              {esHoy && <span className="agenda-semana__hoy">hoy</span>}
              <span>{delDia.length} turnos</span>
            </header>

            {delDia.length === 0 ? (
              <p className="agenda-semana__vacio">Sin turnos</p>
            ) : (
              delDia.map((turno) => (
                <div
                  className={`agenda-semana__item agenda-semana__item--${turno.estado}`}
                  key={turno.id}
                >
                  <strong>
                    {horaDe(turno.inicio)} · {turno.paciente.nombre}
                  </strong>
                  <span>
                    {turno.practica.nombre} · {turno.sillon.nombre}
                  </span>
                </div>
              ))
            )}
          </article>
        );
      })}
    </div>
  );
}
