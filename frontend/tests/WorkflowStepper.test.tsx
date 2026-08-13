import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { WorkflowStepper } from '@/components/generate/WorkflowStepper';

import { buildSteps, renderWithProviders } from './utils';

describe('WorkflowStepper', () => {
  it('lists all six stages as pending before a run starts', () => {
    renderWithProviders(<WorkflowStepper />, { withAuth: false });

    for (const title of [
      'Data Extraction',
      'Web Search Grounding',
      'Copy Generation',
      'Repetition Fix',
      'CTA Optimization',
      'Output Parsing & Logging',
    ]) {
      expect(screen.getByText(title)).toBeInTheDocument();
    }
    expect(screen.getAllByText('Pending')).toHaveLength(6);
  });

  it('reflects reported stage statuses', () => {
    const steps = buildSteps('completed');
    steps[2] = { ...steps[2]!, status: 'in_progress' };
    steps[1] = { ...steps[1]!, status: 'skipped' };

    renderWithProviders(<WorkflowStepper steps={steps} progress={0.5} isRunning />, {
      withAuth: false,
    });

    expect(screen.getAllByText('Completed')).toHaveLength(4);
    expect(screen.getByText('In Progress')).toBeInTheDocument();
    expect(screen.getByText('Skipped')).toBeInTheDocument();
  });

  it('announces progress to assistive technology while running', () => {
    renderWithProviders(<WorkflowStepper steps={buildSteps()} progress={0.5} isRunning />, {
      withAuth: false,
    });

    expect(
      screen.getByText('Generation in progress, 50 percent complete.'),
    ).toBeInTheDocument();
    expect(screen.getByLabelText('Generation progress')).toBeInTheDocument();
  });

  it('shows a stage error message', () => {
    const steps = buildSteps('completed');
    steps[1] = {
      ...steps[1]!,
      status: 'failed',
      error_message: 'Web search grounding failed.',
    };

    renderWithProviders(<WorkflowStepper steps={steps} />, { withAuth: false });

    expect(screen.getByText('Web search grounding failed.')).toBeInTheDocument();
    expect(screen.getByText('Failed')).toBeInTheDocument();
  });
});
