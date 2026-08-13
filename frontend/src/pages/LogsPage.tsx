import {
  Box,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  LinearProgress,
  MenuItem,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TablePagination,
  TableRow,
  Typography,
} from '@mui/material';
import { useEffect, useState } from 'react';

import { type ApiError, toApiError } from '@/api/client';
import { getDashboardSummary, listExecutionLogs } from '@/api/dashboard';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorAlert } from '@/components/common/ErrorAlert';
import { PageHeader } from '@/components/common/PageHeader';
import { StatusChip } from '@/components/common/StatusChip';
import type { AgentExecution, DashboardSummary } from '@/types/models';
import { formatDateTime, formatDuration, formatPercent } from '@/utils/format';

const AGENT_OPTIONS = [
  'data_extraction',
  'web_search_grounding',
  'copy_generation',
  'repetition_fix',
  'cta_optimization',
  'output_parsing',
];

const STATUS_OPTIONS = ['pending', 'in_progress', 'completed', 'failed', 'skipped'];

export const LogsPage = (): JSX.Element => {
  const [logs, setLogs] = useState<AgentExecution[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(25);
  const [agentName, setAgentName] = useState('');
  const [status, setStatus] = useState('');
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async (): Promise<void> => {
      setIsLoading(true);
      setError(null);
      try {
        const [logPage, summaryData] = await Promise.all([
          listExecutionLogs({
            page: page + 1,
            page_size: pageSize,
            agent_name: agentName || undefined,
            status: status || undefined,
          }),
          getDashboardSummary(),
        ]);
        if (cancelled) return;
        setLogs(logPage.items);
        setTotal(logPage.total);
        setSummary(summaryData);
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
  }, [page, pageSize, agentName, status]);

  return (
    <Box>
      <PageHeader
        title="Logs & Analytics"
        description="Agent execution logs and workflow metrics"
      />

      <ErrorAlert error={error} />

      {summary && (
        <Box
          sx={{
            display: 'grid',
            gap: 2,
            gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)', lg: 'repeat(4, 1fr)' },
            mb: 3,
          }}
        >
          {[
            { label: 'Total generations', value: String(summary.copies_generated_total) },
            { label: 'Success rate', value: formatPercent(summary.success_rate) },
            {
              label: 'Average duration',
              value: formatDuration(summary.average_generation_time_ms),
            },
            {
              label: 'Failed runs',
              value: String(summary.generations_by_status.failed ?? 0),
            },
          ].map((metric) => (
            <Card key={metric.label}>
              <CardContent>
                <Typography variant="caption" color="text.secondary">
                  {metric.label}
                </Typography>
                <Typography variant="h3" component="p">
                  {metric.value}
                </Typography>
              </CardContent>
            </Card>
          ))}
        </Box>
      )}

      {summary && Object.keys(summary.generations_by_channel).length > 0 && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h5" component="h2" sx={{ mb: 2 }}>
              Generations by channel
            </Typography>
            <Stack spacing={1.5}>
              {Object.entries(summary.generations_by_channel).map(([channel, count]) => {
                const max = Math.max(...Object.values(summary.generations_by_channel), 1);
                return (
                  <Box key={channel}>
                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="body2" sx={{ textTransform: 'capitalize' }}>
                        {channel}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {count}
                      </Typography>
                    </Stack>
                    <LinearProgress
                      variant="determinate"
                      value={(count / max) * 100}
                      sx={{ height: 6, borderRadius: 1, mt: 0.5 }}
                      aria-label={`${count} generations for ${channel}`}
                    />
                  </Box>
                );
              })}
            </Stack>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent sx={{ p: { xs: 2, md: 3 } }}>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2 }}>
            <FormControl size="small" sx={{ minWidth: 200 }}>
              <InputLabel id="log-agent">Agent</InputLabel>
              <Select
                labelId="log-agent"
                label="Agent"
                value={agentName}
                onChange={(event) => {
                  setPage(0);
                  setAgentName(event.target.value);
                }}
              >
                <MenuItem value="">All agents</MenuItem>
                {AGENT_OPTIONS.map((value) => (
                  <MenuItem key={value} value={value}>
                    {value.replace(/_/g, ' ')}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 180 }}>
              <InputLabel id="log-status">Status</InputLabel>
              <Select
                labelId="log-status"
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
                    {value.replace(/_/g, ' ')}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Stack>

          {!isLoading && logs.length === 0 ? (
            <EmptyState
              title="No execution logs yet"
              description="Logs appear here after the first generation runs."
            />
          ) : (
            <Box sx={{ overflowX: 'auto' }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Generation</TableCell>
                    <TableCell>Agent</TableCell>
                    <TableCell>Model</TableCell>
                    <TableCell>Duration</TableCell>
                    <TableCell>Started</TableCell>
                    <TableCell>Status</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {logs.map((log) => (
                    <TableRow key={log.id} hover>
                      <TableCell>#{log.generation_id}</TableCell>
                      <TableCell>
                        <Typography variant="body2" fontWeight={600}>
                          {log.title}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {log.error_message ?? log.description}
                        </Typography>
                      </TableCell>
                      <TableCell>{log.model_name ?? '--'}</TableCell>
                      <TableCell>{formatDuration(log.duration_ms)}</TableCell>
                      <TableCell>{formatDateTime(log.started_at)}</TableCell>
                      <TableCell>
                        <StatusChip status={log.status} kind="agent" />
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
            rowsPerPageOptions={[25, 50, 100]}
          />
        </CardContent>
      </Card>
    </Box>
  );
};
