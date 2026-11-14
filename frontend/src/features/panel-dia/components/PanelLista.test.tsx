import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import PanelLista from './PanelLista';
import type { PanelTurno, ResumenPanel } from '../types';

const RESUMEN: ResumenPanel = {
  total: 3,
  pendientes_sena: 1,
  confirmados: 1,
  completados: 1,
  ausentes: 0,
};

function turno(overrides: Partial<PanelTurno> & Pick<PanelTurno, 'id' | 'inicio'>): PanelTurno {
  return {
    fin: overrides.inicio,
    estado: 'confirmado',
    estado_sena: 'aprobada',
    monto_sena: '2000.00',
    paciente: {
      id: 'p1',
      nombre: 'Juana Pérez',
      telefono: '+5491140000001',
      faltas_count: 0,
      bloqueado_hasta: null,
    },
    practica: { id: 'pr1', nombre: 'Limpieza dental' },
    sillon: { id: 's1', nombre: 'Sillón 1' },
    odontologo: { id: 'o1', email: 'dra.gomez@clinica.com' },
    ...overrides,
  };
}

const TURNOS: PanelTurno[] = [
  turno({
    id: 'tarde',
    inicio: '2026-11-12T15:00:00-03:00',
    paciente: {
      id: 'p2',
      nombre: 'Beto Sosa',
      telefono: '+5491140000002',
      faltas_count: 0,
      bloqueado_hasta: null,
    },
  }),
  turno({
    id: 'manana',
    inicio: '2026-11-12T09:00:00-03:00',
    estado: 'pendiente_sena',
    estado_sena: 'pendiente',
  }),
];

describe('PanelLista', () => {
  it('ordena los turnos por hora y muestra el resumen de la jornada', () => {
    render(<PanelLista turnos={TURNOS} resumen={RESUMEN} onMarcar={vi.fn()} />);

    const filas = screen.getAllByTestId(/^panel-turno-/);
    expect(filas.map((fila) => fila.getAttribute('data-testid'))).toEqual([
      'panel-turno-manana',
      'panel-turno-tarde',
    ]);

    expect(screen.getByTestId('resumen-panel')).toHaveTextContent('1 pendiente de seña');
    expect(screen.getByTestId('resumen-panel')).toHaveTextContent('1 confirmado');
    expect(screen.getByTestId('resumen-panel')).toHaveTextContent('1 atendido');
  });

  it('muestra la seña con texto, no solo color', () => {
    render(<PanelLista turnos={TURNOS} resumen={RESUMEN} onMarcar={vi.fn()} />);

    const manana = screen.getByTestId('panel-turno-manana');
    expect(within(manana).getByText('Seña pendiente')).toBeInTheDocument();

    const tarde = screen.getByTestId('panel-turno-tarde');
    expect(within(tarde).getByText('Seña aprobada')).toBeInTheDocument();
  });

  it('solo ofrece acciones sobre turnos confirmados', () => {
    render(<PanelLista turnos={TURNOS} resumen={RESUMEN} onMarcar={vi.fn()} />);

    expect(
      within(screen.getByTestId('panel-turno-tarde')).getByRole('button', { name: 'Marcar llegada' }),
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId('panel-turno-manana')).queryByRole('button', {
        name: 'Marcar llegada',
      }),
    ).not.toBeInTheDocument();
  });

  it('emite el marcado con el turno y el destino', () => {
    const onMarcar = vi.fn();
    render(<PanelLista turnos={TURNOS} resumen={RESUMEN} onMarcar={onMarcar} />);

    fireEvent.click(screen.getByRole('button', { name: 'Confirmar ausencia' }));

    expect(onMarcar).toHaveBeenCalledWith(expect.objectContaining({ id: 'tarde' }), 'ausente');
  });

  it('avisa cuando la próxima ausencia bloquea 30 días', () => {
    render(
      <PanelLista
        turnos={[
          turno({
            id: 't1',
            inicio: '2026-11-12T09:00:00-03:00',
            paciente: {
              id: 'p1',
              nombre: 'Juana Pérez',
              telefono: '+5491140000001',
              faltas_count: 1,
              bloqueado_hasta: null,
            },
          }),
        ]}
        resumen={RESUMEN}
        onMarcar={vi.fn()}
      />,
    );

    expect(screen.getByText('Próxima ausencia: bloqueo de 30 días')).toBeInTheDocument();
  });

  it('muestra el vacío de la jornada', () => {
    render(<PanelLista turnos={[]} resumen={{ ...RESUMEN, total: 0 }} onMarcar={vi.fn()} />);

    expect(screen.getByText('No hay turnos para esta jornada')).toBeInTheDocument();
  });
});
