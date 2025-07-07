import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { RootState } from '../index';
import { AlertColor } from '@mui/material/Alert';

export interface Notification {
  id: string;
  message: string;
  type: AlertColor; // 'success' | 'error' | 'warning' | 'info'
  duration?: number; // Auto hide duration in ms
  details?: string; // Optional additional details for more complex notifications
}

interface NotificationState {
  activeNotifications: Notification[]; // Queue of notifications
}

const initialState: NotificationState = {
  activeNotifications: [],
};

const notificationSlice = createSlice({
  name: 'notifications',
  initialState,
  reducers: {
    addNotification: (state, action: PayloadAction<Omit<Notification, 'id'>>) => {
      const newNotification: Notification = {
        id: `notif_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
        ...action.payload,
      };
      state.activeNotifications.push(newNotification);
      // Optional: Limit the queue size
      // if (state.activeNotifications.length > 5) {
      //   state.activeNotifications.shift(); // Remove the oldest
      // }
    },
    removeNotification: (state, action: PayloadAction<string>) => { // Payload is the ID of the notification to remove
      state.activeNotifications = state.activeNotifications.filter(
        (notification) => notification.id !== action.payload
      );
    },
    clearAllNotifications: (state) => {
      state.activeNotifications = [];
    },
  },
});

export const {
  addNotification,
  removeNotification,
  clearAllNotifications,
} = notificationSlice.actions;

// Selectors
export const selectActiveNotifications = (state: RootState) => state.notifications.activeNotifications;
// If you always display one at a time, you might want a selector for the current one:
export const selectCurrentNotification = (state: RootState): Notification | undefined => state.notifications.activeNotifications[0];


export default notificationSlice.reducer;
