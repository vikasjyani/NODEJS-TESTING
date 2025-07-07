import React from 'react';
import { Box, Typography, Paper, Grid, CircularProgress, Alert, Button } from '@mui/material';
import { PlotlyChart, HeatmapChart } from '../charts/PlotlyChart'; // Assuming PlotlyChart is created
import { DataTable } from '../common/DataTable'; // Assuming DataTable is created

interface CorrelationItem {
  variable: string;
  correlation: number; // Raw correlation value
  abs_correlation: number; // Absolute correlation value
  strength?: 'strong' | 'moderate' | 'weak' | string;
  recommendation?: 'recommended' | 'not_recommended' | string;
}

interface CorrelationData {
  sector?: string;
  correlations: CorrelationItem[];
  recommended_variables?: string[];
  // Potentially add a full correlation matrix if backend provides it
  // correlation_matrix?: { variables: string[], matrix: number[][] };
}

interface CorrelationAnalysisProps {
  correlationData: CorrelationItem[] | undefined; // This is the array of correlations from backend
  isLoading: boolean;
  error: { data?: { message?: string }; error?: string; status?: number } | null | undefined;
  sector: string;
  onRefresh?: () => void;
}

export const CorrelationAnalysis: React.FC<CorrelationAnalysisProps> = ({
  correlationData,
  isLoading,
  error,
  sector,
  onRefresh,
}) => {
  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 300 }}>
        <CircularProgress />
        <Typography sx={{ ml: 2 }}>Loading correlation data for {sector} sector...</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" action={onRefresh && <Button onClick={onRefresh}>Retry</Button>}>
        <Typography variant="h6">Error Loading Correlation Data</Typography>
        <Typography>
          Failed to load correlation data for {sector} sector.
          {error.data?.message || error.error || `Status: ${error.status || 'Unknown'}`}
        </Typography>
      </Alert>
    );
  }

  if (!correlationData || correlationData.length === 0) {
    return <Alert severity="info">No correlation data available for the {sector} sector.</Alert>;
  }

  // Prepare data for Heatmap (if a full matrix was available from backend)
  // For now, we only have correlations with 'demand'. A full matrix would be like:
  // const heatmapZData = correlationData.correlation_matrix?.matrix;
  // const heatmapXLabels = correlationData.correlation_matrix?.variables;
  // const heatmapYLabels = correlationData.correlation_matrix?.variables;

  // For displaying the provided list of correlations in a table:
  const tableColumns = [
    { id: 'variable', label: 'Variable', minWidth: 150, sortable: true },
    {
      id: 'correlation',
      label: 'Correlation with Demand',
      minWidth: 180,
      sortable: true,
      format: (value: number) => value?.toFixed(3)
    },
    {
      id: 'abs_correlation',
      label: 'Absolute Correlation',
      minWidth: 170,
      sortable: true,
      format: (value: number) => value?.toFixed(3)
    },
    { id: 'strength', label: 'Strength', minWidth: 100, sortable: true },
    { id: 'recommendation', label: 'Recommended for MLR', minWidth: 200, sortable: true },
  ];

  // Prepare data for a simple bar chart of correlations
  const sortedCorrelations = [...correlationData].sort((a, b) => b.abs_correlation - a.abs_correlation);
  const barChartX = sortedCorrelations.map(c => c.variable);
  const barChartY = sortedCorrelations.map(c => c.correlation);
  const barChartColors = barChartY.map(val => val >= 0 ? 'rgba(25, 118, 210, 0.7)' : 'rgba(211, 47, 47, 0.7)');


  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Correlation Analysis for {sector.charAt(0).toUpperCase() + sector.slice(1)} Sector (with Demand)
      </Typography>
      <Grid container spacing={3}>
        <Grid item xs={12} md={7}>
           <Paper sx={{ p: 2, height: 450 }}>
            <PlotlyChart
              data={[{
                x: barChartX,
                y: barChartY,
                type: 'bar',
                name: 'Correlation',
                marker: { color: barChartColors }
              }]}
              layout={{
                title: `Variable Correlation with Demand`,
                yaxis: { title: 'Correlation Coefficient', range: [-1, 1] },
                xaxis: { title: 'Variable', tickangle: -45 },
                height: 430,
                margin: {b: 100}
              }}
              loading={isLoading}
            />
          </Paper>
        </Grid>
        <Grid item xs={12} md={5}>
            <Paper sx={{p:2, height: 450, display:'flex', flexDirection:'column'}}>
                 <Typography variant="h6" gutterBottom>Key Insights</Typography>
                 <Typography variant="body2" paragraph>
                    This analysis shows the linear relationship between various economic/demographic indicators and energy demand in the {sector} sector.
                 </Typography>
                 <Typography variant="body2" paragraph>
                    Variables with higher absolute correlation values (closer to 1 or -1) are generally considered more influential for demand forecasting models like Multiple Linear Regression (MLR).
                 </Typography>
                 {correlationData.find(c => c.recommendation === 'recommended') &&
                    <Typography variant="body2">
                        <strong>Recommended variables for MLR:</strong> {correlationData.filter(c=>c.recommendation === 'recommended').map(c=>c.variable).join(', ') || 'None with strong correlation.'}
                    </Typography>
                 }
                 <Alert severity="info" sx={{mt: 'auto'}}>
                    Note: Correlation does not imply causation. These values indicate statistical relationships.
                 </Alert>
            </Paper>
        </Grid>

        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Correlation Details</Typography>
            <DataTable
              columns={tableColumns}
              data={correlationData}
              loading={isLoading}
              pagination
              defaultRowsPerPage={Math.min(10, correlationData.length || 10)}
              maxHeight={400}
            />
          </Paper>
        </Grid>

        {/* Placeholder for Heatmap if full matrix becomes available */}
        {/* {heatmapZData && heatmapXLabels && heatmapYLabels && (
          <Grid item xs={12}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>Full Correlation Matrix</Typography>
              <HeatmapChart
                zData={heatmapZData}
                xLabels={heatmapXLabels}
                yLabels={heatmapYLabels}
                colorscale="RdBu" // Red-Blue scale for correlations
                layout={{ title: `Full Correlation Matrix - ${sector}` }}
                loading={isLoading}
              />
            </Paper>
          </Grid>
        )} */}
      </Grid>
    </Box>
  );
};
