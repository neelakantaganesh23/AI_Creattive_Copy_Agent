import { Alert, AlertTitle, Chip, Stack, Typography } from '@mui/material';

import type { QualityCheck } from '@/types/models';
import { FIELD_LABELS } from '@/utils/format';

interface QualityReportProps {
  quality: QualityCheck;
}

/** The warning text the backend derives from a violation, mirrored here so the
 *  same finding is not shown twice — once structured and once as loose text. */
const violationWarning = (field: string, explanation: string): string =>
  `${field.replace(/_/g, ' ')}: ${explanation}`;

export const QualityReport = ({ quality }: QualityReportProps): JSX.Element | null => {
  const { violations, warnings } = quality;

  const covered = new Set(
    violations.map((violation) => violationWarning(violation.field, violation.explanation)),
  );
  const otherWarnings = warnings.filter((warning) => !covered.has(warning));

  if (violations.length === 0 && otherWarnings.length === 0) return null;

  return (
    <Stack spacing={1.5} sx={{ mb: 2 }}>
      {violations.length > 0 && (
        <Alert severity="warning">
          <AlertTitle>
            {violations.length === 1
              ? '1 content rule was not satisfied'
              : `${violations.length} content rules were not satisfied`}
          </AlertTitle>
          <Stack component="ul" spacing={0.75} sx={{ m: 0, pl: 2 }}>
            {violations.map((violation, index) => (
              <li key={`${violation.rule_id ?? 'judge'}-${violation.field}-${index}`}>
                <Stack direction="row" spacing={1} alignItems="baseline" flexWrap="wrap">
                  <Chip
                    size="small"
                    label={violation.severity === 'error' ? 'Error' : 'Warning'}
                    color={violation.severity === 'error' ? 'error' : 'warning'}
                    variant="outlined"
                  />
                  <Typography variant="body2" component="span">
                    <strong>{FIELD_LABELS[violation.field] ?? violation.field}</strong>{' '}
                    {violation.explanation}
                    {violation.rule_name ? ` (${violation.rule_name})` : ''}
                  </Typography>
                </Stack>
                {violation.suggestion && (
                  <Typography variant="caption" color="text.secondary" display="block">
                    {violation.suggestion}
                  </Typography>
                )}
              </li>
            ))}
          </Stack>
        </Alert>
      )}

      {otherWarnings.length > 0 && (
        <Alert severity="warning">
          <Stack component="ul" sx={{ m: 0, pl: 2 }}>
            {otherWarnings.map((warning) => (
              <li key={warning}>
                <Typography variant="body2">{warning}</Typography>
              </li>
            ))}
          </Stack>
        </Alert>
      )}
    </Stack>
  );
};
