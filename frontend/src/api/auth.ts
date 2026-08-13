import { apiClient, setAccessToken } from '@/api/client';
import type { AuthOptions, Role, TokenResponse, User } from '@/types/models';

export interface LoginPayload {
  email: string;
  password: string;
  remember_me?: boolean;
}

export interface RegisterPayload {
  name: string;
  email: string;
  password: string;
  role?: Role;
}

export const login = async (payload: LoginPayload): Promise<TokenResponse> => {
  const { data } = await apiClient.post<TokenResponse>('/auth/login', payload);
  setAccessToken(data.access_token);
  return data;
};

export const register = async (payload: RegisterPayload): Promise<TokenResponse> => {
  const { data } = await apiClient.post<TokenResponse>('/auth/register', payload);
  setAccessToken(data.access_token);
  return data;
};

/** Exchanges the HttpOnly refresh cookie for a new access token. */
export const refreshSession = async (): Promise<TokenResponse> => {
  const { data } = await apiClient.post<TokenResponse>('/auth/refresh', {});
  setAccessToken(data.access_token);
  return data;
};

export const logout = async (): Promise<void> => {
  try {
    await apiClient.post('/auth/logout', {});
  } finally {
    setAccessToken(null);
  }
};

export const fetchCurrentUser = async (): Promise<User> => {
  const { data } = await apiClient.get<User>('/auth/me');
  return data;
};

/** Exchanges a Google Identity Services ID token for an application session. */
export const loginWithGoogle = async (credential: string): Promise<TokenResponse> => {
  const { data } = await apiClient.post<TokenResponse>('/auth/google', { credential });
  setAccessToken(data.access_token);
  return data;
};

export const fetchAuthOptions = async (): Promise<AuthOptions> => {
  const { data } = await apiClient.get<AuthOptions>('/auth/options');
  return data;
};

export const requestPasswordReset = async (email: string): Promise<{ message: string }> => {
  const { data } = await apiClient.post<{ message: string }>('/auth/password-reset/request', {
    email,
  });
  return data;
};

export const confirmPasswordReset = async (
  token: string,
  password: string,
): Promise<{ message: string }> => {
  const { data } = await apiClient.post<{ message: string }>('/auth/password-reset/confirm', {
    token,
    password,
  });
  return data;
};
