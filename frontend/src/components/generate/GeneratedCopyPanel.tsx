import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  IconButton,
  Menu,
  MenuItem,
  Snackbar,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableRow,
  Tabs,
  Tooltip,
  Typography,
} from '@mui/material';
import {
  Check,
  Copy,
  Download,
  Mail,
  MessageSquare,
  RefreshCw,
  Smartphone,
} from 'lucide-react';
import { useState } from 'react';

import { StatusChip } from '@/components/common/StatusChip';
import { EmailPreview } from '@/components/generate/EmailPreview';
import { QualityReport } from '@/components/generate/QualityReport';
import {
  copyToClipboard,
  downloadAsJson,
  downloadAsText,
  outputToPlainText,
  slugifyFilename,
} from '@/services/download';
import type { Channel, GenerationDetail, GenerationOutput } from '@/types/models';
import { CHANNEL_LABELS, FIELD_LABELS, formatDateTime, formatDuration } from '@/utils/format';

interface GeneratedCopyPanelProps {
  output: GenerationOutput;
  generation?: GenerationDetail | null;
  executionTimeMs?: number | null;
  onRegenerate?: () => void;
  isRegenerating?: boolean;
}

const CHANNEL_ORDER: Channel[] = ['email', 'mobile', 'sms'];
const CHANNEL_ICONS = { email: Mail, mobile: Smartphone, sms: MessageSquare } as const;

export const GeneratedCopyPanel = ({
  output,
  generation,
  executionTimeMs,
  onRegenerate,
  isRegenerating = false,
}: GeneratedCopyPanelProps): JSX.Element => {
  const [tab, setTab] = useState<Channel>(output.channel);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [downloadAnchor, setDownloadAnchor] = useState<HTMLElement | null>(null);

  const fields = (
    tab === 'email' ? output.email : tab === 'mobile' ? output.mobile : output.sms
  ) as unknown as Record<string, string>;

  const handleCopy = async (label: string, value: string): Promise<void> => {
    const copied = await copyToClipboard(value);
    setToast(copied ? `${label} copied to clipboard.` : 'Copying is unavailable in this browser.');
    if (copied) {
      setCopiedField(label);
      setTimeout(() => setCopiedField(null), 1500);
    }
  };

  const baseName = slugifyFilename(generation?.title ?? 'generated-copy');

  return (
    <Card component="section" aria-labelledby="generated-copy-heading">
      <CardContent sx={{ p: { xs: 2, md: 3 } }}>
        <Stack
          direction={{ xs: 'column', md: 'row' }}
          justifyContent="space-between"
          alignItems={{ xs: 'flex-start', md: 'center' }}
          gap={1.5}
          sx={{ mb: 2 }}
        >
          <Box>
            <Stack direction="row" spacing={1} alignItems="center">
              <Typography variant="h5" component="h2" id="generated-copy-heading">
                Generated Copy
              </Typography>
              {generation && <StatusChip status={generation.status} />}
            </Stack>
            <Typography variant="caption" color="text.secondary">
              AI-generated content for your campaign
            </Typography>
          </Box>

          <Stack direction="row" spacing={1} flexWrap="wrap">
            <Button
              size="small"
              variant="outlined"
              startIcon={<Copy size={15} />}
              onClick={() => void handleCopy('All copy', outputToPlainText(output, generation ?? undefined))}
            >
              Copy All
            </Button>
            <Button
              size="small"
              variant="outlined"
              startIcon={<Download size={15} />}
              onClick={(event) => setDownloadAnchor(event.currentTarget)}
              aria-haspopup="menu"
            >
              Download
            </Button>
            {onRegenerate && (
              <Button
                size="small"
                variant="contained"
                startIcon={<RefreshCw size={15} />}
                onClick={onRegenerate}
                disabled={isRegenerating}
              >
                {isRegenerating ? 'Regenerating...' : 'Regenerate'}
              </Button>
            )}
          </Stack>
        </Stack>

        <Menu
          anchorEl={downloadAnchor}
          open={Boolean(downloadAnchor)}
          onClose={() => setDownloadAnchor(null)}
        >
          <MenuItem
            onClick={() => {
              downloadAsJson(baseName, output);
              setDownloadAnchor(null);
            }}
          >
            Download as JSON
          </MenuItem>
          <MenuItem
            onClick={() => {
              downloadAsText(baseName, output, generation ?? undefined);
              setDownloadAnchor(null);
            }}
          >
            Download as TXT
          </MenuItem>
        </Menu>

        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
          <Chip size="small" variant="outlined" label={`Channel: ${CHANNEL_LABELS[output.channel]}`} />
          {generation?.audience_segment_name && (
            <Chip size="small" variant="outlined" label={`Audience: ${generation.audience_segment_name}`} />
          )}
          <Chip size="small" variant="outlined" label={`Language: ${output.language}`} />
          <Chip
            size="small"
            variant="outlined"
            label={`Generated in ${formatDuration(executionTimeMs ?? generation?.execution_time_ms)}`}
          />
          {generation && (
            <Chip size="small" variant="outlined" label={formatDateTime(generation.created_at)} />
          )}
          <Chip
            size="small"
            color={output.quality.status === 'passed' ? 'success' : 'warning'}
            variant="outlined"
            label={`Quality: ${output.quality.status}`}
          />
          <Chip
            size="small"
            variant="outlined"
            label={output.grounded ? 'Externally grounded' : 'Not externally grounded'}
          />
          {output.quality.judge_score !== null && (
            <Chip
              size="small"
              variant="outlined"
              color={output.quality.judge_score >= 0.7 ? 'success' : 'warning'}
              label={`Judge score: ${Math.round(output.quality.judge_score * 100)}%`}
            />
          )}
          {output.quality.revisions > 0 && (
            <Chip
              size="small"
              variant="outlined"
              label={
                output.quality.revisions === 1
                  ? 'Revised once after review'
                  : `Revised ${output.quality.revisions} times after review`
              }
            />
          )}
        </Stack>

        <QualityReport quality={output.quality} />

        <Tabs
          value={tab}
          onChange={(_event, next: Channel) => setTab(next)}
          aria-label="Generated copy channels"
          sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}
        >
          {CHANNEL_ORDER.map((channel) => {
            const Icon = CHANNEL_ICONS[channel];
            return (
              <Tab
                key={channel}
                value={channel}
                label={CHANNEL_LABELS[channel]}
                icon={<Icon size={16} />}
                iconPosition="start"
                id={`channel-tab-${channel}`}
                aria-controls={`channel-panel-${channel}`}
              />
            );
          })}
        </Tabs>

        <Stack direction={{ xs: 'column', lg: 'row' }} spacing={3}>
          <Box
            sx={{ flex: 1, minWidth: 0 }}
            role="tabpanel"
            id={`channel-panel-${tab}`}
            aria-labelledby={`channel-tab-${tab}`}
          >
            <Table size="small">
              <TableBody>
                {Object.entries(fields).map(([field, value]) => (
                  <TableRow key={field}>
                    <TableCell
                      component="th"
                      scope="row"
                      sx={{ width: 190, verticalAlign: 'top', color: 'text.secondary' }}
                    >
                      {FIELD_LABELS[field] ?? field}
                    </TableCell>
                    <TableCell
                      sx={{
                        fontWeight: field === 'cta' ? 700 : 500,
                        color: field === 'cta' ? 'primary.main' : 'text.primary',
                      }}
                    >
                      {value}
                    </TableCell>
                    <TableCell align="right" sx={{ width: 48 }}>
                      <Tooltip title={`Copy ${FIELD_LABELS[field] ?? field}`}>
                        <IconButton
                          size="small"
                          aria-label={`Copy ${FIELD_LABELS[field] ?? field}`}
                          onClick={() => void handleCopy(FIELD_LABELS[field] ?? field, value)}
                        >
                          {copiedField === (FIELD_LABELS[field] ?? field) ? (
                            <Check size={15} color="#22A861" />
                          ) : (
                            <Copy size={15} />
                          )}
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>

          {tab === 'email' && (
            <Box sx={{ width: { xs: '100%', lg: 420 }, flexShrink: 0 }}>
              <EmailPreview
                copy={output.email}
                brandName={generation?.brand_name}
                imageUrl={output.image_url}
              />
            </Box>
          )}
        </Stack>

        <Divider sx={{ my: 2 }} />
        <Typography variant="caption" color="text.secondary">
          AI-generated content should be reviewed and validated against your brand guidelines
          before publishing.
        </Typography>
      </CardContent>

      <Snackbar
        open={toast !== null}
        autoHideDuration={2500}
        onClose={() => setToast(null)}
        message={toast ?? ''}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      />
    </Card>
  );
};
