import { Box, Card, CardContent, Skeleton, Stack, Typography } from '@mui/material';
import { Clock, FileText, Megaphone, Users } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

import type { DashboardSummary } from '@/types/models';
import { formatDuration } from '@/utils/format';

interface SummaryCardsProps {
  summary: DashboardSummary | null;
  isLoading: boolean;
}

interface Metric {
  label: string;
  value: string;
  caption: string;
  icon: LucideIcon;
  tint: string;
  color: string;
}

const buildMetrics = (summary: DashboardSummary): Metric[] => [
  {
    label: 'Copies Generated',
    value: String(summary.copies_generated_this_month),
    caption: 'This Month',
    icon: FileText,
    tint: '#EEF0FF',
    color: '#4B3BC4',
  },
  {
    label: 'Audience Segments',
    value: String(summary.audience_segments_configured),
    caption: 'Configured',
    icon: Users,
    tint: '#E7F6EE',
    color: '#12734A',
  },
  {
    label: 'Channels Supported',
    value: String(summary.channels_supported),
    caption: summary.channels.map((channel) => channel.label).join(', '),
    icon: Megaphone,
    tint: '#E8F1FF',
    color: '#175CD3',
  },
  {
    label: 'Avg. Generation Time',
    value: formatDuration(summary.average_generation_time_ms),
    caption: 'Per Request',
    icon: Clock,
    tint: '#FEF3E2',
    color: '#B54708',
  },
];

export const SummaryCards = ({ summary, isLoading }: SummaryCardsProps): JSX.Element => {
  if (isLoading || !summary) {
    return (
      <Box
        sx={{
          display: 'grid',
          gap: 2,
          gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', lg: 'repeat(4, 1fr)' },
        }}
      >
        {[0, 1, 2, 3].map((key) => (
          <Skeleton key={key} variant="rounded" height={104} />
        ))}
      </Box>
    );
  }

  return (
    <Box
      sx={{
        display: 'grid',
        gap: 2,
        gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', lg: 'repeat(4, 1fr)' },
      }}
    >
      {buildMetrics(summary).map(({ label, value, caption, icon: Icon, tint, color }) => (
        <Card key={label}>
          <CardContent sx={{ p: 2.25 }}>
            <Stack direction="row" spacing={1.75} alignItems="center">
              <Box
                aria-hidden
                sx={{
                  width: 42,
                  height: 42,
                  borderRadius: 2,
                  bgcolor: tint,
                  color,
                  display: 'grid',
                  placeItems: 'center',
                  flexShrink: 0,
                }}
              >
                <Icon size={20} />
              </Box>
              <Box sx={{ minWidth: 0 }}>
                <Typography variant="caption" color="text.secondary" noWrap component="p">
                  {label}
                </Typography>
                <Typography variant="h3" component="p" sx={{ lineHeight: 1.2 }}>
                  {value}
                </Typography>
                <Typography variant="caption" color="text.secondary" noWrap component="p">
                  {caption}
                </Typography>
              </Box>
            </Stack>
          </CardContent>
        </Card>
      ))}
    </Box>
  );
};
