/**
 * Acceso interno a la agenda, el catálogo del alta y la creación de turnos.
 *
 * Usa el `api-client` autenticado: el interceptor agrega el Bearer y redirige a
 * `/login` en un 401. El canal público no se toca (C-06 sigue con
 * `public-client`).
 */

import { apiClient } from '@/shared/api-client';
import type {
  AgendaResponse,
  AltaTurnoInput,
  FiltrosAgenda,
  Odontologo,
  PacienteBusqueda,
  PracticaInterna,
  Sillon,
  TurnoInterno,
} from './types';

/** `GET /api/internal/agenda` — turnos del día o de la semana. */
export async function fetchAgenda(filtros: FiltrosAgenda): Promise<AgendaResponse> {
  const params: Record<string, string> = {
    vista: filtros.vista,
    fecha: filtros.fecha,
  };
  if (filtros.sillonId) {
    params['sillon'] = filtros.sillonId;
  }
  if (filtros.odontologoId) {
    params['odontologo'] = filtros.odontologoId;
  }
  if (filtros.estado) {
    params['estado'] = filtros.estado;
  }

  const { data } = await apiClient.get<AgendaResponse>('/api/internal/agenda', { params });
  return data;
}

/** `GET /api/internal/odontologos` — filtros del alta y de la agenda. */
export async function fetchOdontologos(): Promise<Odontologo[]> {
  const { data } = await apiClient.get<Odontologo[]>('/api/internal/odontologos');
  return data;
}

/** `GET /api/internal/sillones` — columnas de la grilla y alta. */
export async function fetchSillones(): Promise<Sillon[]> {
  const { data } = await apiClient.get<Sillon[]>('/api/internal/sillones');
  return data;
}

/** `GET /api/internal/tipos-practica` — prácticas activas para el alta. */
export async function fetchPracticas(): Promise<PracticaInterna[]> {
  const { data } = await apiClient.get<PracticaInterna[]>('/api/internal/tipos-practica');
  return data;
}

/**
 * `GET /api/internal/pacientes?q=` — búsqueda acotada a la clínica.
 * No se llama con menos de 2 caracteres: el backend responde 422 y el selector
 * no debe disparar errores mientras la persona escribe.
 */
export async function buscarPacientes(q: string): Promise<PacienteBusqueda[]> {
  const termino = q.trim();
  if (termino.length < 2) {
    return [];
  }
  const { data } = await apiClient.get<PacienteBusqueda[]>('/api/internal/pacientes', {
    params: { q: termino },
  });
  return data;
}

/** `POST /api/internal/turnos` — alta interna con excepción opcional. */
export async function crearTurnoInterno(input: AltaTurnoInput): Promise<TurnoInterno> {
  const body: AltaTurnoInput = {
    paciente_id: input.paciente_id,
    sillon_id: input.sillon_id,
    odontologo_id: input.odontologo_id,
    tipo_practica_id: input.tipo_practica_id,
    inicio: input.inicio,
  };
  if (input.motivo_excepcion !== undefined) {
    body.motivo_excepcion = input.motivo_excepcion;
  }

  const { data } = await apiClient.post<TurnoInterno>('/api/internal/turnos', body);
  return data;
}
