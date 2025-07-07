import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { RootState } from '../index';

type ThemeMode = 'light' | 'dark' | 'system';

interface ModalState {
  isOpen: boolean;
  type: string | null; // e.g., 'confirmAction', 'editItem', 'viewDetails'
  data?: any; // Optional data to pass to the modal
}

interface UIState {
  isLoading: boolean; // Global loading indicator state
  loadingMessage: string | null;
  theme: ThemeMode;
  modal: ModalState;
  sidebarOpen: boolean; // For collapsible sidebar
}

const initialState: UIState = {
  isLoading: false,
  loadingMessage: null,
  theme: 'light', // Default theme
  modal: {
    isOpen: false,
    type: null,
    data: null,
  },
  sidebarOpen: true, // Assuming sidebar is open by default on larger screens
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    setGlobalLoading: (state, action: PayloadAction<boolean | { status: boolean; message?: string }>) => {
      if (typeof action.payload === 'boolean') {
        state.isLoading = action.payload;
        if (!action.payload) {
          state.loadingMessage = null;
        }
      } else {
        state.isLoading = action.payload.status;
        state.loadingMessage = action.payload.message || null;
        if (!action.payload.status) {
          state.loadingMessage = null;
        }
      }
    },
    setLoadingMessage: (state, action: PayloadAction<string | null>) => {
        state.loadingMessage = action.payload;
    },
    setTheme: (state, action: PayloadAction<ThemeMode>) => {
      state.theme = action.payload;
      // Potentially save to localStorage here
    },
    openModal: (state, action: PayloadAction<{ type: string; data?: any }>) => {
      state.modal.isOpen = true;
      state.modal.type = action.payload.type;
      state.modal.data = action.payload.data || null;
    },
    closeModal: (state) => {
      state.modal.isOpen = false;
      state.modal.type = null;
      state.modal.data = null;
    },
    toggleSidebar: (state) => {
      state.sidebarOpen = !state.sidebarOpen;
    },
    setSidebarOpen: (state, action: PayloadAction<boolean>) => {
      state.sidebarOpen = action.payload;
    },
  },
});

export const {
  setGlobalLoading,
  setLoadingMessage,
  setTheme,
  openModal,
  closeModal,
  toggleSidebar,
  setSidebarOpen,
} = uiSlice.actions;

// Selectors
export const selectIsLoading = (state: RootState) => state.ui.isLoading;
export const selectLoadingMessage = (state: RootState) => state.ui.loadingMessage;
export const selectTheme = (state: RootState) => state.ui.theme;
export const selectModalState = (state: RootState) => state.ui.modal;
export const selectIsSidebarOpen = (state: RootState) => state.ui.sidebarOpen;

export default uiSlice.reducer;
