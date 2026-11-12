/**
 * Lectura del problem+json público (C-06).
 *
 * Las pantallas deciden con el `codigo` estable, nunca con el texto del
 * `detail`: el copy puede cambiar sin romper el flujo.
 */

import type { CodigoErrorPublico, ProblemDetailsPublico } from './types';

/** Cuerpo problem+json del backend, o `null` si el error no trae uno. */
export function problemaDeErrorPublico(error: unknown): ProblemDetailsPublico | null {
  if (typeof error !== 'object' || error === null) {
    return null;
  }

  const response = (error as { response?: unknown }).response;
  if (typeof response !== 'object' || response === null) {
    return null;
  }

  const data = (response as { data?: unknown }).data;
  if (typeof data !== 'object' || data === null) {
    return null;
  }

  const body = data as Partial<ProblemDetailsPublico>;
  if (typeof body.status !== 'number' || typeof body.detail !== 'string') {
    return null;
  }

  return body as ProblemDetailsPublico;
}

/** Código estable del error (`solape`, `token_invalido`, …) o `null`. */
export function codigoDeErrorPublico(error: unknown): CodigoErrorPublico | null {
  return problemaDeErrorPublico(error)?.codigo ?? null;
}
