import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import MarcarEstadoDialog from './MarcarEstadoDialog';
import { marcarTurno } from '../api';
import type { PanelTurno } from '../types';

vi.mock('../api', () => ({
  marcarTurno: vi.fn(),
}));

const marcarMock = vi.mocked(marcarTurno);

function turno(overrides: Partial<PanelTurno> = {}): PanelTurno {
  return {
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
    ...overrides,
  };
}

function problema(status: number, codigo: string) {
  return { response: { status, data: { status, detail: 'detalle', codigo } } };
}

function renderDialog(overrides: Partial<Parameters<typeof MarcarEstadoDialog>[0]> = {}) {
  const onMarcado = vi.fn();
  const onCerrar = vi.fn();
  const onRefrescar = vi.fn();
  render(
    <MarcarEstadoDialog
      turno={turno()}
      destino="ausente"
      onMarcado={onMarcado}
      onCerrar={onCerrar}
      onRefrescar={onRefrescar}
      {...overrides}
    />,
  );
  return { onMarcado, onCerrar, onRefrescar };
}

describe('MarcarEstadoDialog', () => {
  beforeEach(() => {
    marcarMock.mockReset();
  });

  it('avisa que la segunda falta bloquea 30 días', () => {
    renderDialog({
      turno: turno({
        paciente: {
          id: 'p1',
          nombre: 'Juana Pérez',
          telefono: '+5491140000001',
          faltas_count: 1,
          bloqueado_hasta: null,
        },
      }),
    });

    expect(screen.getByRole('note')).toHaveTextContent(
      'Esta es la segunda falta: el paciente queda bloqueado 30 días',
    );
  });

  it('confirma la ausencia y devuelve el turno actualizado', async () => {
    const actualizado = turno({ estado: 'ausente' });
    marcarMock.mockResolvedValue(actualizado);
    const { onMarcado } = renderDialog();

    fireEvent.click(screen.getByRole('button', { name: 'Confirmar ausencia' }));

    await waitFor(() => expect(onMarcado).toHaveBeenCalledWith(actualizado));
    expect(marcarMock).toHaveBeenCalledWith('t1', 'ausente');
  });

  it('ante 409 estado_no_actualizable refresca la jornada sin marcar', async () => {
    marcarMock.mockRejectedValue(problema(409, 'estado_no_actualizable'));
    const { onMarcado, onRefrescar } = renderDialog();

    fireEvent.click(screen.getByRole('button', { name: 'Confirmar ausencia' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'El turno cambió de estado. Actualizamos la jornada.',
    );
    expect(onRefrescar).toHaveBeenCalled();
    expect(onMarcado).not.toHaveBeenCalled();
  });

  it('muestra la idempotencia cuando ya está marcado con ese destino', () => {
    renderDialog({ turno: turno({ estado: 'ausente' }) });

    expect(screen.getByText('Ya está marcado como ausente: no se suma otra falta.')).toBeVisible();
    expect(screen.queryByRole('button', { name: 'Confirmar ausencia' })).not.toBeInTheDocument();
  });

  it('permite volver sin marcar nada', () => {
    const { onCerrar } = renderDialog();

    fireEvent.click(screen.getByRole('button', { name: 'Volver' }));

    expect(onCerrar).toHaveBeenCalled();
    expect(marcarMock).not.toHaveBeenCalled();
  });
});
