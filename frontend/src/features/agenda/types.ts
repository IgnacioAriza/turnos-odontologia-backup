/**
 * Contratos internos de la agenda operativa y del alta de turnos (C-07).
 *
 * Fuente de verdad: `backend/app/domain/turnos/schemas.py` y
 * `backend/app/api/internal/agenda.py`.
 *
 * Decisiones de contrato:
 * - `inicio`/`fin` llegan ya convertidos a la zona de la clínica
 *   (`America/Argentina/Buenos_Aires`), con offset. La hora visible es el
 *   literal ISO (`slice(11, 16)`), no la del reloj del navegador.
 * - `monto_sena` viaja como string decimal, igual que en el canal público.
 * - Los errores problem+json usan `codigo` (`solape`, `bloqueado`,
 *   `motivo_requerido`, `estado_no_actualizable`, `turno_no_encontrado`).
 */

export type FechaISO = string;

/** Fecha y hora ISO-8601 con offset de zona (la que serializa FastAPI). */
export type FechaHoraISO = string;

export type VistaAgenda = 'dia' | 'semana';

export const ESTADOS_TURNO = [
  'pendiente_sena',
  'confirmado',
  'cancelado',
  'reprogramado',
  'completado',
  'ausente',
] as const;

export type EstadoTurno = (typeof ESTADOS_TURNO)[number];

export interface AgendaPaciente {
  id: string;
  nombre: string;
}

export interface AgendaPractica {
  id: string;
  nombre: string;
}

export interface AgendaSillon {
  id: string;
  nombre: string;
}

export interface AgendaOdontologo {
  id: string;
  email: string;
}

export interface AgendaTurno {
  id: string;
  inicio: FechaHoraISO;
  fin: FechaHoraISO;
  estado: EstadoTurno;
  paciente: AgendaPaciente;
  practica: AgendaPractica;
  sillon: AgendaSillon;
  odontologo: AgendaOdontologo;
}

/** Respuesta de `GET /api/internal/agenda`. */
export interface AgendaResponse {
  vista: VistaAgenda;
  desde: FechaHoraISO;
  hasta: FechaHoraISO;
  turnos: AgendaTurno[];
}

/** Filtros de la agenda; los vacíos se omiten de la query. */
export interface FiltrosAgenda {
  vista: VistaAgenda;
  fecha: FechaISO;
  sillonId?: string;
  odontologoId?: string;
  estado?: EstadoTurno;
}

/** Cambios parciales de filtros; `undefined` limpia el filtro. */
export type CambiosFiltros = {
  [K in keyof FiltrosAgenda]?: FiltrosAgenda[K] | undefined;
};

/** `GET /api/internal/odontologos`. */
export interface Odontologo {
  id: string;
  email: string;
}

/** `GET /api/internal/sillones` (solo los campos que usa la agenda). */
export interface Sillon {
  id: string;
  nombre: string;
}

/** `GET /api/internal/tipos-practica` (solo los campos que usa el alta). */
export interface PracticaInterna {
  id: string;
  nombre: string;
  duracion_min: number;
}

/** `GET /api/internal/pacientes?q=` — paciente acotado para el selector. */
export interface PacienteBusqueda {
  id: string;
  nombre: string;
  telefono: string;
  dni: string | null;
}

/** Cuerpo de `POST /api/internal/turnos`. */
export interface AltaTurnoInput {
  paciente_id: string;
  sillon_id: string;
  odontologo_id: string;
  tipo_practica_id: string;
  inicio: FechaHoraISO;
  motivo_excepcion?: string;
}

/** Respuesta de `POST /api/internal/turnos` (201). */
export interface TurnoInterno {
  id: string;
  paciente_id: string;
  sillon_id: string;
  odontologo_id: string;
  tipo_practica_id: string;
  inicio: FechaHoraISO;
  fin: FechaHoraISO;
  estado: EstadoTurno;
  monto_sena: string;
  manage_token: string | null;
}

/** Códigos estables de error del canal interno (campo `codigo`). */
export const CODIGOS_ERROR_AGENDA = [
  'solape',
  'bloqueado',
  'motivo_requerido',
  'estado_no_actualizable',
  'turno_no_encontrado',
] as const;

export type CodigoErrorAgenda = (typeof CODIGOS_ERROR_AGENDA)[number];
