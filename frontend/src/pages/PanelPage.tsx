import { useAuth } from '@/features/auth/hooks/useAuth';
import JornadaPanel from '@/features/panel-dia/components/JornadaPanel';

/**
 * Panel del día para recepción y admin. El odontólogo usa la misma jornada
 * desde `/agenda` en modo "Mi agenda" (C-07 8.7).
 */
export default function PanelPage() {
  const { user } = useAuth();
  const esOdonto = user?.role === 'odonto';

  return (
    <JornadaPanel
      titulo={esOdonto ? 'Mi jornada' : 'Panel del día'}
      subtitulo={
        esOdonto
          ? 'Tus turnos de hoy: marcá llegadas y ausencias propias'
          : 'Llegadas, ausencias y contacto por WhatsApp'
      }
    />
  );
}
