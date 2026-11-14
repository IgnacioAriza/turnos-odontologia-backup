import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import AgendaDia from './AgendaDia';
import type { AgendaTurno } from '../types';

const SILLON_1 = { id: 's1', nombre: 'Sillón 1' };
const SILLON_2 = { id: 's2', nombre: 'Sillón 2' };

function turno(overrides: Partial<AgendaTurno> & Pick<AgendaTurno, 'id' | 'inicio'>): AgendaTurno {
  return {
    fin: overrides.inicio,
    estado: 'confirmado',
    paciente: { id: 'p1', nombre: 'Juana Pérez' },
    practica: { id: 'pr1', nombre: 'Limpieza dental' },
    sillon: SILLON_1,
    odontologo: { id: 'o1', email: 'dra.gomez@clinica.com' },
    ...overrides,
  };
}

describe('AgendaDia', () => {
  it('renderiza una columna por sillón y una fila por hora', () => {
    render(
      <AgendaDia
        fecha="2026-11-12"
        sillones={[SILLON_1, SILLON_2]}
        turnos={[
          turno({ id: 't1', inicio: '2026-11-12T09:00:00-03:00' }),
          turno({
            id: 't2',
            inicio: '2026-11-12T09:00:00-03:00',
            sillon: SILLON_2,
            paciente: { id: 'p2', nombre: 'Beto Sosa' },
          }),
        ]}
      />,
    );

    expect(screen.getByRole('columnheader', { name: 'Sillón 1' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Sillón 2' })).toBeInTheDocument();
    expect(screen.getByRole('rowheader', { name: '09:00' })).toBeInTheDocument();

    const celda1 = screen.getByTestId('celda-s1-09:00');
    expect(within(celda1).getByText('Juana Pérez')).toBeInTheDocument();
    expect(within(celda1).getByText('Limpieza dental')).toBeInTheDocument();

    const celda2 = screen.getByTestId('celda-s2-09:00');
    expect(within(celda2).getByText('Beto Sosa')).toBeInTheDocument();
  });

  it('ordena las horas de menor a mayor sin importar el orden de la API', () => {
    render(
      <AgendaDia
        fecha="2026-11-12"
        sillones={[SILLON_1]}
        turnos={[
          turno({ id: 'tarde', inicio: '2026-11-12T15:00:00-03:00' }),
          turno({ id: 'manana', inicio: '2026-11-12T08:30:00-03:00' }),
        ]}
      />,
    );

    const horas = screen.getAllByRole('rowheader').map((nodo) => nodo.textContent);
    expect(horas).toEqual(['08:30', '15:00']);
  });

  it('muestra el estado del turno con texto, no solo color', () => {
    render(
      <AgendaDia
        fecha="2026-11-12"
        sillones={[SILLON_1]}
        turnos={[
          turno({ id: 't1', inicio: '2026-11-12T09:00:00-03:00', estado: 'pendiente_sena' }),
        ]}
      />,
    );

    expect(screen.getByText('Pendiente de seña')).toBeInTheDocument();
  });

  it('muestra el vacío del día', () => {
    render(<AgendaDia fecha="2026-11-12" sillones={[SILLON_1]} turnos={[]} />);

    expect(screen.getByText('No hay turnos para este día')).toBeInTheDocument();
  });
});
