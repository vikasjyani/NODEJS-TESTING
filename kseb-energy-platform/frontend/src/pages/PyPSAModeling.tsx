import React, { useState, useEffect, useCallback } from 'react';
import { useSelector } from 'react-redux';
import {
  Container, Grid, Paper, Typography, Button, Box,
  Accordion, AccordionSummary, AccordionDetails, TextField,
  FormControl, FormLabel, RadioGroup, FormControlLabel, Radio,
  Checkbox, FormGroup, Select, MenuItem, InputLabel, SelectChangeEvent,
  Alert, Chip, CircularProgress, Tooltip, IconButton
} from '@mui/material';
import {
  ExpandMore, PlayArrow, StopCircle, CloudUpload, Settings,
  Assessment, Info, Warning, CheckCircle, HelpOutline, FolderOpen
} from '@mui/icons-material';

import { RootState, useAppDispatch } from '../../store';
import {
  useRunOptimizationMutation,
  // useGetOptimizationStatusQuery, // Can be used for polling if WebSocket is not primary
  useUploadFileMutation // Assuming a generic file upload for PyPSA input template
} from '../../store/api/apiSlice';
import { usePyPSANotifications } from '../../services/websocket'; // Changed from usePyPSAProgress
import { OptimizationProgress } from '../../components/pypsa/OptimizationProgress'; // Will be created
import { SystemStatus } from '../../components/pypsa/SystemStatus'; // Will be created
import { ExcelSettingsLoader } from '../../components/pypsa/ExcelSettingsLoader'; // Will be created
import { addNotification } from '../../store/slices/notificationSlice';

// Mirrored from backend/src/controllers/pypsaController.js and Python script expectations
export interface PyPSAModelConfiguration {
  scenario_name: string;
  input_file?: string; // Path to the main PyPSA Excel template or NetCDF file
  base_year: number;
  investment_mode: 'single_year' | 'multi_year' | 'all_in_one';
  snapshot_selection?: 'all' | 'critical_days'; // Default to 'all' if not specified

  // Advanced options - align with Python script's config expectations
  generator_clustering?: boolean;
  unit_commitment?: boolean;
  monthly_constraints?: boolean;
  battery_constraints?: 'none' | 'daily' | 'weekly' | 'monthly';

  // Solver options
  solver_options?: {
    solver?: 'highs' | 'gurobi' | 'cplex' | 'glpk' | 'cbc' | 'scip'; // Common solvers
    optimality_gap?: number; // e.g., 0.01 for 1%
    time_limit?: number; // in seconds
  };
  timeout?: number; // Python script execution timeout in ms
}

const defaultSolverOptions = {
    solver: 'highs' as PyPSAModelConfiguration['solver_options']['solver'],
    optimality_gap: 0.01,
    time_limit: 3600 // 1 hour
};

export const PyPSAModeling: React.FC = () => {
  const dispatch = useAppDispatch();
  const [config, setConfig] = useState<PyPSAModelConfiguration>({
    scenario_name: `PyPSA_Scenario_${new Date().toISOString().slice(0,10)}`,
    base_year: new Date().getFullYear(),
    investment_mode: 'single_year',
    snapshot_selection: 'all',
    generator_clustering: false,
    unit_commitment: false,
    monthly_constraints: false,
    battery_constraints: 'none',
    solver_options: { ...defaultSolverOptions },
    timeout: 1800000, // 30 mins default for script execution
  });

  const [currentOptimizationJobId, setCurrentOptimizationJobId] = useState<string | null>(null);
  const [inputFileUploaded, setInputFileUploaded] = useState<File | null>(null);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  // API hooks
  const [runOptimization, { isLoading: startingOptimization, error: optimizationStartError }] = useRunOptimizationMutation();
  const [uploadFile, {isLoading: uploadingInputFile, error: uploadError}] = useUploadFileMutation();

  // WebSocket progress tracking
  usePyPSANotifications(currentOptimizationJobId);

  // Redux state for all optimization jobs
  const optimizationJobs = useSelector((state: RootState) => state.pypsa.optimizationJobs);
  const activeJobDetails = currentOptimizationJobId ? optimizationJobs[currentOptimizationJobId] : null;

  useEffect(() => {
    if (optimizationStartError) {
      dispatch(addNotification({type: 'error', message: `Failed to start PyPSA optimization: ${ (optimizationStartError as any)?.data?.message || (optimizationStartError as any)?.error || 'Unknown error'}`}));
    }
    if (uploadError) {
        dispatch(addNotification({type: 'error', message: `Input file upload failed: ${ (uploadError as any)?.data?.message || (uploadError as any)?.error || 'Unknown error'}`}));
    }
  }, [optimizationStartError, uploadError, dispatch]);


  const handleConfigChange = (field: keyof PyPSAModelConfiguration | `solver_options.${keyof NonNullable<PyPSAModelConfiguration['solver_options'] >}`, value: any) => {
    if (field.startsWith('solver_options.')) {
        const subField = field.split('.')[1] as keyof NonNullable<PyPSAModelConfiguration['solver_options']>;
        setConfig(prev => ({
            ...prev,
            solver_options: {
                ...(prev.solver_options || defaultSolverOptions),
                [subField]: value,
            }
        }));
    } else {
        setConfig(prev => ({ ...prev, [field as keyof PyPSAModelConfiguration]: value }));
    }
    // Clear validation error for the field being changed
    if (validationErrors[field]) {
      setValidationErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  const validateConfiguration = useCallback((): boolean => {
    const errors: Record<string, string> = {};
    if (!config.scenario_name.trim()) errors.scenario_name = 'Scenario name is required.';
    if (config.base_year < 2000 || config.base_year > 2070) errors.base_year = 'Base year must be realistic (e.g., 2000-2070).';
    if (config.solver_options?.optimality_gap && (config.solver_options.optimality_gap < 0 || config.solver_options.optimality_gap > 1)) errors['solver_options.optimality_gap'] = 'Optimality gap must be between 0 and 1.';
    if (config.solver_options?.time_limit && config.solver_options.time_limit < 60) errors['solver_options.time_limit'] = 'Solver time limit must be at least 60 seconds.';
    if (!inputFileUploaded && !config.input_file) errors.input_file = 'PyPSA input template/file must be provided or selected.';
    // Add more specific validations as required by pypsa_runner.py or PyPSA itself
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  }, [config, inputFileUploaded]);


  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
        setInputFileUploaded(file);
        setConfig(prev => ({ ...prev, input_file: file.name })); // Store filename in config
        setValidationErrors(prev => ({...prev, input_file: ''})); // Clear file error
        dispatch(addNotification({type: 'success', message: `File "${file.name}" selected.`}));
        // Optionally, immediately upload if that's the workflow
        // For instance, if backend needs the file before starting optimization:
        // try {
        //   await uploadFile({ file, fileType: 'pypsa_input_template' }).unwrap();
        //   dispatch(addNotification({type: 'success', message: `File "${file.name}" uploaded successfully.`}));
        //   setConfig(prev => ({ ...prev, input_file: `uploads/${file.name}` })); // Backend might return a path
        // } catch (err) { /* error handled by useEffect */ }
    }
  };

  const handleStartOptimization = async () => {
    if (!validateConfiguration()) {
      dispatch(addNotification({type: 'warning', message: 'Please fix configuration errors before starting.'}));
      return;
    }

    let finalConfig = { ...config };

    // If a file was selected locally and needs to be uploaded first
    if (inputFileUploaded && !config.input_file?.startsWith('uploads/')) { // Assuming 'uploads/' prefix means already uploaded
        try {
            dispatch(addNotification({type: 'info', message: `Uploading input file: ${inputFileUploaded.name}...`}));
            const uploadResult = await uploadFile({ file: inputFileUploaded, fileType: 'pypsa_input_template' }).unwrap();
            if (uploadResult.success && uploadResult.filePath) {
                 finalConfig.input_file = uploadResult.filePath; // Use the server-side path
                 dispatch(addNotification({type: 'success', message: `File ${inputFileUploaded.name} uploaded to ${uploadResult.filePath}.`}));
            } else {
                throw new Error(uploadResult.message || "File upload failed before optimization.");
            }
        } catch (err: any) {
            dispatch(addNotification({type: 'error', message: `Critical: Input file upload failed: ${err.message}`}));
            return; // Stop if essential file upload fails
        }
    }


    try {
      const response = await runOptimization(finalConfig).unwrap();
      if (response.success && response.jobId) {
        setCurrentOptimizationJobId(response.jobId);
        dispatch(addNotification({type: 'info', message: `PyPSA optimization job '${response.jobId}' started.`}));
      } else {
         dispatch(addNotification({type: 'error', message: response.message || 'Failed to initiate PyPSA optimization.'}));
      }
    } catch (err) {
      // Error handled by useEffect for optimizationStartError
      console.error('Failed to start PyPSA optimization:', err);
    }
  };

  const handleCancelOptimization = () => {
     if (activeJobDetails && (activeJobDetails.status === 'running' || activeJobDetails.status === 'queued')) {
        // TODO: API call to cancel
        dispatch(addNotification({type: 'info', message: `Requesting cancellation for job ${activeJobDetails.id}.`}));
    }
  };

  const loadExcelSettings = (settings: Partial<PyPSAModelConfiguration>) => {
    // Merges settings from Excel, preferring Excel values for common fields
    setConfig(prev => ({
      ...prev, // Keep existing values not in Excel
      scenario_name: settings.scenario_name || prev.scenario_name,
      base_year: settings.base_year || prev.base_year,
      investment_mode: settings.investment_mode || prev.investment_mode,
      snapshot_selection: settings.snapshot_selection || prev.snapshot_selection,
      generator_clustering: settings.generator_clustering ?? prev.generator_clustering,
      unit_commitment: settings.unit_commitment ?? prev.unit_commitment,
      monthly_constraints: settings.monthly_constraints ?? prev.monthly_constraints,
      battery_constraints: settings.battery_constraints || prev.battery_constraints,
      solver_options: settings.solver_options ? { ...defaultSolverOptions, ...settings.solver_options } : prev.solver_options,
      input_file: settings.input_file || prev.input_file, // Excel might specify a relative path for the main data
      timeout: settings.timeout || prev.timeout,
    }));
    dispatch(addNotification({type: 'success', message: 'Settings loaded from Excel.'}));
  };

  const investmentModeDescription = {
    single_year: 'Optimize for a single target year with fixed topology.',
    multi_year: 'Multi-year capacity expansion with investment decisions across periods.',
    all_in_one: 'Comprehensive optimization across all years simultaneously (computationally intensive).',
  };


  return (
    <Container maxWidth="xl" sx={{pb:4}}>
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Paper sx={{ p: {xs:2, sm:3}, borderRadius: 2 }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={2}>
              <Box>
                <Typography variant="h4" component="h1" gutterBottom> PyPSA Power System Modeling </Typography>
                <Typography variant="body1" color="text.secondary"> Configure and execute power system optimization with PyPSA. </Typography>
              </Box>
              <Box sx={{display: 'flex', gap:1, alignItems:'center'}}>
                <Chip
                  label={`Solver: ${config.solver_options?.solver?.toUpperCase() || 'N/A'}`}
                  color="primary"
                  variant="outlined"
                />
                <Chip
                  label={config.input_file ? (inputFileUploaded ? `File: ${inputFileUploaded.name}` : `Path: ${config.input_file}`) : 'No Input File'}
                  color={config.input_file ? 'success' : 'default'}
                  icon={config.input_file ? <CheckCircle /> : <Warning />}
                  variant="outlined"
                />
              </Box>
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12}><SystemStatus /></Grid>

        {activeJobDetails && (activeJobDetails.status === 'running' || activeJobDetails.status === 'queued') && (
          <Grid item xs={12}>
            <OptimizationProgress
              job={activeJobDetails}
              onCancel={handleCancelOptimization}
              title={`Optimizing: ${config.scenario_name || activeJobDetails.id}`}
            />
          </Grid>
        )}
         {activeJobDetails?.status === 'failed' && (
            <Grid item xs={12}> <Alert severity="error" onClose={() => setCurrentOptimizationJobId(null)}> Optimization '{activeJobDetails.id}' failed: {activeJobDetails.error} </Alert> </Grid>
        )}
        {activeJobDetails?.status === 'completed' && (
            <Grid item xs={12}> <Alert severity="success" action={<Button size="small" onClick={() => { /* navigate to results page */ }}>View Results</Button>}> Optimization '{config.scenario_name}' completed. </Alert> </Grid>
        )}


        <Grid item xs={12} md={8}>
          <Paper sx={{ p: {xs:2, sm:3}, borderRadius: 2 }}>
            <Typography variant="h6" gutterBottom sx={{mb:2}}> Model Configuration </Typography>

            {Object.keys(validationErrors).length > 0 && (
              <Alert severity="warning" sx={{ mb: 2 }}>
                Please address the following issues:
                <ul>{Object.entries(validationErrors).map(([key, msg]) => msg && <li key={key}><Typography variant="caption">{key.replace(/_/g, ' ')}: {msg}</Typography></li>)}</ul>
              </Alert>
            )}

            <Accordion defaultExpanded>
              <AccordionSummary expandIcon={<ExpandMore />}><Typography variant="subtitle1">Core Settings</Typography></AccordionSummary>
              <AccordionDetails>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}><TextField fullWidth label="Scenario Name" name="scenario_name" value={config.scenario_name} onChange={(e) => handleConfigChange('scenario_name', e.target.value)} error={!!validationErrors.scenario_name} helperText={validationErrors.scenario_name} required /></Grid>
                  <Grid item xs={12} sm={6}><TextField fullWidth type="number" label="Base Year" name="base_year" value={config.base_year} onChange={(e) => handleConfigChange('base_year', parseInt(e.target.value))} error={!!validationErrors.base_year} helperText={validationErrors.base_year} required /></Grid>
                  <Grid item xs={12}><ExcelSettingsLoader onSettingsLoaded={loadExcelSettings} /></Grid>
                  <Grid item xs={12}>
                     <Button component="label" variant="outlined" startIcon={<CloudUpload />} sx={{width: '100%', py:1.5, textTransform:'none', justifyContent:'flex-start', color: validationErrors.input_file ? 'error.main' : undefined}}>
                        {inputFileUploaded ? `Selected File: ${inputFileUploaded.name}` : (config.input_file ? `Using Path: ${config.input_file}` : 'Upload PyPSA Input Template (.xlsx)')}
                        <input type="file" hidden accept=".xlsx,.xls,.nc" onChange={handleFileUpload} />
                     </Button>
                     {validationErrors.input_file && <Typography color="error" variant="caption" sx={{display: 'block', mt:0.5}}>{validationErrors.input_file}</Typography>}
                     {uploadingInputFile && <CircularProgress size={20} sx={{ml:1}}/>}
                  </Grid>
                </Grid>
              </AccordionDetails>
            </Accordion>

            <Accordion>
              <AccordionSummary expandIcon={<ExpandMore />}><Typography variant="subtitle1">Time & Investment Settings</Typography></AccordionSummary>
              <AccordionDetails>
                <Grid container spacing={2}>
                    <Grid item xs={12} sm={6}>
                        <FormControl component="fieldset" fullWidth>
                            <FormLabel component="legend">Investment Mode</FormLabel>
                            <RadioGroup row value={config.investment_mode} onChange={(e) => handleConfigChange('investment_mode', e.target.value as PyPSAModelConfiguration['investment_mode'])}>
                                <FormControlLabel value="single_year" control={<Radio />} label="Single Year" />
                                <FormControlLabel value="multi_year" control={<Radio />} label="Multi-Year" />
                                <FormControlLabel value="all_in_one" control={<Radio />} label="All-in-One" />
                            </RadioGroup>
                            <Typography variant="caption" color="textSecondary">{investmentModeDescription[config.investment_mode]}</Typography>
                        </FormControl>
                    </Grid>
                    <Grid item xs={12} sm={6}>
                        <FormControl component="fieldset" fullWidth>
                            <FormLabel component="legend">Snapshot Selection</FormLabel>
                            <RadioGroup row value={config.snapshot_selection} onChange={(e) => handleConfigChange('snapshot_selection', e.target.value as PyPSAModelConfiguration['snapshot_selection'])}>
                                <FormControlLabel value="all" control={<Radio />} label="All (Full Year)" />
                                <FormControlLabel value="critical_days" control={<Radio />} label="Critical Days" />
                            </RadioGroup>
                        </FormControl>
                    </Grid>
                </Grid>
              </AccordionDetails>
            </Accordion>

            <Accordion>
              <AccordionSummary expandIcon={<ExpandMore />}><Typography variant="subtitle1">Advanced Technical Options</Typography></AccordionSummary>
              <AccordionDetails>
                <FormGroup>
                    <FormControlLabel control={<Checkbox checked={config.generator_clustering} onChange={(e) => handleConfigChange('generator_clustering', e.target.checked)} />} label="Enable Generator Clustering" />
                    <FormControlLabel control={<Checkbox checked={config.unit_commitment} onChange={(e) => handleConfigChange('unit_commitment', e.target.checked)} />} label="Enable Unit Commitment Constraints" />
                    <FormControlLabel control={<Checkbox checked={config.monthly_constraints} onChange={(e) => handleConfigChange('monthly_constraints', e.target.checked)} />} label="Enable Monthly Constraints (e.g., hydro, emissions)" />
                </FormGroup>
                <FormControl fullWidth margin="normal" size="small">
                    <InputLabel id="battery-constraints-label">Battery Cycling Constraints</InputLabel>
                    <Select labelId="battery-constraints-label" value={config.battery_constraints} label="Battery Cycling Constraints" onChange={(e: SelectChangeEvent<PyPSAModelConfiguration['battery_constraints']>) => handleConfigChange('battery_constraints', e.target.value)}>
                        <MenuItem value="none">None</MenuItem><MenuItem value="daily">Daily</MenuItem><MenuItem value="weekly">Weekly</MenuItem><MenuItem value="monthly">Monthly</MenuItem>
                    </Select>
                </FormControl>
              </AccordionDetails>
            </Accordion>

            <Accordion>
              <AccordionSummary expandIcon={<ExpandMore />}><Typography variant="subtitle1">Solver Settings</Typography></AccordionSummary>
              <AccordionDetails>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={4}>
                    <FormControl fullWidth size="small">
                      <InputLabel>Solver</InputLabel>
                      <Select value={config.solver_options?.solver || 'highs'} label="Solver" onChange={(e) => handleConfigChange('solver_options.solver', e.target.value)}>
                        {['highs', 'cbc', 'glpk', 'gurobi', 'cplex', 'scip', 'xpress'].map(s => <MenuItem key={s} value={s}>{s.toUpperCase()}</MenuItem>)}
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid item xs={12} sm={4}><TextField fullWidth size="small" type="number" label="Optimality Gap" value={config.solver_options?.optimality_gap || ''} onChange={(e) => handleConfigChange('solver_options.optimality_gap', parseFloat(e.target.value))} inputProps={{ min: 0, max: 1, step: 0.001 }} error={!!validationErrors['solver_options.optimality_gap']} helperText={validationErrors['solver_options.optimality_gap'] || "e.g., 0.01 for 1%"} /></Grid>
                  <Grid item xs={12} sm={4}><TextField fullWidth size="small" type="number" label="Time Limit (sec)" value={config.solver_options?.time_limit || ''} onChange={(e) => handleConfigChange('solver_options.time_limit', parseInt(e.target.value))} inputProps={{ min: 60 }} error={!!validationErrors['solver_options.time_limit']} helperText={validationErrors['solver_options.time_limit']}/></Grid>
                </Grid>
              </AccordionDetails>
            </Accordion>

            <Grid item xs={12} sx={{mt:2}}>
                <TextField fullWidth size="small" type="number" label="Script Timeout (ms)" value={config.timeout} onChange={(e) => handleConfigChange('timeout', parseInt(e.target.value))} helperText="Max execution time for the Python script itself." />
            </Grid>

            <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
              <Button variant="outlined" onClick={() => {/* TODO: Implement validation logic if backend supports it */ alert('Model validation not yet implemented.')}} startIcon={<Assessment/>}>Validate Model</Button>
              <Button
                variant="contained"
                size="large"
                startIcon={startingOptimization || uploadingInputFile ? <CircularProgress size={20} color="inherit"/> : <PlayArrow />}
                onClick={handleStartOptimization}
                disabled={startingOptimization || uploadingInputFile || (activeJobDetails?.status === 'running')}
              >
                {startingOptimization || uploadingInputFile ? 'Preparing...' : 'Run Optimization'}
              </Button>
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper sx={{ p: {xs:2, sm:3}, borderRadius: 2, height: '100%' }}>
            <Typography variant="h6" gutterBottom>Information & Status</Typography>
            <Alert severity="info" icon={<HelpOutline/>} sx={{ mb: 2 }}>
              Configure your PyPSA model here. Upload an Excel input template or provide a path to an existing NetCDF file. Detailed solver and model options can be adjusted in the accordions.
            </Alert>
            <Typography variant="subtitle2" gutterBottom>Current Configuration:</Typography>
            <Chip size="small" label={`Scenario: ${config.scenario_name}`} sx={{m:0.5}}/>
            <Chip size="small" label={`Base Year: ${config.base_year}`} sx={{m:0.5}}/>
            <Chip size="small" label={`Mode: ${config.investment_mode}`} sx={{m:0.5}}/>
            <Chip size="small" label={`Solver: ${config.solver_options?.solver || 'default'}`} sx={{m:0.5}}/>
            {/* Add more chips for key config items */}
            <Divider sx={{my:2}}/>
            <Typography variant="subtitle2" gutterBottom>Recent Optimizations:</Typography>
            {/* This would list recent jobs from Redux state or an API call */}
            <Typography variant="body2" color="text.secondary">No recent optimization history available in this view yet.</Typography>
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
};
