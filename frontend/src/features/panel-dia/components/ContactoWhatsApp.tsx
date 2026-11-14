import { enlaceWhatsApp } from '../formato';

interface ContactoWhatsAppProps {
  telefono: string;
  nombre: string;
}

/** Enlace directo al chat del paciente, con el saludo del consultorio. */
export default function ContactoWhatsApp({ telefono, nombre }: ContactoWhatsAppProps) {
  return (
    <a
      className="panel-wa"
      href={enlaceWhatsApp(telefono, nombre)}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={`WhatsApp de ${nombre}`}
    >
      WhatsApp
    </a>
  );
}
