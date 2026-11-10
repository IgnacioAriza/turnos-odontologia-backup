import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AdminPage from './AdminPage';
import { fetchAranceles, updateSenaPct } from '@/features/admin/aranceles/api';
import type { ArancelAdmin } from '@/features/admin/aranceles/types';

vi.mock('@/features/admin/aranceles/api', () => ({
  fetchAranceles: vi.fn(),
  updateSenaPct: vi.fn(),
}));

const practicas: ArancelAdmin[] = [
  {
    tipo_practica_id: 'practica-1',
    nombre: 'Limpieza',
    duracion_min: 30,
    precio: 15000,
    sena_pct: 30,
    activa: true,
  },
  {
    tipo_practica_id: 'practica-2',
    nombre: 'Endodoncia',
    duracion_min: 60,
    precio: 45000,
    sena_pct: 20,
    activa: false,
  },
];

describe('AdminPage', () => {
  beforeEach(() => {
    vi.mocked(fetchAranceles).mockReset();
    vi.mocked(updateSenaPct).mockReset();
  });

  it('muestra las prácticas traídas del backend', async () => {
    vi.mocked(fetchAranceles).mockResolvedValue(practicas);

    render(<AdminPage />);

    expect((await screen.findAllByText('Limpieza')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('Endodoncia').length).toBeGreaterThan(0);
    expect(screen.getByText('$15.000')).toBeInTheDocument();
    expect(screen.getByText('30%')).toBeInTheDocument();
  });

  it('muestra un error si la consulta falla', async () => {
    vi.mocked(fetchAranceles).mockRejectedValue(new Error('boom'));

    render(<AdminPage />);

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No se pudieron cargar los aranceles',
    );
  });

  it('envía el PATCH y refresca el % seña de la fila', async () => {
    vi.mocked(fetchAranceles).mockResolvedValue(practicas);
    vi.mocked(updateSenaPct).mockResolvedValue({
      id: 'practica-1',
      clinic_id: 'clinic-1',
      nombre: 'Limpieza',
      duracion_min: 30,
      precio_base: 15000,
      sena_pct: 55,
      activa: true,
    });

    render(<AdminPage />);
    await screen.findAllByText('Limpieza');

    const input = screen.getByLabelText('Seña %');
    fireEvent.change(input, { target: { value: '55' } });
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }));

    await waitFor(() => {
      expect(updateSenaPct).toHaveBeenCalledWith('practica-1', 55);
    });
    expect(await screen.findByText('55%')).toBeInTheDocument();
  });

  it('rechaza un porcentaje fuera de rango sin llamar al backend', async () => {
    vi.mocked(fetchAranceles).mockResolvedValue(practicas);

    render(<AdminPage />);
    await screen.findAllByText('Limpieza');

    const input = screen.getByLabelText('Seña %');
    fireEvent.change(input, { target: { value: '150' } });
    fireEvent.click(screen.getByRole('button', { name: 'Guardar' }));

    expect(await screen.findByText('El % de seña debe ser un entero entre 0 y 100.')).toBeInTheDocument();
    expect(updateSenaPct).not.toHaveBeenCalled();
  });
});
