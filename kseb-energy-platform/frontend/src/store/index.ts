import { configureStore } from '@reduxjs/toolkit';
import { setupListeners } from '@reduxjs/toolkit/query/react';

// Import slice reducers
import projectReducer from './slices/projectSlice'; // Will be created
import demandReducer from './slices/demandSlice'; // Will be created
import loadProfileReducer from './slices/loadProfileSlice'; // Will be created
import pypsaReducer from './slices/pypsaSlice'; // Will be created
import uiReducer from './slices/uiSlice'; // Will be created
import notificationReducer from './slices/notificationSlice'; // Will be created

// Import API slice
import { apiSlice } from './api/apiSlice'; // Will be created

export const store = configureStore({
  reducer: {
    // Feature slices
    project: projectReducer,
    demand: demandReducer,
    loadProfile: loadProfileReducer,
    pypsa: pypsaReducer,
    ui: uiReducer,
    notifications: notificationReducer,

    // API slice
    [apiSlice.reducerPath]: apiSlice.reducer, // Use reducerPath for the key
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // Ignore these action types from redux-persist if it's used later
        ignoredActions: ['persist/PERSIST', 'persist/REHYDRATE', /* add other specific actions if needed */],
        // Ignore these paths in the state
        ignoredPaths: [/* 'some.path.to.ignore' */],
      },
    }).concat(apiSlice.middleware),
  devTools: process.env.NODE_ENV !== 'production',
});

// Setup RTK Query listeners
// It enables caching, invalidation, polling, and other useful features of `rtk-query`.
setupListeners(store.dispatch);

// Infer the `RootState` and `AppDispatch` types from the store itself
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

// Export typed hooks (will be defined in hooks.ts)
// For now, this line might cause a temporary error until hooks.ts is created and exports these
// export { useAppDispatch, useAppSelector } from './hooks';
