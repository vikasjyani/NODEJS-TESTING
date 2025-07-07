import React from 'react';
import { Backdrop, CircularProgress, Typography, Box } from '@mui/material';
// import { useSelector } from 'react-redux'; // If using Redux for global loading state
// import { RootState } from '../../store'; // Path to your RootState type

interface LoadingOverlayProps {
  open?: boolean; // Allow manual control via prop
  message?: string;
}

export const LoadingOverlay: React.FC<LoadingOverlayProps> = ({
  open: controlledOpen,
  message = "Loading..."
}) => {
  // Example: If using Redux to control global loading state
  // const isLoadingFromStore = useSelector((state: RootState) => state.ui.isLoading);
  // const loadingMessageFromStore = useSelector((state: RootState) => state.ui.loadingMessage);

  // Determine if overlay should be open
  // If 'open' prop is provided, it takes precedence. Otherwise, use store.
  // const isOpen = controlledOpen !== undefined ? controlledOpen : isLoadingFromStore;
  // const displayMessage = controlledOpen !== undefined ? message : (loadingMessageFromStore || message);

  // For now, let's make it controllable via props or a simple local state for demonstration
  // In a real app, this would likely be driven by a global state (Redux, Context API)
  const [localOpen, setLocalOpen] = React.useState(false); // Example local control

  // Determine if overlay should be open:
  // If 'controlledOpen' prop is provided, it takes precedence.
  // Otherwise, this component would typically subscribe to a global loading state (e.g., from Redux).
  // For this placeholder, we'll assume 'controlledOpen' is the primary way or it's managed elsewhere.
  const isOpen = controlledOpen !== undefined ? controlledOpen : false; // Default to false if not controlled by Redux yet
  const displayMessage = message;


  // This is just to demonstrate how it might look when active.
  // Remove this useEffect if you control 'open' from outside or via Redux.
  // useEffect(() => {
  //   if (controlledOpen === undefined) { // Only use local toggle if not controlled
  //     setLocalOpen(true);
  //     const timer = setTimeout(() => setLocalOpen(false), 3000); // Show for 3s
  //     return () => clearTimeout(timer);
  //   }
  // }, [controlledOpen]);
  // const isOpen = controlledOpen !== undefined ? controlledOpen : localOpen;


  if (!isOpen) {
    return null;
  }

  return (
    <Backdrop
      sx={{
        color: '#fff',
        zIndex: (theme) => theme.zIndex.drawer + 100, // Ensure it's above other elements like drawers/modals
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center'
      }}
      open={isOpen}
      // onClick={handleClose} // Optional: close on click
    >
      <CircularProgress color="inherit" size={60} thickness={4} />
      {displayMessage && (
        <Typography variant="h6" component="div" sx={{ mt: 2 }}>
          {displayMessage}
        </Typography>
      )}
    </Backdrop>
  );
};
