import { Alert, Box, Chip, Stack, Typography } from '@mui/material';

import { createRule, deleteRule, listRules, updateRule } from '@/api/rules';
import { ResourceManager } from '@/components/common/ResourceManager';
import { useAuth } from '@/hooks/useAuth';
import type { Rule } from '@/types/models';
import { CHANNEL_LABELS, FIELD_LABELS, RULE_TYPE_LABELS, RULE_VALUE_HINTS } from '@/utils/format';

const RULE_TYPE_OPTIONS = Object.entries(RULE_TYPE_LABELS).map(([value, label]) => ({
  value,
  label,
}));

const FIELD_OPTIONS = Object.entries(FIELD_LABELS).map(([value, label]) => ({ value, label }));

const VALUE_HELPER = Object.entries(RULE_VALUE_HINTS)
  .map(([type, hint]) => `${RULE_TYPE_LABELS[type as Rule['rule_type']]}: ${hint}`)
  .join(' · ');

export const RulesPage = (): JSX.Element => {
  const { hasRole } = useAuth();

  return (
    <Box>
      <Alert severity="info" sx={{ mb: 2 }}>
        Rules are applied while the copy is written, not after. Anything measurable — character
        and word counts, banned or required terms, patterns — is checked in code and the model is
        asked to rewrite until it complies. <strong>Guideline</strong> rules are natural language
        and are assessed by the AI judge in the Content Validation stage. An <em>error</em> rule
        triggers a rewrite; a <em>warning</em> rule is reported but accepted.
      </Alert>

      <ResourceManager<Rule>
        title="Content Rules"
        description="Constraints every generated campaign must satisfy"
        entityName="rule"
        canManage={hasRole('admin')}
        columns={[
          {
            key: 'name',
            label: 'Rule',
            render: (row) => (
              <Stack spacing={0.25}>
                <Typography variant="body2" fontWeight={600}>
                  {row.name}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {RULE_TYPE_LABELS[row.rule_type]}
                </Typography>
              </Stack>
            ),
          },
          {
            key: 'value',
            label: 'Value',
            render: (row) => (
              <Typography variant="body2" sx={{ maxWidth: 320 }}>
                {row.value}
              </Typography>
            ),
          },
          {
            key: 'scope',
            label: 'Applies to',
            render: (row) => (
              <Typography variant="body2">
                {row.channel ? CHANNEL_LABELS[row.channel] : 'All channels'}
                {' · '}
                {row.field_name ? (FIELD_LABELS[row.field_name] ?? row.field_name) : 'All fields'}
              </Typography>
            ),
          },
          {
            key: 'severity',
            label: 'Severity',
            render: (row) => (
              <Chip
                size="small"
                label={row.severity === 'error' ? 'Error' : 'Warning'}
                color={row.severity === 'error' ? 'error' : 'warning'}
                variant="outlined"
              />
            ),
          },
          { key: 'priority', label: 'Priority', render: (row) => row.priority },
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
            name: 'name',
            label: 'Name',
            type: 'text',
            required: true,
            helperText: 'For example: CTA word count',
          },
          {
            name: 'rule_type',
            label: 'Rule type',
            type: 'select',
            required: true,
            options: RULE_TYPE_OPTIONS,
            defaultValue: 'max_chars',
          },
          {
            name: 'value',
            label: 'Value',
            type: 'multiline',
            required: true,
            helperText: VALUE_HELPER,
          },
          {
            name: 'severity',
            label: 'Severity',
            type: 'select',
            required: true,
            defaultValue: 'error',
            options: [
              { value: 'error', label: 'Error — rewrite until it passes' },
              { value: 'warning', label: 'Warning — report only' },
            ],
          },
          {
            name: 'channel',
            label: 'Channel (blank = all)',
            type: 'select',
            options: Object.entries(CHANNEL_LABELS).map(([value, label]) => ({ value, label })),
          },
          {
            name: 'field_name',
            label: 'Field (blank = all)',
            type: 'select',
            options: FIELD_OPTIONS,
          },
          { name: 'brand_id', label: 'Brand id (optional)', type: 'number' },
          {
            name: 'audience_segment_id',
            label: 'Audience segment id (optional)',
            type: 'number',
          },
          {
            name: 'priority',
            label: 'Priority',
            type: 'number',
            required: true,
            defaultValue: 50,
            helperText: 'Higher is applied first.',
          },
          { name: 'description', label: 'Description', type: 'multiline' },
          { name: 'is_active', label: 'Active', type: 'switch', defaultValue: true },
        ]}
        load={async () => (await listRules()).items}
        create={(payload) => createRule(payload as Partial<Rule>)}
        update={(id, payload) => updateRule(id, payload as Partial<Rule>)}
        remove={deleteRule}
        toFormValues={(row) => ({
          name: row.name,
          rule_type: row.rule_type,
          value: row.value,
          severity: row.severity,
          channel: row.channel ?? '',
          field_name: row.field_name ?? '',
          brand_id: row.brand_id ?? '',
          audience_segment_id: row.audience_segment_id ?? '',
          priority: row.priority,
          description: row.description ?? '',
          is_active: row.is_active,
        })}
      />
    </Box>
  );
};
