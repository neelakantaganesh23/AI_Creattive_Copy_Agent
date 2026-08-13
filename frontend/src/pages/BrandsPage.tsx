import { Box, Chip, Tab, Tabs, Typography } from '@mui/material';
import { useEffect, useState } from 'react';

import {
  createBrand,
  createProduct,
  deleteBrand,
  deleteProduct,
  listBrands,
  listProducts,
  updateBrand,
  updateProduct,
} from '@/api/taxonomy';
import { ResourceManager } from '@/components/common/ResourceManager';
import { useAuth } from '@/hooks/useAuth';
import type { Brand, Product } from '@/types/models';

const ActiveChip = ({ active }: { active: boolean }): JSX.Element => (
  <Chip
    size="small"
    label={active ? 'Active' : 'Inactive'}
    color={active ? 'success' : 'default'}
    variant="outlined"
  />
);

export const BrandsPage = (): JSX.Element => {
  const { hasRole } = useAuth();
  const canManage = hasRole('admin');
  const [tab, setTab] = useState<'brands' | 'products'>('brands');
  const [brandOptions, setBrandOptions] = useState<Array<{ value: string; label: string }>>([]);

  useEffect(() => {
    let cancelled = false;
    void listBrands()
      .then((page) => {
        if (cancelled) return;
        setBrandOptions(page.items.map((brand) => ({ value: String(brand.id), label: brand.name })));
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [tab]);

  return (
    <Box>
      <Tabs
        value={tab}
        onChange={(_event, next: 'brands' | 'products') => setTab(next)}
        sx={{ mb: 2 }}
        aria-label="Brands and products"
      >
        <Tab value="brands" label="Brands" />
        <Tab value="products" label="Products" />
      </Tabs>

      {tab === 'brands' ? (
        <ResourceManager<Brand>
          title="Brands"
          description="Brand identity and guidelines used to steer generated copy"
          entityName="brand"
          canManage={canManage}
          columns={[
            {
              key: 'name',
              label: 'Name',
              render: (row) => (
                <Typography variant="body2" fontWeight={600}>
                  {row.name}
                </Typography>
              ),
            },
            { key: 'description', label: 'Description', render: (row) => row.description ?? '--' },
            { key: 'guidelines', label: 'Guidelines', render: (row) => row.guidelines ?? '--' },
            {
              key: 'active',
              label: 'Status',
              render: (row) => <ActiveChip active={row.is_active} />,
            },
          ]}
          fields={[
            { name: 'name', label: 'Brand name', type: 'text', required: true },
            { name: 'description', label: 'Description', type: 'multiline' },
            {
              name: 'guidelines',
              label: 'Brand guidelines',
              type: 'multiline',
              helperText: 'Constraints the copy generation agent must respect.',
            },
            { name: 'is_active', label: 'Active', type: 'switch', defaultValue: true },
          ]}
          load={async () => (await listBrands()).items}
          create={(payload) => createBrand(payload as Partial<Brand>)}
          update={(id, payload) => updateBrand(id, payload as Partial<Brand>)}
          remove={deleteBrand}
          toFormValues={(row) => ({
            name: row.name,
            description: row.description ?? '',
            guidelines: row.guidelines ?? '',
            is_active: row.is_active,
          })}
        />
      ) : (
        <ResourceManager<Product>
          title="Products"
          description="Products available for selection on the campaign brief"
          entityName="product"
          canManage={canManage}
          columns={[
            {
              key: 'name',
              label: 'Name',
              render: (row) => (
                <Typography variant="body2" fontWeight={600}>
                  {row.name}
                </Typography>
              ),
            },
            { key: 'brand', label: 'Brand', render: (row) => row.brand_name ?? '--' },
            { key: 'sku', label: 'SKU', render: (row) => row.sku ?? '--' },
            { key: 'features', label: 'Features', render: (row) => row.features ?? '--' },
            {
              key: 'active',
              label: 'Status',
              render: (row) => <ActiveChip active={row.is_active} />,
            },
          ]}
          fields={[
            {
              name: 'brand_id',
              label: 'Brand',
              type: 'select',
              required: true,
              options: brandOptions,
            },
            { name: 'name', label: 'Product name', type: 'text', required: true },
            { name: 'sku', label: 'SKU', type: 'text' },
            { name: 'description', label: 'Description', type: 'multiline' },
            {
              name: 'features',
              label: 'Features',
              type: 'text',
              helperText: 'Comma separated, for example: lightweight, breathable, speed',
            },
            { name: 'is_active', label: 'Active', type: 'switch', defaultValue: true },
          ]}
          load={async () => (await listProducts()).items}
          create={(payload) =>
            createProduct({
              ...payload,
              brand_id: Number(payload.brand_id),
            } as Partial<Product>)
          }
          update={(id, payload) =>
            updateProduct(id, {
              ...payload,
              brand_id: Number(payload.brand_id),
            } as Partial<Product>)
          }
          remove={deleteProduct}
          toFormValues={(row) => ({
            brand_id: String(row.brand_id),
            name: row.name,
            sku: row.sku ?? '',
            description: row.description ?? '',
            features: row.features ?? '',
            is_active: row.is_active,
          })}
        />
      )}
    </Box>
  );
};
