/**
 * Regresión del guard público (C-06 11.1).
 *
 * Un usuario interno autenticado que abre `/` debe terminar en el panel de su
 * rol. El bug original mandaba a `/`, que es ruta pública: el guard volvía a
 * redirigir a `/` y la app quedaba en un ciclo de redirecciones.
 */

import { render, waitFor } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { rutas } from '@/router';
import '@testing-library/jest-dom';

const authState = vi.hoisted(() => ({ role: 'recepcion' as string, autenticado: true }));

vi.mock('@/features/auth/hooks/useAuth', () => ({
  useAuth: () => ({
    user: authState.autenticado
      ? { id: 'u1', email: 'staff@clinica.com', role: authState.role, nombre: 'Staff' }
      : null,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
    refreshToken: vi.fn(),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

function renderEn(ruta: string) {
  const router = createMemoryRouter(rutas, { initialEntries: [ruta] });
  render(<RouterProvider router={router} />);
  return router;
}

describe('PublicRoute', () => {
  it.each([
    ['recepcion', '/panel'],
    ['admin', '/admin'],
    ['odonto', '/agenda'],
  ])('un usuario %s autenticado que abre / termina en %s', async (role, destino) => {
    authState.autenticado = true;
    authState.role = role;

    const router = renderEn('/');

    await waitFor(() => expect(router.state.location.pathname).toBe(destino));
  });

  it('un visitante sin sesión sigue viendo la landing en /', async () => {
    authState.autenticado = false;

    const router = renderEn('/');

    await waitFor(() => expect(router.state.location.pathname).toBe('/'));
  });

  it('un usuario autenticado puede abrir un enlace de gestión por token', async () => {
    authState.autenticado = true;
    authState.role = 'recepcion';

    const router = renderEn('/gestionar/token-de-prueba');

    await waitFor(() => expect(router.state.location.pathname).toBe('/gestionar/token-de-prueba'));
  });
});
