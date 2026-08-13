import { useCallback, useEffect, useState } from 'react';

import { type ApiError, toApiError } from '@/api/client';
import { listAudienceSegments, listBrands, listProducts } from '@/api/taxonomy';
import type { AudienceSegment, Brand, Product } from '@/types/models';

interface TaxonomyState {
  brands: Brand[];
  products: Product[];
  segments: AudienceSegment[];
  isLoading: boolean;
  error: ApiError | null;
  reload: () => void;
}

/** Loads the active brand/product and audience options used by the brief form. */
export const useTaxonomy = (): TaxonomyState => {
  const [brands, setBrands] = useState<Brand[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [segments, setSegments] = useState<AudienceSegment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const load = async (): Promise<void> => {
      setIsLoading(true);
      setError(null);
      try {
        const [brandPage, productPage, segmentPage] = await Promise.all([
          listBrands({ is_active: true }),
          listProducts({ is_active: true }),
          listAudienceSegments({ is_active: true }),
        ]);
        if (cancelled) return;
        setBrands(brandPage.items);
        setProducts(productPage.items);
        setSegments(segmentPage.items);
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

  const reload = useCallback(() => setReloadToken((token) => token + 1), []);

  return { brands, products, segments, isLoading, error, reload };
};
