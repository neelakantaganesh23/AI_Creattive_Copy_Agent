import { Box, Button, Stack, Typography } from '@mui/material';
import { Link } from 'react-router-dom';

export const NotFoundPage = (): JSX.Element => (
  <Box sx={{ minHeight: '100vh', display: 'grid', placeItems: 'center', p: 3 }}>
    <Stack spacing={2} alignItems="center">
      <Typography variant="h1" sx={{ fontSize: '3rem' }}>
        404
      </Typography>
      <Typography variant="body1" color="text.secondary">
        We could not find that page.
      </Typography>
      <Button component={Link} to="/dashboard" variant="contained">
        Back to dashboard
      </Button>
    </Stack>
  </Box>
);
