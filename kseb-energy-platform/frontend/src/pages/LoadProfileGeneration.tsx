import React, { useState, useEffect } from 'react';
import { useSelector } from 'react-redux';
import {
  Container, Grid, Paper, Typography, Button, Box,
  Stepper, Step, StepLabel, StepContent, Alert, Chip, Dialog, DialogTitle, DialogContent, CircularProgress
} from '@mui/material';
import {
  Timeline, TrendingUp, CloudUpload, PlayArrow, Visibility, ListAlt, SettingsApplications
} from '@mui/icons-material'; // Removed BarChart as it's not used here directly

import { RootState } from '../store';
import { useAppDispatch } from '../store/hooks';
import {
  useGenerateProfileMutation,
  useGetSavedProfilesQuery,
} from '../store/api/apiSlice';
import { useProfileNotifications } from '../services/websocket';
import { MethodSelection, GenerationMethod } from '../components/loadProfile/MethodSelection';
import { ConfigurationForm, ProfileConfigData } from '../components/loadProfile/ConfigurationForm';
import { TemplateUpload } from '../components/loadProfile/TemplateUpload';
import { ProfilePreview } from '../components/loadProfile/ProfilePreview';
import { ProfileManager } from '../components/loadProfile/ProfileManager';
import { GenerationProgress } from '../components/loadProfile/GenerationProgress';
import { addNotification } from '../store/slices/notificationSlice';

interface GenerationStep {
  label: string;
  description: string;
  icon: React.ReactElement;
}

const WIZARD_STEPS: GenerationStep[] = [
  {
    label: 'Method Selection',
    description: 'Choose generation method based on your data and requirements.',
    icon: <ListAlt />
  },
  {
    label: 'Configuration',
    description: 'Set parameters for the selected generation method.',
    icon: <SettingsApplications />
  },
  {
    label: 'Data Upload (Optional)',
    description: 'Upload required templates or custom data if not using defaults.',
    icon: <CloudUpload />
  },
  {
    label: 'Review & Generate',
    description: 'Review settings and execute profile generation.',
    icon: <PlayArrow />
  }
];


export const LoadProfileGeneration: React.FC = () => {
  const dispatch = useAppDispatch();
  const [activeStep, setActiveStep] = useState(0);
  const [selectedMethod, setSelectedMethod] = useState<GenerationMethod | null>(null);
  const [generationConfig, setGenerationConfig] = useState<Partial<ProfileConfigData>>({});
  const [templateFileUploaded, setTemplateFileUploaded] = useState<boolean>(false);

  const [currentProfileJobId, setCurrentProfileJobId] = useState<string | null>(null);
  const [previewDialogOpen, setPreviewDialogOpen] = useState(false);

  const [generateProfile, { isLoading: startingGeneration, error: generationStartError }] = useGenerateProfileMutation();
  const { data: savedProfilesData, refetch: refetchProfiles, isLoading: profilesLoading } = useGetSavedProfilesQuery(undefined, {});

  useProfileNotifications(currentProfileJobId);

  const profileJobs = useSelector((state: RootState) => state.loadProfile.generationJobs);
  const activeJobDetails = currentProfileJobId ? profileJobs[currentProfileJobId] : null;

  useEffect(() => {
    if (generationStartError) {
      dispatch(addNotification({type: 'error', message: `Failed to start profile generation: ${ (generationStartError as any)?.data?.message || (generationStartError as any)?.error || 'Unknown error'}`}));
    }
  }, [generationStartError, dispatch]);

  const isStepCompleted = (stepIndex: number): boolean => {
    if (stepIndex < activeStep) return true;
    if (stepIndex === 0) return !!selectedMethod;
    if (stepIndex === 1) return !!selectedMethod && (selectedMethod.requiresConfig === false || Object.keys(generationConfig).length > 0);
    if (stepIndex === 2) {
        if (selectedMethod?.requiresTemplateUpload && !templateFileUploaded) return false;
        return true;
    }
    return false;
  };


  const handleMethodSelection = (method: GenerationMethod) => {
    setSelectedMethod(method);
    setGenerationConfig({});
    setActiveStep(1);
  };

  const handleConfigurationComplete = (config: ProfileConfigData) => {
    setGenerationConfig(config);
    // Only auto-advance if data upload is not required by the method, or if it's already handled
    if (!selectedMethod?.requiresTemplateUpload) {
        setActiveStep(3); // Skip to Review & Generate
    } else {
        setActiveStep(2); // Move to Data Upload
    }
  };

  const handleDataValidated = (fileUploaded: boolean, filePath?: string) => {
    setTemplateFileUploaded(fileUploaded);
    if (fileUploaded && filePath) {
        // If a file path is returned (e.g. from server after upload), store it in config
        setGenerationConfig(prev => ({...prev, customTemplatePath: filePath}));
    }
    // Potentially auto-advance if this step is now complete
    // setActiveStep(3); // Or let user click Next
  };

  const handleNext = () => {
    // Special handling for skipping optional data upload step
    if (activeStep === 1 && selectedMethod && !selectedMethod.requiresTemplateUpload && !selectedMethod.requiresConfig) {
        // If config was also not required and method selected, can skip to review
         setActiveStep(3); // Skip to Review & Generate
    } else if (activeStep === 1 && selectedMethod && !selectedMethod.requiresTemplateUpload && selectedMethod.requiresConfig && Object.keys(generationConfig).length > 0) {
        setActiveStep(3); // Skip to Review & Generate
    }
    else {
        setActiveStep((prevActiveStep) => prevActiveStep + 1);
    }
  };

  const handleBack = () => {
    setActiveStep((prevActiveStep) => prevActiveStep - 1);
  };

  const handleStepClick = (stepIndex: number) => {
    // Allow navigation to any previous step, or current step if prerequisites met
    if (stepIndex < activeStep || isStepCompleted(stepIndex-1) || stepIndex === 0) {
         // If going back to step 0, reset method and config
        if(stepIndex === 0 && activeStep > 0) {
            // setSelectedMethod(null); // Keep method selected to avoid re-showing selection unless user explicitly changes
            // setGenerationConfig({});
            // setTemplateFileUploaded(false);
        }
      setActiveStep(stepIndex);
    } else {
        dispatch(addNotification({type: 'info', message: `Please complete step ${activeStep +1} first.`}))
    }
  };


  const handleStartGeneration = async () => {
    if (!selectedMethod) {
        dispatch(addNotification({type: 'error', message: 'Please select a generation method.'}));
        return;
    }
    if (Object.keys(generationConfig).length === 0 && selectedMethod.requiresConfig) {
         dispatch(addNotification({type: 'error', message: 'Please complete the configuration for the selected method.'}));
        return;
    }
    if (selectedMethod.requiresTemplateUpload && !templateFileUploaded) {
        dispatch(addNotification({type: 'error', message: 'A template file is required for this method.'}));
        return;
    }


    const finalConfig: any = { // Cast to any or define a more encompassing type for submission
      method: selectedMethod.id,
      ...generationConfig,
    };
    // If templateFileUploaded and a path was stored (e.g., from a server upload response)
    // finalConfig.templateFilePath = (generationConfig as any).customTemplatePath;


    try {
      const response = await generateProfile(finalConfig).unwrap();
      if (response.success && response.profileJobId) {
        setCurrentProfileJobId(response.profileJobId);
        dispatch(addNotification({type: 'info', message: `Profile generation job '${response.profileJobId}' started.`}));
        setActiveStep(WIZARD_STEPS.length);
      } else {
        dispatch(addNotification({type: 'error', message: response.message || 'Failed to start profile generation.'}));
      }
    } catch (err) {
      console.error('Failed to start generation:', err);
    }
  };

  const handleCancelGeneration = () => {
    if (activeJobDetails && (activeJobDetails.status === 'running' || activeJobDetails.status === 'queued')) {
        dispatch(addNotification({type: 'info', message: `Requesting cancellation for job ${activeJobDetails.id}.`}));
    }
  };

  return (
    <Container maxWidth="xl" sx={{pb:4}}>
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Paper sx={{ p: {xs:2, sm:3}, borderRadius: 2 }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={2}>
              <Box>
                <Typography variant="h4" component="h1" gutterBottom>
                  Load Profile Generation
                </Typography>
                <Typography variant="body1" color="text.secondary">
                  Create hourly load profiles using various generation methods and configurations.
                </Typography>
              </Box>
              <Box sx={{display: 'flex', gap: 1}}>
                <Button
                  variant="outlined"
                  startIcon={<Visibility />}
                  onClick={() => setPreviewDialogOpen(true)}
                >
                  Preview Base Data
                </Button>
                <Chip
                  label={selectedMethod ? `Method: ${selectedMethod.name}` : 'No Method Selected'}
                  color={selectedMethod ? 'primary' : 'default'}
                  variant={selectedMethod ? 'filled' : 'outlined'}
                  icon={selectedMethod?.icon}
                />
              </Box>
            </Box>
          </Paper>
        </Grid>

        {activeJobDetails && (activeJobDetails.status === 'running' || activeJobDetails.status === 'queued') && (
          <Grid item xs={12}>
            <GenerationProgress
              job={activeJobDetails}
              onCancel={handleCancelGeneration}
              title={`Generating Profile: ${activeJobDetails.config?.profile_name || activeJobDetails.id}`}
            />
          </Grid>
        )}
        {activeJobDetails?.status === 'failed' && (
            <Grid item xs={12}> <Alert severity="error" onClose={() => setCurrentProfileJobId(null)}> Generation job '{activeJobDetails.id}' failed: {activeJobDetails.error} </Alert> </Grid>
        )}
        {activeJobDetails?.status === 'completed' && (
            <Grid item xs={12}> <Alert severity="success" action={<Button size="small" onClick={() => { /* navigate to analysis or refresh list */ }}>View Profile</Button>}> Profile '{activeJobDetails.result?.profile_id}' generated. </Alert> </Grid>
        )}


        <Grid item xs={12} md={activeStep < WIZARD_STEPS.length ? 8 : 12}>
          <Paper sx={{ p: {xs:2, sm:3}, borderRadius: 2 }}>
            <Typography variant="h6" gutterBottom sx={{mb:2}}>
              Generation Wizard {activeStep < WIZARD_STEPS.length ? ` - Step ${activeStep + 1} of ${WIZARD_STEPS.length}` : '- Monitoring'}
            </Typography>

            {activeStep < WIZARD_STEPS.length ? (
                <Stepper activeStep={activeStep} orientation="vertical">
                {WIZARD_STEPS.map((step, index) => (
                  <Step key={step.label} completed={isStepCompleted(index)}>
                    <StepLabel
                      onClick={() => handleStepClick(index)}
                      icon={step.icon}
                      sx={{ cursor: (isStepCompleted(index) || index < activeStep || index === 0) ? 'pointer' : 'default', mb:1 }}
                    >
                      <Typography variant="subtitle1">{step.label}</Typography>
                    </StepLabel>
                    <StepContent sx={{borderLeft: (theme) => `1px solid ${theme.palette.divider}`, ml: ((step.icon as any)?.type?.muiName === 'SvgIcon' ? 1.5 : 0) + (step.icon ? 1.5 : 0), pl:2, pb:2}}> {/* Adjust margin based on icon presence */}
                      <Typography variant="body2" color="text.secondary" gutterBottom>
                        {step.description}
                      </Typography>

                      {index === 0 && (
                        <MethodSelection
                          onMethodSelect={handleMethodSelection}
                          selectedMethodId={selectedMethod?.id}
                        />
                      )}
                      {index === 1 && selectedMethod && (
                        <ConfigurationForm
                          method={selectedMethod}
                          onConfigChange={handleConfigurationComplete}
                          initialConfig={generationConfig}
                          isLoading={startingGeneration}
                        />
                      )}
                      {index === 2 && selectedMethod && (
                        <TemplateUpload
                          method={selectedMethod}
                          onDataUploaded={handleDataValidated}
                        />
                      )}
                      {index === 3 && selectedMethod && (
                        <Box>
                          <Typography variant="subtitle2" gutterBottom>Review Configuration:</Typography>
                          <Paper variant="outlined" sx={{p:2, mb:2, maxHeight: 200, overflowY:'auto', whiteSpace:'pre-wrap', wordBreak:'break-all', bgcolor:'action.hover'}}>
                                {`Method: ${selectedMethod.name}\n`}
                                {`Config: ${JSON.stringify(generationConfig, null, 2)}\n`}
                                {templateFileUploaded ? "Custom template has been processed." : "Using default/no template."}
                          </Paper>
                          <Button
                            variant="contained"
                            color="primary"
                            startIcon={startingGeneration ? <CircularProgress size={20} color="inherit"/> : <PlayArrow />}
                            onClick={handleStartGeneration}
                            disabled={startingGeneration || (activeJobDetails?.status === 'running')}
                            size="large"
                          >
                            {startingGeneration ? 'Starting...' : 'Generate Load Profile'}
                          </Button>
                        </Box>
                      )}
                       <Box sx={{ mt: 2, mb: 1 }}>
                        <div>
                          <Button disabled={index === 0} onClick={handleBack} sx={{ mr: 1 }}>
                            Back
                          </Button>
                          <Button
                            variant="contained"
                            onClick={index === WIZARD_STEPS.length - 1 ? handleStartGeneration : handleNext}
                            // Disable Next if current step is not completed, unless it's the method selection step
                            disabled={
                                !(index === 0 && selectedMethod) && // For step 0, only need method selected to enable Next
                                !(index > 0 && isStepCompleted(index)) && // For other steps, they must be "completed"
                                !(index === WIZARD_STEPS.length - 1) // Generate button has its own disabled logic
                            }
                          >
                            {index === WIZARD_STEPS.length - 1 ? (startingGeneration ? 'Processing...' : 'Generate') : 'Next'}
                          </Button>
                        </div>
                      </Box>
                    </StepContent>
                  </Step>
                ))}
              </Stepper>
            ) : (
                 <Box sx={{textAlign: 'center', p:3}}>
                    <Typography variant="h5">Profile Generation In Progress</Typography>
                    <Typography>Monitoring job: {activeJobDetails?.id || currentProfileJobId}</Typography>
                    <Button onClick={() => { setActiveStep(0); setCurrentProfileJobId(null); setSelectedMethod(null); setGenerationConfig({}); setTemplateFileUploaded(false); }} sx={{mt:2}}>
                        Start New Generation
                    </Button>
                 </Box>
            )}
          </Paper>
        </Grid>

        { (activeStep >= WIZARD_STEPS.length || !selectedMethod) && (
            <Grid item xs={12} md={4}>
                <ProfileManager
                savedProfiles={savedProfilesData?.profiles || []}
                onRefresh={refetchProfiles}
                isLoading={profilesLoading}
                activeGenerationJobId={currentProfileJobId}
                />
            </Grid>
        )}
      </Grid>

      <Dialog open={previewDialogOpen} onClose={() => setPreviewDialogOpen(false)} maxWidth="lg" fullWidth>
        <DialogTitle>Base Data Preview</DialogTitle>
        <DialogContent>
          <ProfilePreview
            selectedMethodId={selectedMethod?.id}
          />
        </DialogContent>
      </Dialog>
    </Container>
  );
};
