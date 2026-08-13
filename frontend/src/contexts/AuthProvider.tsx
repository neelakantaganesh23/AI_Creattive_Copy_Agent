/** Authentication state shared across the application. */
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';

import * as authApi from '@/api/auth';
import { setAccessToken, setUnauthenticatedHandler, toApiError } from '@/api/client';
import { AuthContext, type AuthContextValue } from '@/contexts/AuthContext';
import type { Role, User } from '@/types/models';

export const AuthProvider = ({ children }: { children: ReactNode }): JSX.Element => {
  const [user, setUser] = useState<User | null>(null);
  const [isInitialising, setIsInitialising] = useState(true);

  // On a page reload the access token is gone (it is memory-only), so try to
  // restore the session from the HttpOnly refresh cookie exactly once.
  useEffect(() => {
    let cancelled = false;
    const restore = async (): Promise<void> => {
      try {
        const session = await authApi.refreshSession();
        if (!cancelled) setUser(session.user);
      } catch {
        if (!cancelled) setUser(null);
      } finally {
        if (!cancelled) setIsInitialising(false);
      }
    };
    void restore();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    setUnauthenticatedHandler(() => {
      setUser(null);
      setAccessToken(null);
    });
    return () => setUnauthenticatedHandler(null);
  }, []);

  const login = useCallback(
    async (email: string, password: string, rememberMe = false): Promise<User> => {
      try {
        const session = await authApi.login({ email, password, remember_me: rememberMe });
        setUser(session.user);
        return session.user;
      } catch (error) {
        throw toApiError(error);
      }
    },
    [],
  );

  const register = useCallback(
    async (name: string, email: string, password: string): Promise<User> => {
      try {
        const session = await authApi.register({ name, email, password });
        setUser(session.user);
        return session.user;
      } catch (error) {
        throw toApiError(error);
      }
    },
    [],
  );

  const logout = useCallback(async (): Promise<void> => {
    await authApi.logout().catch(() => undefined);
    setUser(null);
  }, []);

  const hasRole = useCallback(
    (...roles: Role[]): boolean => (user ? roles.includes(user.role) : false),
    [user],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: user !== null,
      isInitialising,
      login,
      register,
      logout,
      hasRole,
    }),
    [user, isInitialising, login, register, logout, hasRole],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
