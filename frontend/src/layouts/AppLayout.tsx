import { Box, Drawer } from '@mui/material';
import { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';

import { Header } from '@/components/layout/Header';
import { Sidebar } from '@/components/layout/Sidebar';

const SIDEBAR_WIDTH = 256;

const PAGE_META: Record<string, { title: string; description: string }> = {
  '/dashboard': {
    title: 'Creative Copy Dashboard',
    description: 'Campaign performance and generation activity at a glance',
  },
  '/generate': {
    title: 'Generate Copy',
    description: 'Create AI-powered marketing copy in seconds',
  },
  '/history': { title: 'History', description: 'Every generation you have run' },
  '/templates': { title: 'Templates', description: 'Reusable prompt templates per channel' },
  '/brands': { title: 'Brands & Products', description: 'Manage brands and their products' },
  '/audience-segments': {
    title: 'Audience Segments',
    description: 'Define who the copy is written for',
  },
  '/cta-rules': { title: 'CTA Rules', description: 'Deterministic call-to-action rules' },
  '/logs': { title: 'Logs & Analytics', description: 'Agent execution logs and workflow metrics' },
  '/settings': { title: 'Settings', description: 'Account and runtime configuration' },
};

export const AppLayout = (): JSX.Element => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { pathname } = useLocation();
  const meta = PAGE_META[pathname] ??
    PAGE_META[`/${pathname.split('/')[1] ?? ''}`] ?? {
      title: 'AI Creative Copy Agent',
      description: '',
    };

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      {/* Permanent rail on desktop (>= 1200px). */}
      <Box
        component="aside"
        sx={{
          width: SIDEBAR_WIDTH,
          flexShrink: 0,
          display: { xs: 'none', lg: 'block' },
          position: 'sticky',
          top: 0,
          height: '100vh',
        }}
      >
        <Sidebar />
      </Box>

      {/* Drawer below 1200px (§17). */}
      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={() => setMobileOpen(false)}
        ModalProps={{ keepMounted: true }}
        sx={{
          display: { lg: 'none' },
          '& .MuiDrawer-paper': { width: SIDEBAR_WIDTH, border: 0 },
        }}
      >
        <Sidebar onNavigate={() => setMobileOpen(false)} />
      </Drawer>

      <Box sx={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
        <Header
          title={meta.title}
          description={meta.description}
          onOpenSidebar={() => setMobileOpen(true)}
        />
        <Box
          component="main"
          id="main-content"
          sx={{ flex: 1, p: { xs: 2, md: 3 }, maxWidth: 1440, width: '100%', mx: 'auto' }}
        >
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
};
