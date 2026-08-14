import { apiClient } from '@/api/client';
import type { Page, Rule } from '@/types/models';

interface ListParams {
  page?: number;
  page_size?: number;
  is_active?: boolean;
}

export const listRules = async (params: ListParams = {}): Promise<Page<Rule>> => {
  const { data } = await apiClient.get<Page<Rule>>('/rules', {
    params: { page_size: 100, ...params },
  });
  return data;
};

export const createRule = async (payload: Partial<Rule>): Promise<Rule> =>
  (await apiClient.post<Rule>('/rules', payload)).data;

export const updateRule = async (id: number, payload: Partial<Rule>): Promise<Rule> =>
  (await apiClient.put<Rule>(`/rules/${id}`, payload)).data;

export const deleteRule = async (id: number): Promise<void> => {
  await apiClient.delete(`/rules/${id}`);
};
