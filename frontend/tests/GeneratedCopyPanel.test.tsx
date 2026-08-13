import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { GeneratedCopyPanel } from '@/components/generate/GeneratedCopyPanel';

import { mockGeneration, mockOutput, renderWithProviders } from './utils';

describe('GeneratedCopyPanel', () => {
  it('renders the email fields by default', () => {
    renderWithProviders(
      <GeneratedCopyPanel output={mockOutput} generation={mockGeneration} />,
      { withAuth: false },
    );

    expect(screen.getAllByText('Run Lighter. Go Farther. Feel Unstoppable.').length).toBe(2);
    expect(screen.getAllByText(/Introducing AeroFlex Running Shoes/).length).toBeGreaterThan(0);
    expect(screen.getAllByText('SHOP AEROFLEX RUNNING SHOES').length).toBeGreaterThan(0);
    expect(screen.getByText('Headline (HL)')).toBeInTheDocument();
  });

  it('shows the email preview and the review notice', () => {
    renderWithProviders(
      <GeneratedCopyPanel output={mockOutput} generation={mockGeneration} />,
      { withAuth: false },
    );

    expect(screen.getByText('Email Preview')).toBeInTheDocument();
    expect(
      screen.getByText(/AI-generated content should be reviewed and validated/),
    ).toBeInTheDocument();
  });

  it('switches to the mobile and SMS tabs', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <GeneratedCopyPanel output={mockOutput} generation={mockGeneration} />,
      { withAuth: false },
    );

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

    renderWithProviders(
      <GeneratedCopyPanel output={mockOutput} generation={mockGeneration} />,
      { withAuth: false },
    );

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

    renderWithProviders(
      <GeneratedCopyPanel output={mockOutput} generation={mockGeneration} />,
      { withAuth: false },
    );

    await user.click(screen.getByRole('button', { name: /copy all/i }));
    const copied = writeText.mock.calls[0]?.[0] as string;
    expect(copied).toContain('EMAIL');
    expect(copied).toContain('MOBILE');
    expect(copied).toContain('SMS');
  });

  it('offers JSON and TXT downloads', async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <GeneratedCopyPanel output={mockOutput} generation={mockGeneration} />,
      { withAuth: false },
    );

    await user.click(screen.getByRole('button', { name: /download/i }));
    const menu = await screen.findByRole('menu');
    expect(within(menu).getByText('Download as JSON')).toBeInTheDocument();
    expect(within(menu).getByText('Download as TXT')).toBeInTheDocument();
  });

  it('shows the metadata chips', () => {
    renderWithProviders(
      <GeneratedCopyPanel output={mockOutput} generation={mockGeneration} />,
      { withAuth: false },
    );

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
      { withAuth: false },
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
      { withAuth: false },
    );

    await user.click(screen.getByRole('button', { name: /regenerate/i }));
    expect(onRegenerate).toHaveBeenCalledTimes(1);
  });
});
