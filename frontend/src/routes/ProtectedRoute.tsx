import { Box, CircularProgress } from '@mui/material';
import { Navigate, Outlet, useLocation } from 'react-router-dom';

import { useAuth } from '@/hooks/useAuth';

/** Gate for authenticated areas: redirects to /login and remembers the target. */
export const ProtectedRoute = (): JSX.Element => {
  const { isAuthenticated, isInitialising } = useAuth();
  const location = useLocation();

  if (isInitialising) {
    return (
      <Box
        sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center' }}
        role="status"
        aria-live="polite"
      >
        <CircularProgress aria-label="Restoring your session" />
      </Box>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <Outlet />;
};

/** Inverse gate: keeps signed-in users away from /login and /register. */
export const PublicOnlyRoute = (): JSX.Element => {
  const { isAuthenticated, isInitialising } = useAuth();

  if (isInitialising) {
    return (
      <Box
        sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center' }}
        role="status"
        aria-live="polite"
      >
        <CircularProgress aria-label="Loading" />
      </Box>
    );
  }

  return isAuthenticated ? <Navigate to="/dashboard" replace /> : <Outlet />;
};
