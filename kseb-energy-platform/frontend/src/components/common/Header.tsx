import React from 'react';
import { AppBar, Toolbar, Typography, IconButton, Box, Tooltip, PaletteMode, Avatar } from '@mui/material'; // Added PaletteMode
import { Menu as MenuIcon, Brightness4, Brightness7, Notifications, AccountCircle, Settings, ExitToApp } from '@mui/icons-material';
// Removed useTheme as mode comes from props now

interface HeaderProps {
  onToggleTheme: () => void;
  currentThemeMode: PaletteMode; // Added prop to receive current theme mode
  sidebarWidth: number;
  onDrawerToggle?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onToggleTheme, currentThemeMode, sidebarWidth, onDrawerToggle }) => {
  // const theme = useTheme(); // No longer needed if mode is passed as prop
  // const currentThemeMode = theme.palette.mode;

  return (
    <AppBar
      position="fixed"
      sx={{
        zIndex: (theme) => theme.zIndex.drawer + 1,
      }}
    >
      <Toolbar>
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

          <Tooltip title="User Account">
            <IconButton sx={{ ml: 1 }} color="inherit">
              <AccountCircle />
            </IconButton>
          </Tooltip>
        </Box>
      </Toolbar>
    </AppBar>
  );
};
