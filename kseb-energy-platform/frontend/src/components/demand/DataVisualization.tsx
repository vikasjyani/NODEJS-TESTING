import React from 'react';
import { Box, Typography, Paper, Grid, CircularProgress, Alert, Button } from '@mui/material';
import { PlotlyChart, LineChart, BarChart } from '../charts/PlotlyChart'; // Assuming PlotlyChart is created in Chunk 5.1
import { DataTable } from '../common/DataTable'; // Assuming DataTable is created in Chunk 5.2

// Define expected structure for sector data, stats, and quality (align with backend response)
interface SectorStats {
  years_available?: number;
  data_points?: number;
  columns?: string[];
  date_range?: { start?: number; end?: number };
  // Add other relevant stats
}

interface SectorDataQuality {
  score: number; // 0-1
  completeness?: number;
  consistency?: number;
  temporal_coverage?: number;
  issues?: string[];
}

interface DataVisualizationProps {
  sectorData: any[] | undefined; // Example: Array of { year: number, demand: number, gdp?: number, population?: number }
  stats: SectorStats | undefined;
  quality: SectorDataQuality | undefined;
  isLoading: boolean;
  error: { data?: { message?: string }; error?: string; status?: number } | null | undefined;
  sector: string;
  onRefresh?: () => void;
}

export const DataVisualization: React.FC<DataVisualizationProps> = ({
  sectorData,
  stats,
  quality,
  isLoading,
  error,
  sector,
  onRefresh,
}) => {
  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 300 }}>
        <CircularProgress />
        <Typography sx={{ ml: 2 }}>Loading historical data for {sector} sector...</Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" action={onRefresh && <Button onClick={onRefresh}>Retry</Button>}>
        <Typography variant="h6">Error Loading Data</Typography>
        <Typography>
          Failed to load historical data for {sector} sector.
          {error.data?.message || error.error || `Status: ${error.status || 'Unknown'}`}
        </Typography>
      </Alert>
    );
  }

  if (!sectorData || sectorData.length === 0) {
    return <Alert severity="info">No historical data available for the {sector} sector.</Alert>;
  }

  // Prepare data for charts and table
  const chartData = sectorData.map(d => ({ ...d, year_date: new Date(d.year, 0, 1) })).sort((a,b) => a.year - b.year);
  const demandValues = chartData.map(d => d.demand);
  const years = chartData.map(d => d.year);
  const gdpValues = chartData.map(d => d.gdp).filter(v => v !== undefined && v !== null);
  const populationValues = chartData.map(d => d.population).filter(v => v !== undefined && v !== null);

  const columnsForTable = [
    { id: 'year', label: 'Year', minWidth: 80, sortable: true },
    { id: 'demand', label: 'Demand (GWh)', minWidth: 100, sortable: true, format: (value: number) => value?.toLocaleString() },
    ...(chartData[0]?.gdp !== undefined ? [{ id: 'gdp', label: 'GDP (Indicator)', minWidth: 100, sortable: true, format: (value: number) => value?.toLocaleString() }] : []),
    ...(chartData[0]?.population !== undefined ? [{ id: 'population', label: 'Population (Indicator)', minWidth: 120, sortable: true, format: (value: number) => value?.toLocaleString() }] : []),
  ];

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Historical Data for {sector.charAt(0).toUpperCase() + sector.slice(1)} Sector
      </Typography>

      {/* Data Quality Summary (if available) */}
      {quality && (
        <Paper sx={{p:2, mb:2, backgroundColor: quality.score < 0.6 ? 'error.light' : quality.score < 0.8 ? 'warning.light' : 'success.light'}}>
            <Typography variant="subtitle1">Data Quality Score: {(quality.score * 100).toFixed(1)}%</Typography>
            {quality.issues && quality.issues.length > 0 && (
                <Box>
                    <Typography variant="body2">Issues:</Typography>
                    <ul>{quality.issues.map((issue, i) => <li key={i}><Typography variant="caption">{issue}</Typography></li>)}</ul>
                </Box>
            )}
        </Paper>
      )}


      <Grid container spacing={3}>
        <Grid item xs={12} md={stats?.columns && stats.columns.length > 3 ? 7 : 12}>
          <Paper sx={{ p: 2, height: 400 }}>
            <LineChart
              data={[{
                x: years,
                y: demandValues,
                type: 'scatter',
                mode: 'lines+markers',
                name: 'Demand (GWh)',
                marker: { color: 'primary.main' }
              }]}
              layout={{ title: {text: `Annual Demand Trend - ${sector}`} , xaxis: {title: {text: 'Year'}}, yaxis: {title: {text: 'Demand (GWh)'}}}}
              loading={isLoading}
            />
          </Paper>
        </Grid>

        {stats?.columns && stats.columns.length > 3 && (gdpValues.length > 0 || populationValues.length > 0) && (
          <Grid item xs={12} md={5}>
            {gdpValues.length > 0 && (
              <Paper sx={{ p: 2, height: populationValues.length > 0 ? 190: 400, mb: populationValues.length > 0 ? 2 : 0 }}>
                <BarChart
                  data={[{ x: years, y: gdpValues, type: 'bar', name: 'GDP Indicator', marker: {color: 'secondary.main'} }]}
                  layout={{ title: {text: 'GDP Trend'}, height: populationValues.length > 0 ? 170: 380, yaxis: {title: {text: 'GDP (Indicator)'}} }}
                  loading={isLoading}
                />
              </Paper>
            )}
            {populationValues.length > 0 && (
              <Paper sx={{ p: 2, height: gdpValues.length > 0 ? 190: 400 }}>
                <BarChart
                  data={[{ x: years, y: populationValues, type: 'bar', name: 'Population Indicator', marker: {color: 'success.main'} }]}
                  layout={{ title: {text: 'Population Trend'}, height: gdpValues.length > 0 ? 170: 380, yaxis: {title: {text: 'Population (Indicator)'}} }}
                  loading={isLoading}
                />
              </Paper>
            )}
          </Grid>
        )}

        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Raw Data Table</Typography>
            <DataTable
              columns={columnsForTable}
              data={chartData}
              loading={isLoading}
              pagination
              rowsPerPageOptions={[5, 10, Math.min(25, chartData.length)]} // Ensure options are not > data length
              defaultRowsPerPage={Math.min(10, chartData.length)}
              maxHeight={400}
              searchable
            />
          </Paper>
        </Grid>

        {stats && (
            <Grid item xs={12}>
                <Paper sx={{p:2}}>
                    <Typography variant="h6">Data Statistics</Typography>
                    <Grid container spacing={1}>
                        <Grid item xs={6} sm={3}><Typography>Years Available: {stats.years_available ?? 'N/A'}</Typography></Grid>
                        <Grid item xs={6} sm={3}><Typography>Data Points: {stats.data_points ?? 'N/A'}</Typography></Grid>
                        <Grid item xs={6} sm={3}><Typography>Start Year: {stats.date_range?.start ?? 'N/A'}</Typography></Grid>
                        <Grid item xs={6} sm={3}><Typography>End Year: {stats.date_range?.end ?? 'N/A'}</Typography></Grid>
                        <Grid item xs={12}><Typography>Columns: {stats.columns?.join(', ') ?? 'N/A'}</Typography></Grid>
                    </Grid>
                </Paper>
            </Grid>
        )}

      </Grid>
    </Box>
  );
};
