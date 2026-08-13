/**
 * Axios instance and token handling.
 *
 * The access token lives in memory only -- never in localStorage -- and the
 * refresh token is an HttpOnly cookie the browser sends automatically. All token
 * handling is confined to this module (§5).
 */
import axios, {
  type AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from 'axios';

import { env } from '@/config/env';
import type { ApiErrorPayload } from '@/types/models';

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly details: unknown;
  readonly requestId: string | null;

  constructor(message: string, code: string, status: number, details: unknown, requestId: string | null) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.details = details;
    this.requestId = requestId;
  }

  /** True when the error is worth offering a retry for. */
  get isRetryable(): boolean {
    return this.status >= 500 || this.status === 429 || this.code === 'NETWORK_ERROR';
  }
}

let accessToken: string | null = null;
let onUnauthenticated: (() => void) | null = null;

export const setAccessToken = (token: string | null): void => {
  accessToken = token;
};

export const getAccessToken = (): string | null => accessToken;

export const setUnauthenticatedHandler = (handler: (() => void) | null): void => {
  onUnauthenticated = handler;
};

export const apiClient: AxiosInstance = axios.create({
  baseURL: env.apiBaseUrl,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
});

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

interface RetriableConfig extends AxiosRequestConfig {
  _retriedAfterRefresh?: boolean;
}

/** Endpoints that must never trigger the refresh-and-retry cycle. */
const AUTH_ENDPOINTS = ['/auth/login', '/auth/register', '/auth/refresh', '/auth/logout'];

let refreshInFlight: Promise<string | null> | null = null;

const refreshAccessToken = async (): Promise<string | null> => {
  refreshInFlight ??= axios
    .post<{ access_token: string }>(
      `${env.apiBaseUrl}/auth/refresh`,
      {},
      { withCredentials: true },
    )
    .then((response) => {
      setAccessToken(response.data.access_token);
      return response.data.access_token;
    })
    .catch(() => {
      setAccessToken(null);
      return null;
    })
    .finally(() => {
      refreshInFlight = null;
    });
  return refreshInFlight;
};

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiErrorPayload>) => {
    const config = error.config as RetriableConfig | undefined;
    const status = error.response?.status ?? 0;
    const url = config?.url ?? '';
    const isAuthEndpoint = AUTH_ENDPOINTS.some((endpoint) => url.includes(endpoint));

    // A 401 on a normal call means the short-lived access token expired: rotate
    // it once using the refresh cookie, then replay the original request.
    if (status === 401 && config && !config._retriedAfterRefresh && !isAuthEndpoint) {
      config._retriedAfterRefresh = true;
      const token = await refreshAccessToken();
      if (token) {
        return apiClient.request(config);
      }
      onUnauthenticated?.();
    }

    throw toApiError(error);
  },
);

export const toApiError = (error: unknown): ApiError => {
  if (error instanceof ApiError) return error;

  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<ApiErrorPayload>;
    const payload = axiosError.response?.data;
    if (payload?.error) {
      return new ApiError(
        payload.error.message,
        payload.error.code,
        axiosError.response?.status ?? 0,
        payload.error.details,
        payload.error.request_id,
      );
    }
    if (axiosError.code === 'ECONNABORTED') {
      return new ApiError(
        'The request timed out. Please try again.',
        'TIMEOUT',
        0,
        null,
        null,
      );
    }
    if (!axiosError.response) {
      return new ApiError(
        'Unable to reach the server. Check your connection and try again.',
        'NETWORK_ERROR',
        0,
        null,
        null,
      );
    }
    return new ApiError(
      axiosError.message || 'Something went wrong.',
      'HTTP_ERROR',
      axiosError.response.status,
      null,
      null,
    );
  }

  return new ApiError('Something went wrong.', 'UNKNOWN_ERROR', 0, null, null);
};
