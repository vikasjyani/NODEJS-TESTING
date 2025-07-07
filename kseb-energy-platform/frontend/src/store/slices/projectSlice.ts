import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { RootState } from '../index';

interface ProjectFile {
  name: string;
  path: string;
  type: 'input' | 'result' | 'config' | 'script';
  lastModified: string;
}

interface ProjectState {
  currentProject: {
    name: string | null;
    path: string | null;
    description?: string;
    files: ProjectFile[];
    lastAccessed: string | null;
    isLoading: boolean;
    error: string | null;
  } | null;
  recentProjects: Array<{ name: string; path: string; lastAccessed: string }>;
}

const initialState: ProjectState = {
  currentProject: null,
  recentProjects: [], // This could be loaded from localStorage or Electron store
};

const projectSlice = createSlice({
  name: 'project',
  initialState,
  reducers: {
    loadProjectStart: (state, action: PayloadAction<{ path: string }>) => {
      if (!state.currentProject || state.currentProject.path !== action.payload.path) {
        state.currentProject = {
          name: null, // Will be filled upon successful load
          path: action.payload.path,
          files: [],
          lastAccessed: null,
          isLoading: true,
          error: null,
        };
      } else {
        state.currentProject.isLoading = true;
        state.currentProject.error = null;
      }
    },
    loadProjectSuccess: (state, action: PayloadAction<{ name: string; path: string; description?: string; files?: ProjectFile[] }>) => {
      if (state.currentProject && state.currentProject.path === action.payload.path) {
        state.currentProject.name = action.payload.name;
        state.currentProject.description = action.payload.description;
        state.currentProject.files = action.payload.files || [];
        state.currentProject.lastAccessed = new Date().toISOString();
        state.currentProject.isLoading = false;
        state.currentProject.error = null;

        // Update recent projects
        const existingIndex = state.recentProjects.findIndex(p => p.path === action.payload.path);
        if (existingIndex > -1) {
          state.recentProjects.splice(existingIndex, 1);
        }
        state.recentProjects.unshift({ name: action.payload.name, path: action.payload.path, lastAccessed: new Date().toISOString() });
        if (state.recentProjects.length > 10) { // Keep only last 10
          state.recentProjects.pop();
        }
      }
    },
    loadProjectFailure: (state, action: PayloadAction<{ path: string; error: string }>) => {
      if (state.currentProject && state.currentProject.path === action.payload.path) {
        state.currentProject.isLoading = false;
        state.currentProject.error = action.payload.error;
      }
      // Optionally, clear currentProject if load fails completely or set a generic error state
      // state.currentProject = null;
    },
    createProjectSuccess: (state, action: PayloadAction<{ name: string; path: string; description?: string }>) => {
        state.currentProject = {
            name: action.payload.name,
            path: action.payload.path,
            description: action.payload.description,
            files: [],
            lastAccessed: new Date().toISOString(),
            isLoading: false,
            error: null,
        };
        // Add to recent projects as well
        state.recentProjects.unshift({ name: action.payload.name, path: action.payload.path, lastAccessed: new Date().toISOString() });
        if (state.recentProjects.length > 10) state.recentProjects.pop();
    },
    closeProject: (state) => {
      state.currentProject = null;
    },
    addProjectFile: (state, action: PayloadAction<ProjectFile>) => {
      if (state.currentProject) {
        state.currentProject.files.push(action.payload);
      }
    },
    removeProjectFile: (state, action: PayloadAction<string>) => { // path of the file
      if (state.currentProject) {
        state.currentProject.files = state.currentProject.files.filter(f => f.path !== action.payload);
      }
    },
    setRecentProjects: (state, action: PayloadAction<Array<{ name: string; path: string; lastAccessed: string }>>) => {
        state.recentProjects = action.payload;
    }
  },
});

export const {
  loadProjectStart,
  loadProjectSuccess,
  loadProjectFailure,
  createProjectSuccess,
  closeProject,
  addProjectFile,
  removeProjectFile,
  setRecentProjects,
} = projectSlice.actions;

// Selectors
export const selectCurrentProject = (state: RootState) => state.project.currentProject;
export const selectRecentProjects = (state: RootState) => state.project.recentProjects;
export const selectProjectLoading = (state: RootState) => state.project.currentProject?.isLoading ?? false;
export const selectProjectError = (state: RootState) => state.project.currentProject?.error;

export default projectSlice.reducer;
