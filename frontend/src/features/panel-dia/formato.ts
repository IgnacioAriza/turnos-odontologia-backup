/**
 * Formato del panel del día (C-07).
 *
 * `inicio` llega en la zona de la clínica; la hora visible es el literal ISO,
 * nunca la del navegador.
 */

import type { EstadoSena } from './types';

const ETIQUETAS_SENA: Record<EstadoSena, string> = {
  pendiente: 'Seña pendiente',
  aprobada: 'Seña aprobada',
  perdida: 'Seña perdida',
  no_requerida: 'Sin seña',
};

/** Etiqueta textual de la seña: el badge no depende solo del color. */
export function etiquetaSena(estado: EstadoSena): string {
  return ETIQUETAS_SENA[estado];
}

/** Sufijo de clase CSS por estado de seña. */
export function claseSena(estado: EstadoSena): string {
  return estado;
}

/**
 * Teléfono en formato internacional sin símbolos, como lo espera `wa.me`.
 * `+54 9 11 4000-0001` → `5491140000001`.
 */
export function telefonoWhatsApp(telefono: string): string {
  return telefono.replace(/\D/g, '');
}

/** Enlace de WhatsApp con el saludo del consultorio prellenado. */
export function enlaceWhatsApp(telefono: string, nombre: string): string {
  const numero = telefonoWhatsApp(telefono);
  const texto = encodeURIComponent(
    `Hola ${nombre}, te escribimos del consultorio por tu turno de hoy.`,
  );
  return `https://wa.me/${numero}?text=${texto}`;
}
