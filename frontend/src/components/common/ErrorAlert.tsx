import { Alert, AlertTitle, Button } from '@mui/material';

import type { ApiError } from '@/api/client';

interface ErrorAlertProps {
  error: ApiError | null;
  title?: string;
  onRetry?: () => void;
}

/**
 * Renders an API failure in terms the user can act on. Technical detail beyond
 * the request id is deliberately not surfaced.
 */
export const ErrorAlert = ({ error, title, onRetry }: ErrorAlertProps): JSX.Element | null => {
  if (!error) return null;

  return (
    <Alert
      severity="error"
      role="alert"
      sx={{ mb: 2, borderRadius: 2 }}
      action={
        onRetry && error.isRetryable ? (
          <Button color="inherit" size="small" onClick={onRetry}>
            Retry
          </Button>
        ) : undefined
      }
    >
      {title && <AlertTitle>{title}</AlertTitle>}
      {error.message}
      {error.requestId ? ` (reference: ${error.requestId.slice(0, 8)})` : ''}
    </Alert>
  );
};
