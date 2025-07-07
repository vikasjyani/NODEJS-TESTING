import React from 'react';
import { Box, Typography, Container, Paper, TextField, Button, Switch, FormControlLabel } from '@mui/material';

export const Settings: React.FC = () => {
  return (
    <Container maxWidth="lg">
      <Typography variant="h4" gutterBottom sx={{ mb: 3 }}>
        Application Settings
      </Typography>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>User Preferences</Typography>
        <Box component="form" noValidate autoComplete="off">
          <TextField
            fullWidth
            label="Default Project Path"
            variant="outlined"
            margin="normal"
            helperText="Path where new projects are created by default."
          />
          <FormControlLabel
            control={<Switch defaultChecked />}
            label="Enable Dark Mode by Default"
            sx={{mt:1}}
          />
        </Box>
      </Paper>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>Python Configuration</Typography>
        <Box component="form" noValidate autoComplete="off">
          <TextField
            fullWidth
            label="Python Interpreter Path"
            variant="outlined"
            margin="normal"
            helperText="Overrides the auto-detected Python path (e.g., /usr/bin/python3 or C:\\Python39\\python.exe)."
          />
           <TextField
            fullWidth
            type="number"
            label="Max Concurrent Python Processes"
            variant="outlined"
            margin="normal"
            defaultValue={3}
            inputProps={{ min: 1, max: 10 }}
            helperText="Number of Python scripts that can run simultaneously."
          />
        </Box>
      </Paper>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>API & Cache Settings</Typography>
         <Box component="form" noValidate autoComplete="off">
            <TextField
                fullWidth
                label="Backend API URL"
                variant="outlined"
                margin="normal"
                defaultValue="http://localhost:5000/api"
            />
            <TextField
                fullWidth
                type="number"
                label="Default Cache TTL (seconds)"
                variant="outlined"
                margin="normal"
                defaultValue={300}
                inputProps={{ min: 60 }}
                helperText="Default time-to-live for cached items."
            />
            <Button variant="outlined" sx={{mt:1}}>Clear Application Cache</Button>
        </Box>
      </Paper>

      <Box sx={{ mt: 4, display: 'flex', justifyContent: 'flex-end' }}>
        <Button variant="contained" color="primary">
          Save Settings
        </Button>
      </Box>
    </Container>
  );
};
