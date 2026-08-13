import {
  Box,
  Button,
  Card,
  CardContent,
  IconButton,
  Skeleton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from '@mui/material';
import { Clock, Eye } from 'lucide-react';
import { Link } from 'react-router-dom';

import { EmptyState } from '@/components/common/EmptyState';
import { StatusChip } from '@/components/common/StatusChip';
import type { GenerationSummary } from '@/types/models';
import { CHANNEL_LABELS, formatDateTime, truncate } from '@/utils/format';

interface RecentGenerationsTableProps {
  items: GenerationSummary[];
  isLoading: boolean;
  showViewAll?: boolean;
}

export const RecentGenerationsTable = ({
  items,
  isLoading,
  showViewAll = true,
}: RecentGenerationsTableProps): JSX.Element => (
  <Card component="section" aria-labelledby="recent-generations-heading">
    <CardContent sx={{ p: { xs: 2, md: 3 } }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Stack direction="row" spacing={1.25} alignItems="center">
          <Box sx={{ color: 'primary.main', display: 'flex' }} aria-hidden>
            <Clock size={18} />
          </Box>
          <Typography variant="h5" component="h2" id="recent-generations-heading">
            Recent Generations
          </Typography>
        </Stack>
        {showViewAll && (
          <Button component={Link} to="/history" size="small" variant="outlined">
            View All
          </Button>
        )}
      </Stack>

      {isLoading ? (
        <Stack spacing={1}>
          {[0, 1, 2].map((key) => (
            <Skeleton key={key} variant="rounded" height={44} />
          ))}
        </Stack>
      ) : items.length === 0 ? (
        <EmptyState
          title="No generations yet."
          description="Create your first campaign to get started."
        />
      ) : (
        <Box sx={{ overflowX: 'auto' }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Campaign / Brief</TableCell>
                <TableCell>Brand / Product</TableCell>
                <TableCell>Channel</TableCell>
                <TableCell>Audience Segment</TableCell>
                <TableCell>Generated On</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">View</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.map((item) => (
                <TableRow key={item.id} hover>
                  <TableCell sx={{ maxWidth: 260 }}>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {truncate(item.title, 60)}
                    </Typography>
                  </TableCell>
                  <TableCell>{item.product_name ?? item.brand_name ?? '--'}</TableCell>
                  <TableCell>{CHANNEL_LABELS[item.channel]}</TableCell>
                  <TableCell>{item.audience_segment_name ?? '--'}</TableCell>
                  <TableCell>{formatDateTime(item.created_at)}</TableCell>
                  <TableCell>
                    <StatusChip status={item.status} />
                  </TableCell>
                  <TableCell align="right">
                    <Tooltip title="View generation">
                      <IconButton
                        component={Link}
                        to={`/history/${item.id}`}
                        size="small"
                        aria-label={`View generation ${item.title}`}
                      >
                        <Eye size={16} />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>
      )}
    </CardContent>
  </Card>
);
