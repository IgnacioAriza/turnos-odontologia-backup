import axios, { type AxiosInstance } from 'axios';

/**
 * Cliente HTTP del canal público (pacientes).
 *
 * Deliberadamente NO reutiliza `api-client.ts`: no registra interceptores y no
 * lee `localStorage`, así que nunca agrega `Authorization` (un recepcionista
 * logueado en la misma máquina no reserva como paciente) y un `403` del token
 * de gestión no dispara el borrado de sesión ni la redirección a `/login`.
 */

const API_URL = import.meta.env['VITE_API_URL'] || 'http://localhost:8000';

export const publicClient: AxiosInstance = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

export default publicClient;
