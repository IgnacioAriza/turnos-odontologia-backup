import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import FiltrosAgenda from './FiltrosAgenda';
import type { FiltrosAgenda as Filtros } from '../types';

const FILTROS: Filtros = { vista: 'dia', fecha: '2026-11-12' };
const ODONTOLOGOS = [
  { id: 'o1', email: 'dra.gomez@clinica.com' },
  { id: 'o2', email: 'dr.perez@clinica.com' },
];
const SILLONES = [
  { id: 's1', nombre: 'Sillón 1' },
  { id: 's2', nombre: 'Sillón 2' },
];

function renderFiltros(overrides: Partial<Parameters<typeof FiltrosAgenda>[0]> = {}) {
  const onCambiar = vi.fn();
  const onVista = vi.fn();
  render(
    <FiltrosAgenda
      filtros={FILTROS}
      odontologos={ODONTOLOGOS}
      sillones={SILLONES}
      mostrarOdontologo
      onCambiar={onCambiar}
      onVista={onVista}
      {...overrides}
    />,
  );
  return { onCambiar, onVista };
}

describe('FiltrosAgenda', () => {
  it('emite el cambio de fecha', () => {
    const { onCambiar } = renderFiltros();

    fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2026-11-13' } });

    expect(onCambiar).toHaveBeenCalledWith({ fecha: '2026-11-13' });
  });

  it('emite el sillón elegido por id', () => {
    const { onCambiar } = renderFiltros();

    fireEvent.change(screen.getByLabelText('Sillón'), { target: { value: 's2' } });

    expect(onCambiar).toHaveBeenCalledWith({ sillonId: 's2' });
  });

  it('oculta el filtro de odontólogo para el rol odonto', () => {
    renderFiltros({ mostrarOdontologo: false });

    expect(screen.queryByLabelText('Odontólogo')).not.toBeInTheDocument();
  });

  it('cambia entre día y semana', () => {
    const { onVista } = renderFiltros();

    const semana = screen.getByRole('button', { name: 'Semana' });
    expect(semana).toHaveAttribute('aria-pressed', 'false');
    fireEvent.click(semana);

    expect(onVista).toHaveBeenCalledWith('semana');
  });
});
