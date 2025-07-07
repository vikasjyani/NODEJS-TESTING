import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Provider } from 'react-redux';
import { ThemeProvider, createTheme, PaletteMode } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { Box } from '@mui/material';

import { store } from './store'; // Will be created in Chunk 3.2
import { WebSocketProvider } from './services/websocket'; // Will be created in Chunk 3.3
import { ErrorBoundary } from './components/common/ErrorBoundary'; // Will be created
import { Header } from './components/common/Header'; // Will be created
import { Sidebar } from './components/common/Sidebar'; // Will be created
import { LoadingOverlay } from './components/common/LoadingOverlay'; // Will be created
import { NotificationManager } from './components/common/NotificationManager'; // Will be created

// Page components (placeholders for now, will be created in Phase 4)
const Dashboard = () => <Box>Dashboard Page</Box>;
const DemandProjection = () => <Box>Demand Projection Page</Box>;
const DemandVisualization = () => <Box>Demand Visualization Page</Box>;
const LoadProfileGeneration = () => <Box>Load Profile Generation Page</Box>;
const LoadProfileAnalysis = () => <Box>Load Profile Analysis Page</Box>;
const PyPSAModeling = () => <Box>PyPSA Modeling Page</Box>;
const PyPSAResults = () => <Box>PyPSA Results Page</Box>;
const Settings = () => <Box>Settings Page</Box>;

// Theme configuration
const getDesignTokens = (mode: PaletteMode) => ({
  palette: {
    mode,
    ...(mode === 'light'
      ? {
          // Light mode palette
          primary: { main: '#1976d2' }, // Blue
          secondary: { main: '#dc004e' }, // Pink/Red
          background: { default: '#f4f6f8', paper: '#ffffff' },
          text: { primary: '#172b4d', secondary: '#6b778c' },
        }
      : {
          // Dark mode palette
          primary: { main: '#64b5f6' }, // Lighter Blue
          secondary: { main: '#f48fb1' }, // Lighter Pink/Red
          background: { default: '#121212', paper: '#1e1e1e' }, // Common dark background shades
          text: { primary: '#e0e0e0', secondary: '#b0bec5' },
        }),
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h4: { fontWeight: 600, fontSize: '1.75rem' },
    h5: { fontWeight: 500, fontSize: '1.5rem' },
    h6: { fontWeight: 500, fontSize: '1.25rem' },
    button: { textTransform: 'none' as 'none' } // Keep button text case as is
  },
  components: {
    MuiAppBar: {
      styleOverrides: {
        root: ({ theme }) => ({
          backgroundColor: theme.palette.mode === 'light' ? '#1565c0' : theme.palette.background.paper, // Darker blue for light, paper for dark
          boxShadow: theme.palette.mode === 'dark' ? '0px 1px 1px -1px rgba(255,255,255,0.12),0px 1px 1px 0px rgba(255,255,255,0.08),0px 1px 3px 0px rgba(255,255,255,0.04)' : undefined,
        }),
      },
    },
    MuiDrawer: {
        styleOverrides: {
            paper: ({ theme }) => ({
                 backgroundColor: theme.palette.mode === 'light' ? theme.palette.background.paper : '#1e1e1e', // Consistent sidebar background
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
            root: ({theme}) => ({
                 backgroundImage: 'none', // Disable MuiPaper's default gradient background image
            })
        }
    }
  },
  shape: {
    borderRadius: 8,
  },
});


const App: React.FC = () => {
  // For now, let's default to light mode.
  // A theme switcher could be added to Redux state later.
  const [mode, setMode] = React.useState<PaletteMode>('light');
  const theme = React.useMemo(() => createTheme(getDesignTokens(mode)), [mode]);

  useEffect(() => {
    document.title = 'KSEB Energy Futures Platform';
  }, []);

  // Example function to toggle theme (can be moved to a context or Redux)
  const toggleTheme = () => {
    setMode((prevMode) => (prevMode === 'light' ? 'dark' : 'light'));
  };


  const SIDEBAR_WIDTH = 256; // Define sidebar width

  return (
    <Provider store={store}>
      <ThemeProvider theme={theme}>
        <CssBaseline /> {/* Normalize CSS and apply background color */}
        <ErrorBoundary> {/* Will be created */}
          <WebSocketProvider> {/* Will be created */}
            <Router>
              <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
                <Header onToggleTheme={toggleTheme} sidebarWidth={SIDEBAR_WIDTH} /> {/* Pass toggle and width */}
                <Sidebar width={SIDEBAR_WIDTH} /> {/* Pass width */}

                <Box
                  component="main"
                  sx={{
                    flexGrow: 1,
                    p: { xs: 2, sm: 3 }, // Responsive padding
                    mt: '64px', // AppBar height
                    ml: { sm: `${SIDEBAR_WIDTH}px` }, // Margin for sidebar on larger screens
                    width: { sm: `calc(100% - ${SIDEBAR_WIDTH}px)` }, // Ensure main content takes remaining width
                    minHeight: 'calc(100vh - 64px)',
                    overflowX: 'hidden', // Prevent horizontal scroll if content is too wide
                  }}
                >
                  <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/demand-projection" element={<DemandProjection />} />
                    <Route path="/demand-visualization" element={<DemandVisualization />} />
                    <Route path="/load-profile-generation" element={<LoadProfileGeneration />} />
                    <Route path="/load-profile-analysis" element={<LoadProfileAnalysis />} />
                    <Route path="/pypsa-modeling" element={<PyPSAModeling />} />
                    <Route path="/pypsa-results" element={<PyPSAResults />} />
                    <Route path="/settings" element={<Settings />} />
                    <Route path="*" element={<Navigate to="/" replace />} /> {/* Fallback route */}
                  </Routes>
                </Box>

                <LoadingOverlay /> {/* Will be created */}
                <NotificationManager /> {/* Will be created */}
              </Box>
            </Router>
          </WebSocketProvider>
        </ErrorBoundary>
      </ThemeProvider>
    </Provider>
  );
};

export default App;
