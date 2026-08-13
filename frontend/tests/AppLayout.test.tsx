import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

// `restoreMocks` clears implementations between tests, so the session mock is
// re-established in beforeEach rather than inside the factory.
const refreshSession = vi.fn();

vi.mock('@/api/auth', () => ({
  login: vi.fn(),
  register: vi.fn(),
  refreshSession: () => refreshSession(),
  logout: vi.fn().mockResolvedValue(undefined),
  fetchCurrentUser: vi.fn(),
}));

const SESSION = {
  access_token: 'token',
  expires_in: 1800,
  user: {
    id: 2,
    name: 'Marketing User',
    email: 'marketer@example.com',
    role: 'marketer' as const,
    is_active: true,
    created_at: '2026-01-01T09:00:00Z',
  },
};

const { renderWithProviders } = await import('./utils');
const { AppLayout } = await import('@/layouts/AppLayout');

describe('AppLayout', () => {
  beforeEach(() => {
    refreshSession.mockResolvedValue(SESSION);
  });

  it('renders the page title and every navigation entry', async () => {
    renderWithProviders(<AppLayout />, { route: '/dashboard' });

    expect(await screen.findByRole('heading', { name: 'Creative Copy Dashboard' })).toBeInTheDocument();
    for (const label of [
      'Dashboard',
      'Generate Copy',
      'History',
      'Templates',
      'Brands & Products',
      'Audience Segments',
      'CTA Rules',
      'Logs & Analytics',
      'Settings',
    ]) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    }
  });

  it('opens the navigation drawer on small screens', async () => {
    const user = userEvent.setup();
    renderWithProviders(<AppLayout />, { route: '/generate' });

    const menuButton = await screen.findByRole('button', { name: /open navigation menu/i });
    await user.click(menuButton);

    // The drawer duplicates the rail, so nav labels now appear twice.
    await waitFor(() => {
      expect(screen.getAllByText('Generate Copy').length).toBeGreaterThan(1);
    });
  });

  it('exposes the account menu with a logout action', async () => {
    const user = userEvent.setup();
    renderWithProviders(<AppLayout />, { route: '/dashboard' });

    await user.click(await screen.findByRole('button', { name: /open account menu/i }));
    expect(await screen.findByRole('menuitem', { name: /logout/i })).toBeInTheDocument();
    // The address appears in both the sidebar summary and the account menu.
    expect(screen.getAllByText(/marketer@example\.com/).length).toBeGreaterThan(0);
  });
});
