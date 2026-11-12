import { describe, expect, it } from 'vitest';
import { normalizarTelefonoAR } from './normalizarTelefono';

describe('normalizarTelefonoAR', () => {
  it('normaliza un número nacional con espacios a E.164 argentino', () => {
    expect(normalizarTelefonoAR('11 5555 1234')).toBe('+5491155551234');
  });

  it('es idempotente cuando la entrada ya viene con +54 9', () => {
    const entrada = '+54 9 11 5555 1234';
    const primera = normalizarTelefonoAR(entrada);

    expect(primera).toBe('+5491155551234');
    expect(normalizarTelefonoAR(primera as string)).toBe(primera);
  });

  it('acepta el formato compacto +549... ya normalizado', () => {
    expect(normalizarTelefonoAR('+5491155551234')).toBe('+5491155551234');
  });

  it('agrega el 9 a un +54 sin 9 (formato tipo fijo)', () => {
    expect(normalizarTelefonoAR('+54 11 5555 1234')).toBe('+5491155551234');
  });

  it('quita el prefijo nacional 0 y los separadores', () => {
    expect(normalizarTelefonoAR('011 5555-1234')).toBe('+5491155551234');
    expect(normalizarTelefonoAR('(011) 5555.1234')).toBe('+5491155551234');
  });

  it('devuelve null para un número corto', () => {
    expect(normalizarTelefonoAR('11 5555 123')).toBeNull();
    expect(normalizarTelefonoAR('123')).toBeNull();
  });

  it('devuelve null para entrada vacía o sin dígitos', () => {
    expect(normalizarTelefonoAR('')).toBeNull();
    expect(normalizarTelefonoAR('   ')).toBeNull();
    expect(normalizarTelefonoAR('sin telefono')).toBeNull();
  });

  it('devuelve null para un número demasiado largo', () => {
    expect(normalizarTelefonoAR('11 5555 12345')).toBeNull();
    expect(normalizarTelefonoAR('+54 9 11 5555 12345')).toBeNull();
  });

  it('devuelve null para un prefijo internacional que no es argentino', () => {
    expect(normalizarTelefonoAR('+1 555 555 1234')).toBeNull();
  });
});
