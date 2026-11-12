import { AxiosError, type AxiosAdapter, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { apiClient } from './api-client';
import { publicClient } from './public-client';

function adaptadorQueResponde(
  status: number,
  data: Record<string, unknown> = {},
): { adapter: AxiosAdapter; requestCapturado: () => InternalAxiosRequestConfig } {
  let ultimo: InternalAxiosRequestConfig | null = null;

  const adapter: AxiosAdapter = (config) => {
    ultimo = config;
    const respuesta: AxiosResponse = {
      data,
      status,
      statusText: status === 200 ? 'OK' : 'Forbidden',
      headers: {},
      config,
    };
    return Promise.resolve(respuesta);
  };

  return {
    adapter,
    requestCapturado: () => {
      if (!ultimo) {
        throw new Error('El adaptador no recibió ningún request');
      }
      return ultimo;
    },
  };
}

function adaptadorQueFalla(
  status: number,
  data: Record<string, unknown>,
): AxiosAdapter {
  return (config) => {
    const respuesta: AxiosResponse = {
      data,
      status,
      statusText: 'Forbidden',
      headers: { 'content-type': 'application/problem+json' },
      config,
    };
    return Promise.reject(
      new AxiosError('Request failed with status code 403', 'ERR_BAD_REQUEST', config, undefined, respuesta),
    );
  };
}

describe('publicClient', () => {
  let asignacionesDeHref: string[];

  beforeEach(() => {
    asignacionesDeHref = [];
    vi.stubGlobal('location', {
      pathname: '/gestionar/token-de-prueba',
      get href() {
        return 'http://localhost/gestionar/token-de-prueba';
      },
      set href(valor: string) {
        asignacionesDeHref.push(valor);
      },
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('no agrega Authorization aunque haya access_token en localStorage', async () => {
    vi.spyOn(localStorage, 'getItem').mockImplementation((clave: string) =>
      clave === 'access_token' ? 'jwt-del-panel' : null,
    );
    const { adapter, requestCapturado } = adaptadorQueResponde(200);

    await publicClient.get('/api/public/slots', { adapter });

    const request = requestCapturado();
    expect(request.headers.get('Authorization')).toBeUndefined();
    expect(request.headers.get('authorization')).toBeUndefined();
  });

  it('es una instancia distinta del cliente autenticado del panel', () => {
    expect(publicClient).not.toBe(apiClient);
  });

  it('un 403 del backend no dispara lógica de sesión ni redirección a /login', async () => {
    vi.spyOn(localStorage, 'getItem').mockImplementation((clave: string) =>
      clave === 'access_token' ? 'jwt-del-panel' : null,
    );
    const removeItem = vi.spyOn(localStorage, 'removeItem');
    const adapter = adaptadorQueFalla(403, {
      type: 'about:blank',
      title: 'Forbidden',
      status: 403,
      detail: 'El enlace de gestión no es válido',
      instance: '/api/public/gestion/[redactado]',
      codigo: 'token_invalido',
    });

    await expect(
      publicClient.get('/api/public/gestion/token-de-prueba', { adapter }),
    ).rejects.toMatchObject({
      response: { status: 403, data: { codigo: 'token_invalido' } },
    });

    expect(removeItem).not.toHaveBeenCalled();
    expect(asignacionesDeHref).toEqual([]);
    expect(localStorage.getItem('access_token')).toBe('jwt-del-panel');
  });
});
