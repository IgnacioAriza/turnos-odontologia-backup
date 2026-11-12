import { describe, expect, it } from 'vitest';
import { ESTADOS_TURNO } from './types';
import type {
  CancelarGestionInput,
  GestionTurno,
  ProblemDetailsPublico,
  ReprogramarGestionInput,
  ReservaPublica,
  ReservaPublicaInput,
  SlotsResponse,
} from './types';

// Fixtures con la forma que devuelve realmente el backend de C-05/C-06.
const slotsResponse: SlotsResponse = {
  fecha: '2026-11-12',
  practica_id: '7c9e6679-7425-40de-944b-e07fc1f90ae7',
  duracion_min: 30,
  slots: [
    {
      inicio: '2026-11-12T10:00:00-03:00',
      fin: '2026-11-12T10:30:00-03:00',
      sillon_id: '1c9e6679-7425-40de-944b-e07fc1f90ae7',
      odontologo_id: '2c9e6679-7425-40de-944b-e07fc1f90ae7',
    },
  ],
};

const reservaInput: ReservaPublicaInput = {
  nombre: 'Ana Pérez',
  telefono: '+5491155551234',
  practica_id: '7c9e6679-7425-40de-944b-e07fc1f90ae7',
  inicio: '2026-11-12T10:00:00-03:00',
};

const reserva: ReservaPublica = {
  turno_id: '3c9e6679-7425-40de-944b-e07fc1f90ae7',
  manage_token: 'token-opaco-de-gestion',
  inicio: '2026-11-12T10:00:00-03:00',
  fin: '2026-11-12T10:30:00-03:00',
  monto_sena: '2000.00',
  estado: 'pendiente_sena',
};

const gestion: GestionTurno = {
  turno_id: '3c9e6679-7425-40de-944b-e07fc1f90ae7',
  estado: 'confirmado',
  inicio: '2026-11-12T10:00:00-03:00',
  fin: '2026-11-12T10:30:00-03:00',
  practica: {
    id: '7c9e6679-7425-40de-944b-e07fc1f90ae7',
    nombre: 'Limpieza',
    duracion_min: 30,
  },
  monto_sena: '2000.00',
  sena_perdida: false,
  reprogramaciones_count: 0,
  reprogramaciones_restantes: 1,
  dentro_de_ventana: true,
};

const cancelar: CancelarGestionInput = {
  manage_token: 'token-opaco-de-gestion',
  confirmar_perdida_sena: false,
};

const reprogramar: ReprogramarGestionInput = {
  manage_token: 'token-opaco-de-gestion',
  confirmar_perdida_sena: true,
  nuevo_inicio: '2026-11-13T09:00:00-03:00',
};

const errorToken: ProblemDetailsPublico = {
  type: 'about:blank',
  title: 'Forbidden',
  status: 403,
  detail: 'El enlace de gestión no es válido',
  instance: '/api/public/gestion/[redactado]',
  codigo: 'token_invalido',
};

const errorConfirmacion: ProblemDetailsPublico = {
  type: 'about:blank',
  title: 'Conflict',
  status: 409,
  detail: 'La seña no se devuelve si cancelás dentro de las 12 horas previas',
  instance: '/api/public/gestion/[redactado]/cancelar',
  codigo: 'requiere_confirmacion',
  perdida_sena: true,
};

describe('contratos del canal público', () => {
  it('los estados de turno coinciden con los del backend', () => {
    expect(ESTADOS_TURNO).toHaveLength(6);
    expect(ESTADOS_TURNO).toContain(gestion.estado);
    expect(ESTADOS_TURNO).toContain(reserva.estado);
  });

  it('el slot conserva los identificadores de recurso y los rangos ISO', () => {
    expect(slotsResponse.slots).toHaveLength(1);
    const [slot] = slotsResponse.slots;
    expect(slot?.sillon_id).toBe('1c9e6679-7425-40de-944b-e07fc1f90ae7');
    expect(slot?.odontologo_id).toBe('2c9e6679-7425-40de-944b-e07fc1f90ae7');
    expect(slot?.inicio).toBe('2026-11-12T10:00:00-03:00');
    expect(slotsResponse.fecha).toBe('2026-11-12');
  });

  it('la reserva pública envía el teléfono normalizado y devuelve la seña como string', () => {
    expect(reservaInput.telefono).toBe('+5491155551234');
    expect(reserva.manage_token).not.toBe('');
    expect(typeof reserva.monto_sena).toBe('string');
    expect(reserva.estado).toBe('pendiente_sena');
  });

  it('la gestión expone la seña y las reprogramaciones restantes sin el token', () => {
    expect(gestion.sena_perdida).toBe(false);
    expect(gestion.reprogramaciones_restantes).toBe(1);
    expect(gestion.dentro_de_ventana).toBe(true);
    expect(Object.keys(gestion)).not.toContain('manage_token');
    expect(gestion.practica.nombre).toBe('Limpieza');
  });

  it('los POST de gestión llevan manage_token en el cuerpo', () => {
    expect(cancelar.manage_token).toBe('token-opaco-de-gestion');
    expect(reprogramar.nuevo_inicio).toBe('2026-11-13T09:00:00-03:00');
    expect(reprogramar.confirmar_perdida_sena).toBe(true);
  });

  it('el problem+json usa codigo estable y puede traer perdida_sena', () => {
    expect(errorToken.codigo).toBe('token_invalido');
    expect(errorToken.status).toBe(403);
    expect(errorConfirmacion.codigo).toBe('requiere_confirmacion');
    expect(errorConfirmacion.perdida_sena).toBe(true);
  });
});
