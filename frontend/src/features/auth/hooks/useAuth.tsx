import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { apiClient } from '@/shared/api-client';

export interface User {
  id: string;
  email: string;
  role: string;
  nombre: string;
}

/** Cuerpo real de `/api/auth/me` (el backend usa `rol`). */
interface UsuarioApi {
  id: string;
  email: string;
  rol: string;
}

/**
 * Normalizar el usuario del backend al contrato del frontend.
 *
 * `/api/auth/login` y `/api/auth/refresh` devuelven solo tokens, y `/me` usa
 * `rol`: sin este mapeo el guard por rol recibía `role=undefined` y rebotaba
 * al login (defecto detectado al conectar C-07 con el backend real).
 */
export function normalizarUsuario(data: UsuarioApi): User {
  return {
    id: data.id,
    email: data.email,
    role: data.rol,
    nombre: data.email.split('@')[0] ?? data.email,
  };
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const cargarPerfil = async (): Promise<User> => {
    const { data } = await apiClient.get<UsuarioApi>('/api/auth/me');
    return normalizarUsuario(data);
  };

  const cerrarSesion = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
  };

  const refreshToken = async () => {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) return;

    try {
      const response = await apiClient.post('/api/auth/refresh', { refresh_token: refreshToken });
      const { access_token } = response.data;
      localStorage.setItem('access_token', access_token);
      setUser(await cargarPerfil());
    } catch {
      cerrarSesion();
    }
  };

  useEffect(() => {
    const initAuth = async () => {
      const accessToken = localStorage.getItem('access_token');
      if (accessToken) {
        try {
          setUser(await cargarPerfil());
        } catch {
          await refreshToken();
        }
      }
      setIsLoading(false);
    };
    initAuth();
  }, []);

  const login = async (email: string, password: string) => {
    const response = await apiClient.post('/api/auth/login', { email, password });
    const { access_token, refresh_token } = response.data;
    localStorage.setItem('access_token', access_token);
    localStorage.setItem('refresh_token', refresh_token);
    try {
      setUser(await cargarPerfil());
    } catch (error) {
      cerrarSesion();
      throw error;
    }
  };

  const logout = () => {
    cerrarSesion();
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout, refreshToken }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}