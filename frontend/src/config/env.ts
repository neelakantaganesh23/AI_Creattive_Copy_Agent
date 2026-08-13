/** Typed access to build-time environment configuration. */

const toBoolean = (value: string | undefined, fallback: boolean): boolean => {
  if (value === undefined || value === '') return fallback;
  return value.toLowerCase() === 'true';
};

const toNumber = (value: string | undefined, fallback: number): number => {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
};

export const env = {
  appName: import.meta.env.VITE_APP_NAME ?? 'AI Creative Copy Agent',
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1',
  enableGoogleLogin: toBoolean(import.meta.env.VITE_ENABLE_GOOGLE_LOGIN, false),
  enableDemoData: toBoolean(import.meta.env.VITE_ENABLE_DEMO_DATA, true),
  pollIntervalMs: toNumber(import.meta.env.VITE_POLL_INTERVAL_MS, 900),
} as const;
