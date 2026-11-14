/**
 * Acceso por rol a la agenda operativa (C-07 7.6).
 *
 * Recepción entra a `/agenda` (además de `/panel`) porque el alta interna y la
 * agenda multi-sillón son parte de su trabajo; el odontólogo sigue sin acceso
 * al panel general.
 */

import { render, waitFor } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { rutas } from '@/router';
import '@testing-library/jest-dom';

const authState = vi.hoisted(() => ({ role: 'recepcion' as string }));

vi.mock('@/features/auth/hooks/useAuth', () => ({
  useAuth: () => ({
    user: { id: 'u1', email: 'staff@clinica.com', role: authState.role, nombre: 'Staff' },
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
    refreshToken: vi.fn(),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock('@/features/agenda/api', () => ({
  fetchAgenda: vi.fn().mockResolvedValue({
    vista: 'dia',
    desde: '2026-11-12T00:00:00-03:00',
    hasta: '2026-11-12T23:59:59-03:00',
    turnos: [],
  }),
  fetchOdontologos: vi.fn().mockResolvedValue([]),
  fetchSillones: vi.fn().mockResolvedValue([]),
  fetchPracticas: vi.fn().mockResolvedValue([]),
  buscarPacientes: vi.fn().mockResolvedValue([]),
  crearTurnoInterno: vi.fn(),
}));

function renderEn(ruta: string) {
  const router = createMemoryRouter(rutas, { initialEntries: [ruta] });
  render(<RouterProvider router={router} />);
  return router;
}

describe('Acceso a /agenda por rol', () => {
  it('recepción puede abrir la agenda', async () => {
    authState.role = 'recepcion';

    const router = renderEn('/agenda');

    await waitFor(() => expect(router.state.location.pathname).toBe('/agenda'));
  });

  it('el odontólogo que abre el panel general vuelve a su agenda', async () => {
    authState.role = 'odonto';

    const router = renderEn('/panel');

    await waitFor(() => expect(router.state.location.pathname).toBe('/agenda'));
  });
});
