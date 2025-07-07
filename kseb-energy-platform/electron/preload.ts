import { contextBridge, ipcRenderer, IpcRendererEvent } from 'electron';

// Define the shape of the API exposed to the renderer process
// This should mirror the handlers set up in `electron/main.ts` using `ipcMain.handle` or `ipcMain.on`
export interface ElectronAPI {
  // Dialogs
  selectFolder: () => Promise<string | null>;
  selectFile: (options: Electron.OpenDialogOptions) => Promise<string | null>;
  saveFile: (options: Electron.SaveDialogOptions) => Promise<string | null>;
  showMessageBox: (options: Electron.MessageBoxOptions) => Promise<Electron.MessageBoxReturnValue>;
  showErrorBox: (title: string, content: string) => Promise<void>; // Note: showErrorBox in main doesn't return promise

  // App Info & Control
  getVersion: () => Promise<string>;
  isDev: () => Promise<boolean>;
  relaunchApp: () => Promise<void>;
  quitApp: () => Promise<void>;

  // Window Control
  minimizeWindow: () => Promise<void>;
  maximizeWindow: () => Promise<void>;
  closeWindow: () => Promise<void>;
  toggleFullscreen: () => Promise<void>;

  // Shell Operations
  openExternalLink: (url: string) => Promise<{ success: boolean; error?: string }>;
  openPathInExplorer: (itemPath: string) => Promise<{ success: boolean; error?: string }>; // Changed name for clarity
  showItemInFolder: (fullPath: string) => Promise<void>; // shell.showItemInFolder doesn't return a promise directly

  // System Info
  getSystemInfo: () => Promise<any>; // Define a more specific type in electron.d.ts

  // Backend Process Info & Control
  getBackendStatus: () => Promise<{ status: string; port: number; pid?: number, logs?: string[] }>;
  startBackend: () => Promise<{success: boolean, error?: string}>;
  stopBackend: () => Promise<{success: boolean, error?: string}>;

  // Basic FS Operations (use with caution from renderer)
  fsExists: (filePath: string) => Promise<boolean>;
  fsReadFile: (filePath: string, encoding?: BufferEncoding) => Promise<string | Buffer>; // Can be string or buffer
  fsWriteFile: (filePath: string, content: string | Buffer, encoding?: BufferEncoding) => Promise<void>;
  fsMkdir: (dirPath: string) => Promise<void>;
  fsReadDir: (dirPath: string) => Promise<string[]>;
  fsRemove: (itemPath: string, options?: {recursive?: boolean, force?: boolean}) => Promise<void>;


  // Event Listeners (from main to renderer)
  onNavigate: (callback: (path: string) => void) => () => void; // Returns an unlisten function
  onMenuAction: (callback: (action: string, ...args: any[]) => void) => () => void;
  onUpdaterStatus: (callback: (status: { message: string; error?: string; downloaded?: boolean }) => void) => () => void;
  onBackendLog: (callback: (log: {level: string, message: string}) => void) => () => void;
  // Add more listeners as needed

  // Function to remove a specific listener, or all listeners for a channel
  removeListener: (channel: string, callback: (...args: any[]) => void) => void;
  removeAllListeners: (channel: string) => void;

  // Platform info (synchronous example, could also be async via invoke)
  getPlatform: () => NodeJS.Platform; // Direct access to process.platform
}

const exposedAPI: ElectronAPI = {
  // Dialogs
  selectFolder: () => ipcRenderer.invoke('dialog:selectFolder'),
  selectFile: (options) => ipcRenderer.invoke('dialog:selectFile', options),
  saveFile: (options) => ipcRenderer.invoke('dialog:saveFile', options),
  showMessageBox: (options) => ipcRenderer.invoke('dialog:showMessageBox', options),
  showErrorBox: (title, content) => ipcRenderer.invoke('dialog:showErrorBox', { title, content }), // Wrap args

  // App Info & Control
  getVersion: () => ipcRenderer.invoke('app:getVersion'),
  isDev: () => ipcRenderer.invoke('app:isDev'),
  relaunchApp: () => ipcRenderer.invoke('app:relaunch'),
  quitApp: () => ipcRenderer.invoke('app:quit'),

  // Window Control
  minimizeWindow: () => ipcRenderer.invoke('window:minimize'),
  maximizeWindow: () => ipcRenderer.invoke('window:maximize'),
  closeWindow: () => ipcRenderer.invoke('window:close'),
  toggleFullscreen: () => ipcRenderer.invoke('window:toggleFullscreen'),

  // Shell Operations
  openExternalLink: (url) => ipcRenderer.invoke('shell:openExternal', url),
  openPathInExplorer: (itemPath) => ipcRenderer.invoke('shell:openPath', itemPath),
  showItemInFolder: (fullPath) => ipcRenderer.invoke('shell:showItemInFolder', fullPath),

  // System Info
  getSystemInfo: () => ipcRenderer.invoke('system:getSysInfo'),

  // Backend Process Info & Control
  getBackendStatus: () => ipcRenderer.invoke('backend:getStatus'),
  startBackend: () => ipcRenderer.invoke('backend:start'),
  stopBackend: () => ipcRenderer.invoke('backend:stop'),

  // Basic FS Operations
  fsExists: (filePath) => ipcRenderer.invoke('fs:exists', filePath),
  fsReadFile: (filePath, encoding) => ipcRenderer.invoke('fs:readFile', filePath, encoding),
  fsWriteFile: (filePath, content, encoding) => ipcRenderer.invoke('fs:writeFile', filePath, content, encoding),
  fsMkdir: (dirPath) => ipcRenderer.invoke('fs:mkdir', dirPath),
  fsReadDir: (dirPath) => ipcRenderer.invoke('fs:readdir', dirPath),
  fsRemove: (itemPath, options) => ipcRenderer.invoke('fs:rm', itemPath, options),


  // Event Listeners (from main to renderer)
  // These functions set up an IPC listener and return a function to remove that specific listener.
  onNavigate: (callback) => {
    const handler = (_: IpcRendererEvent, path: string) => callback(path);
    ipcRenderer.on('navigate', handler);
    return () => ipcRenderer.removeListener('navigate', handler);
  },
  onMenuAction: (callback) => {
    const handler = (_: IpcRendererEvent, action: string, ...args: any[]) => callback(action, ...args);
    ipcRenderer.on('menu-action', handler);
    return () => ipcRenderer.removeListener('menu-action', handler);
  },
  onUpdaterStatus: (callback) => {
    const handler = (_: IpcRendererEvent, statusUpdate: { message: string; error?: string; downloaded?: boolean }) => callback(statusUpdate);
    ipcRenderer.on('updater-status', handler);
    return () => ipcRenderer.removeListener('updater-status', handler);
  },
  onBackendLog: (callback) => {
    const handler = (_: IpcRendererEvent, logEntry: {level: string, message: string}) => callback(logEntry);
    ipcRenderer.on('backend-log', handler);
    return () => ipcRenderer.removeListener('backend-log', handler);
  },

  removeListener: (channel, callback) => {
      ipcRenderer.removeListener(channel, callback);
  },
  removeAllListeners: (channel) => {
      ipcRenderer.removeAllListeners(channel);
  },

  getPlatform: () => process.platform, // Expose platform directly
};

// Securely expose the API to the renderer process
try {
  contextBridge.exposeInMainWorld('electronAPI', exposedAPI);
  // Also expose a simple boolean flag for easier checking in renderer
  contextBridge.exposeInMainWorld('isElectron', true);
} catch (error) {
  console.error("Failed to expose electronAPI to main world:", error);
}


// It's good practice to clean up any potentially dangerous globals that might have been
// injected by a compromised script in the renderer, though with contextIsolation=true,
// this is less of a direct risk to the preload script itself.
window.addEventListener('DOMContentLoaded', () => {
  // Example: delete (window as any).require;
});

// Global error handlers in preload can catch errors within preload itself
process.on('uncaughtException', (error) => {
    console.error('Preload Uncaught Exception:', error);
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('Preload Unhandled Rejection at:', promise, 'reason:', reason);
});
