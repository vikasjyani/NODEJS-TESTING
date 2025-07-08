import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Provider } from 'react-redux';
import { ThemeProvider, createTheme, Theme } from '@mui/material/styles';
import { PaletteMode } from '@mui/material';
import CssBaseline from '@mui/material/CssBaseline';
import { Box } from '@mui/material';

import { store } from './store';
import { WebSocketProvider } from './services/websocket';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { Header } from './components/common/Header';
import { Sidebar } from './components/common/Sidebar';
import { LoadingOverlay } from './components/common/LoadingOverlay';
import { NotificationManager } from './components/common/NotificationManager';

// Placeholder Page Imports (actual pages will be imported once their errors are fixed)
import Typography from '@mui/material/Typography'; // For placeholder pages
const Dashboard = () => <Box sx={{p:2}}><Typography variant="h5">Dashboard Page Content</Typography></Box>;
const DemandProjectionPage = () => <Box sx={{p:2}}><Typography variant="h5">Demand Projection Page Content</Typography></Box>;
const DemandVisualizationPage = () => <Box sx={{p:2}}><Typography variant="h5">Demand Visualization Page Content</Typography></Box>;
const LoadProfileGenerationPage = () => <Box sx={{p:2}}><Typography variant="h5">Load Profile Generation Page Content</Typography></Box>;
const LoadProfileAnalysisPage = () => <Box sx={{p:2}}><Typography variant="h5">Load Profile Analysis Page Content</Typography></Box>;
const PyPSAModelingPage = () => <Box sx={{p:2}}><Typography variant="h5">PyPSA Modeling Page Content</Typography></Box>;
const PyPSAResultsPage = () => <Box sx={{p:2}}><Typography variant="h5">PyPSA Results Page Content</Typography></Box>;
const SettingsPage = () => <Box sx={{p:2}}><Typography variant="h5">Settings Page Content</Typography></Box>;
// End Placeholder Page Imports


const getDesignTokens = (mode: PaletteMode) => ({
  palette: {
    mode,
    ...(mode === 'light'
      ? {
          primary: { main: '#1976d2' },
          secondary: { main: '#dc004e' },
          background: { default: '#f4f6f8', paper: '#ffffff' },
          text: { primary: '#172b4d', secondary: '#6b778c' },
        }
      : {
          primary: { main: '#64b5f6' },
          secondary: { main: '#f48fb1' },
          background: { default: '#121212', paper: '#1e1e1e' },
          text: { primary: '#e0e0e0', secondary: '#b0bec5' },
        }),
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h4: { fontWeight: 600, fontSize: '1.75rem' },
    h5: { fontWeight: 500, fontSize: '1.5rem' },
    h6: { fontWeight: 500, fontSize: '1.25rem' },
    button: { textTransform: 'none' as 'none' }
  },
  components: {
    MuiAppBar: {
      styleOverrides: {
        root: ({ theme }: { theme: Theme }) => ({
          backgroundColor: theme.palette.mode === 'light' ? '#1565c0' : theme.palette.background.paper,
          boxShadow: theme.palette.mode === 'dark' ? '0px 1px 1px -1px rgba(255,255,255,0.12),0px 1px 1px 0px rgba(255,255,255,0.08),0px 1px 3px 0px rgba(255,255,255,0.04)' : undefined,
        }),
      },
    },
    MuiDrawer: {
        styleOverrides: {
            paper: ({ theme }: { theme: Theme }) => ({
                 backgroundColor: theme.palette.mode === 'light' ? theme.palette.background.paper : '#1e1e1e',
            }),
        }
    },
    MuiButton: {
      defaultProps: {
        disableElevation: true,
      },
    },
    MuiPaper: {
        styleOverrides: {
            root: ({theme}: { theme: Theme }) => ({
                 backgroundImage: 'none',
            })
        }
    }
  },
  shape: {
    borderRadius: 8,
  },
});


const App: React.FC = () => {
  const [mode, setMode] = React.useState<PaletteMode>('light');
  const theme = React.useMemo(() => createTheme(getDesignTokens(mode)), [mode]);

  useEffect(() => {
    document.title = 'KSEB Energy Futures Platform';
  }, []);

  const toggleTheme = () => {
    setMode((prevMode: PaletteMode) => (prevMode === 'light' ? 'dark' : 'light'));
  };

  const SIDEBAR_WIDTH = 256;

  return (
    <Provider store={store}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <ErrorBoundary>
          <WebSocketProvider>
            <Router>
              <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
                <Header onToggleTheme={toggleTheme} currentThemeMode={mode} sidebarWidth={SIDEBAR_WIDTH} /> {/* Passed currentThemeMode */}
                <Sidebar width={SIDEBAR_WIDTH} />

                <Box
                  component="main"
                  sx={{
                    flexGrow: 1,
                    p: { xs: 2, sm: 3 },
                    mt: '64px',
                    ml: { sm: `${SIDEBAR_WIDTH}px` },
                    width: { sm: `calc(100% - ${SIDEBAR_WIDTH}px)` },
                    minHeight: 'calc(100vh - 64px)',
                    overflowX: 'hidden',
                  }}
                >
                  <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/demand-projection" element={<DemandProjectionPage />} />
                    <Route path="/demand-visualization" element={<DemandVisualizationPage />} />
                    <Route path="/load-profile-generation" element={<LoadProfileGenerationPage />} />
                    <Route path="/load-profile-analysis" element={<LoadProfileAnalysisPage />} />
                    <Route path="/pypsa-modeling" element={<PyPSAModelingPage />} />
                    <Route path="/pypsa-results" element={<PyPSAResultsPage />} />
                    <Route path="/settings" element={<SettingsPage />} />
                    <Route path="*" element={<Navigate to="/" replace />} />
                  </Routes>
                </Box>

                <LoadingOverlay />
                <NotificationManager />
              </Box>
            </Router>
          </WebSocketProvider>
        </ErrorBoundary>
      </ThemeProvider>
    </Provider>
  );
};

export default App;
