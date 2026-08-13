import { Box, Card, CardContent, Stack, Typography } from '@mui/material';
import { Mail, MessageSquare, Radio, Smartphone } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

import type { ChannelInfo } from '@/types/models';

const ICONS: Record<string, LucideIcon> = {
  email: Mail,
  mobile: Smartphone,
  sms: MessageSquare,
};

export const SupportedChannels = ({ channels }: { channels: ChannelInfo[] }): JSX.Element => (
  <Card component="section" aria-labelledby="supported-channels-heading">
    <CardContent sx={{ p: { xs: 2, md: 3 } }}>
      <Stack direction="row" spacing={1.25} alignItems="center" sx={{ mb: 2 }}>
        <Box sx={{ color: 'primary.main', display: 'flex' }} aria-hidden>
          <Radio size={18} />
        </Box>
        <Typography variant="h5" component="h2" id="supported-channels-heading">
          Supported Channels
        </Typography>
      </Stack>

      <Stack spacing={2}>
        {channels.map((channel) => {
          const Icon = ICONS[channel.value] ?? Mail;
          return (
            <Stack key={channel.value} direction="row" spacing={1.5} alignItems="flex-start">
              <Box
                aria-hidden
                sx={{
                  width: 34,
                  height: 34,
                  borderRadius: 1.5,
                  bgcolor: '#F4F1FF',
                  color: 'primary.main',
                  display: 'grid',
                  placeItems: 'center',
                  flexShrink: 0,
                }}
              >
                <Icon size={17} />
              </Box>
              <Box>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  {channel.label}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {channel.description}
                </Typography>
              </Box>
            </Stack>
          );
        })}
      </Stack>
    </CardContent>
  </Card>
);
