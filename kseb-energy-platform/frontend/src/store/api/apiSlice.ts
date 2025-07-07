import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';
import { RootState } from '../index'; // Adjust path as necessary

// Define a base query function that prepares headers and handles potential errors
const baseQuery = fetchBaseQuery({
  baseUrl: process.env.REACT_APP_API_URL || 'http://localhost:5000/api', // Ensure your .env has REACT_APP_API_URL or adjust
  credentials: 'include', // If you need to send cookies
  prepareHeaders: (headers, { getState }) => {
    // Example: Add an authorization token if available in the Redux state
    // const token = (getState() as RootState).auth.token; // Assuming an auth slice
    // if (token) {
    //   headers.set('authorization', `Bearer ${token}`);
    // }
    headers.set('Content-Type', 'application/json');
    return headers;
  },
});

// Define the API slice
export const apiSlice = createApi({
  reducerPath: 'api', // This is the key where your API reducer will be mounted in the store
  baseQuery: baseQuery,
  tagTypes: [ // Define tag types for caching and invalidation
    'Project',
    'DemandForecast',
    'LoadProfile',
    'PyPSAOptimization',
    'SectorData', // For caching sector-specific data from demand module
    'NetworkResults', // For caching PyPSA network results
    'UploadedFile' // For file uploads
  ],
  endpoints: (builder) => ({
    // Project endpoints (example)
    createProject: builder.mutation({
      query: (projectData) => ({
        url: '/projects', // Example endpoint
        method: 'POST',
        body: projectData,
      }),
      invalidatesTags: ['Project'], // Invalidate 'Project' tag on successful mutation
    }),

    loadProject: builder.mutation({
      query: (projectPath) => ({
        url: '/projects/load', // Example endpoint
        method: 'POST',
        body: { path: projectPath },
      }),
      invalidatesTags: ['Project'],
    }),

    // Demand projection endpoints
    getSectorData: builder.query({
      query: (sector: string) => `/demand/sectors/${sector}`,
      providesTags: (result, error, sector) => [{ type: 'SectorData', id: sector }],
    }),

    runForecast: builder.mutation({
      query: (config) => ({
        url: '/demand/forecast',
        method: 'POST',
        body: config,
      }),
      // invalidatesTags: ['DemandForecast'], // Could invalidate if you list forecasts
    }),

    getForecastStatus: builder.query({
      query: (forecastId: string) => `/demand/forecast/${forecastId}/status`,
      providesTags: (result, error, forecastId) => [{ type: 'DemandForecast', id: forecastId }],
      // Consider adding polling for status updates if not using WebSockets for everything
      // async onCacheEntryAdded(arg, { updateCachedData, cacheDataLoaded, cacheEntryRemoved }) {
      //   // TODO: WebSocket logic for real-time updates can be integrated here or in components
      // }
    }),

    getCorrelationData: builder.query({
      query: (sector: string) => `/demand/correlation/${sector}`,
      providesTags: (result, error, sector) => [{ type: 'SectorData', id: `correlation-${sector}` }],
    }),

    // Load profile endpoints
    generateProfile: builder.mutation({
      query: (config) => ({
        url: '/loadprofile/generate',
        method: 'POST',
        body: config,
      }),
      invalidatesTags: ['LoadProfile'], // Invalidate list of profiles
    }),

    getSavedProfiles: builder.query({
      query: () => '/loadprofile/profiles',
      providesTags: (result) =>
        result ? [...result.profiles.map(({ profile_id }: any) => ({ type: 'LoadProfile' as const, id: profile_id })), { type: 'LoadProfile', id: 'LIST' }] : [{ type: 'LoadProfile', id: 'LIST'}],
    }),

    getProfileData: builder.query({
      query: (profileId: string) => `/loadprofile/profiles/${profileId}`,
      providesTags: (result, error, profileId) => [{ type: 'LoadProfile', id: profileId }],
    }),

    analyzeProfile: builder.query({
      query: ({ profileId, analysisType }: { profileId: string; analysisType: string }) =>
        `/loadprofile/analyze/${profileId}?analysisType=${analysisType}`,
      providesTags: (result, error, { profileId, analysisType }) => [
        { type: 'LoadProfile', id: `${profileId}-${analysisType}` }
      ],
    }),

    compareProfiles: builder.mutation({
      query: (profileIds: string[]) => ({
        url: '/loadprofile/compare',
        method: 'POST',
        body: { profileIds }, // Backend expects { profileIds: [...] }
      }),
      // No specific invalidation here unless it affects other cached data
    }),

    deleteProfile: builder.mutation({
      query: (profileId: string) => ({
        url: `/loadprofile/profiles/${profileId}`,
        method: 'DELETE',
      }),
      invalidatesTags: (result, error, profileId) => [{ type: 'LoadProfile', id: 'LIST' }, { type: 'LoadProfile', id: profileId }],
    }),

    // PyPSA endpoints
    runOptimization: builder.mutation({
      query: (config) => ({
        url: '/pypsa/optimize',
        method: 'POST',
        body: config,
      }),
      // invalidatesTags: ['PyPSAOptimization'],
    }),

    getOptimizationStatus: builder.query({
      query: (jobId: string) => `/pypsa/optimization/${jobId}/status`,
      providesTags: (result, error, jobId) => [{ type: 'PyPSAOptimization', id: jobId }],
    }),

    getAvailableNetworks: builder.query({
      query: () => '/pypsa/networks',
      providesTags: (result) =>
        result ? [...result.networks.map(({ scenario_name }: any) => ({ type: 'NetworkResults' as const, id: scenario_name })), { type: 'NetworkResults', id: 'LIST' }] : [{ type: 'NetworkResults', id: 'LIST'}],
    }),

    extractNetworkResults: builder.mutation({
      query: (params: { networkPath?: string; scenarioName?: string }) => ({ // networkPath or scenarioName
        url: '/pypsa/extract-results', // Changed from /pypsa/extract to match controller
        method: 'POST',
        body: params, // Send { networkPath } or { scenarioName }
      }),
      // invalidatesTags: (result, error, { scenarioName }) => scenarioName ? [{ type: 'NetworkResults', id: scenarioName }] : [],
    }),

    getPyPSAAnalysisData: builder.query({
        query: ({ analysisType, networkPath, params }: { analysisType: string, networkPath: string, params?: Record<string, string> }) => {
            const searchParams = new URLSearchParams(params);
            return `/pypsa/analysis/${encodeURIComponent(networkPath)}/${analysisType}?${searchParams}`;
        },
        providesTags: (result, error, { networkPath, analysisType }) => [
            { type: 'NetworkResults', id: `${analysisType}-${networkPath}` }
        ],
    }),

    // File upload endpoint
    uploadFile: builder.mutation({
      query: ({ file, fileType }: { file: File, fileType: string }) => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('type', fileType); // e.g., 'demand_input', 'load_profile_template', 'pypsa_config'

        return {
          url: '/files/upload', // Assuming a generic file upload endpoint
          method: 'POST',
          body: formData,
          // formData: true, // fetchBaseQuery automatically handles FormData
        };
      },
      invalidatesTags: ['UploadedFile'], // Or more specific tags if needed
    }),
  }),
});

// Export hooks for usage in functional components
// These are automatically generated based on the endpoints defined above
export const {
  // Project hooks
  useCreateProjectMutation,
  useLoadProjectMutation,

  // Demand projection hooks
  useGetSectorDataQuery,
  useRunForecastMutation,
  useGetForecastStatusQuery,
  useGetCorrelationDataQuery,

  // Load profile hooks
  useGenerateProfileMutation,
  useGetSavedProfilesQuery,
  useGetProfileDataQuery,
  useAnalyzeProfileQuery,
  useCompareProfilesMutation,
  useDeleteProfileMutation,

  // PyPSA hooks
  useRunOptimizationMutation,
  useGetOptimizationStatusQuery,
  useGetAvailableNetworksQuery,
  useExtractNetworkResultsMutation,
  useGetPyPSAAnalysisDataQuery, // Generic query for PyPSA analysis types

  // File upload hook
  useUploadFileMutation,
} = apiSlice;
