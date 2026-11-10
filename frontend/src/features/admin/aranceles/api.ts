import { apiClient } from '@/shared/api-client';
import type { ArancelAdmin, TipoPracticaActualizada } from './types';

export async function fetchAranceles(): Promise<ArancelAdmin[]> {
  const response = await apiClient.get<ArancelAdmin[]>('/api/admin/aranceles');
  return response.data;
}

export async function updateSenaPct(
  tipoPracticaId: string,
  senaPct: number,
): Promise<TipoPracticaActualizada> {
  const response = await apiClient.patch<TipoPracticaActualizada>(
    `/api/admin/tipos-practica/${tipoPracticaId}/sena-pct`,
    { sena_pct: senaPct },
  );
  return response.data;
}
