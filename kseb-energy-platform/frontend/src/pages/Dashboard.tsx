import React from 'react';
import { Box, Typography, Paper, Grid, Container } from '@mui/material';
import { BarChart, LineChart, PieChart } from '@mui/icons-material'; // Example icons

const Dashboard: React.FC = () => {
  return (
    <Container maxWidth="xl">
      <Typography variant="h4" gutterBottom sx={{ mb: 3 }}>
        Energy Platform Dashboard
      </Typography>
      <Grid container spacing={3}>
        {/* Example Stat Card 1 */}
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%' }}>
            <BarChart color="primary" sx={{ fontSize: 40, mb: 1 }} />
            <Typography variant="h6">Active Projects</Typography>
            <Typography variant="h3" component="p">5</Typography>
            <Typography color="text.secondary">View Details</Typography>
          </Paper>
        </Grid>
        {/* Example Stat Card 2 */}
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%' }}>
            <LineChart color="secondary" sx={{ fontSize: 40, mb: 1 }} />
            <Typography variant="h6">Forecasts Ran</Typography>
            <Typography variant="h3" component="p">27</Typography>
            <Typography color="text.secondary">Last 30 days</Typography>
          </Paper>
        </Grid>
        {/* Example Stat Card 3 */}
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%' }}>
            <PieChart sx={{ fontSize: 40, mb: 1, color: 'success.main' }} />
            <Typography variant="h6">Models Optimized</Typography>
            <Typography variant="h3" component="p">12</Typography>
            <Typography color="text.secondary">PyPSA Scenarios</Typography>
          </Paper>
        </Grid>
        {/* Example Stat Card 4 */}
        <Grid item xs={12} sm={6} md={3}>
          <Paper sx={{ p: 2, display: 'flex', flexDirection: 'column', alignItems: 'center', height: '100%' }}>
            <Typography variant="h6">System Status</Typography>
            <Typography variant="h4" component="p" sx={{color: 'success.main', mt:1}}>Healthy</Typography>
            <Typography color="text.secondary" sx={{mt:2}}>Backend & Python Services OK</Typography>
          </Paper>
        </Grid>

        {/* Example Chart Placeholder 1 */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 2, height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Typography variant="h6" color="text.secondary">Overall Demand Trend (Chart)</Typography>
          </Paper>
        </Grid>
        {/* Example Chart Placeholder 2 */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Typography variant="h6" color="text.secondary">Task Completion (Chart)</Typography>
          </Paper>
        </Grid>

        {/* Example Recent Activity Placeholder */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Recent Activity</Typography>
            <Box>
              <Typography variant="body2" sx={{mb:1}}>- User ' planner1' started new demand forecast 'High Growth 2040'.</Typography>
              <Typography variant="body2" sx={{mb:1}}>- PyPSA optimization 'Kerala_Solar_Max' completed successfully.</Typography>
              <Typography variant="body2">- Load profile 'Industrial_Expansion_2035' generated.</Typography>
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
};

export { Dashboard }; // Exporting named export for consistency with App.tsx
// export default Dashboard; // Default export would also work
