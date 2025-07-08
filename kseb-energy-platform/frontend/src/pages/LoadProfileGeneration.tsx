import React, { useState, useEffect } from 'react';
import { useSelector } from 'react-redux';
import {
  Container, Grid, Paper, Typography, Button, Box,
  Stepper, Step, StepLabel, StepContent, Alert, Chip, Dialog, DialogTitle, DialogContent, CircularProgress
} from '@mui/material';
import {
  Timeline, TrendingUp, CloudUpload, PlayArrow, Visibility, ListAlt, SettingsApplications, BarChart
} from '@mui/icons-material';

import { RootState } from '../store'; // Corrected
import { useAppDispatch } from '../store/hooks'; // Corrected
import {
  useGenerateProfileMutation,
  useGetSavedProfilesQuery,
  // useUploadFileMutation
} from '../store/api/apiSlice'; // Corrected
import { useProfileNotifications } from '../services/websocket'; // Corrected
import { MethodSelection, GenerationMethod } from '../components/loadProfile/MethodSelection'; // Corrected
import { ConfigurationForm, ProfileConfigData } from '../components/loadProfile/ConfigurationForm'; // Corrected
import { TemplateUpload } from '../components/loadProfile/TemplateUpload'; // Corrected
import { ProfilePreview } from '../components/loadProfile/ProfilePreview'; // Corrected
import { ProfileManager } from '../components/loadProfile/ProfileManager'; // Corrected
import { GenerationProgress } from '../components/loadProfile/GenerationProgress'; // Corrected
import { addNotification } from '../store/slices/notificationSlice'; // Corrected

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
    if (stepIndex === 1) return !!selectedMethod && Object.keys(generationConfig).length > 0;
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
    setActiveStep(2);
  };

  const handleDataValidated = (fileUploaded: boolean) => {
    setTemplateFileUploaded(fileUploaded);
  };

  const handleNext = () => {
    setActiveStep((prevActiveStep) => prevActiveStep + 1);
  };

  const handleBack = () => {
    setActiveStep((prevActiveStep) => prevActiveStep - 1);
  };

  const handleStepClick = (stepIndex: number) => {
    if (isStepCompleted(stepIndex) || stepIndex < activeStep) {
      setActiveStep(stepIndex);
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

    const finalConfig = {
      method: selectedMethod.id,
      ...generationConfig,
    };

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
                      sx={{ cursor: (isStepCompleted(index) || index < activeStep) ? 'pointer' : 'default', mb:1 }}
                    >
                      <Typography variant="subtitle1">{step.label}</Typography>
                    </StepLabel>
                    <StepContent sx={{borderLeft: (theme) => `1px solid ${theme.palette.divider}`, ml:1.5, pl:2, pb:2}}>
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
                          <Paper variant="outlined" sx={{p:2, mb:2, maxHeight: 200, overflowY:'auto'}}>
                            <pre style={{margin:0, fontSize:'0.8rem'}}>
                                Method: {selectedMethod.name}\n
                                {JSON.stringify(generationConfig, null, 2)}
                                {templateFileUploaded ? "\nCustom template uploaded." : ""}
                            </pre>
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
                            disabled={!isStepCompleted(index) || (index === WIZARD_STEPS.length - 1 && (startingGeneration || activeJobDetails?.status === 'running'))}
                          >
                            {index === WIZARD_STEPS.length - 1 ? 'Generate' : 'Next'}
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
                    <Button onClick={() => { setActiveStep(0); setCurrentProfileJobId(null); }} sx={{mt:2}}>
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
          <ProfilePreview />
        </DialogContent>
      </Dialog>
    </Container>
  );
};
