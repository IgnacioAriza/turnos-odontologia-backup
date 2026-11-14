import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AltaTurnoDialog from './AltaTurnoDialog';
import { buscarPacientes, crearTurnoInterno } from '../api';
import type { TurnoInterno } from '../types';

vi.mock('../api', () => ({
  buscarPacientes: vi.fn(),
  crearTurnoInterno: vi.fn(),
}));

const buscarMock = vi.mocked(buscarPacientes);
const crearMock = vi.mocked(crearTurnoInterno);

const ODONTOLOGOS = [{ id: 'o1', email: 'dra.gomez@clinica.com' }];
const SILLONES = [{ id: 's1', nombre: 'Sillón 1' }];
const PRACTICAS = [{ id: 'pr1', nombre: 'Limpieza dental', duracion_min: 40 }];
const PACIENTE = {
  id: 'p1',
  nombre: 'Juana Pérez',
  telefono: '+5491140000001',
  dni: '30111222',
};

const TURNO: TurnoInterno = {
  id: 't1',
  paciente_id: 'p1',
  sillon_id: 's1',
  odontologo_id: 'o1',
  tipo_practica_id: 'pr1',
  inicio: '2026-11-12T09:30:00-03:00',
  fin: '2026-11-12T10:10:00-03:00',
  estado: 'confirmado',
  monto_sena: '2000.00',
  manage_token: null,
};

function problema(status: number, codigo: string, extra: Record<string, unknown> = {}) {
  return { response: { status, data: { status, detail: 'detalle', codigo, ...extra } } };
}

function renderDialog(overrides: Partial<Parameters<typeof AltaTurnoDialog>[0]> = {}) {
  const onCreado = vi.fn();
  const onCerrar = vi.fn();
  render(
    <AltaTurnoDialog
      fechaInicial="2026-11-12"
      odontologos={ODONTOLOGOS}
      sillones={SILLONES}
      practicas={PRACTICAS}
      puedeExceptuar
      onCreado={onCreado}
      onCerrar={onCerrar}
      {...overrides}
    />,
  );
  return { onCreado, onCerrar };
}

async function completarFormulario() {
  fireEvent.change(screen.getByLabelText('Buscar paciente'), { target: { value: 'juana' } });
  fireEvent.click(screen.getByRole('button', { name: 'Buscar' }));

  const resultado = await screen.findByRole('button', { name: /Juana Pérez/ });
  fireEvent.click(resultado);

  fireEvent.change(screen.getByLabelText('Práctica'), { target: { value: 'pr1' } });
  fireEvent.change(screen.getByLabelText('Sillón'), { target: { value: 's1' } });
  fireEvent.change(screen.getByLabelText('Odontólogo'), { target: { value: 'o1' } });
  fireEvent.change(screen.getByLabelText('Hora'), { target: { value: '09:30' } });
}

describe('AltaTurnoDialog', () => {
  beforeEach(() => {
    buscarMock.mockReset();
    crearMock.mockReset();
    buscarMock.mockResolvedValue([PACIENTE]);
  });

  it('crea el turno, cierra y avisa al padre', async () => {
    crearMock.mockResolvedValue(TURNO);
    const { onCreado } = renderDialog();

    await completarFormulario();
    fireEvent.click(screen.getByRole('button', { name: 'Crear turno' }));

    await waitFor(() => expect(onCreado).toHaveBeenCalledWith(TURNO));
    expect(crearMock).toHaveBeenCalledWith({
      paciente_id: 'p1',
      sillon_id: 's1',
      odontologo_id: 'o1',
      tipo_practica_id: 'pr1',
      inicio: '2026-11-12T09:30:00-03:00',
    });
  });

  it('ante 409 solape conserva los datos y no cierra', async () => {
    crearMock.mockRejectedValue(problema(409, 'solape'));
    const { onCreado } = renderDialog();

    await completarFormulario();
    fireEvent.click(screen.getByRole('button', { name: 'Crear turno' }));

    const alerta = await screen.findByRole('alert');
    expect(alerta).toHaveTextContent('Ese horario se acaba de ocupar');
    expect(screen.getByText('Paciente: Juana Pérez')).toBeInTheDocument();
    expect(screen.getByLabelText('Hora')).toHaveValue('09:30');
    expect(onCreado).not.toHaveBeenCalled();
  });

  it('ante 403 bloqueado muestra hasta cuándo y pide motivo', async () => {
    crearMock.mockRejectedValue(
      problema(403, 'bloqueado', { bloqueado_hasta: '2026-12-12T09:00:00-03:00' }),
    );
    renderDialog();

    await completarFormulario();
    fireEvent.click(screen.getByRole('button', { name: 'Crear turno' }));

    const alerta = await screen.findByRole('alert');
    expect(alerta).toHaveTextContent('Paciente bloqueado');
    expect(alerta).toHaveTextContent('12/12/2026');
    expect(screen.getByLabelText('Motivo de la excepción')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Crear con excepción' })).toBeInTheDocument();
  });

  it('reenvía el alta con el motivo de excepción', async () => {
    crearMock
      .mockRejectedValueOnce(
        problema(403, 'bloqueado', { bloqueado_hasta: '2026-12-12T09:00:00-03:00' }),
      )
      .mockResolvedValueOnce(TURNO);
    const { onCreado } = renderDialog();

    await completarFormulario();
    fireEvent.click(screen.getByRole('button', { name: 'Crear turno' }));

    const motivo = await screen.findByLabelText('Motivo de la excepción');
    fireEvent.change(motivo, { target: { value: 'Dolor agudo autorizado por la Dra. Gómez' } });
    fireEvent.click(screen.getByRole('button', { name: 'Crear con excepción' }));

    await waitFor(() => expect(onCreado).toHaveBeenCalledWith(TURNO));
    expect(crearMock).toHaveBeenLastCalledWith({
      paciente_id: 'p1',
      sillon_id: 's1',
      odontologo_id: 'o1',
      tipo_practica_id: 'pr1',
      inicio: '2026-11-12T09:30:00-03:00',
      motivo_excepcion: 'Dolor agudo autorizado por la Dra. Gómez',
    });
  });
});
