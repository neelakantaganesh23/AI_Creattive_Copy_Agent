import type { AgentStatus, Channel, GenerationStatus } from '@/types/models';

export const CHANNEL_LABELS: Record<Channel, string> = {
  email: 'Email',
  mobile: 'Mobile',
  sms: 'SMS',
};

export const FIELD_LABELS: Record<string, string> = {
  headline: 'Headline (HL)',
  sub_heading: 'Sub-heading (SH)',
  cta: 'Call To Action (CTA)',
  superline: 'Superline',
  pre_heading: 'Pre-heading',
  description: 'Promotional description',
};

export const GENERATION_STATUS_LABELS: Record<GenerationStatus, string> = {
  pending: 'Pending',
  running: 'In Progress',
  completed: 'Completed',
  partial: 'Completed with warnings',
  failed: 'Failed',
};

export const AGENT_STATUS_LABELS: Record<AgentStatus, string> = {
  pending: 'Pending',
  in_progress: 'In Progress',
  completed: 'Completed',
  failed: 'Failed',
  skipped: 'Skipped',
};

export const formatDuration = (milliseconds: number | null | undefined): string => {
  if (milliseconds === null || milliseconds === undefined) return '--';
  if (milliseconds < 1000) return `${milliseconds}ms`;
  const seconds = milliseconds / 1000;
  return seconds < 60 ? `${seconds.toFixed(1)}s` : `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
};

export const formatDateTime = (value: string | null | undefined): string => {
  if (!value) return '--';
  const date = new Date(value.endsWith('Z') || value.includes('+') ? value : `${value}Z`);
  if (Number.isNaN(date.getTime())) return '--';
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
};

export const formatPercent = (ratio: number): string => `${Math.round(ratio * 100)}%`;

export const truncate = (value: string, limit: number): string =>
  value.length <= limit ? value : `${value.slice(0, limit).trimEnd()}...`;
