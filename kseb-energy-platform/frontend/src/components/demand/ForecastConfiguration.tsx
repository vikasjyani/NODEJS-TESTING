import React, { useState, useEffect } from 'react';
import {
  Box, Typography, TextField, Button, Grid, Paper,
  FormGroup, FormControlLabel, Checkbox, Autocomplete, Chip,
  Accordion, AccordionSummary, AccordionDetails, IconButton, Tooltip
} from '@mui/material';
import { ExpandMore, AddCircleOutline, RemoveCircleOutline, Info } from '@mui/icons-material';

// Define types for configuration (can be expanded)
interface SectorModelConfig {
  models: string[]; // e.g., ['MLR', 'SLR', 'TimeSeries']
  independent_variables?: string[]; // For MLR
  // Add other model-specific params here, e.g.,
  // timeSeriesParams?: { order: [p,d,q], seasonal_order: [P,D,Q,s] }
  // wamParams?: { window: number, growth_method: 'compound' | 'simple' }
}

export interface ForecastConfigData {
  scenario_name: string;
  target_year: number;
  input_file?: string; // Optional path to a specific input data file
  exclude_covid?: boolean;
  sectors: Record<string, SectorModelConfig>; // Key is sector name (e.g., 'residential')
  timeout?: number; // Optional timeout for the Python script in ms
}

interface ForecastConfigurationProps {
  onSubmit: (config: ForecastConfigData) => void;
  onCancel: () => void;
  isLoading: boolean;
  initialConfig?: Partial<ForecastConfigData>;
}

const ALL_AVAILABLE_MODELS = ['MLR', 'SLR', 'WAM', 'TimeSeries', 'ARIMA', 'Prophet']; // Example models
const ALL_AVAILABLE_SECTORS = ['residential', 'commercial', 'industrial', 'agriculture', 'transport', 'other']; // Example sectors
const COMMON_INDEPENDENT_VARS = ['gdp', 'population', 'temperature', 'price_index', 'gva_sector']; // Example common variables

export const ForecastConfiguration: React.FC<ForecastConfigurationProps> = ({
  onSubmit,
  onCancel,
  isLoading,
  initialConfig = {},
}) => {
  const [config, setConfig] = useState<ForecastConfigData>({
    scenario_name: initialConfig.scenario_name || `Forecast_${new Date().toISOString().slice(0,10)}`,
    target_year: initialConfig.target_year || new Date().getFullYear() + 10,
    exclude_covid: initialConfig.exclude_covid ?? true,
    sectors: initialConfig.sectors || {
        residential: { models: ['MLR', 'SLR'], independent_variables: ['gdp', 'population'] },
        commercial: { models: ['SLR'] }
    },
    timeout: initialConfig.timeout || 300000, // Default 5 mins
  });
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  const validateField = (name: keyof ForecastConfigData | string, value: any): string | null => {
    if (name === 'scenario_name' && (!value || String(value).trim() === '')) return 'Scenario name is required.';
    if (name === 'target_year' && (isNaN(Number(value)) || Number(value) <= new Date().getFullYear() || Number(value) > 2100 )) return 'Target year must be a valid future year.';
    if (name === 'timeout' && (isNaN(Number(value)) || Number(value) <=0 )) return 'Timeout must be a positive number.';
    // Add more specific validation for sectors object if needed here
    return null;
  };

  const handleChange = (field: keyof ForecastConfigData, value: any) => {
    setConfig(prev => ({ ...prev, [field]: value }));
    if (validationErrors[field]) {
      setValidationErrors(prev => ({...prev, [field]: ''}));
    }
  };

  const handleBlur = (event: React.FocusEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = event.target;
    const error = validateField(name as keyof ForecastConfigData, value);
    if (error) {
      setValidationErrors(prev => ({...prev, [name]: error}));
    }
  };

  const handleSectorChange = (sectorName: string, sectorConfig: Partial<SectorModelConfig>) => {
    setConfig(prev => ({
      ...prev,
      sectors: {
        ...prev.sectors,
        [sectorName]: { ...prev.sectors[sectorName], ...sectorConfig } as SectorModelConfig,
      },
    }));
  };

  const handleAddSector = () => {
    const newSectorName = `new_sector_${Object.keys(config.sectors).length + 1}`;
    // Find a sector not already in use
    let i = 1;
    let candidateName = `custom_sector_${i}`;
    while(config.sectors[candidateName]) {
        i++;
        candidateName = `custom_sector_${i}`;
    }
    handleSectorChange(candidateName, { models: ['SLR'] });
  };

  const handleRemoveSector = (sectorName: string) => {
    setConfig(prev => {
        const newSectors = {...prev.sectors};
        delete newSectors[sectorName];
        return {...prev, sectors: newSectors};
    });
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    // Perform final validation
    let isValid = true;
    const currentErrors: Record<string, string> = {};
    (Object.keys(config) as Array<keyof ForecastConfigData>).forEach(key => {
        const err = validateField(key, config[key]);
        if(err) {
            currentErrors[key] = err;
            isValid = false;
        }
    });
    if (Object.keys(config.sectors).length === 0) {
        currentErrors['sectors'] = 'At least one sector must be configured.';
        isValid = false;
    }

    setValidationErrors(currentErrors);

    if (isValid) {
      onSubmit(config);
    }
  };

  return (
    <Box component="form" onSubmit={handleSubmit} noValidate>
      <Grid container spacing={3}>
        {/* General Configuration */}
        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Scenario Name"
            name="scenario_name"
            value={config.scenario_name}
            onChange={(e) => handleChange('scenario_name', e.target.value)}
            onBlur={handleBlur}
            error={!!validationErrors.scenario_name}
            helperText={validationErrors.scenario_name || "A unique name for this forecast scenario."}
            required
            margin="normal"
          />
        </Grid>
        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            type="number"
            label="Target Year"
            name="target_year"
            value={config.target_year}
            onChange={(e) => handleChange('target_year', parseInt(e.target.value, 10))}
            onBlur={handleBlur}
            error={!!validationErrors.target_year}
            helperText={validationErrors.target_year || "The final year for the forecast projection."}
            required
            margin="normal"
          />
        </Grid>
        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Input Data File (Optional)"
            name="input_file"
            value={config.input_file || ''}
            onChange={(e) => handleChange('input_file', e.target.value)}
            helperText="Path to a custom input data file (e.g., Excel). If blank, defaults will be used."
            margin="normal"
          />
        </Grid>
         <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            type="number"
            label="Job Timeout (ms)"
            name="timeout"
            value={config.timeout}
            onChange={(e) => handleChange('timeout', parseInt(e.target.value, 10))}
            onBlur={handleBlur}
            error={!!validationErrors.timeout}
            helperText={validationErrors.timeout || "Max time for Python script (e.g., 300000 for 5 mins)."}
            margin="normal"
          />
        </Grid>
        <Grid item xs={12}>
          <FormGroup>
            <FormControlLabel
              control={
                <Checkbox
                  checked={config.exclude_covid ?? true}
                  onChange={(e) => handleChange('exclude_covid', e.target.checked)}
                  name="exclude_covid"
                />
              }
              label="Exclude COVID-19 Impact Years (e.g., 2020-2022) from historical data analysis"
            />
          </FormGroup>
        </Grid>

        {/* Sector Configurations */}
        <Grid item xs={12}>
          <Typography variant="h6" sx={{ mt: 2, mb: 1 }}>Sector Configurations</Typography>
          {Object.keys(config.sectors).map((sectorName) => (
            <Accordion key={sectorName} defaultExpanded={Object.keys(config.sectors).length < 3}>
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Typography sx={{textTransform: 'capitalize'}}>{sectorName}</Typography>
                <Tooltip title="Remove this sector configuration">
                    <IconButton size="small" onClick={(e) => { e.stopPropagation(); handleRemoveSector(sectorName);}} sx={{ml: 'auto'}}>
                        <RemoveCircleOutline color="error"/>
                    </IconButton>
                </Tooltip>
              </AccordionSummary>
              <AccordionDetails>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <Autocomplete
                      multiple
                      options={ALL_AVAILABLE_MODELS}
                      value={config.sectors[sectorName]?.models || []}
                      onChange={(event, newValue) => {
                        handleSectorChange(sectorName, { models: newValue });
                      }}
                      renderTags={(value, getTagProps) =>
                        value.map((option, index) => (
                          <Chip variant="outlined" label={option} {...getTagProps({ index })} />
                        ))
                      }
                      renderInput={(params) => (
                        <TextField
                          {...params}
                          variant="outlined"
                          label="Forecasting Models"
                          placeholder="Select models"
                          helperText="Choose one or more models for this sector."
                        />
                      )}
                    />
                  </Grid>
                  {config.sectors[sectorName]?.models.includes('MLR') && (
                    <Grid item xs={12} sm={6}>
                      <Autocomplete
                        multiple
                        options={COMMON_INDEPENDENT_VARS} // Can be dynamic based on available data
                        value={config.sectors[sectorName]?.independent_variables || []}
                        onChange={(event, newValue) => {
                          handleSectorChange(sectorName, { independent_variables: newValue });
                        }}
                        freeSolo // Allows adding custom variables not in the predefined list
                        renderTags={(value, getTagProps) =>
                          value.map((option, index) => (
                            <Chip variant="outlined" label={option} {...getTagProps({ index })} />
                          ))
                        }
                        renderInput={(params) => (
                          <TextField
                            {...params}
                            variant="outlined"
                            label="Independent Variables (for MLR)"
                            placeholder="Select or type variables"
                            helperText="Required if MLR model is selected."
                          />
                        )}
                      />
                    </Grid>
                  )}
                  {/* Add more model-specific configurations here */}
                </Grid>
              </AccordionDetails>
            </Accordion>
          ))}
          <Button startIcon={<AddCircleOutline />} onClick={handleAddSector} sx={{ mt: 1 }}>
            Add Sector Configuration
          </Button>
           {validationErrors.sectors && <Typography color="error" variant="caption" sx={{display: 'block', mt:1}}>{validationErrors.sectors}</Typography>}
        </Grid>
      </Grid>

      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 4, gap: 2 }}>
        <Button onClick={onCancel} color="inherit" disabled={isLoading}>
          Cancel
        </Button>
        <Button type="submit" variant="contained" color="primary" disabled={isLoading || Object.keys(validationErrors).some(k => !!validationErrors[k])}>
          {isLoading ? 'Starting Forecast...' : 'Run Forecast'}
        </Button>
      </Box>
    </Box>
  );
};
