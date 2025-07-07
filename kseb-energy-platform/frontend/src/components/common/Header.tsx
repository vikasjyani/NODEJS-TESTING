import React from 'react';
import { AppBar, Toolbar, Typography, IconButton, Box, Tooltip, Avatar } from '@mui/material';
import { Menu as MenuIcon, Brightness4, Brightness7, Notifications, AccountCircle, Settings, ExitToApp } from '@mui/icons-material';

interface HeaderProps {
  onToggleTheme: () => void;
  sidebarWidth: number; // To handle content shift if sidebar is part of layout under header
  onDrawerToggle?: () => void; // For mobile drawer toggle
}

export const Header: React.FC<HeaderProps> = ({ onToggleTheme, sidebarWidth, onDrawerToggle }) => {
  const currentThemeMode = 'light'; // This would ideally come from theme context or Redux

  return (
    <AppBar
      position="fixed"
      sx={{
        zIndex: (theme) => theme.zIndex.drawer + 1, // Ensure header is above sidebar
        // width: { sm: `calc(100% - ${sidebarWidth}px)` }, // Adjust width if sidebar is persistent
        // ml: { sm: `${sidebarWidth}px` }, // Adjust margin if sidebar is persistent
      }}
    >
      <Toolbar>
        {/* Hamburger Icon for mobile (optional, if sidebar is toggleable on mobile) */}
        {onDrawerToggle && (
            <IconButton
              color="inherit"
              aria-label="open drawer"
              edge="start"
              onClick={onDrawerToggle}
              sx={{ mr: 2, display: { sm: 'none' } }}
            >
              <MenuIcon />
            </IconButton>
        )}

        <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
          KSEB Energy Futures Platform
        </Typography>

        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Tooltip title="Toggle light/dark theme">
            <IconButton sx={{ ml: 1 }} onClick={onToggleTheme} color="inherit">
              {currentThemeMode === 'dark' ? <Brightness7 /> : <Brightness4 />}
            </IconButton>
          </Tooltip>

          <Tooltip title="Notifications">
            <IconButton sx={{ ml: 1 }} color="inherit">
              <Notifications />
            </IconButton>
          </Tooltip>

          {/* User Menu (Placeholder) */}
          <Tooltip title="User Account">
            <IconButton sx={{ ml: 1 }} color="inherit">
              <AccountCircle />
              {/* <Avatar sx={{ width: 32, height: 32 }}>U</Avatar> */}
            </IconButton>
          </Tooltip>
           {/* Can add a Menu component here for dropdown options like Profile, Settings, Logout */}
        </Box>
      </Toolbar>
    </AppBar>
  );
};
