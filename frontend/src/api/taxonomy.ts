import { apiClient } from '@/api/client';
import type {
  AudienceSegment,
  Brand,
  CtaRule,
  Page,
  Product,
  Template,
} from '@/types/models';

interface ListParams {
  page?: number;
  page_size?: number;
  is_active?: boolean;
  brand_id?: number;
  channel?: string;
}

const list = async <T>(path: string, params: ListParams = {}): Promise<Page<T>> => {
  const { data } = await apiClient.get<Page<T>>(path, {
    params: { page_size: 100, ...params },
  });
  return data;
};

export const listBrands = (params?: ListParams) => list<Brand>('/brands', params);
export const listProducts = (params?: ListParams) => list<Product>('/products', params);
export const listAudienceSegments = (params?: ListParams) =>
  list<AudienceSegment>('/audience-segments', params);
export const listCtaRules = (params?: ListParams) => list<CtaRule>('/cta-rules', params);
export const listTemplates = (params?: ListParams) => list<Template>('/templates', params);

export const createBrand = async (payload: Partial<Brand>): Promise<Brand> =>
  (await apiClient.post<Brand>('/brands', payload)).data;
export const updateBrand = async (id: number, payload: Partial<Brand>): Promise<Brand> =>
  (await apiClient.put<Brand>(`/brands/${id}`, payload)).data;
export const deleteBrand = async (id: number): Promise<void> => {
  await apiClient.delete(`/brands/${id}`);
};

export const createProduct = async (payload: Partial<Product>): Promise<Product> =>
  (await apiClient.post<Product>('/products', payload)).data;
export const updateProduct = async (id: number, payload: Partial<Product>): Promise<Product> =>
  (await apiClient.put<Product>(`/products/${id}`, payload)).data;
export const deleteProduct = async (id: number): Promise<void> => {
  await apiClient.delete(`/products/${id}`);
};

export const createAudienceSegment = async (
  payload: Partial<AudienceSegment>,
): Promise<AudienceSegment> =>
  (await apiClient.post<AudienceSegment>('/audience-segments', payload)).data;
export const updateAudienceSegment = async (
  id: number,
  payload: Partial<AudienceSegment>,
): Promise<AudienceSegment> =>
  (await apiClient.put<AudienceSegment>(`/audience-segments/${id}`, payload)).data;
export const deleteAudienceSegment = async (id: number): Promise<void> => {
  await apiClient.delete(`/audience-segments/${id}`);
};

export const createCtaRule = async (payload: Partial<CtaRule>): Promise<CtaRule> =>
  (await apiClient.post<CtaRule>('/cta-rules', payload)).data;
export const updateCtaRule = async (id: number, payload: Partial<CtaRule>): Promise<CtaRule> =>
  (await apiClient.put<CtaRule>(`/cta-rules/${id}`, payload)).data;
export const deleteCtaRule = async (id: number): Promise<void> => {
  await apiClient.delete(`/cta-rules/${id}`);
};

export const createTemplate = async (payload: Partial<Template>): Promise<Template> =>
  (await apiClient.post<Template>('/templates', payload)).data;
export const updateTemplate = async (id: number, payload: Partial<Template>): Promise<Template> =>
  (await apiClient.put<Template>(`/templates/${id}`, payload)).data;
export const deleteTemplate = async (id: number): Promise<void> => {
  await apiClient.delete(`/templates/${id}`);
};
