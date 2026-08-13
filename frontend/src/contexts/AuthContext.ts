import { createContext } from 'react';

import type { Role, User } from '@/types/models';

export interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  /** True until the initial silent refresh has settled. */
  isInitialising: boolean;
  login: (email: string, password: string, rememberMe?: boolean) => Promise<User>;
  loginWithGoogle: (credential: string) => Promise<User>;
  register: (name: string, email: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  hasRole: (...roles: Role[]) => boolean;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);
