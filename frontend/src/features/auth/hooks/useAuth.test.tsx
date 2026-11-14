import { act, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthProvider, normalizarUsuario, useAuth } from './useAuth';
import { apiClient } from '@/shared/api-client';

vi.mock('@/shared/api-client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn() },
  default: {},
}));

const getMock = vi.mocked(apiClient.get);
const postMock = vi.mocked(apiClient.post);

function almacenamiento(): Storage {
  const datos = new Map<string, string>();
  return {
    getItem: (clave: string) => datos.get(clave) ?? null,
    setItem: (clave: string, valor: string) => void datos.set(clave, valor),
    removeItem: (clave: string) => void datos.delete(clave),
    clear: () => datos.clear(),
    key: (indice: number) => [...datos.keys()][indice] ?? null,
    get length() {
      return datos.size;
    },
  };
}

function Sonda() {
  const { user, login, refreshToken } = useAuth();
  return (
    <div>
      <span data-testid="rol">{user?.role ?? 'sin sesión'}</span>
      <button
        type="button"
        onClick={() => {
          void login('recepcion@clinica.com', 'secreto').catch(() => {});
        }}
      >
        login
      </button>
      <button type="button" onClick={() => void refreshToken()}>
        refresh
      </button>
    </div>
  );
}

describe('normalizarUsuario', () => {
  it('mapea el campo `rol` del backend al `role` del frontend', () => {
    expect(
      normalizarUsuario({ id: 'u1', email: 'recepcion@clinica.com', rol: 'recepcion' }),
    ).toEqual({
      id: 'u1',
      email: 'recepcion@clinica.com',
      role: 'recepcion',
      nombre: 'recepcion',
    });
  });
});

describe('useAuth contra el contrato real del backend', () => {
  beforeEach(() => {
    getMock.mockReset();
    postMock.mockReset();
    Object.defineProperty(window, 'localStorage', {
      value: almacenamiento(),
      writable: true,
    });
  });

  it('después del login pide /me y expone el rol', async () => {
    postMock.mockResolvedValue({
      data: { access_token: 'acc', refresh_token: 'ref', token_type: 'bearer', expires_in: 1800 },
    });
    getMock.mockResolvedValue({
      data: { id: 'u1', email: 'recepcion@clinica.com', rol: 'recepcion' },
    });

    render(
      <AuthProvider>
        <Sonda />
      </AuthProvider>,
    );

    await act(async () => {
      screen.getByRole('button', { name: 'login' }).click();
    });

    expect(await screen.findByText('recepcion')).toBeInTheDocument();
    expect(getMock).toHaveBeenCalledWith('/api/auth/me');
    expect(window.localStorage.getItem('access_token')).toBe('acc');
  });

  it('al refrescar vuelve a pedir /me para recuperar el rol', async () => {
    window.localStorage.setItem('refresh_token', 'ref');
    postMock.mockResolvedValue({
      data: { access_token: 'acc2', refresh_token: 'ref2', token_type: 'bearer', expires_in: 1800 },
    });
    getMock.mockResolvedValue({
      data: { id: 'u2', email: 'odonto@clinica.com', rol: 'odonto' },
    });

    render(
      <AuthProvider>
        <Sonda />
      </AuthProvider>,
    );

    await act(async () => {
      screen.getByRole('button', { name: 'refresh' }).click();
    });

    expect(await screen.findByText('odonto')).toBeInTheDocument();
  });

  it('si /me falla después del login, cierra la sesión', async () => {
    postMock.mockResolvedValue({
      data: { access_token: 'acc', refresh_token: 'ref', token_type: 'bearer', expires_in: 1800 },
    });
    getMock.mockRejectedValue(new Error('500'));

    render(
      <AuthProvider>
        <Sonda />
      </AuthProvider>,
    );

    await act(async () => {
      screen.getByRole('button', { name: 'login' }).click();
    });

    expect(await screen.findByText('sin sesión')).toBeInTheDocument();
    expect(window.localStorage.getItem('access_token')).toBeNull();
  });
});
