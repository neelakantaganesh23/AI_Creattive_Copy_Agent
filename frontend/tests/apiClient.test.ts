import { describe, expect, it } from 'vitest';

import { ApiError, getAccessToken, setAccessToken, toApiError } from '@/api/client';
import { outputToPlainText, slugifyFilename } from '@/services/download';
import { formatDateTime, formatDuration, formatPercent, truncate } from '@/utils/format';

import { mockOutput } from './utils';

describe('API client', () => {
  it('keeps the access token in memory only', () => {
    setAccessToken('a-token');
    expect(getAccessToken()).toBe('a-token');
    expect(window.localStorage.getItem('a-token')).toBeNull();
    setAccessToken(null);
    expect(getAccessToken()).toBeNull();
  });

  it('maps a backend error envelope onto ApiError', () => {
    const error = toApiError({
      isAxiosError: true,
      response: {
        status: 422,
        data: {
          error: {
            code: 'VALIDATION_ERROR',
            message: 'Please correct the highlighted fields.',
            details: [{ field: 'brief', message: 'too short' }],
            request_id: 'abc',
          },
        },
      },
    });

    expect(error).toBeInstanceOf(ApiError);
    expect(error.code).toBe('VALIDATION_ERROR');
    expect(error.status).toBe(422);
    expect(error.requestId).toBe('abc');
    expect(error.isRetryable).toBe(false);
  });

  it('treats a missing response as a network error', () => {
    const error = toApiError({ isAxiosError: true, message: 'Network Error' });
    expect(error.code).toBe('NETWORK_ERROR');
    expect(error.isRetryable).toBe(true);
  });

  it('falls back for non-axios values', () => {
    expect(toApiError(new Error('boom')).code).toBe('UNKNOWN_ERROR');
  });
});

describe('formatting helpers', () => {
  it('formats durations', () => {
    expect(formatDuration(null)).toBe('--');
    expect(formatDuration(450)).toBe('450ms');
    expect(formatDuration(1840)).toBe('1.8s');
    expect(formatDuration(65_000)).toBe('1m 5s');
  });

  it('formats percentages and truncates text', () => {
    expect(formatPercent(0.945)).toBe('95%');
    expect(truncate('abcdefgh', 4)).toBe('abcd...');
    expect(truncate('abc', 10)).toBe('abc');
  });

  it('handles missing timestamps', () => {
    expect(formatDateTime(null)).toBe('--');
    expect(formatDateTime('2026-01-01T10:00:00Z')).not.toBe('--');
  });
});

describe('download helpers', () => {
  it('renders every channel in the plain-text export', () => {
    const text = outputToPlainText(mockOutput);
    expect(text).toContain('EMAIL');
    expect(text).toContain('MOBILE');
    expect(text).toContain('SMS');
    expect(text).toContain('SHOP AEROFLEX RUNNING SHOES');
    expect(text).toContain('AI-generated content should be reviewed');
  });

  it('produces safe filenames', () => {
    expect(slugifyFilename('AeroFlex Running Shoes launch!')).toBe('aeroflex-running-shoes-launch');
    expect(slugifyFilename('***')).toBe('generated-copy');
  });
});
