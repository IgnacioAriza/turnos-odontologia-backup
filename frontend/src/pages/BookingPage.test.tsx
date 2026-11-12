/**
 * Formulario de reserva `/reservar` (C-06 tasks 9.3, 9.4 y 9.5).
 *
 * El estado del horario llega por `location.state` desde la landing; el
 * formulario valida el teléfono argentino, conserva los datos ante un 409 y
 * entrega la reserva al checkout solo si hay URL de pago.
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import BookingPage from './BookingPage';
import { crearReserva, fetchSlots } from '@/features/booking/api';
import { redirigirACheckout, urlDeCheckout } from '@/features/booking/checkout';
import type { ReservaPublica, SlotsResponse } from '@/features/booking/types';

vi.mock('@/features/booking/api', () => ({
  crearReserva: vi.fn(),
  fetchSlots: vi.fn(),
}));

vi.mock('@/features/booking/checkout', () => ({
  urlDeCheckout: vi.fn(),
  redirigirACheckout: vi.fn(),
}));

const inicio = '2026-11-12T12:30:00Z';
const fin = '2026-11-12T13:10:00Z';

const estadoReserva = {
  practicaId: 'p1',
  practicaNombre: 'Limpieza dental',
  duracionMin: 40,
  senaPct: 30,
  fecha: '2026-11-12',
  inicio,
};

const reserva: ReservaPublica = {
  turno_id: 't1',
  manage_token: 'tok-123',
  inicio,
  fin,
  monto_sena: '9000.00',
  estado: 'pendiente_sena',
};

const slotsRefrescados: SlotsResponse = {
  fecha: '2026-11-12',
  practica_id: 'p1',
  duracion_min: 40,
  slots: [
    { inicio: '2026-11-12T13:30:00Z', fin: '2026-11-12T14:10:00Z', sillon_id: 's1', odontologo_id: 'o1' },
  ],
};

function renderReserva() {
  return render(
    <MemoryRouter initialEntries={[{ pathname: '/reservar', state: estadoReserva }]}>
      <BookingPage />
    </MemoryRouter>,
  );
}

function completar(nombre: string, telefono: string) {
  fireEvent.change(screen.getByLabelText('Nombre y apellido'), { target: { value: nombre } });
  fireEvent.change(screen.getByLabelText('WhatsApp'), { target: { value: telefono } });
}

describe('BookingPage', () => {
  beforeEach(() => {
    vi.mocked(crearReserva).mockReset();
    vi.mocked(fetchSlots).mockReset();
    vi.mocked(urlDeCheckout).mockReset();
    vi.mocked(redirigirACheckout).mockReset();
  });

  it('muestra el resumen del turno elegido', () => {
    renderReserva();

    expect(screen.getByText('Limpieza dental · 40 min')).toBeInTheDocument();
    expect(screen.getByText(/jueves 12\/11 · 09:30/i)).toBeInTheDocument();
    expect(screen.getByText('Seña (30 %)')).toBeInTheDocument();
  });

  it('bloquea el envío con el teléfono inválido y muestra el error en el campo', async () => {
    renderReserva();

    completar('Juana Pérez', '11 2345');

    expect(
      await screen.findByText(/Ingresá un número de 10 dígitos/i),
    ).toBeInTheDocument();
    const boton = screen.getByRole('button', { name: 'Confirmar turno' });
    expect(boton).toBeDisabled();
    fireEvent.click(boton);
    expect(crearReserva).not.toHaveBeenCalled();
  });

  it('envía el teléfono normalizado a E.164', async () => {
    vi.mocked(crearReserva).mockResolvedValue(reserva);
    vi.mocked(urlDeCheckout).mockReturnValue(null);

    renderReserva();
    completar('Juana Pérez', '11 5555 1234');
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar turno' }));

    await waitFor(() => {
      expect(crearReserva).toHaveBeenCalledWith({
        nombre: 'Juana Pérez',
        telefono: '+5491155551234',
        practica_id: 'p1',
        inicio,
      });
    });
  });

  it('muestra el turno pendiente de seña con su enlace de gestión', async () => {
    vi.mocked(crearReserva).mockResolvedValue(reserva);
    vi.mocked(urlDeCheckout).mockReturnValue(null);

    renderReserva();
    completar('Juana Pérez', '11 5555 1234');
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar turno' }));

    expect(await screen.findByText('Pendiente de seña')).toBeInTheDocument();
    expect(screen.getByText('$ 9.000')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Gestionar mi turno' })).toHaveAttribute(
      'href',
      '/gestionar/tok-123',
    );
    expect(redirigirACheckout).not.toHaveBeenCalled();
  });

  it('redirige al checkout cuando el backend entrega URL de pago', async () => {
    vi.mocked(crearReserva).mockResolvedValue(reserva);
    vi.mocked(urlDeCheckout).mockReturnValue('https://mp.example/checkout/abc');

    renderReserva();
    completar('Juana Pérez', '11 5555 1234');
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar turno' }));

    await waitFor(() => {
      expect(redirigirACheckout).toHaveBeenCalledWith('https://mp.example/checkout/abc');
    });
  });

  it('ante un 409 por solape refresca los horarios y conserva los datos', async () => {
    vi.mocked(crearReserva).mockRejectedValue({
      response: {
        status: 409,
        data: {
          type: 'about:blank',
          title: 'Conflict',
          status: 409,
          detail: 'El horario seleccionado ya no está disponible',
          instance: '/api/public/reservas',
          codigo: 'solape',
        },
      },
    });
    vi.mocked(fetchSlots).mockResolvedValue(slotsRefrescados);

    renderReserva();
    completar('Juana Pérez', '11 5555 1234');
    fireEvent.click(screen.getByRole('button', { name: 'Confirmar turno' }));

    const alerta = await screen.findByRole('alert');
    expect(alerta).toHaveTextContent('Ese horario se acaba de ocupar');
    expect(fetchSlots).toHaveBeenCalledWith({ practicaId: 'p1', fecha: '2026-11-12' });
    expect(screen.getByLabelText('Nombre y apellido')).toHaveValue('Juana Pérez');
    expect(screen.getByLabelText('WhatsApp')).toHaveValue('11 5555 1234');
    expect(await screen.findByRole('button', { name: '10:30' })).toBeInTheDocument();
  });
});
