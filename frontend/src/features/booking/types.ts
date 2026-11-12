/**
 * Contratos del canal público de reservas y gestión.
 *
 * Fuente de verdad: `backend/app/domain/turnos/schemas.py` (C-05/C-06).
 *
 * Decisiones de contrato:
 * - `monto_sena` viaja como **string** decimal (`"2000.00"`), no como number.
 * - Los errores problem+json del backend usan el campo `codigo` (no `code`) y
 *   los 409 de confirmación agregan `perdida_sena`.
 * - Las fechas y horas son strings ISO-8601; `fecha` de slots es `YYYY-MM-DD`.
 */

/** Estados posibles de un turno, en el orden que declara el modelo del backend. */
export const ESTADOS_TURNO = [
  'pendiente_sena',
  'confirmado',
  'cancelado',
  'reprogramado',
  'completado',
  'ausente',
] as const;

export type EstadoTurno = (typeof ESTADOS_TURNO)[number];

/** Fecha local de la clínica en formato `YYYY-MM-DD`. */
export type FechaISO = string;

/** Fecha y hora ISO-8601 con offset de zona (la que serializa FastAPI). */
export type FechaHoraISO = string;

/** Hueco disponible; nunca incluye datos de pacientes. */
export interface SlotPublico {
  inicio: FechaHoraISO;
  fin: FechaHoraISO;
  sillon_id: string;
  odontologo_id: string;
}

/** Respuesta de `GET /api/public/slots?fecha=&practica=`. */
export interface SlotsResponse {
  fecha: FechaISO;
  practica_id: string;
  duracion_min: number;
  slots: SlotPublico[];
}

/** Cuerpo de `POST /api/public/reservas`. */
export interface ReservaPublicaInput {
  nombre: string;
  telefono: string;
  dni?: string | null;
  practica_id: string;
  inicio: FechaHoraISO;
}

/** Respuesta de `POST /api/public/reservas` (201). */
export interface ReservaPublica {
  turno_id: string;
  manage_token: string;
  inicio: FechaHoraISO;
  fin: FechaHoraISO;
  monto_sena: string;
  estado: EstadoTurno;
  /**
   * URL de pago de la seña. C-06 no la produce: la agrega C-08 y el frontend la
   * respeta si viene. Su ausencia es un estado válido (pago pendiente).
   */
  pago_url?: string | null;
}

/** Resumen de práctica que acompaña la vista pública de gestión. */
export interface PracticaResumen {
  id: string;
  nombre: string;
  duracion_min: number;
}

/**
 * Práctica del catálogo público (`GET /api/public/practicas`).
 * El backend no expone `precio_base` ni `clinic_id` en este canal.
 */
export interface PracticaPublica {
  id: string;
  nombre: string;
  duracion_min: number;
  sena_pct: number;
}

/** Respuesta de `GET /api/public/gestion/{token}` y de los POST de gestión. */
export interface GestionTurno {
  turno_id: string;
  estado: EstadoTurno;
  inicio: FechaHoraISO;
  fin: FechaHoraISO;
  practica: PracticaResumen;
  monto_sena: string;
  sena_perdida: boolean;
  reprogramaciones_count: number;
  reprogramaciones_restantes: number;
  dentro_de_ventana: boolean;
}

/**
 * Cuerpo de `POST /api/public/gestion/{token}/cancelar`.
 * Aunque el backend tiene default `false`, el frontend lo envía siempre de
 * forma explícita para que perder la seña nunca sea un efecto involuntario.
 */
export interface CancelarGestionInput {
  manage_token: string;
  confirmar_perdida_sena: boolean;
}

/** Cuerpo de `POST /api/public/gestion/{token}/reprogramar`. */
export interface ReprogramarGestionInput extends CancelarGestionInput {
  nuevo_inicio: FechaHoraISO;
}

/** Códigos estables de error del canal público (campo `codigo`). */
export const CODIGOS_ERROR_PUBLICO = [
  'token_invalido',
  'turno_no_encontrado',
  'estado_no_gestionable',
  'requiere_confirmacion',
  'requiere_nueva_sena',
  'solape',
  'slot_invalido',
  'rate_limited',
] as const;

export type CodigoErrorPublico = (typeof CODIGOS_ERROR_PUBLICO)[number];

/**
 * Cuerpo `application/problem+json` del backend.
 * Los 422 de validación no traen `codigo`; los 409 de confirmación traen
 * `perdida_sena`. El 429 informa el reintento por header `Retry-After`.
 */
export interface ProblemDetailsPublico {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance: string;
  codigo?: CodigoErrorPublico;
  perdida_sena?: boolean;
}
