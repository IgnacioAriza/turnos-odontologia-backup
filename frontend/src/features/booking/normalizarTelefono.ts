/**
 * Normaliza un teléfono argentino al formato E.164 móvil (`+549` + 10 dígitos).
 *
 * Acepta separadores habituales (espacios, guiones, puntos, paréntesis), el
 * prefijo nacional `0`, el `+54` con o sin `9`, y devuelve el mismo resultado
 * para una entrada ya normalizada. Cualquier entrada que no represente un
 * número nacional de 10 dígitos devuelve `null`.
 */

const SOLO_FORMATO_VALIDO = /^\+?[\d\s().-]+$/;
const DIGITOS_NACIONALES = 10;
const PAIS_ARGENTINA = '54';
const PREFIJO_MOVIL = '9';

export function normalizarTelefonoAR(input: string): string | null {
  if (typeof input !== 'string') {
    return null;
  }

  const limpio = input.trim();
  if (limpio === '' || !SOLO_FORMATO_VALIDO.test(limpio)) {
    return null;
  }

  let digitos = limpio.replace(/\D/g, '');
  if (digitos === '') {
    return null;
  }

  if (limpio.startsWith('+')) {
    if (!digitos.startsWith(PAIS_ARGENTINA)) {
      return null;
    }
    digitos = digitos.slice(PAIS_ARGENTINA.length);
  } else if (
    digitos.startsWith(PAIS_ARGENTINA) &&
    (digitos.length === 12 || digitos.length === 13)
  ) {
    digitos = digitos.slice(PAIS_ARGENTINA.length);
  }

  if (digitos.startsWith('0')) {
    digitos = digitos.slice(1);
  }

  if (digitos.length === DIGITOS_NACIONALES + 1 && digitos.startsWith(PREFIJO_MOVIL)) {
    digitos = digitos.slice(1);
  }

  if (digitos.length !== DIGITOS_NACIONALES || digitos.startsWith('0')) {
    return null;
  }

  return `+${PAIS_ARGENTINA}${PREFIJO_MOVIL}${digitos}`;
}
