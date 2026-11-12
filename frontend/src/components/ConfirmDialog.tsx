/**
 * Diálogo de confirmación accesible (C-06 task 10.4).
 *
 * Se usa para las acciones que pierden la seña. El foco arranca en la acción
 * segura, `Escape` cierra, el tabulador no se escapa del diálogo y al cerrar el
 * foco vuelve al elemento que lo abrió.
 */

import { useEffect, useId, useRef } from 'react';
import { createPortal } from 'react-dom';

interface ConfirmDialogProps {
  titulo: string;
  descripcion: string;
  confirmarLabel: string;
  volverLabel?: string;
  onConfirmar: () => void;
  onCerrar: () => void;
  /** Contenido adicional bajo la descripción (avisos, monto, código). */
  children?: React.ReactNode;
}

const SELECTOR_ENFOCABLE =
  'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

export function ConfirmDialog({
  titulo,
  descripcion,
  confirmarLabel,
  volverLabel = 'Volver',
  onConfirmar,
  onCerrar,
  children,
}: ConfirmDialogProps) {
  const id = useId();
  const contenedor = useRef<HTMLDivElement>(null);
  const volver = useRef<HTMLButtonElement>(null);
  const disparador = useRef<Element | null>(null);

  useEffect(() => {
    disparador.current = document.activeElement;
    volver.current?.focus();

    return () => {
      const previo = disparador.current;
      if (previo instanceof HTMLElement && document.contains(previo)) {
        previo.focus();
      }
    };
  }, []);

  const alPresionarTecla = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Escape') {
      event.stopPropagation();
      onCerrar();
      return;
    }

    if (event.key !== 'Tab' || contenedor.current === null) {
      return;
    }

    const enfocables = Array.from(
      contenedor.current.querySelectorAll<HTMLElement>(SELECTOR_ENFOCABLE),
    );
    if (enfocables.length === 0) {
      return;
    }

    const primero = enfocables[0]!;
    const ultimo = enfocables[enfocables.length - 1]!;
    const activo = document.activeElement;

    if (event.shiftKey && (activo === primero || activo === contenedor.current)) {
      event.preventDefault();
      ultimo.focus();
      return;
    }

    if (!event.shiftKey && activo === ultimo) {
      event.preventDefault();
      primero.focus();
    }
  };

  return createPortal(
    <div className="bk-dialog-veil">
      <div
        className="bk-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby={`${id}-titulo`}
        aria-describedby={`${id}-desc`}
        ref={contenedor}
        onKeyDown={alPresionarTecla}
      >
        <h2 id={`${id}-titulo`} className="bk-dialog-titulo">
          {titulo}
        </h2>
        <p id={`${id}-desc`} className="bk-help">
          {descripcion}
        </p>
        {children}
        <div className="bk-dialog-acciones">
          <button type="button" className="bk-btn bk-btn--secondary" ref={volver} onClick={onCerrar}>
            {volverLabel}
          </button>
          <button type="button" className="bk-btn bk-btn--danger" onClick={onConfirmar}>
            {confirmarLabel}
          </button>
        </div>
        <p className="bk-help">Podés cerrar este aviso con Escape o con “{volverLabel}”.</p>
      </div>
    </div>,
    document.body,
  );
}

export default ConfirmDialog;
