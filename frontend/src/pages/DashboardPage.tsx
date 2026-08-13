import { Box, Skeleton, Stack } from '@mui/material';
import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { type ApiError, toApiError } from '@/api/client';
import { getDashboardSummary, getRecentGenerations } from '@/api/dashboard';
import { ErrorAlert } from '@/components/common/ErrorAlert';
import { RecentGenerationsTable } from '@/components/dashboard/RecentGenerationsTable';
import { SummaryCards } from '@/components/dashboard/SummaryCards';
import { SupportedChannels } from '@/components/dashboard/SupportedChannels';
import { CampaignBriefForm } from '@/components/generate/CampaignBriefForm';
import { WorkflowStepper } from '@/components/generate/WorkflowStepper';
import { useAuth } from '@/hooks/useAuth';
import { useGenerationRunner } from '@/hooks/useGenerationRunner';
import { useTaxonomy } from '@/hooks/useTaxonomy';
import type {
  DashboardSummary,
  GenerationCreatePayload,
  GenerationSummary,
} from '@/types/models';

export const DashboardPage = (): JSX.Element => {
  const navigate = useNavigate();
  const { hasRole } = useAuth();
  const { products, segments, isLoading: taxonomyLoading } = useTaxonomy();
  const runner = useGenerationRunner();

  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [recent, setRecent] = useState<GenerationSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const load = async (): Promise<void> => {
      setIsLoading(true);
      setError(null);
      try {
        const [summaryData, recentData] = await Promise.all([
          getDashboardSummary(),
          getRecentGenerations(5),
        ]);
        if (cancelled) return;
        setSummary(summaryData);
        setRecent(recentData);
      } catch (caught) {
        if (!cancelled) setError(toApiError(caught));
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [reloadToken]);

  // Kick a generation off here, then hand the user over to the Generate screen
  // where the full output is rendered.
  const handleSubmit = useCallback(
    async (payload: GenerationCreatePayload) => {
      const id = await runner.start(payload);
      if (id) navigate(`/generate?generationId=${id}`);
    },
    [navigate, runner],
  );

  return (
    <Box>
      <ErrorAlert
        error={error}
        title="Could not load dashboard data"
        onRetry={() => setReloadToken((token) => token + 1)}
      />

      <SummaryCards summary={summary} isLoading={isLoading} />

      <Stack direction={{ xs: 'column', lg: 'row' }} spacing={3} sx={{ mt: 3 }} alignItems="flex-start">
        <Box sx={{ flex: 1, minWidth: 0, width: '100%' }}>
          {taxonomyLoading ? (
            <Skeleton variant="rounded" height={380} />
          ) : (
            <CampaignBriefForm
              variant="compact"
              products={products}
              segments={segments}
              isSubmitting={runner.isRunning}
              disabled={!hasRole('admin', 'marketer')}
              onSubmit={(payload) => void handleSubmit(payload)}
            />
          )}
        </Box>
        <Box sx={{ flex: 1, minWidth: 0, width: '100%' }}>
          <WorkflowStepper
            steps={runner.status?.steps}
            progress={runner.status?.progress ?? 0}
            isRunning={runner.isRunning}
          />
        </Box>
      </Stack>

      <Stack direction={{ xs: 'column', lg: 'row' }} spacing={3} sx={{ mt: 3 }} alignItems="flex-start">
        <Box sx={{ flex: 2, minWidth: 0, width: '100%' }}>
          <RecentGenerationsTable items={recent} isLoading={isLoading} />
        </Box>
        <Box sx={{ flex: 1, minWidth: 0, width: '100%' }}>
          {summary && <SupportedChannels channels={summary.channels} />}
        </Box>
      </Stack>
    </Box>
  );
};
