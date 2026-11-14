/**
 * Lectura del problem+json interno (C-07).
 *
 * Las pantallas deciden con el `codigo` estable (`solape`, `bloqueado`,
 * `motivo_requerido`, `estado_no_actualizable`, `turno_no_encontrado`), nunca
 * con el texto del `detail`.
 */

export interface ProblemDetails {
  status: number;
  detail: string;
  codigo?: string;
  bloqueado_hasta?: string;
}

function esObjeto(valor: unknown): valor is Record<string, unknown> {
  return typeof valor === 'object' && valor !== null;
}

/** Cuerpo problem+json del backend, o `null` si el error no trae uno. */
export function problemaDeError(error: unknown): ProblemDetails | null {
  if (!esObjeto(error) || !esObjeto(error['response'])) {
    return null;
  }

  const data = error['response']['data'];
  if (!esObjeto(data) || typeof data['status'] !== 'number' || typeof data['detail'] !== 'string') {
    return null;
  }

  const problema: ProblemDetails = {
    status: data['status'],
    detail: data['detail'],
  };

  if (typeof data['codigo'] === 'string') {
    problema.codigo = data['codigo'];
  }
  if (typeof data['bloqueado_hasta'] === 'string') {
    problema.bloqueado_hasta = data['bloqueado_hasta'];
  }

  return problema;
}

/** Código estable del error (`solape`, `bloqueado`, …) o `null`. */
export function codigoDeError(error: unknown): string | null {
  return problemaDeError(error)?.codigo ?? null;
}
