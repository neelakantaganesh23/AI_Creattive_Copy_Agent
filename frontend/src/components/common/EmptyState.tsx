import { Box, Stack, Typography } from '@mui/material';
import { Inbox } from 'lucide-react';
import type { ReactNode } from 'react';

interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
}

export const EmptyState = ({ title, description, icon, action }: EmptyStateProps): JSX.Element => (
  <Stack alignItems="center" justifyContent="center" spacing={1.5} sx={{ py: 6, px: 2 }}>
    <Box aria-hidden sx={{ color: 'text.disabled' }}>
      {icon ?? <Inbox size={40} strokeWidth={1.5} />}
    </Box>
    <Typography variant="body1" sx={{ fontWeight: 600 }}>
      {title}
    </Typography>
    {description && (
      <Typography variant="body2" color="text.secondary" textAlign="center">
        {description}
      </Typography>
    )}
    {action}
  </Stack>
);
