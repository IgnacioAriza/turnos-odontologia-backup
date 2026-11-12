/**
 * Entrega de la reserva al checkout de la seña (C-06 task 9.5).
 *
 * C-06 no cobra: solo respeta la URL que devuelva C-08 y, si no existe, deja el
 * turno pendiente de seña sin simular un pago aprobado.
 */

import { describe, expect, it } from 'vitest';
import { urlDeCheckout } from './checkout';
import type { ReservaPublica } from './types';

const reserva: ReservaPublica = {
  turno_id: 't1',
  manage_token: 'tok-123',
  inicio: '2026-11-12T12:30:00Z',
  fin: '2026-11-12T13:10:00Z',
  monto_sena: '9000.00',
  estado: 'pendiente_sena',
};

describe('urlDeCheckout', () => {
  it('devuelve la URL de pago cuando el backend la entrega', () => {
    expect(urlDeCheckout({ ...reserva, pago_url: 'https://mp.example/checkout/abc' })).toBe(
      'https://mp.example/checkout/abc',
    );
  });

  it('devuelve null cuando el cobro todavía no está disponible', () => {
    expect(urlDeCheckout(reserva)).toBeNull();
  });

  it('ignora una URL vacía', () => {
    expect(urlDeCheckout({ ...reserva, pago_url: '' })).toBeNull();
  });
});
