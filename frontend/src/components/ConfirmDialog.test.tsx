/**
 * `ConfirmDialog` accesible (C-06 task 10.4).
 *
 * El foco arranca en la acción segura, `Escape` cierra, el tabulador queda
 * atrapado dentro del diálogo y al cerrar el foco vuelve al disparador.
 */

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { ConfirmDialog } from './ConfirmDialog';

function Harness({ onConfirmar }: { onConfirmar?: () => void }) {
  const [abierto, setAbierto] = useState(false);
  return (
    <div>
      <button type="button" onClick={() => setAbierto(true)}>
        Abrir aviso
      </button>
      {abierto && (
        <ConfirmDialog
          titulo="Cancelar dentro de las 12 horas hace perder la seña"
          descripcion="Si cancelás ahora, la seña no se devuelve."
          confirmarLabel="Cancelar y perder la seña"
          onConfirmar={() => {
            onConfirmar?.();
            setAbierto(false);
          }}
          onCerrar={() => setAbierto(false)}
        />
      )}
    </div>
  );
}

describe('ConfirmDialog', () => {
  it('pone el foco inicial en la acción segura y expone el diálogo', () => {
    render(<Harness />);

    fireEvent.click(screen.getByRole('button', { name: 'Abrir aviso' }));

    const dialogo = screen.getByRole('dialog');
    expect(dialogo).toHaveAttribute('aria-modal', 'true');
    expect(dialogo).toHaveAccessibleName('Cancelar dentro de las 12 horas hace perder la seña');
    expect(screen.getByRole('button', { name: 'Volver' })).toHaveFocus();
  });

  it('cierra con Escape y devuelve el foco al disparador', async () => {
    render(<Harness />);
    const disparador = screen.getByRole('button', { name: 'Abrir aviso' });

    disparador.focus();
    fireEvent.click(disparador);
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });

    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(disparador).toHaveFocus();
  });

  it('atrapa el tabulador dentro del diálogo', () => {
    render(<Harness />);
    fireEvent.click(screen.getByRole('button', { name: 'Abrir aviso' }));

    const volver = screen.getByRole('button', { name: 'Volver' });
    const confirmar = screen.getByRole('button', { name: 'Cancelar y perder la seña' });

    confirmar.focus();
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Tab' });
    expect(volver).toHaveFocus();

    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Tab', shiftKey: true });
    expect(confirmar).toHaveFocus();
  });

  it('ejecuta la acción solo al confirmar', () => {
    const onConfirmar = vi.fn();
    render(<Harness onConfirmar={onConfirmar} />);
    fireEvent.click(screen.getByRole('button', { name: 'Abrir aviso' }));

    expect(onConfirmar).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar y perder la seña' }));

    expect(onConfirmar).toHaveBeenCalledTimes(1);
  });
});
