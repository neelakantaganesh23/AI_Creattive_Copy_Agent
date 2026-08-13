import { zodResolver } from '@hookform/resolvers/zod';
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Divider,
  FormControlLabel,
  IconButton,
  InputAdornment,
  Link as MuiLink,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { Eye, EyeOff, Lock, LogIn, Mail } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link, useLocation, useNavigate } from 'react-router-dom';

import { fetchAuthOptions } from '@/api/auth';
import { ApiError } from '@/api/client';
import { AuthShowcase } from '@/components/auth/AuthShowcase';
import { GoogleSignInButton } from '@/components/auth/GoogleSignInButton';
import { Logo } from '@/components/common/Logo';
import { useAuth } from '@/hooks/useAuth';
import { loginSchema, type LoginFormValues } from '@/schemas/forms';
import type { AuthOptions } from '@/types/models';

interface LocationState {
  from?: string;
}

export const LoginPage = (): JSX.Element => {
  const { login, loginWithGoogle } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [showPassword, setShowPassword] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [options, setOptions] = useState<AuthOptions | null>(null);
  const [googleBusy, setGoogleBusy] = useState(false);

  // The server decides which sign-in methods exist, so the button only appears
  // when a client id is actually configured.
  useEffect(() => {
    let cancelled = false;
    void fetchAuthOptions()
      .then((data) => {
        if (!cancelled) setOptions(data);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  const handleGoogleCredential = async (credential: string): Promise<void> => {
    setAuthError(null);
    setGoogleBusy(true);
    try {
      await loginWithGoogle(credential);
      const target = (location.state as LocationState | null)?.from ?? '/dashboard';
      navigate(target, { replace: true });
    } catch (error) {
      setAuthError(
        error instanceof ApiError ? error.message : 'Google sign-in failed. Please try again.',
      );
    } finally {
      setGoogleBusy(false);
    }
  };

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '', rememberMe: true },
  });

  const onSubmit = async (values: LoginFormValues): Promise<void> => {
    setAuthError(null);
    try {
      await login(values.email, values.password, values.rememberMe);
      const target = (location.state as LocationState | null)?.from ?? '/dashboard';
      navigate(target, { replace: true });
    } catch (error) {
      setAuthError(
        error instanceof ApiError ? error.message : 'Unable to sign in. Please try again.',
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
          bgcolor: 'background.default',
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
            boxShadow: '0 12px 40px rgba(16, 24, 59, 0.06)',
          }}
        >
          <Stack alignItems="center" spacing={1} sx={{ mb: 3 }}>
            <Logo size="medium" showText={false} />
            <Typography variant="h3" component="h1">
              Welcome Back
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Sign in to continue to your account
            </Typography>
          </Stack>

          {authError && (
            <Alert severity="error" role="alert" sx={{ mb: 2 }}>
              {authError}
            </Alert>
          )}

          <Box component="form" onSubmit={handleSubmit(onSubmit)} noValidate>
            <Stack spacing={2.25}>
              <TextField
                {...register('email')}
                label="Email Address"
                type="email"
                placeholder="Enter your email"
                autoComplete="email"
                fullWidth
                error={Boolean(errors.email)}
                helperText={errors.email?.message}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Mail size={17} aria-hidden />
                    </InputAdornment>
                  ),
                }}
              />

              <TextField
                {...register('password')}
                label="Password"
                type={showPassword ? 'text' : 'password'}
                placeholder="Enter your password"
                autoComplete="current-password"
                fullWidth
                error={Boolean(errors.password)}
                helperText={errors.password?.message}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Lock size={17} aria-hidden />
                    </InputAdornment>
                  ),
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => setShowPassword((visible) => !visible)}
                        aria-label={showPassword ? 'Hide password' : 'Show password'}
                        edge="end"
                        size="small"
                      >
                        {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                      </IconButton>
                    </InputAdornment>
                  ),
                }}
              />

              <Stack direction="row" justifyContent="space-between" alignItems="center">
                <FormControlLabel
                  control={<Checkbox {...register('rememberMe')} defaultChecked size="small" />}
                  label={<Typography variant="body2">Remember me</Typography>}
                />
                <MuiLink
                  component={Link}
                  to="/forgot-password"
                  variant="body2"
                  underline="hover"
                >
                  Forgot password?
                </MuiLink>
              </Stack>

              <Button
                type="submit"
                variant="contained"
                size="large"
                fullWidth
                disabled={isSubmitting}
                startIcon={<LogIn size={17} />}
              >
                {isSubmitting ? 'Signing in...' : 'Sign In'}
              </Button>

              {options?.google_login_enabled && options.google_client_id && (
                <>
                  <Divider>
                    <Typography variant="caption" color="text.secondary">
                      or
                    </Typography>
                  </Divider>
                  <GoogleSignInButton
                    clientId={options.google_client_id}
                    disabled={googleBusy || isSubmitting}
                    onCredential={(credential) => void handleGoogleCredential(credential)}
                    onError={setAuthError}
                  />
                </>
              )}

              <Typography variant="body2" color="text.secondary" textAlign="center">
                New to AI Creative Copy Agent?{' '}
                <MuiLink component={Link} to="/register" underline="hover" fontWeight={600}>
                  Create an account
                </MuiLink>
              </Typography>
            </Stack>
          </Box>
        </Box>
      </Box>
    </Box>
  );
};
