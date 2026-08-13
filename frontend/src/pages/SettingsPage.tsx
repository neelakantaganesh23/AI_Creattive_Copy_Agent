import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  Divider,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableRow,
  Typography,
} from '@mui/material';
import { useEffect, useState, type ReactNode } from 'react';

import { type ApiError, toApiError } from '@/api/client';
import { getSystemInfo } from '@/api/dashboard';
import { ErrorAlert } from '@/components/common/ErrorAlert';
import { PageHeader } from '@/components/common/PageHeader';
import { env } from '@/config/env';
import { useAuth } from '@/hooks/useAuth';
import type { SystemInfo } from '@/types/models';
import { formatDateTime } from '@/utils/format';

const Row = ({ label, value }: { label: string; value: ReactNode }): JSX.Element => (
  <TableRow>
    <TableCell component="th" scope="row" sx={{ width: 240, color: 'text.secondary' }}>
      {label}
    </TableCell>
    <TableCell>{value}</TableCell>
  </TableRow>
);

export const SettingsPage = (): JSX.Element => {
  const { user } = useAuth();
  const [info, setInfo] = useState<SystemInfo | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  useEffect(() => {
    let cancelled = false;
    void getSystemInfo()
      .then((data) => {
        if (!cancelled) setInfo(data);
      })
      .catch((caught) => {
        if (!cancelled) setError(toApiError(caught));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Box>
      <PageHeader title="Settings" description="Account and runtime configuration" />

      <ErrorAlert error={error} />

      <Stack spacing={3}>
        <Card>
          <CardContent>
            <Typography variant="h5" component="h2" sx={{ mb: 1.5 }}>
              Profile
            </Typography>
            <Table size="small">
              <TableBody>
                <Row label="Name" value={user?.name ?? '--'} />
                <Row label="Email" value={user?.email ?? '--'} />
                <Row
                  label="Role"
                  value={<Chip size="small" label={user?.role ?? 'unknown'} variant="outlined" />}
                />
                <Row label="Member since" value={formatDateTime(user?.created_at)} />
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <Typography variant="h5" component="h2" sx={{ mb: 1.5 }}>
              AI configuration
            </Typography>
            {info?.ai_provider === 'mock' && (
              <Alert severity="info" sx={{ mb: 2 }}>
                The mock provider is active. Copy is generated from deterministic templates rather
                than a language model. Set <code>AI_PROVIDER=gemini</code> with a Gemini API key and
                model identifiers to switch to live generation.
              </Alert>
            )}
            <Table size="small">
              <TableBody>
                <Row label="Application" value={`${info?.app_name ?? '--'} v${info?.app_version ?? '--'}`} />
                <Row label="Environment" value={info?.environment ?? '--'} />
                <Row label="AI provider" value={info?.ai_provider ?? '--'} />
                <Row label="Fast model" value={info?.models.fast ?? 'not configured'} />
                <Row label="Quality model" value={info?.models.quality ?? 'not configured'} />
                <Row
                  label="Grounding"
                  value={
                    info?.grounding_enabled
                      ? `Enabled (${info.grounding_provider})`
                      : 'Disabled - copy uses the brief only'
                  }
                />
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <Typography variant="h5" component="h2" sx={{ mb: 1.5 }}>
              Channel character limits
            </Typography>
            <Stack
              direction={{ xs: 'column', md: 'row' }}
              spacing={3}
              divider={<Divider orientation="vertical" flexItem />}
            >
              {Object.entries(info?.channel_limits ?? {}).map(([channel, limits]) => (
                <Box key={channel} sx={{ flex: 1 }}>
                  <Typography variant="body2" sx={{ fontWeight: 700, textTransform: 'uppercase' }}>
                    {channel}
                  </Typography>
                  <Table size="small">
                    <TableBody>
                      {Object.entries(limits).map(([field, limit]) => (
                        <TableRow key={field}>
                          <TableCell sx={{ border: 0, py: 0.5, color: 'text.secondary' }}>
                            {field.replace(/_/g, ' ')}
                          </TableCell>
                          <TableCell sx={{ border: 0, py: 0.5 }} align="right">
                            {limit}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </Box>
              ))}
            </Stack>
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <Typography variant="h5" component="h2" sx={{ mb: 1.5 }}>
              Frontend configuration
            </Typography>
            <Table size="small">
              <TableBody>
                <Row label="API base URL" value={env.apiBaseUrl} />
                <Row label="Google sign-in" value={env.enableGoogleLogin ? 'Enabled' : 'Disabled'} />
                <Row label="Demo data" value={env.enableDemoData ? 'Enabled' : 'Disabled'} />
                <Row label="Status poll interval" value={`${env.pollIntervalMs} ms`} />
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </Stack>
    </Box>
  );
};
