import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore, Store } from '@reduxjs/toolkit'; // Import Store type
import { ThemeProvider, createTheme } from '@mui/material/styles';
import '@testing-library/jest-dom';
import { BrowserRouter as Router } from 'react-router-dom'; // Needed for components using Link/useNavigate

// Import components to test (adjust paths as necessary)
import { DemandProjection } from '../../frontend/src/pages/DemandProjection';
import { LoadProfileGeneration } from '../../frontend/src/pages/LoadProfileGeneration';
import { PyPSAModeling } from '../../frontend/src/pages/PyPSAModeling';
import { PlotlyChart, LineChart } from '../../frontend/src/components/charts/PlotlyChart'; // Assuming PlotlyChart is created
import { DataTable, Column } from '../../frontend/src/components/common/DataTable'; // Assuming DataTable is created
import { FileUpload } from '../../frontend/src/components/common/FileUpload'; // Assuming FileUpload is created

// Slices - import actual reducers
import projectReducer from '../../frontend/src/store/slices/projectSlice';
import demandReducer from '../../frontend/src/store/slices/demandSlice';
import loadProfileReducer from '../../frontend/src/store/slices/loadProfileSlice';
import pypsaReducer from '../../frontend/src/store/slices/pypsaSlice';
import uiReducer from '../../frontend/src/store/slices/uiSlice';
import notificationReducer from '../../frontend/src/store/slices/notificationSlice';
import { apiSlice } from '../../frontend/src/store/api/apiSlice'; // Import actual apiSlice

// Mock WebSocket context if components use it directly
jest.mock('../../frontend/src/services/websocket', () => ({
  ...jest.requireActual('../../frontend/src/services/websocket'), // Keep original exports
  useWebSocket: () => ({ // Mock the hook's return value
    socket: null,
    isConnected: true,
    joinRoom: jest.fn(),
    leaveRoom: jest.fn(),
    emitEvent: jest.fn(),
  }),
  // Mock specific progress hooks if they are called directly within tested components
  useForecastNotifications: jest.fn(),
  useProfileNotifications: jest.fn(),
  usePyPSANotifications: jest.fn(),
}));


// Helper to create a mock store for each test or group of tests
const createMockStore = (preloadedState = {}): Store => { // Add return type Store
  return configureStore({
    reducer: {
      [apiSlice.reducerPath]: apiSlice.reducer,
      project: projectReducer,
      demand: demandReducer,
      loadProfile: loadProfileReducer,
      pypsa: pypsaReducer,
      ui: uiReducer,
      notifications: notificationReducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(apiSlice.middleware),
    preloadedState,
  });
};

const theme = createTheme(); // Use your app's theme if customized

// Wrapper component for tests needing Redux store, Theme, and Router
const TestWrapper: React.FC<{ children: React.ReactNode; initialStoreState?: any }> = ({
    children,
    initialStoreState = {}
}) => {
    const store = createMockStore(initialStoreState);
    return (
        <Provider store={store}>
            <ThemeProvider theme={theme}>
                <Router> {/* Add Router here */}
                    {children}
                </Router>
            </ThemeProvider>
        </Provider>
    );
};

// --- Page Component Tests ---
describe('DemandProjection Page', () => {
    it('renders demand projection page title and configure button', () => {
        render(<TestWrapper><DemandProjection /></TestWrapper>);
        expect(screen.getByText(/Demand Projection/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Configure Forecast/i })).toBeInTheDocument();
    });

    it('opens configuration dialog on button click', async () => {
        render(<TestWrapper><DemandProjection /></TestWrapper>);
        const configButton = screen.getByRole('button', { name: /Configure Forecast/i });
        fireEvent.click(configButton);
        // Dialog title might be different or nested, adjust selector
        await waitFor(() => {
            expect(screen.getByRole('dialog')).toBeInTheDocument();
            expect(screen.getByText(/Configure New Demand Forecast/i)).toBeInTheDocument();
        });
    });
});

describe('LoadProfileGeneration Page', () => {
    it('renders load profile generation page title and wizard', () => {
        render(<TestWrapper><LoadProfileGeneration /></TestWrapper>);
        expect(screen.getByText(/Load Profile Generation/i)).toBeInTheDocument();
        expect(screen.getByText(/Generation Wizard/i)).toBeInTheDocument();
    });

    it('allows method selection', async () => {
        render(<TestWrapper><LoadProfileGeneration /></TestWrapper>);
        // Assuming 'Base Year Scaling' is one of the method names
        const baseScalingMethodCard = screen.getByText(/Base Year Scaling/i);
        expect(baseScalingMethodCard).toBeInTheDocument();
        fireEvent.click(baseScalingMethodCard);
        // Check if the wizard moves to the next step or updates state accordingly
        // This might require inspecting the Stepper's active step or a change in displayed content
        await waitFor(() => {
            // Example check: The "Configuration" step's description or unique content appears
            expect(screen.getByText(/Set parameters for the selected generation method/i)).toBeVisible();
        });
    });
});

describe('PyPSAModeling Page', () => {
    it('renders PyPSA modeling page title and configuration sections', () => {
        render(<TestWrapper><PyPSAModeling /></TestWrapper>);
        expect(screen.getByText(/PyPSA Power System Modeling/i)).toBeInTheDocument();
        expect(screen.getByText(/Model Configuration/i)).toBeInTheDocument();
        // Check for a specific accordion or input field
        expect(screen.getByLabelText(/Scenario Name/i)).toBeInTheDocument();
    });
});


// --- Common Component Tests ---
describe('PlotlyChart Component', () => {
    // Mock Plotly.js to avoid actual rendering in tests if it's heavy
    // jest.mock('react-plotly.js', () => ({
    //   __esModule: true,
    //   default: jest.fn(({data, layout}) => ( // Simple mock render
    //     <div data-testid="mock-plotly-chart">
    //       <pre>{JSON.stringify({dataCount: data.length, layoutTitle: layout?.title}, null, 2)}</pre>
    //     </div>
    //   )),
    // }));
    // Note: Lazy loading Plotly might require different mocking or test setup for Suspense

    const mockChartData = [{ x: [1, 2, 3], y: [10, 15, 13], type: 'scatter' as Plotly.PlotType }];

    it('renders chart title and shows loading state', async () => {
        render(
            <TestWrapper>
                <PlotlyChart data={[]} title="Test Chart Loading" loading={true} height={300} />
            </TestWrapper>
        );
        expect(screen.getByText('Loading chart...')).toBeInTheDocument();
        // Title might not be rendered when loading, depending on implementation
        // If title is always rendered, add: expect(screen.getByText('Test Chart Loading')).toBeInTheDocument();
    });

    it('renders chart with data when not loading (basic check)', async () => {
        // This test will be basic due to Plotly being complex to fully test in JSDOM
        // It primarily checks if the component attempts to render Plotly
        render(
            <TestWrapper>
                 <React.Suspense fallback={<div>Loading Plotly...</div>}>
                    <PlotlyChart data={mockChartData} title="Actual Test Chart" height={300} />
                 </React.Suspense>
            </TestWrapper>
        );
        await screen.findByText('Actual Test Chart'); // Wait for title to appear
        // Due to lazy loading and Plotly's nature, deeper inspection is hard without e2e
        // We can check if the container for Plotly is there.
        // The actual Plotly rendering is complex and usually not unit-tested.
        // We trust react-plotly.js works.
    });

    it('shows error message when error prop is provided', () => {
        render(<TestWrapper><PlotlyChart data={[]} title="Error Chart" error="Failed to load data" height={300}/></TestWrapper>);
        expect(screen.getByText(/Error loading chart: Failed to load data/i)).toBeInTheDocument();
    });
});

describe('DataTable Component', () => {
    interface SampleData { id: number; name: string; value: number; }
    const columns: Column<SampleData>[] = [
        { id: 'id', label: 'ID', sortable: true },
        { id: 'name', label: 'Name', sortable: true, filterable: true },
        { id: 'value', label: 'Value', sortable: true, type: 'number' },
    ];
    const data: SampleData[] = [
        { id: 1, name: 'Alpha', value: 100 },
        { id: 2, name: 'Bravo', value: 200 },
        { id: 3, name: 'Charlie', value: 150 },
    ];

    it('renders table with title, headers, and data', () => {
        render(<TestWrapper><DataTable columns={columns} data={data} title="Sample Table" /></TestWrapper>);
        expect(screen.getByText('Sample Table')).toBeInTheDocument();
        columns.forEach(col => expect(screen.getByText(col.label)).toBeInTheDocument());
        data.forEach(row => expect(screen.getByText(row.name)).toBeInTheDocument());
    });

    it('sorts data when a sortable column header is clicked', () => {
        render(<TestWrapper><DataTable columns={columns} data={data} title="Sortable Table" /></TestWrapper>);
        const nameHeader = screen.getByText('Name');
        fireEvent.click(nameHeader); // Sort ascending by name
        let rows = screen.getAllByRole('row');
        // Row 0 is header, Row 1 is first data row
        expect(rows[1].textContent).toContain('Alpha');
        fireEvent.click(nameHeader); // Sort descending by name
        rows = screen.getAllByRole('row');
        expect(rows[1].textContent).toContain('Charlie');
    });

    it('filters data based on search term', () => {
        render(<TestWrapper><DataTable columns={columns} data={data} title="Searchable Table" searchable={true} /></TestWrapper>);
        const searchInput = screen.getByPlaceholderText(/Search table/i);
        fireEvent.change(searchInput, { target: { value: 'Bravo' } });
        expect(screen.getByText('Bravo')).toBeInTheDocument();
        expect(screen.queryByText('Alpha')).not.toBeInTheDocument();
    });
});

describe('FileUpload Component', () => {
    it('renders file upload zone and title', () => {
        render(<TestWrapper><FileUpload title="Test Uploader" onFilesProcess={jest.fn()} /></TestWrapper>);
        expect(screen.getByText('Test Uploader')).toBeInTheDocument();
        expect(screen.getByText(/Select or Drop Files/i)).toBeInTheDocument(); // Part of default description
    });

    // More complex tests for FileUpload would involve mocking File objects and react-dropzone interactions,
    // which can be involved. Basic render check is a good start.
    // Example for simulating a drop:
    // it('processes dropped files', async () => {
    //   const mockOnFilesProcess = jest.fn();
    //   render(<TestWrapper><FileUpload onFilesProcess={mockOnFilesProcess} /></TestWrapper>);
    //   const dropzone = screen.getByText(/Drag 'n' drop files here/i).closest('div'); // Adjust selector

    //   const file = new File(['content'], 'testfile.png', { type: 'image/png' });
    //   Object.defineProperty(dropzone, 'files', { value: [file] }); // Mocking files property

    //   // This is a simplification. react-dropzone's onDrop is complex to trigger manually.
    //   // You might need to mock react-dropzone itself for deeper testing.
    //   // await act(async () => {
    //   //   fireEvent.drop(dropzone);
    //   // });
    //   // expect(mockOnFilesProcess).toHaveBeenCalled();
    // });
});

// Simple test to ensure the TestWrapper and store are minimally functional
describe('TestWrapper with Redux Store', () => {
    it('renders children and provides store', () => {
        const testMessage = "Child Component Rendered";
        const store = createMockStore({ ui: { isLoading: false, theme: 'light' } }); // Example initial state
        render(
            <Provider store={store}>
                <ThemeProvider theme={theme}>
                    <Router>
                        <div>{testMessage}</div>
                    </Router>
                </ThemeProvider>
            </Provider>
        );
        expect(screen.getByText(testMessage)).toBeInTheDocument();
    });
});
