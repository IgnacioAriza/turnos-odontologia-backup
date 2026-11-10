import { useEffect, useState } from 'react';
import PracticaSelector from '@/features/admin/aranceles/components/PracticaSelector';
import { fetchAranceles, updateSenaPct } from '@/features/admin/aranceles/api';
import type { ArancelAdmin } from '@/features/admin/aranceles/types';
import './AdminPage.css';

const formatoNumero = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 0 });

function formatearPrecio(precio: number): string {
  return `$${formatoNumero.format(precio)}`;
}

export default function AdminPage() {
  const [aranceles, setAranceles] = useState<ArancelAdmin[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [recarga, setRecarga] = useState(0);

  const [selectedId, setSelectedId] = useState('');
  const [senaInput, setSenaInput] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveOk, setSaveOk] = useState(false);

  useEffect(() => {
    let activo = true;

    async function cargar() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchAranceles();
        if (!activo) return;
        setAranceles(data);
        const primera = data[0];
        setSelectedId(primera?.tipo_practica_id ?? '');
        setSenaInput(primera ? String(primera.sena_pct) : '');
      } catch {
        if (activo) {
          setError('No se pudieron cargar los aranceles. Intentá de nuevo.');
        }
      } finally {
        if (activo) {
          setLoading(false);
        }
      }
    }

    cargar();
    return () => {
      activo = false;
    };
  }, [recarga]);

  function handleSeleccionar(tipoPracticaId: string) {
    setSelectedId(tipoPracticaId);
    const practica = aranceles.find((item) => item.tipo_practica_id === tipoPracticaId);
    setSenaInput(practica ? String(practica.sena_pct) : '');
    setSaveError(null);
    setSaveOk(false);
  }

  async function handleGuardar() {
    if (!selectedId) {
      setSaveError('Elegí una práctica para editar.');
      return;
    }
    if (senaInput.trim() === '') {
      setSaveError('Ingresá un porcentaje de seña.');
      return;
    }
    const nuevoPct = Number(senaInput);
    if (!Number.isInteger(nuevoPct) || nuevoPct < 0 || nuevoPct > 100) {
      setSaveError('El % de seña debe ser un entero entre 0 y 100.');
      return;
    }

    setSaving(true);
    setSaveError(null);
    setSaveOk(false);
    try {
      const actualizada = await updateSenaPct(selectedId, nuevoPct);
      setAranceles((prev) =>
        prev.map((practica) =>
          practica.tipo_practica_id === selectedId
            ? { ...practica, sena_pct: actualizada.sena_pct }
            : practica,
        ),
      );
      setSenaInput(String(actualizada.sena_pct));
      setSaveOk(true);
    } catch {
      setSaveError('No se pudo guardar el % de seña.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="admin-page">
      <div className="page-header">
        <h1>Administración</h1>
        <p className="page-subtitle">Gestión de la clínica</p>
      </div>

      <div className="admin-nav">
        <nav className="admin-tabs" role="tablist">
          <button role="tab" aria-selected="true" className="admin-tab active">
            Aranceles
          </button>
          <button role="tab" aria-selected="false" className="admin-tab">
            Odontólogos
          </button>
          <button role="tab" aria-selected="false" className="admin-tab">
            Sillones
          </button>
          <button role="tab" aria-selected="false" className="admin-tab">
            Configuración
          </button>
        </nav>
      </div>

      <div className="admin-content">
        <section className="admin-section" aria-labelledby="aranceles-heading">
          <div className="section-header">
            <h2 id="aranceles-heading">Aranceles</h2>
          </div>

          {loading && <p className="admin-status">Cargando aranceles…</p>}

          {!loading && error && (
            <div className="admin-alert" role="alert">
              <span>{error}</span>
              <button className="btn btn-sm btn-secondary" onClick={() => setRecarga((n) => n + 1)}>
                Reintentar
              </button>
            </div>
          )}

          {!loading && !error && (
            <>
              <div className="table-container">
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Práctica</th>
                      <th>Duración</th>
                      <th>Precio</th>
                      <th>Seña %</th>
                      <th>Activo</th>
                      <th>Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {aranceles.length === 0 && (
                      <tr>
                        <td colSpan={6} className="admin-empty">
                          No hay prácticas cargadas.
                        </td>
                      </tr>
                    )}
                    {aranceles.map((practica) => (
                      <tr
                        key={practica.tipo_practica_id}
                        className={practica.tipo_practica_id === selectedId ? 'selected' : undefined}
                      >
                        <td>{practica.nombre}</td>
                        <td>{practica.duracion_min} min</td>
                        <td>{formatearPrecio(practica.precio)}</td>
                        <td>{practica.sena_pct}%</td>
                        <td>
                          <span className={practica.activa ? 'badge active' : 'badge inactive'}>
                            {practica.activa ? 'Sí' : 'No'}
                          </span>
                        </td>
                        <td>
                          <button
                            className="btn btn-sm btn-secondary"
                            onClick={() => handleSeleccionar(practica.tipo_practica_id)}
                          >
                            Editar
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="admin-edit-panel">
                <h3>Editar % de seña</h3>
                <PracticaSelector
                  practicas={aranceles}
                  value={selectedId}
                  onChange={handleSeleccionar}
                />
                <div className="form-field">
                  <label htmlFor="sena-pct">Seña %</label>
                  <input
                    id="sena-pct"
                    className="form-input"
                    type="number"
                    min={0}
                    max={100}
                    step={1}
                    value={senaInput}
                    onChange={(event) => setSenaInput(event.target.value)}
                  />
                </div>
                {saveError && (
                  <p className="admin-form-error" role="alert">
                    {saveError}
                  </p>
                )}
                {saveOk && <p className="admin-form-ok">% de seña actualizado.</p>}
                <button
                  className="btn btn-primary"
                  onClick={handleGuardar}
                  disabled={saving || aranceles.length === 0}
                >
                  {saving ? 'Guardando…' : 'Guardar'}
                </button>
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
