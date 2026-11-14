import { describe, expect, it } from 'vitest';
import { codigoDeError, problemaDeError } from './problema';

function errorCon(data: unknown): unknown {
  return { response: { status: 409, data } };
}

describe('problemaDeError', () => {
  it('devuelve null cuando el error no trae cuerpo problem+json', () => {
    expect(problemaDeError(null)).toBeNull();
    expect(problemaDeError('boom')).toBeNull();
    expect(problemaDeError({})).toBeNull();
    expect(problemaDeError({ response: {} })).toBeNull();
    expect(problemaDeError({ response: { data: { codigo: 'solape' } } })).toBeNull();
  });

  it('extrae status, detail, codigo y bloqueado_hasta', () => {
    const problema = problemaDeError(
      errorCon({
        status: 403,
        detail: 'Paciente bloqueado',
        codigo: 'bloqueado',
        bloqueado_hasta: '2026-12-12T09:00:00-03:00',
      }),
    );

    expect(problema).toEqual({
      status: 403,
      detail: 'Paciente bloqueado',
      codigo: 'bloqueado',
      bloqueado_hasta: '2026-12-12T09:00:00-03:00',
    });
  });

  it('ignora un codigo que no es string', () => {
    const problema = problemaDeError(errorCon({ status: 409, detail: 'Solape', codigo: 7 }));

    expect(problema?.codigo).toBeUndefined();
  });
});

describe('codigoDeError', () => {
  it('devuelve el codigo estable o null', () => {
    expect(codigoDeError(errorCon({ status: 409, detail: 'Solape', codigo: 'solape' }))).toBe(
      'solape',
    );
    expect(codigoDeError(errorCon({ status: 500, detail: 'Error' }))).toBeNull();
    expect(codigoDeError(new Error('network'))).toBeNull();
  });
});
