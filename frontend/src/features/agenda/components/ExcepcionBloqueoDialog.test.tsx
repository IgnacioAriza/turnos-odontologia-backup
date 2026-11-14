import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import ExcepcionBloqueoDialog from './ExcepcionBloqueoDialog';

describe('ExcepcionBloqueoDialog', () => {
  it('muestra hasta cuándo dura el bloqueo', () => {
    render(
      <ExcepcionBloqueoDialog
        bloqueadoHasta="2026-12-12T09:00:00-03:00"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByRole('alert')).toHaveTextContent('12/12/2026');
  });

  it('exige un motivo antes de confirmar', () => {
    const onConfirm = vi.fn();
    render(
      <ExcepcionBloqueoDialog
        bloqueadoHasta="2026-12-12T09:00:00-03:00"
        onConfirm={onConfirm}
        onCancel={vi.fn()}
      />,
    );

    const confirmar = screen.getByRole('button', { name: 'Crear con excepción' });
    expect(confirmar).toBeDisabled();

    fireEvent.change(screen.getByLabelText('Motivo de la excepción'), {
      target: { value: '   ' },
    });
    expect(confirmar).toBeDisabled();

    fireEvent.change(screen.getByLabelText('Motivo de la excepción'), {
      target: { value: '  Dolor agudo  ' },
    });
    fireEvent.click(confirmar);

    expect(onConfirm).toHaveBeenCalledWith('Dolor agudo');
  });

  it('permite volver sin crear nada', () => {
    const onCancel = vi.fn();
    render(
      <ExcepcionBloqueoDialog
        bloqueadoHasta="2026-12-12T09:00:00-03:00"
        onConfirm={vi.fn()}
        onCancel={onCancel}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Volver' }));

    expect(onCancel).toHaveBeenCalled();
  });
});
