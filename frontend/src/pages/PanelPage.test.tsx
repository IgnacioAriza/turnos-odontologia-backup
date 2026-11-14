import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import PanelPage from './PanelPage';
import { fetchPanelDia } from '@/features/panel-dia/api';
import type { PanelDia } from '@/features/panel-dia/types';

vi.mock('@/features/panel-dia/api', () => ({
  fetchPanelDia: vi.fn(),
  marcarTurno: vi.fn(),
}));

vi.mock('@/features/auth/hooks/useAuth', () => ({
  useAuth: () => ({
    user: { id: 'u1', email: 'recepcion@clinica.com', role: 'recepcion', nombre: 'Recep' },
    isLoading: false,
  }),
}));

const PANEL: PanelDia = {
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

describe('PanelPage', () => {
  beforeEach(() => {
    vi.mocked(fetchPanelDia).mockReset();
  });

  it('carga la jornada y muestra el resumen y los turnos', async () => {
    vi.mocked(fetchPanelDia).mockResolvedValue(PANEL);

    render(<PanelPage />);

    expect(await screen.findByText('Juana Pérez')).toBeInTheDocument();
    expect(screen.getByTestId('resumen-panel')).toHaveTextContent('1 turno');
    expect(screen.getByTestId('resumen-panel')).toHaveTextContent('1 confirmado');
  });

  it('abre la confirmación de llegada sobre un turno confirmado', async () => {
    vi.mocked(fetchPanelDia).mockResolvedValue(PANEL);

    render(<PanelPage />);

    await screen.findByText('Juana Pérez');
    fireEvent.click(screen.getByRole('button', { name: 'Marcar llegada' }));

    expect(await screen.findByRole('dialog', { name: 'Marcar llegada' })).toBeInTheDocument();
  });

  it('muestra el error con reintento y vuelve a pedir la jornada', async () => {
    vi.mocked(fetchPanelDia).mockRejectedValueOnce(new Error('network'));
    vi.mocked(fetchPanelDia).mockResolvedValueOnce(PANEL);

    render(<PanelPage />);

    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo cargar el panel');
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }));

    await waitFor(() => expect(screen.getByText('Juana Pérez')).toBeInTheDocument());
    expect(vi.mocked(fetchPanelDia)).toHaveBeenCalledTimes(2);
  });

  it('recarga la jornada al cambiar la fecha', async () => {
    vi.mocked(fetchPanelDia).mockResolvedValue(PANEL);

    render(<PanelPage />);

    await screen.findByText('Juana Pérez');
    fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2026-11-13' } });

    await waitFor(() =>
      expect(vi.mocked(fetchPanelDia)).toHaveBeenLastCalledWith('2026-11-13'),
    );
  });
});
