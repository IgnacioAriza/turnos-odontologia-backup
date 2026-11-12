/**
 * Acceso al canal público de reservas y gestión.
 *
 * Usa `public-client` (sin `Authorization`, sin interceptor de 401): un paciente
 * puede reservar desde una máquina con sesión interna abierta y un 403 de token
 * de gestión no debe cerrar esa sesión.
 */

import publicClient from '../../shared/api-client/public-client';
import type {
  CancelarGestionInput,
  FechaISO,
  GestionTurno,
  PracticaPublica,
  ReprogramarGestionInput,
  ReservaPublica,
  ReservaPublicaInput,
  SlotsResponse,
} from './types';

/** `GET /api/public/practicas` — catálogo reservable, sin precio. */
export async function fetchPracticas(): Promise<PracticaPublica[]> {
  const { data } = await publicClient.get<PracticaPublica[]>('/api/public/practicas');
  return data;
}

/** `GET /api/public/slots` — huecos libres de un día para una práctica. */
export async function fetchSlots({
  practicaId,
  fecha,
}: {
  practicaId: string;
  fecha: FechaISO;
}): Promise<SlotsResponse> {
  const { data } = await publicClient.get<SlotsResponse>('/api/public/slots', {
    params: { practica: practicaId, fecha },
  });
  return data;
}

/** `POST /api/public/reservas` — alta sin login; devuelve el `manage_token`. */
export async function crearReserva(input: ReservaPublicaInput): Promise<ReservaPublica> {
  const { data } = await publicClient.post<ReservaPublica>('/api/public/reservas', input);
  return data;
}

/** `GET /api/public/gestion/{token}` — vista del turno por enlace. */
export async function fetchGestion(token: string): Promise<GestionTurno> {
  const { data } = await publicClient.get<GestionTurno>(
    `/api/public/gestion/${encodeURIComponent(token)}`,
  );
  return data;
}

/** `POST /api/public/gestion/{token}/cancelar`. */
export async function cancelarTurno(
  token: string,
  input: CancelarGestionInput,
): Promise<GestionTurno> {
  const { data } = await publicClient.post<GestionTurno>(
    `/api/public/gestion/${encodeURIComponent(token)}/cancelar`,
    input,
  );
  return data;
}

/** `POST /api/public/gestion/{token}/reprogramar`. */
export async function reprogramarTurno(
  token: string,
  input: ReprogramarGestionInput,
): Promise<GestionTurno> {
  const { data } = await publicClient.post<GestionTurno>(
    `/api/public/gestion/${encodeURIComponent(token)}/reprogramar`,
    input,
  );
  return data;
}
