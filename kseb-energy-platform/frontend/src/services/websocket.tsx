import React, { createContext, useContext, useEffect, useRef, ReactNode, useState, useCallback } from 'react';
import { useDispatch } from 'react-redux';
import { io, Socket } from 'socket.io-client';

import { AppDispatch } from '../store'; // Assuming AppDispatch is exported from your store
import {
  updateForecastProgress,
  setForecastCompleted,
  setForecastError,
  setForecastCancelled
} from '../store/slices/demandSlice';
import {
  updateProfileProgress,
  setProfileCompleted,
  setProfileError,
  setProfileCancelled
} from '../store/slices/loadProfileSlice';
import {
  updateOptimizationProgress,
  setOptimizationCompleted,
  setOptimizationError,
  setOptimizationCancelled
} from '../store/slices/pypsaSlice';
import {
  addNotification,
  Notification // Import Notification type if not already globally available
} from '../store/slices/notificationSlice';

interface WebSocketContextType {
  socket: Socket | null;
  isConnected: boolean;
  joinRoom: (roomId: string) => void;
  leaveRoom: (roomId: string) => void;
  emitEvent: <T = any>(event: string, data: T) => void; // Renamed from 'emit' to avoid conflict
}

const WebSocketContext = createContext<WebSocketContextType | null>(null);

interface WebSocketProviderProps {
  children: ReactNode;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const socketRef = useRef<Socket | null>(null);
  const dispatch = useDispatch<AppDispatch>();
  const [isConnected, setIsConnected] = useState(false);

  const showNotification = useCallback((notification: Omit<Notification, 'id'>) => {
    dispatch(addNotification(notification));
  }, [dispatch]);

  useEffect(() => {
    const socketUrl = process.env.REACT_APP_WS_URL || 'http://localhost:5000';

    socketRef.current = io(socketUrl, {
      transports: ['websocket', 'polling'],
      autoConnect: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 3000,
    });

    const socket = socketRef.current;

    socket.on('connect', () => {
      console.log('WebSocket connected:', socket.id);
      setIsConnected(true);
      showNotification({ type: 'success', message: 'Connected to real-time server.', duration: 3000 });
    });

    socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
      setIsConnected(false);
      if (reason === 'io server disconnect') {
        // the disconnection was initiated by the server, you need to reconnect manually
        socket.connect();
      }
      showNotification({ type: 'warning', message: 'Disconnected from real-time server.', duration: 5000 });
    });

    socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      setIsConnected(false);
      showNotification({ type: 'error', message: `Failed to connect to server: ${error.message}`, duration: 7000 });
    });

    // Demand projection events
    socket.on('forecast-progress', (data) => {
      dispatch(updateForecastProgress(data));
    });
    socket.on('forecast-completed', (data) => {
      dispatch(setForecastCompleted(data));
      showNotification({ type: 'success', message: `Forecast ${data.forecastId} completed.`, duration: 5000 });
    });
    socket.on('forecast-error', (data) => {
      dispatch(setForecastError(data));
      showNotification({ type: 'error', message: `Forecast ${data.forecastId} failed: ${data.error}`, duration: 7000 });
    });
    socket.on('forecast-cancelled', (data) => {
      dispatch(setForecastCancelled(data));
      showNotification({ type: 'info', message: `Forecast ${data.forecastId} was cancelled.`, duration: 5000 });
    });
     socket.on('forecast-status', (data) => { // General status update
        if (data.status === 'running' && data.progress !== undefined) {
            dispatch(updateForecastProgress(data));
        } else if (data.status === 'completed') {
            dispatch(setForecastCompleted(data));
        } else if (data.status === 'failed') {
            dispatch(setForecastError(data));
        } else if (data.status === 'cancelled') {
            dispatch(setForecastCancelled(data));
        }
        // Potentially show a less intrusive notification for general status updates if needed
    });


    // Load profile events
    socket.on('profile-progress', (data) => {
      dispatch(updateProfileProgress(data));
    });
    socket.on('profile-generated', (data) => { // Assuming 'profile-generated' is the completion event
      dispatch(setProfileCompleted({ profileJobId: data.profileJobId, result: data.result }));
      showNotification({ type: 'success', message: `Profile (Job ID: ${data.profileJobId}) generated.`, duration: 5000 });
    });
    socket.on('profile-error', (data) => {
      dispatch(setProfileError({ profileJobId: data.profileJobId, error: data.error }));
      showNotification({ type: 'error', message: `Profile generation (Job ID: ${data.profileJobId}) failed: ${data.error}`, duration: 7000 });
    });
    socket.on('profile-cancelled', (data) => {
        dispatch(setProfileCancelled({profileJobId: data.profileJobId}));
        showNotification({ type: 'info', message: `Profile generation (Job ID: ${data.profileJobId}) was cancelled.`, duration: 5000 });
    });
    socket.on('profile-generation-status', (data) => { // General status update
        if (data.status === 'running' && data.progress !== undefined) {
            dispatch(updateProfileProgress(data));
        } else if (data.status === 'completed') {
            dispatch(setProfileCompleted({ profileJobId: data.profileJobId, result: data.result }));
        } else if (data.status === 'failed') {
            dispatch(setProfileError({ profileJobId: data.profileJobId, error: data.error }));
        } else if (data.status === 'cancelled') {
            dispatch(setProfileCancelled({profileJobId: data.profileJobId}));
        }
    });


    // PyPSA events
    socket.on('pypsa-progress', (data) => {
      dispatch(updateOptimizationProgress(data));
    });
    socket.on('pypsa-completed', (data) => {
      dispatch(setOptimizationCompleted(data));
      showNotification({ type: 'success', message: `PyPSA optimization ${data.jobId} completed.`, duration: 5000 });
    });
    socket.on('pypsa-error', (data) => {
      dispatch(setOptimizationError(data));
      showNotification({ type: 'error', message: `PyPSA optimization ${data.jobId} failed: ${data.error}`, duration: 7000 });
    });
    socket.on('pypsa-cancelled', (data) => {
        dispatch(setOptimizationCancelled(data));
        showNotification({ type: 'info', message: `PyPSA optimization ${data.jobId} was cancelled.`, duration: 5000 });
    });
    socket.on('pypsa-job-status', (data) => { // General status update
        if (data.status === 'running' && data.progress !== undefined) {
            dispatch(updateOptimizationProgress(data));
        } else if (data.status === 'completed') {
            dispatch(setOptimizationCompleted(data));
        } else if (data.status === 'failed') {
            dispatch(setOptimizationError(data));
        } else if (data.status === 'cancelled') {
            dispatch(setOptimizationCancelled(data));
        }
    });

    // General notification from backend
    socket.on('server-notification', (data: Omit<Notification, 'id'>) => {
        showNotification(data);
    });


    return () => {
      if (socketRef.current) {
        console.log('Disconnecting WebSocket...');
        socketRef.current.disconnect();
      }
    };
  }, [dispatch, showNotification]);

  const joinRoom = useCallback((roomId: string) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit('join-room', roomId);
      console.log(`Attempted to join room: ${roomId}`);
    } else {
      console.warn(`Socket not connected. Cannot join room: ${roomId}`);
    }
  }, []);

  const leaveRoom = useCallback((roomId: string) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit('leave-room', roomId);
      console.log(`Attempted to leave room: ${roomId}`);
    }
  }, []);

  const emitEvent = useCallback(<T = any>(event: string, data: T) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit(event, data);
    } else {
      console.warn(`Socket not connected. Cannot emit event '${event}'.`);
    }
  }, []);

  const contextValue: WebSocketContextType = {
    socket: socketRef.current,
    isConnected,
    joinRoom,
    leaveRoom,
    emitEvent,
  };

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = (): WebSocketContextType => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};

// Specific hooks for joining/leaving rooms based on job IDs
// These hooks simplify component logic for subscribing to specific job updates.

export const useForecastNotifications = (forecastId: string | null | undefined) => {
  const { joinRoom, leaveRoom } = useWebSocket();
  useEffect(() => {
    const roomName = `forecast-${forecastId}`;
    if (forecastId) {
      joinRoom(roomName);
      return () => leaveRoom(roomName);
    }
  }, [forecastId, joinRoom, leaveRoom]);
};

export const useProfileNotifications = (profileJobId: string | null | undefined) => {
  const { joinRoom, leaveRoom } = useWebSocket();
   useEffect(() => {
    const roomName = `profile-job-${profileJobId}`;
    if (profileJobId) {
      joinRoom(roomName);
      return () => leaveRoom(roomName);
    }
  }, [profileJobId, joinRoom, leaveRoom]);
};

export const usePyPSANotifications = (jobId: string | null | undefined) => {
  const { joinRoom, leaveRoom } = useWebSocket();
  useEffect(() => {
    const roomName = `pypsa-job-${jobId}`;
    if (jobId) {
      joinRoom(roomName);
      return () => leaveRoom(roomName);
    }
  }, [jobId, joinRoom, leaveRoom]);
};
