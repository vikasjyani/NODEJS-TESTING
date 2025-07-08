import React, { useState, useEffect } from 'react';
import { Box, Typography, Paper, Grid, Chip, CircularProgress as MuiCircularProgress, Alert } from '@mui/material'; // Renamed CircularProgress
import { CheckCircleOutline, ErrorOutline, Dns, Memory, Storage, Speed, CloudQueue } from '@mui/icons-material'; // Added CloudQueue
// import { useGetBackendStatusQuery } // If backend status is fetched via RTK Query

type SolverStatusValue = 'loading' | 'ok' | 'not_found' | 'error'; // Define type for solver status values

interface SystemStatusData {
  backendStatus: 'loading' | 'healthy' | 'unhealthy' | 'error';
  pythonEnvStatus: 'loading' | 'ok' | 'misconfigured' | 'error';
  solverStatus: Record<string, SolverStatusValue>; // Use defined type
  // Add other relevant system metrics if available, e.g., disk space
}

type StatusLabel = 'loading' | 'healthy' | 'unhealthy' | 'ok' | 'misconfigured' | 'not_found' | 'error' | 'Checking...' | 'OK' | 'Error' | 'Misconfigured' | 'Not Found';


export const SystemStatus: React.FC = () => {
  const [status, setStatus] = useState<SystemStatusData>({
    backendStatus: 'loading',
    pythonEnvStatus: 'loading',
    solverStatus: { highs: 'loading', gurobi: 'loading', cplex: 'loading' }, // This is now valid
  });

  // In a real app, this data would come from an API call or Electron IPC
  useEffect(() => {
    const fetchStatus = async () => {
      // Simulate fetching status
      await new Promise(resolve => setTimeout(resolve, 1500));
      setStatus({
        backendStatus: Math.random() > 0.1 ? 'healthy' : 'unhealthy',
        pythonEnvStatus: Math.random() > 0.15 ? 'ok' : 'misconfigured',
        solverStatus: {
          highs: Math.random() > 0.05 ? 'ok' : 'error',
          gurobi: Math.random() > 0.5 ? 'ok' : 'not_found',
          cplex: 'not_found', // Assume CPLEX is less common
        },
      });
    };
    fetchStatus();
  }, []);

  const renderStatusChip = (
    componentName: string,
    currentStatus: SystemStatusData['backendStatus'] | SystemStatusData['pythonEnvStatus'] | SolverStatusValue, // Use combined types
    icon?: React.ReactElement
  ) => {
    let color: 'default' | 'success' | 'warning' | 'error' | 'info' = 'default';
    let labelText: StatusLabel = currentStatus as StatusLabel; // Cast to broader StatusLabel type initially
    let displayIcon = icon || <CloudQueue />; // Default to CloudQueue

    switch (currentStatus) {
      case 'loading':
        color = 'info';
        labelText = 'Checking...';
        displayIcon = <MuiCircularProgress size={16} color="inherit"/>; // Use aliased import
        break;
      case 'healthy':
      case 'ok':
        color = 'success';
        labelText = 'OK';
        displayIcon = icon || <CheckCircleOutline />;
        break;
      case 'unhealthy':
      case 'error':
        color = 'error';
        labelText = 'Error';
        displayIcon = icon || <ErrorOutline />;
        break;
      case 'misconfigured':
        color = 'warning';
        labelText = 'Misconfigured';
        displayIcon = icon || <ErrorOutline />;
        break;
      case 'not_found':
         color = 'default';
         labelText = 'Not Found';
         displayIcon = icon || <ErrorOutline sx={{color: 'text.disabled'}}/>;
        break;
      default: // Should not be reached if types are correct
        color = 'default';
        labelText = 'Unknown';
        break;
    }

    return (
      <Chip
        avatar={displayIcon}
        label={`${componentName}: ${labelText.charAt(0).toUpperCase() + labelText.slice(1)}`}
        color={color}
        variant="outlined"
        size="small"
      />
    );
  };

  return (
    <Paper sx={{ p: 2, borderRadius: 2 }}>
      <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 'medium' }}>
        System & Solver Status
      </Typography>
      <Grid container spacing={1}>
        <Grid item>{renderStatusChip('Backend API', status.backendStatus, <Dns />)}</Grid>
        <Grid item>{renderStatusChip('Python Environment', status.pythonEnvStatus, <Memory />)}</Grid>
        {Object.entries(status.solverStatus).map(([solverName, solverStat]) => (
          <Grid item key={solverName}>
            {renderStatusChip(`Solver: ${solverName.toUpperCase()}`, solverStat, <Speed />)}
          </Grid>
        ))}
      </Grid>
      {(status.backendStatus === 'unhealthy' || status.pythonEnvStatus === 'misconfigured' || Object.values(status.solverStatus).some(s => s === 'error' || s === 'not_found')) && (
        <Alert severity="warning" sx={{mt:1.5}}>
            One or more system components may not be functioning correctly. This could affect optimization capabilities. Please check logs or settings.
        </Alert>
      )}
    </Paper>
  );
};
