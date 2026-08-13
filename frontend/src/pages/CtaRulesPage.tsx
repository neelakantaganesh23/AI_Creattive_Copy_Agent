import { Alert, Box, Chip, Typography } from '@mui/material';

import { createCtaRule, deleteCtaRule, listCtaRules, updateCtaRule } from '@/api/taxonomy';
import { ResourceManager } from '@/components/common/ResourceManager';
import { useAuth } from '@/hooks/useAuth';
import type { CtaRule } from '@/types/models';
import { CHANNEL_LABELS } from '@/utils/format';

export const CtaRulesPage = (): JSX.Element => {
  const { hasRole } = useAuth();

  return (
    <Box>
      <Alert severity="info" sx={{ mb: 2 }}>
        CTA rules are deterministic. The highest-priority active rule whose placeholders can all be
        resolved wins. Supported placeholders: <code>{'{product}'}</code>, <code>{'{brand}'}</code>,{' '}
        <code>{'{channel}'}</code>, <code>{'{audience}'}</code>.
      </Alert>

      <ResourceManager<CtaRule>
        title="CTA Rules"
        description="Deterministic call-to-action rules applied after copy generation"
        entityName="rule"
        canManage={hasRole('admin')}
        columns={[
          {
            key: 'template',
            label: 'Template',
            render: (row) => (
              <Typography variant="body2" fontWeight={600}>
                {row.template}
              </Typography>
            ),
          },
          { key: 'priority', label: 'Priority', render: (row) => row.priority },
          {
            key: 'channel',
            label: 'Channel',
            render: (row) => (row.channel ? CHANNEL_LABELS[row.channel] : 'Any'),
          },
          { key: 'brand', label: 'Brand', render: (row) => row.brand_id ?? 'Any' },
          { key: 'product', label: 'Product', render: (row) => row.product_id ?? 'Any' },
          {
            key: 'active',
            label: 'Status',
            render: (row) => (
              <Chip
                size="small"
                label={row.is_active ? 'Active' : 'Inactive'}
                color={row.is_active ? 'success' : 'default'}
                variant="outlined"
              />
            ),
          },
        ]}
        fields={[
          {
            name: 'template',
            label: 'Template',
            type: 'text',
            required: true,
            helperText: 'For example: SHOP {product}',
          },
          {
            name: 'priority',
            label: 'Priority',
            type: 'number',
            required: true,
            defaultValue: 50,
            helperText: 'Higher wins.',
          },
          {
            name: 'channel',
            label: 'Channel',
            type: 'select',
            options: Object.entries(CHANNEL_LABELS).map(([value, label]) => ({ value, label })),
          },
          { name: 'brand_id', label: 'Brand id (optional)', type: 'number' },
          { name: 'product_id', label: 'Product id (optional)', type: 'number' },
          { name: 'is_active', label: 'Active', type: 'switch', defaultValue: true },
        ]}
        load={async () => (await listCtaRules()).items}
        create={(payload) => createCtaRule(payload as Partial<CtaRule>)}
        update={(id, payload) => updateCtaRule(id, payload as Partial<CtaRule>)}
        remove={deleteCtaRule}
        toFormValues={(row) => ({
          template: row.template,
          priority: row.priority,
          channel: row.channel ?? '',
          brand_id: row.brand_id ?? '',
          product_id: row.product_id ?? '',
          is_active: row.is_active,
        })}
      />
    </Box>
  );
};
