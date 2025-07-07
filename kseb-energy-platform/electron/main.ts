import { app, BrowserWindow, ipcMain, dialog, shell, Menu, MenuItemConstructorOptions, Tray, nativeImage } from 'electron';
import * as path from 'path';
import * as isDev from 'electron-is-dev';
import { autoUpdater } from 'electron-updater';
import { spawn, ChildProcess, execSync } from 'child_process';
import * as fs from 'fs';
import * as os from 'os';
// import { machineIdSync } from 'node-machine-id'; // Optional: for unique machine ID

interface BackendProcess {
  process: ChildProcess | null;
  port: number;
  status: 'starting' | 'running' | 'stopped' | 'error' | 'killed';
  logs: string[]; // Store recent logs
}

const MAX_LOG_LINES = 100;

class ElectronApp {
  private mainWindow: BrowserWindow | null = null;
  private tray: Tray | null = null;
  private backend: BackendProcess = {
    process: null,
    port: parseInt(process.env.BACKEND_PORT || '5000', 10), // Ensure backend port is configurable
    status: 'stopped',
    logs: [],
  };
  private readonly isMac = process.platform === 'darwin';
  private readonly isWindows = process.platform === 'win32';
  private readonly isLinux = process.platform === 'linux';


  constructor() {
    this.ensureSingleInstance();
    this.setupApp();
    this.setupIPC();
    // Menu setup is deferred until app is ready and backend potentially started
    // this.setupAutoUpdater(); // Auto-updater setup also deferred
  }

  private logToBackend(level: 'info' | 'warn' | 'error', message: string) {
    this.backend.logs.push(`[${new Date().toISOString()}] [${level.toUpperCase()}] ${message}`);
    if (this.backend.logs.length > MAX_LOG_LINES) {
      this.backend.logs.shift();
    }
    // Optionally, send to mainWindow if it exists and is listening
    this.mainWindow?.webContents.send('backend-log', {level, message});
  }

  private ensureSingleInstance(): void {
    const gotTheLock = app.requestSingleInstanceLock();
    if (!gotTheLock) {
      app.quit();
    } else {
      app.on('second-instance', (event, commandLine, workingDirectory) => {
        if (this.mainWindow) {
          if (this.mainWindow.isMinimized()) this.mainWindow.restore();
          this.mainWindow.focus();
        }
      });
    }
  }

  private setupApp(): void {
    if (this.isWindows) {
      app.setAppUserModelId('in.gov.kseb.energyfuturesplatform'); // Unique App ID
    }

    app.on('ready', async () => {
      try {
        await this.startBackendServer();
        this.createMainWindow();
        this.setupMenu(); // Setup menu after window creation
        this.setupTray();
        this.setupAutoUpdater(); // Setup auto-updater after app is ready
      } catch (error) {
          console.error("Error during app initialization:", error);
          dialog.showErrorBox("Initialization Error", `Failed to start critical services: ${(error as Error).message}. The application might not work correctly.`);
          // Optionally, still create main window with an error message or quit
          if (!this.mainWindow) this.createMainWindow(true); // Create window with error flag
      }
    });

    app.on('window-all-closed', () => {
      // On macOS it is common for applications and their menu bar
      // to stay active until the user quits explicitly with Cmd + Q
      if (!this.isMac) {
        this.cleanupAndQuit();
      }
    });

    app.on('activate', () => {
      // On macOS it's common to re-create a window in the app when the
      // dock icon is clicked and there are no other windows open.
      if (BrowserWindow.getAllWindows().length === 0) {
        this.createMainWindow();
      }
    });

    app.on('before-quit', (event) => {
        // Perform cleanup before quitting. If cleanup is async, prevent default.
        // For this example, cleanupAndQuit handles it.
        console.log("Application is about to quit.");
    });

    // Prevent new window creation via `window.open` or links with `target="_blank"`
    // and open them in the default browser instead.
    app.on('web-contents-created', (event, contents) => {
      contents.setWindowOpenHandler(({ url }) => {
        // Ask to open in external browser
        shell.openExternal(url);
        return { action: 'deny' };
      });
    });
  }

  private cleanupAndQuit(): void {
    console.log("Running cleanup before quit...");
    this.killBackendServer()
        .then(() => {
            console.log("Backend server stopped or was not running.");
        })
        .catch(err => {
            console.error("Error stopping backend server during quit:", err);
        })
        .finally(() => {
            app.quit(); // Ensure app quits after attempt
        });
  }


  private async startBackendServer(): Promise<void> {
    if (this.backend.process && this.backend.status === 'running') {
        this.logToBackend('info', 'Backend server already running.');
        return Promise.resolve();
    }
    this.logToBackend('info', 'Attempting to start backend server...');
    this.backend.status = 'starting';

    return new Promise((resolve, reject) => {
      const backendDir = isDev ? path.join(__dirname, '../../backend') : path.join(process.resourcesPath, 'app.asar.unpacked', 'backend');
      const backendScript = path.join(backendDir, 'src', 'app.js'); // Assuming structure

      // Check if script exists
      if (!fs.existsSync(backendScript)) {
          const errorMsg = `Backend script not found at ${backendScript}`;
          this.logToBackend('error', errorMsg);
          this.backend.status = 'error';
          return reject(new Error(errorMsg));
      }

      const nodeExecutable = this.getNodeExecutable();
      if (!nodeExecutable) {
          const errorMsg = 'Node.js executable not found.';
          this.logToBackend('error', errorMsg);
          this.backend.status = 'error';
          return reject(new Error(errorMsg));
      }

      this.logToBackend('info', `Using Node: ${nodeExecutable}`);
      this.logToBackend('info', `Backend script: ${backendScript}`);
      this.logToBackend('info', `Backend CWD: ${backendDir}`);


      this.backend.process = spawn(nodeExecutable, [backendScript], {
        cwd: backendDir, // Set CWD to backend's root for relative paths in backend code
        env: {
          ...process.env,
          NODE_ENV: isDev ? 'development' : 'production',
          PORT: this.backend.port.toString(),
          ELECTRON_APP: 'true', // Flag for backend to know it's run by Electron
          PYTHON_PATH: this.getPythonPath(), // Pass Python path to backend
          // RESULTS_DIR: path.join(app.getPath('userData'), 'results'), // Example: store results in userData
          // STORAGE_PATH: path.join(app.getPath('userData'), 'storage'), // Example: store other files
        },
        stdio: ['pipe', 'pipe', 'pipe'], // stdin, stdout, stderr
        // detached: !this.isWindows, // Detach on non-Windows to allow parent to exit independently if needed (usually false for bundled apps)
      });

      let startupTimeout = setTimeout(() => {
        if (this.backend.status === 'starting') {
          const errorMsg = `Backend server startup timed out after 30s on port ${this.backend.port}.`;
          this.logToBackend('error', errorMsg);
          this.backend.status = 'error';
          this.killBackendServer().catch(console.error);
          reject(new Error(errorMsg));
        }
      }, 30000); // 30 seconds timeout

      this.backend.process.stdout?.on('data', (data) => {
        const output = data.toString();
        this.logToBackend('info', `Backend STDOUT: ${output.trim()}`);
        if (output.includes(`Server running on port ${this.backend.port}`)) {
          this.logToBackend('info', 'Backend server confirmed running.');
          this.backend.status = 'running';
          clearTimeout(startupTimeout);
          resolve();
        }
      });

      this.backend.process.stderr?.on('data', (data) => {
        const errorOutput = data.toString();
        this.logToBackend('error', `Backend STDERR: ${errorOutput.trim()}`);
        // Consider rejecting if critical errors occur during startup, but be cautious
      });

      this.backend.process.on('error', (error) => {
        const errorMsg = `Failed to start backend process: ${error.message}`;
        this.logToBackend('error', errorMsg);
        this.backend.status = 'error';
        clearTimeout(startupTimeout);
        reject(new Error(errorMsg));
      });

      this.backend.process.on('exit', (code, signal) => {
        const exitMsg = `Backend process exited with code ${code}, signal ${signal}.`;
        this.logToBackend(code === 0 || signal === 'SIGTERM' ? 'info' : 'warn', exitMsg);
        if (this.backend.status !== 'killed') { // Avoid overriding 'killed' status
            this.backend.status = 'stopped';
        }
        this.backend.process = null;
        clearTimeout(startupTimeout);
        if (this.backend.status === 'starting' && code !== 0) { // If it exits during startup and it wasn't a clean shutdown
             reject(new Error(`Backend process failed to start properly. Exit code: ${code}, Signal: ${signal}`));
        }
      });
    });
  }

  private async killBackendServer(): Promise<void> {
    if (this.backend.process) {
        this.logToBackend('info', 'Attempting to stop backend server...');
        this.backend.status = 'killed'; // Mark as intentionally killed
        return new Promise((resolve, reject) => {
            this.backend.process?.kill('SIGTERM'); // Graceful shutdown
            const timeout = setTimeout(() => {
                if (this.backend.process && !this.backend.process.killed) {
                    this.logToBackend('warn', 'Backend server did not stop gracefully, forcing kill (SIGKILL).');
                    this.backend.process.kill('SIGKILL');
                }
            }, 5000); // 5 seconds for graceful shutdown

            this.backend.process?.on('exit', () => {
                clearTimeout(timeout);
                this.logToBackend('info', 'Backend server process exited.');
                this.backend.process = null;
                resolve();
            });
             this.backend.process?.on('error', (err) => { // Should not happen on kill but good practice
                clearTimeout(timeout);
                this.logToBackend('error', `Error during backend server termination: ${err.message}`);
                this.backend.process = null;
                reject(err);
            });
        });
    }
    return Promise.resolve();
  }


  private getNodeExecutable(): string | null {
    // For development, use 'node' from PATH
    if (isDev) return 'node';

    // For production, point to the bundled Node.js executable
    // The path depends on how electron-builder packages it.
    // Common locations: resources/bin/node, resources/app.asar.unpacked/node_modules/.bin/node
    // This needs to be robust.
    const platform = process.platform;
    const potentialPaths = [
        path.join(process.resourcesPath, 'bin', platform === 'win32' ? 'node.exe' : 'node'),
        path.join(process.resourcesPath, 'app.asar.unpacked', 'node_modules', '.bin', platform === 'win32' ? 'node.cmd' : 'node'), // If packaged within node_modules
        path.join(process.resourcesPath, 'app.asar.unpacked', 'dist', 'server', platform === 'win32' ? 'node.exe' : 'node'), // Custom packaging
        // Fallback: try to find node in system path if bundled one is not found (less ideal for packaged app)
    ];

    for (const p of potentialPaths) {
        if (fs.existsSync(p)) return p;
    }

    // Last resort: check system path (might not be what you want for a bundled app)
    try {
        const nodePath = execSync(platform === 'win32' ? 'where node' : 'which node').toString().trim();
        if (nodePath) return nodePath.split('\n')[0]; // Take the first result
    } catch (e) {
        console.error("Node.js not found via which/where command.", e);
    }

    this.logToBackend('error', 'Node executable not found in expected production paths or system PATH.');
    return null;
  }

  private getPythonPath(): string {
    // For development, use 'python' or 'python3' from PATH
    if (isDev) return process.env.PYTHON_EXECUTABLE || 'python3'; // Or 'python'

    // For production, point to bundled Python if available
    // This path needs to be configured correctly in electron-builder's `extraResources`
    const platform = process.platform;
    const bundledPythonDir = path.join(process.resourcesPath, 'python'); // e.g., extraResources: [{ "from": "python-runtime/win", "to": "python" }]

    let pythonExe = platform === 'win32' ? 'python.exe' : 'bin/python3'; // common structure for embedded python
    if (platform === 'darwin') pythonExe = 'bin/python3'; // macOS often python3

    const fullBundledPath = path.join(bundledPythonDir, pythonExe);

    if (fs.existsSync(fullBundledPath)) {
      return fullBundledPath;
    }

    this.logToBackend('warn', `Bundled Python not found at ${fullBundledPath}. Falling back to system Python.`);
    // Fallback to system path if bundled python is not found
    return process.env.PYTHON_EXECUTABLE || (platform === 'win32' ? 'python' : 'python3');
  }

  private createMainWindow(withError?: boolean): void {
    this.mainWindow = new BrowserWindow({
      width: 1400,
      height: 900,
      minWidth: 1024, // Minimum sensible width
      minHeight: 768, // Minimum sensible height
      webPreferences: {
        nodeIntegration: false, // Best practice for security
        contextIsolation: true, // Best practice for security
        preload: path.join(__dirname, 'preload.js'), // Securely expose IPC
        sandbox: false, // Set to true if renderer doesn't need Node.js/Electron APIs directly (requires careful preload setup)
        devTools: isDev, // Enable DevTools only in development
        webSecurity: !isDev, // Disable webSecurity only if absolutely necessary for local file access in dev (generally not recommended)
      },
      icon: this.getAppIconPath(),
      title: 'KSEB Energy Futures Platform',
      show: false, // Don't show until ready
      backgroundColor: '#ffffff', // Or a theme-appropriate color
      titleBarStyle: this.isMac ? 'hiddenInset' : 'default', // macOS specific style
      // frame: false, // For custom window controls (more complex)
    });

    const frontendUrl = isDev
      ? `http://localhost:${process.env.FRONTEND_PORT || 3000}` // React dev server
      : `file://${path.join(__dirname, '../../frontend/build/index.html')}`; // Production build
      // Alternative for production if backend serves frontend: `http://localhost:${this.backend.port}`

    if (withError) {
        const errorPagePath = path.join(__dirname, '../assets/error.html'); // Assume you have a static error.html
        this.mainWindow.loadFile(errorPagePath)
            .catch(err => console.error("Failed to load error page:", err));
    } else {
        this.mainWindow.loadURL(frontendUrl)
            .catch(err => {
                console.error(`Failed to load URL ${frontendUrl}:`, err);
                dialog.showErrorBox("Load Error", `Could not load the application page: ${err.message}. Please check if the frontend server (port ${process.env.FRONTEND_PORT || 3000}) is running during development, or if the production build exists.`);
                // Optionally load a local error page here too
            });
    }


    this.mainWindow.once('ready-to-show', () => {
      this.mainWindow?.show();
      if (isDev) {
        // this.mainWindow?.webContents.openDevTools({ mode: 'detach' });
      }
    });

    this.mainWindow.on('closed', () => {
      this.mainWindow = null;
      // If not on macOS, quitting the app when main window closes is handled by 'window-all-closed'
      // However, if backend should stop when UI closes:
      // this.killBackendServer().catch(console.error);
    });
  }

  private getAppIconPath(): string {
    const iconName = this.isWindows ? 'icon.ico' : (this.isMac ? 'icon.icns' : 'icon.png');
    // In development, load from local assets. In production, from resourcesPath.
    return isDev
      ? path.join(app.getAppPath(), 'assets', iconName) // app.getAppPath() points to project root in dev
      : path.join(process.resourcesPath, 'assets', iconName); // electron-builder should place assets in resources/assets
  }

  private setupTray(): void {
    if (this.isWindows || this.isMac) { // Tray icon is more common on Win/Mac
        const iconPath = this.getAppIconPath(); // Use the same app icon
        if (!fs.existsSync(iconPath)) {
            console.warn(`Tray icon not found at ${iconPath}. Using default.`);
            // Use a default Electron icon or skip tray if icon is critical
            // For now, let it try to load, Electron might handle missing icon gracefully or error.
        }
        const nImage = nativeImage.createFromPath(iconPath);
        if (nImage.isEmpty() && (this.isWindows || this.isMac)) { // Only warn if icon actually failed to load on platforms that use it.
            console.warn(`Failed to load tray icon image from ${iconPath}. Tray might not display correctly.`);
        }

        this.tray = new Tray(nImage.resize({width:16, height:16})); // Resize for tray
        const contextMenu = Menu.buildFromTemplate([
            { label: 'Show App', click: () => this.mainWindow?.show() },
            { label: 'Backend Status: ' + this.backend.status, enabled: false },
            { type: 'separator' },
            { label: 'Check for Updates', click: () => autoUpdater.checkForUpdatesAndNotify() },
            { label: 'Quit', click: () => this.cleanupAndQuit() }
        ]);
        this.tray.setToolTip('KSEB Energy Futures Platform');
        this.tray.setContextMenu(contextMenu);
        this.tray.on('click', () => { // Show window on single click (common on Windows)
            if (this.mainWindow) {
                this.mainWindow.isVisible() ? this.mainWindow.hide() : this.mainWindow.show();
            }
        });
        // Update backend status in tray menu periodically or on event
        setInterval(() => {
            const newContextMenu = Menu.buildFromTemplate([
                 { label: 'Show App', click: () => this.mainWindow?.show() },
                 { label: 'Backend: ' + this.backend.status, enabled: false },
                 { type: 'separator' },
                 { label: 'Check for Updates', click: () => autoUpdater.checkForUpdatesAndNotify() },
                 { label: 'Quit', click: () => this.cleanupAndQuit() }
            ]);
            this.tray?.setContextMenu(newContextMenu);
        }, 5000); // Update every 5s
    }
  }


  private setupIPC(): void {
    // File/Folder Dialogs
    ipcMain.handle('dialog:selectFolder', async () => {
      if (!this.mainWindow) return null;
      const result = await dialog.showOpenDialog(this.mainWindow, { properties: ['openDirectory'] });
      return result.canceled ? null : result.filePaths[0];
    });
    ipcMain.handle('dialog:selectFile', async (_, options: Electron.OpenDialogOptions) => {
      if (!this.mainWindow) return null;
      const result = await dialog.showOpenDialog(this.mainWindow, options);
      return result.canceled ? null : result.filePaths[0];
    });
    ipcMain.handle('dialog:saveFile', async (_, options: Electron.SaveDialogOptions) => {
      if (!this.mainWindow) return null;
      const result = await dialog.showSaveDialog(this.mainWindow, options);
      return result.canceled ? null : result.filePath;
    });
    ipcMain.handle('dialog:showMessageBox', async (_, options: Electron.MessageBoxOptions) => {
        if (!this.mainWindow) return {response:0}; // Default response if no window
        return await dialog.showMessageBox(this.mainWindow, options);
    });
    ipcMain.handle('dialog:showErrorBox', (_, {title, content}: {title:string, content:string}) => dialog.showErrorBox(title, content));


    // App Info & Control
    ipcMain.handle('app:getVersion', () => app.getVersion());
    ipcMain.handle('app:isDev', () => isDev);
    ipcMain.handle('app:relaunch', () => { app.relaunch(); app.exit(); });
    ipcMain.handle('app:quit', () => this.cleanupAndQuit());

    // Window Control
    ipcMain.handle('window:minimize', () => this.mainWindow?.minimize());
    ipcMain.handle('window:maximize', () => this.mainWindow?.isMaximized() ? this.mainWindow.unmaximize() : this.mainWindow?.maximize());
    ipcMain.handle('window:close', () => this.mainWindow?.close()); // Standard close, respects before-quit etc.
    ipcMain.handle('window:toggleFullscreen', () => this.mainWindow?.setFullScreen(!this.mainWindow.isFullScreen()));

    // Shell operations
    ipcMain.handle('shell:openExternal', async (_, url: string) => {
        try {
            await shell.openExternal(url);
            return {success: true};
        } catch (error: any) {
            return {success: false, error: error.message};
        }
    });
    ipcMain.handle('shell:openPath', async (_, itemPath: string) => {
         try {
            const errorMsg = await shell.openPath(itemPath); // Returns empty string on success
            if (errorMsg) throw new Error(errorMsg);
            return {success: true};
        } catch (error: any) {
            return {success: false, error: error.message};
        }
    });
    ipcMain.handle('shell:showItemInFolder', (_, fullPath: string) => shell.showItemInFolder(fullPath));


    // System Info
    ipcMain.handle('system:getSysInfo', () => ({
      platform: process.platform, arch: process.arch, nodeVersion: process.versions.node,
      electronVersion: process.versions.electron, chromeVersion: process.versions.chrome,
      totalMemoryMB: Math.round(os.totalmem() / (1024 * 1024)),
      freeMemoryMB: Math.round(os.freemem() / (1024 * 1024)),
      cpus: os.cpus().map(cpu => ({model: cpu.model, speed: cpu.speed})), // Basic CPU info
      homedir: os.homedir(), tmpdir: os.tmpdir(),
      // machineId: machineIdSync({original: true}) // Optional
    }));

    // Backend Process Info
    ipcMain.handle('backend:getStatus', () => ({
      status: this.backend.status,
      port: this.backend.port,
      pid: this.backend.process?.pid,
      logs: this.backend.logs.slice(-20) // Last 20 log lines
    }));
    ipcMain.handle('backend:start', async () => {
        try { await this.startBackendServer(); return {success: true}; }
        catch(e:any) { return {success: false, error: e.message};}
    });
    ipcMain.handle('backend:stop', async () => {
        try { await this.killBackendServer(); return {success: true}; }
        catch(e:any) { return {success: false, error: e.message};}
    });


    // Basic FS operations (use with caution, ensure paths are validated if coming from renderer)
    // These are simplified. For robust FS, consider more checks and specific error handling.
    ipcMain.handle('fs:exists', async (_, filePath: string) => fs.existsSync(filePath)); // Use sync for exists for simplicity here
    ipcMain.handle('fs:readFile', async (_, filePath: string, encoding: BufferEncoding = 'utf-8') => fs.promises.readFile(filePath, encoding));
    ipcMain.handle('fs:writeFile', async (_, filePath: string, content: string, encoding: BufferEncoding = 'utf-8') => fs.promises.writeFile(filePath, content, encoding));
    ipcMain.handle('fs:mkdir', async (_, dirPath: string) => fs.promises.mkdir(dirPath, { recursive: true }));
    ipcMain.handle('fs:readdir', async (_, dirPath: string) => fs.promises.readdir(dirPath));
    ipcMain.handle('fs:rm', async (_, itemPath: string, options?: fs.RmOptions) => fs.promises.rm(itemPath, options)); // Node 14.14+ for recursive rm
  }

  private setupMenu(): void {
    const template: MenuItemConstructorOptions[] = [
      // {AppMenu} for macOS
      ...(this.isMac ? [{
          label: app.name,
          submenu: [
            { role: 'about' },
            { type: 'separator' },
            { label: 'Preferences...', accelerator: 'CmdOrCtrl+,', click: () => this.mainWindow?.webContents.send('navigate', '/settings') },
            { type: 'separator' },
            { role: 'services' },
            { type: 'separator' },
            { role: 'hide' },
            { role: 'hideOthers' },
            { role: 'unhide' },
            { type: 'separator' },
            { role: 'quit' }
          ]
      }] : []) as MenuItemConstructorOptions[],
      // {FileMenu}
      {
        label: 'File',
        submenu: [
          { label: 'New Project', accelerator: 'CmdOrCtrl+N', click: () => this.mainWindow?.webContents.send('menu-action', 'new-project') },
          { label: 'Open Project...', accelerator: 'CmdOrCtrl+O', click: () => this.mainWindow?.webContents.send('menu-action', 'open-project') },
          // { label: 'Open Recent', role: 'recentDocuments', submenu: [{label: 'Clear Recent', role: 'clearRecentDocuments'}] }, // Electron handles recent docs
          { type: 'separator' },
          { label: 'Save', accelerator: 'CmdOrCtrl+S', click: () => this.mainWindow?.webContents.send('menu-action', 'save-project') },
          // { label: 'Save As...', accelerator: 'CmdOrCtrl+Shift+S', click: () => { /* ... */ } },
          { type: 'separator' },
          { label: 'Export Chart/Data...', click: () => this.mainWindow?.webContents.send('menu-action', 'export-data') },
          { type: 'separator' },
          ...(this.isWindows ? [{ label: 'Settings', accelerator: 'Ctrl+,', click: () => this.mainWindow?.webContents.send('navigate', '/settings') }, {type: 'separator' as const}] : []),
          this.isMac ? { role: 'close' } : { role: 'quit', label: 'Exit' }
        ]
      },
      // {EditMenu}
      { label: 'Edit', submenu: [ {role: 'undo'}, {role: 'redo'}, {type: 'separator'}, {role: 'cut'}, {role: 'copy'}, {role: 'paste'}, ...(this.isMac ? [{role: 'pasteAndMatchStyle'}, {role: 'delete'}, {role: 'selectAll'}, {type: 'separator'}, {label: 'Speech', submenu: [{role: 'startSpeaking'}, {role: 'stopSpeaking'}]}] : [{role: 'delete'}, {type: 'separator'}, {role: 'selectAll'}]) ] },
      // {ViewMenu}
      { label: 'View', submenu: [ {role: 'reload'}, {role: 'forceReload'}, {role: 'toggleDevTools'}, {type: 'separator'}, {role: 'resetZoom'}, {role: 'zoomIn'}, {role: 'zoomOut'}, {type: 'separator'}, {role: 'togglefullscreen'} ] },
      // {WindowMenu}
      { label: 'Window', submenu: [ {role: 'minimize'}, {role: 'zoom'}, ...(this.isMac ? [{type: 'separator'}, {role: 'front'}, {type: 'separator'}, {role: 'window'}] : [{role: 'close'}]) ] },
      // {HelpMenu}
      {
        role: 'help',
        submenu: [
          { label: 'Learn More', click: async () => await shell.openExternal('https://github.com/your-repo/kseb-energy-platform') },
          { label: 'Documentation', click: () => this.mainWindow?.webContents.send('navigate', '/docs') /* or open external link */ },
          { label: 'Show App Data Folder', click: () => shell.openPath(app.getPath('userData'))},
          { type: 'separator' },
          { label: 'Check for Updates...', click: () => autoUpdater.checkForUpdatesAndNotify() },
           ...(isDev ? [{label: 'Toggle Developer Tools (Main)', click: () => this.mainWindow?.webContents.openDevTools()}] : [])
        ]
      }
    ];

    const menu = Menu.buildFromTemplate(template);
    Menu.setApplicationMenu(menu);
  }

  private setupAutoUpdater(): void {
    if (isDev) {
        this.logToBackend('info', "Auto-updater: Skipped in development mode.");
        return;
    }

    autoUpdater.logger = { // Pipe autoUpdater logs to main log
        info: (msg) => this.logToBackend('info', `AutoUpdater: ${msg}`),
        warn: (msg) => this.logToBackend('warn', `AutoUpdater: ${msg}`),
        error: (msg) => this.logToBackend('error', `AutoUpdater: ${msg}`),
        debug: (msg) => console.debug(`AutoUpdater (debug): ${msg}`), // console.debug for less noise in backend.logs
    };

    autoUpdater.on('checking-for-update', () => this.mainWindow?.webContents.send('updater-status', { message: 'Checking for updates...' }));
    autoUpdater.on('update-available', (info) => {
        this.mainWindow?.webContents.send('updater-status', { message: `Update available: v${info.version}. Downloading...` });
        dialog.showMessageBox(this.mainWindow!, {
            type: 'info', title: 'Update Available',
            message: `A new version (v${info.version}) is available. It will be downloaded in the background. You'll be notified when it's ready to install.`,
            buttons: ['OK']
        });
    });
    autoUpdater.on('update-not-available', () => this.mainWindow?.webContents.send('updater-status', { message: 'You are on the latest version.' }));
    autoUpdater.on('error', (err) => this.mainWindow?.webContents.send('updater-status', { error: `Update error: ${err.message}` }));
    autoUpdater.on('download-progress', (progressObj) => {
      this.mainWindow?.webContents.send('updater-status', { message: `Downloading update: ${Math.round(progressObj.percent)}% (${formatBytes(progressObj.bytesPerSecond)}/s)` });
      if (this.mainWindow) this.mainWindow.setProgressBar(progressObj.percent / 100);
    });
    autoUpdater.on('update-downloaded', (info) => {
      this.mainWindow?.webContents.send('updater-status', { message: `Update v${info.version} downloaded. Restart to install.`, downloaded: true });
      if (this.mainWindow) this.mainWindow.setProgressBar(-1); // Remove progress bar
      dialog.showMessageBox(this.mainWindow!, {
        type: 'info', title: 'Update Ready to Install',
        message: `Version ${info.version} has been downloaded. Restart the application to apply the update?`,
        buttons: ['Restart Now', 'Later']
      }).then((result) => {
        if (result.response === 0) autoUpdater.quitAndInstall();
      });
    });

    // Check for updates on startup (after a short delay)
    setTimeout(() => autoUpdater.checkForUpdatesAndNotify(), 5000);
  }
}

// Helper function (can be moved to a utils file)
const formatBytes = (bytes: number, decimals = 2): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
};


// Initialize the application
new ElectronApp();
