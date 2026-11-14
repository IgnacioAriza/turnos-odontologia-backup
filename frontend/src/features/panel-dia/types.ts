/**
 * Contratos del panel del día (C-07).
 *
 * Fuente de verdad: `backend/app/domain/turnos/schemas.py` (`PanelDiaOut`,
 * `PanelTurnoOut`, `ResumenPanelOut`, `MarcarTurnoIn`) y
 * `backend/app/domain/turnos/gestion.py` (`estado_sena`).
 *
 * Decisiones de contrato:
 * - `estado_sena` es un proxy derivado del turno hasta C-09; la UI lo trata
 *   como texto estable (`pendiente`, `aprobada`, `perdida`, `no_requerida`).
 * - `monto_sena` viaja como string decimal.
 * - `inicio`/`fin` llegan en la zona de la clínica; la hora visible es el
 *   literal ISO (`slice(11, 16)`).
 * - Solo `confirmado` es marcable; el backend responde 409
 *   `estado_no_actualizable` para el resto.
 */

import type { FechaHoraISO, EstadoTurno } from '../agenda/types';

export type { EstadoTurno, FechaHoraISO };

export const ESTADOS_SENA = ['pendiente', 'aprobada', 'perdida', 'no_requerida'] as const;

export type EstadoSena = (typeof ESTADOS_SENA)[number];

export type EstadoMarcable = 'completado' | 'ausente';

export interface PanelPaciente {
  id: string;
  nombre: string;
  telefono: string;
  faltas_count: number;
  bloqueado_hasta: FechaHoraISO | null;
}

export interface PanelPractica {
  id: string;
  nombre: string;
}

export interface PanelSillon {
  id: string;
  nombre: string;
}

export interface PanelOdontologo {
  id: string;
  email: string;
}

export interface PanelTurno {
  id: string;
  inicio: FechaHoraISO;
  fin: FechaHoraISO;
  estado: EstadoTurno;
  estado_sena: EstadoSena;
  monto_sena: string;
  paciente: PanelPaciente;
  practica: PanelPractica;
  sillon: PanelSillon;
  odontologo: PanelOdontologo;
}

export interface ResumenPanel {
  total: number;
  pendientes_sena: number;
  confirmados: number;
  completados: number;
  ausentes: number;
}

/** Respuesta de `GET /api/internal/panel/dia`. */
export interface PanelDia {
  fecha: string;
  turnos: PanelTurno[];
  resumen: ResumenPanel;
}

/** Cuerpo de `PATCH /api/internal/panel/turnos/{id}`. */
export interface MarcarTurnoInput {
  estado: EstadoMarcable;
}
