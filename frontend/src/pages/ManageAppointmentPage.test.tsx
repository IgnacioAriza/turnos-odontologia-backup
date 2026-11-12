/**
 * Pantalla de gestión por token `/gestionar/:token` (C-06 tasks 10.1–10.4).
 *
 * El enlace de WhatsApp es la única credencial del paciente: la vista nunca
 * manda a `/login` y las acciones destructivas piden confirmación explícita.
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ManageAppointmentPage from './ManageAppointmentPage';
import { cancelarTurno, fetchGestion, fetchSlots, reprogramarTurno } from '@/features/booking/api';
import type { GestionTurno, SlotsResponse } from '@/features/booking/types';

vi.mock('@/features/booking/api', () => ({
  fetchGestion: vi.fn(),
  cancelarTurno: vi.fn(),
  reprogramarTurno: vi.fn(),
  fetchSlots: vi.fn(),
}));

const turno: GestionTurno = {
  turno_id: 't1',
  estado: 'confirmado',
  inicio: '2026-11-12T12:30:00Z',
  fin: '2026-11-12T13:10:00Z',
  practica: { id: 'p1', nombre: 'Limpieza dental', duracion_min: 40 },
  monto_sena: '9000.00',
  sena_perdida: false,
  reprogramaciones_count: 0,
  reprogramaciones_restantes: 1,
  dentro_de_ventana: false,
};

const slots: SlotsResponse = {
  fecha: '2026-11-12',
  practica_id: 'p1',
  duracion_min: 40,
  slots: [
    {
      inicio: '2026-11-12T13:30:00Z',
      fin: '2026-11-12T14:10:00Z',
      sillon_id: 's1',
      odontologo_id: 'o1',
    },
  ],
};

const problem = (status: number, codigo: string, detail: string, extra = {}) => ({
  response: {
    status,
    data: {
      type: 'about:blank',
      title: status === 409 ? 'Conflict' : 'Forbidden',
      status,
      detail,
      instance: '/api/public/gestion/tok-123',
      codigo,
      ...extra,
    },
  },
});

function renderGestion() {
  const router = createMemoryRouter(
    [
      { path: '/gestionar/:token', element: <ManageAppointmentPage /> },
      { path: '/login', element: <p>Pantalla de login</p> },
    ],
    { initialEntries: ['/gestionar/tok-123'] },
  );
  render(<RouterProvider router={router} />);
  return router;
}

describe('ManageAppointmentPage', () => {
  beforeEach(() => {
    vi.mocked(fetchGestion).mockReset();
    vi.mocked(cancelarTurno).mockReset();
    vi.mocked(reprogramarTurno).mockReset();
    vi.mocked(fetchSlots).mockReset();
  });

  it('muestra fecha, práctica, estado de seña y reprogramaciones restantes', async () => {
    vi.mocked(fetchGestion).mockResolvedValue(turno);

    renderGestion();

    expect(await screen.findByText('Limpieza dental')).toBeInTheDocument();
    expect(screen.getByText(/jueves 12\/11 · 09:30 a 10:10/i)).toBeInTheDocument();
    expect(screen.getByText('Confirmado')).toBeInTheDocument();
    expect(screen.getByText('$ 9.000')).toBeInTheDocument();
    expect(screen.getByText(/queda 1 sin seña nueva/i)).toBeInTheDocument();
    expect(fetchGestion).toHaveBeenCalledWith('tok-123');
  });

  it('con token inválido muestra el enlace inválido y no navega a /login', async () => {
    vi.mocked(fetchGestion).mockRejectedValue(
      problem(403, 'token_invalido', 'El enlace de gestión no es válido'),
    );

    const router = renderGestion();

    expect(await screen.findByText(/El enlace de gestión no es válido/i)).toBeInTheDocument();
    expect(screen.getByText('token_invalido')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /iniciar sesión/i })).not.toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/gestionar/tok-123');
  });

  it('oculta las acciones cuando el turno ya está cancelado', async () => {
    vi.mocked(fetchGestion).mockResolvedValue({ ...turno, estado: 'cancelado', sena_perdida: true });

    renderGestion();

    expect(await screen.findByText('Cancelado')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Cancelar turno' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Reprogramar turno' })).not.toBeInTheDocument();
  });

  it('advierte la pérdida de seña y solo cancela al confirmar', async () => {
    vi.mocked(fetchGestion).mockResolvedValue({ ...turno, dentro_de_ventana: true });
    vi.mocked(cancelarTurno).mockRejectedValueOnce(
      problem(409, 'requiere_confirmacion', 'Cancelar dentro de las 12 horas hace perder la seña', {
        perdida_sena: true,
      }),
    );

    renderGestion();
    await screen.findByText('Limpieza dental');

    fireEvent.click(screen.getByRole('button', { name: 'Cancelar turno' }));

    const dialogo = await screen.findByRole('dialog');
    expect(dialogo).toHaveAccessibleName(/hace perder la seña/i);
    expect(screen.getByText(/no se devuelve/i)).toBeInTheDocument();
    expect(cancelarTurno).toHaveBeenCalledTimes(1);
    expect(cancelarTurno).toHaveBeenCalledWith('tok-123', {
      manage_token: 'tok-123',
      confirmar_perdida_sena: false,
    });
    expect(screen.getByText('Confirmado')).toBeInTheDocument();

    vi.mocked(cancelarTurno).mockResolvedValue({
      ...turno,
      estado: 'cancelado',
      sena_perdida: true,
      dentro_de_ventana: true,
    });
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar y perder la seña' }));

    await waitFor(() => expect(screen.getByText('Cancelado')).toBeInTheDocument());
    expect(cancelarTurno).toHaveBeenLastCalledWith('tok-123', {
      manage_token: 'tok-123',
      confirmar_perdida_sena: true,
    });
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('advierte la seña nueva en la segunda reprogramación', async () => {
    vi.mocked(fetchGestion).mockResolvedValue({
      ...turno,
      reprogramaciones_count: 1,
      reprogramaciones_restantes: 0,
    });
    vi.mocked(fetchSlots).mockResolvedValue(slots);
    vi.mocked(reprogramarTurno).mockRejectedValueOnce(
      problem(409, 'requiere_nueva_sena', 'La segunda reprogramación exige una seña nueva'),
    );

    renderGestion();
    await screen.findByText('Limpieza dental');

    fireEvent.click(screen.getByRole('button', { name: 'Reprogramar turno' }));
    fireEvent.click(await screen.findByRole('button', { name: '10:30' }));
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar cambio' }));

    const dialogo = await screen.findByRole('dialog');
    expect(dialogo).toHaveAccessibleName(/exige una seña nueva/i);
    expect(reprogramarTurno).toHaveBeenCalledWith('tok-123', {
      manage_token: 'tok-123',
      nuevo_inicio: '2026-11-12T13:30:00Z',
      confirmar_perdida_sena: false,
    });

    vi.mocked(reprogramarTurno).mockResolvedValue({
      ...turno,
      estado: 'pendiente_sena',
      inicio: '2026-11-12T13:30:00Z',
      fin: '2026-11-12T14:10:00Z',
      reprogramaciones_count: 1,
      reprogramaciones_restantes: 0,
    });
    fireEvent.click(screen.getByRole('button', { name: 'Aceptar y pagar seña nueva' }));

    expect(await screen.findByText('Pendiente de seña')).toBeInTheDocument();
    expect(reprogramarTurno).toHaveBeenLastCalledWith('tok-123', {
      manage_token: 'tok-123',
      nuevo_inicio: '2026-11-12T13:30:00Z',
      confirmar_perdida_sena: true,
    });
  });

  it('si el paciente desiste, el turno no cambia', async () => {
    vi.mocked(fetchGestion).mockResolvedValue({ ...turno, dentro_de_ventana: true });
    vi.mocked(cancelarTurno).mockRejectedValue(
      problem(409, 'requiere_confirmacion', 'Cancelar dentro de las 12 horas hace perder la seña', {
        perdida_sena: true,
      }),
    );

    renderGestion();
    await screen.findByText('Limpieza dental');

    fireEvent.click(screen.getByRole('button', { name: 'Cancelar turno' }));
    await screen.findByRole('dialog');
    fireEvent.click(screen.getByRole('button', { name: 'Volver' }));

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(screen.getByText('Confirmado')).toBeInTheDocument();
    expect(cancelarTurno).toHaveBeenCalledTimes(1);
  });
});
