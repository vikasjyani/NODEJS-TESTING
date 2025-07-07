import React from 'react';
import { Drawer, List, ListItem, ListItemButton, ListItemIcon, ListItemText, Toolbar, Divider, Box, Typography, Tooltip } from '@mui/material';
import { Link as RouterLink, useLocation } from 'react-router-dom';
import {
  Dashboard as DashboardIcon,
  ShowChart as DemandIcon,
  BarChart as LoadProfileIcon,
  DeveloperBoard as PyPSAIcon,
  Settings as SettingsIcon,
  HelpOutline as HelpIcon,
  Assessment as AnalysisIcon,
  BubbleChart as VisualizationIcon,
  AccountTree as ModelingIcon,
  ExitToApp as LogoutIcon
} from '@mui/icons-material';

interface SidebarProps {
  width: number;
  // onDrawerToggle?: () => void; // For mobile temporary drawer
  // mobileOpen?: boolean; // For mobile temporary drawer
}

const menuItems = [
  { text: 'Dashboard', icon: <DashboardIcon />, path: '/' },
  { text: 'Demand Projection', icon: <DemandIcon />, path: '/demand-projection' },
  { text: 'Demand Visualization', icon: <VisualizationIcon />, path: '/demand-visualization' },
  { text: 'Load Profile Gen.', icon: <LoadProfileIcon />, path: '/load-profile-generation' },
  { text: 'Load Profile Analysis', icon: <AnalysisIcon />, path: '/load-profile-analysis' },
  { text: 'PyPSA Modeling', icon: <ModelingIcon />, path: '/pypsa-modeling' },
  { text: 'PyPSA Results', icon: <PyPSAIcon />, path: '/pypsa-results' },
];

const secondaryMenuItems = [
    { text: 'Settings', icon: <SettingsIcon />, path: '/settings' },
    { text: 'Help', icon: <HelpIcon />, path: '/help' }, // Example, not in App.tsx routes yet
    { text: 'Logout', icon: <LogoutIcon />, path: '/logout'} // Example, not in App.tsx routes yet
]

export const Sidebar: React.FC<SidebarProps> = ({ width /*, onDrawerToggle, mobileOpen*/ }) => {
  const location = useLocation();

  const drawerContent = (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        <Toolbar sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', py: 2 }}>
            {/* Optional: Logo or App Name here */}
            <Typography variant="h6" component="div" sx={{color: 'primary.main', fontWeight: 'bold'}}>
                KSEB EFP
            </Typography>
        </Toolbar>
        <Divider />
        <List sx={{ flexGrow: 1, overflowY: 'auto', p:1 }}>
        {menuItems.map((item) => (
          <ListItem key={item.text} disablePadding sx={{ display: 'block' }}>
            <Tooltip title={item.text} placement="right" arrow disableHoverListener={false}>
                <ListItemButton
                component={RouterLink}
                to={item.path}
                selected={location.pathname === item.path || (item.path !== "/" && location.pathname.startsWith(item.path))}
                sx={{
                    minHeight: 48,
                    justifyContent: 'initial',
                    px: 2.5,
                    borderRadius: (theme) => theme.shape.borderRadius,
                    mb: 0.5,
                    '&.Mui-selected': {
                        backgroundColor: (theme) => theme.palette.action.selected,
                        color: (theme) => theme.palette.primary.main,
                        '& .MuiListItemIcon-root': {
                            color: (theme) => theme.palette.primary.main,
                        },
                         '&:hover': {
                            backgroundColor: (theme) => theme.palette.action.hover,
                        }
                    },
                    '&:hover': {
                        backgroundColor: (theme) => theme.palette.action.hover,
                    }
                }}
                >
                <ListItemIcon
                    sx={{
                    minWidth: 0,
                    mr: 3, // open ? 3 : 'auto',
                    justifyContent: 'center',
                    }}
                >
                    {item.icon}
                </ListItemIcon>
                <ListItemText primary={item.text} sx={{ opacity: 1 /*open ? 1 : 0*/ }} />
                </ListItemButton>
            </Tooltip>
          </ListItem>
        ))}
      </List>
      <Divider />
      <List sx={{p:1}}>
        {secondaryMenuItems.map((item) => (
             <ListItem key={item.text} disablePadding sx={{ display: 'block' }}>
                <Tooltip title={item.text} placement="right" arrow disableHoverListener={false}>
                    <ListItemButton
                        component={RouterLink}
                        to={item.path}
                        selected={location.pathname === item.path}
                         sx={{
                            minHeight: 48,
                            justifyContent: 'initial',
                            px: 2.5,
                            borderRadius: (theme) => theme.shape.borderRadius,
                            mb: 0.5,
                             '&.Mui-selected': {
                                backgroundColor: (theme) => theme.palette.action.selected,
                                '&:hover': {
                                    backgroundColor: (theme) => theme.palette.action.hover,
                                }
                            },
                            '&:hover': {
                                backgroundColor: (theme) => theme.palette.action.hover,
                            }
                        }}
                    >
                        <ListItemIcon  sx={{ minWidth: 0, mr: 3, justifyContent: 'center' }}>{item.icon}</ListItemIcon>
                        <ListItemText primary={item.text} />
                    </ListItemButton>
                </Tooltip>
             </ListItem>
        ))}
      </List>
    </Box>
  );

  return (
    <Box
      component="nav"
      sx={{ width: { sm: width }, flexShrink: { sm: 0 } }}
      aria-label="mailbox folders"
    >
      {/* For mobile: Temporary Drawer */}
      {/* <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={onDrawerToggle}
        ModalProps={{
          keepMounted: true, // Better open performance on mobile.
        }}
        sx={{
          display: { xs: 'block', sm: 'none' },
          '& .MuiDrawer-paper': { boxSizing: 'border-box', width: width },
        }}
      >
        {drawerContent}
      </Drawer> */}

      {/* For desktop: Permanent Drawer */}
      <Drawer
        variant="permanent"
        sx={{
          display: { xs: 'none', sm: 'block' },
          '& .MuiDrawer-paper': { boxSizing: 'border-box', width: width, borderRight: (theme) => `1px solid ${theme.palette.divider}` },
        }}
        open // Permanent drawer is always open
      >
        {drawerContent}
      </Drawer>
    </Box>
  );
};
