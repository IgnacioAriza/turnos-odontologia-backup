/**
 * Landing pública `/` (C-06 tasks 9.1 y 9.2).
 *
 * Cubre los escenarios de `booking-publico`: catálogo desde la API, búsqueda de
 * horarios, día sin horarios, catálogo vacío y error con reintento.
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import HomePage from './HomePage';
import { fetchPracticas, fetchSlots } from '@/features/booking/api';
import type { PracticaPublica, SlotsResponse } from '@/features/booking/types';

vi.mock('@/features/booking/api', () => ({
  fetchPracticas: vi.fn(),
  fetchSlots: vi.fn(),
}));

const practicas: PracticaPublica[] = [
  { id: 'p1', nombre: 'Limpieza dental', duracion_min: 40, sena_pct: 30 },
  { id: 'p2', nombre: 'Endodoncia', duracion_min: 60, sena_pct: 20 },
];

const slots: SlotsResponse = {
  fecha: '2026-11-12',
  practica_id: 'p1',
  duracion_min: 40,
  slots: [
    {
      inicio: '2026-11-12T12:30:00Z',
      fin: '2026-11-12T13:10:00Z',
      sillon_id: 's1',
      odontologo_id: 'o1',
    },
    {
      inicio: '2026-11-12T13:30:00Z',
      fin: '2026-11-12T14:10:00Z',
      sillon_id: 's1',
      odontologo_id: 'o1',
    },
  ],
};

function renderLanding() {
  return render(
    <MemoryRouter>
      <HomePage />
    </MemoryRouter>,
  );
}

describe('HomePage', () => {
  beforeEach(() => {
    vi.mocked(fetchPracticas).mockReset();
    vi.mocked(fetchSlots).mockReset();
  });

  it('llena el selector con las prácticas del catálogo público', async () => {
    vi.mocked(fetchPracticas).mockResolvedValue(practicas);

    renderLanding();

    expect(
      await screen.findByRole('option', { name: 'Limpieza dental · 40 min' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Endodoncia · 60 min' })).toBeInTheDocument();
    expect(screen.getByLabelText('Fecha')).toBeInTheDocument();
  });

  it('muestra un estado explícito cuando no hay prácticas activas', async () => {
    vi.mocked(fetchPracticas).mockResolvedValue([]);

    renderLanding();

    expect(await screen.findByText(/No hay prácticas disponibles/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Buscar horarios' })).not.toBeInTheDocument();
  });

  it('busca horarios con la práctica y la fecha elegidas', async () => {
    vi.mocked(fetchPracticas).mockResolvedValue(practicas);
    vi.mocked(fetchSlots).mockResolvedValue(slots);

    renderLanding();
    await screen.findByRole('option', { name: 'Limpieza dental · 40 min' });

    fireEvent.click(screen.getByRole('button', { name: 'Buscar horarios' }));

    expect(await screen.findByRole('button', { name: '09:30' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '10:30' })).toBeInTheDocument();
    expect(fetchSlots).toHaveBeenCalledWith({ practicaId: 'p1', fecha: expect.any(String) });
  });

  it('avisa cuando el día no tiene horarios y sugiere otra fecha', async () => {
    vi.mocked(fetchPracticas).mockResolvedValue(practicas);
    vi.mocked(fetchSlots).mockResolvedValue({ ...slots, slots: [] });

    renderLanding();
    await screen.findByRole('option', { name: 'Limpieza dental · 40 min' });

    fireEvent.click(screen.getByRole('button', { name: 'Buscar horarios' }));

    expect(await screen.findByText(/No hay horarios disponibles/i)).toBeInTheDocument();
    expect(screen.getByText(/Probá con otra fecha/i)).toBeInTheDocument();
  });

  it('muestra un error legible y permite reintentar sin volver a elegir', async () => {
    vi.mocked(fetchPracticas).mockResolvedValue(practicas);
    vi.mocked(fetchSlots).mockRejectedValueOnce(new Error('boom'));

    renderLanding();
    await screen.findByRole('option', { name: 'Limpieza dental · 40 min' });

    fireEvent.click(screen.getByRole('button', { name: 'Buscar horarios' }));

    const alerta = await screen.findByRole('alert');
    expect(alerta).toHaveTextContent('No pudimos buscar horarios');
    expect(alerta).not.toHaveTextContent('boom');

    vi.mocked(fetchSlots).mockResolvedValueOnce(slots);
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }));

    expect(await screen.findByRole('button', { name: '09:30' })).toBeInTheDocument();
    expect(fetchSlots).toHaveBeenCalledTimes(2);
  });

  it('permite continuar al formulario con el horario elegido', async () => {
    vi.mocked(fetchPracticas).mockResolvedValue(practicas);
    vi.mocked(fetchSlots).mockResolvedValue(slots);

    renderLanding();
    await screen.findByRole('option', { name: 'Limpieza dental · 40 min' });
    fireEvent.click(screen.getByRole('button', { name: 'Buscar horarios' }));
    await screen.findByRole('button', { name: '09:30' });

    fireEvent.click(screen.getByRole('button', { name: '09:30' }));

    await waitFor(() => {
      expect(screen.getByRole('link', { name: 'Continuar' })).toHaveAttribute('href', '/reservar');
    });
  });
});
