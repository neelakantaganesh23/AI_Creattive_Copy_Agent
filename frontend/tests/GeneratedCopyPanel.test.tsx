import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { GeneratedCopyPanel } from '@/components/generate/GeneratedCopyPanel';

const sendTestEmail = vi.fn();

vi.mock('@/api/generations', () => ({
  sendTestEmail: (...args: unknown[]) => sendTestEmail(...args),
  createGeneration: vi.fn(),
  getGenerationStatus: vi.fn(),
  getGeneration: vi.fn(),
  regenerateGeneration: vi.fn(),
  listGenerations: vi.fn(),
  deleteGeneration: vi.fn(),
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
  token_type: 'bearer',
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

const { renderWithProviders, mockGeneration, mockOutput } = await import('./utils');

describe('GeneratedCopyPanel', () => {
  beforeEach(() => {
    refreshSession.mockResolvedValue(SESSION);
  });

  it('renders the email fields by default', () => {
    renderWithProviders(<GeneratedCopyPanel output={mockOutput} generation={mockGeneration} />);

    expect(screen.getAllByText('Run Lighter. Go Farther. Feel Unstoppable.').length).toBe(2);
    expect(screen.getAllByText(/Introducing AeroFlex Running Shoes/).length).toBeGreaterThan(0);
    expect(screen.getAllByText('SHOP AEROFLEX RUNNING SHOES').length).toBeGreaterThan(0);
    expect(screen.getByText('Headline (HL)')).toBeInTheDocument();
  });

  it('shows the email preview and the review notice', () => {
    renderWithProviders(<GeneratedCopyPanel output={mockOutput} generation={mockGeneration} />);

    expect(screen.getByText('Email Preview')).toBeInTheDocument();
    expect(
      screen.getByText(/AI-generated content should be reviewed and validated/),
    ).toBeInTheDocument();
  });

  it('switches to the mobile and SMS tabs', async () => {
    const user = userEvent.setup();
    renderWithProviders(<GeneratedCopyPanel output={mockOutput} generation={mockGeneration} />);

    await user.click(screen.getByRole('tab', { name: 'Mobile' }));
    expect(screen.getByText('Superline')).toBeInTheDocument();
    expect(screen.getByText('JUST LAUNCHED')).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: 'SMS' }));
    expect(screen.getByText('Promotional description')).toBeInTheDocument();
  });

  it('copies a single field to the clipboard', async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText },
      configurable: true,
    });

    renderWithProviders(<GeneratedCopyPanel output={mockOutput} generation={mockGeneration} />);

    await user.click(screen.getByRole('button', { name: /copy headline/i }));
    expect(writeText).toHaveBeenCalledWith('Run Lighter. Go Farther. Feel Unstoppable.');
    expect(await screen.findByText(/copied to clipboard/i)).toBeInTheDocument();
  });

  it('copies every channel at once', async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText },
      configurable: true,
    });

    renderWithProviders(<GeneratedCopyPanel output={mockOutput} generation={mockGeneration} />);

    await user.click(screen.getByRole('button', { name: /copy all/i }));
    const copied = writeText.mock.calls[0]?.[0] as string;
    expect(copied).toContain('EMAIL');
    expect(copied).toContain('MOBILE');
    expect(copied).toContain('SMS');
  });

  it('offers JSON and TXT downloads', async () => {
    const user = userEvent.setup();
    renderWithProviders(<GeneratedCopyPanel output={mockOutput} generation={mockGeneration} />);

    await user.click(screen.getByRole('button', { name: /download/i }));
    const menu = await screen.findByRole('menu');
    expect(within(menu).getByText('Download as JSON')).toBeInTheDocument();
    expect(within(menu).getByText('Download as TXT')).toBeInTheDocument();
  });

  it('shows the metadata chips', () => {
    renderWithProviders(<GeneratedCopyPanel output={mockOutput} generation={mockGeneration} />);

    expect(screen.getByText('Channel: Email')).toBeInTheDocument();
    expect(screen.getByText('Audience: Performance Seekers')).toBeInTheDocument();
    expect(screen.getByText('Quality: passed')).toBeInTheDocument();
    expect(screen.getByText('Not externally grounded')).toBeInTheDocument();
  });

  it('renders quality warnings when present', () => {
    renderWithProviders(
      <GeneratedCopyPanel
        output={{
          ...mockOutput,
          quality: {
            ...mockOutput.quality,
            status: 'warning',
            warnings: ['EMAIL headline is 92 characters (recommended maximum 80).'],
          },
        }}
        generation={mockGeneration}
      />,
    );

    expect(screen.getByText(/EMAIL headline is 92 characters/)).toBeInTheDocument();
  });

  it('triggers regeneration', async () => {
    const onRegenerate = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(
      <GeneratedCopyPanel
        output={mockOutput}
        generation={mockGeneration}
        onRegenerate={onRegenerate}
      />,
    );

    await user.click(screen.getByRole('button', { name: /regenerate/i }));
    expect(onRegenerate).toHaveBeenCalledTimes(1);
  });

  describe('send test email', () => {
    it('only offers the send button on the Email tab', async () => {
      const user = userEvent.setup();
      renderWithProviders(<GeneratedCopyPanel output={mockOutput} generation={mockGeneration} />);

      await waitFor(() =>
        expect(screen.getByRole('button', { name: /send test email/i })).toBeInTheDocument(),
      );

      await user.click(screen.getByRole('tab', { name: 'Mobile' }));
      expect(screen.queryByRole('button', { name: /send test email/i })).not.toBeInTheDocument();
    });

    it('confirms with the recipient before sending, then sends', async () => {
      sendTestEmail.mockResolvedValue({ message: 'Test email sent to marketer@example.com.' });
      const user = userEvent.setup();
      renderWithProviders(<GeneratedCopyPanel output={mockOutput} generation={mockGeneration} />);

      await user.click(await screen.findByRole('button', { name: /send test email/i }));
      expect(screen.getByText(/marketer@example\.com/)).toBeInTheDocument();

      await user.click(screen.getByRole('button', { name: /^send$/i }));

      expect(sendTestEmail).toHaveBeenCalledWith(mockGeneration.id);
      expect(await screen.findByText('Test email sent to marketer@example.com.')).toBeInTheDocument();
    });

    it('cancelling the dialog does not send anything', async () => {
      const user = userEvent.setup();
      renderWithProviders(<GeneratedCopyPanel output={mockOutput} generation={mockGeneration} />);

      await user.click(await screen.findByRole('button', { name: /send test email/i }));
      await user.click(screen.getByRole('button', { name: /cancel/i }));

      expect(sendTestEmail).not.toHaveBeenCalled();
    });

    it('shows the error message when sending fails', async () => {
      const { ApiError } = await import('@/api/client');
      sendTestEmail.mockRejectedValue(
        new ApiError('This generation has not completed yet.', 'GENERATION_NOT_READY', 409, null, null),
      );
      const user = userEvent.setup();
      renderWithProviders(<GeneratedCopyPanel output={mockOutput} generation={mockGeneration} />);

      await user.click(await screen.findByRole('button', { name: /send test email/i }));
      await user.click(screen.getByRole('button', { name: /^send$/i }));

      expect(await screen.findByText('This generation has not completed yet.')).toBeInTheDocument();
    });

    it('does not offer the send button without a persisted generation', () => {
      renderWithProviders(<GeneratedCopyPanel output={mockOutput} generation={null} />);
      expect(screen.queryByRole('button', { name: /send test email/i })).not.toBeInTheDocument();
    });
  });
});
