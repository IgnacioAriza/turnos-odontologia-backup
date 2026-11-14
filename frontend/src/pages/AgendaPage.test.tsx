import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AgendaPage from './AgendaPage';
import {
  fetchAgenda,
  fetchOdontologos,
  fetchPracticas,
  fetchSillones,
} from '@/features/agenda/api';
import { fetchPanelDia } from '@/features/panel-dia/api';
import type { AgendaResponse } from '@/features/agenda/types';
import type { PanelDia } from '@/features/panel-dia/types';

vi.mock('@/features/agenda/api', () => ({
  fetchAgenda: vi.fn(),
  fetchOdontologos: vi.fn(),
  fetchSillones: vi.fn(),
  fetchPracticas: vi.fn(),
  buscarPacientes: vi.fn(),
  crearTurnoInterno: vi.fn(),
}));

vi.mock('@/features/panel-dia/api', () => ({
  fetchPanelDia: vi.fn(),
  marcarTurno: vi.fn(),
}));

const usuario = { id: 'u1', email: 'recepcion@clinica.com', role: 'recepcion', nombre: 'Recep' };

vi.mock('@/features/auth/hooks/useAuth', () => ({
  useAuth: () => ({ user: usuario, isLoading: false }),
}));

const AGENDA: AgendaResponse = {
  vista: 'dia',
  desde: '2026-11-12T00:00:00-03:00',
  hasta: '2026-11-12T23:59:59-03:00',
  turnos: [
    {
      id: 't1',
      inicio: '2026-11-12T09:00:00-03:00',
      fin: '2026-11-12T09:40:00-03:00',
      estado: 'confirmado',
      paciente: { id: 'p1', nombre: 'Juana Pérez' },
      practica: { id: 'pr1', nombre: 'Limpieza dental' },
      sillon: { id: 's1', nombre: 'Sillón 1' },
      odontologo: { id: 'o1', email: 'dra.gomez@clinica.com' },
    },
  ],
};

const VACIA: AgendaResponse = { ...AGENDA, turnos: [] };

const PANEL_ODONTO: PanelDia = {
  fecha: '2026-11-12',
  turnos: [
    {
      id: 't1',
      inicio: '2026-11-12T09:00:00-03:00',
      fin: '2026-11-12T09:40:00-03:00',
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
    },
  ],
  resumen: {
    total: 1,
    pendientes_sena: 0,
    confirmados: 1,
    completados: 0,
    ausentes: 0,
  },
};

describe('AgendaPage', () => {
  beforeEach(() => {
    vi.mocked(fetchAgenda).mockReset();
    vi.mocked(fetchOdontologos).mockReset();
    vi.mocked(fetchSillones).mockReset();
    vi.mocked(fetchPracticas).mockReset();
    vi.mocked(fetchPanelDia).mockReset();

    usuario.role = 'recepcion';
    vi.mocked(fetchOdontologos).mockResolvedValue([{ id: 'o1', email: 'dra.gomez@clinica.com' }]);
    vi.mocked(fetchSillones).mockResolvedValue([{ id: 's1', nombre: 'Sillón 1' }]);
    vi.mocked(fetchPracticas).mockResolvedValue([
      { id: 'pr1', nombre: 'Limpieza dental', duracion_min: 40 },
    ]);
  });

  it('carga la agenda del día y muestra los turnos con su sillón', async () => {
    vi.mocked(fetchAgenda).mockResolvedValue(AGENDA);

    render(<AgendaPage />);

    expect(await screen.findByText('Juana Pérez')).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Sillón 1' })).toBeInTheDocument();
    expect(vi.mocked(fetchAgenda)).toHaveBeenCalledWith(
      expect.objectContaining({ vista: 'dia', fecha: expect.any(String) }),
    );
  });

  it('recepción puede dar de alta un turno interno', async () => {
    vi.mocked(fetchAgenda).mockResolvedValue(AGENDA);

    render(<AgendaPage />);

    await screen.findByText('Juana Pérez');
    fireEvent.click(screen.getByRole('button', { name: 'Nuevo turno' }));

    expect(await screen.findByRole('dialog', { name: 'Nuevo turno' })).toBeInTheDocument();
  });

  it('el odontólogo ve su propia jornada, con marcado y sin ABM', async () => {
    usuario.role = 'odonto';
    vi.mocked(fetchPanelDia).mockResolvedValue(PANEL_ODONTO);

    render(<AgendaPage />);

    expect(await screen.findByRole('heading', { name: 'Mi agenda' })).toBeInTheDocument();
    expect(await screen.findByText('Juana Pérez')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Marcar llegada' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Confirmar ausencia' })).toBeInTheDocument();

    expect(screen.queryByRole('button', { name: 'Nuevo turno' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Semana' })).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Odontólogo')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /cancelar/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /reprogramar/i })).not.toBeInTheDocument();
    expect(vi.mocked(fetchAgenda)).not.toHaveBeenCalled();
  });

  it('muestra el vacío del día', async () => {
    vi.mocked(fetchAgenda).mockResolvedValue(VACIA);

    render(<AgendaPage />);

    expect(await screen.findByText('No hay turnos para este día')).toBeInTheDocument();
  });

  it('muestra el error con reintento y vuelve a pedir la agenda', async () => {
    vi.mocked(fetchAgenda).mockRejectedValueOnce(new Error('network'));
    vi.mocked(fetchAgenda).mockResolvedValueOnce(AGENDA);

    render(<AgendaPage />);

    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo cargar la agenda');
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }));

    await waitFor(() => expect(screen.getByText('Juana Pérez')).toBeInTheDocument());
    expect(vi.mocked(fetchAgenda)).toHaveBeenCalledTimes(2);
  });

  it('cambia a la vista semanal y vuelve a pedir la agenda', async () => {
    vi.mocked(fetchAgenda).mockResolvedValue(AGENDA);

    render(<AgendaPage />);

    await screen.findByText('Juana Pérez');
    fireEvent.click(screen.getByRole('button', { name: 'Semana' }));

    await waitFor(() =>
      expect(vi.mocked(fetchAgenda)).toHaveBeenLastCalledWith(
        expect.objectContaining({ vista: 'semana' }),
      ),
    );
  });
});
