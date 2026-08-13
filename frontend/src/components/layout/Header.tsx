import {
  AppBar,
  Avatar,
  Badge,
  Box,
  Divider,
  IconButton,
  ListItemIcon,
  Menu,
  MenuItem,
  Stack,
  Toolbar,
  Tooltip,
  Typography,
} from '@mui/material';
import { Bell, CircleHelp, LogOut, Menu as MenuIcon, Settings, User } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useAuth } from '@/hooks/useAuth';

interface HeaderProps {
  title: string;
  description?: string;
  onOpenSidebar: () => void;
}

export const Header = ({ title, description, onOpenSidebar }: HeaderProps): JSX.Element => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const [helpAnchorEl, setHelpAnchorEl] = useState<HTMLElement | null>(null);

  return (
    <AppBar
      position="sticky"
      elevation={0}
      color="inherit"
      sx={{ borderBottom: 1, borderColor: 'divider', bgcolor: 'background.paper' }}
    >
      <Toolbar sx={{ gap: 1, minHeight: { xs: 60, md: 72 } }}>
        <IconButton
          onClick={onOpenSidebar}
          aria-label="Open navigation menu"
          sx={{ display: { lg: 'none' } }}
        >
          <MenuIcon size={20} />
        </IconButton>

        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="h4" component="h1" noWrap>
            {title}
          </Typography>
          {description && (
            <Typography variant="caption" color="text.secondary" noWrap component="p">
              {description}
            </Typography>
          )}
        </Box>

        <Stack direction="row" spacing={0.5} alignItems="center">
          <Tooltip title="How it works">
            <IconButton aria-label="Open help menu" onClick={(e) => setHelpAnchorEl(e.currentTarget)}>
              <CircleHelp size={19} />
            </IconButton>
          </Tooltip>
          <Tooltip title="Notifications">
            <IconButton aria-label="Notifications">
              <Badge color="primary" variant="dot">
                <Bell size={19} />
              </Badge>
            </IconButton>
          </Tooltip>
          <IconButton
            onClick={(e) => setAnchorEl(e.currentTarget)}
            aria-label="Open account menu"
            aria-haspopup="menu"
          >
            <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.main', fontSize: 13 }}>
              {(user?.name ?? 'U').slice(0, 2).toUpperCase()}
            </Avatar>
          </IconButton>
        </Stack>

        <Menu
          anchorEl={helpAnchorEl}
          open={Boolean(helpAnchorEl)}
          onClose={() => setHelpAnchorEl(null)}
        >
          <MenuItem disabled sx={{ opacity: 1 }}>
            <Typography variant="caption" sx={{ fontWeight: 700 }}>
              How generation works
            </Typography>
          </MenuItem>
          <Divider />
          {[
            '1. Enter a raw campaign brief',
            '2. Choose brand, channel and audience',
            '3. Six agents extract, ground, write and check',
            '4. Review, copy or download the output',
          ].map((step) => (
            <MenuItem key={step} onClick={() => setHelpAnchorEl(null)}>
              <Typography variant="body2">{step}</Typography>
            </MenuItem>
          ))}
        </Menu>

        <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={() => setAnchorEl(null)}>
          <MenuItem disabled sx={{ opacity: 1 }}>
            <Stack>
              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                {user?.name}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {`${user?.email ?? ''} · ${user?.role ?? ''}`}
              </Typography>
            </Stack>
          </MenuItem>
          <Divider />
          <MenuItem
            onClick={() => {
              setAnchorEl(null);
              navigate('/settings');
            }}
          >
            <ListItemIcon>
              <User size={16} />
            </ListItemIcon>
            Profile
          </MenuItem>
          <MenuItem
            onClick={() => {
              setAnchorEl(null);
              navigate('/settings');
            }}
          >
            <ListItemIcon>
              <Settings size={16} />
            </ListItemIcon>
            Settings
          </MenuItem>
          <Divider />
          <MenuItem
            onClick={() => {
              setAnchorEl(null);
              void logout();
            }}
          >
            <ListItemIcon>
              <LogOut size={16} />
            </ListItemIcon>
            Logout
          </MenuItem>
        </Menu>
      </Toolbar>
    </AppBar>
  );
};
