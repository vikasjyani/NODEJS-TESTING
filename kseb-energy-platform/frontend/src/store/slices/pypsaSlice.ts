import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { RootState } from '../index';

interface PyPSAJob {
  id: string; // jobId from backend controller
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number; // 0-100
  currentStep?: string; // Current step in optimization (e.g., "Network Loading", "Solving")
  statusDetails?: string; // More detailed status from Python
  startTime: string; // ISO string
  completedTime?: string; // ISO string
  failedTime?: string; // ISO string
  config: any; // Configuration used
  result?: any; // Final result (e.g., { network_path, summary, objective_value })
  error?: string;
}

// Could also store list of available networks if not solely relying on RTK Query
interface AvailableNetwork {
    scenario_name: string;
    network_path: string; // Server-side path
    file_size?: number;
    created_time?: string;
}

interface PyPSAState {
  optimizationJobs: Record<string, PyPSAJob>; // Keyed by jobId
  // availableNetworksList: AvailableNetwork[]; // Alternative to RTK Query
}

const initialState: PyPSAState = {
  optimizationJobs: {},
  // availableNetworksList: [],
};

const pypsaSlice = createSlice({
  name: 'pypsa',
  initialState,
  reducers: {
    optimizationJobStarted: (state, action: PayloadAction<{ jobId: string; config: any }>) => {
      const { jobId, config } = action.payload;
      state.optimizationJobs[jobId] = {
        id: jobId,
        config,
        status: 'queued',
        progress: 0,
        startTime: new Date().toISOString(),
      };
    },
    updateOptimizationProgress: (
      state,
      action: PayloadAction<{
        jobId: string; // Main job ID from Node.js controller
        pythonJobId?: string; // ID from Python script, if any
        progress: number;
        step?: string; // Current step from Python
        status?: string; // Detailed status from Python
      }>
    ) => {
      const { jobId, progress, step, status } = action.payload;
      if (state.optimizationJobs[jobId]) {
        state.optimizationJobs[jobId].progress = progress;
        if (step) state.optimizationJobs[jobId].currentStep = step;
        if (status) state.optimizationJobs[jobId].statusDetails = status;
        if (state.optimizationJobs[jobId].status === 'queued' && progress > 0) {
            state.optimizationJobs[jobId].status = 'running';
        }
      }
    },
    setOptimizationCompleted: (
      state,
      action: PayloadAction<{ jobId: string; result: any }> // result from Python
    ) => {
      const { jobId, result } = action.payload;
      if (state.optimizationJobs[jobId]) {
        state.optimizationJobs[jobId].status = 'completed';
        state.optimizationJobs[jobId].progress = 100;
        state.optimizationJobs[jobId].result = result; // Python result: { network_path, summary, etc. }
        state.optimizationJobs[jobId].completedTime = new Date().toISOString();
      }
    },
    setOptimizationError: (
      state,
      action: PayloadAction<{ jobId: string; error: string }>
    ) => {
      const { jobId, error } = action.payload;
      if (state.optimizationJobs[jobId]) {
        state.optimizationJobs[jobId].status = 'failed';
        state.optimizationJobs[jobId].error = error;
        state.optimizationJobs[jobId].failedTime = new Date().toISOString();
      }
    },
    setOptimizationCancelled: (state, action: PayloadAction<{ jobId: string }>) => {
        const { jobId } = action.payload;
        if (state.optimizationJobs[jobId]) {
            state.optimizationJobs[jobId].status = 'cancelled';
        }
    },
    clearOptimizationJob: (state, action: PayloadAction<string>) => {
        delete state.optimizationJobs[action.payload];
    },
    clearAllOptimizationJobs: (state) => {
        state.optimizationJobs = {};
    }
    // Potentially add reducers for managing availableNetworksList
  },
});

export const {
  optimizationJobStarted,
  updateOptimizationProgress,
  setOptimizationCompleted,
  setOptimizationError,
  setOptimizationCancelled,
  clearOptimizationJob,
  clearAllOptimizationJobs,
} = pypsaSlice.actions;

// Selectors
export const selectAllOptimizationJobs = (state: RootState) => state.pypsa.optimizationJobs;
export const selectOptimizationJobById = (state: RootState, jobId: string) => state.pypsa.optimizationJobs[jobId];

export default pypsaSlice.reducer;
