/**
 * Formato de la agenda interna.
 *
 * El backend entrega `inicio` ya convertido a la zona de la clínica, así que la
 * hora visible es el literal ISO (`2026-11-12T09:00:00-03:00` → `09:00`). Usar
 * `new Date()` acá mostraría la hora del navegador y rompería la grilla.
 */

import type { EstadoTurno } from './types';

/**
 * Argentina no aplica horario de verano: el offset de la clínica es fijo.
 * El backend interpreta el `inicio` en su propia zona; mandar el offset
 * explícito evita depender de la zona del navegador.
 */
const OFFSET_CLINICA = '-03:00';

/** Combinar `YYYY-MM-DD` + `HH:mm` en un ISO con offset de la clínica. */
export function inicioIso(fecha: string, hora: string): string {
  return `${fecha}T${hora}:00${OFFSET_CLINICA}`;
}

const DIAS = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'] as const;

const ETIQUETAS_ESTADO: Record<EstadoTurno, string> = {
  pendiente_sena: 'Pendiente de seña',
  confirmado: 'Confirmado',
  cancelado: 'Cancelado',
  reprogramado: 'Reprogramado',
  completado: 'Atendido',
  ausente: 'Ausente',
};

/** `2026-11-12T09:00:00-03:00` → `09:00`. */
export function horaDe(inicio: string): string {
  return inicio.length >= 16 ? inicio.slice(11, 16) : '';
}

/** `2026-11-12T09:00:00-03:00` → `2026-11-12`. */
export function fechaDe(inicio: string): string {
  return inicio.slice(0, 10);
}

/** `2026-12-12T09:00:00-03:00` → `12/12/2026`. */
export function formatearFecha(iso: string): string {
  return `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;
}

/** Etiqueta legible del estado, para badges que no dependen solo del color. */
export function etiquetaEstado(estado: EstadoTurno): string {
  return ETIQUETAS_ESTADO[estado];
}

/** Sufijo de clase CSS por estado. */
export function claseEstado(estado: EstadoTurno): string {
  return estado;
}

/**
 * Los siete días (lunes a domingo) de la semana que contiene `fecha`.
 * Se calcula en UTC para que el resultado no dependa de la zona del navegador.
 */
export function semanaDe(fecha: string): string[] {
  const base = new Date(`${fecha}T00:00:00Z`);
  const dia = base.getUTCDay();
  const desplazamiento = dia === 0 ? -6 : 1 - dia;
  const lunes = base.getTime() + desplazamiento * 86_400_000;

  return Array.from({ length: 7 }, (_, indice) =>
    new Date(lunes + indice * 86_400_000).toISOString().slice(0, 10),
  );
}

/** `2026-11-12` → `Jue 12`. */
export function etiquetaDia(fecha: string): string {
  const base = new Date(`${fecha}T00:00:00Z`);
  const dia = DIAS[base.getUTCDay()] ?? '';
  return `${dia} ${Number(fecha.slice(8, 10))}`;
}
