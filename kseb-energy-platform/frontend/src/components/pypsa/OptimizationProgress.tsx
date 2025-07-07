import React from 'react';
import { Box, Typography, Paper, LinearProgress, Button, IconButton, Chip, Grid, Tooltip } from '@mui/material';
import { PlayArrow, Pause, StopCircle, InfoOutlined, ErrorOutline, CheckCircleOutline, HourglassEmpty, SettingsBackupRestore } from '@mui/icons-material';

// Matches the structure of the job object from pypsaSlice
interface OptimizationJob {
  id: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number; // 0-100
  currentStep?: string; // e.g., "Network Loading", "Solving LP"
  statusDetails?: string; // More detailed message from Python
  config?: { scenario_name?: string; solver_options?: { solver?: string } }; // To display info
  error?: string;
  startTime?: string;
  completedTime?: string;
  failedTime?: string;
  result?: { objective_value?: number }; // Key results
}

interface OptimizationProgressProps {
  job: OptimizationJob | null | undefined;
  title?: string; // Optional title for the monitor
  onCancel?: (jobId: string) => void; // Callback to handle cancellation
  onRetry?: (jobId: string) => void; // Callback to handle retry for failed jobs
}

export const OptimizationProgress: React.FC<OptimizationProgressProps> = ({
  job,
  title,
  onCancel,
  onRetry,
}) => {
  if (!job) {
    return null;
  }

  const getStatusColor = (): "default" | "primary" | "secondary" | "error" | "info" | "success" | "warning" => {
    switch (job.status) {
      case 'completed': return 'success';
      case 'failed': return 'error';
      case 'cancelled': return 'warning';
      case 'running': return 'primary';
      case 'queued': return 'info';
      default: return 'default';
    }
  };

  const getStatusIcon = () => {
    switch (job.status) {
      case 'completed': return <CheckCircleOutline />;
      case 'failed': return <ErrorOutline />;
      case 'cancelled': return <StopCircle />;
      case 'running': return <CircularProgressWithLabel value={job.progress} size={20} />;
      case 'queued': return <HourglassEmpty />;
      default: return <InfoOutlined />;
    }
  };

  const scenarioName = job.config?.scenario_name || job.id;
  const displayTitle = title || `Job: ${scenarioName}`;

  return (
    <Paper elevation={2} sx={{ p: 2, mb: 2, borderRadius: 2, borderLeft: 5, borderColor: `${getStatusColor()}.main` }}>
      <Grid container spacing={2} alignItems="center">
        <Grid item xs={12} sm={4} md={3}>
          <Typography variant="subtitle1" component="div" noWrap sx={{fontWeight: 'medium'}}>
            {displayTitle}
          </Typography>
           <Typography variant="caption" color="text.secondary" display="block">
            Solver: {job.config?.solver_options?.solver || 'N/A'}
          </Typography>
          <Chip
            icon={getStatusIcon()}
            label={job.status.charAt(0).toUpperCase() + job.status.slice(1)}
            color={getStatusColor()}
            size="small"
            sx={{mt: 0.5}}
          />
        </Grid>

        <Grid item xs={12} sm={8} md={6}>
          <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
            <Box sx={{ width: '100%', mr: 1 }}>
              <LinearProgress variant="determinate" value={job.progress} color={getStatusColor()} sx={{height: 8, borderRadius: 1}}/>
            </Box>
            <Box sx={{ minWidth: 35 }}>
              <Typography variant="body2" color="text.secondary">{`${Math.round(job.progress)}%`}</Typography>
            </Box>
          </Box>
          {job.status === 'running' && job.currentStep && (
             <Tooltip title={job.statusDetails || job.currentStep}>
                <Typography variant="caption" color="text.secondary" noWrap display="block" sx={{mt:0.5}}>
                    Current Step: {job.currentStep.length > 50 ? job.currentStep.substring(0,47) + '...' : job.currentStep}
                </Typography>
             </Tooltip>
          )}
          {job.status === 'failed' && job.error && (
             <Tooltip title={job.error}>
                <Typography variant="caption" color="error" noWrap display="block" sx={{mt:0.5}}>
                    Error: {job.error.length > 70 ? job.error.substring(0,67) + '...' : job.error}
                </Typography>
             </Tooltip>
          )}
           {job.status === 'completed' && (
             <Typography variant="caption" color="success.main" display="block" sx={{mt:0.5}}>
                Optimization completed. Objective: {job.result?.objective_value?.toLocaleString() || 'N/A'}
            </Typography>
           )}
        </Grid>

        <Grid item xs={12} md={3} sx={{ display: 'flex', justifyContent: {xs: 'flex-start', md: 'flex-end'}, gap: 1, mt: {xs:1, md:0} }}>
          {onCancel && (job.status === 'running' || job.status === 'queued') && (
            <Button
                size="small"
                variant="outlined"
                color="error"
                startIcon={<StopCircle />}
                onClick={() => onCancel(job.id)}
            >
              Cancel Job
            </Button>
          )}
          {onRetry && job.status === 'failed' && (
             <Button
                size="small"
                variant="outlined"
                color="warning"
                startIcon={<SettingsBackupRestore />}
                onClick={() => onRetry(job.id)}
            >
              Retry Job
            </Button>
          )}
        </Grid>
      </Grid>
    </Paper>
  );
};

// Helper for CircularProgress with label
function CircularProgressWithLabel(props: { value: number, size?: number }) {
  return (
    <Box sx={{ position: 'relative', display: 'inline-flex', alignItems:'center', justifyContent:'center' }}>
      <CircularProgress variant="determinate" {...props} />
    </Box>
  );
}
