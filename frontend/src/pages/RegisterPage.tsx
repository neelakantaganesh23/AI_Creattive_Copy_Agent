import { zodResolver } from '@hookform/resolvers/zod';
import {
  Alert,
  Box,
  Button,
  Link as MuiLink,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link, useNavigate } from 'react-router-dom';

import { ApiError } from '@/api/client';
import { AuthShowcase } from '@/components/auth/AuthShowcase';
import { Logo } from '@/components/common/Logo';
import { useAuth } from '@/hooks/useAuth';
import { registerSchema, type RegisterFormValues } from '@/schemas/forms';

export const RegisterPage = (): JSX.Element => {
  const { register: registerAccount } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormValues>({ resolver: zodResolver(registerSchema) });

  const onSubmit = async (values: RegisterFormValues): Promise<void> => {
    setError(null);
    try {
      await registerAccount(values.name, values.email, values.password);
      navigate('/dashboard', { replace: true });
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : 'Unable to create your account. Please try again.',
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
              Create your account
            </Typography>
            <Typography variant="body2" color="text.secondary">
              New accounts are created with the marketer role
            </Typography>
          </Stack>

          {error && (
            <Alert severity="error" role="alert" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <Box component="form" onSubmit={handleSubmit(onSubmit)} noValidate>
            <Stack spacing={2.25}>
              <TextField
                {...register('name')}
                label="Full Name"
                fullWidth
                autoComplete="name"
                error={Boolean(errors.name)}
                helperText={errors.name?.message}
              />
              <TextField
                {...register('email')}
                label="Email Address"
                type="email"
                fullWidth
                autoComplete="email"
                error={Boolean(errors.email)}
                helperText={errors.email?.message}
              />
              <TextField
                {...register('password')}
                label="Password"
                type="password"
                fullWidth
                autoComplete="new-password"
                error={Boolean(errors.password)}
                helperText={errors.password?.message ?? 'At least 8 characters, with a number.'}
              />
              <TextField
                {...register('confirmPassword')}
                label="Confirm Password"
                type="password"
                fullWidth
                autoComplete="new-password"
                error={Boolean(errors.confirmPassword)}
                helperText={errors.confirmPassword?.message}
              />
              <Button type="submit" variant="contained" size="large" disabled={isSubmitting}>
                {isSubmitting ? 'Creating account...' : 'Create account'}
              </Button>
              <Typography variant="body2" color="text.secondary" textAlign="center">
                Already have an account?{' '}
                <MuiLink component={Link} to="/login" underline="hover" fontWeight={600}>
                  Sign in
                </MuiLink>
              </Typography>
            </Stack>
          </Box>
        </Box>
      </Box>
    </Box>
  );
};
