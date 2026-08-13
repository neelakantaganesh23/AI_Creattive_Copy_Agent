import { Chip, Typography } from '@mui/material';

import { createTemplate, deleteTemplate, listTemplates, updateTemplate } from '@/api/taxonomy';
import { ResourceManager } from '@/components/common/ResourceManager';
import { useAuth } from '@/hooks/useAuth';
import type { Template } from '@/types/models';
import { CHANNEL_LABELS, truncate } from '@/utils/format';

export const TemplatesPage = (): JSX.Element => {
  const { hasRole } = useAuth();

  return (
    <ResourceManager<Template>
      title="Templates"
      description="Reusable prompt guidance applied per channel during copy generation"
      entityName="template"
      canManage={hasRole('admin')}
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
        { key: 'channel', label: 'Channel', render: (row) => CHANNEL_LABELS[row.channel] },
        { key: 'description', label: 'Description', render: (row) => row.description ?? '--' },
        {
          key: 'prompt',
          label: 'Prompt',
          render: (row) => (
            <Typography variant="caption" color="text.secondary">
              {truncate(row.prompt_template, 90)}
            </Typography>
          ),
        },
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
        { name: 'name', label: 'Template name', type: 'text', required: true },
        {
          name: 'channel',
          label: 'Channel',
          type: 'select',
          required: true,
          options: Object.entries(CHANNEL_LABELS).map(([value, label]) => ({ value, label })),
          defaultValue: 'email',
        },
        { name: 'description', label: 'Description', type: 'multiline' },
        {
          name: 'prompt_template',
          label: 'Prompt template',
          type: 'multiline',
          required: true,
          helperText: 'Appended to the copy generation prompt for this channel.',
        },
        { name: 'is_active', label: 'Active', type: 'switch', defaultValue: true },
      ]}
      load={async () => (await listTemplates()).items}
      create={(payload) => createTemplate(payload as Partial<Template>)}
      update={(id, payload) => updateTemplate(id, payload as Partial<Template>)}
      remove={deleteTemplate}
      toFormValues={(row) => ({
        name: row.name,
        channel: row.channel,
        description: row.description ?? '',
        prompt_template: row.prompt_template,
        is_active: row.is_active,
      })}
    />
  );
};
