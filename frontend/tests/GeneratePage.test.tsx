import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/api/client';

const createGeneration = vi.fn();
const getGenerationStatus = vi.fn();
const getGeneration = vi.fn();
const regenerateGeneration = vi.fn();

vi.mock('@/api/generations', () => ({
  createGeneration: (...args: unknown[]) => createGeneration(...args),
  getGenerationStatus: (...args: unknown[]) => getGenerationStatus(...args),
  getGeneration: (...args: unknown[]) => getGeneration(...args),
  regenerateGeneration: (...args: unknown[]) => regenerateGeneration(...args),
  listGenerations: vi.fn(),
  deleteGeneration: vi.fn(),
}));

const listProducts = vi.fn();
const listAudienceSegments = vi.fn();
const listBrands = vi.fn();
vi.mock('@/api/taxonomy', () => ({
  listProducts: () => listProducts(),
  listAudienceSegments: () => listAudienceSegments(),
  listBrands: () => listBrands(),
  listCtaRules: vi.fn(),
  listTemplates: vi.fn(),
}));

// `restoreMocks` clears implementations between tests, so the session mock is
// re-established in beforeEach rather than inside the factory.
const refreshSession = vi.fn();

vi.mock('@/api/auth', () => ({
  login: vi.fn(),
  register: vi.fn(),
  refreshSession: () => refreshSession(),
  logout: vi.fn().mockResolvedValue(undefined),
  fetchCurrentUser: vi.fn(),
}));

const SESSION = {
  access_token: 'token',
  expires_in: 1800,
  user: {
    id: 2,
    name: 'Marketing User',
    email: 'marketer@example.com',
    role: 'marketer' as const,
    is_active: true,
    created_at: '2026-01-01T09:00:00Z',
  },
};

const { renderWithProviders, mockGeneration, mockStatus, buildSteps } = await import('./utils');

/** Waits for the session restore to enable the button before clicking. */
const clickGenerate = async (user: ReturnType<typeof userEvent.setup>): Promise<void> => {
  const button = await screen.findByRole('button', { name: /generate copy/i });
  await waitFor(() => expect(button).toBeEnabled());
  await user.click(button);
};
const { GeneratePage } = await import('@/pages/GeneratePage');

const brand = {
  id: 1,
  name: 'AeroFlex',
  description: null,
  guidelines: null,
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const product = {
  id: 1,
  brand_id: 1,
  brand_name: 'AeroFlex',
  name: 'AeroFlex Running Shoes',
  sku: 'AF-RUN-001',
  description: null,
  features: 'speed, comfort',
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const segment = {
  id: 3,
  name: 'Performance Seekers',
  description: null,
  tone_guidance: null,
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

describe('GeneratePage', () => {
  beforeEach(() => {
    refreshSession.mockResolvedValue(SESSION);
    listBrands.mockResolvedValue({ items: [brand], total: 1, page: 1, page_size: 100, pages: 1 });
    listProducts.mockResolvedValue({ items: [product], total: 1, page: 1, page_size: 100, pages: 1 });
    listAudienceSegments.mockResolvedValue({
      items: [segment],
      total: 1,
      page: 1,
      page_size: 100,
      pages: 1,
    });
    getGeneration.mockResolvedValue(mockGeneration);
  });

  it('runs a generation and renders the output', async () => {
    const user = userEvent.setup();
    createGeneration.mockResolvedValue({ ...mockGeneration, status: 'pending' });
    getGenerationStatus.mockResolvedValue(mockStatus());

    renderWithProviders(<GeneratePage />, { route: '/generate' });

    await clickGenerate(user);

    await waitFor(() => expect(createGeneration).toHaveBeenCalledTimes(1));
    expect(await screen.findByText('Generated Copy')).toBeInTheDocument();
    expect(
      screen.getAllByText('Run Lighter. Go Farther. Feel Unstoppable.').length,
    ).toBeGreaterThan(0);
  });

  it('shows the workflow progressing through its stages', async () => {
    const user = userEvent.setup();
    createGeneration.mockResolvedValue({ ...mockGeneration, status: 'pending' });
    const running = buildSteps('pending');
    running[0] = { ...running[0]!, status: 'completed' };
    running[1] = { ...running[1]!, status: 'in_progress' };
    getGenerationStatus.mockResolvedValue(
      mockStatus({ status: 'running', progress: 0.16, steps: running, output: null }),
    );

    renderWithProviders(<GeneratePage />, { route: '/generate' });
    await clickGenerate(user);

    expect(await screen.findByText('In Progress')).toBeInTheDocument();
    expect(screen.getByLabelText('Generation progress')).toBeInTheDocument();
    expect(screen.queryByText('Generated Copy')).not.toBeInTheDocument();
  });

  it('surfaces an API failure when the generation cannot be started', async () => {
    const user = userEvent.setup();
    createGeneration.mockRejectedValue(
      new ApiError('Unable to generate campaign copy.', 'GENERATION_FAILED', 500, null, 'req-1'),
    );

    renderWithProviders(<GeneratePage />, { route: '/generate' });
    await clickGenerate(user);

    expect(await screen.findByText(/Unable to generate campaign copy/)).toBeInTheDocument();
  });

  it('reports a failed workflow to the user', async () => {
    const user = userEvent.setup();
    createGeneration.mockResolvedValue({ ...mockGeneration, status: 'pending' });
    getGenerationStatus.mockResolvedValue(
      mockStatus({
        status: 'failed',
        progress: 0.5,
        output: null,
        error_code: 'AI_PROVIDER_ERROR',
        error_message: 'The AI provider could not complete the request.',
      }),
    );

    renderWithProviders(<GeneratePage />, { route: '/generate' });
    await clickGenerate(user);

    expect(
      await screen.findByText(/The AI provider could not complete the request/),
    ).toBeInTheDocument();
  });

  it('resumes an in-flight generation from the URL', async () => {
    getGenerationStatus.mockResolvedValue(mockStatus());
    renderWithProviders(<GeneratePage />, { route: '/generate?generationId=1' });

    await waitFor(() => expect(getGenerationStatus).toHaveBeenCalledWith(1));
    expect(await screen.findByText('Generated Copy')).toBeInTheDocument();
  });
});
