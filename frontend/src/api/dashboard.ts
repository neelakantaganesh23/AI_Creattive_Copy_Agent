import { apiClient } from '@/api/client';
import type {
  AgentExecution,
  DashboardSummary,
  GenerationSummary,
  Page,
  SystemInfo,
} from '@/types/models';

export const getDashboardSummary = async (): Promise<DashboardSummary> => {
  const { data } = await apiClient.get<DashboardSummary>('/dashboard/summary');
  return data;
};

export const getRecentGenerations = async (limit = 5): Promise<GenerationSummary[]> => {
  const { data } = await apiClient.get<{ items: GenerationSummary[] }>('/dashboard/recent', {
    params: { limit },
  });
  return data.items;
};

export interface ExecutionLogParams {
  page?: number;
  page_size?: number;
  generation_id?: number;
  agent_name?: string;
  status?: string;
}

export const listExecutionLogs = async (
  params: ExecutionLogParams = {},
): Promise<Page<AgentExecution>> => {
  const { data } = await apiClient.get<Page<AgentExecution>>('/execution-logs', { params });
  return data;
};

/** ``/system/info`` sits outside the versioned prefix. */
export const getSystemInfo = async (): Promise<SystemInfo> => {
  const { data } = await apiClient.get<SystemInfo>('/system/info', {
    baseURL: apiClient.defaults.baseURL?.replace(/\/api\/v1$/, ''),
  });
  return data;
};
