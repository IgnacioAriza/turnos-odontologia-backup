/**
 * Acceso interno al panel del día y al marcado de llegadas/ausencias (C-07).
 *
 * Usa el `api-client` autenticado; un 401 lo maneja el interceptor global.
 */

import { apiClient } from '@/shared/api-client';
import type { EstadoMarcable, PanelDia, PanelTurno } from './types';

/** `GET /api/internal/panel/dia` — jornada operable; hoy por defecto. */
export async function fetchPanelDia(fecha?: string): Promise<PanelDia> {
  const { data } = await apiClient.get<PanelDia>('/api/internal/panel/dia', {
    params: fecha ? { fecha } : {},
  });
  return data;
}

/**
 * `PATCH /api/internal/panel/turnos/{id}` — marcar llegada o ausencia.
 * Es idempotente por destino: repetir la misma acción no duplica faltas.
 */
export async function marcarTurno(
  turnoId: string,
  estado: EstadoMarcable,
): Promise<PanelTurno> {
  const { data } = await apiClient.patch<PanelTurno>(`/api/internal/panel/turnos/${turnoId}`, {
    estado,
  });
  return data;
}
