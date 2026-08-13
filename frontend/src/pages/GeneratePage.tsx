import { Alert, Box, Skeleton, Stack } from '@mui/material';
import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { getGeneration } from '@/api/generations';
import { ErrorAlert } from '@/components/common/ErrorAlert';
import { PageHeader } from '@/components/common/PageHeader';
import { CampaignBriefForm } from '@/components/generate/CampaignBriefForm';
import { GeneratedCopyPanel } from '@/components/generate/GeneratedCopyPanel';
import { WorkflowStepper } from '@/components/generate/WorkflowStepper';
import { useAuth } from '@/hooks/useAuth';
import { useGenerationRunner } from '@/hooks/useGenerationRunner';
import { useTaxonomy } from '@/hooks/useTaxonomy';
import type { GenerationCreatePayload, GenerationDetail } from '@/types/models';

export const GeneratePage = (): JSX.Element => {
  const { hasRole } = useAuth();
  const { brands, products, segments, isLoading, error: taxonomyError, reload } = useTaxonomy();
  const runner = useGenerationRunner();
  const [searchParams, setSearchParams] = useSearchParams();
  const [detail, setDetail] = useState<GenerationDetail | null>(null);

  const canGenerate = hasRole('admin', 'marketer');
  const trackedId = searchParams.get('generationId');

  // Deep link support: /generate?generationId=12 resumes an existing run.
  useEffect(() => {
    if (trackedId && Number(trackedId) !== runner.generationId) {
      runner.track(Number(trackedId));
    }
    // `runner` is recreated per render; tracking is keyed on the id alone.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trackedId]);

  // Once the workflow finishes, fetch the full record for titles and metadata.
  const status = runner.status;
  useEffect(() => {
    if (!runner.generationId || !status) return;
    if (status.status === 'pending' || status.status === 'running') return;
    let cancelled = false;
    void getGeneration(runner.generationId)
      .then((generation) => {
        if (!cancelled) setDetail(generation);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [runner.generationId, status]);

  const handleSubmit = useCallback(
    async (payload: GenerationCreatePayload) => {
      setDetail(null);
      const id = await runner.start(payload);
      if (id) setSearchParams({ generationId: String(id) }, { replace: true });
    },
    [runner, setSearchParams],
  );

  const handleRegenerate = useCallback(async () => {
    setDetail(null);
    const id = await runner.regenerate();
    if (id) setSearchParams({ generationId: String(id) }, { replace: true });
  }, [runner, setSearchParams]);

  const output = status?.output ?? null;

  return (
    <Box>
      <PageHeader
        title="Generate Copy"
        description="Create AI-powered marketing copy in seconds"
      />

      {!canGenerate && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Your account has read-only access. Ask an administrator for the marketer role to create
          new campaign copy.
        </Alert>
      )}

      <ErrorAlert error={taxonomyError} title="Could not load campaign options" onRetry={reload} />
      <ErrorAlert error={runner.error} title="Generation failed" />

      {status?.status === 'failed' && (
        <Alert severity="error" sx={{ mb: 2 }} role="alert">
          {status.error_message ?? 'The generation could not be completed.'} You can adjust the
          brief and try again.
        </Alert>
      )}

      <Stack direction={{ xs: 'column', lg: 'row' }} spacing={3} alignItems="flex-start">
        <Box sx={{ flex: 1, minWidth: 0, width: '100%' }}>
          {isLoading ? (
            <Skeleton variant="rounded" height={430} />
          ) : (
            <CampaignBriefForm
              brands={brands}
              products={products}
              segments={segments}
              isSubmitting={runner.isRunning}
              disabled={!canGenerate}
              canRegenerate={Boolean(runner.generationId) && canGenerate}
              onSubmit={(payload) => void handleSubmit(payload)}
              onRegenerate={() => void handleRegenerate()}
            />
          )}
        </Box>

        <Box sx={{ flex: 1, minWidth: 0, width: '100%' }}>
          <WorkflowStepper
            steps={status?.steps}
            progress={status?.progress ?? 0}
            isRunning={runner.isRunning}
          />
        </Box>
      </Stack>

      {output && (
        <Box sx={{ mt: 3 }}>
          <GeneratedCopyPanel
            output={output}
            generation={detail}
            executionTimeMs={status?.execution_time_ms}
            onRegenerate={canGenerate ? () => void handleRegenerate() : undefined}
            isRegenerating={runner.isRunning}
          />
        </Box>
      )}
    </Box>
  );
};
