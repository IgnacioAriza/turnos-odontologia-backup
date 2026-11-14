import { createBrowserRouter, Navigate, type RouteObject } from 'react-router-dom';
import { useAuth } from '@/features/auth/hooks/useAuth';
import Layout from '@/layouts/Layout';
import PublicLayout from '@/layouts/PublicLayout';
import HomePage from '@/pages/HomePage';
import BookingPage from '@/pages/BookingPage';
import ManageAppointmentPage from '@/pages/ManageAppointmentPage';
import LoginPage from '@/pages/LoginPage';
import AgendaPage from '@/pages/AgendaPage';
import PanelPage from '@/pages/PanelPage';
import AdminPage from '@/pages/AdminPage';

interface ProtectedRouteProps {
  allowedRoles?: string[];
  children: React.ReactNode;
}

/**
 * Home interno por rol. El canal público no es destino válido para un usuario
 * autenticado: mandarlo a `/` lo devolvía al guard público y producía un ciclo
 * de redirecciones (regresión cubierta en `router.public-guard.test.tsx`).
 */
const HOME_POR_ROL: Record<string, string> = {
  admin: '/admin',
  recepcion: '/panel',
  odonto: '/agenda',
};

function ProtectedRoute({ allowedRoles, children }: ProtectedRouteProps) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return null;
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: window.location.pathname }} />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to={HOME_POR_ROL[user.role] ?? '/login'} replace />;
  }

  return <>{children}</>;
}

interface PublicRouteProps {
  children: React.ReactNode;
}

function PublicRoute({ children }: PublicRouteProps) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return null;
  }

  if (user) {
    const destino = HOME_POR_ROL[user.role];
    // Rol desconocido: se renderiza la vista pública en lugar de redirigir a un
    // destino inexistente, que dejaría al usuario en un ciclo.
    if (destino) {
      return <Navigate to={destino} replace />;
    }
  }

  return <>{children}</>;
}

export const rutas: RouteObject[] = [
  {
    path: '/',
    element: (
      <PublicLayout>
        <PublicRoute>
          <HomePage />
        </PublicRoute>
      </PublicLayout>
    ),
  },
  {
    path: '/reservar',
    element: (
      <PublicLayout>
        <PublicRoute>
          <BookingPage />
        </PublicRoute>
      </PublicLayout>
    ),
  },
  {
    path: '/gestionar/:token',
    element: (
      <PublicLayout>
        <ManageAppointmentPage />
      </PublicLayout>
    ),
  },
  {
    path: '/login',
    element: (
      <PublicLayout>
        <PublicRoute>
          <LoginPage />
        </PublicRoute>
      </PublicLayout>
    ),
  },
  {
    path: '/agenda',
    element: (
      <Layout>
        <ProtectedRoute allowedRoles={['recepcion', 'odonto', 'admin']}>
          <AgendaPage />
        </ProtectedRoute>
      </Layout>
    ),
  },
  {
    path: '/panel',
    element: (
      <Layout>
        <ProtectedRoute allowedRoles={['recepcion', 'admin']}>
          <PanelPage />
        </ProtectedRoute>
      </Layout>
    ),
  },
  {
    path: '/admin',
    element: (
      <Layout>
        <ProtectedRoute allowedRoles={['admin']}>
          <AdminPage />
        </ProtectedRoute>
      </Layout>
    ),
  },
];

export const router = createBrowserRouter(rutas);
