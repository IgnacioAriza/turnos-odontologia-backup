/**
 * Header del canal público (C-06).
 *
 * El mockup aprobado muestra solo el logo y los enlaces públicos: un paciente
 * con el enlace de gestión no debe ver "Iniciar sesión", porque el enlace por
 * token es su única credencial. El acceso interno sigue existiendo en `/login`
 * por URL directa.
 */

import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import PublicLayout from './PublicLayout';

function renderLayout() {
  return render(
    <MemoryRouter>
      <PublicLayout>
        <p>contenido</p>
      </PublicLayout>
    </MemoryRouter>,
  );
}

describe('PublicLayout', () => {
  it('muestra los enlaces públicos y ninguno de inicio de sesión', () => {
    renderLayout();

    expect(screen.getByRole('link', { name: 'Inicio' })).toHaveAttribute('href', '/');
    expect(screen.getByRole('link', { name: 'Reservar turno' })).toHaveAttribute(
      'href',
      '/reservar',
    );
    expect(screen.queryByRole('link', { name: /iniciar sesión/i })).not.toBeInTheDocument();
  });

  it('renderiza el contenido de la página dentro del layout', () => {
    renderLayout();

    expect(screen.getByText('contenido')).toBeInTheDocument();
  });
});
