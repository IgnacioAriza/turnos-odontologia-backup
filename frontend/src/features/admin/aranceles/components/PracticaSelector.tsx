import type { ArancelAdmin } from '../types';

interface PracticaSelectorProps {
  practicas: ArancelAdmin[];
  value: string;
  onChange: (tipoPracticaId: string) => void;
}

export default function PracticaSelector({ practicas, value, onChange }: PracticaSelectorProps) {
  return (
    <div className="form-field">
      <label htmlFor="practica-selector">Práctica</label>
      <select
        id="practica-selector"
        className="form-select"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {practicas.map((practica) => (
          <option key={practica.tipo_practica_id} value={practica.tipo_practica_id}>
            {practica.nombre}
          </option>
        ))}
      </select>
    </div>
  );
}
