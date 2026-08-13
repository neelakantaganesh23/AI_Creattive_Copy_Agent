import { apiClient } from '@/api/client';
import type {
  GenerationCreatePayload,
  GenerationDetail,
  GenerationStatusResponse,
  GenerationSummary,
  Page,
} from '@/types/models';

export interface GenerationListParams {
  page?: number;
  page_size?: number;
  channel?: string;
  status?: string;
  audience_segment_id?: number;
  brand_id?: number;
  search?: string;
}

export const createGeneration = async (
  payload: GenerationCreatePayload,
): Promise<GenerationDetail> => {
  const { data } = await apiClient.post<GenerationDetail>('/generations', payload);
  return data;
};

export const listGenerations = async (
  params: GenerationListParams = {},
): Promise<Page<GenerationSummary>> => {
  const { data } = await apiClient.get<Page<GenerationSummary>>('/generations', { params });
  return data;
};

export const getGeneration = async (id: number): Promise<GenerationDetail> => {
  const { data } = await apiClient.get<GenerationDetail>(`/generations/${id}`);
  return data;
};

export const getGenerationStatus = async (id: number): Promise<GenerationStatusResponse> => {
  const { data } = await apiClient.get<GenerationStatusResponse>(`/generations/${id}/status`);
  return data;
};

export const regenerateGeneration = async (id: number): Promise<GenerationDetail> => {
  const { data } = await apiClient.post<GenerationDetail>(`/generations/${id}/regenerate`, {});
  return data;
};

export const deleteGeneration = async (id: number): Promise<void> => {
  await apiClient.delete(`/generations/${id}`);
};
