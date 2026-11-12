/**
 * Helpers de formato del canal público (C-06).
 *
 * Todo lo que se muestra al paciente pasa por acá: la zona de la clínica es
 * `America/Argentina/Buenos_Aires` sin importar el reloj del dispositivo, y los
 * montos viajan como string decimal desde el backend.
 */

import { describe, expect, it } from 'vitest';
import {
  fechaLocalDe,
  formatearFecha,
  formatearHora,
  formatearMonto,
  hoyISO,
} from './formato';

describe('formatearHora', () => {
  it('muestra la hora local de la clínica, no la del dispositivo', () => {
    expect(formatearHora('2026-11-12T12:30:00Z')).toBe('09:30');
  });

  it('usa 24 horas también a la tarde', () => {
    expect(formatearHora('2026-11-12T21:05:00Z')).toBe('18:05');
  });
});

describe('formatearFecha', () => {
  it('muestra día de la semana y fecha corta', () => {
    expect(formatearFecha('2026-11-12')).toBe('jueves 12/11');
  });
});

describe('fechaLocalDe', () => {
  it('devuelve el día de la clínica, no el de UTC', () => {
    expect(fechaLocalDe('2026-11-12T12:30:00Z')).toBe('2026-11-12');
    expect(fechaLocalDe('2026-11-12T02:30:00Z')).toBe('2026-11-11');
  });
});

describe('formatearMonto', () => {
  it('convierte el string decimal del backend en pesos', () => {
    expect(formatearMonto('9000.00')).toBe('$ 9.000');
  });

  it('no inventa decimales en montos enteros', () => {
    expect(formatearMonto('12345.00')).toBe('$ 12.345');
  });
});

describe('hoyISO', () => {
  it('devuelve una fecha YYYY-MM-DD', () => {
    expect(hoyISO()).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
});
