/**
 * Helpers de formato del canal público (C-06).
 *
 * Todo lo que se muestra al paciente pasa por acá: la zona de la clínica es
 * `America/Argentina/Buenos_Aires` sin importar el reloj del dispositivo, y los
 * montos viajan como string decimal desde el backend.
 */

const ZONA_CLINICA = 'America/Argentina/Buenos_Aires';

/** Hora local de la clínica en formato 24h (`09:30`). */
export function formatearHora(iso: string): string {
  return new Date(iso).toLocaleTimeString('es-AR', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: ZONA_CLINICA,
  });
}

/** Fecha local de la clínica como `jueves 12/11`. */
export function formatearFecha(fecha: string): string {
  const [anio, mes, dia] = fecha.split('-').map(Number);
  if (!anio || !mes || !dia) {
    return fecha;
  }
  const diaSemana = new Date(Date.UTC(anio, mes - 1, dia, 12)).toLocaleDateString('es-AR', {
    weekday: 'long',
    timeZone: ZONA_CLINICA,
  });
  const diaMes = `${String(dia).padStart(2, '0')}/${String(mes).padStart(2, '0')}`;
  return `${diaSemana} ${diaMes}`;
}

/** Monto decimal del backend (`"9000.00"`) como pesos (`$ 9.000`). */
export function formatearMonto(monto: string): string {
  const valor = Number(monto);
  if (!Number.isFinite(valor)) {
    return monto;
  }
  return `$ ${valor.toLocaleString('es-AR', { maximumFractionDigits: 2 })}`;
}

/** Fecha de hoy en la zona de la clínica, para el `input[type=date]`. */
export function hoyISO(): string {
  return new Intl.DateTimeFormat('en-CA', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    timeZone: ZONA_CLINICA,
  }).format(new Date());
}

/** Día local de la clínica de un instante ISO (`YYYY-MM-DD`). */
export function fechaLocalDe(iso: string): string {
  return new Intl.DateTimeFormat('en-CA', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    timeZone: ZONA_CLINICA,
  }).format(new Date(iso));
}
