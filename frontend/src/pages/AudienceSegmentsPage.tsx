import { Chip, Typography } from '@mui/material';

import {
  createAudienceSegment,
  deleteAudienceSegment,
  listAudienceSegments,
  updateAudienceSegment,
} from '@/api/taxonomy';
import { ResourceManager } from '@/components/common/ResourceManager';
import { useAuth } from '@/hooks/useAuth';
import type { AudienceSegment } from '@/types/models';

export const AudienceSegmentsPage = (): JSX.Element => {
  const { hasRole } = useAuth();

  return (
    <ResourceManager<AudienceSegment>
      title="Audience Segments"
      description="Define who the copy is written for and how it should sound"
      entityName="segment"
      canManage={hasRole('admin')}
      columns={[
        {
          key: 'name',
          label: 'Name',
          render: (row) => <Typography variant="body2" fontWeight={600}>{row.name}</Typography>,
        },
        { key: 'description', label: 'Description', render: (row) => row.description ?? '--' },
        { key: 'tone', label: 'Tone guidance', render: (row) => row.tone_guidance ?? '--' },
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
        { name: 'name', label: 'Name', type: 'text', required: true },
        { name: 'description', label: 'Description', type: 'multiline' },
        {
          name: 'tone_guidance',
          label: 'Tone guidance',
          type: 'multiline',
          helperText: 'Passed to the copy generation agent as audience tone instructions.',
        },
        { name: 'is_active', label: 'Active', type: 'switch', defaultValue: true },
      ]}
      load={async () => (await listAudienceSegments()).items}
      create={(payload) => createAudienceSegment(payload as Partial<AudienceSegment>)}
      update={(id, payload) => updateAudienceSegment(id, payload as Partial<AudienceSegment>)}
      remove={deleteAudienceSegment}
      toFormValues={(row) => ({
        name: row.name,
        description: row.description ?? '',
        tone_guidance: row.tone_guidance ?? '',
        is_active: row.is_active,
      })}
    />
  );
};
