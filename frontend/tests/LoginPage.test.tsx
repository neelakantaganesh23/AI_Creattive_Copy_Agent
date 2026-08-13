import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/api/client';

const login = vi.fn();
const refreshSession = vi.fn();

vi.mock('@/api/auth', () => ({
  login: (...args: unknown[]) => login(...args),
  register: vi.fn(),
  refreshSession: () => refreshSession(),
  logout: vi.fn().mockResolvedValue(undefined),
  fetchCurrentUser: vi.fn(),
}));

const navigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => navigate };
});

const { renderWithProviders, mockUser } = await import('./utils');
const { LoginPage } = await import('@/pages/LoginPage');

describe('LoginPage', () => {
  beforeEach(() => {
    login.mockReset();
    navigate.mockReset();
    // No existing session: the silent refresh on mount fails.
    refreshSession.mockRejectedValue(new ApiError('no session', 'TOKEN_INVALID', 401, null, null));
  });

  it('renders the product showcase and the sign-in form', async () => {
    renderWithProviders(<LoginPage />, { route: '/login' });

    expect(await screen.findByRole('heading', { name: 'Welcome Back' })).toBeInTheDocument();
    expect(screen.getByText('Sign in to continue to your account')).toBeInTheDocument();
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^sign in$/i })).toBeInTheDocument();
  });

  it('shows validation messages for an empty submission', async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />, { route: '/login' });

    await user.click(await screen.findByRole('button', { name: /^sign in$/i }));

    expect(await screen.findByText('Email address is required.')).toBeInTheDocument();
    expect(screen.getByText('Password is required.')).toBeInTheDocument();
    expect(login).not.toHaveBeenCalled();
  });

  it('rejects a malformed email address', async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />, { route: '/login' });

    await user.type(await screen.findByLabelText(/email address/i), 'not-an-email');
    await user.type(screen.getByLabelText('Password'), 'ChangeMe123!');
    await user.click(screen.getByRole('button', { name: /^sign in$/i }));

    expect(await screen.findByText('Enter a valid email address.')).toBeInTheDocument();
    expect(login).not.toHaveBeenCalled();
  });

  it('signs in and redirects to the dashboard', async () => {
    const user = userEvent.setup();
    login.mockResolvedValue({ access_token: 'token', user: mockUser, expires_in: 1800 });
    renderWithProviders(<LoginPage />, { route: '/login' });

    await user.type(await screen.findByLabelText(/email address/i), 'marketer@example.com');
    await user.type(screen.getByLabelText('Password'), 'ChangeMe123!');
    await user.click(screen.getByRole('button', { name: /^sign in$/i }));

    await waitFor(() => {
      expect(login).toHaveBeenCalledWith({
        email: 'marketer@example.com',
        password: 'ChangeMe123!',
        remember_me: true,
      });
    });
    await waitFor(() => {
      expect(navigate).toHaveBeenCalledWith('/dashboard', { replace: true });
    });
  });

  it('surfaces an authentication error without leaking detail', async () => {
    const user = userEvent.setup();
    login.mockRejectedValue(
      new ApiError('Incorrect email or password.', 'INVALID_CREDENTIALS', 401, null, 'abc123'),
    );
    renderWithProviders(<LoginPage />, { route: '/login' });

    await user.type(await screen.findByLabelText(/email address/i), 'marketer@example.com');
    await user.type(screen.getByLabelText('Password'), 'WrongPassword1');
    await user.click(screen.getByRole('button', { name: /^sign in$/i }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Incorrect email or password.');
    expect(navigate).not.toHaveBeenCalled();
  });

  it('toggles password visibility', async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />, { route: '/login' });

    const password = await screen.findByLabelText('Password');
    expect(password).toHaveAttribute('type', 'password');

    await user.click(screen.getByRole('button', { name: /show password/i }));
    expect(password).toHaveAttribute('type', 'text');
  });

  it('disables Google sign-in when it is not configured', async () => {
    renderWithProviders(<LoginPage />, { route: '/login' });
    expect(await screen.findByRole('button', { name: /google/i })).toBeDisabled();
  });
});
