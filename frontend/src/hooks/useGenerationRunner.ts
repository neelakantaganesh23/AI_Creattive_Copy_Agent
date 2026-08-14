import { useCallback, useEffect, useRef, useState } from 'react';

import { type ApiError, toApiError } from '@/api/client';
import {
  createGeneration,
  getGenerationStatus,
  regenerateGeneration,
} from '@/api/generations';
import { env } from '@/config/env';
import type {
  AgentExecution,
  GenerationCreatePayload,
  GenerationStatusResponse,
} from '@/types/models';

const TERMINAL_STATUSES = new Set(['completed', 'partial', 'failed']);

/** Placeholder stepper rows shown before the backend has reported anything. */
export const PENDING_STEPS: Array<Pick<AgentExecution, 'agent_name' | 'title' | 'description'>> = [
  {
    agent_name: 'data_extraction',
    title: 'Data Extraction',
    description: 'Extracting brand, products, SKUs and athlete mentions',
  },
  {
    agent_name: 'web_search_grounding',
    title: 'Web Search Grounding',
    description: 'Finding relevant real-world context',
  },
  {
    agent_name: 'copy_generation',
    title: 'Copy Generation',
    description: 'Generating personalized marketing copy',
  },
  {
    agent_name: 'repetition_fix',
    title: 'Repetition Fix',
    description: 'Checking and fixing repetitive content',
  },
  {
    agent_name: 'cta_optimization',
    title: 'CTA Optimization',
    description: 'Applying CTA rules and brand guidelines',
  },
  {
    agent_name: 'image_generation',
    title: 'Image Generation',
    description: 'Generating a campaign visual from the brief',
  },
  {
    agent_name: 'content_validation',
    title: 'Content Validation',
    description: 'Judging copy against the configured content rules',
  },
  {
    agent_name: 'output_parsing',
    title: 'Output Parsing & Logging',
    description: 'Parsing output and logging execution details',
  },
];

export interface GenerationRunnerState {
  generationId: number | null;
  status: GenerationStatusResponse | null;
  isSubmitting: boolean;
  isRunning: boolean;
  error: ApiError | null;
  start: (payload: GenerationCreatePayload) => Promise<number | null>;
  regenerate: () => Promise<number | null>;
  track: (generationId: number) => void;
  reset: () => void;
}

/**
 * Starts a generation and polls its status endpoint until the workflow reaches a
 * terminal state, so the stepper can show live progress (§8).
 */
export const useGenerationRunner = (): GenerationRunnerState => {
  const [generationId, setGenerationId] = useState<number | null>(null);
  const [status, setStatus] = useState<GenerationStatusResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cancelledRef = useRef(false);

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const poll = useCallback(
    async (id: number): Promise<void> => {
      if (cancelledRef.current) return;
      try {
        const next = await getGenerationStatus(id);
        if (cancelledRef.current) return;
        setStatus(next);
        if (!TERMINAL_STATUSES.has(next.status)) {
          timerRef.current = setTimeout(() => void poll(id), env.pollIntervalMs);
        }
      } catch (caught) {
        if (cancelledRef.current) return;
        setError(toApiError(caught));
      }
    },
    [],
  );

  useEffect(() => {
    cancelledRef.current = false;
    return () => {
      cancelledRef.current = true;
      clearTimer();
    };
  }, [clearTimer]);

  const track = useCallback(
    (id: number) => {
      clearTimer();
      setGenerationId(id);
      setStatus(null);
      setError(null);
      void poll(id);
    },
    [clearTimer, poll],
  );

  const start = useCallback(
    async (payload: GenerationCreatePayload): Promise<number | null> => {
      clearTimer();
      setIsSubmitting(true);
      setError(null);
      setStatus(null);
      try {
        const generation = await createGeneration(payload);
        setGenerationId(generation.id);
        void poll(generation.id);
        return generation.id;
      } catch (caught) {
        setError(toApiError(caught));
        return null;
      } finally {
        setIsSubmitting(false);
      }
    },
    [clearTimer, poll],
  );

  const regenerate = useCallback(async (): Promise<number | null> => {
    if (generationId === null) return null;
    clearTimer();
    setIsSubmitting(true);
    setError(null);
    try {
      const generation = await regenerateGeneration(generationId);
      setStatus(null);
      setGenerationId(generation.id);
      void poll(generation.id);
      return generation.id;
    } catch (caught) {
      setError(toApiError(caught));
      return null;
    } finally {
      setIsSubmitting(false);
    }
  }, [clearTimer, generationId, poll]);

  const reset = useCallback(() => {
    clearTimer();
    setGenerationId(null);
    setStatus(null);
    setError(null);
  }, [clearTimer]);

  const isRunning =
    isSubmitting || (status !== null && !TERMINAL_STATUSES.has(status.status)) ||
    (generationId !== null && status === null && error === null);

  return {
    generationId,
    status,
    isSubmitting,
    isRunning,
    error,
    start,
    regenerate,
    track,
    reset,
  };
};
