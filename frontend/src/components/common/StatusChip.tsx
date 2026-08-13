import { Chip, type ChipProps } from '@mui/material';

import type { AgentStatus, GenerationStatus } from '@/types/models';
import { AGENT_STATUS_LABELS, GENERATION_STATUS_LABELS } from '@/utils/format';

type Tone = 'default' | 'info' | 'success' | 'warning' | 'error';

const TONE_STYLES: Record<Tone, ChipProps['sx']> = {
  default: { bgcolor: '#F2F4F8', color: '#667085' },
  info: { bgcolor: '#EEF0FF', color: '#4B3BC4' },
  success: { bgcolor: '#E7F6EE', color: '#12734A' },
  warning: { bgcolor: '#FEF3E2', color: '#B54708' },
  error: { bgcolor: '#FDECEA', color: '#B42318' },
};

const AGENT_TONES: Record<AgentStatus, Tone> = {
  pending: 'default',
  in_progress: 'info',
  completed: 'success',
  failed: 'error',
  skipped: 'default',
};

const GENERATION_TONES: Record<GenerationStatus, Tone> = {
  pending: 'default',
  running: 'info',
  completed: 'success',
  partial: 'warning',
  failed: 'error',
};

interface StatusChipProps {
  status: AgentStatus | GenerationStatus;
  kind?: 'agent' | 'generation';
  size?: ChipProps['size'];
}

export const StatusChip = ({
  status,
  kind = 'generation',
  size = 'small',
}: StatusChipProps): JSX.Element => {
  const isAgent = kind === 'agent';
  const tone = isAgent
    ? (AGENT_TONES[status as AgentStatus] ?? 'default')
    : (GENERATION_TONES[status as GenerationStatus] ?? 'default');
  const label = isAgent
    ? (AGENT_STATUS_LABELS[status as AgentStatus] ?? status)
    : (GENERATION_STATUS_LABELS[status as GenerationStatus] ?? status);

  return (
    <Chip
      label={label}
      size={size}
      sx={{ ...TONE_STYLES[tone], fontSize: '0.75rem' }}
      // Progress is announced politely so screen readers follow the workflow.
      aria-label={`Status: ${label}`}
    />
  );
};
