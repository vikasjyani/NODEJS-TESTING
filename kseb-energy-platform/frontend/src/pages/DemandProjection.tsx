import React, { useState, useEffect } from 'react';
import { useSelector } from 'react-redux'; // useDispatch removed as it's not directly used here now
import {
  Container, Grid, Paper, Typography, Button, Box,
  Tabs, Tab, LinearProgress, Dialog, DialogTitle,
  DialogContent, Alert, Chip, CircularProgress
} from '@mui/material';
import { PlayArrow, StopCircle, Settings, Assessment, BarChart, Timeline, Insights, Storage } from '@mui/icons-material'; // Added more icons

import { RootState, useAppDispatch } from '../store'; // Assuming useAppDispatch is exported from store/hooks via store/index
import {
  useGetSectorDataQuery,
  useRunForecastMutation,
  useGetCorrelationDataQuery,
  // useGetForecastStatusQuery, // RTK Query hook for status polling (alternative/supplement to WebSocket)
} from '../store/api/apiSlice';
import { useForecastNotifications } from '../services/websocket'; // Changed from useForecastProgress
import { SectorNavigation, SectorQualityData, QualityColor } from '../components/demand/SectorNavigation'; // Will be created
import { DataVisualization } from '../components/demand/DataVisualization'; // Will be created
import { CorrelationAnalysis } from '../components/demand/CorrelationAnalysis'; // Will be created
import { ForecastConfiguration, ForecastConfigData } from '../components/demand/ForecastConfiguration'; // Will be created
import { ProgressMonitor } from '../components/demand/ProgressMonitor'; // Will be created
import { addNotification } from '../store/slices/notificationSlice'; // For local notifications

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
  className?: string;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index, className }) => (
  <div role="tabpanel" hidden={value !== index} id={`demand-tabpanel-${index}`} aria-labelledby={`demand-tab-${index}`} className={className} style={{ paddingTop: 16 }}>
    {value === index && <Box sx={{ p: {xs: 1, sm: 2} }}>{children}</Box>}
  </div>
);

const availableSectors = [
    { id: 'residential', label: 'Residential', icon: <BarChart /> },
    { id: 'commercial', label: 'Commercial', icon: <Timeline /> },
    { id: 'industrial', label: 'Industrial', icon: <Insights /> },
    { id: 'agriculture', label: 'Agriculture', icon: <BarChart /> }, // Replace with relevant icon
    { id: 'transport', label: 'Transport', icon: <Timeline /> }, // Replace with relevant icon
];


export const DemandProjection: React.FC = () => {
  const dispatch = useAppDispatch();
  const [selectedSector, setSelectedSector] = useState<string>(availableSectors[0].id);
  const [currentTab, setCurrentTab] = useState(0);
  const [configDialogOpen, setConfigDialogOpen] = useState(false);

  // Track the ID of the forecast job initiated from this component
  const [currentForecastJobId, setCurrentForecastJobId] = useState<string | null>(null);

  // API hooks for data fetching
  const {
    data: sectorData,
    isLoading: sectorLoading,
    error: sectorError,
    refetch: refetchSectorData,
  } = useGetSectorDataQuery(selectedSector, {
      // skip: !selectedSector, // Skip query if no sector selected (though we default one)
      // refetchOnMountOrArgChange: true, // Refetch if sector changes
  });

  const {
    data: correlationData,
    isLoading: correlationLoading,
    error: correlationError,
    refetch: refetchCorrelationData,
  } = useGetCorrelationDataQuery(selectedSector, {
      // skip: !selectedSector,
      // refetchOnMountOrArgChange: true,
  });

  const [runForecast, { isLoading: forecastStarting, error: forecastStartError }] = useRunForecastMutation();

  // Redux state for all forecast jobs (managed by WebSocket updates and direct dispatches)
  const forecastJobs = useSelector((state: RootState) => state.demand.forecastJobs);

  // Get the specific job this component is tracking
  const activeJobDetails = currentForecastJobId ? forecastJobs[currentForecastJobId] : null;

  // Subscribe to WebSocket notifications for the active forecast job
  useForecastNotifications(currentForecastJobId);

  // Effect to handle forecast start errors
  useEffect(() => {
    if (forecastStartError) {
      dispatch(addNotification({type: 'error', message: `Failed to start forecast: ${ (forecastStartError as any)?.data?.message || (forecastStartError as any)?.error || 'Unknown error'}`}));
    }
  }, [forecastStartError, dispatch]);


  const handleSectorChange = (sector: string) => {
    setSelectedSector(sector);
    setCurrentTab(0); // Reset to data view
    // refetchSectorData(); // RTK Query handles refetch on arg change if configured
    // refetchCorrelationData();
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  const handleStartForecast = async (config: ForecastConfigData) => {
    try {
      // The `runForecast` mutation from RTK Query will make the API call.
      // The backend will return a forecastId.
      const response = await runForecast(config).unwrap(); // unwrap() throws on error
      if (response.success && response.forecastId) {
        setCurrentForecastJobId(response.forecastId); // Start tracking this job
        setConfigDialogOpen(false);
        dispatch(addNotification({type: 'info', message: `Forecast job '${response.forecastId}' started.`}));
      } else {
        dispatch(addNotification({type: 'error', message: response.message || 'Failed to start forecast job.'}));
      }
    } catch (err: any) {
      // Error is already handled by the useEffect for forecastStartError,
      // but you can log it here or show a more specific error if needed.
      console.error('Failed to start forecast:', err);
      // dispatch(addNotification({type: 'error', message: `Error initiating forecast: ${err.data?.message || err.error || 'Unknown error'}`}));
    }
  };

  const handleCancelForecast = () => {
      if (activeJobDetails && (activeJobDetails.status === 'running' || activeJobDetails.status === 'queued')) {
          // TODO: Implement API call to cancel forecast
          // e.g., using a mutation: cancelForecastMutation(activeJobDetails.id);
          console.warn("Cancel forecast functionality to be fully implemented via API call.");
          dispatch(addNotification({type: 'info', message: `Requesting cancellation for forecast ${activeJobDetails.id}.`}));
          // For now, just clear current tracking
          // setCurrentForecastJobId(null); // Or wait for WebSocket 'cancelled' event
      }
  };

  // Mock data quality - in real app, this would come from backend/validation
  const getSectorQuality = (sector: string): SectorQualityData => {
    const qualities: { [key: string]: { score: number; issues: string[] } } = {
      residential: { score: 0.9, issues: [] },
      commercial: { score: 0.75, issues: ["Missing data for 2019 Q3"] },
      industrial: { score: 0.8, issues: [] },
      agriculture: { score: 0.6, issues: ["Inconsistent units", "Outliers present"] },
      transport: { score: 0.4, issues: ["High number of missing values", "Short historical data"] }
    };
    return qualities[sector] || { score: 0.5, issues: ["Data quality unknown"] };
  };

  const getQualityColor = (score: number): QualityColor => {
    if (score >= 0.8) return 'success';
    if (score >= 0.6) return 'warning';
    return 'error';
  };

  return (
    <Container maxWidth="xl" sx={{pb: 4}}>
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Paper sx={{ p: {xs:2, sm:3}, borderRadius: 2 }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={2}>
              <Box>
                <Typography variant="h4" component="h1" gutterBottom>
                  Demand Projection
                </Typography>
                <Typography variant="body1" color="text.secondary">
                  Analyze historical data, configure, and run electricity demand forecasts.
                </Typography>
              </Box>
              <Box sx={{display: 'flex', gap: 1}}>
                <Button
                  variant="contained"
                  startIcon={<Settings />}
                  onClick={() => setConfigDialogOpen(true)}
                  disabled={forecastStarting || (activeJobDetails?.status === 'running')}
                >
                  Configure Forecast
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<Assessment />}
                  disabled={!sectorData && !activeJobDetails} // Enable if data or a job exists
                  onClick={() => setCurrentTab(2)} // Navigate to results/scenarios tab
                >
                  View Results
                </Button>
              </Box>
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12}>
          <SectorNavigation
            sectors={availableSectors}
            selectedSector={selectedSector}
            onSectorChange={handleSectorChange}
            getSectorQuality={getSectorQuality}
            getQualityColor={getQualityColor}
          />
        </Grid>

        {activeJobDetails && (activeJobDetails.status === 'running' || activeJobDetails.status === 'queued') && (
          <Grid item xs={12}>
            <ProgressMonitor
              job={activeJobDetails}
              onCancel={handleCancelForecast} // Pass cancel handler
              title={`Forecast: ${activeJobDetails.config?.scenario_name || activeJobDetails.id}`}
            />
          </Grid>
        )}
         {activeJobDetails && activeJobDetails.status === 'failed' && (
            <Grid item xs={12}>
                <Alert severity="error" onClose={() => setCurrentForecastJobId(null)}>
                    Forecast '{activeJobDetails.config?.scenario_name || activeJobDetails.id}' failed: {activeJobDetails.error}
                </Alert>
            </Grid>
        )}
        {activeJobDetails && activeJobDetails.status === 'completed' && (
            <Grid item xs={12}>
                <Alert severity="success" onClose={() => {/* Optionally clear or allow viewing results */}}>
                    Forecast '{activeJobDetails.config?.scenario_name || activeJobDetails.id}' completed successfully.
                     <Button size="small" onClick={() => setCurrentTab(2)} sx={{ml:2}}>View Results</Button>
                </Alert>
            </Grid>
        )}


        <Grid item xs={12}>
          <Paper sx={{ borderRadius: 2, overflow: 'hidden' }}>
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
              <Tabs value={currentTab} onChange={handleTabChange} aria-label="demand analysis tabs" variant="scrollable" scrollButtons="auto">
                <Tab label="Historical Data" id="demand-tab-0" aria-controls="demand-tabpanel-0" />
                <Tab label="Correlation Analysis" id="demand-tab-1" aria-controls="demand-tabpanel-1" />
                <Tab label="Forecast Results & Scenarios" id="demand-tab-2" aria-controls="demand-tabpanel-2" />
                <Tab label="Model Performance" id="demand-tab-3" aria-controls="demand-tabpanel-3" />
              </Tabs>
            </Box>

            <TabPanel value={currentTab} index={0}>
              <DataVisualization
                sectorData={sectorData?.sample_data} // Assuming sectorData has this structure
                stats={sectorData?.statistics}
                quality={sectorData?.data_quality}
                isLoading={sectorLoading}
                error={sectorError as any} // Cast error if type is complex
                sector={selectedSector}
                onRefresh={refetchSectorData}
              />
            </TabPanel>

            <TabPanel value={currentTab} index={1}>
              <CorrelationAnalysis
                correlationData={correlationData?.correlations} // Assuming this structure
                isLoading={correlationLoading}
                error={correlationError as any}
                sector={selectedSector}
                onRefresh={refetchCorrelationData}
              />
            </TabPanel>

            <TabPanel value={currentTab} index={2}>
              <Typography variant="h6" gutterBottom>Forecast Results & Scenarios</Typography>
              {/* This area will display results of completed forecasts, potentially from activeJobDetails.result or by fetching */}
              {activeJobDetails?.status === 'completed' && activeJobDetails.result ? (
                <pre>{JSON.stringify(activeJobDetails.result, null, 2)}</pre>
              ) : (
                <Alert severity="info">Run a forecast to see results here. Previously saved scenarios will also be listed.</Alert>
              )}
            </TabPanel>

            <TabPanel value={currentTab} index={3}>
              <Typography variant="h6" gutterBottom>Model Performance Metrics</Typography>
              <Alert severity="info">
                Detailed model performance metrics (R², MAE, RMSE, etc.) will be available after forecasts are completed.
              </Alert>
            </TabPanel>
          </Paper>
        </Grid>

        <Dialog
          open={configDialogOpen}
          onClose={() => setConfigDialogOpen(false)}
          maxWidth="md"
          fullWidth
        >
          <DialogTitle>
            <Typography variant="h6">Configure New Demand Forecast</Typography>
            <Typography variant="body2" color="text.secondary">
              Set parameters, select models, and define variables for your forecast.
            </Typography>
          </DialogTitle>
          <DialogContent dividers>
            <ForecastConfiguration
              onSubmit={handleStartForecast}
              onCancel={() => setConfigDialogOpen(false)}
              isLoading={forecastStarting}
              initialConfig={{ scenario_name: `Forecast_${new Date().toISOString().split('T')[0]}`, target_year: new Date().getFullYear() + 10 }}
            />
          </DialogContent>
        </Dialog>
      </Grid>
    </Container>
  );
};
