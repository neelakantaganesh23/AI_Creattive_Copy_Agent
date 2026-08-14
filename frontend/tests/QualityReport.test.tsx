import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { GeneratedCopyPanel } from '@/components/generate/GeneratedCopyPanel';
import { QualityReport } from '@/components/generate/QualityReport';
import type { QualityCheck, RuleViolation } from '@/types/models';

vi.mock('@/api/generations', () => ({
  sendTestEmail: vi.fn(),
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

const { mockGeneration, mockOutput, renderWithProviders } = await import('./utils');

beforeEach(() => {
  refreshSession.mockResolvedValue(SESSION);
});

const violation = (overrides: Partial<RuleViolation> = {}): RuleViolation => ({
  field: 'headline',
  severity: 'error',
  explanation: 'is 92 characters, maximum 50',
  rule_id: 4,
  rule_name: 'EMAIL headline length',
  suggestion: 'Shorten the headline to 50 characters or fewer.',
  ...overrides,
});

const quality = (overrides: Partial<QualityCheck> = {}): QualityCheck => ({
  status: 'warning',
  warnings: [],
  repetition_score: 0,
  repetition_fixed: false,
  violations: [],
  judge_score: 1,
  naturalness: 1,
  revisions: 0,
  ...overrides,
});

describe('QualityReport', () => {
  it('renders nothing when the copy passed cleanly', () => {
    const { container } = renderWithProviders(
      <QualityReport quality={quality({ status: 'passed' })} />,
      { withAuth: false },
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('lists each violation with its field, severity and suggestion', () => {
    renderWithProviders(<QualityReport quality={quality({ violations: [violation()] })} />, {
      withAuth: false,
    });

    expect(screen.getByText('1 content rule was not satisfied')).toBeInTheDocument();
    expect(screen.getByText('Headline (HL)')).toBeInTheDocument();
    expect(screen.getByText(/is 92 characters, maximum 50/)).toBeInTheDocument();
    expect(screen.getByText(/Shorten the headline/)).toBeInTheDocument();
    expect(screen.getByText('Error')).toBeInTheDocument();
  });

  it('does not repeat a warning that a violation already covers', () => {
    renderWithProviders(
      <QualityReport
        quality={quality({
          violations: [violation()],
          // The backend derives this string from the violation above.
          warnings: ['headline: is 92 characters, maximum 50', 'Grounding was unavailable.'],
        })}
      />,
      { withAuth: false },
    );

    expect(screen.queryByText('headline: is 92 characters, maximum 50')).not.toBeInTheDocument();
    expect(screen.getByText('Grounding was unavailable.')).toBeInTheDocument();
  });
});

describe('GeneratedCopyPanel generated image', () => {
  it('renders the generated image when present', () => {
    renderWithProviders(
      <GeneratedCopyPanel
        output={{ ...mockOutput, image_url: '/media/aeroflex-ab12cd34.png' }}
        generation={mockGeneration}
      />,
    );

    const image = screen.getByRole('img', { name: /generated visual/i });
    expect(image).toHaveAttribute('src', expect.stringContaining('/media/aeroflex-ab12cd34.png'));
  });

  it('falls back to the CSS placeholder when no image was generated', () => {
    renderWithProviders(
      <GeneratedCopyPanel output={{ ...mockOutput, image_url: null }} generation={mockGeneration} />,
    );

    expect(screen.queryByRole('img', { name: /generated visual/i })).not.toBeInTheDocument();
    expect(screen.getByText('Email Preview')).toBeInTheDocument();
  });
});

describe('GeneratedCopyPanel judge results', () => {
  it('shows the judge score and revision count', () => {
    renderWithProviders(
      <GeneratedCopyPanel
        output={{ ...mockOutput, quality: quality({ judge_score: 0.82, revisions: 1 }) }}
        generation={mockGeneration}
      />,
    );

    expect(screen.getByText('Judge score: 82%')).toBeInTheDocument();
    expect(screen.getByText('Revised once after review')).toBeInTheDocument();
  });

  it('omits the judge chip when validation did not run', () => {
    renderWithProviders(
      <GeneratedCopyPanel
        output={{ ...mockOutput, quality: quality({ judge_score: null }) }}
        generation={mockGeneration}
      />,
    );

    expect(screen.queryByText(/Judge score/)).not.toBeInTheDocument();
  });
});
