import {
  Box,
  Button,
  Card,
  CardContent,
  Dialog,
  DialogContent,
  DialogTitle,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import { Eye, Trash2, X } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { type ApiError, toApiError } from '@/api/client';
import { deleteGeneration, getGeneration, listGenerations } from '@/api/generations';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorAlert } from '@/components/common/ErrorAlert';
import { PageHeader } from '@/components/common/PageHeader';
import { StatusChip } from '@/components/common/StatusChip';
import { GeneratedCopyPanel } from '@/components/generate/GeneratedCopyPanel';
import { WorkflowStepper } from '@/components/generate/WorkflowStepper';
import { useAuth } from '@/hooks/useAuth';
import type { GenerationDetail, GenerationSummary } from '@/types/models';
import { CHANNEL_LABELS, formatDateTime, formatDuration, truncate } from '@/utils/format';

const STATUS_OPTIONS = ['pending', 'running', 'completed', 'partial', 'failed'] as const;

export const HistoryPage = (): JSX.Element => {
  const { generationId } = useParams();
  const navigate = useNavigate();
  const { hasRole } = useAuth();

  const [items, setItems] = useState<GenerationSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [channel, setChannel] = useState('');
  const [status, setStatus] = useState('');
  const [search, setSearch] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const [detail, setDetail] = useState<GenerationDetail | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const load = async (): Promise<void> => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await listGenerations({
          page: page + 1,
          page_size: pageSize,
          channel: channel || undefined,
          status: status || undefined,
          search: search || undefined,
        });
        if (cancelled) return;
        setItems(data.items);
        setTotal(data.total);
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
  }, [page, pageSize, channel, status, search, reloadToken]);

  useEffect(() => {
    if (!generationId) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    void getGeneration(Number(generationId))
      .then((data) => {
        if (!cancelled) setDetail(data);
      })
      .catch((caught) => {
        if (!cancelled) setError(toApiError(caught));
      });
    return () => {
      cancelled = true;
    };
  }, [generationId]);

  const handleDelete = useCallback(async (id: number) => {
    try {
      await deleteGeneration(id);
      setReloadToken((token) => token + 1);
    } catch (caught) {
      setError(toApiError(caught));
    }
  }, []);

  return (
    <Box>
      <PageHeader title="History" description="Every generation you have run" />

      <ErrorAlert error={error} onRetry={() => setReloadToken((token) => token + 1)} />

      <Card>
        <CardContent sx={{ p: { xs: 2, md: 3 } }}>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} sx={{ mb: 2 }}>
            <TextField
              label="Search briefs"
              size="small"
              value={search}
              onChange={(event) => {
                setPage(0);
                setSearch(event.target.value);
              }}
              sx={{ minWidth: 220 }}
            />
            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel id="history-channel">Channel</InputLabel>
              <Select
                labelId="history-channel"
                label="Channel"
                value={channel}
                onChange={(event) => {
                  setPage(0);
                  setChannel(event.target.value);
                }}
              >
                <MenuItem value="">All channels</MenuItem>
                {Object.entries(CHANNEL_LABELS).map(([value, label]) => (
                  <MenuItem key={value} value={value}>
                    {label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel id="history-status">Status</InputLabel>
              <Select
                labelId="history-status"
                label="Status"
                value={status}
                onChange={(event) => {
                  setPage(0);
                  setStatus(event.target.value);
                }}
              >
                <MenuItem value="">All statuses</MenuItem>
                {STATUS_OPTIONS.map((value) => (
                  <MenuItem key={value} value={value}>
                    {value}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Stack>

          {!isLoading && items.length === 0 ? (
            <EmptyState
              title="No generations found"
              description="Adjust your filters or create a new campaign."
              action={
                <Button variant="contained" onClick={() => navigate('/generate')}>
                  Generate copy
                </Button>
              }
            />
          ) : (
            <Box sx={{ overflowX: 'auto' }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Campaign / Brief</TableCell>
                    <TableCell>Brand / Product</TableCell>
                    <TableCell>Channel</TableCell>
                    <TableCell>Audience</TableCell>
                    <TableCell>Duration</TableCell>
                    <TableCell>Generated On</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {items.map((item) => (
                    <TableRow key={item.id} hover>
                      <TableCell sx={{ maxWidth: 280 }}>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {truncate(item.title, 70)}
                        </Typography>
                      </TableCell>
                      <TableCell>{item.product_name ?? item.brand_name ?? '--'}</TableCell>
                      <TableCell>{CHANNEL_LABELS[item.channel]}</TableCell>
                      <TableCell>{item.audience_segment_name ?? '--'}</TableCell>
                      <TableCell>{formatDuration(item.execution_time_ms)}</TableCell>
                      <TableCell>{formatDateTime(item.created_at)}</TableCell>
                      <TableCell>
                        <StatusChip status={item.status} />
                      </TableCell>
                      <TableCell align="right">
                        <Tooltip title="View details">
                          <IconButton
                            size="small"
                            aria-label={`View generation ${item.title}`}
                            onClick={() => navigate(`/history/${item.id}`)}
                          >
                            <Eye size={16} />
                          </IconButton>
                        </Tooltip>
                        {hasRole('admin', 'marketer') && (
                          <Tooltip title="Delete">
                            <IconButton
                              size="small"
                              aria-label={`Delete generation ${item.title}`}
                              onClick={() => void handleDelete(item.id)}
                            >
                              <Trash2 size={16} />
                            </IconButton>
                          </Tooltip>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
          )}

          <TablePagination
            component="div"
            count={total}
            page={page}
            onPageChange={(_event, next) => setPage(next)}
            rowsPerPage={pageSize}
            onRowsPerPageChange={(event) => {
              setPageSize(Number(event.target.value));
              setPage(0);
            }}
            rowsPerPageOptions={[10, 25, 50]}
          />
        </CardContent>
      </Card>

      <Dialog
        open={Boolean(generationId)}
        onClose={() => navigate('/history')}
        maxWidth="lg"
        fullWidth
        scroll="body"
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box sx={{ flex: 1 }}>{detail?.title ?? 'Generation detail'}</Box>
          <IconButton onClick={() => navigate('/history')} aria-label="Close details">
            <X size={18} />
          </IconButton>
        </DialogTitle>
        <DialogContent dividers>
          {detail ? (
            <Stack spacing={2.5}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="caption" color="text.secondary">
                    Campaign brief
                  </Typography>
                  <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', mt: 0.5 }}>
                    {detail.brief}
                  </Typography>
                </CardContent>
              </Card>

              <WorkflowStepper steps={detail.agent_executions} />

              {detail.output ? (
                <GeneratedCopyPanel output={detail.output} generation={detail} />
              ) : (
                <EmptyState
                  title="No output was produced"
                  description={detail.error_message ?? 'This generation did not complete.'}
                />
              )}

              {detail.grounding_sources.length > 0 && (
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="h6" sx={{ mb: 1 }}>
                      Grounding sources
                    </Typography>
                    <Stack component="ul" sx={{ pl: 2, m: 0 }}>
                      {detail.grounding_sources.map((source) => (
                        <li key={source.id}>
                          <Typography variant="body2">
                            {source.title} — {source.url}
                          </Typography>
                        </li>
                      ))}
                    </Stack>
                  </CardContent>
                </Card>
              )}
            </Stack>
          ) : (
            <EmptyState title="Loading generation..." />
          )}
        </DialogContent>
      </Dialog>
    </Box>
  );
};
