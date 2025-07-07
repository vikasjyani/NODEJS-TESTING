import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { RootState } from '../index';

interface ForecastJob {
  id: string; // forecastId from backend
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number; // 0-100
  currentSector?: string; // Sector being processed
  statusDetails?: string; // More detailed status message from Python
  startTime: string; // ISO string
  completedTime?: string; // ISO string
  failedTime?: string; // ISO string
  config: any; // The configuration used for this forecast
  result?: any; // The final result from the forecast
  error?: string; // Error message if failed
}

interface DemandState {
  // Stores multiple active or recent forecast jobs
  forecastJobs: Record<string, ForecastJob>; // Keyed by forecastId
  // Potentially other demand-related state like selected sector data, correlation results etc.
  // but these are better handled by RTK Query's caching if fetched via API.
}

const initialState: DemandState = {
  forecastJobs: {},
};

const demandSlice = createSlice({
  name: 'demand',
  initialState,
  reducers: {
    // Action to initiate or update a forecast job when it starts
    forecastJobStarted: (state, action: PayloadAction<{ forecastId: string; config: any }>) => {
      const { forecastId, config } = action.payload;
      state.forecastJobs[forecastId] = {
        id: forecastId,
        config,
        status: 'queued',
        progress: 0,
        startTime: new Date().toISOString(),
      };
    },
    // Action to update the progress of a forecast
    updateForecastProgress: (
      state,
      action: PayloadAction<{
        forecastId: string;
        progress: number;
        sector?: string;
        status?: string; // Detailed status from Python
      }>
    ) => {
      const { forecastId, progress, sector, status } = action.payload;
      if (state.forecastJobs[forecastId]) {
        state.forecastJobs[forecastId].progress = progress;
        if (sector) state.forecastJobs[forecastId].currentSector = sector;
        if (status) state.forecastJobs[forecastId].statusDetails = status;
        if (state.forecastJobs[forecastId].status === 'queued' && progress > 0) {
             state.forecastJobs[forecastId].status = 'running';
        }
      }
    },
    // Action when a forecast is successfully completed
    setForecastCompleted: (
      state,
      action: PayloadAction<{ forecastId: string; result: any }>
    ) => {
      const { forecastId, result } = action.payload;
      if (state.forecastJobs[forecastId]) {
        state.forecastJobs[forecastId].status = 'completed';
        state.forecastJobs[forecastId].progress = 100;
        state.forecastJobs[forecastId].result = result;
        state.forecastJobs[forecastId].completedTime = new Date().toISOString();
      }
    },
    // Action when a forecast fails
    setForecastError: (
      state,
      action: PayloadAction<{ forecastId: string; error: string }>
    ) => {
      const { forecastId, error } = action.payload;
      if (state.forecastJobs[forecastId]) {
        state.forecastJobs[forecastId].status = 'failed';
        state.forecastJobs[forecastId].error = error;
        state.forecastJobs[forecastId].failedTime = new Date().toISOString();
      }
    },
    // Action when a forecast is cancelled
    setForecastCancelled: (state, action: PayloadAction<{ forecastId: string }>) => {
        const { forecastId } = action.payload;
        if (state.forecastJobs[forecastId]) {
            state.forecastJobs[forecastId].status = 'cancelled';
            // Optionally record cancelledTime
        }
    },
    // Clear a specific forecast job from state
    clearForecastJob: (state, action: PayloadAction<string>) => {
        delete state.forecastJobs[action.payload];
    },
    // Clear all forecast jobs
    clearAllForecastJobs: (state) => {
        state.forecastJobs = {};
    }
  },
  // Extra reducers can be used to handle actions from RTK Query if needed,
  // for example, when a `runForecast` mutation is initiated or fulfilled.
  // extraReducers: (builder) => {
  //   builder
  //     .addMatcher(
  //       apiSlice.endpoints.runForecast.matchPending,
  //       (state, action) => {
  //         // action.meta.arg.originalArgs is the config passed to the mutation
  //         // action.meta.requestId is unique for this pending request
  //         // You might not get forecastId here until backend responds.
  //         // Better to dispatch forecastJobStarted from component when backend confirms job acceptance.
  //       }
  //     )
  //     .addMatcher(
  //       apiSlice.endpoints.runForecast.matchFulfilled,
  //       (state, action) => {
  //         // action.payload contains { success, forecastId, message }
  //         const { forecastId } = action.payload;
  //         const originalConfig = action.meta.arg.originalArgs;
  //         if (forecastId && !state.forecastJobs[forecastId]) { // Ensure not already started by WebSocket
  //            state.forecastJobs[forecastId] = {
  //                id: forecastId,
  //                config: originalConfig,
  //                status: 'queued', // Or 'running' if backend starts immediately
  //                progress: 0,
  //                startTime: new Date().toISOString(),
  //            };
  //         }
  //       }
  //     );
  // }
});

export const {
  forecastJobStarted,
  updateForecastProgress,
  setForecastCompleted,
  setForecastError,
  setForecastCancelled,
  clearForecastJob,
  clearAllForecastJobs,
} = demandSlice.actions;

// Selectors
export const selectAllForecastJobs = (state: RootState) => state.demand.forecastJobs;
export const selectForecastJobById = (state: RootState, forecastId: string) => state.demand.forecastJobs[forecastId];

export default demandSlice.reducer;
