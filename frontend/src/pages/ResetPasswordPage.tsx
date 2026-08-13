import { zodResolver } from '@hookform/resolvers/zod';
import { Alert, Box, Button, Link as MuiLink, Stack, TextField, Typography } from '@mui/material';
import { CheckCircle2 } from 'lucide-react';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';

import { confirmPasswordReset } from '@/api/auth';
import { ApiError } from '@/api/client';
import { AuthShowcase } from '@/components/auth/AuthShowcase';
import { Logo } from '@/components/common/Logo';
import { resetPasswordSchema, type ResetPasswordFormValues } from '@/schemas/forms';

export const ResetPasswordPage = (): JSX.Element => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token') ?? '';
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordFormValues>({ resolver: zodResolver(resetPasswordSchema) });

  const onSubmit = async (values: ResetPasswordFormValues): Promise<void> => {
    setError(null);
    try {
      await confirmPasswordReset(token, values.password);
      setDone(true);
      // Every session was revoked server-side, so the user must sign in again.
      setTimeout(() => navigate('/login', { replace: true }), 2500);
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.message : 'Unable to reset your password right now.',
      );
    }
  };

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <AuthShowcase />
      <Box
        sx={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          p: { xs: 2.5, md: 6 },
        }}
      >
        <Box
          sx={{
            width: '100%',
            maxWidth: 420,
            bgcolor: 'background.paper',
            border: 1,
            borderColor: 'divider',
            borderRadius: 3,
            p: { xs: 3, md: 4.5 },
          }}
        >
          <Stack alignItems="center" spacing={1} sx={{ mb: 3 }}>
            <Logo size="medium" showText={false} />
            <Typography variant="h3" component="h1">
              Choose a new password
            </Typography>
          </Stack>

          {!token ? (
            <Stack spacing={2} alignItems="center">
              <Alert severity="error" sx={{ width: '100%' }} role="alert">
                This reset link is missing its token. Request a new link and try again.
              </Alert>
              <Button component={Link} to="/forgot-password" variant="contained">
                Request a new link
              </Button>
            </Stack>
          ) : done ? (
            <Stack spacing={2} alignItems="center">
              <Alert severity="success" icon={<CheckCircle2 size={18} />} sx={{ width: '100%' }}>
                Your password has been updated. Redirecting you to sign in...
              </Alert>
              <Button component={Link} to="/login">
                Sign in now
              </Button>
            </Stack>
          ) : (
            <Box component="form" onSubmit={handleSubmit(onSubmit)} noValidate>
              <Stack spacing={2.25}>
                {error && (
                  <Alert severity="error" role="alert">
                    {error}
                  </Alert>
                )}
                <TextField
                  {...register('password')}
                  label="New Password"
                  type="password"
                  fullWidth
                  autoComplete="new-password"
                  autoFocus
                  error={Boolean(errors.password)}
                  helperText={errors.password?.message ?? 'At least 8 characters, with a number.'}
                />
                <TextField
                  {...register('confirmPassword')}
                  label="Confirm New Password"
                  type="password"
                  fullWidth
                  autoComplete="new-password"
                  error={Boolean(errors.confirmPassword)}
                  helperText={errors.confirmPassword?.message}
                />
                {/* Static guidance, not an event: "alert" would make screen
                    readers interrupt on every render. */}
                <Alert severity="info" role="note">
                  Changing your password signs you out everywhere else.
                </Alert>
                <Button type="submit" variant="contained" size="large" disabled={isSubmitting}>
                  {isSubmitting ? 'Updating...' : 'Update password'}
                </Button>
                <Typography variant="body2" color="text.secondary" textAlign="center">
                  <MuiLink component={Link} to="/login" underline="hover" fontWeight={600}>
                    Back to sign in
                  </MuiLink>
                </Typography>
              </Stack>
            </Box>
          )}
        </Box>
      </Box>
    </Box>
  );
};
