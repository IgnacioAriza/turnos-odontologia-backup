import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import AgendaSemana from './AgendaSemana';
import type { AgendaTurno } from '../types';

function turno(id: string, inicio: string, nombre: string): AgendaTurno {
  return {
    id,
    inicio,
    fin: inicio,
    estado: 'confirmado',
    paciente: { id: `p-${id}`, nombre },
    practica: { id: 'pr1', nombre: 'Limpieza dental' },
    sillon: { id: 's1', nombre: 'Sillón 1' },
    odontologo: { id: 'o1', email: 'dra.gomez@clinica.com' },
  };
}

describe('AgendaSemana', () => {
  it('renderiza los siete días de la semana de la fecha pedida', () => {
    render(
      <AgendaSemana
        fecha="2026-11-12"
        turnos={[turno('t1', '2026-11-12T09:00:00-03:00', 'Juana Pérez')]}
      />,
    );

    expect(screen.getByTestId('dia-2026-11-09')).toBeInTheDocument();
    expect(screen.getByTestId('dia-2026-11-15')).toBeInTheDocument();
    expect(screen.getAllByTestId(/^dia-2026-11-/)).toHaveLength(7);
  });

  it('agrupa cada turno bajo su día con hora y paciente', () => {
    render(
      <AgendaSemana
        fecha="2026-11-12"
        turnos={[
          turno('t1', '2026-11-11T10:00:00-03:00', 'Carla Díaz'),
          turno('t2', '2026-11-12T09:00:00-03:00', 'Juana Pérez'),
        ]}
      />,
    );

    const miercoles = screen.getByTestId('dia-2026-11-11');
    expect(within(miercoles).getByText('10:00 · Carla Díaz')).toBeInTheDocument();

    const jueves = screen.getByTestId('dia-2026-11-12');
    expect(within(jueves).getByText('09:00 · Juana Pérez')).toBeInTheDocument();
  });

  it('marca el día de hoy con un indicador textual', () => {
    render(<AgendaSemana fecha="2026-11-12" turnos={[]} hoy="2026-11-12" />);

    expect(within(screen.getByTestId('dia-2026-11-12')).getByText('hoy')).toBeInTheDocument();
  });

  it('muestra los días sin turnos como cerrados o vacíos', () => {
    render(<AgendaSemana fecha="2026-11-12" turnos={[]} />);

    expect(within(screen.getByTestId('dia-2026-11-15')).getByText('Sin turnos')).toBeInTheDocument();
  });
});
