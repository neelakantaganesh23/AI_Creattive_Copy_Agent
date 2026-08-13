import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { CampaignBriefForm } from '@/components/generate/CampaignBriefForm';
import type { AudienceSegment, Product } from '@/types/models';

import { renderWithProviders } from './utils';

const products: Product[] = [
  {
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
  },
];

const segments: AudienceSegment[] = [
  {
    id: 3,
    name: 'Performance Seekers',
    description: null,
    tone_guidance: null,
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 1,
    name: 'Trendsetters',
    description: null,
    tone_guidance: null,
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
];

const renderForm = (onSubmit = vi.fn(), isSubmitting = false) => {
  renderWithProviders(
    <CampaignBriefForm
      products={products}
      segments={segments}
      isSubmitting={isSubmitting}
      onSubmit={onSubmit}
    />,
    { withAuth: false },
  );
  return onSubmit;
};

describe('CampaignBriefForm', () => {
  it('pre-fills the sample campaign and its selections', () => {
    renderForm();

    const brief = screen.getByLabelText(/raw marketing brief/i) as HTMLTextAreaElement;
    expect(brief.value).toContain('AeroFlex Running Shoes');
    expect(screen.getByText('AeroFlex Running Shoes')).toBeInTheDocument();
    expect(screen.getByText('Performance Seekers')).toBeInTheDocument();
  });

  it('shows the character counter', () => {
    renderForm();
    const brief = screen.getByLabelText(/raw marketing brief/i) as HTMLTextAreaElement;
    expect(screen.getByText(new RegExp(`${brief.value.length} / 4000`))).toBeInTheDocument();
  });

  it('rejects a brief below the minimum length', async () => {
    const user = userEvent.setup();
    const onSubmit = renderForm();

    const brief = screen.getByLabelText(/raw marketing brief/i);
    await user.clear(brief);
    await user.type(brief, 'Too short');
    await user.click(screen.getByRole('button', { name: /generate copy/i }));

    expect(
      await screen.findByText('The brief must be at least 20 characters.'),
    ).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('submits the selected channel, product and audience', async () => {
    const user = userEvent.setup();
    const onSubmit = renderForm();

    await user.click(screen.getByRole('button', { name: /generate copy/i }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        channel: 'email',
        product_id: 1,
        brand_id: 1,
        audience_segment_id: 3,
        language: 'English',
      }),
    );
  });

  it('lets the channel be changed to SMS', async () => {
    const user = userEvent.setup();
    const onSubmit = renderForm();

    await user.click(screen.getByLabelText(/3\. channel/i));
    await user.click(within(screen.getByRole('listbox')).getByText('SMS'));
    await user.click(screen.getByRole('button', { name: /generate copy/i }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ channel: 'sms' }));
  });

  it('lets the audience segment be changed', async () => {
    const user = userEvent.setup();
    const onSubmit = renderForm();

    await user.click(screen.getByLabelText(/4\. audience segment/i));
    await user.click(within(screen.getByRole('listbox')).getByText('Trendsetters'));
    await user.click(screen.getByRole('button', { name: /generate copy/i }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ audience_segment_id: 1 }));
  });

  it('clears the form', async () => {
    const user = userEvent.setup();
    renderForm();

    await user.click(screen.getByRole('button', { name: /clear form/i }));
    expect((screen.getByLabelText(/raw marketing brief/i) as HTMLTextAreaElement).value).toBe('');
  });

  it('disables the submit button while a generation is running', () => {
    renderForm(vi.fn(), true);
    expect(screen.getByRole('button', { name: /generating/i })).toBeDisabled();
  });
});
