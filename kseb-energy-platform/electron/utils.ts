// This file can contain utility functions specific to the Electron main or preload processes.
// For now, it can be a placeholder or include very generic utilities if needed.

/**
 * Example utility function for the Electron environment.
 * This is just a placeholder.
 * @param ms Milliseconds to wait.
 * @returns A Promise that resolves after the specified time.
 */
export const delay = (ms: number): Promise<void> => {
  return new Promise(resolve => setTimeout(resolve, ms));
};

/**
 * Checks if the current environment is development based on electron-is-dev.
 * Note: `electron-is-dev` is typically used in the main process.
 * If needed in preload for some reason, ensure it's bundled or handled appropriately.
 * For direct use in preload, `process.env.NODE_ENV` might be more straightforward if set.
 */
export const isDevelopmentEnvironment = (): boolean => {
  // In preload, `process.env.NODE_ENV` might be more reliable if set by your build process for preload.
  // Or, you could expose `isDev` from the main process via `ipcRenderer.invoke`.
  // For simplicity, if this util is for main process context:
  // import * as isDev from 'electron-is-dev';
  // return isDev;
  return process.env.NODE_ENV === 'development';
};

/**
 * Formats a file path for display, potentially shortening long paths.
 * @param filePath The full file path.
 * @param maxLength Max length before shortening.
 * @returns Formatted file path string.
 */
export const formatDisplayPath = (filePath: string, maxLength: number = 50): string => {
  if (filePath.length <= maxLength) {
    return filePath;
  }
  const startLength = Math.floor(maxLength * 0.6);
  const endLength = maxLength - startLength - 3; // 3 for "..."
  return `${filePath.substring(0, startLength)}...${filePath.substring(filePath.length - endLength)}`;
};


// Add other Electron-specific utility functions here as the application grows.
// For example, functions to manage application data paths, settings persistence using electron-store, etc.

export default {
  delay,
  isDevelopmentEnvironment,
  formatDisplayPath,
};
