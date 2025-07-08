import React, { useState, useEffect } from 'react';
import { Box, Typography, Paper, CircularProgress, Alert, Tabs, Tab, Select, MenuItem, FormControl, InputLabel, SelectChangeEvent } from '@mui/material';
import { PlotlyChart, LineChart } from '../charts/PlotlyChart'; // Assuming PlotlyChart exists
// import { useGetSampleProfileDataQuery } // Example: if fetching sample data via RTK Query

interface ProfilePreviewProps {
  // Props to pass data or configuration for preview
  baseYearData?: { year: number; data: Array<{ datetime: string | Date; load: number }> }; // Example structure
  selectedMethodId?: string | null; // To tailor preview if needed
}

// Mock data for demonstration if no props are passed
const MOCK_HOURLY_LOAD_DATA = (year: number) => Array.from({ length: 24 * 7 }, (_, i) => { // 7 days
  const date = new Date(year, 0, Math.floor(i / 24) + 1, i % 24);
  return {
    datetime: date.toISOString(),
    load: 100 + 50 * Math.sin(i * Math.PI / 12) + 20 * Math.sin(i * Math.PI / (12*7)) + Math.random() * 10,
  };
});


export const ProfilePreview: React.FC<ProfilePreviewProps> = ({ baseYearData, selectedMethodId }) => {
  const [activeTab, setActiveTab] = useState(0);
  const [selectedYearForPreview, setSelectedYearForPreview] = useState<number>(new Date().getFullYear() -1);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Use provided data or mock data
  const currentPreviewData = baseYearData?.data || MOCK_HOURLY_LOAD_DATA(selectedYearForPreview);
  const currentYearLabel = baseYearData?.year || selectedYearForPreview;

  // Example: Fetch sample data if needed
  // const { data: sampleData, isLoading, error } = useGetSampleProfileDataQuery(selectedYearForPreview, {
  //   skip: !!baseYearData, // Skip if data is provided via props
  // });
  // useEffect(() => {
  //   if (sampleData) setPreviewData(sampleData);
  // }, [sampleData]);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const handleYearChange = (event: SelectChangeEvent<number>) => {
    setSelectedYearForPreview(event.target.value as number);
    // If fetching data: refetchSampleProfileData(event.target.value);
  };

  if (isLoading) {
    return <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}><CircularProgress /></Box>;
  }
  if (error) {
    return <Alert severity="error" sx={{m:2}}>Error loading preview data: {error}</Alert>;
  }
  if (!currentPreviewData || currentPreviewData.length === 0) {
    return <Alert severity="info" sx={{m:2}}>No data available for preview.</Alert>;
  }

  // Prepare data for charts
  const chartX = currentPreviewData.map(d => new Date(d.datetime));
  const chartY = currentPreviewData.map(d => d.load);

  const dailyAverage = Array.from({length: 24}, (_, hour) => {
    const hourlyLoads = currentPreviewData.filter(d => new Date(d.datetime).getHours() === hour).map(d => d.load);
    return hourlyLoads.length > 0 ? hourlyLoads.reduce((sum, val) => sum + val, 0) / hourlyLoads.length : 0;
  });

  return (
    <Box>
        {!baseYearData && ( // Show year selector only if data is not directly passed
             <FormControl sx={{ m: 1, minWidth: 120 }} size="small">
                <InputLabel id="preview-year-select-label">Preview Year</InputLabel>
                <Select
                    labelId="preview-year-select-label"
                    value={selectedYearForPreview}
                    label="Preview Year"
                    onChange={handleYearChange}
                >
                    {[2023, 2022, 2021, 2020, 2019].map(y => <MenuItem key={y} value={y}>{y}</MenuItem>)}
                </Select>
            </FormControl>
        )}
      <Tabs value={activeTab} onChange={handleTabChange} sx={{ mb: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Tab label="Hourly Profile (Sample)" />
        <Tab label="Typical Daily Shape" />
        {/* Add more tabs for different previews: e.g., Weekly, Monthly, Statistics */}
      </Tabs>

      {activeTab === 0 && (
        <Paper variant="outlined" sx={{ p: 2, height: 400 }}>
          <LineChart
            xData={chartX}
            yData={chartY}
            names={[`Load (Year ${currentYearLabel})`]}
            layout={{
                title: {text: `Sample Hourly Load Profile - Year ${currentYearLabel} (First Week)`},
                xaxis: { title: {text: 'Time'}, type: 'date' },
                yaxis: { title: {text: 'Load (MW)'} },
                height: 380,
            }}
          />
        </Paper>
      )}
      {activeTab === 1 && (
        <Paper variant="outlined" sx={{ p: 2, height: 400 }}>
          <LineChart
            xData={Array.from({length: 24}, (_, i) => i)}
            yData={dailyAverage}
            names={['Avg. Daily Load']}
            layout={{
                title: {text: `Typical Daily Load Shape - Year ${currentYearLabel}`},
                xaxis: { title: {text: 'Hour of Day'}, tickmode: 'array', tickvals: Array.from({length:24}, (_,i)=>i) },
                yaxis: { title: {text: 'Average Load (MW)'} },
                height: 380,
            }}
          />
        </Paper>
      )}
      {/* Add content for other tabs here */}
    </Box>
  );
};
