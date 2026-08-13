import {
  Avatar,
  Box,
  Button,
  Divider,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Stack,
  Typography,
} from '@mui/material';
import { LogOut } from 'lucide-react';
import { NavLink } from 'react-router-dom';

import { Logo } from '@/components/common/Logo';
import { NAV_ITEMS } from '@/components/layout/navItems';
import { useAuth } from '@/hooks/useAuth';
import { gradients } from '@/theme/theme';

interface SidebarProps {
  onNavigate?: () => void;
}

export const Sidebar = ({ onNavigate }: SidebarProps): JSX.Element => {
  const { user, logout } = useAuth();

  return (
    <Stack
      component="nav"
      aria-label="Main navigation"
      sx={{ height: '100%', background: gradients.sidebar, color: '#FFFFFF', px: 2, py: 2.5 }}
    >
      <Box sx={{ px: 1, pb: 2 }}>
        <Logo variant="light" />
      </Box>

      <List sx={{ flex: 1, overflowY: 'auto' }}>
        {NAV_ITEMS.map(({ label, to, icon: Icon }) => (
          <ListItemButton
            key={to}
            component={NavLink}
            to={to}
            onClick={onNavigate}
            sx={{
              borderRadius: 2,
              mb: 0.5,
              color: 'rgba(255,255,255,0.72)',
              '&:hover': { backgroundColor: 'rgba(255,255,255,0.08)', color: '#FFFFFF' },
              '&.active': { background: gradients.primary, color: '#FFFFFF' },
            }}
          >
            <ListItemIcon sx={{ minWidth: 34, color: 'inherit' }}>
              <Icon size={18} aria-hidden />
            </ListItemIcon>
            <ListItemText
              primary={label}
              primaryTypographyProps={{ fontSize: '0.875rem', fontWeight: 500 }}
            />
          </ListItemButton>
        ))}
      </List>

      <Divider sx={{ borderColor: 'rgba(255,255,255,0.12)', my: 1.5 }} />

      {user && (
        <Stack direction="row" spacing={1.25} alignItems="center" sx={{ px: 1, pb: 1.5 }}>
          <Avatar sx={{ width: 34, height: 34, bgcolor: 'rgba(255,255,255,0.16)', fontSize: 13 }}>
            {user.name.slice(0, 2).toUpperCase()}
          </Avatar>
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="body2" sx={{ fontWeight: 600 }} noWrap>
              {user.name}
            </Typography>
            <Typography variant="caption" sx={{ color: 'rgba(255,255,255,0.6)' }} noWrap>
              {user.email}
            </Typography>
          </Box>
        </Stack>
      )}

      <Button
        onClick={() => void logout()}
        startIcon={<LogOut size={16} />}
        sx={{ justifyContent: 'flex-start', color: 'rgba(255,255,255,0.72)', px: 1.5 }}
      >
        Logout
      </Button>
    </Stack>
  );
};
