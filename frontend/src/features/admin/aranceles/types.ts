export interface ArancelAdmin {
  tipo_practica_id: string;
  nombre: string;
  duracion_min: number;
  precio: number;
  sena_pct: number;
  activa: boolean;
}

export interface TipoPracticaActualizada {
  id: string;
  clinic_id: string;
  nombre: string;
  duracion_min: number;
  precio_base: number;
  sena_pct: number;
  activa: boolean;
}
