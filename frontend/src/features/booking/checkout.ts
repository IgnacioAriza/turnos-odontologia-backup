/**
 * Entrega de la reserva al checkout de la seña (C-06 task 9.5).
 *
 * C-06 no cobra: solo respeta la URL que devuelva C-08 y, si no existe, deja el
 * turno pendiente de seña sin simular un pago aprobado.
 */

import type { ReservaPublica } from './types';

/** URL de pago del turno, o `null` si el cobro todavía no está disponible. */
export function urlDeCheckout(reserva: ReservaPublica): string | null {
  const url = reserva.pago_url;
  if (typeof url !== 'string') {
    return null;
  }
  const limpia = url.trim();
  return limpia === '' ? null : limpia;
}

/** Sale de la app hacia el checkout externo. */
export function redirigirACheckout(url: string): void {
  window.location.assign(url);
}
