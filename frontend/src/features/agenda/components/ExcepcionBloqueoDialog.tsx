import { useState } from 'react';
import { formatearFecha } from '../formato';

interface ExcepcionBloqueoDialogProps {
  bloqueadoHasta: string;
  onConfirm: (motivo: string) => void;
  onCancel: () => void;
}

/**
 * Excepción al bloqueo por ausentismo (C-07 D7).
 *
 * Solo recepción/admin la ven. El motivo es obligatorio y el backend lo audita
 * en `excepciones_bloqueo` junto con el turno creado.
 */
export default function ExcepcionBloqueoDialog({
  bloqueadoHasta,
  onConfirm,
  onCancel,
}: ExcepcionBloqueoDialogProps) {
  const [motivo, setMotivo] = useState('');
  const limpio = motivo.trim();

  return (
    <div
      className="agenda-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="excepcion-titulo"
    >
      <h3 id="excepcion-titulo">Paciente bloqueado</h3>

      <div className="agenda-alerta agenda-alerta--danger" role="alert">
        <strong>Paciente bloqueado</strong>
        <p>
          Bloqueo por ausentismo vigente: no puede reservar hasta el{' '}
          {formatearFecha(bloqueadoHasta)}. Podés crear el turno con una excepción auditada.
        </p>
      </div>

      <div className="agenda-campo">
        <label htmlFor="excepcion-motivo">Motivo de la excepción</label>
        <textarea
          id="excepcion-motivo"
          className="agenda-textarea"
          value={motivo}
          aria-describedby="excepcion-ayuda"
          onChange={(event) => setMotivo(event.target.value)}
        />
        <span className="agenda-ayuda" id="excepcion-ayuda">
          Obligatorio. Queda auditado con tu usuario y el turno creado.
        </span>
      </div>

      <div className="agenda-dialog__acciones">
        <button type="button" className="agenda-btn" onClick={onCancel}>
          Volver
        </button>
        <button
          type="button"
          className="agenda-btn agenda-btn--danger"
          disabled={limpio.length === 0}
          onClick={() => onConfirm(limpio)}
        >
          Crear con excepción
        </button>
      </div>
    </div>
  );
}
