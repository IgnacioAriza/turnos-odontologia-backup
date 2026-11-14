import { horaDe } from '@/features/agenda/formato';
import { claseSena, etiquetaSena } from '../formato';
import ContactoWhatsApp from './ContactoWhatsApp';
import type { EstadoMarcable, PanelTurno, ResumenPanel } from '../types';

interface PanelListaProps {
  turnos: PanelTurno[];
  resumen: ResumenPanel;
  onMarcar: (turno: PanelTurno, destino: EstadoMarcable) => void;
}

function plural(cantidad: number, singular: string, plural_: string): string {
  return `${cantidad} ${cantidad === 1 ? singular : plural_}`;
}

export default function PanelLista({ turnos, resumen, onMarcar }: PanelListaProps) {
  const ordenados = [...turnos].sort((a, b) => a.inicio.localeCompare(b.inicio));

  return (
    <section className="panel-lista" aria-label="Turnos de la jornada">
      <div className="panel-resumen" data-testid="resumen-panel">
        <strong>{plural(resumen.total, 'turno', 'turnos')}</strong>
        <span>{plural(resumen.pendientes_sena, 'pendiente de seña', 'pendientes de seña')}</span>
        <span>{plural(resumen.confirmados, 'confirmado', 'confirmados')}</span>
        <span>{plural(resumen.completados, 'atendido', 'atendidos')}</span>
        <span>{plural(resumen.ausentes, 'ausente', 'ausentes')}</span>
      </div>

      {ordenados.length === 0 ? (
        <div className="panel-vacio">
          <h3>No hay turnos para esta jornada</h3>
          <p>Probá con otra fecha.</p>
        </div>
      ) : (
        <div className="panel-tabla" role="table" aria-label="Turnos por hora">
          <div className="panel-fila panel-fila--head" role="row">
            <span role="columnheader">Hora</span>
            <span role="columnheader">Paciente</span>
            <span role="columnheader">Práctica</span>
            <span role="columnheader">Seña</span>
            <span role="columnheader">Acciones</span>
          </div>

          {ordenados.map((turno) => {
            const confirmado = turno.estado === 'confirmado';
            const avisoFalta =
              confirmado && turno.paciente.faltas_count >= 1 && !turno.paciente.bloqueado_hasta;

            return (
              <div
                className={`panel-fila panel-fila--${turno.estado}`}
                role="row"
                data-testid={`panel-turno-${turno.id}`}
                key={turno.id}
              >
                <span className="panel-hora" role="rowheader">
                  {horaDe(turno.inicio)}
                </span>

                <div className="panel-paciente">
                  <strong>{turno.paciente.nombre}</strong>
                  <span className="panel-meta">
                    {turno.sillon.nombre} · {turno.odontologo.email}
                  </span>
                  <ContactoWhatsApp
                    telefono={turno.paciente.telefono}
                    nombre={turno.paciente.nombre}
                  />
                  {avisoFalta && (
                    <span className="panel-aviso-falta" role="note">
                      Próxima ausencia: bloqueo de 30 días
                    </span>
                  )}
                </div>

                <div className="panel-practica">
                  <strong>{turno.practica.nombre}</strong>
                  <span className="panel-meta">${turno.monto_sena}</span>
                </div>

                <span className={`panel-badge panel-badge--${claseSena(turno.estado_sena)}`}>
                  {etiquetaSena(turno.estado_sena)}
                </span>

                <div className="panel-acciones">
                  {confirmado ? (
                    <>
                      <button
                        type="button"
                        className="panel-btn panel-btn--ok"
                        onClick={() => onMarcar(turno, 'completado')}
                      >
                        Marcar llegada
                      </button>
                      <button
                        type="button"
                        className="panel-btn panel-btn--danger"
                        onClick={() => onMarcar(turno, 'ausente')}
                      >
                        Confirmar ausencia
                      </button>
                    </>
                  ) : (
                    <span className="panel-meta">
                      {turno.estado === 'completado'
                        ? 'Atendido'
                        : turno.estado === 'ausente'
                          ? 'Ausente'
                          : 'Sin acciones'}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
