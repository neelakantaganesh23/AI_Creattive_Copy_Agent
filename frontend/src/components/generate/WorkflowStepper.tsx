import {
  Box,
  Card,
  CardContent,
  CircularProgress,
  LinearProgress,
  Stack,
  Tooltip,
  Typography,
} from '@mui/material';
import {
  CheckCircle2,
  CircleDot,
  ClipboardCheck,
  Database,
  FileSearch,
  Globe,
  Image as ImageIcon,
  PencilLine,
  ShieldCheck,
  Target,
  Terminal,
  TriangleAlert,
  Workflow,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useState } from 'react';

import { PromptDialog } from '@/components/common/PromptDialog';
import { StatusChip } from '@/components/common/StatusChip';
import { useAuth } from '@/hooks/useAuth';
import { PENDING_STEPS } from '@/hooks/useGenerationRunner';
import type { AgentExecution, AgentStatus } from '@/types/models';
import { formatDuration } from '@/utils/format';

const AGENT_ICONS: Record<string, LucideIcon> = {
  data_extraction: FileSearch,
  web_search_grounding: Globe,
  copy_generation: PencilLine,
  repetition_fix: ShieldCheck,
  cta_optimization: Target,
  image_generation: ImageIcon,
  content_validation: ClipboardCheck,
  output_parsing: Database,
};

type StepLike = Pick<AgentExecution, 'agent_name' | 'title' | 'description'> &
  Partial<Pick<AgentExecution, 'status' | 'duration_ms' | 'error_message' | 'input_summary'>>;

interface WorkflowStepperProps {
  steps?: AgentExecution[];
  progress?: number;
  isRunning?: boolean;
}

const StatusIndicator = ({ status }: { status: AgentStatus }): JSX.Element => {
  if (status === 'completed') return <CheckCircle2 size={18} color="#22A861" aria-hidden />;
  if (status === 'failed') return <TriangleAlert size={18} color="#D92D20" aria-hidden />;
  if (status === 'in_progress') return <CircularProgress size={16} aria-hidden />;
  return <CircleDot size={18} color="#98A2B3" aria-hidden />;
};

export const WorkflowStepper = ({
  steps,
  progress = 0,
  isRunning = false,
}: WorkflowStepperProps): JSX.Element => {
  const { hasRole } = useAuth();
  const [promptStep, setPromptStep] = useState<StepLike | null>(null);
  const rows: StepLike[] = steps?.length ? steps : PENDING_STEPS;
  // Prompts are only meaningful once a stage has actually run, and are shown
  // to admins only -- they can reveal brand guidelines and configured rules.
  const canViewPrompts = hasRole('admin');

  return (
    <Card component="section" aria-labelledby="workflow-heading">
      <CardContent sx={{ p: { xs: 2, md: 3 } }}>
        <Stack direction="row" spacing={1.25} alignItems="center" sx={{ mb: 2 }}>
          <Box sx={{ color: 'primary.main', display: 'flex' }} aria-hidden>
            <Workflow size={18} />
          </Box>
          <Box sx={{ flex: 1 }}>
            <Typography variant="h5" component="h2" id="workflow-heading">
              Generation Workflow
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Multi-agent pipeline execution
            </Typography>
          </Box>
        </Stack>

        {isRunning && (
          <LinearProgress
            variant={progress > 0 ? 'determinate' : 'indeterminate'}
            value={Math.round(progress * 100)}
            sx={{ mb: 2, borderRadius: 1, height: 6 }}
            aria-label="Generation progress"
          />
        )}

        {/* Screen readers are told about stage changes without stealing focus. */}
        <Box
          aria-live="polite"
          aria-atomic="true"
          sx={{
            position: 'absolute',
            width: 1,
            height: 1,
            overflow: 'hidden',
            clip: 'rect(0 0 0 0)',
          }}
        >
          {isRunning
            ? `Generation in progress, ${Math.round(progress * 100)} percent complete.`
            : ''}
        </Box>

        <Stack spacing={0.5} component="ol" sx={{ listStyle: 'none', p: 0, m: 0 }}>
          {rows.map((step, index) => {
            const Icon = AGENT_ICONS[step.agent_name] ?? CircleDot;
            const status: AgentStatus = step.status ?? 'pending';
            const hasPrompt = canViewPrompts && Boolean(step.input_summary);
            return (
              <Stack
                key={step.agent_name}
                component="li"
                direction="row"
                spacing={1.5}
                alignItems="center"
                onClick={hasPrompt ? () => setPromptStep(step) : undefined}
                sx={{
                  py: 1.25,
                  px: 1,
                  borderRadius: 2,
                  cursor: hasPrompt ? 'pointer' : 'default',
                  bgcolor: status === 'in_progress' ? 'rgba(101,72,232,0.06)' : 'transparent',
                  '&:hover': hasPrompt ? { bgcolor: 'action.hover' } : undefined,
                }}
              >
                <Typography
                  variant="caption"
                  sx={{
                    width: 22,
                    height: 22,
                    borderRadius: '50%',
                    display: 'grid',
                    placeItems: 'center',
                    bgcolor: status === 'completed' ? '#E7F6EE' : '#F2F4F8',
                    color: status === 'completed' ? '#12734A' : 'text.secondary',
                    fontWeight: 700,
                    flexShrink: 0,
                  }}
                >
                  {index + 1}
                </Typography>

                <Box sx={{ color: 'text.secondary', display: 'flex' }} aria-hidden>
                  <Icon size={17} />
                </Box>

                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Typography variant="body2" sx={{ fontWeight: 600 }} noWrap>
                    {step.title}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" noWrap component="p">
                    {step.error_message ?? step.description}
                  </Typography>
                </Box>

                {hasPrompt && (
                  <Tooltip title="View the prompt sent to the model">
                    <Box sx={{ color: 'text.secondary', display: 'flex' }}>
                      <Terminal size={15} />
                    </Box>
                  </Tooltip>
                )}

                {step.duration_ms != null && step.duration_ms > 0 && (
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ display: { xs: 'none', sm: 'block' } }}
                  >
                    {formatDuration(step.duration_ms)}
                  </Typography>
                )}

                <Tooltip title={step.error_message ?? ''} disableHoverListener={!step.error_message}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <StatusIndicator status={status} />
                    <Box sx={{ display: { xs: 'none', sm: 'block' } }}>
                      <StatusChip status={status} kind="agent" />
                    </Box>
                  </Box>
                </Tooltip>
              </Stack>
            );
          })}
        </Stack>
      </CardContent>

      <PromptDialog
        open={promptStep !== null}
        onClose={() => setPromptStep(null)}
        title={promptStep?.title ?? ''}
        prompt={promptStep?.input_summary ?? null}
      />
    </Card>
  );
};
