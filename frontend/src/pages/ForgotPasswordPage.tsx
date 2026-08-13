import { zodResolver } from '@hookform/resolvers/zod';
import { Alert, Box, Button, Link as MuiLink, Stack, TextField, Typography } from '@mui/material';
import { ArrowLeft, MailCheck } from 'lucide-react';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link } from 'react-router-dom';

import { requestPasswordReset } from '@/api/auth';
import { ApiError } from '@/api/client';
import { AuthShowcase } from '@/components/auth/AuthShowcase';
import { Logo } from '@/components/common/Logo';
import { forgotPasswordSchema, type ForgotPasswordFormValues } from '@/schemas/forms';

export const ForgotPasswordPage = (): JSX.Element => {
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordFormValues>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: '' },
  });

  const onSubmit = async (values: ForgotPasswordFormValues): Promise<void> => {
    setError(null);
    try {
      await requestPasswordReset(values.email);
      // The response is identical whether or not the address exists, so the
      // confirmation is deliberately non-committal.
      setSent(true);
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.message : 'Unable to send the reset link right now.',
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
              Forgot your password?
            </Typography>
            <Typography variant="body2" color="text.secondary" textAlign="center">
              Enter your email address and we will send you a link to reset it.
            </Typography>
          </Stack>

          {sent ? (
            <Stack spacing={2.5} alignItems="center">
              <Alert severity="success" icon={<MailCheck size={18} />} sx={{ width: '100%' }}>
                If that email address has an account, a reset link is on its way. The link expires
                in 30 minutes.
              </Alert>
              <Button component={Link} to="/login" startIcon={<ArrowLeft size={16} />}>
                Back to sign in
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
                  {...register('email')}
                  label="Email Address"
                  type="email"
                  fullWidth
                  autoComplete="email"
                  autoFocus
                  error={Boolean(errors.email)}
                  helperText={errors.email?.message}
                />
                <Button type="submit" variant="contained" size="large" disabled={isSubmitting}>
                  {isSubmitting ? 'Sending...' : 'Send reset link'}
                </Button>
                <Typography variant="body2" color="text.secondary" textAlign="center">
                  Remembered it?{' '}
                  <MuiLink component={Link} to="/login" underline="hover" fontWeight={600}>
                    Sign in
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
