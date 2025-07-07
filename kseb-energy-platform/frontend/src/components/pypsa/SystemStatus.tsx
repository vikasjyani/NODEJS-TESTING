import React, { useState, useEffect } from 'react';
import { Box, Typography, Paper, Grid, Chip, CircularProgress, Alert } from '@mui/material';
import { CheckCircleOutline, ErrorOutline, Dns, Memory, Storage, Speed } from '@mui/icons-material';
// import { useGetBackendStatusQuery } // If backend status is fetched via RTK Query

interface SystemStatusData {
  backendStatus: 'loading' | 'healthy' | 'unhealthy' | 'error';
  pythonEnvStatus: 'loading' | 'ok' | 'misconfigured' | 'error'; // Status of Python environment/dependencies
  solverStatus: Record<string, 'ok' | 'not_found' | 'error'>; // e.g., { highs: 'ok', gurobi: 'not_found' }
  // Add other relevant system metrics if available, e.g., disk space
}

export const SystemStatus: React.FC = () => {
  const [status, setStatus] = useState<SystemStatusData>({
    backendStatus: 'loading',
    pythonEnvStatus: 'loading',
    solverStatus: { highs: 'loading', gurobi: 'loading', cplex: 'loading' },
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
    currentStatus: 'loading' | 'healthy' | 'ok' | 'unhealthy' | 'misconfigured' | 'not_found' | 'error',
    icon?: React.ReactElement
  ) => {
    let color: 'default' | 'success' | 'warning' | 'error' | 'info' = 'default';
    let label = currentStatus;
    let displayIcon = icon || <Dns />;

    switch (currentStatus) {
      case 'loading':
        color = 'info';
        label = 'Checking...';
        displayIcon = <CircularProgress size={16} color="inherit"/>;
        break;
      case 'healthy':
      case 'ok':
        color = 'success';
        label = 'OK';
        displayIcon = icon || <CheckCircleOutline />;
        break;
      case 'unhealthy':
      case 'error':
        color = 'error';
        label = 'Error';
        displayIcon = icon || <ErrorOutline />;
        break;
      case 'misconfigured':
        color = 'warning';
        label = 'Misconfigured';
        displayIcon = icon || <ErrorOutline />;
        break;
      case 'not_found':
         color = 'default';
         label = 'Not Found';
         displayIcon = icon || <ErrorOutline sx={{color: 'text.disabled'}}/>;
        break;
    }

    return (
      <Chip
        avatar={displayIcon}
        label={`${componentName}: ${label.charAt(0).toUpperCase() + label.slice(1)}`}
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
