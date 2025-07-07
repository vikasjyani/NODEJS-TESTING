import { useEffect } from 'react';
import { useWebSocket } from '../services/websocket'; // Assuming websocket.tsx exports this

/**
 * Custom hook to manage joining and leaving a WebSocket room for forecast progress.
 * @param forecastId The ID of the forecast to track. Null or undefined to leave/not join.
 */
export const useForecastProgressTracking = (forecastId: string | null | undefined): void => {
  const { joinRoom, leaveRoom, isConnected } = useWebSocket();

  useEffect(() => {
    if (forecastId && isConnected) {
      const roomName = `forecast-${forecastId}`;
      joinRoom(roomName);
      // console.log(`Joined forecast room: ${roomName}`);
      return () => {
        leaveRoom(roomName);
        // console.log(`Left forecast room: ${roomName}`);
      };
    }
  }, [forecastId, joinRoom, leaveRoom, isConnected]);
};

/**
 * Custom hook to manage joining and leaving a WebSocket room for load profile generation progress.
 * @param profileJobId The ID of the load profile generation job to track. Null or undefined to leave/not join.
 */
export const useProfileProgressTracking = (profileJobId: string | null | undefined): void => {
  const { joinRoom, leaveRoom, isConnected } = useWebSocket();

  useEffect(() => {
    if (profileJobId && isConnected) {
      const roomName = `profile-job-${profileJobId}`; // Align with room name on server
      joinRoom(roomName);
      // console.log(`Joined profile job room: ${roomName}`);
      return () => {
        leaveRoom(roomName);
        // console.log(`Left profile job room: ${roomName}`);
      };
    }
  }, [profileJobId, joinRoom, leaveRoom, isConnected]);
};

/**
 * Custom hook to manage joining and leaving a WebSocket room for PyPSA optimization progress.
 * @param jobId The ID of the PyPSA optimization job to track. Null or undefined to leave/not join.
 */
export const usePyPSAProgressTracking = (jobId: string | null | undefined): void => {
  const { joinRoom, leaveRoom, isConnected } = useWebSocket();

  useEffect(() => {
    if (jobId && isConnected) {
      const roomName = `pypsa-job-${jobId}`; // Align with room name on server
      joinRoom(roomName);
      // console.log(`Joined PyPSA job room: ${roomName}`);
      return () => {
        leaveRoom(roomName);
        // console.log(`Left PyPSA job room: ${roomName}`);
      };
    }
  }, [jobId, joinRoom, leaveRoom, isConnected]);
};

/**
 * A generic progress tracking hook if room naming conventions are consistent.
 * @param jobType Type of the job (e.g., 'forecast', 'profile', 'pypsa').
 * @param jobId The ID of the job.
 */
export const useGenericJobProgressTracking = (jobType: string, jobId: string | null | undefined): void => {
    const { joinRoom, leaveRoom, isConnected } = useWebSocket();

    useEffect(() => {
        if (jobId && jobType && isConnected) {
            const roomName = `${jobType}-job-${jobId}`; // Example generic room name
            joinRoom(roomName);
            return () => {
                leaveRoom(roomName);
            };
        }
    }, [jobType, jobId, joinRoom, leaveRoom, isConnected]);
};
