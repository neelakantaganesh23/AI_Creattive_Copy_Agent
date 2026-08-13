import { screen, waitFor } from '@testing-library/react';
import { Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/api/client';

const refreshSession = vi.fn();

vi.mock('@/api/auth', () => ({
  login: vi.fn(),
  register: vi.fn(),
  refreshSession: () => refreshSession(),
  logout: vi.fn().mockResolvedValue(undefined),
  fetchCurrentUser: vi.fn(),
}));

const { renderWithProviders, mockUser } = await import('./utils');
const { ProtectedRoute } = await import('@/routes/ProtectedRoute');

const Tree = (): JSX.Element => (
  <Routes>
    <Route path="/login" element={<p>Login screen</p>} />
    <Route element={<ProtectedRoute />}>
      <Route path="/dashboard" element={<p>Dashboard content</p>} />
    </Route>
  </Routes>
);

describe('ProtectedRoute', () => {
  beforeEach(() => {
    refreshSession.mockReset();
  });

  it('redirects an unauthenticated visitor to the login screen', async () => {
    refreshSession.mockRejectedValue(
      new ApiError('no session', 'TOKEN_INVALID', 401, null, null),
    );
    renderWithProviders(<Tree />, { route: '/dashboard' });

    expect(await screen.findByText('Login screen')).toBeInTheDocument();
    expect(screen.queryByText('Dashboard content')).not.toBeInTheDocument();
  });

  it('renders the protected page once the session is restored', async () => {
    refreshSession.mockResolvedValue({ access_token: 'token', user: mockUser, expires_in: 1800 });
    renderWithProviders(<Tree />, { route: '/dashboard' });

    await waitFor(() => {
      expect(screen.getByText('Dashboard content')).toBeInTheDocument();
    });
  });

  it('shows a loading state while the session is being restored', () => {
    refreshSession.mockReturnValue(new Promise(() => undefined));
    renderWithProviders(<Tree />, { route: '/dashboard' });

    expect(screen.getByRole('status')).toBeInTheDocument();
  });
});
