import { Link } from 'react-router-dom';
import './PublicLayout.css';

interface PublicLayoutProps {
  children: React.ReactNode;
}

export default function PublicLayout({ children }: PublicLayoutProps) {
  return (
    <div className="public-layout" data-testid="app-root">
      <header className="public-layout-header">
        <nav className="public-layout-nav">
          <Link to="/" className="public-layout-brand">
            Turnos Odontología
          </Link>
          {/*
            El canal público no ofrece login: la gestión del turno se hace con el
            enlace por token que llega por WhatsApp. El acceso interno vive en
            `/login`, al que se llega por URL directa (mockup aprobado de C-06).
          */}
          <ul className="public-layout-menu">
            <li>
              <Link to="/">Inicio</Link>
            </li>
            <li>
              <Link to="/reservar">Reservar turno</Link>
            </li>
          </ul>
        </nav>
      </header>
      <main className="public-layout-main">
        {children}
      </main>
    </div>
  );
}