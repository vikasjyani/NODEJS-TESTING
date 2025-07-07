import React from 'react';
import { Snackbar, Alert, AlertColor, IconButton } from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
// import { useSelector, useDispatch } from 'react-redux'; // If using Redux for notifications
// import { RootState, AppDispatch } from '../../store'; // Path to your RootState and AppDispatch types
// import { removeNotification } from '../../store/slices/notificationSlice'; // Example action

export interface Notification {
  id: string;
  message: string;
  type: AlertColor; // 'success' | 'error' | 'warning' | 'info'
  duration?: number; // Auto hide duration in ms
  details?: string; // Optional additional details
}

interface NotificationManagerProps {
  // Props can be added if notifications are not managed by Redux
}

export const NotificationManager: React.FC<NotificationManagerProps> = () => {
  // Example: If using Redux to manage notifications
  // const notifications = useSelector((state: RootState) => state.notifications.activeNotifications);
  // const dispatch: AppDispatch = useDispatch();

  // For now, let's use a placeholder for demonstration if not using Redux yet.
  // This local state would be replaced by Redux state.
  const [notifications, setNotifications] = React.useState<Notification[]>([]);

  // Example function to add a notification (would be a Redux action dispatch)
  // const addDemoNotification = () => {
  //   setNotifications(prev => [...prev, {
  //     id: `demo-${Date.now()}`,
  //     message: "This is a demo notification!",
  //     type: 'info',
  //     duration: 3000
  //   }]);
  // };
  // React.useEffect(() => { // To show a demo notification
  //    const timer = setTimeout(addDemoNotification, 2000);
  //    return () => clearTimeout(timer);
  // }, []);


  const handleClose = (id: string, reason?: string) => {
    if (reason === 'clickaway') {
      return;
    }
    // If using Redux:
    // dispatch(removeNotification(id));

    // If using local state:
    setNotifications((prevNotifications) => prevNotifications.filter(n => n.id !== id));
  };

  if (!notifications || notifications.length === 0) {
    return null;
  }

  // Display only the first notification in the queue (Material-UI Snackbar pattern)
  // For multiple stacked notifications, a more complex solution or a library like 'notistack' would be better.
  const currentNotification = notifications[0];

  return (
    <Snackbar
      key={currentNotification.id}
      anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      open={true} // Snackbar is open as long as there's a currentNotification
      autoHideDuration={currentNotification.duration || 6000}
      onClose={(event, reason) => handleClose(currentNotification.id, reason)}
      // TransitionComponent={Slide} // Optional transition
    >
      <Alert
        onClose={() => handleClose(currentNotification.id)}
        severity={currentNotification.type}
        variant="filled"
        sx={{ width: '100%', boxShadow: 6 }}
        action={
          <IconButton
            aria-label="close"
            color="inherit"
            size="small"
            onClick={() => handleClose(currentNotification.id)}
          >
            <CloseIcon fontSize="inherit" />
          </IconButton>
        }
      >
        {currentNotification.message}
        {currentNotification.details && (
            <Typography variant="caption" display="block" sx={{ mt: 1}}>
                {currentNotification.details}
            </Typography>
        )}
      </Alert>
    </Snackbar>
  );
};
