// This file can augment existing Electron types or define custom types for your app.

// Augment the global Window interface to include the API exposed by preload.ts
declare global {
  interface Window {
    electronAPI: ElectronAPIType; // Use the specific type defined below
    isElectron: boolean; // Flag to check if running in Electron
  }
}

// Define the structure of the API exposed from preload.ts to the renderer process.
// This should match the `exposedAPI` object in `electron/preload.ts`.
export interface ElectronAPIType {
  // Dialogs
  selectFolder: () => Promise<string | null>;
  selectFile: (options: Electron.OpenDialogOptions) => Promise<string | null>;
  saveFile: (options: Electron.SaveDialogOptions) => Promise<string | null>;
  showMessageBox: (options: Electron.MessageBoxOptions) => Promise<Electron.MessageBoxReturnValue>;
  showErrorBox: (title: string, content: string) => Promise<void>;

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
  openPathInExplorer: (itemPath: string) => Promise<{ success: boolean; error?: string }>;
  showItemInFolder: (fullPath: string) => Promise<void>;

  // System Info
  getSystemInfo: () => Promise<SystemInformation>; // Defined below

  // Backend Process Info & Control
  getBackendStatus: () => Promise<BackendStatusInfo>; // Defined below
  startBackend: () => Promise<{success: boolean, error?: string}>;
  stopBackend: () => Promise<{success: boolean, error?: string}>;

  // Basic FS Operations
  fsExists: (filePath: string) => Promise<boolean>;
  fsReadFile: (filePath: string, encoding?: BufferEncoding) => Promise<string | Buffer>;
  fsWriteFile: (filePath: string, content: string | Buffer, encoding?: BufferEncoding) => Promise<void>;
  fsMkdir: (dirPath: string) => Promise<void>;
  fsReadDir: (dirPath: string) => Promise<string[]>;
  fsRemove: (itemPath: string, options?: {recursive?: boolean, force?: boolean}) => Promise<void>;

  // Event Listeners (from main to renderer)
  onNavigate: (callback: (path: string) => void) => () => void;
  onMenuAction: (callback: (action: string, ...args: any[]) => void) => () => void;
  onUpdaterStatus: (callback: (status: UpdaterStatus) => void) => () => void; // Defined below
  onBackendLog: (callback: (log: BackendLogEntry) => void) => () => void; // Defined below

  removeListener: (channel: string, callback: (...args: any[]) => void) => void;
  removeAllListeners: (channel: string) => void;

  getPlatform: () => NodeJS.Platform;
}

// Custom type definitions for complex objects returned by IPC handlers

export interface SystemInformation {
  platform: NodeJS.Platform;
  arch: string;
  nodeVersion: string;
  electronVersion: string;
  chromeVersion: string;
  totalMemoryMB: number;
  freeMemoryMB: number;
  cpus: Array<{ model: string; speed: number }>;
  homedir: string;
  tmpdir: string;
  machineId?: string; // If you decide to use node-machine-id
}

export interface BackendStatusInfo {
  status: 'starting' | 'running' | 'stopped' | 'error' | 'killed';
  port: number;
  pid?: number;
  logs?: string[]; // Array of recent log messages
}

export interface UpdaterStatus {
  message: string;
  error?: string;
  downloaded?: boolean; // True if an update is downloaded and ready to install
  version?: string; // Available version
  progressPercent?: number; // Download progress
}

export interface BackendLogEntry {
    level: 'info' | 'warn' | 'error' | 'debug';
    message: string;
    timestamp?: string; // Optional, if main.ts adds it
}


// This export is necessary for the file to be treated as a module by TypeScript.
export {};
