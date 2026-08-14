import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import * as authApi from '@/api/auth';
import { WorkflowStepper } from '@/components/generate/WorkflowStepper';

import { buildSteps, mockUser, renderWithProviders } from './utils';

vi.mock('@/api/auth');

const adminUser = { ...mockUser, role: 'admin' as const };

describe('WorkflowStepper prompt visibility', () => {
  beforeEach(() => {
    vi.mocked(authApi.refreshSession).mockReset();
  });

  it('lets an admin open the full prompt for a completed stage', async () => {
    vi.mocked(authApi.refreshSession).mockResolvedValue({
      access_token: 'token',
      token_type: 'bearer',
      expires_in: 3600,
      user: adminUser,
    });

    const steps = buildSteps('completed');
    steps[0] = { ...steps[0]!, input_summary: '--- Instructions ---\nBe precise.' };

    const user = userEvent.setup();
    renderWithProviders(<WorkflowStepper steps={steps} />);

    await waitFor(() => screen.getByText('Data Extraction'));
    await user.click(screen.getByText('Data Extraction'));

    expect(await screen.findByText('Prompt: Data Extraction')).toBeInTheDocument();
    expect(screen.getByText(/Be precise\./)).toBeInTheDocument();
  });

  it('does not let a marketer open a stage prompt', async () => {
    vi.mocked(authApi.refreshSession).mockResolvedValue({
      access_token: 'token',
      token_type: 'bearer',
      expires_in: 3600,
      user: mockUser,
    });

    const steps = buildSteps('completed');
    steps[0] = { ...steps[0]!, input_summary: '--- Instructions ---\nBe precise.' };

    const user = userEvent.setup();
    renderWithProviders(<WorkflowStepper steps={steps} />);

    await waitFor(() => screen.getByText('Data Extraction'));
    await user.click(screen.getByText('Data Extraction'));

    expect(screen.queryByText('Prompt: Data Extraction')).not.toBeInTheDocument();
  });
});
