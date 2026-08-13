import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/api/client';

const requestPasswordReset = vi.fn();
const confirmPasswordReset = vi.fn();
const refreshSession = vi.fn();

vi.mock('@/api/auth', () => ({
  login: vi.fn(),
  loginWithGoogle: vi.fn(),
  register: vi.fn(),
  refreshSession: () => refreshSession(),
  logout: vi.fn().mockResolvedValue(undefined),
  fetchCurrentUser: vi.fn(),
  fetchAuthOptions: vi.fn().mockResolvedValue({
    google_login_enabled: false,
    google_client_id: null,
    registration_enabled: true,
    password_reset_enabled: true,
  }),
  requestPasswordReset: (...args: unknown[]) => requestPasswordReset(...args),
  confirmPasswordReset: (...args: unknown[]) => confirmPasswordReset(...args),
}));

const navigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => navigate };
});

const { renderWithProviders } = await import('./utils');
const { ForgotPasswordPage } = await import('@/pages/ForgotPasswordPage');
const { ResetPasswordPage } = await import('@/pages/ResetPasswordPage');

describe('ForgotPasswordPage', () => {
  beforeEach(() => {
    refreshSession.mockRejectedValue(new ApiError('no session', 'TOKEN_INVALID', 401, null, null));
    requestPasswordReset.mockResolvedValue({ message: 'ok' });
  });

  it('validates the email address', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ForgotPasswordPage />, { route: '/forgot-password' });

    await user.click(await screen.findByRole('button', { name: /send reset link/i }));
    expect(await screen.findByText('Email address is required.')).toBeInTheDocument();
    expect(requestPasswordReset).not.toHaveBeenCalled();

    await user.type(screen.getByLabelText(/email address/i), 'nope');
    await user.click(screen.getByRole('button', { name: /send reset link/i }));
    expect(await screen.findByText('Enter a valid email address.')).toBeInTheDocument();
  });

  it('confirms without revealing whether the account exists', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ForgotPasswordPage />, { route: '/forgot-password' });

    await user.type(await screen.findByLabelText(/email address/i), 'someone@example.com');
    await user.click(screen.getByRole('button', { name: /send reset link/i }));

    await waitFor(() => expect(requestPasswordReset).toHaveBeenCalledWith('someone@example.com'));
    const confirmation = await screen.findByText(/if that email address has an account/i);
    expect(confirmation).toBeInTheDocument();
    // No wording that would confirm or deny the address.
    expect(screen.queryByText(/we sent|not found|unknown/i)).not.toBeInTheDocument();
  });

  it('surfaces a server failure', async () => {
    const user = userEvent.setup();
    requestPasswordReset.mockRejectedValue(
      new ApiError('Too many requests.', 'RATE_LIMITED', 429, null, null),
    );
    renderWithProviders(<ForgotPasswordPage />, { route: '/forgot-password' });

    await user.type(await screen.findByLabelText(/email address/i), 'someone@example.com');
    await user.click(screen.getByRole('button', { name: /send reset link/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Too many requests.');
  });
});

describe('ResetPasswordPage', () => {
  beforeEach(() => {
    refreshSession.mockRejectedValue(new ApiError('no session', 'TOKEN_INVALID', 401, null, null));
    confirmPasswordReset.mockResolvedValue({ message: 'ok' });
    navigate.mockReset();
  });

  it('refuses to render the form without a token', async () => {
    renderWithProviders(<ResetPasswordPage />, { route: '/reset-password' });

    expect(await screen.findByText(/missing its token/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/new password/i)).not.toBeInTheDocument();
  });

  it('requires a strong, matching password', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ResetPasswordPage />, { route: '/reset-password?token=abc123' });

    await user.type(await screen.findByLabelText('New Password'), 'onlyletters');
    await user.type(screen.getByLabelText('Confirm New Password'), 'different');
    await user.click(screen.getByRole('button', { name: /update password/i }));

    expect(
      await screen.findByText('Include at least one letter and one number.'),
    ).toBeInTheDocument();
    expect(screen.getByText('Passwords do not match.')).toBeInTheDocument();
    expect(confirmPasswordReset).not.toHaveBeenCalled();
  });

  it('submits the token and the new password', async () => {
    const user = userEvent.setup();
    renderWithProviders(<ResetPasswordPage />, { route: '/reset-password?token=abc123' });

    await user.type(await screen.findByLabelText('New Password'), 'BrandNewPass1');
    await user.type(screen.getByLabelText('Confirm New Password'), 'BrandNewPass1');
    await user.click(screen.getByRole('button', { name: /update password/i }));

    await waitFor(() =>
      expect(confirmPasswordReset).toHaveBeenCalledWith('abc123', 'BrandNewPass1'),
    );
    expect(await screen.findByText(/your password has been updated/i)).toBeInTheDocument();
  });

  it('warns that an expired link cannot be used', async () => {
    const user = userEvent.setup();
    confirmPasswordReset.mockRejectedValue(
      new ApiError(
        'This reset link is invalid or has expired. Request a new one.',
        'TOKEN_INVALID',
        401,
        null,
        null,
      ),
    );
    renderWithProviders(<ResetPasswordPage />, { route: '/reset-password?token=stale' });

    await user.type(await screen.findByLabelText('New Password'), 'BrandNewPass1');
    await user.type(screen.getByLabelText('Confirm New Password'), 'BrandNewPass1');
    await user.click(screen.getByRole('button', { name: /update password/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/invalid or has expired/i);
  });

  it('tells the user other sessions will end', async () => {
    renderWithProviders(<ResetPasswordPage />, { route: '/reset-password?token=abc123' });
    expect(await screen.findByText(/signs you out everywhere else/i)).toBeInTheDocument();
  });
});
