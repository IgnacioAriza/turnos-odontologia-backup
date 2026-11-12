/**
 * Lectura del problem+json público (C-06).
 *
 * Las pantallas deciden con el `codigo` estable, nunca con el texto del
 * `detail`: el copy puede cambiar sin romper el flujo.
 */

import { describe, expect, it } from 'vitest';
import { codigoDeErrorPublico, problemaDeErrorPublico } from './errores';

const problem = {
  type: 'about:blank',
  title: 'Conflict',
  status: 409,
  detail: 'El horario seleccionado ya no está disponible',
  instance: '/api/public/reservas',
  codigo: 'solape',
};

describe('problemaDeErrorPublico', () => {
  it('extrae el cuerpo problem+json de un error de axios', () => {
    expect(problemaDeErrorPublico({ response: { status: 409, data: problem } })).toEqual(problem);
  });

  it('devuelve null para un error de red sin respuesta', () => {
    expect(problemaDeErrorPublico(new Error('Network Error'))).toBeNull();
  });

  it('devuelve null si el cuerpo no es un problem+json', () => {
    expect(problemaDeErrorPublico({ response: { status: 500, data: '<html>' } })).toBeNull();
  });
});

describe('codigoDeErrorPublico', () => {
  it('devuelve el código estable cuando existe', () => {
    expect(codigoDeErrorPublico({ response: { status: 409, data: problem } })).toBe('solape');
  });

  it('devuelve null cuando el problem+json no trae código', () => {
    expect(
      codigoDeErrorPublico({ response: { status: 422, data: { ...problem, codigo: undefined } } }),
    ).toBeNull();
  });
});
