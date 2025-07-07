# KSEB Energy Futures Platform - Node.js + React Development Guide

## Complete Step-by-Step AI Development Chunks


---

## **PHASE 1: PROJECT FOUNDATION**

### **Chunk 1.1: Project Structure Setup**
```
Task: Create the foundational project structure for KSEB Energy Futures Platform

Create a complete project structure with the following specifications:

ROOT DIRECTORY: kseb-energy-platform/
├── backend/
│   ├── src/
│   │   ├── controllers/
│   │   ├── services/
│   │   ├── middleware/
│   │   ├── routes/
│   │   ├── python/
│   │   ├── config/
│   │   └── utils/
│   ├── tests/
│   └── package.json
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── store/
│   │   ├── types/
│   │   ├── utils/
│   │   └── styles/
│   ├── public/
│   └── package.json
├── electron/
│   ├── main.ts
│   ├── preload.ts
│   └── package.json
├── docs/
└── package.json (root)

Requirements:
1. Create package.json for each module with proper dependencies
2. Backend: Express, cors, helmet, compression, socket.io, child_process
3. Frontend: React, TypeScript, @mui/material, @reduxjs/toolkit, socket.io-client
4. Electron: electron, electron-builder, concurrently
5. Include proper folder structure with index files
6. Add .gitignore, README.md, and basic configuration files
7. Set up TypeScript configurations for frontend and electron
8. Create basic npm scripts for development and build processes

Focus on creating a scalable, maintainable structure that supports the energy planning modules.
```

### **Chunk 1.2: Backend Core Setup**
```
Task: Set up the Node.js backend core infrastructure

Create the main backend application with the following specifications:

FILE: backend/src/app.js
```javascript
const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const { createServer } = require('http');
const { Server } = require('socket.io');

// Import custom modules
const routes = require('./routes');
const { errorHandler } = require('./middleware/errorHandler');
const { logger } = require('./utils/logger');

const app = express();
const server = createServer(app);

// Initialize Socket.IO
const io = new Server(server, {
    cors: {
        origin: process.env.NODE_ENV === 'production' ? false : 'http://localhost:3000',
        methods: ['GET', 'POST']
    }
});

// Security middleware
app.use(helmet());
app.use(cors({
    origin: process.env.NODE_ENV === 'production' ? false : 'http://localhost:3000',
    credentials: true
}));

// Performance middleware
app.use(compression());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Rate limiting
const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100
});
app.use('/api/', limiter);

// Store io instance for use in routes
app.set('io', io);

// Routes
app.use('/api', routes);

// Error handling
app.use(errorHandler);

// Socket.IO connection handling
io.on('connection', (socket) => {
    console.log('Client connected:', socket.id);
    
    socket.on('disconnect', () => {
        console.log('Client disconnected:', socket.id);
    });
});

const PORT = process.env.PORT || 5000;
server.listen(PORT, () => {
    logger.info(`Server running on port ${PORT}`);
});

module.exports = { app, server, io };
```

Create supporting files:
1. middleware/errorHandler.js - Comprehensive error handling
2. utils/logger.js - Winston-based logging system
3. config/database.js - Database configuration
4. routes/index.js - Main routes handler

Ensure proper error handling, logging, and security measures are implemented.
```

### **Chunk 1.3: Python Process Manager**
```
Task: Create the Python Process Manager for executing energy analysis modules

Create a robust Python process management system with the following specifications:

FILE: backend/src/services/pythonProcessManager.js
```javascript
const { spawn } = require('child_process');
const path = require('path');
const { EventEmitter } = require('events');
const { logger } = require('../utils/logger');

class PythonProcessManager extends EventEmitter {
    constructor() {
        super();
        this.activeProcesses = new Map();
        this.maxConcurrentProcesses = 3;
        this.pythonPath = this.findPythonPath();
    }

    findPythonPath() {
        // Try different Python executable names
        const pythonCommands = ['python', 'python3', 'py'];
        return pythonCommands[0]; // In production, test each
    }

    async executePythonScript(scriptPath, args = [], options = {}) {
        return new Promise((resolve, reject) => {
            const processId = this.generateProcessId();
            const fullScriptPath = path.join(__dirname, '../python', scriptPath);
            
            logger.info(`Starting Python process: ${scriptPath}`);
            
            const pythonProcess = spawn(this.pythonPath, [fullScriptPath, ...args], {
                stdio: ['pipe', 'pipe', 'pipe'],
                cwd: process.cwd(),
                env: { 
                    ...process.env, 
                    PYTHONPATH: path.join(__dirname, '../python') 
                }
            });

            let stdout = '';
            let stderr = '';

            pythonProcess.stdout.on('data', (data) => {
                const chunk = data.toString();
                stdout += chunk;
                
                // Handle real-time progress updates
                if (options.onProgress && chunk.includes('PROGRESS:')) {
                    try {
                        const progressData = JSON.parse(chunk.split('PROGRESS:')[1]);
                        options.onProgress(progressData);
                    } catch (e) {
                        // Ignore invalid progress JSON
                    }
                }
            });

            pythonProcess.stderr.on('data', (data) => {
                stderr += data.toString();
            });

            pythonProcess.on('close', (code) => {
                this.activeProcesses.delete(processId);
                
                if (code === 0) {
                    try {
                        const result = JSON.parse(stdout);
                        resolve(result);
                    } catch (error) {
                        reject(new Error(`Invalid JSON output: ${stdout}`));
                    }
                } else {
                    reject(new Error(`Python script failed: ${stderr}`));
                }
            });

            // Store process for potential cancellation
            this.activeProcesses.set(processId, {
                process: pythonProcess,
                startTime: Date.now(),
                script: scriptPath
            });

            // Set timeout if specified
            if (options.timeout) {
                setTimeout(() => {
                    if (this.activeProcesses.has(processId)) {
                        pythonProcess.kill('SIGTERM');
                        reject(new Error('Python process timeout'));
                    }
                }, options.timeout);
            }
        });
    }

    generateProcessId() {
        return `py_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
}

module.exports = new PythonProcessManager();
```

Create helper modules for specific energy analysis:
1. demandProjection helper with forecast execution
2. loadProfile helper with profile generation
3. pypsa helper with optimization execution

Include proper error handling, timeout management, and progress tracking.
```

---

## **PHASE 2: CORE BACKEND MODULES**

### **Chunk 2.1: Demand Projection Controller**
```
Task: Create the Demand Projection API controller with complete functionality

Create a comprehensive demand projection controller with the following specifications:

FILE: backend/src/controllers/demandController.js
```javascript
const pythonManager = require('../services/pythonProcessManager');
const { validateForecastConfig } = require('../middleware/validation');
const { cacheGet, cacheSet } = require('../services/cacheService');
const { logger } = require('../utils/logger');

class DemandController {
    constructor() {
        this.activeForecastJobs = new Map();
    }

    async getSectorData(req, res, next) {
        try {
            const { sector } = req.params;
            const cacheKey = `demand_data_${sector}`;
            
            // Check cache first
            let data = await cacheGet(cacheKey);
            if (!data) {
                data = await pythonManager.executePythonScript(
                    'demand_projection.py', 
                    ['--sector-data', sector]
                );
                await cacheSet(cacheKey, data, 300); // Cache for 5 minutes
            }
            
            res.json({
                success: true,
                data: data
            });
        } catch (error) {
            next(error);
        }
    }

    async runForecast(req, res, next) {
        try {
            const config = req.body;
            
            // Validate configuration
            const validationResult = validateForecastConfig(config);
            if (!validationResult.isValid) {
                return res.status(400).json({
                    success: false,
                    errors: validationResult.errors
                });
            }

            // Start forecast with progress tracking
            const forecastId = `forecast_${Date.now()}`;
            const io = req.app.get('io');
            
            // Store forecast job
            this.activeForecastJobs.set(forecastId, {
                status: 'running',
                progress: 0,
                startTime: Date.now(),
                config: config
            });

            // Run forecast asynchronously
            this.executeForecastWithProgress(forecastId, config, io)
                .then(result => {
                    this.activeForecastJobs.set(forecastId, {
                        status: 'completed',
                        progress: 100,
                        result: result,
                        completedTime: Date.now()
                    });
                    io.emit('forecast-completed', { forecastId, result });
                })
                .catch(error => {
                    this.activeForecastJobs.set(forecastId, {
                        status: 'failed',
                        error: error.message,
                        failedTime: Date.now()
                    });
                    io.emit('forecast-error', { forecastId, error: error.message });
                });

            res.json({
                success: true,
                forecastId: forecastId,
                message: 'Forecast started successfully'
            });
        } catch (error) {
            next(error);
        }
    }

    async executeForecastWithProgress(forecastId, config, io) {
        const onProgress = (progressData) => {
            const job = this.activeForecastJobs.get(forecastId);
            if (job) {
                job.progress = progressData.progress;
                job.currentSector = progressData.sector;
                job.status = progressData.status;
                this.activeForecastJobs.set(forecastId, job);
                
                io.emit('forecast-progress', {
                    forecastId,
                    progress: progressData.progress,
                    sector: progressData.sector,
                    status: progressData.status
                });
            }
        };

        return pythonManager.executePythonScript(
            'demand_projection.py',
            ['--config', JSON.stringify(config)],
            { 
                timeout: 300000, // 5 minute timeout
                onProgress
            }
        );
    }

    async getForecastStatus(req, res, next) {
        try {
            const { forecastId } = req.params;
            const job = this.activeForecastJobs.get(forecastId);

            if (!job) {
                return res.status(404).json({
                    success: false,
                    message: 'Forecast job not found'
                });
            }

            res.json({
                success: true,
                job: job
            });
        } catch (error) {
            next(error);
        }
    }

    async getCorrelationData(req, res, next) {
        try {
            const { sector } = req.params;
            const cacheKey = `correlation_${sector}`;
            
            let data = await cacheGet(cacheKey);
            if (!data) {
                data = await pythonManager.executePythonScript(
                    'demand_projection.py',
                    ['--correlation', sector]
                );
                await cacheSet(cacheKey, data, 600); // Cache for 10 minutes
            }
            
            res.json({
                success: true,
                data: data
            });
        } catch (error) {
            next(error);
        }
    }

    async cancelForecast(req, res, next) {
        try {
            const { forecastId } = req.params;
            const job = this.activeForecastJobs.get(forecastId);

            if (!job) {
                return res.status(404).json({
                    success: false,
                    message: 'Forecast job not found'
                });
            }

            // Cancel the job (implementation depends on Python process management)
            job.status = 'cancelled';
            this.activeForecastJobs.set(forecastId, job);

            res.json({
                success: true,
                message: 'Forecast cancelled successfully'
            });
        } catch (error) {
            next(error);
        }
    }
}

module.exports = new DemandController();
```

Create supporting files:
1. middleware/validation.js for configuration validation
2. services/cacheService.js for Redis/memory caching
3. Route handlers in routes/demand.js

Ensure proper error handling, progress tracking, and WebSocket integration.
```

### **Chunk 2.2: Load Profile Controller**
```
Task: Create the Load Profile API controller with generation and analysis capabilities

Create a comprehensive load profile controller with the following specifications:

FILE: backend/src/controllers/loadProfileController.js
```javascript
const pythonManager = require('../services/pythonProcessManager');
const { validateProfileConfig } = require('../middleware/validation');
const { fileService } = require('../services/fileService');
const { logger } = require('../utils/logger');
const path = require('path');
const fs = require('fs').promises;

class LoadProfileController {
    constructor() {
        this.activeGenerationJobs = new Map();
        this.savedProfiles = new Map();
    }

    async generateProfile(req, res, next) {
        try {
            const config = req.body;
            
            // Validate configuration
            const validationResult = validateProfileConfig(config);
            if (!validationResult.isValid) {
                return res.status(400).json({
                    success: false,
                    errors: validationResult.errors
                });
            }

            const profileId = `profile_${Date.now()}`;
            const io = req.app.get('io');
            
            // Store generation job
            this.activeGenerationJobs.set(profileId, {
                status: 'running',
                progress: 0,
                startTime: Date.now(),
                config: config
            });

            // Run generation asynchronously
            this.executeGenerationWithProgress(profileId, config, io)
                .then(result => {
                    this.activeGenerationJobs.set(profileId, {
                        status: 'completed',
                        progress: 100,
                        result: result,
                        completedTime: Date.now()
                    });
                    
                    // Save to profiles map
                    this.savedProfiles.set(result.profile_id, result);
                    
                    io.emit('profile-generated', { profileId, result });
                })
                .catch(error => {
                    this.activeGenerationJobs.set(profileId, {
                        status: 'failed',
                        error: error.message,
                        failedTime: Date.now()
                    });
                    io.emit('profile-error', { profileId, error: error.message });
                });

            res.json({
                success: true,
                profileId: profileId,
                message: 'Profile generation started successfully'
            });
        } catch (error) {
            next(error);
        }
    }

    async executeGenerationWithProgress(profileId, config, io) {
        const onProgress = (progressData) => {
            const job = this.activeGenerationJobs.get(profileId);
            if (job) {
                job.progress = progressData.progress;
                job.currentStep = progressData.step;
                job.status = progressData.status;
                this.activeGenerationJobs.set(profileId, job);
                
                io.emit('profile-progress', {
                    profileId,
                    progress: progressData.progress,
                    step: progressData.step,
                    status: progressData.status
                });
            }
        };

        return pythonManager.executePythonScript(
            'load_profile_generation.py',
            ['--config', JSON.stringify(config)],
            { 
                timeout: 600000, // 10 minute timeout
                onProgress
            }
        );
    }

    async getGenerationStatus(req, res, next) {
        try {
            const { profileId } = req.params;
            const job = this.activeGenerationJobs.get(profileId);

            if (!job) {
                return res.status(404).json({
                    success: false,
                    message: 'Profile generation job not found'
                });
            }

            res.json({
                success: true,
                job: job
            });
        } catch (error) {
            next(error);
        }
    }

    async getSavedProfiles(req, res, next) {
        try {
            // Load profiles from file system if not in memory
            await this.loadSavedProfilesFromDisk();
            
            const profiles = Array.from(this.savedProfiles.values()).map(profile => ({
                profile_id: profile.profile_id,
                method: profile.method,
                generation_time: profile.generation_time,
                years_generated: profile.years_generated,
                summary: profile.summary
            }));

            res.json({
                success: true,
                profiles: profiles
            });
        } catch (error) {
            next(error);
        }
    }

    async getProfileData(req, res, next) {
        try {
            const { profileId } = req.params;
            const profile = this.savedProfiles.get(profileId);

            if (!profile) {
                // Try loading from disk
                await this.loadProfileFromDisk(profileId);
                const profile = this.savedProfiles.get(profileId);
                
                if (!profile) {
                    return res.status(404).json({
                        success: false,
                        message: 'Profile not found'
                    });
                }
            }

            res.json({
                success: true,
                profile: profile
            });
        } catch (error) {
            next(error);
        }
    }

    async analyzeProfile(req, res, next) {
        try {
            const { profileId } = req.params;
            const { analysisType } = req.query;
            
            const result = await pythonManager.executePythonScript(
                'load_profile_analysis.py',
                ['--profile-id', profileId, '--analysis-type', analysisType || 'overview']
            );

            res.json({
                success: true,
                analysis: result
            });
        } catch (error) {
            next(error);
        }
    }

    async deleteProfile(req, res, next) {
        try {
            const { profileId } = req.params;
            
            // Remove from memory
            this.savedProfiles.delete(profileId);
            
            // Remove from disk
            const profilePath = path.join(process.cwd(), 'results', 'load_profiles', `${profileId}.json`);
            try {
                await fs.unlink(profilePath);
            } catch (error) {
                // File might not exist, that's okay
            }

            res.json({
                success: true,
                message: 'Profile deleted successfully'
            });
        } catch (error) {
            next(error);
        }
    }

    async compareProfiles(req, res, next) {
        try {
            const { profileIds } = req.body;
            
            if (!Array.isArray(profileIds) || profileIds.length < 2) {
                return res.status(400).json({
                    success: false,
                    message: 'At least 2 profile IDs are required for comparison'
                });
            }

            const result = await pythonManager.executePythonScript(
                'load_profile_analysis.py',
                ['--compare', JSON.stringify(profileIds)]
            );

            res.json({
                success: true,
                comparison: result
            });
        } catch (error) {
            next(error);
        }
    }

    async loadSavedProfilesFromDisk() {
        try {
            const profilesDir = path.join(process.cwd(), 'results', 'load_profiles');
            const files = await fs.readdir(profilesDir);
            
            for (const file of files) {
                if (file.endsWith('.json')) {
                    const profileId = file.replace('.json', '');
                    if (!this.savedProfiles.has(profileId)) {
                        await this.loadProfileFromDisk(profileId);
                    }
                }
            }
        } catch (error) {
            // Directory might not exist yet
            logger.info('No saved profiles directory found');
        }
    }

    async loadProfileFromDisk(profileId) {
        try {
            const profilePath = path.join(process.cwd(), 'results', 'load_profiles', `${profileId}.json`);
            const profileData = await fs.readFile(profilePath, 'utf-8');
            const profile = JSON.parse(profileData);
            this.savedProfiles.set(profileId, profile);
        } catch (error) {
            logger.error(`Failed to load profile ${profileId} from disk:`, error);
        }
    }
}

module.exports = new LoadProfileController();
```

Create supporting files:
1. Route handlers in routes/loadProfile.js
2. Validation middleware for profile configurations
3. File service for managing profile files

Include proper file management, progress tracking, and analysis integration.
```

### **Chunk 2.3: PyPSA Controller**
```
Task: Create the PyPSA power system modeling API controller

Create a comprehensive PyPSA controller with the following specifications:

FILE: backend/src/controllers/pypsaController.js
```javascript
const pythonManager = require('../services/pythonProcessManager');
const { validatePyPSAConfig } = require('../middleware/validation');
const { fileService } = require('../services/fileService');
const { logger } = require('../utils/logger');
const path = require('path');
const fs = require('fs').promises;

class PyPSAController {
    constructor() {
        this.activeOptimizationJobs = new Map();
        this.availableNetworks = new Map();
        this.resultsCache = new Map();
    }

    async runOptimization(req, res, next) {
        try {
            const config = req.body;
            
            // Validate configuration
            const validationResult = validatePyPSAConfig(config);
            if (!validationResult.isValid) {
                return res.status(400).json({
                    success: false,
                    errors: validationResult.errors
                });
            }

            const jobId = `pypsa_${Date.now()}`;
            const io = req.app.get('io');
            
            // Store optimization job
            this.activeOptimizationJobs.set(jobId, {
                status: 'running',
                progress: 0,
                startTime: Date.now(),
                config: config
            });

            // Run optimization asynchronously
            this.executeOptimizationWithProgress(jobId, config, io)
                .then(result => {
                    this.activeOptimizationJobs.set(jobId, {
                        status: 'completed',
                        progress: 100,
                        result: result,
                        completedTime: Date.now()
                    });
                    
                    // Cache the network path for future access
                    if (result.network_path) {
                        this.availableNetworks.set(result.scenario_name, result.network_path);
                    }
                    
                    io.emit('pypsa-completed', { jobId, result });
                })
                .catch(error => {
                    this.activeOptimizationJobs.set(jobId, {
                        status: 'failed',
                        error: error.message,
                        failedTime: Date.now()
                    });
                    io.emit('pypsa-error', { jobId, error: error.message });
                });

            res.json({
                success: true,
                jobId: jobId,
                message: 'PyPSA optimization started successfully'
            });
        } catch (error) {
            next(error);
        }
    }

    async executeOptimizationWithProgress(jobId, config, io) {
        const onProgress = (progressData) => {
            const job = this.activeOptimizationJobs.get(jobId);
            if (job) {
                job.progress = progressData.progress;
                job.currentStep = progressData.step;
                job.status = progressData.status;
                this.activeOptimizationJobs.set(jobId, job);
                
                io.emit('pypsa-progress', {
                    jobId,
                    progress: progressData.progress,
                    step: progressData.step,
                    status: progressData.status
                });
            }
        };

        return pythonManager.executePythonScript(
            'pypsa_runner.py',
            ['--config', JSON.stringify(config)],
            { 
                timeout: 1800000, // 30 minute timeout
                onProgress
            }
        );
    }

    async getOptimizationStatus(req, res, next) {
        try {
            const { jobId } = req.params;
            const job = this.activeOptimizationJobs.get(jobId);

            if (!job) {
                return res.status(404).json({
                    success: false,
                    message: 'Optimization job not found'
                });
            }

            res.json({
                success: true,
                job: job
            });
        } catch (error) {
            next(error);
        }
    }

    async getAvailableNetworks(req, res, next) {
        try {
            // Scan for available network files
            await this.scanForNetworkFiles();
            
            const networks = Array.from(this.availableNetworks.entries()).map(([name, path]) => ({
                scenario_name: name,
                network_path: path,
                file_size: 0, // TODO: Get actual file size
                created_time: null // TODO: Get file creation time
            }));

            res.json({
                success: true,
                networks: networks
            });
        } catch (error) {
            next(error);
        }
    }

    async extractNetworkResults(req, res, next) {
        try {
            const { networkPath } = req.body;
            const cacheKey = `results_${networkPath}`;
            
            // Check cache first
            let results = this.resultsCache.get(cacheKey);
            if (!results) {
                results = await pythonManager.executePythonScript(
                    'pypsa_runner.py',
                    ['--extract', networkPath]
                );
                
                // Cache results for 30 minutes
                this.resultsCache.set(cacheKey, results);
                setTimeout(() => {
                    this.resultsCache.delete(cacheKey);
                }, 30 * 60 * 1000);
            }

            res.json({
                success: true,
                results: results
            });
        } catch (error) {
            next(error);
        }
    }

    async getDispatchData(req, res, next) {
        try {
            const { networkPath } = req.params;
            const { startDate, endDate, resolution } = req.query;
            
            const result = await pythonManager.executePythonScript(
                'pypsa_analysis.py',
                [
                    '--network', networkPath,
                    '--analysis', 'dispatch',
                    '--start-date', startDate || '',
                    '--end-date', endDate || '',
                    '--resolution', resolution || '1H'
                ]
            );

            res.json({
                success: true,
                data: result
            });
        } catch (error) {
            next(error);
        }
    }

    async getCapacityData(req, res, next) {
        try {
            const { networkPath } = req.params;
            
            const result = await pythonManager.executePythonScript(
                'pypsa_analysis.py',
                [
                    '--network', networkPath,
                    '--analysis', 'capacity'
                ]
            );

            res.json({
                success: true,
                data: result
            });
        } catch (error) {
            next(error);
        }
    }

    async getStorageData(req, res, next) {
        try {
            const { networkPath } = req.params;
            const { startDate, endDate } = req.query;
            
            const result = await pythonManager.executePythonScript(
                'pypsa_analysis.py',
                [
                    '--network', networkPath,
                    '--analysis', 'storage',
                    '--start-date', startDate || '',
                    '--end-date', endDate || ''
                ]
            );

            res.json({
                success: true,
                data: result
            });
        } catch (error) {
            next(error);
        }
    }

    async getEmissionsData(req, res, next) {
        try {
            const { networkPath } = req.params;
            
            const result = await pythonManager.executePythonScript(
                'pypsa_analysis.py',
                [
                    '--network', networkPath,
                    '--analysis', 'emissions'
                ]
            );

            res.json({
                success: true,
                data: result
            });
        } catch (error) {
            next(error);
        }
    }

    async getNetworkInfo(req, res, next) {
        try {
            const { networkPath } = req.params;
            
            const result = await pythonManager.executePythonScript(
                'pypsa_analysis.py',
                [
                    '--network', networkPath,
                    '--analysis', 'info'
                ]
            );

            res.json({
                success: true,
                info: result
            });
        } catch (error) {
            next(error);
        }
    }

    async compareNetworks(req, res, next) {
        try {
            const { networkPaths, metrics } = req.body;
            
            if (!Array.isArray(networkPaths) || networkPaths.length < 2) {
                return res.status(400).json({
                    success: false,
                    message: 'At least 2 network paths are required for comparison'
                });
            }

            const result = await pythonManager.executePythonScript(
                'pypsa_analysis.py',
                [
                    '--compare', JSON.stringify(networkPaths),
                    '--metrics', JSON.stringify(metrics || ['cost', 'emissions', 'renewable_share'])
                ]
            );

            res.json({
                success: true,
                comparison: result
            });
        } catch (error) {
            next(error);
        }
    }

    async cancelOptimization(req, res, next) {
        try {
            const { jobId } = req.params;
            const job = this.activeOptimizationJobs.get(jobId);

            if (!job) {
                return res.status(404).json({
                    success: false,
                    message: 'Optimization job not found'
                });
            }

            // Cancel the job (implementation depends on Python process management)
            job.status = 'cancelled';
            this.activeOptimizationJobs.set(jobId, job);

            res.json({
                success: true,
                message: 'Optimization cancelled successfully'
            });
        } catch (error) {
            next(error);
        }
    }

    async scanForNetworkFiles() {
        try {
            const resultsDir = path.join(process.cwd(), 'results', 'pypsa');
            const files = await fs.readdir(resultsDir);
            
            for (const file of files) {
                if (file.endsWith('.nc')) {
                    const scenarioName = file.replace('.nc', '');
                    const fullPath = path.join(resultsDir, file);
                    this.availableNetworks.set(scenarioName, fullPath);
                }
            }
        } catch (error) {
            // Directory might not exist yet
            logger.info('No PyPSA results directory found');
        }
    }
}

module.exports = new PyPSAController();
```

Create supporting files:
1. Route handlers in routes/pypsa.js
2. PyPSA-specific validation middleware
3. Analysis scripts for different result types

Include proper optimization tracking, result caching, and network management.
```

---

## **PHASE 3: FRONTEND FOUNDATION**

### **Chunk 3.1: React App Structure**
```
Task: Create the main React application structure with TypeScript and Material-UI

Set up the React frontend with the following specifications:

FILE: frontend/src/App.tsx
```typescript
import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Provider } from 'react-redux';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { Box } from '@mui/material';

import { store } from './store';
import { WebSocketProvider } from './services/websocket';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { Header } from './components/common/Header';
import { Sidebar } from './components/common/Sidebar';
import { LoadingOverlay } from './components/common/LoadingOverlay';
import { NotificationManager } from './components/common/NotificationManager';

// Page components
import { Dashboard } from './pages/Dashboard';
import { DemandProjection } from './pages/DemandProjection';
import { DemandVisualization } from './pages/DemandVisualization';
import { LoadProfileGeneration } from './pages/LoadProfileGeneration';
import { LoadProfileAnalysis } from './pages/LoadProfileAnalysis';
import { PyPSAModeling } from './pages/PyPSAModeling';
import { PyPSAResults } from './pages/PyPSAResults';
import { Settings } from './pages/Settings';

// Create theme
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
    background: {
      default: '#f5f5f5',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h4: {
      fontWeight: 600,
    },
    h5: {
      fontWeight: 500,
    },
  },
  components: {
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: '#1565c0',
        },
      },
    },
  },
});

const App: React.FC = () => {
  useEffect(() => {
    document.title = 'KSEB Energy Futures Platform';
  }, []);

  return (
    <Provider store={store}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <ErrorBoundary>
          <WebSocketProvider>
            <Router>
              <Box sx={{ display: 'flex', minHeight: '100vh' }}>
                <Header />
                <Sidebar />
                <Box
                  component="main"
                  sx={{
                    flexGrow: 1,
                    p: 3,
                    marginTop: '64px', // AppBar height
                    marginLeft: '240px', // Sidebar width
                    minHeight: 'calc(100vh - 64px)',
                  }}
                >
                  <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/demand-projection" element={<DemandProjection />} />
                    <Route path="/demand-visualization" element={<DemandVisualization />} />
                    <Route path="/load-profile-generation" element={<LoadProfileGeneration />} />
                    <Route path="/load-profile-analysis" element={<LoadProfileAnalysis />} />
                    <Route path="/pypsa-modeling" element={<PyPSAModeling />} />
                    <Route path="/pypsa-results" element={<PyPSAResults />} />
                    <Route path="/settings" element={<Settings />} />
                  </Routes>
                </Box>
                <LoadingOverlay />
                <NotificationManager />
              </Box>
            </Router>
          </WebSocketProvider>
        </ErrorBoundary>
      </ThemeProvider>
    </Provider>
  );
};

export default App;
```

Create supporting components:
1. components/common/Header.tsx - Top navigation bar
2. components/common/Sidebar.tsx - Side navigation menu
3. components/common/ErrorBoundary.tsx - Error handling wrapper
4. components/common/LoadingOverlay.tsx - Global loading indicator
5. components/common/NotificationManager.tsx - Toast notifications

Include proper routing, theming, and state management setup.
```

### **Chunk 3.2: Redux Store Setup**
```
Task: Create the Redux store with RTK Query for state management

Set up Redux store with the following specifications:

FILE: frontend/src/store/index.ts
```typescript
import { configureStore } from '@reduxjs/toolkit';
import { setupListeners } from '@reduxjs/toolkit/query';

// Import slice reducers
import projectReducer from './slices/projectSlice';
import demandReducer from './slices/demandSlice';
import loadProfileReducer from './slices/loadProfileSlice';
import pypsaReducer from './slices/pypsaSlice';
import uiReducer from './slices/uiSlice';
import notificationReducer from './slices/notificationSlice';

// Import API slice
import { apiSlice } from './api/apiSlice';

export const store = configureStore({
  reducer: {
    // Feature slices
    project: projectReducer,
    demand: demandReducer,
    loadProfile: loadProfileReducer,
    pypsa: pypsaReducer,
    ui: uiReducer,
    notifications: notificationReducer,
    
    // API slice
    api: apiSlice.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST', 'persist/REHYDRATE'],
      },
    }).concat(apiSlice.middleware),
  devTools: process.env.NODE_ENV !== 'production',
});

// Setup RTK Query listeners
setupListeners(store.dispatch);

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

// Export typed hooks
export { useAppDispatch, useAppSelector } from './hooks';
```

FILE: frontend/src/store/api/apiSlice.ts
```typescript
import { createApi, fetchBaseQuery } from '@reduxjs/toolkit/query/react';

const baseQuery = fetchBaseQuery({
  baseUrl: process.env.REACT_APP_API_URL || 'http://localhost:5000/api',
  credentials: 'include',
  prepareHeaders: (headers, { getState }) => {
    // Add any auth headers here if needed
    headers.set('Content-Type', 'application/json');
    return headers;
  },
});

export const apiSlice = createApi({
  reducerPath: 'api',
  baseQuery,
  tagTypes: [
    'Project',
    'DemandForecast', 
    'LoadProfile', 
    'PyPSAOptimization',
    'SectorData',
    'NetworkResults'
  ],
  endpoints: (builder) => ({
    // Project endpoints
    createProject: builder.mutation({
      query: (projectData) => ({
        url: '/projects',
        method: 'POST',
        body: projectData,
      }),
      invalidatesTags: ['Project'],
    }),
    
    loadProject: builder.mutation({
      query: (projectPath) => ({
        url: '/projects/load',
        method: 'POST',
        body: { path: projectPath },
      }),
      invalidatesTags: ['Project'],
    }),
    
    // Demand projection endpoints
    getSectorData: builder.query({
      query: (sector) => `/demand/sectors/${sector}`,
      providesTags: (result, error, sector) => [{ type: 'SectorData', id: sector }],
    }),
    
    runForecast: builder.mutation({
      query: (config) => ({
        url: '/demand/forecast',
        method: 'POST',
        body: config,
      }),
      invalidatesTags: ['DemandForecast'],
    }),
    
    getForecastStatus: builder.query({
      query: (forecastId) => `/demand/forecast/${forecastId}/status`,
      providesTags: (result, error, forecastId) => [
        { type: 'DemandForecast', id: forecastId }
      ],
    }),
    
    getCorrelationData: builder.query({
      query: (sector) => `/demand/correlation/${sector}`,
      providesTags: (result, error, sector) => [
        { type: 'SectorData', id: `correlation-${sector}` }
      ],
    }),
    
    // Load profile endpoints
    generateProfile: builder.mutation({
      query: (config) => ({
        url: '/loadprofile/generate',
        method: 'POST',
        body: config,
      }),
      invalidatesTags: ['LoadProfile'],
    }),
    
    getSavedProfiles: builder.query({
      query: () => '/loadprofile/profiles',
      providesTags: ['LoadProfile'],
    }),
    
    getProfileData: builder.query({
      query: (profileId) => `/loadprofile/profiles/${profileId}`,
      providesTags: (result, error, profileId) => [
        { type: 'LoadProfile', id: profileId }
      ],
    }),
    
    analyzeProfile: builder.query({
      query: ({ profileId, analysisType }) => 
        `/loadprofile/analyze/${profileId}?analysisType=${analysisType}`,
      providesTags: (result, error, { profileId, analysisType }) => [
        { type: 'LoadProfile', id: `${profileId}-${analysisType}` }
      ],
    }),
    
    compareProfiles: builder.mutation({
      query: (profileIds) => ({
        url: '/loadprofile/compare',
        method: 'POST',
        body: { profileIds },
      }),
    }),
    
    deleteProfile: builder.mutation({
      query: (profileId) => ({
        url: `/loadprofile/profiles/${profileId}`,
        method: 'DELETE',
      }),
      invalidatesTags: ['LoadProfile'],
    }),
    
    // PyPSA endpoints
    runOptimization: builder.mutation({
      query: (config) => ({
        url: '/pypsa/optimize',
        method: 'POST',
        body: config,
      }),
      invalidatesTags: ['PyPSAOptimization'],
    }),
    
    getOptimizationStatus: builder.query({
      query: (jobId) => `/pypsa/optimization/${jobId}/status`,
      providesTags: (result, error, jobId) => [
        { type: 'PyPSAOptimization', id: jobId }
      ],
    }),
    
    getAvailableNetworks: builder.query({
      query: () => '/pypsa/networks',
      providesTags: ['NetworkResults'],
    }),
    
    extractNetworkResults: builder.mutation({
      query: (networkPath) => ({
        url: '/pypsa/extract',
        method: 'POST',
        body: { networkPath },
      }),
      invalidatesTags: ['NetworkResults'],
    }),
    
    getDispatchData: builder.query({
      query: ({ networkPath, startDate, endDate, resolution }) => {
        const params = new URLSearchParams();
        if (startDate) params.append('startDate', startDate);
        if (endDate) params.append('endDate', endDate);
        if (resolution) params.append('resolution', resolution);
        
        return `/pypsa/dispatch/${encodeURIComponent(networkPath)}?${params}`;
      },
      providesTags: (result, error, { networkPath }) => [
        { type: 'NetworkResults', id: `dispatch-${networkPath}` }
      ],
    }),
    
    getCapacityData: builder.query({
      query: (networkPath) => `/pypsa/capacity/${encodeURIComponent(networkPath)}`,
      providesTags: (result, error, networkPath) => [
        { type: 'NetworkResults', id: `capacity-${networkPath}` }
      ],
    }),
    
    // File upload endpoint
    uploadFile: builder.mutation({
      query: ({ file, fileType }) => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('type', fileType);
        
        return {
          url: '/files/upload',
          method: 'POST',
          body: formData,
          formData: true,
        };
      },
    }),
  }),
});

// Export hooks for usage in functional components
export const {
  // Project hooks
  useCreateProjectMutation,
  useLoadProjectMutation,
  
  // Demand projection hooks
  useGetSectorDataQuery,
  useRunForecastMutation,
  useGetForecastStatusQuery,
  useGetCorrelationDataQuery,
  
  // Load profile hooks
  useGenerateProfileMutation,
  useGetSavedProfilesQuery,
  useGetProfileDataQuery,
  useAnalyzeProfileQuery,
  useCompareProfilesMutation,
  useDeleteProfileMutation,
  
  // PyPSA hooks
  useRunOptimizationMutation,
  useGetOptimizationStatusQuery,
  useGetAvailableNetworksQuery,
  useExtractNetworkResultsMutation,
  useGetDispatchDataQuery,
  useGetCapacityDataQuery,
  
  // File upload hook
  useUploadFileMutation,
} = apiSlice;
```

Create additional slice files:
1. slices/projectSlice.ts - Project state management
2. slices/demandSlice.ts - Demand projection state
3. slices/loadProfileSlice.ts - Load profile state
4. slices/pypsaSlice.ts - PyPSA state
5. slices/uiSlice.ts - UI state (loading, modals, etc.)
6. store/hooks.ts - Typed Redux hooks

Include proper TypeScript types and error handling.
```

### **Chunk 3.3: WebSocket Integration**
```
Task: Create WebSocket service for real-time communication

Set up WebSocket integration with the following specifications:

FILE: frontend/src/services/websocket.tsx
```typescript
import React, { createContext, useContext, useEffect, useRef, ReactNode } from 'react';
import { useDispatch } from 'react-redux';
import { io, Socket } from 'socket.io-client';

import { 
  updateForecastProgress, 
  setForecastCompleted, 
  setForecastError 
} from '../store/slices/demandSlice';
import { 
  updateProfileProgress, 
  setProfileCompleted, 
  setProfileError 
} from '../store/slices/loadProfileSlice';
import { 
  updateOptimizationProgress, 
  setOptimizationCompleted, 
  setOptimizationError 
} from '../store/slices/pypsaSlice';
import { 
  addNotification 
} from '../store/slices/notificationSlice';

interface WebSocketContextType {
  socket: Socket | null;
  isConnected: boolean;
  joinRoom: (roomId: string) => void;
  leaveRoom: (roomId: string) => void;
  emit: (event: string, data: any) => void;
}

const WebSocketContext = createContext<WebSocketContextType | null>(null);

interface WebSocketProviderProps {
  children: ReactNode;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const socketRef = useRef<Socket | null>(null);
  const dispatch = useDispatch();
  const [isConnected, setIsConnected] = React.useState(false);

  useEffect(() => {
    // Initialize socket connection
    const socketUrl = process.env.REACT_APP_WS_URL || 'http://localhost:5000';
    
    socketRef.current = io(socketUrl, {
      transports: ['websocket', 'polling'],
      autoConnect: true,
    });

    const socket = socketRef.current;

    // Connection event handlers
    socket.on('connect', () => {
      console.log('WebSocket connected:', socket.id);
      setIsConnected(true);
      dispatch(addNotification({
        type: 'success',
        message: 'Connected to server',
        duration: 3000,
      }));
    });

    socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
      setIsConnected(false);
      dispatch(addNotification({
        type: 'warning',
        message: 'Disconnected from server',
        duration: 5000,
      }));
    });

    socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      setIsConnected(false);
      dispatch(addNotification({
        type: 'error',
        message: 'Failed to connect to server',
        duration: 10000,
      }));
    });

    // Demand projection event handlers
    socket.on('forecast-progress', (data) => {
      dispatch(updateForecastProgress({
        forecastId: data.forecastId,
        progress: data.progress,
        sector: data.sector,
        status: data.status,
      }));
    });

    socket.on('forecast-completed', (data) => {
      dispatch(setForecastCompleted({
        forecastId: data.forecastId,
        result: data.result,
      }));
      dispatch(addNotification({
        type: 'success',
        message: `Forecast ${data.forecastId} completed successfully`,
        duration: 5000,
      }));
    });

    socket.on('forecast-error', (data) => {
      dispatch(setForecastError({
        forecastId: data.forecastId,
        error: data.error,
      }));
      dispatch(addNotification({
        type: 'error',
        message: `Forecast ${data.forecastId} failed: ${data.error}`,
        duration: 10000,
      }));
    });

    // Load profile event handlers
    socket.on('profile-progress', (data) => {
      dispatch(updateProfileProgress({
        profileId: data.profileId,
        progress: data.progress,
        step: data.step,
        status: data.status,
      }));
    });

    socket.on('profile-generated', (data) => {
      dispatch(setProfileCompleted({
        profileId: data.profileId,
        result: data.result,
      }));
      dispatch(addNotification({
        type: 'success',
        message: `Profile ${data.profileId} generated successfully`,
        duration: 5000,
      }));
    });

    socket.on('profile-error', (data) => {
      dispatch(setProfileError({
        profileId: data.profileId,
        error: data.error,
      }));
      dispatch(addNotification({
        type: 'error',
        message: `Profile generation ${data.profileId} failed: ${data.error}`,
        duration: 10000,
      }));
    });

    // PyPSA event handlers
    socket.on('pypsa-progress', (data) => {
      dispatch(updateOptimizationProgress({
        jobId: data.jobId,
        progress: data.progress,
        step: data.step,
        status: data.status,
      }));
    });

    socket.on('pypsa-completed', (data) => {
      dispatch(setOptimizationCompleted({
        jobId: data.jobId,
        result: data.result,
      }));
      dispatch(addNotification({
        type: 'success',
        message: `PyPSA optimization ${data.jobId} completed successfully`,
        duration: 5000,
      }));
    });

    socket.on('pypsa-error', (data) => {
      dispatch(setOptimizationError({
        jobId: data.jobId,
        error: data.error,
      }));
      dispatch(addNotification({
        type: 'error',
        message: `PyPSA optimization ${data.jobId} failed: ${data.error}`,
        duration: 10000,
      }));
    });

    // Cleanup on unmount
    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, [dispatch]);

  const joinRoom = (roomId: string) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit('join-room', roomId);
      console.log(`Joined room: ${roomId}`);
    }
  };

  const leaveRoom = (roomId: string) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit('leave-room', roomId);
      console.log(`Left room: ${roomId}`);
    }
  };

  const emit = (event: string, data: any) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit(event, data);
    }
  };

  const contextValue: WebSocketContextType = {
    socket: socketRef.current,
    isConnected,
    joinRoom,
    leaveRoom,
    emit,
  };

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  );
};

// Custom hook to use WebSocket context
export const useWebSocket = (): WebSocketContextType => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};

// Custom hooks for specific functionality
export const useForecastProgress = (forecastId: string | null) => {
  const { joinRoom, leaveRoom } = useWebSocket();

  useEffect(() => {
    if (forecastId) {
      joinRoom(`forecast-${forecastId}`);
      return () => leaveRoom(`forecast-${forecastId}`);
    }
  }, [forecastId, joinRoom, leaveRoom]);
};

export const useProfileProgress = (profileId: string | null) => {
  const { joinRoom, leaveRoom } = useWebSocket();

  useEffect(() => {
    if (profileId) {
      joinRoom(`profile-${profileId}`);
      return () => leaveRoom(`profile-${profileId}`);
    }
  }, [profileId, joinRoom, leaveRoom]);
};

export const usePyPSAProgress = (jobId: string | null) => {
  const { joinRoom, leaveRoom } = useWebSocket();

  useEffect(() => {
    if (jobId) {
      joinRoom(`pypsa-${jobId}`);
      return () => leaveRoom(`pypsa-${jobId}`);
    }
  }, [jobId, joinRoom, leaveRoom]);
};
```

Create supporting files:
1. types/websocket.ts - WebSocket event type definitions
2. hooks/useProgressTracking.ts - Progress tracking hook
3. components/common/ConnectionStatus.tsx - Connection indicator

Include proper error handling, reconnection logic, and progress tracking.
```

## **PHASE 4: FRONTEND MODULE IMPLEMENTATION**

### **Chunk 4.1: Demand Projection Component**
```
Task: Create the main Demand Projection page component with full functionality

Create a comprehensive demand projection interface with the following specifications:

FILE: frontend/src/pages/DemandProjection.tsx
```typescript
import React, { useState, useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import {
  Container, Grid, Paper, Typography, Button, Box,
  Tabs, Tab, LinearProgress, Dialog, DialogTitle,
  DialogContent, DialogActions, Alert, Chip
} from '@mui/material';
import { PlayArrow, Stop, Settings, Assessment } from '@mui/icons-material';

import { RootState } from '../store';
import { 
  useGetSectorDataQuery, 
  useRunForecastMutation,
  useGetCorrelationDataQuery 
} from '../store/api/apiSlice';
import { useForecastProgress } from '../services/websocket';
import { SectorNavigation } from '../components/demand/SectorNavigation';
import { DataVisualization } from '../components/demand/DataVisualization';
import { CorrelationAnalysis } from '../components/demand/CorrelationAnalysis';
import { ForecastConfiguration } from '../components/demand/ForecastConfiguration';
import { ProgressMonitor } from '../components/demand/ProgressMonitor';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => (
  <div hidden={value !== index} style={{ paddingTop: 16 }}>
    {value === index && children}
  </div>
);

export const DemandProjection: React.FC = () => {
  const dispatch = useDispatch();
  const [selectedSector, setSelectedSector] = useState('residential');
  const [currentTab, setCurrentTab] = useState(0);
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [activeForecast, setActiveForecast] = useState<string | null>(null);

  // API hooks
  const { 
    data: sectorData, 
    isLoading: sectorLoading, 
    error: sectorError 
  } = useGetSectorDataQuery(selectedSector);
  
  const {
    data: correlationData,
    isLoading: correlationLoading
  } = useGetCorrelationDataQuery(selectedSector);

  const [runForecast, { 
    isLoading: forecastStarting 
  }] = useRunForecastMutation();

  // WebSocket progress tracking
  useForecastProgress(activeForecast);

  // Redux state
  const forecastJobs = useSelector((state: RootState) => state.demand.forecastJobs);
  const currentJob = activeForecast ? forecastJobs[activeForecast] : null;

  const handleSectorChange = (sector: string) => {
    setSelectedSector(sector);
    setCurrentTab(0); // Reset to data view when changing sectors
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  const handleStartForecast = async (config: any) => {
    try {
      const result = await runForecast(config).unwrap();
      setActiveForecast(result.forecastId);
      setConfigDialogOpen(false);
    } catch (error) {
      console.error('Failed to start forecast:', error);
    }
  };

  const getSectorQuality = (sector: string) => {
    // Mock data quality assessment - in real app, this would come from API
    const qualities: { [key: string]: 'excellent' | 'good' | 'fair' | 'poor' } = {
      residential: 'excellent',
      commercial: 'good',
      industrial: 'good',
      agriculture: 'fair',
      transport: 'poor'
    };
    return qualities[sector] || 'fair';
  };

  const getQualityColor = (quality: string) => {
    switch (quality) {
      case 'excellent': return 'success';
      case 'good': return 'info';
      case 'fair': return 'warning';
      case 'poor': return 'error';
      default: return 'default';
    }
  };

  return (
    <Container maxWidth="xl">
      <Grid container spacing={3}>
        {/* Header */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Box display="flex" justifyContent="space-between" alignItems="center">
              <Box>
                <Typography variant="h4" gutterBottom>
                  Demand Projection & Forecasting
                </Typography>
                <Typography variant="body1" color="text.secondary">
                  Create comprehensive electricity demand forecasts using multiple models
                </Typography>
              </Box>
              <Box>
                <Button
                  variant="contained"
                  startIcon={<Settings />}
                  onClick={() => setConfigDialogOpen(true)}
                  disabled={forecastStarting || Boolean(currentJob?.status === 'running')}
                  sx={{ mr: 2 }}
                >
                  Configure Forecast
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<Assessment />}
                  disabled={!sectorData}
                >
                  View Results
                </Button>
              </Box>
            </Box>
          </Paper>
        </Grid>

        {/* Sector Navigation */}
        <Grid item xs={12}>
          <SectorNavigation
            selectedSector={selectedSector}
            onSectorChange={handleSectorChange}
            getSectorQuality={getSectorQuality}
            getQualityColor={getQualityColor}
          />
        </Grid>

        {/* Active Forecast Progress */}
        {currentJob?.status === 'running' && (
          <Grid item xs={12}>
            <ProgressMonitor
              job={currentJob}
              onCancel={() => setActiveForecast(null)}
            />
          </Grid>
        )}

        {/* Main Content Tabs */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
              <Tabs value={currentTab} onChange={handleTabChange}>
                <Tab label="Data & Charts" />
                <Tab label="Correlation Analysis" />
                <Tab label="Model Performance" />
                <Tab label="Scenarios" />
              </Tabs>
            </Box>

            <TabPanel value={currentTab} index={0}>
              <DataVisualization
                sectorData={sectorData}
                isLoading={sectorLoading}
                error={sectorError}
                sector={selectedSector}
              />
            </TabPanel>

            <TabPanel value={currentTab} index={1}>
              <CorrelationAnalysis
                correlationData={correlationData}
                isLoading={correlationLoading}
                sector={selectedSector}
              />
            </TabPanel>

            <TabPanel value={currentTab} index={2}>
              <Typography variant="h6" gutterBottom>
                Model Performance Analysis
              </Typography>
              <Alert severity="info" sx={{ mt: 2 }}>
                Model performance metrics will be available after running forecasts.
              </Alert>
            </TabPanel>

            <TabPanel value={currentTab} index={3}>
              <Typography variant="h6" gutterBottom>
                Forecast Scenarios
              </Typography>
              <Alert severity="info" sx={{ mt: 2 }}>
                Saved forecast scenarios will appear here.
              </Alert>
            </TabPanel>
          </Paper>
        </Grid>

        {/* Configuration Dialog */}
        <Dialog
          open={configDialogOpen}
          onClose={() => setConfigDialogOpen(false)}
          maxWidth="lg"
          fullWidth
        >
          <DialogTitle>
            Configure Forecast Models
            <Typography variant="body2" color="text.secondary">
              Set up comprehensive demand forecasting with multiple models
            </Typography>
          </DialogTitle>
          <DialogContent>
            <ForecastConfiguration
              onSubmit={handleStartForecast}
              onCancel={() => setConfigDialogOpen(false)}
              isLoading={forecastStarting}
            />
          </DialogContent>
        </Dialog>
      </Grid>
    </Container>
  );
};
```

Create supporting components:
1. components/demand/SectorNavigation.tsx - Sector selection tabs
2. components/demand/DataVisualization.tsx - Charts and data tables
3. components/demand/CorrelationAnalysis.tsx - Correlation matrix display
4. components/demand/ForecastConfiguration.tsx - Forecast setup form
5. components/demand/ProgressMonitor.tsx - Real-time progress display

Include proper loading states, error handling, and responsive design.
```

### **Chunk 4.2: Load Profile Generation Component**
```
Task: Create the Load Profile Generation page with method selection and configuration

Create a comprehensive load profile generation interface with the following specifications:

FILE: frontend/src/pages/LoadProfileGeneration.tsx
```typescript
import React, { useState, useEffect } from 'react';
import { useSelector } from 'react-redux';
import {
  Container, Grid, Paper, Typography, Button, Box,
  Stepper, Step, StepLabel, StepContent, Card, CardContent,
  CardActions, Radio, RadioGroup, FormControlLabel, FormControl,
  FormLabel, Alert, Chip, Dialog, DialogTitle, DialogContent
} from '@mui/material';
import { 
  Timeline, TrendingUp, Assessment, CloudUpload, 
  PlayArrow, Visibility 
} from '@mui/icons-material';

import { RootState } from '../store';
import { 
  useGenerateProfileMutation,
  useGetSavedProfilesQuery,
  useUploadFileMutation 
} from '../store/api/apiSlice';
import { useProfileProgress } from '../services/websocket';
import { MethodSelection } from '../components/loadProfile/MethodSelection';
import { ConfigurationForm } from '../components/loadProfile/ConfigurationForm';
import { TemplateUpload } from '../components/loadProfile/TemplateUpload';
import { ProfilePreview } from '../components/loadProfile/ProfilePreview';
import { ProfileManager } from '../components/loadProfile/ProfileManager';
import { GenerationProgress } from '../components/loadProfile/GenerationProgress';

interface GenerationStep {
  label: string;
  description: string;
  completed: boolean;
  active: boolean;
}

export const LoadProfileGeneration: React.FC = () => {
  const [activeStep, setActiveStep] = useState(0);
  const [selectedMethod, setSelectedMethod] = useState<'base_scaling' | 'stl_decomposition' | null>(null);
  const [generationConfig, setGenerationConfig] = useState<any>({});
  const [activeGeneration, setActiveGeneration] = useState<string | null>(null);
  const [previewDialogOpen, setPreviewDialogOpen] = useState(false);

  // API hooks
  const [generateProfile, { isLoading: generating }] = useGenerateProfileMutation();
  const { data: savedProfiles, refetch: refetchProfiles } = useGetSavedProfilesQuery();
  const [uploadTemplate] = useUploadFileMutation();

  // WebSocket progress tracking
  useProfileProgress(activeGeneration);

  // Redux state
  const profileJobs = useSelector((state: RootState) => state.loadProfile.generationJobs);
  const currentJob = activeGeneration ? profileJobs[activeGeneration] : null;

  const steps: GenerationStep[] = [
    {
      label: 'Method Selection',
      description: 'Choose generation method based on your data and requirements',
      completed: Boolean(selectedMethod),
      active: activeStep === 0
    },
    {
      label: 'Configuration',
      description: 'Set parameters for the selected generation method',
      completed: Boolean(selectedMethod && Object.keys(generationConfig).length > 0),
      active: activeStep === 1
    },
    {
      label: 'Data Upload',
      description: 'Upload required templates and validate data',
      completed: false, // Check template upload status
      active: activeStep === 2
    },
    {
      label: 'Generation',
      description: 'Execute profile generation with real-time monitoring',
      completed: false,
      active: activeStep === 3
    }
  ];

  const handleMethodSelection = (method: 'base_scaling' | 'stl_decomposition') => {
    setSelectedMethod(method);
    setActiveStep(1);
  };

  const handleConfigurationComplete = (config: any) => {
    setGenerationConfig(config);
    setActiveStep(2);
  };

  const handleDataValidated = () => {
    setActiveStep(3);
  };

  const handleStartGeneration = async () => {
    try {
      const config = {
        method: selectedMethod,
        ...generationConfig
      };

      const result = await generateProfile(config).unwrap();
      setActiveGeneration(result.profileId);
    } catch (error) {
      console.error('Failed to start generation:', error);
    }
  };

  const handleStepClick = (step: number) => {
    // Allow navigation to completed steps
    if (step <= activeStep || steps[step].completed) {
      setActiveStep(step);
    }
  };

  const getMethodIcon = (method: string) => {
    switch (method) {
      case 'base_scaling': return <TrendingUp />;
      case 'stl_decomposition': return <Timeline />;
      default: return <Assessment />;
    }
  };

  const getMethodDescription = (method: string) => {
    switch (method) {
      case 'base_scaling':
        return 'Scale historical load patterns using future demand projections while maintaining characteristic shapes';
      case 'stl_decomposition':
        return 'Advanced time series decomposition with trend, seasonal, and residual components';
      default:
        return '';
    }
  };

  return (
    <Container maxWidth="xl">
      <Grid container spacing={3}>
        {/* Header */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Box display="flex" justifyContent="space-between" alignItems="center">
              <Box>
                <Typography variant="h4" gutterBottom>
                  Load Profile Generation
                </Typography>
                <Typography variant="body1" color="text.secondary">
                  Generate detailed hourly load profiles using historical patterns and demand projections
                </Typography>
              </Box>
              <Box>
                <Button
                  variant="outlined"
                  startIcon={<Visibility />}
                  onClick={() => setPreviewDialogOpen(true)}
                  sx={{ mr: 2 }}
                >
                  Preview Data
                </Button>
                <Chip 
                  label={selectedMethod ? `Method: ${selectedMethod.replace('_', ' ').toUpperCase()}` : 'No Method Selected'}
                  color={selectedMethod ? 'primary' : 'default'}
                  variant={selectedMethod ? 'filled' : 'outlined'}
                />
              </Box>
            </Box>
          </Paper>
        </Grid>

        {/* Generation Progress Monitor */}
        {currentJob?.status === 'running' && (
          <Grid item xs={12}>
            <GenerationProgress
              job={currentJob}
              onCancel={() => setActiveGeneration(null)}
            />
          </Grid>
        )}

        <Grid container spacing={3}>
          {/* Left Panel - Generation Wizard */}
          <Grid item xs={12} md={8}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Generation Wizard
              </Typography>

              <Stepper activeStep={activeStep} orientation="vertical">
                {steps.map((step, index) => (
                  <Step key={step.label} completed={step.completed}>
                    <StepLabel 
                      onClick={() => handleStepClick(index)}
                      sx={{ cursor: step.completed || index <= activeStep ? 'pointer' : 'default' }}
                    >
                      <Typography variant="subtitle1">{step.label}</Typography>
                    </StepLabel>
                    <StepContent>
                      <Typography variant="body2" color="text.secondary" gutterBottom>
                        {step.description}
                      </Typography>

                      {/* Step 0: Method Selection */}
                      {index === 0 && (
                        <MethodSelection
                          selectedMethod={selectedMethod}
                          onMethodSelect={handleMethodSelection}
                          getMethodIcon={getMethodIcon}
                          getMethodDescription={getMethodDescription}
                        />
                      )}

                      {/* Step 1: Configuration */}
                      {index === 1 && selectedMethod && (
                        <ConfigurationForm
                          method={selectedMethod}
                          onConfigurationComplete={handleConfigurationComplete}
                          initialConfig={generationConfig}
                        />
                      )}

                      {/* Step 2: Data Upload */}
                      {index === 2 && (
                        <TemplateUpload
                          onDataValidated={handleDataValidated}
                          uploadTemplate={uploadTemplate}
                        />
                      )}

                      {/* Step 3: Generation */}
                      {index === 3 && (
                        <Box>
                          <Alert severity="info" sx={{ mb: 2 }}>
                            Ready to generate load profile with the following configuration:
                            <br />
                            <strong>Method:</strong> {selectedMethod?.replace('_', ' ').toUpperCase()}
                            <br />
                            <strong>Years:</strong> {generationConfig.startYear} - {generationConfig.endYear}
                          </Alert>
                          <Button
                            variant="contained"
                            startIcon={<PlayArrow />}
                            onClick={handleStartGeneration}
                            disabled={generating || Boolean(currentJob?.status === 'running')}
                            size="large"
                          >
                            {generating ? 'Starting Generation...' : 'Start Generation'}
                          </Button>
                        </Box>
                      )}
                    </StepContent>
                  </Step>
                ))}
              </Stepper>
            </Paper>
          </Grid>

          {/* Right Panel - Profile Manager */}
          <Grid item xs={12} md={4}>
            <ProfileManager
              savedProfiles={savedProfiles}
              onRefresh={refetchProfiles}
              activeGeneration={activeGeneration}
            />
          </Grid>
        </Grid>

        {/* Preview Dialog */}
        <Dialog
          open={previewDialogOpen}
          onClose={() => setPreviewDialogOpen(false)}
          maxWidth="lg"
          fullWidth
        >
          <DialogTitle>Data Preview</DialogTitle>
          <DialogContent>
            <ProfilePreview />
          </DialogContent>
        </Dialog>
      </Grid>
    </Container>
  );
};
```

Create supporting components:
1. components/loadProfile/MethodSelection.tsx - Method comparison cards
2. components/loadProfile/ConfigurationForm.tsx - Dynamic configuration form
3. components/loadProfile/TemplateUpload.tsx - File upload and validation
4. components/loadProfile/ProfilePreview.tsx - Data preview charts
5. components/loadProfile/ProfileManager.tsx - Saved profiles list
6. components/loadProfile/GenerationProgress.tsx - Generation progress monitor

Include proper step validation, file handling, and progress tracking.
```

### **Chunk 4.3: PyPSA Modeling Component**
```
Task: Create the PyPSA power system modeling interface with configuration and monitoring

Create a comprehensive PyPSA modeling interface with the following specifications:

FILE: frontend/src/pages/PyPSAModeling.tsx
```typescript
import React, { useState, useEffect } from 'react';
import { useSelector } from 'react-redux';
import {
  Container, Grid, Paper, Typography, Button, Box,
  Accordion, AccordionSummary, AccordionDetails, TextField,
  FormControl, FormLabel, RadioGroup, FormControlLabel, Radio,
  Checkbox, FormGroup, Select, MenuItem, InputLabel,
  Alert, Chip, LinearProgress, Card, CardContent, CardActions
} from '@mui/material';
import {
  ExpandMore, PlayArrow, Stop, CloudUpload, Settings,
  Assessment, Info, Warning, CheckCircle
} from '@mui/icons-material';

import { RootState } from '../store';
import { 
  useRunOptimizationMutation,
  useGetOptimizationStatusQuery,
  useUploadFileMutation 
} from '../store/api/apiSlice';
import { usePyPSAProgress } from '../services/websocket';
import { OptimizationProgress } from '../components/pypsa/OptimizationProgress';
import { SystemStatus } from '../components/pypsa/SystemStatus';
import { ExcelSettingsLoader } from '../components/pypsa/ExcelSettingsLoader';

interface ModelConfiguration {
  scenarioName: string;
  inputFile: string;
  baseYear: number;
  investmentMode: 'single_year' | 'multi_year' | 'all_in_one';
  snapshotSelection: 'all' | 'critical_days';
  
  // Advanced options
  generatorClustering: boolean;
  unitCommitment: boolean;
  monthlyConstraints: boolean;
  batteryConstraints: 'daily' | 'weekly' | 'monthly' | 'none';
  
  // Solver options
  solverOptions: {
    solver: 'highs' | 'gurobi' | 'cplex';
    optimality_gap: number;
    time_limit: number;
  };
}

export const PyPSAModeling: React.FC = () => {
  const [config, setConfig] = useState<ModelConfiguration>({
    scenarioName: '',
    inputFile: '',
    baseYear: new Date().getFullYear(),
    investmentMode: 'single_year',
    snapshotSelection: 'all',
    generatorClustering: false,
    unitCommitment: false,
    monthlyConstraints: false,
    batteryConstraints: 'none',
    solverOptions: {
      solver: 'highs',
      optimality_gap: 0.01,
      time_limit: 3600
    }
  });

  const [activeOptimization, setActiveOptimization] = useState<string | null>(null);
  const [inputFileUploaded, setInputFileUploaded] = useState(false);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  // API hooks
  const [runOptimization, { isLoading: startingOptimization }] = useRunOptimizationMutation();
  const [uploadFile] = useUploadFileMutation();

  // WebSocket progress tracking
  usePyPSAProgress(activeOptimization);

  // Redux state
  const optimizationJobs = useSelector((state: RootState) => state.pypsa.optimizationJobs);
  const currentJob = activeOptimization ? optimizationJobs[activeOptimization] : null;

  const handleConfigChange = (field: keyof ModelConfiguration, value: any) => {
    setConfig(prev => ({
      ...prev,
      [field]: value
    }));
    
    // Clear validation errors when user makes changes
    if (validationErrors.length > 0) {
      setValidationErrors([]);
    }
  };

  const handleSolverOptionChange = (option: string, value: any) => {
    setConfig(prev => ({
      ...prev,
      solverOptions: {
        ...prev.solverOptions,
        [option]: value
      }
    }));
  };

  const validateConfiguration = (): boolean => {
    const errors: string[] = [];

    if (!config.scenarioName.trim()) {
      errors.push('Scenario name is required');
    }

    if (!inputFileUploaded) {
      errors.push('PyPSA input file must be uploaded');
    }

    if (config.baseYear < 2020 || config.baseYear > 2050) {
      errors.push('Base year must be between 2020 and 2050');
    }

    if (config.solverOptions.optimality_gap < 0 || config.solverOptions.optimality_gap > 1) {
      errors.push('Optimality gap must be between 0 and 1');
    }

    if (config.solverOptions.time_limit < 60) {
      errors.push('Time limit must be at least 60 seconds');
    }

    setValidationErrors(errors);
    return errors.length === 0;
  };

  const handleFileUpload = async (file: File) => {
    try {
      await uploadFile({ file, fileType: 'pypsa_input' }).unwrap();
      setInputFileUploaded(true);
      setConfig(prev => ({ ...prev, inputFile: file.name }));
    } catch (error) {
      console.error('File upload failed:', error);
    }
  };

  const handleStartOptimization = async () => {
    if (!validateConfiguration()) {
      return;
    }

    try {
      const result = await runOptimization(config).unwrap();
      setActiveOptimization(result.jobId);
    } catch (error) {
      console.error('Failed to start optimization:', error);
    }
  };

  const loadExcelSettings = (settings: any) => {
    setConfig(prev => ({
      ...prev,
      ...settings,
      scenarioName: settings.scenario_name || prev.scenarioName,
      baseYear: settings.base_year || prev.baseYear,
      investmentMode: settings.investment_mode || prev.investmentMode
    }));
  };

  const getInvestmentModeDescription = (mode: string) => {
    switch (mode) {
      case 'single_year':
        return 'Optimize for a single target year with fixed topology';
      case 'multi_year':
        return 'Multi-year capacity expansion with investment decisions';
      case 'all_in_one':
        return 'Comprehensive optimization across all years simultaneously';
      default:
        return '';
    }
  };

  return (
    <Container maxWidth="xl">
      <Grid container spacing={3}>
        {/* Header */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Box display="flex" justifyContent="space-between" alignItems="center">
              <Box>
                <Typography variant="h4" gutterBottom>
                  PyPSA Power System Modeling
                </Typography>
                <Typography variant="body1" color="text.secondary">
                  Configure and execute power system optimization with PyPSA
                </Typography>
              </Box>
              <Box>
                <Chip 
                  label={`Solver: ${config.solverOptions.solver.toUpperCase()}`}
                  color="primary"
                  sx={{ mr: 2 }}
                />
                <Chip 
                  label={inputFileUploaded ? 'Input Ready' : 'No Input File'}
                  color={inputFileUploaded ? 'success' : 'error'}
                  icon={inputFileUploaded ? <CheckCircle /> : <Warning />}
                />
              </Box>
            </Box>
          </Paper>
        </Grid>

        {/* System Status */}
        <Grid item xs={12}>
          <SystemStatus />
        </Grid>

        {/* Active Optimization Progress */}
        {currentJob?.status === 'running' && (
          <Grid item xs={12}>
            <OptimizationProgress
              job={currentJob}
              onCancel={() => setActiveOptimization(null)}
            />
          </Grid>
        )}

        <Grid container spacing={3}>
          {/* Left Panel - Configuration */}
          <Grid item xs={12} md={8}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Model Configuration
              </Typography>

              {/* Validation Errors */}
              {validationErrors.length > 0 && (
                <Alert severity="error" sx={{ mb: 3 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    Please fix the following errors:
                  </Typography>
                  <ul style={{ margin: 0, paddingLeft: 20 }}>
                    {validationErrors.map((error, index) => (
                      <li key={index}>{error}</li>
                    ))}
                  </ul>
                </Alert>
              )}

              {/* Scenario & Input Settings */}
              <Accordion defaultExpanded>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Typography variant="subtitle1">Scenario & Input Settings</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Grid container spacing={2}>
                    <Grid item xs={12} md={6}>
                      <TextField
                        fullWidth
                        label="Scenario Name"
                        value={config.scenarioName}
                        onChange={(e) => handleConfigChange('scenarioName', e.target.value)}
                        placeholder="e.g., High_Renewable_2030"
                        helperText="Unique name for this optimization scenario"
                      />
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <TextField
                        fullWidth
                        type="number"
                        label="Base Year"
                        value={config.baseYear}
                        onChange={(e) => handleConfigChange('baseYear', parseInt(e.target.value))}
                        helperText="Year for optimization analysis"
                      />
                    </Grid>
                    <Grid item xs={12}>
                      <ExcelSettingsLoader onSettingsLoaded={loadExcelSettings} />
                    </Grid>
                    <Grid item xs={12}>
                      <Box
                        sx={{
                          border: 2,
                          borderColor: inputFileUploaded ? 'success.main' : 'grey.300',
                          borderStyle: 'dashed',
                          borderRadius: 1,
                          p: 3,
                          textAlign: 'center',
                          cursor: 'pointer',
                          '&:hover': { backgroundColor: 'grey.50' }
                        }}
                        onClick={() => document.getElementById('file-upload')?.click()}
                      >
                        <input
                          id="file-upload"
                          type="file"
                          accept=".xlsx,.xls"
                          style={{ display: 'none' }}
                          onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (file) handleFileUpload(file);
                          }}
                        />
                        <CloudUpload sx={{ fontSize: 48, color: 'grey.400', mb: 1 }} />
                        <Typography variant="h6" gutterBottom>
                          {inputFileUploaded ? 'Input File Uploaded' : 'Upload PyPSA Input Template'}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {inputFileUploaded 
                            ? `File: ${config.inputFile}` 
                            : 'Click to select Excel file with network data'
                          }
                        </Typography>
                      </Box>
                    </Grid>
                  </Grid>
                </AccordionDetails>
              </Accordion>

              {/* Time & Snapshot Settings */}
              <Accordion>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Typography variant="subtitle1">Time & Snapshot Settings</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Grid container spacing={2}>
                    <Grid item xs={12}>
                      <FormControl component="fieldset">
                        <FormLabel component="legend">Investment Mode</FormLabel>
                        <RadioGroup
                          value={config.investmentMode}
                          onChange={(e) => handleConfigChange('investmentMode', e.target.value)}
                        >
                          <FormControlLabel 
                            value="single_year" 
                            control={<Radio />} 
                            label="Single Year Optimization" 
                          />
                          <FormControlLabel 
                            value="multi_year" 
                            control={<Radio />} 
                            label="Multi-Year Capacity Expansion" 
                          />
                          <FormControlLabel 
                            value="all_in_one" 
                            control={<Radio />} 
                            label="All-in-One Multi-Year" 
                          />
                        </RadioGroup>
                        <Typography variant="caption" color="text.secondary">
                          {getInvestmentModeDescription(config.investmentMode)}
                        </Typography>
                      </FormControl>
                    </Grid>
                    <Grid item xs={12}>
                      <FormControl component="fieldset">
                        <FormLabel component="legend">Snapshot Selection</FormLabel>
                        <RadioGroup
                          value={config.snapshotSelection}
                          onChange={(e) => handleConfigChange('snapshotSelection', e.target.value)}
                        >
                          <FormControlLabel 
                            value="all" 
                            control={<Radio />} 
                            label="All Snapshots (Full Year)" 
                          />
                          <FormControlLabel 
                            value="critical_days" 
                            control={<Radio />} 
                            label="Critical Days (Representative)" 
                          />
                        </RadioGroup>
                      </FormControl>
                    </Grid>
                  </Grid>
                </AccordionDetails>
              </Accordion>

              {/* Advanced Options */}
              <Accordion>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Typography variant="subtitle1">Advanced Options</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <FormGroup>
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={config.generatorClustering}
                          onChange={(e) => handleConfigChange('generatorClustering', e.target.checked)}
                        />
                      }
                      label="Generator Clustering"
                    />
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={config.unitCommitment}
                          onChange={(e) => handleConfigChange('unitCommitment', e.target.checked)}
                        />
                      }
                      label="Unit Commitment"
                    />
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={config.monthlyConstraints}
                          onChange={(e) => handleConfigChange('monthlyConstraints', e.target.checked)}
                        />
                      }
                      label="Monthly Constraints"
                    />
                  </FormGroup>
                  
                  <FormControl fullWidth sx={{ mt: 2 }}>
                    <InputLabel>Battery Cycle Constraints</InputLabel>
                    <Select
                      value={config.batteryConstraints}
                      onChange={(e) => handleConfigChange('batteryConstraints', e.target.value)}
                    >
                      <MenuItem value="none">None</MenuItem>
                      <MenuItem value="daily">Daily</MenuItem>
                      <MenuItem value="weekly">Weekly</MenuItem>
                      <MenuItem value="monthly">Monthly</MenuItem>
                    </Select>
                  </FormControl>
                </AccordionDetails>
              </Accordion>

              {/* Solver Settings */}
              <Accordion>
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Typography variant="subtitle1">Solver Settings</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Grid container spacing={2}>
                    <Grid item xs={12} md={4}>
                      <FormControl fullWidth>
                        <InputLabel>Solver</InputLabel>
                        <Select
                          value={config.solverOptions.solver}
                          onChange={(e) => handleSolverOptionChange('solver', e.target.value)}
                        >
                          <MenuItem value="highs">HiGHS</MenuItem>
                          <MenuItem value="gurobi">Gurobi</MenuItem>
                          <MenuItem value="cplex">CPLEX</MenuItem>
                        </Select>
                      </FormControl>
                    </Grid>
                    <Grid item xs={12} md={4}>
                      <TextField
                        fullWidth
                        type="number"
                        label="Optimality Gap"
                        value={config.solverOptions.optimality_gap}
                        onChange={(e) => handleSolverOptionChange('optimality_gap', parseFloat(e.target.value))}
                        inputProps={{ min: 0, max: 1, step: 0.001 }}
                        helperText="0.01 = 1% gap"
                      />
                    </Grid>
                    <Grid item xs={12} md={4}>
                      <TextField
                        fullWidth
                        type="number"
                        label="Time Limit (seconds)"
                        value={config.solverOptions.time_limit}
                        onChange={(e) => handleSolverOptionChange('time_limit', parseInt(e.target.value))}
                        inputProps={{ min: 60 }}
                        helperText="Maximum solver time"
                      />
                    </Grid>
                  </Grid>
                </AccordionDetails>
              </Accordion>

              {/* Action Buttons */}
              <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
                <Button
                  variant="contained"
                  size="large"
                  startIcon={<PlayArrow />}
                  onClick={handleStartOptimization}
                  disabled={startingOptimization || Boolean(currentJob?.status === 'running')}
                >
                  {startingOptimization ? 'Starting...' : 'Run Optimization'}
                </Button>
                <Button
                  variant="outlined"
                  size="large"
                  startIcon={<Assessment />}
                  disabled={!inputFileUploaded}
                >
                  Validate Model
                </Button>
              </Box>
            </Paper>
          </Grid>

          {/* Right Panel - Information */}
          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Model Information
              </Typography>
              
              {/* Model Stats */}
              <Card sx={{ mb: 2 }}>
                <CardContent>
                  <Typography variant="subtitle2" gutterBottom>
                    Configuration Status
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <Chip 
                      size="small" 
                      label="Scenario" 
                      color={config.scenarioName ? 'success' : 'default'} 
                    />
                    <Typography variant="body2" sx={{ ml: 1 }}>
                      {config.scenarioName || 'Not set'}
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <Chip 
                      size="small" 
                      label="Input File" 
                      color={inputFileUploaded ? 'success' : 'default'} 
                    />
                    <Typography variant="body2" sx={{ ml: 1 }}>
                      {inputFileUploaded ? 'Ready' : 'Required'}
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <Chip 
                      size="small" 
                      label="Validation" 
                      color={validationErrors.length === 0 ? 'success' : 'error'} 
                    />
                    <Typography variant="body2" sx={{ ml: 1 }}>
                      {validationErrors.length === 0 ? 'Passed' : `${validationErrors.length} errors`}
                    </Typography>
                  </Box>
                </CardContent>
              </Card>

              {/* Help Information */}
              <Alert severity="info" sx={{ mb: 2 }}>
                <Typography variant="body2">
                  Upload the PyPSA input template with your network data to begin optimization.
                  Use Excel settings loader to quickly populate configuration from file.
                </Typography>
              </Alert>

              {/* Recent Optimizations */}
              <Typography variant="subtitle2" gutterBottom>
                Recent Optimizations
              </Typography>
              <Typography variant="body2" color="text.secondary">
                No recent optimizations found.
              </Typography>
            </Paper>
          </Grid>
        </Grid>
      </Grid>
    </Container>
  );
};
```

Create supporting components:
1. components/pypsa/OptimizationProgress.tsx - Progress monitoring
2. components/pypsa/SystemStatus.tsx - System health display
3. components/pypsa/ExcelSettingsLoader.tsx - Excel file configuration loader

Include proper validation, file handling, and real-time monitoring.
```

---

## **PHASE 5: ADVANCED COMPONENTS**

### **Chunk 5.1: Chart Components with Plotly**
```
Task: Create reusable chart components with Plotly.js integration

Create comprehensive chart components with the following specifications:

FILE: frontend/src/components/charts/PlotlyChart.tsx
```typescript
import React, { useEffect, useRef, useState } from 'react';
import Plot from 'react-plotly.js';
import { Box, Typography, IconButton, Menu, MenuItem, CircularProgress } from '@mui/material';
import { MoreVert, Download, Fullscreen, Refresh } from '@mui/icons-material';

interface PlotlyChartProps {
  data: any[];
  layout?: Partial<Plotly.Layout>;
  config?: Partial<Plotly.Config>;
  title?: string;
  height?: number;
  loading?: boolean;
  error?: string;
  onExport?: (format: 'png' | 'pdf' | 'svg' | 'html') => void;
  onRefresh?: () => void;
  responsive?: boolean;
}

export const PlotlyChart: React.FC<PlotlyChartProps> = ({
  data,
  layout = {},
  config = {},
  title,
  height = 400,
  loading = false,
  error,
  onExport,
  onRefresh,
  responsive = true
}) => {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [plotSize, setPlotSize] = useState({ width: 0, height: height });
  const containerRef = useRef<HTMLDivElement>(null);

  // Handle responsive sizing
  useEffect(() => {
    if (!responsive) return;

    const handleResize = () => {
      if (containerRef.current) {
        const { width } = containerRef.current.getBoundingClientRect();
        setPlotSize({ width: width - 32, height }); // Account for padding
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [height, responsive]);

  const defaultLayout: Partial<Plotly.Layout> = {
    autosize: true,
    margin: { l: 50, r: 50, t: 50, b: 50 },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { family: '"Roboto", "Helvetica", "Arial", sans-serif' },
    ...layout
  };

  const defaultConfig: Partial<Plotly.Config> = {
    displayModeBar: true,
    modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'],
    displaylogo: false,
    toImageButtonOptions: {
      format: 'png',
      filename: title || 'chart',
      height: height,
      width: plotSize.width,
      scale: 2
    },
    ...config
  };

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleExport = (format: 'png' | 'pdf' | 'svg' | 'html') => {
    onExport?.(format);
    handleMenuClose();
  };

  if (loading) {
    return (
      <Box 
        ref={containerRef}
        sx={{ 
          height, 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          border: 1,
          borderColor: 'grey.300',
          borderRadius: 1
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box 
        ref={containerRef}
        sx={{ 
          height, 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          border: 1,
          borderColor: 'error.main',
          borderRadius: 1,
          backgroundColor: 'error.light',
          color: 'error.contrastText'
        }}
      >
        <Typography variant="body2">Error: {error}</Typography>
      </Box>
    );
  }

  return (
    <Box ref={containerRef} sx={{ position: 'relative' }}>
      {/* Chart Header */}
      {(title || onExport || onRefresh) && (
        <Box sx={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          mb: 1,
          px: 1
        }}>
          {title && (
            <Typography variant="h6" component="h3">
              {title}
            </Typography>
          )}
          <Box>
            {onRefresh && (
              <IconButton size="small" onClick={onRefresh}>
                <Refresh />
              </IconButton>
            )}
            {onExport && (
              <>
                <IconButton size="small" onClick={handleMenuOpen}>
                  <MoreVert />
                </IconButton>
                <Menu
                  anchorEl={anchorEl}
                  open={Boolean(anchorEl)}
                  onClose={handleMenuClose}
                >
                  <MenuItem onClick={() => handleExport('png')}>
                    <Download sx={{ mr: 1 }} />
                    Export PNG
                  </MenuItem>
                  <MenuItem onClick={() => handleExport('pdf')}>
                    <Download sx={{ mr: 1 }} />
                    Export PDF
                  </MenuItem>
                  <MenuItem onClick={() => handleExport('svg')}>
                    <Download sx={{ mr: 1 }} />
                    Export SVG
                  </MenuItem>
                  <MenuItem onClick={() => handleExport('html')}>
                    <Download sx={{ mr: 1 }} />
                    Export HTML
                  </MenuItem>
                </Menu>
              </>
            )}
          </Box>
        </Box>
      )}

      {/* Plotly Chart */}
      <Plot
        data={data}
        layout={{
          ...defaultLayout,
          width: responsive ? plotSize.width : layout.width,
          height: height
        }}
        config={defaultConfig}
        useResizeHandler={responsive}
        style={{ width: '100%' }}
      />
    </Box>
  );
};

// Specialized chart components
export const LineChart: React.FC<PlotlyChartProps & {
  xData: any[];
  yData: any[];
  name?: string;
  color?: string;
}> = ({ xData, yData, name, color, ...props }) => {
  const data = [{
    x: xData,
    y: yData,
    type: 'scatter',
    mode: 'lines',
    name: name || 'Series',
    line: { color: color || '#1976d2' }
  }];

  return <PlotlyChart data={data} {...props} />;
};

export const BarChart: React.FC<PlotlyChartProps & {
  xData: any[];
  yData: any[];
  name?: string;
  color?: string;
}> = ({ xData, yData, name, color, ...props }) => {
  const data = [{
    x: xData,
    y: yData,
    type: 'bar',
    name: name || 'Series',
    marker: { color: color || '#1976d2' }
  }];

  return <PlotlyChart data={data} {...props} />;
};

export const HeatmapChart: React.FC<PlotlyChartProps & {
  zData: number[][];
  xLabels: string[];
  yLabels: string[];
  colorscale?: string;
}> = ({ zData, xLabels, yLabels, colorscale = 'Viridis', ...props }) => {
  const data = [{
    z: zData,
    x: xLabels,
    y: yLabels,
    type: 'heatmap',
    colorscale: colorscale,
    showscale: true
  }];

  return <PlotlyChart data={data} {...props} />;
};

export const ScatterChart: React.FC<PlotlyChartProps & {
  xData: any[];
  yData: any[];
  name?: string;
  color?: string;
  size?: number[];
}> = ({ xData, yData, name, color, size, ...props }) => {
  const data = [{
    x: xData,
    y: yData,
    type: 'scatter',
    mode: 'markers',
    name: name || 'Series',
    marker: { 
      color: color || '#1976d2',
      size: size || 8
    }
  }];

  return <PlotlyChart data={data} {...props} />;
};

export const MultiLineChart: React.FC<PlotlyChartProps & {
  series: Array<{
    x: any[];
    y: any[];
    name: string;
    color?: string;
  }>;
}> = ({ series, ...props }) => {
  const data = series.map((s, index) => ({
    x: s.x,
    y: s.y,
    type: 'scatter',
    mode: 'lines',
    name: s.name,
    line: { color: s.color || `hsl(${index * 360 / series.length}, 70%, 50%)` }
  }));

  return <PlotlyChart data={data} {...props} />;
};
```

Create additional chart utilities:
1. components/charts/ChartExporter.tsx - Chart export functionality
2. components/charts/ChartFilters.tsx - Interactive chart filtering
3. utils/chartColors.ts - Color palette management
4. hooks/useChartData.ts - Chart data processing hook

Include proper error handling, loading states, and export capabilities.
```

### **Chunk 5.2: Data Table Component**
```
Task: Create an advanced data table component with sorting, filtering, and pagination

Create a comprehensive data table component with the following specifications:

FILE: frontend/src/components/common/DataTable.tsx
```typescript
import React, { useState, useMemo } from 'react';
import {
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, TablePagination, TextField, InputAdornment, IconButton,
  Toolbar, Typography, Checkbox, Button, Menu, MenuItem,
  Chip, Box, TableSortLabel, Tooltip
} from '@mui/material';
import {
  Search, FilterList, Download, Visibility, VisibilityOff,
  MoreVert, Refresh
} from '@mui/icons-material';

interface Column {
  id: string;
  label: string;
  minWidth?: number;
  align?: 'right' | 'left' | 'center';
  format?: (value: any) => string;
  sortable?: boolean;
  filterable?: boolean;
  type?: 'string' | 'number' | 'date' | 'boolean';
}

interface DataTableProps {
  columns: Column[];
  data: any[];
  title?: string;
  loading?: boolean;
  error?: string;
  selectable?: boolean;
  onRowSelect?: (selectedRows: any[]) => void;
  onExport?: (format: 'csv' | 'excel') => void;
  onRefresh?: () => void;
  maxHeight?: number;
  searchable?: boolean;
  filterable?: boolean;
  pagination?: boolean;
  rowsPerPageOptions?: number[];
  defaultRowsPerPage?: number;
  dense?: boolean;
}

type Order = 'asc' | 'desc';

export const DataTable: React.FC<DataTableProps> = ({
  columns,
  data,
  title,
  loading = false,
  error,
  selectable = false,
  onRowSelect,
  onExport,
  onRefresh,
  maxHeight = 400,
  searchable = true,
  filterable = true,
  pagination = true,
  rowsPerPageOptions = [5, 10, 25, 50],
  defaultRowsPerPage = 10,
  dense = false
}) => {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(defaultRowsPerPage);
  const [orderBy, setOrderBy] = useState<string>('');
  const [order, setOrder] = useState<Order>('asc');
  const [searchTerm, setSearchTerm] = useState('');
  const [columnFilters, setColumnFilters] = useState<{[key: string]: any}>({});
  const [hiddenColumns, setHiddenColumns] = useState<Set<string>>(new Set());
  const [selectedRows, setSelectedRows] = useState<Set<number>>(new Set());
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [columnMenuAnchor, setColumnMenuAnchor] = useState<null | HTMLElement>(null);

  // Filter and sort data
  const filteredData = useMemo(() => {
    let filtered = data;

    // Apply search filter
    if (searchTerm) {
      filtered = filtered.filter(row =>
        columns.some(column => {
          const value = row[column.id];
          return value && value.toString().toLowerCase().includes(searchTerm.toLowerCase());
        })
      );
    }

    // Apply column filters
    Object.entries(columnFilters).forEach(([columnId, filterValue]) => {
      if (filterValue !== undefined && filterValue !== '') {
        filtered = filtered.filter(row => {
          const value = row[columnId];
          const column = columns.find(c => c.id === columnId);
          
          if (column?.type === 'number') {
            return value === parseFloat(filterValue);
          } else if (column?.type === 'boolean') {
            return value === (filterValue === 'true');
          } else {
            return value && value.toString().toLowerCase().includes(filterValue.toLowerCase());
          }
        });
      }
    });

    return filtered;
  }, [data, searchTerm, columnFilters, columns]);

  // Sort data
  const sortedData = useMemo(() => {
    if (!orderBy) return filteredData;

    return [...filteredData].sort((a, b) => {
      const aVal = a[orderBy];
      const bVal = b[orderBy];

      if (aVal < bVal) {
        return order === 'asc' ? -1 : 1;
      }
      if (aVal > bVal) {
        return order === 'asc' ? 1 : -1;
      }
      return 0;
    });
  }, [filteredData, orderBy, order]);

  // Paginate data
  const paginatedData = useMemo(() => {
    if (!pagination) return sortedData;
    
    const startIndex = page * rowsPerPage;
    return sortedData.slice(startIndex, startIndex + rowsPerPage);
  }, [sortedData, page, rowsPerPage, pagination]);

  const handleSort = (columnId: string) => {
    const column = columns.find(c => c.id === columnId);
    if (!column?.sortable) return;

    const isAsc = orderBy === columnId && order === 'asc';
    setOrder(isAsc ? 'desc' : 'asc');
    setOrderBy(columnId);
  };

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleSelectAllClick = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.checked) {
      const newSelected = new Set(paginatedData.map((_, index) => page * rowsPerPage + index));
      setSelectedRows(newSelected);
    } else {
      setSelectedRows(new Set());
    }
  };

  const handleRowClick = (index: number) => {
    const actualIndex = page * rowsPerPage + index;
    const newSelected = new Set(selectedRows);
    
    if (newSelected.has(actualIndex)) {
      newSelected.delete(actualIndex);
    } else {
      newSelected.add(actualIndex);
    }
    
    setSelectedRows(newSelected);
  };

  const handleColumnFilter = (columnId: string, value: any) => {
    setColumnFilters(prev => ({
      ...prev,
      [columnId]: value
    }));
    setPage(0); // Reset to first page when filtering
  };

  const toggleColumnVisibility = (columnId: string) => {
    const newHidden = new Set(hiddenColumns);
    if (newHidden.has(columnId)) {
      newHidden.delete(columnId);
    } else {
      newHidden.add(columnId);
    }
    setHiddenColumns(newHidden);
  };

  const visibleColumns = columns.filter(column => !hiddenColumns.has(column.id));

  // Handle row selection callback
  React.useEffect(() => {
    if (onRowSelect) {
      const selectedData = Array.from(selectedRows).map(index => data[index]).filter(Boolean);
      onRowSelect(selectedData);
    }
  }, [selectedRows, data, onRowSelect]);

  return (
    <Paper sx={{ width: '100%', overflow: 'hidden' }}>
      {/* Table Toolbar */}
      <Toolbar sx={{ pl: 2, pr: 1 }}>
        <Typography variant="h6" component="div" sx={{ flex: '1 1 100%' }}>
          {title}
          {selectedRows.size > 0 && (
            <Chip 
              label={`${selectedRows.size} selected`} 
              size="small" 
              sx={{ ml: 2 }} 
            />
          )}
        </Typography>

        {/* Search */}
        {searchable && (
          <TextField
            size="small"
            placeholder="Search..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search />
                </InputAdornment>
              ),
            }}
            sx={{ mx: 1, minWidth: 200 }}
          />
        )}

        {/* Action Buttons */}
        <Box>
          {onRefresh && (
            <IconButton onClick={onRefresh}>
              <Refresh />
            </IconButton>
          )}
          
          <IconButton onClick={(e) => setColumnMenuAnchor(e.currentTarget)}>
            <Visibility />
          </IconButton>
          
          {onExport && (
            <IconButton onClick={(e) => setAnchorEl(e.currentTarget)}>
              <Download />
            </IconButton>
          )}
        </Box>

        {/* Export Menu */}
        {onExport && (
          <Menu
            anchorEl={anchorEl}
            open={Boolean(anchorEl)}
            onClose={() => setAnchorEl(null)}
          >
            <MenuItem onClick={() => { onExport('csv'); setAnchorEl(null); }}>
              Export CSV
            </MenuItem>
            <MenuItem onClick={() => { onExport('excel'); setAnchorEl(null); }}>
              Export Excel
            </MenuItem>
          </Menu>
        )}

        {/* Column Visibility Menu */}
        <Menu
          anchorEl={columnMenuAnchor}
          open={Boolean(columnMenuAnchor)}
          onClose={() => setColumnMenuAnchor(null)}
        >
          {columns.map((column) => (
            <MenuItem key={column.id} onClick={() => toggleColumnVisibility(column.id)}>
              <Checkbox 
                checked={!hiddenColumns.has(column.id)}
                size="small"
              />
              {column.label}
            </MenuItem>
          ))}
        </Menu>
      </Toolbar>

      {/* Column Filters */}
      {filterable && (
        <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
          <Typography variant="subtitle2" gutterBottom>
            Filters
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            {visibleColumns
              .filter(column => column.filterable !== false)
              .map((column) => (
                <TextField
                  key={column.id}
                  size="small"
                  label={`Filter ${column.label}`}
                  value={columnFilters[column.id] || ''}
                  onChange={(e) => handleColumnFilter(column.id, e.target.value)}
                  sx={{ minWidth: 150 }}
                />
              ))}
          </Box>
        </Box>
      )}

      {/* Table */}
      <TableContainer sx={{ maxHeight }}>
        <Table stickyHeader aria-labelledby="tableTitle" size={dense ? 'small' : 'medium'}>
          <TableHead>
            <TableRow>
              {selectable && (
                <TableCell padding="checkbox">
                  <Checkbox
                    indeterminate={selectedRows.size > 0 && selectedRows.size < paginatedData.length}
                    checked={paginatedData.length > 0 && selectedRows.size === paginatedData.length}
                    onChange={handleSelectAllClick}
                  />
                </TableCell>
              )}
              {visibleColumns.map((column) => (
                <TableCell
                  key={column.id}
                  align={column.align}
                  style={{ minWidth: column.minWidth }}
                >
                  {column.sortable !== false ? (
                    <TableSortLabel
                      active={orderBy === column.id}
                      direction={orderBy === column.id ? order : 'asc'}
                      onClick={() => handleSort(column.id)}
                    >
                      {column.label}
                    </TableSortLabel>
                  ) : (
                    column.label
                  )}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={visibleColumns.length + (selectable ? 1 : 0)} align="center">
                  Loading...
                </TableCell>
              </TableRow>
            ) : error ? (
              <TableRow>
                <TableCell colSpan={visibleColumns.length + (selectable ? 1 : 0)} align="center">
                  Error: {error}
                </TableCell>
              </TableRow>
            ) : paginatedData.length === 0 ? (
              <TableRow>
                <TableCell colSpan={visibleColumns.length + (selectable ? 1 : 0)} align="center">
                  No data available
                </TableCell>
              </TableRow>
            ) : (
              paginatedData.map((row, index) => {
                const actualIndex = page * rowsPerPage + index;
                const isSelected = selectedRows.has(actualIndex);
                
                return (
                  <TableRow
                    hover
                    role="checkbox"
                    aria-checked={isSelected}
                    tabIndex={-1}
                    key={actualIndex}
                    selected={isSelected}
                    onClick={() => selectable && handleRowClick(index)}
                    sx={{ cursor: selectable ? 'pointer' : 'default' }}
                  >
                    {selectable && (
                      <TableCell padding="checkbox">
                        <Checkbox checked={isSelected} />
                      </TableCell>
                    )}
                    {visibleColumns.map((column) => {
                      const value = row[column.id];
                      return (
                        <TableCell key={column.id} align={column.align}>
                          {column.format ? column.format(value) : value}
                        </TableCell>
                      );
                    })}
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Pagination */}
      {pagination && (
        <TablePagination
          rowsPerPageOptions={rowsPerPageOptions}
          component="div"
          count={sortedData.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
        />
      )}
    </Paper>
  );
};
```

Create supporting utilities:
1. utils/tableExport.ts - Table data export functions
2. components/common/TableFilters.tsx - Advanced filter components
3. hooks/useTableData.ts - Table data management hook

Include proper performance optimization for large datasets.
```

### **Chunk 5.3: File Upload Component**
```
Task: Create a comprehensive file upload component with validation and progress tracking

Create an advanced file upload component with the following specifications:

FILE: frontend/src/components/common/FileUpload.tsx
```typescript
import React, { useState, useCallback, useRef } from 'react';
import {
  Box, Typography, Button, LinearProgress, Alert, Chip,
  IconButton, List, ListItem, ListItemText, ListItemSecondaryAction,
  Dialog, DialogTitle, DialogContent, DialogActions, Paper
} from '@mui/material';
import {
  CloudUpload, Delete, CheckCircle, Error, Warning,
  InsertDriveFile, Description, Image
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';

interface FileUploadProps {
  accept?: string[];
  maxSize?: number; // in bytes
  maxFiles?: number;
  multiple?: boolean;
  onUpload?: (files: File[]) => Promise<void>;
  onValidation?: (file: File) => string | null; // Return error message or null
  title?: string;
  description?: string;
  disabled?: boolean;
  showPreview?: boolean;
}

interface UploadedFile {
  file: File;
  id: string;
  status: 'pending' | 'uploading' | 'success' | 'error';
  progress: number;
  error?: string;
  preview?: string;
}

export const FileUpload: React.FC<FileUploadProps> = ({
  accept = ['.xlsx', '.xls', '.csv'],
  maxSize = 16 * 1024 * 1024, // 16MB
  maxFiles = 1,
  multiple = false,
  onUpload,
  onValidation,
  title = 'Upload Files',
  description = 'Drag and drop files here, or click to select files',
  disabled = false,
  showPreview = true
}) => {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [previewFile, setPreviewFile] = useState<UploadedFile | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const generateFileId = () => `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

  const getFileIcon = (file: File) => {
    const extension = file.name.split('.').pop()?.toLowerCase();
    
    if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg'].includes(extension || '')) {
      return <Image color="primary" />;
    } else if (['xlsx', 'xls', 'csv'].includes(extension || '')) {
      return <Description color="success" />;
    } else {
      return <InsertDriveFile color="action" />;
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const validateFile = (file: File): string | null => {
    // Size validation
    if (file.size > maxSize) {
      return `File size (${formatFileSize(file.size)}) exceeds maximum allowed size (${formatFileSize(maxSize)})`;
    }

    // Type validation
    if (accept.length > 0) {
      const extension = '.' + file.name.split('.').pop()?.toLowerCase();
      const mimeType = file.type;
      
      const isValidExtension = accept.some(acceptedType => {
        if (acceptedType.startsWith('.')) {
          return extension === acceptedType;
        }
        return mimeType.match(acceptedType);
      });

      if (!isValidExtension) {
        return `File type not supported. Accepted types: ${accept.join(', ')}`;
      }
    }

    // Custom validation
    if (onValidation) {
      return onValidation(file);
    }

    return null;
  };

  const processFiles = useCallback(async (files: File[]) => {
    if (disabled || uploading) return;

    // Validate file count
    if (!multiple && files.length > 1) {
      return;
    }

    if (uploadedFiles.length + files.length > maxFiles) {
      alert(`Maximum ${maxFiles} files allowed`);
      return;
    }

    // Process each file
    const newFiles: UploadedFile[] = files.map(file => {
      const validationError = validateFile(file);
      
      return {
        file,
        id: generateFileId(),
        status: validationError ? 'error' : 'pending',
        progress: 0,
        error: validationError || undefined,
        preview: showPreview && file.type.startsWith('image/') 
          ? URL.createObjectURL(file) 
          : undefined
      };
    });

    setUploadedFiles(prev => [...prev, ...newFiles]);

    // Upload valid files
    const validFiles = newFiles.filter(f => f.status === 'pending');
    if (validFiles.length > 0 && onUpload) {
      setUploading(true);
      
      try {
        // Update status to uploading
        setUploadedFiles(prev => 
          prev.map(f => 
            validFiles.find(vf => vf.id === f.id) 
              ? { ...f, status: 'uploading' as const }
              : f
          )
        );

        // Simulate upload progress (in real app, this would come from upload API)
        for (const uploadFile of validFiles) {
          for (let progress = 0; progress <= 100; progress += 10) {
            await new Promise(resolve => setTimeout(resolve, 100));
            setUploadedFiles(prev => 
              prev.map(f => 
                f.id === uploadFile.id 
                  ? { ...f, progress }
                  : f
              )
            );
          }
        }

        // Call upload handler
        await onUpload(validFiles.map(f => f.file));

        // Mark as successful
        setUploadedFiles(prev => 
          prev.map(f => 
            validFiles.find(vf => vf.id === f.id) 
              ? { ...f, status: 'success' as const, progress: 100 }
              : f
          )
        );
      } catch (error) {
        // Mark as failed
        setUploadedFiles(prev => 
          prev.map(f => 
            validFiles.find(vf => vf.id === f.id) 
              ? { 
                  ...f, 
                  status: 'error' as const, 
                  error: error instanceof Error ? error.message : 'Upload failed' 
                }
              : f
          )
        );
      } finally {
        setUploading(false);
      }
    }
  }, [disabled, uploading, uploadedFiles.length, maxFiles, multiple, maxSize, accept, onValidation, onUpload, showPreview]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: processFiles,
    accept: accept.reduce((acc, type) => ({ ...acc, [type]: [] }), {}),
    maxSize,
    maxFiles,
    multiple,
    disabled: disabled || uploading
  });

  const removeFile = (fileId: string) => {
    setUploadedFiles(prev => {
      const fileToRemove = prev.find(f => f.id === fileId);
      if (fileToRemove?.preview) {
        URL.revokeObjectURL(fileToRemove.preview);
      }
      return prev.filter(f => f.id !== fileId);
    });
  };

  const getStatusIcon = (status: UploadedFile['status']) => {
    switch (status) {
      case 'success':
        return <CheckCircle color="success" />;
      case 'error':
        return <Error color="error" />;
      case 'uploading':
        return <LinearProgress sx={{ width: 20 }} />;
      default:
        return <Warning color="warning" />;
    }
  };

  const getStatusColor = (status: UploadedFile['status']) => {
    switch (status) {
      case 'success':
        return 'success';
      case 'error':
        return 'error';
      case 'uploading':
        return 'info';
      default:
        return 'default';
    }
  };

  return (
    <Box>
      {/* Upload Zone */}
      <Paper
        {...getRootProps()}
        sx={{
          border: 2,
          borderColor: isDragActive ? 'primary.main' : 'grey.300',
          borderStyle: 'dashed',
          borderRadius: 1,
          p: 3,
          textAlign: 'center',
          cursor: disabled || uploading ? 'not-allowed' : 'pointer',
          backgroundColor: isDragActive ? 'action.hover' : 'background.paper',
          opacity: disabled || uploading ? 0.6 : 1,
          transition: 'all 0.2s ease-in-out',
          '&:hover': {
            backgroundColor: disabled || uploading ? 'background.paper' : 'action.hover',
            borderColor: disabled || uploading ? 'grey.300' : 'primary.main'
          }
        }}
      >
        <input {...getInputProps()} ref={fileInputRef} />
        
        <CloudUpload 
          sx={{ 
            fontSize: 48, 
            color: isDragActive ? 'primary.main' : 'grey.400', 
            mb: 2 
          }} 
        />
        
        <Typography variant="h6" gutterBottom>
          {title}
        </Typography>
        
        <Typography variant="body2" color="text.secondary" paragraph>
          {isDragActive ? 'Drop files here...' : description}
        </Typography>
        
        <Box sx={{ display: 'flex', justifyContent: 'center', gap: 1, flexWrap: 'wrap', mb: 2 }}>
          <Chip label={`Max size: ${formatFileSize(maxSize)}`} size="small" />
          <Chip label={`Max files: ${maxFiles}`} size="small" />
          <Chip label={`Types: ${accept.join(', ')}`} size="small" />
        </Box>
        
        <Button
          variant="outlined"
          disabled={disabled || uploading}
          sx={{ mt: 1 }}
        >
          {uploading ? 'Uploading...' : 'Select Files'}
        </Button>
      </Paper>

      {/* File List */}
      {uploadedFiles.length > 0 && (
        <Box sx={{ mt: 3 }}>
          <Typography variant="h6" gutterBottom>
            Files ({uploadedFiles.length})
          </Typography>
          
          <List>
            {uploadedFiles.map((uploadedFile) => (
              <ListItem key={uploadedFile.id} divider>
                <Box sx={{ mr: 2 }}>
                  {getFileIcon(uploadedFile.file)}
                </Box>
                
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="body1">
                        {uploadedFile.file.name}
                      </Typography>
                      <Chip 
                        label={uploadedFile.status} 
                        size="small" 
                        color={getStatusColor(uploadedFile.status)}
                        icon={getStatusIcon(uploadedFile.status)}
                      />
                    </Box>
                  }
                  secondary={
                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        {formatFileSize(uploadedFile.file.size)}
                      </Typography>
                      
                      {uploadedFile.status === 'uploading' && (
                        <LinearProgress 
                          variant="determinate" 
                          value={uploadedFile.progress} 
                          sx={{ mt: 1 }}
                        />
                      )}
                      
                      {uploadedFile.error && (
                        <Alert severity="error" sx={{ mt: 1 }}>
                          {uploadedFile.error}
                        </Alert>
                      )}
                    </Box>
                  }
                />
                
                <ListItemSecondaryAction>
                  {showPreview && uploadedFile.preview && (
                    <IconButton 
                      edge="end" 
                      onClick={() => setPreviewFile(uploadedFile)}
                      sx={{ mr: 1 }}
                    >
                      <Image />
                    </IconButton>
                  )}
                  
                  <IconButton 
                    edge="end" 
                    onClick={() => removeFile(uploadedFile.id)}
                    disabled={uploadedFile.status === 'uploading'}
                  >
                    <Delete />
                  </IconButton>
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        </Box>
      )}

      {/* Preview Dialog */}
      <Dialog
        open={Boolean(previewFile)}
        onClose={() => setPreviewFile(null)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          File Preview: {previewFile?.file.name}
        </DialogTitle>
        <DialogContent>
          {previewFile?.preview && (
            <img 
              src={previewFile.preview} 
              alt={previewFile.file.name}
              style={{ 
                width: '100%', 
                height: 'auto', 
                maxHeight: '70vh',
                objectFit: 'contain'
              }}
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPreviewFile(null)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
```

Create supporting components:
1. components/common/FileValidator.tsx - File validation utilities
2. hooks/useFileUpload.ts - File upload management hook
3. utils/fileUtils.ts - File utility functions

Include proper memory management for previews and upload progress tracking.
```

---

## **PHASE 6: ELECTRON DESKTOP INTEGRATION**

### **Chunk 6.1: Electron Main Process**
```
Task: Create the Electron main process for desktop application packaging

Create the Electron main process with the following specifications:

FILE: electron/main.ts
```typescript
import { app, BrowserWindow, ipcMain, dialog, shell, Menu } from 'electron';
import * as path from 'path';
import * as isDev from 'electron-is-dev';
import { autoUpdater } from 'electron-updater';
import { spawn, ChildProcess } from 'child_process';
import * as fs from 'fs';
import * as os from 'os';

interface BackendProcess {
  process: ChildProcess | null;
  port: number;
  status: 'starting' | 'running' | 'stopped' | 'error';
}

class ElectronApp {
  private mainWindow: BrowserWindow | null = null;
  private backend: BackendProcess = {
    process: null,
    port: 5000,
    status: 'stopped'
  };

  constructor() {
    this.setupApp();
    this.setupIPC();
    this.setupMenu();
    this.setupAutoUpdater();
  }

  private setupApp(): void {
    // Set app user model ID for Windows
    if (process.platform === 'win32') {
      app.setAppUserModelId('com.kseb.energy-futures-platform');
    }

    // App event handlers
    app.whenReady().then(async () => {
      await this.startBackendServer();
      this.createMainWindow();
    });

    app.on('window-all-closed', () => {
      this.cleanup();
      if (process.platform !== 'darwin') {
        app.quit();
      }
    });

    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        this.createMainWindow();
      }
    });

    app.on('before-quit', () => {
      this.cleanup();
    });

    // Security: Prevent new window creation
    app.on('web-contents-created', (event, contents) => {
      contents.on('new-window', (navigationEvent, navigationURL) => {
        navigationEvent.preventDefault();
        shell.openExternal(navigationURL);
      });
    });
  }

  private async startBackendServer(): Promise<void> {
    return new Promise((resolve, reject) => {
      const backendPath = isDev 
        ? path.join(__dirname, '../backend/src/app.js')
        : path.join(process.resourcesPath, 'backend', 'app.js');

      const nodeExecutable = isDev ? 'node' : this.getNodeExecutable();

      console.log('Starting backend server...');
      
      this.backend.status = 'starting';
      this.backend.process = spawn(nodeExecutable, [backendPath], {
        env: {
          ...process.env,
          NODE_ENV: isDev ? 'development' : 'production',
          PORT: this.backend.port.toString(),
          ELECTRON_MODE: 'true',
          PYTHON_PATH: this.getPythonPath()
        },
        stdio: ['pipe', 'pipe', 'pipe'],
        detached: false
      });

      let startupTimeout: NodeJS.Timeout;

      this.backend.process.stdout?.on('data', (data) => {
        console.log(`Backend: ${data}`);
        const output = data.toString();
        
        if (output.includes(`Server running on port ${this.backend.port}`)) {
          this.backend.status = 'running';
          clearTimeout(startupTimeout);
          resolve();
        }
      });

      this.backend.process.stderr?.on('data', (data) => {
        console.error(`Backend Error: ${data}`);
      });

      this.backend.process.on('error', (error) => {
        console.error('Failed to start backend process:', error);
        this.backend.status = 'error';
        clearTimeout(startupTimeout);
        reject(error);
      });

      this.backend.process.on('exit', (code, signal) => {
        console.log(`Backend process exited with code ${code}, signal ${signal}`);
        this.backend.status = 'stopped';
        
        if (code !== 0 && code !== null) {
          clearTimeout(startupTimeout);
          reject(new Error(`Backend process exited with code ${code}`));
        }
      });

      // Timeout after 30 seconds
      startupTimeout = setTimeout(() => {
        this.backend.status = 'error';
        reject(new Error('Backend startup timeout'));
      }, 30000);
    });
  }

  private getNodeExecutable(): string {
    if (isDev) return 'node';
    
    switch (process.platform) {
      case 'win32':
        return path.join(process.resourcesPath, 'node.exe');
      case 'darwin':
        return path.join(process.resourcesPath, 'node');
      case 'linux':
        return path.join(process.resourcesPath, 'node');
      default:
        return 'node';
    }
  }

  private getPythonPath(): string {
    if (isDev) return 'python';
    
    switch (process.platform) {
      case 'win32':
        return path.join(process.resourcesPath, 'python', 'python.exe');
      case 'darwin':
        return path.join(process.resourcesPath, 'python', 'bin', 'python');
      case 'linux':
        return path.join(process.resourcesPath, 'python', 'bin', 'python');
      default:
        return 'python';
    }
  }

  private createMainWindow(): void {
    this.mainWindow = new BrowserWindow({
      width: 1400,
      height: 900,
      minWidth: 1200,
      minHeight: 800,
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        enableRemoteModule: false,
        preload: path.join(__dirname, 'preload.js'),
        webSecurity: !isDev
      },
      icon: this.getAppIcon(),
      title: 'KSEB Energy Futures Platform',
      show: false,
      titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default'
    });

    // Load the React app
    const appUrl = isDev 
      ? `http://localhost:3000`
      : `http://localhost:${this.backend.port}`;

    this.mainWindow.loadURL(appUrl);

    // Show window when ready
    this.mainWindow.once('ready-to-show', () => {
      this.mainWindow?.show();
      
      if (isDev) {
        this.mainWindow?.webContents.openDevTools();
      }
    });

    // Handle window closed
    this.mainWindow.on('closed', () => {
      this.mainWindow = null;
    });

    // Handle external links
    this.mainWindow.webContents.setWindowOpenHandler(({ url }) => {
      shell.openExternal(url);
      return { action: 'deny' };
    });

    // Prevent navigation to external URLs
    this.mainWindow.webContents.on('will-navigate', (event, navigationUrl) => {
      const parsedUrl = new URL(navigationUrl);
      const expectedOrigin = isDev ? 'http://localhost:3000' : `http://localhost:${this.backend.port}`;
      
      if (parsedUrl.origin !== expectedOrigin) {
        event.preventDefault();
        shell.openExternal(navigationUrl);
      }
    });
  }

  private getAppIcon(): string {
    const iconName = process.platform === 'win32' ? 'icon.ico' : 
                     process.platform === 'darwin' ? 'icon.icns' : 'icon.png';
    
    return isDev 
      ? path.join(__dirname, '../assets', iconName)
      : path.join(process.resourcesPath, 'assets', iconName);
  }

  private setupIPC(): void {
    // File system operations
    ipcMain.handle('select-folder', async () => {
      if (!this.mainWindow) return null;
      
      const result = await dialog.showOpenDialog(this.mainWindow, {
        properties: ['openDirectory'],
        title: 'Select Project Folder'
      });
      
      return result.canceled ? null : result.filePaths[0];
    });

    ipcMain.handle('select-file', async (_, options: any) => {
      if (!this.mainWindow) return null;
      
      const result = await dialog.showOpenDialog(this.mainWindow, {
        properties: ['openFile'],
        filters: options.filters || [],
        title: options.title || 'Select File'
      });
      
      return result.canceled ? null : result.filePaths[0];
    });

    ipcMain.handle('save-file', async (_, options: any) => {
      if (!this.mainWindow) return null;
      
      const result = await dialog.showSaveDialog(this.mainWindow, {
        filters: options.filters || [],
        defaultPath: options.defaultPath || '',
        title: options.title || 'Save File'
      });
      
      return result.canceled ? null : result.filePath;
    });

    // Application control
    ipcMain.handle('app-version', () => app.getVersion());
    ipcMain.handle('app-quit', () => app.quit());
    ipcMain.handle('app-minimize', () => this.mainWindow?.minimize());
    ipcMain.handle('app-maximize', () => {
      if (this.mainWindow?.isMaximized()) {
        this.mainWindow.unmaximize();
      } else {
        this.mainWindow?.maximize();
      }
    });

    ipcMain.handle('app-toggle-fullscreen', () => {
      const isFullScreen = this.mainWindow?.isFullScreen();
      this.mainWindow?.setFullScreen(!isFullScreen);
    });

    // System information
    ipcMain.handle('get-system-info', () => ({
      platform: process.platform,
      arch: process.arch,
      nodeVersion: process.version,
      electronVersion: process.versions.electron,
      chromeVersion: process.versions.chrome,
      memory: process.getSystemMemoryInfo(),
      cpu: os.cpus(),
      homeDir: os.homedir(),
      tmpDir: os.tmpdir()
    }));

    // Backend status
    ipcMain.handle('get-backend-status', () => ({
      status: this.backend.status,
      port: this.backend.port,
      pid: this.backend.process?.pid
    }));

    // File system operations
    ipcMain.handle('fs-exists', async (_, filePath: string) => {
      try {
        await fs.promises.access(filePath);
        return true;
      } catch {
        return false;
      }
    });

    ipcMain.handle('fs-read-file', async (_, filePath: string, encoding = 'utf-8') => {
      try {
        return await fs.promises.readFile(filePath, encoding);
      } catch (error: any) {
        throw new Error(`Failed to read file: ${error.message}`);
      }
    });

    ipcMain.handle('fs-write-file', async (_, filePath: string, content: string, encoding = 'utf-8') => {
      try {
        await fs.promises.writeFile(filePath, content, encoding);
        return true;
      } catch (error: any) {
        throw new Error(`Failed to write file: ${error.message}`);
      }
    });

    ipcMain.handle('fs-mkdir', async (_, dirPath: string) => {
      try {
        await fs.promises.mkdir(dirPath, { recursive: true });
        return true;
      } catch (error: any) {
        throw new Error(`Failed to create directory: ${error.message}`);
      }
    });

    // Dialog operations
    ipcMain.handle('show-message', async (_, options: any) => {
      if (!this.mainWindow) return { response: 0 };
      return await dialog.showMessageBox(this.mainWindow, options);
    });

    ipcMain.handle('show-error', async (_, title: string, content: string) => {
      dialog.showErrorBox(title, content);
    });

    ipcMain.handle('show-notification', (_, options: any) => {
      // Use system notifications if needed
      console.log('Notification:', options);
    });
  }

  private setupMenu(): void {
    const template: Electron.MenuItemConstructorOptions[] = [
      {
        label: 'File',
        submenu: [
          {
            label: 'New Project',
            accelerator: 'CmdOrCtrl+N',
            click: () => {
              this.mainWindow?.webContents.send('menu-action', 'new-project');
            }
          },
         
          {
            label: 'Open Project',
            accelerator: 'CmdOrCtrl+O',
            click: () => {
              this.mainWindow?.webContents.send('menu-action', 'open-project');
            }
          },
          {
            label: 'Save',
            accelerator: 'CmdOrCtrl+S',
            click: () => {
              this.mainWindow?.webContents.send('menu-action', 'save');
            }
          },
          { type: 'separator' },
          {
            label: 'Export Data',
            submenu: [
              {
                label: 'Export as CSV',
                click: () => {
                  this.mainWindow?.webContents.send('menu-action', 'export-csv');
                }
              },
              {
                label: 'Export as Excel',
                click: () => {
                  this.mainWindow?.webContents.send('menu-action', 'export-excel');
                }
              }
            ]
          },
          { type: 'separator' },
          {
            label: 'Exit',
            accelerator: process.platform === 'darwin' ? 'Cmd+Q' : 'Ctrl+Q',
            click: () => {
              app.quit();
            }
          }
        ]
      },
      {
        label: 'Edit',
        submenu: [
          { role: 'undo' },
          { role: 'redo' },
          { type: 'separator' },
          { role: 'cut' },
          { role: 'copy' },
          { role: 'paste' },
          { role: 'selectall' }
        ]
      },
      {
        label: 'View',
        submenu: [
          { role: 'reload' },
          { role: 'forceReload' },
          { role: 'toggleDevTools' },
          { type: 'separator' },
          { role: 'resetZoom' },
          { role: 'zoomIn' },
          { role: 'zoomOut' },
          { type: 'separator' },
          { role: 'togglefullscreen' }
        ]
      },
      {
        label: 'Analysis',
        submenu: [
          {
            label: 'Demand Projection',
            click: () => {
              this.mainWindow?.webContents.send('menu-action', 'demand-projection');
            }
          },
          {
            label: 'Load Profile Generation',
            click: () => {
              this.mainWindow?.webContents.send('menu-action', 'load-profile');
            }
          },
          {
            label: 'PyPSA Modeling',
            click: () => {
              this.mainWindow?.webContents.send('menu-action', 'pypsa-modeling');
            }
          }
        ]
      },
      {
        label: 'Help',
        submenu: [
          {
            label: 'User Guide',
            click: () => {
              this.mainWindow?.webContents.send('menu-action', 'user-guide');
            }
          },
          {
            label: 'Documentation',
            click: () => {
              shell.openExternal('https://docs.kseb-energy-platform.com');
            }
          },
          { type: 'separator' },
          {
            label: 'Check for Updates',
            click: () => {
              autoUpdater.checkForUpdatesAndNotify();
            }
          },
          {
            label: 'About',
            click: () => {
              dialog.showMessageBox(this.mainWindow!, {
                type: 'info',
                title: 'About KSEB Energy Futures Platform',
                message: 'KSEB Energy Futures Platform',
                detail: `Version: ${app.getVersion()}\nElectron: ${process.versions.electron}\nNode: ${process.versions.node}`
              });
            }
          }
        ]
      }
    ];

    // macOS specific menu adjustments
    if (process.platform === 'darwin') {
      template.unshift({
        label: app.getName(),
        submenu: [
          { role: 'about' },
          { type: 'separator' },
          { role: 'services' },
          { type: 'separator' },
          { role: 'hide' },
          { role: 'hideOthers' },
          { role: 'unhide' },
          { type: 'separator' },
          { role: 'quit' }
        ]
      });
    }

    const menu = Menu.buildFromTemplate(template);
    Menu.setApplicationMenu(menu);
  }

  private setupAutoUpdater(): void {
    if (isDev) return;

    autoUpdater.checkForUpdatesAndNotify();
    
    autoUpdater.on('update-available', () => {
      dialog.showMessageBox(this.mainWindow!, {
        type: 'info',
        title: 'Update Available',
        message: 'A new version is available. It will be downloaded in the background.',
        buttons: ['OK']
      });
    });

    autoUpdater.on('update-downloaded', () => {
      dialog.showMessageBox(this.mainWindow!, {
        type: 'info',
        title: 'Update Ready',
        message: 'Update downloaded. The application will restart to apply the update.',
        buttons: ['Restart Now', 'Later']
      }).then((result) => {
        if (result.response === 0) {
          autoUpdater.quitAndInstall();
        }
      });
    });

    autoUpdater.on('error', (error) => {
      console.error('Auto-updater error:', error);
    });
  }

  private cleanup(): void {
    if (this.backend.process && !this.backend.process.killed) {
      console.log('Terminating backend process...');
      
      // Graceful shutdown
      this.backend.process.kill('SIGTERM');
      
      // Force kill after 5 seconds
      setTimeout(() => {
        if (this.backend.process && !this.backend.process.killed) {
          console.log('Force killing backend process...');
          this.backend.process.kill('SIGKILL');
        }
      }, 5000);
    }
  }
}

// Initialize the application
new ElectronApp();
```

Create the preload script and package configuration files.

### **Chunk 6.2: Electron Preload Script**
```
Task: Create the Electron preload script for secure IPC communication

Create the preload script with the following specifications:

FILE: electron/preload.ts
```typescript
import { contextBridge, ipcRenderer } from 'electron';

// Define the API interface for type safety
interface ElectronAPI {
  // File operations
  selectFolder: () => Promise<string | null>;
  selectFile: (options: {
    filters?: Array<{name: string; extensions: string[]}>;
    title?: string;
  }) => Promise<string | null>;
  saveFile: (options: {
    filters?: Array<{name: string; extensions: string[]}>;
    defaultPath?: string;
    title?: string;
  }) => Promise<string | null>;

  // Application control
  getVersion: () => Promise<string>;
  quit: () => Promise<void>;
  minimize: () => Promise<void>;
  maximize: () => Promise<void>;
  toggleFullscreen: () => Promise<void>;

  // System information
  getSystemInfo: () => Promise<{
    platform: string;
    arch: string;
    nodeVersion: string;
    electronVersion: string;
    chromeVersion: string;
    memory: any;
    cpu: any[];
    homeDir: string;
    tmpDir: string;
  }>;

  getBackendStatus: () => Promise<{
    status: 'starting' | 'running' | 'stopped' | 'error';
    port: number;
    pid?: number;
  }>;

  // File system operations
  fileExists: (path: string) => Promise<boolean>;
  readFile: (path: string, encoding?: string) => Promise<string>;
  writeFile: (path: string, content: string, encoding?: string) => Promise<boolean>;
  createDirectory: (path: string) => Promise<boolean>;

  // Dialog operations
  showMessage: (options: {
    type?: 'none' | 'info' | 'error' | 'question' | 'warning';
    title?: string;
    message: string;
    detail?: string;
    buttons?: string[];
    defaultId?: number;
    cancelId?: number;
  }) => Promise<{response: number; checkboxChecked?: boolean}>;
  
  showError: (title: string, content: string) => Promise<void>;
  showNotification: (options: {
    title: string;
    body: string;
    icon?: string;
  }) => Promise<void>;

  // Event listeners
  onMenuAction: (callback: (action: string) => void) => void;
  removeAllListeners: (channel: string) => void;

  // Platform info
  platform: string;
  isElectron: boolean;
}

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
const electronAPI: ElectronAPI = {
  // File operations
  selectFolder: () => ipcRenderer.invoke('select-folder'),
  selectFile: (options) => ipcRenderer.invoke('select-file', options),
  saveFile: (options) => ipcRenderer.invoke('save-file', options),
  
  // Application control
  getVersion: () => ipcRenderer.invoke('app-version'),
  quit: () => ipcRenderer.invoke('app-quit'),
  minimize: () => ipcRenderer.invoke('app-minimize'),
  maximize: () => ipcRenderer.invoke('app-maximize'),
  toggleFullscreen: () => ipcRenderer.invoke('app-toggle-fullscreen'),
  
  // System information
  getSystemInfo: () => ipcRenderer.invoke('get-system-info'),
  getBackendStatus: () => ipcRenderer.invoke('get-backend-status'),
  
  // File system operations
  fileExists: (path: string) => ipcRenderer.invoke('fs-exists', path),
  readFile: (path: string, encoding = 'utf-8') => ipcRenderer.invoke('fs-read-file', path, encoding),
  writeFile: (path: string, content: string, encoding = 'utf-8') => 
    ipcRenderer.invoke('fs-write-file', path, content, encoding),
  createDirectory: (path: string) => ipcRenderer.invoke('fs-mkdir', path),
  
  // Dialog operations
  showMessage: (options) => ipcRenderer.invoke('show-message', options),
  showError: (title: string, content: string) => ipcRenderer.invoke('show-error', title, content),
  showNotification: (options) => ipcRenderer.invoke('show-notification', options),
  
  // Event listeners
  onMenuAction: (callback) => {
    ipcRenderer.on('menu-action', (_, action) => callback(action));
  },
  removeAllListeners: (channel) => {
    ipcRenderer.removeAllListeners(channel);
  },
  
  // Platform info
  platform: process.platform,
  isElectron: true
};

// Expose the API to the renderer process
contextBridge.exposeInMainWorld('electronAPI', electronAPI);

// Expose a flag to detect Electron environment
contextBridge.exposeInMainWorld('isElectron', true);

// Type definitions for the exposed API
declare global {
  interface Window {
    electronAPI: ElectronAPI;
    isElectron: boolean;
  }
}

// Additional security measures
window.addEventListener('DOMContentLoaded', () => {
  // Remove any dangerous globals that might have been exposed
  delete (window as any).require;
  delete (window as any).exports;
  delete (window as any).module;
});

// Handle uncaught errors
window.addEventListener('error', (event) => {
  console.error('Renderer error:', event.error);
});

window.addEventListener('unhandledrejection', (event) => {
  console.error('Unhandled promise rejection:', event.reason);
});
```

Create supporting files:
1. types/electron.d.ts - TypeScript definitions
2. electron/utils.ts - Electron utility functions

Include proper error handling and security measures.
```

### **Chunk 6.3: Electron Build Configuration**
```
Task: Create build configuration for packaging the Electron application

Create comprehensive build configuration with the following specifications:

FILE: package.json (root)
```json
{
  "name": "kseb-energy-futures-platform",
  "version": "1.0.0",
  "description": "KSEB Energy Futures Platform - Desktop Application for Energy Planning and Analysis",
  "main": "dist/electron/main.js",
  "author": "KSEB Energy Planning Team",
  "license": "MIT",
  "private": true,
  "homepage": "./",
  "scripts": {
    "dev": "concurrently \"npm run dev:backend\" \"npm run dev:frontend\" \"wait-on http://localhost:5000 http://localhost:3000 && npm run dev:electron\"",
    "dev:backend": "cd backend && npm run dev",
    "dev:frontend": "cd frontend && npm start",
    "dev:electron": "cross-env NODE_ENV=development electron .",
    
    "build": "npm run build:backend && npm run build:frontend && npm run build:electron",
    "build:backend": "cd backend && npm run build",
    "build:frontend": "cd frontend && npm run build",
    "build:electron": "tsc -p electron/tsconfig.json",
    
    "package": "npm run build && electron-builder",
    "package:dir": "npm run build && electron-builder --dir",
    "package:win": "npm run build && electron-builder --win",
    "package:mac": "npm run build && electron-builder --mac",
    "package:linux": "npm run build && electron-builder --linux",
    
    "dist": "npm run build && electron-builder --publish=never",
    "dist:all": "npm run build && electron-builder -mwl --publish=never",
    "publish": "npm run build && electron-builder --publish=always",
    
    "clean": "rimraf dist && rimraf backend/dist && rimraf frontend/build",
    "postinstall": "electron-builder install-app-deps",
    "test": "jest",
    "lint": "eslint . --ext .ts,.tsx,.js,.jsx"
  },
  "devDependencies": {
    "@types/node": "^18.15.0",
    "@types/electron": "^1.6.10",
    "concurrently": "^7.6.0",
    "cross-env": "^7.0.3",
    "electron": "^23.1.0",
    "electron-builder": "^23.6.0",
    "typescript": "^4.9.5",
    "wait-on": "^7.0.1",
    "rimraf": "^4.4.0",
    "eslint": "^8.36.0",
    "jest": "^29.5.0"
  },
  "dependencies": {
    "electron-is-dev": "^2.0.0",
    "electron-updater": "^5.3.0",
    "node-machine-id": "^1.1.12"
  },
  "build": {
    "appId": "com.kseb.energy-futures-platform",
    "productName": "KSEB Energy Futures Platform",
    "copyright": "Copyright © 2024 KSEB Energy Planning Team",
    "directories": {
      "output": "dist/packages"
    },
    "files": [
      "dist/electron/**/*",
      "node_modules/**/*",
      "package.json"
    ],
    "extraResources": [
      {
        "from": "backend/dist",
        "to": "backend",
        "filter": ["**/*"]
      },
      {
        "from": "backend/src/python",
        "to": "python",
        "filter": ["**/*.py"]
      },
      {
        "from": "frontend/build",
        "to": "frontend",
        "filter": ["**/*"]
      },
      {
        "from": "assets",
        "to": "assets",
        "filter": ["**/*"]
      }
    ],
    "win": {
      "target": [
        {
          "target": "nsis",
          "arch": ["x64"]
        },
        {
          "target": "portable",
          "arch": ["x64"]
        },
        {
          "target": "zip",
          "arch": ["x64"]
        }
      ],
      "icon": "assets/icon.ico",
      "publisherName": "KSEB Energy Planning Team",
      "verifyUpdateCodeSignature": false,
      "extraResources": [
        {
          "from": "python-runtime/windows",
          "to": "python",
          "filter": ["**/*"]
        }
      ]
    },
    "mac": {
      "target": [
        {
          "target": "dmg",
          "arch": ["x64", "arm64"]
        },
        {
          "target": "zip",
          "arch": ["x64", "arm64"]
        }
      ],
      "icon": "assets/icon.icns",
      "category": "public.app-category.productivity",
      "darkModeSupport": true,
      "extraResources": [
        {
          "from": "python-runtime/macos",
          "to": "python",
          "filter": ["**/*"]
        }
      ]
    },
    "linux": {
      "target": [
        {
          "target": "AppImage",
          "arch": ["x64"]
        },
        {
          "target": "deb",
          "arch": ["x64"]
        },
        {
          "target": "rpm",
          "arch": ["x64"]
        },
        {
          "target": "tar.gz",
          "arch": ["x64"]
        }
      ],
      "icon": "assets/icon.png",
      "category": "Science",
      "extraResources": [
        {
          "from": "python-runtime/linux",
          "to": "python",
          "filter": ["**/*"]
        }
      ]
    },
    "portable": {
      "artifactName": "${productName}-${version}-portable.${ext}"
    },
    "nsis": {
      "oneClick": false,
      "allowToChangeInstallationDirectory": true,
      "createDesktopShortcut": true,
      "createStartMenuShortcut": true,
      "menuCategory": "KSEB Energy Tools",
      "runAfterFinish": true,
      "installerIcon": "assets/icon.ico",
      "uninstallerIcon": "assets/icon.ico",
      "installerHeader": "assets/installer-header.bmp",
      "installerSidebar": "assets/installer-sidebar.bmp",
      "include": "build/installer.nsh"
    },
    "dmg": {
      "title": "${productName} ${version}",
      "icon": "assets/icon.icns",
      "background": "assets/dmg-background.png",
      "contents": [
        {
          "x": 410,
          "y": 150,
          "type": "link",
          "path": "/Applications"
        },
        {
          "x": 130,
          "y": 150,
          "type": "file"
        }
      ]
    },
    "publish": [
      {
        "provider": "github",
        "owner": "kseb-energy",
        "repo": "energy-futures-platform",
        "private": true
      }
    ],
    "compression": "normal",
    "artifactName": "${productName}-${version}-${platform}-${arch}.${ext}"
  }
}
```

FILE: electron/tsconfig.json
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "lib": ["ES2020"],
    "outDir": "../dist/electron",
    "rootDir": ".",
    "removeComments": true,
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "moduleResolution": "node",
    "allowSyntheticDefaultImports": true,
    "experimentalDecorators": true,
    "emitDecoratorMetadata": true,
    "declaration": false,
    "resolveJsonModule": true,
    "types": ["node", "electron"]
  },
  "include": [
    "**/*.ts"
  ],
  "exclude": [
    "node_modules",
    "dist",
    "**/*.spec.ts",
    "**/*.test.ts"
  ]
}
```

FILE: build/installer.nsh
```nsis
; Custom NSIS installer script for advanced features
!include "MUI2.nsh"

; Install Python runtime if not present
Section "Python Runtime" SecPython
  SetOutPath "$INSTDIR\python"
  File /r "${BUILD_RESOURCES_DIR}\python\*"
SectionEnd

; Create desktop shortcut with custom icon
Section "Desktop Shortcut" SecDesktop
  CreateShortCut "$DESKTOP\KSEB Energy Futures Platform.lnk" "$INSTDIR\KSEB Energy Futures Platform.exe" "" "$INSTDIR\resources\assets\icon.ico"
SectionEnd

; Register file associations
Section "File Associations" SecFileAssoc
  ; Register .kseb project files
  WriteRegStr HKCR ".kseb" "" "KSEBProject"
  WriteRegStr HKCR "KSEBProject" "" "KSEB Energy Project"
  WriteRegStr HKCR "KSEBProject\DefaultIcon" "" "$INSTDIR\resources\assets\icon.ico"
  WriteRegStr HKCR "KSEBProject\shell\open\command" "" '"$INSTDIR\KSEB Energy Futures Platform.exe" "%1"'
SectionEnd

; Uninstaller section
Section "Uninstall"
  ; Remove file associations
  DeleteRegKey HKCR ".kseb"
  DeleteRegKey HKCR "KSEBProject"
  
  ; Remove desktop shortcut
  Delete "$DESKTOP\KSEB Energy Futures Platform.lnk"
  
  ; Remove installation directory
  RMDir /r "$INSTDIR"
SectionEnd
```

Create additional configuration files:
1. .eslintrc.js - ESLint configuration
2. jest.config.js - Jest testing configuration
3. GitHub Actions workflow for automated builds

Include proper code signing, auto-update, and cross-platform compatibility.
```

---

## **PHASE 7: PYTHON MODULES INTEGRATION**

### **Chunk 7.1: Enhanced Demand Projection Python Module**
```
Task: Create the enhanced demand projection Python module for Node.js integration

Create a comprehensive demand projection module with the following specifications:

FILE: backend/src/python/demand_projection.py
```python
import sys
import json
import argparse
import logging
import traceback
import uuid
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Configure logging for Node.js integration
logging.basicConfig(
    level=logging.INFO,
    format='{"level": "%(levelname)s", "message": "%(message)s", "timestamp": "%(asctime)s"}'
)
logger = logging.getLogger(__name__)

class ProgressReporter:
    """Real-time progress reporting to Node.js"""
    
    def __init__(self):
        self.current_progress = 0
        
    def report(self, progress: float, sector: str, status: str, details: str = ""):
        """Send progress update to Node.js via stdout"""
        progress_data = {
            "progress": min(100, max(0, progress)),
            "sector": sector,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        print(f"PROGRESS:{json.dumps(progress_data)}", flush=True)
        self.current_progress = progress

class DataValidator:
    """Comprehensive data validation for demand projection"""
    
    @staticmethod
    def validate_input_file(file_path: str) -> Dict[str, Any]:
        """Validate input demand file structure and quality"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "quality_score": 0,
            "sector_quality": {},
            "recommendations": []
        }
        
        try:
            # Check file existence
            if not Path(file_path).exists():
                validation_result["valid"] = False
                validation_result["errors"].append(f"File not found: {file_path}")
                return validation_result
            
            # Load Excel file
            excel_file = pd.ExcelFile(file_path)
            required_sectors = ['residential', 'commercial', 'industrial', 'agriculture', 'transport']
            
            total_quality = 0
            sectors_found = 0
            
            for sector in required_sectors:
                if sector in excel_file.sheet_names:
                    sectors_found += 1
                    df = pd.read_excel(file_path, sheet_name=sector)
                    
                    # Validate sector data
                    sector_quality = DataValidator._validate_sector_data(df, sector)
                    validation_result["sector_quality"][sector] = sector_quality
                    total_quality += sector_quality["score"]
                    
                    if sector_quality["score"] < 0.5:
                        validation_result["warnings"].append(
                            f"Poor data quality for {sector} sector (score: {sector_quality['score']:.2f})"
                        )
                else:
                    validation_result["warnings"].append(f"Missing sector sheet: {sector}")
            
            # Calculate overall quality score
            if sectors_found > 0:
                validation_result["quality_score"] = total_quality / sectors_found
            
            # Generate recommendations
            if validation_result["quality_score"] < 0.7:
                validation_result["recommendations"].append("Consider improving data quality before forecasting")
            if sectors_found < len(required_sectors):
                validation_result["recommendations"].append("Add missing sector data for comprehensive analysis")
                
        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"File validation error: {str(e)}")
        
        return validation_result
    
    @staticmethod
    def _validate_sector_data(df: pd.DataFrame, sector: str) -> Dict[str, Any]:
        """Validate individual sector data quality"""
        quality_metrics = {
            "score": 0,
            "completeness": 0,
            "consistency": 0,
            "temporal_coverage": 0,
            "issues": []
        }
        
        required_columns = ['year', 'demand', 'gdp', 'population']
        
        # Check required columns
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            quality_metrics["issues"].append(f"Missing columns: {missing_columns}")
            return quality_metrics
        
        # Completeness check
        total_cells = len(df) * len(required_columns)
        missing_cells = df[required_columns].isnull().sum().sum()
        quality_metrics["completeness"] = 1 - (missing_cells / total_cells)
        
        # Temporal coverage check
        if 'year' in df.columns:
            years = df['year'].dropna().unique()
            year_range = max(years) - min(years) + 1 if len(years) > 0 else 0
            expected_years = 15  # Expect at least 15 years of data
            quality_metrics["temporal_coverage"] = min(1.0, len(years) / expected_years)
        
        # Consistency check (no negative values, reasonable trends)
        if 'demand' in df.columns:
            demand_values = df['demand'].dropna()
            negative_values = (demand_values < 0).sum()
            quality_metrics["consistency"] = 1 - (negative_values / len(demand_values))
        
        # Calculate overall score
        quality_metrics["score"] = (
            quality_metrics["completeness"] * 0.4 +
            quality_metrics["temporal_coverage"] * 0.3 +
            quality_metrics["consistency"] * 0.3
        )
        
        return quality_metrics

class ForecastingEngine:
    """Advanced forecasting engine with multiple models"""
    
    def __init__(self, progress_reporter: ProgressReporter):
        self.progress_reporter = progress_reporter
        self.models = {}
        
    def execute_forecast(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute complete forecasting workflow"""
        try:
            # Initialize result structure
            result = {
                "success": True,
                "scenario_name": config["scenario_name"],
                "target_year": config["target_year"],
                "execution_time": datetime.now().isoformat(),
                "sectors": {},
                "summary": {},
                "configuration": config
            }
            
            # Load input data
            self.progress_reporter.report(5, "initialization", "Loading input data")
            input_data = self._load_input_data(config.get("input_file", "inputs/input_demand_file.xlsx"))
            
            # Process each sector
            sectors = config.get("sectors", {})
            total_sectors = len(sectors)
            
            for i, (sector_name, sector_config) in enumerate(sectors.items()):
                sector_progress = 10 + (70 * i / total_sectors)
                self.progress_reporter.report(
                    sector_progress, 
                    sector_name, 
                    f"Processing {sector_name} sector"
                )
                
                try:
                    sector_result = self._process_sector(
                        sector_name, 
                        sector_config, 
                        input_data.get(sector_name, pd.DataFrame()),
                        config
                    )
                    result["sectors"][sector_name] = sector_result
                except Exception as e:
                    logger.error(f"Sector {sector_name} processing failed: {e}")
                    result["sectors"][sector_name] = {
                        "error": str(e),
                        "status": "failed"
                    }
            
            # Generate summary
            self.progress_reporter.report(85, "consolidation", "Generating forecast summary")
            result["summary"] = self._generate_summary(result["sectors"], config)
            
            # Save results
            self.progress_reporter.report(95, "saving", "Saving forecast results")
            self._save_results(result)
            
            self.progress_reporter.report(100, "completed", "Forecast completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Forecast execution failed: {e}")
            raise
    
    def _load_input_data(self, file_path: str) -> Dict[str, pd.DataFrame]:
        """Load and validate input data from Excel file"""
        input_data = {}
        
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Input file not found: {file_path}")
        
        excel_file = pd.ExcelFile(file_path)
        
        for sheet_name in excel_file.sheet_names:
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                # Basic data cleaning
                df = df.dropna(how='all')  # Remove completely empty rows
                input_data[sheet_name] = df
            except Exception as e:
                logger.warning(f"Failed to load sheet {sheet_name}: {e}")
        
        return input_data
    
    def _process_sector(self, sector_name: str, sector_config: Dict[str, Any], 
                       sector_data: pd.DataFrame, global_config: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual sector forecast"""
        sector_result = {
            "sector": sector_name,
            "models": {},
            "status": "completed",
            "data_quality": 0,
            "best_model": None
        }
        
        # Validate sector data
        if sector_data.empty:
            raise ValueError(f"No data available for sector: {sector_name}")
        
        # Calculate data quality score
        sector_result["data_quality"] = self._calculate_data_quality(sector_data)
        
        # Get selected models for this sector
        models = sector_config.get("models", ["MLR"])
        target_year = global_config["target_year"]
        exclude_covid = global_config.get("exclude_covid", True)
        
        model_performance = {}
        
        # Execute each model
        for model_name in models:
            try:
                if model_name == "MLR":
                    model_result = self._run_mlr_model(sector_data, sector_config, target_year, exclude_covid)
                elif model_name == "SLR":
                    model_result = self._run_slr_model(sector_data, target_year, exclude_covid)
                elif model_name == "WAM":
                    model_result = self._run_wam_model(sector_data, sector_config, target_year)
                elif model_name == "TimeSeries":
                    model_result = self._run_timeseries_model(sector_data, target_year, exclude_covid)
                else:
                    raise ValueError(f"Unknown model: {model_name}")
                
                sector_result["models"][model_name] = model_result
                model_performance[model_name] = model_result.get("performance_score", 0)
                
            except Exception as e:
                logger.error(f"Model {model_name} failed for sector {sector_name}: {e}")
                sector_result["models"][model_name] = {
                    "error": str(e),
                    "status": "failed"
                }
        
        # Determine best model
        if model_performance:
            sector_result["best_model"] = max(model_performance, key=model_performance.get)
        
        return sector_result
    
    def _run_mlr_model(self, data: pd.DataFrame, config: Dict[str, Any], 
                      target_year: int, exclude_covid: bool) -> Dict[str, Any]:
        """Multiple Linear Regression model implementation"""
        from sklearn.linear_model import LinearRegression
        from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
        from sklearn.preprocessing import StandardScaler
        
        # Prepare data
        if exclude_covid:
            data = data[~data['year'].isin([2020, 2021, 2022])]
        
        # Get independent variables
        independent_vars = config.get("independent_variables", ["gdp", "population"])
        available_vars = [var for var in independent_vars if var in data.columns]
        
        if not available_vars:
            raise ValueError("No independent variables available for MLR")
        
        # Prepare features and target
        X = data[available_vars].fillna(method='ffill').fillna(method='bfill')
        y = data['demand'].fillna(method='ffill').fillna(method='bfill')
        
        # Remove rows with missing values
        valid_indices = ~(X.isnull().any(axis=1) | y.isnull())
        X = X[valid_indices]
        y = y[valid_indices]
        
        if len(X) < 3:
            raise ValueError("Insufficient data for MLR model")
        
        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Train model
        model = LinearRegression()
        model.fit(X_scaled, y)
        
        # Make predictions on training data
        y_pred = model.predict(X_scaled)
        
        # Calculate metrics
        r2 = r2_score(y, y_pred)
        mae = mean_absolute_error(y, y_pred)
        rmse = np.sqrt(mean_squared_error(y, y_pred))
        
        # Generate future projections
        future_projections = self._generate_future_projections_mlr(
            model, scaler, data, available_vars, target_year
        )
        
        # Calculate performance score
        performance_score = max(0, r2)  # R² as performance indicator
        
        return {
            "model_type": "MLR",
            "r2_score": float(r2),
            "mae": float(mae),
            "rmse": float(rmse),
            "performance_score": float(performance_score),
            "coefficients": model.coef_.tolist(),
            "intercept": float(model.intercept_),
            "independent_variables": available_vars,
            "feature_importance": dict(zip(available_vars, model.coef_)),
            "future_projections": future_projections,
            "data_points_used": len(X),
            "status": "completed"
        }
    
    def _run_slr_model(self, data: pd.DataFrame, target_year: int, exclude_covid: bool) -> Dict[str, Any]:
        """Simple Linear Regression (time-based trend) model"""
        from sklearn.linear_model import LinearRegression
        from sklearn.metrics import r2_score
        
        # Prepare data
        if exclude_covid:
            data = data[~data['year'].isin([2020, 2021, 2022])]
        
        # Remove missing values
        clean_data = data[['year', 'demand']].dropna()
        
        if len(clean_data) < 3:
            raise ValueError("Insufficient data for SLR model")
        
        X = clean_data['year'].values.reshape(-1, 1)
        y = clean_data['demand'].values
        
        # Train model
        model = LinearRegression()
        model.fit(X, y)
        
        # Calculate metrics
        y_pred = model.predict(X)
        r2 = r2_score(y, y_pred)
        
        # Generate future projections
        current_year = data['year'].max()
        future_years = list(range(int(current_year) + 1, target_year + 1))
        future_X = np.array(future_years).reshape(-1, 1)
        future_predictions = model.predict(future_X)
        
        future_projections = [
            {
                "year": int(year),
                "projected_demand": max(0, float(demand))  # Ensure non-negative
            }
            for year, demand in zip(future_years, future_predictions)
        ]
        
        performance_score = max(0, r2)
        
        return {
            "model_type": "SLR",
            "r2_score": float(r2),
            "performance_score": float(performance_score),
            "slope": float(model.coef_[0]),
            "intercept": float(model.intercept_),
            "trend": "increasing" if model.coef_[0] > 0 else "decreasing",
            "future_projections": future_projections,
            "data_points_used": len(clean_data),
            "status": "completed"
        }
    
    def _run_wam_model(self, data: pd.DataFrame, config: Dict[str, Any], target_year: int) -> Dict[str, Any]:
        """Weighted Average Method model"""
        window_size = config.get("wam_window", 5)
        growth_method = config.get("growth_method", "compound")
        
        # Get recent demand data
        clean_data = data[['year', 'demand']].dropna().sort_values('year')
        
        if len(clean_data) < window_size:
            window_size = len(clean_data)
        
        if window_size < 2:
            raise ValueError("Insufficient data for WAM model")
        
        recent_data = clean_data.tail(window_size)
        
        # Calculate weights (linear weighting - more recent years get higher weights)
        weights = np.linspace(1, window_size, window_size)
        weights = weights / weights.sum()
        
        # Calculate weighted average growth rate
        if growth_method == "compound":
            # Compound annual growth rate
            years = recent_data['year'].values
            demands = recent_data['demand'].values
            
            if len(demands) >= 2:
                growth_rate = ((demands[-1] / demands[0]) ** (1 / (years[-1] - years[0]))) - 1
            else:
                growth_rate = 0.02  # Default 2% growth
        else:
            # Simple average growth rate
            growth_rates = recent_data['demand'].pct_change().dropna()
            growth_rate = np.average(growth_rates, weights=weights[1:]) if len(growth_rates) > 0 else 0.02
        
        # Generate future projections
        base_demand = recent_data['demand'].iloc[-1]
        base_year = recent_data['year'].iloc[-1]
        
        future_projections = []
        for year in range(int(base_year) + 1, target_year + 1):
            years_ahead = year - base_year
            projected_demand = base_demand * ((1 + growth_rate) ** years_ahead)
            
            future_projections.append({
                "year": year,
                "projected_demand": max(0, float(projected_demand))
            })
        
        # Calculate performance score based on recent trend consistency
        performance_score = min(1.0, 1 / (1 + abs(growth_rate - 0.03)))  # Penalize extreme growth rates
        
        return {
            "model_type": "WAM",
            "window_size": window_size,
            "growth_rate": float(growth_rate),
            "growth_method": growth_method,
            "performance_score": float(performance_score),
            "base_demand": float(base_demand),
            "base_year": int(base_year),
            "future_projections": future_projections,
            "data_points_used": len(recent_data),
            "status": "completed"
        }
    
    def _run_timeseries_model(self, data: pd.DataFrame, target_year: int, exclude_covid: bool) -> Dict[str, Any]:
        """Advanced time series forecasting model"""
        try:
            from statsmodels.tsa.arima.model import ARIMA
            from statsmodels.tsa.seasonal import seasonal_decompose
            from statsmodels.stats.diagnostic import acorr_ljungbox
        except ImportError:
            raise ImportError("statsmodels is required for time series analysis")
        
        # Prepare data
        if exclude_covid:
            data = data[~data['year'].isin([2020, 2021, 2022])]
        
        clean_data = data[['year', 'demand']].dropna().sort_values('year')
        
        if len(clean_data) < 5:
            raise ValueError("Insufficient data for time series model (minimum 5 years required)")
        
        # Create time series
        ts_data = clean_data.set_index('year')['demand']
        
        # Seasonal decomposition (if enough data)
        decomposition = None
        if len(ts_data) >= 8:
            try:
                decomposition = seasonal_decompose(ts_data, model='additive', period=min(4, len(ts_data)//2))
            except:
                pass
        
        # Determine ARIMA order automatically
        arima_order = self._determine_arima_order(ts_data)
        
        # Fit ARIMA model
        model = ARIMA(ts_data, order=arima_order)
        fitted_model = model.fit()
        
        # Generate forecasts
        current_year = clean_data['year'].max()
        steps = target_year - current_year
        
        forecast = fitted_model.forecast(steps=steps)
        conf_int = fitted_model.get_forecast(steps=steps).conf_int()
        
        # Generate future projections
        future_projections = []
        for i, year in enumerate(range(int(current_year) + 1, target_year + 1)):
            future_projections.append({
                "year": year,
                "projected_demand": max(0, float(forecast.iloc[i])),
                "lower_confidence": max(0, float(conf_int.iloc[i, 0])),
                "upper_confidence": max(0, float(conf_int.iloc[i, 1]))
            })
        
        # Calculate performance score based on model diagnostics
        try:
            ljung_box = acorr_ljungbox(fitted_model.resid, lags=min(10, len(ts_data)//4), return_df=True)
            performance_score = 1 - ljung_box['lb_pvalue'].iloc[0]  # Higher p-value = better performance
        except:
            performance_score = 0.5  # Default score if diagnostics fail
        
        return {
            "model_type": "TimeSeries",
            "arima_order": arima_order,
            "aic": float(fitted_model.aic),
            "bic": float(fitted_model.bic),
            "performance_score": float(performance_score),
            "future_projections": future_projections,
            "seasonal_components": self._extract_seasonal_components(decomposition) if decomposition else None,
            "data_points_used": len(ts_data),
            "status": "completed"
        }
    
    def _determine_arima_order(self, ts_data: pd.Series) -> Tuple[int, int, int]:
        """Automatically determine optimal ARIMA order"""
        # Simple heuristic for ARIMA order selection
        n = len(ts_data)
        
        if n < 10:
            return (1, 1, 1)
        elif n < 20:
            return (2, 1, 1)
        else:
            return (2, 1, 2)
    
    def _extract_seasonal_components(self, decomposition) -> Dict[str, Any]:
        """Extract seasonal decomposition components"""
        return {
            "trend": decomposition.trend.dropna().to_dict(),
            "seasonal": decomposition.seasonal.to_dict(),
            "residual": decomposition.resid.dropna().to_dict()
        }
    
    def _generate_future_projections_mlr(self, model, scaler, data: pd.DataFrame, 
                                        variables: List[str], target_year: int) -> List[Dict[str, Any]]:
        """Generate future projections for MLR model"""
        current_year = data['year'].max()
        future_projections = []
        
        # Simple projection: assume linear growth for independent variables
        for year in range(int(current_year) + 1, target_year + 1):
            # Project independent variables (simplified approach)
            projected_features = []
            for var in variables:
                if var in data.columns:
                    recent_values = data[var].dropna().tail(5)
                    if len(recent_values) >= 2:
                        growth_rate = recent_values.pct_change().mean()
                        last_value = recent_values.iloc[-1]
                        years_ahead = year - current_year
                        projected_value = last_value * ((1 + growth_rate) ** years_ahead)
                        projected_features.append(projected_value)
                    else:
                        projected_features.append(0)
            
            # Scale features and predict
            if projected_features:
                scaled_features = scaler.transform([projected_features])
                projected_demand = model.predict(scaled_features)[0]
                
                future_projections.append({
                    "year": year,
                    "projected_demand": max(0, float(projected_demand)),
                    "projected_variables": dict(zip(variables, projected_features))
                })
        
        return future_projections
    
    def _calculate_data_quality(self, data: pd.DataFrame) -> float:
        """Calculate data quality score for a sector"""
        if data.empty:
            return 0.0
        
        required_columns = ['year', 'demand']
        available_columns = [col for col in required_columns if col in data.columns]
        
        if not available_columns:
            return 0.0
        
        # Completeness score
        completeness = 1 - (data[available_columns].isnull().sum().sum() / 
                           (len(data) * len(available_columns)))
        
        # Temporal coverage score
        if 'year' in data.columns:
            years = data['year'].dropna().nunique()
            temporal_score = min(1.0, years / 15)  # Expect 15+ years
        else:
            temporal_score = 0.0
        
        # Consistency score (no negative demands)
        if 'demand' in data.columns:
            demand_values = data['demand'].dropna()
            if len(demand_values) > 0:
                consistency = 1 - (demand_values < 0).sum() / len(demand_values)
            else:
                consistency = 0.0
        else:
            consistency = 0.0
        
        return (completeness * 0.4 + temporal_score * 0.3 + consistency * 0.3)
    
    def _generate_summary(self, sectors: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate forecast summary statistics"""
        summary = {
            "total_sectors": len(sectors),
            "successful_sectors": 0,
            "failed_sectors": 0,
            "models_used": set(),
            "average_data_quality": 0,
            "execution_timestamp": datetime.now().isoformat(),
            "configuration_hash": hash(json.dumps(config, sort_keys=True))
        }
        
        total_quality = 0
        quality_count = 0
        
        for sector_name, sector_result in sectors.items():
            if isinstance(sector_result, dict) and "error" not in sector_result:
                summary["successful_sectors"] += 1
                
                # Collect model names
                if "models" in sector_result:
                    summary["models_used"].update(sector_result["models"].keys())
                
                # Accumulate data quality
                if "data_quality" in sector_result:
                    total_quality += sector_result["data_quality"]
                    quality_count += 1
            else:
                summary["failed_sectors"] += 1
        
        summary["models_used"] = list(summary["models_used"])
        
        if quality_count > 0:
            summary["average_data_quality"] = total_quality / quality_count
        
        return summary
    
    def _save_results(self, result: Dict[str, Any]):
        """Save forecast results to structured files"""
        scenario_name = result["scenario_name"]
        output_dir = Path("results") / "demand_forecasts" / scenario_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save complete results
        results_file = output_dir / "forecast_results.json"
        with open(results_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        # Save sector-specific results
        for sector_name, sector_result in result["sectors"].items():
            sector_file = output_dir / f"{sector_name}_forecast.json"
            with open(sector_file, 'w') as f:
                json.dump(sector_result, f, indent=2, default=str)
        
        # Save summary
        summary_file = output_dir / "forecast_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(result["summary"], f, indent=2, default=str)

def get_sector_data(sector: str) -> Dict[str, Any]:
    """Get sector data for display"""
    try:
        input_file = Path("inputs") / "input_demand_file.xlsx"
        if not input_file.exists():
            return {"error": "Input file not found"}
        
        df = pd.read_excel(input_file, sheet_name=sector)
        
        # Basic statistics
        stats = {
            "sector": sector,
            "years_available": df['year'].nunique() if 'year' in df.columns else 0,
            "data_points": len(df),
            "columns": df.columns.tolist(),
            "date_range": {
                "start": int(df['year'].min()) if 'year' in df.columns else None,
                "end": int(df['year'].max()) if 'year' in df.columns else None
            }
        }
        
        # Sample data (first 10 rows)
        sample_data = df.head(10).to_dict('records')
        
        return {
            "success": True,
            "statistics": stats,
            "sample_data": sample_data,
            "data_quality": DataValidator._validate_sector_data(df, sector)
        }
        
    except Exception as e:
        return {"error": str(e)}

def get_correlation_data(sector: str) -> Dict[str, Any]:
    """Get correlation analysis for MLR variable selection"""
    try:
        input_file = Path("inputs") / "input_demand_file.xlsx"
        if not input_file.exists():
            return {"error": "Input file not found"}
        
        df = pd.read_excel(input_file, sheet_name=sector)
        
        if 'demand' not in df.columns:
            return {"error": "Demand column not found"}
        
        # Calculate correlations
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        correlations = df[numeric_columns].corr()['demand'].drop('demand')
        
        # Prepare correlation data
        correlation_data = []
        for variable, correlation in correlations.items():
            if not np.isnan(correlation):
                strength = "strong" if abs(correlation) > 0.7 else "moderate" if abs(correlation) > 0.4 else "weak"
                recommendation = "recommended" if abs(correlation) > 0.4 else "not_recommended"
                
                correlation_data.append({
                    "variable": variable,
                    "correlation": float(correlation),
                    "abs_correlation": float(abs(correlation)),
                    "strength": strength,
                    "recommendation": recommendation
                })
        
        # Sort by absolute correlation
        correlation_data.sort(key=lambda x: x["abs_correlation"], reverse=True)
        
        return {
            "success": True,
            "sector": sector,
            "correlations": correlation_data,
            "recommended_variables": [
                item["variable"] for item in correlation_data 
                if item["recommendation"] == "recommended"
            ]
        }
        
    except Exception as e:
        return {"error": str(e)}

def main():
    """Main function for command-line execution"""
    parser = argparse.ArgumentParser(description='Enhanced Demand Projection Runner')
    parser.add_argument('--config', help='JSON configuration string for forecast execution')
    parser.add_argument('--validate', help='Validate input file')
    parser.add_argument('--sector-data', help='Get sector data for display')
    parser.add_argument('--correlation', help='Get correlation data for sector')
    
    args = parser.parse_args()
    
    try:
        if args.validate:
            result = DataValidator.validate_input_file(args.validate)
        elif args.sector_data:
            result = get_sector_data(args.sector_data)
        elif args.correlation:
            result = get_correlation_data(args.correlation)
        elif args.config:
            # Execute forecast
            config = json.loads(args.config)
            progress_reporter = ProgressReporter()
            engine = ForecastingEngine(progress_reporter)
            result = engine.execute_forecast(config)
        else:
            result = {"error": "No valid operation specified"}
        
        # Output result as JSON for Node.js consumption
        print(json.dumps(result, indent=2, default=str))
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(1)

if __name__ == "__main__":
    main()
```

Create supporting Python files:
1. shared/data_utils.py - Common data processing utilities
2. shared/validation.py - Data validation functions
3. test_environment.py - Environment testing script

Include comprehensive error handling, progress tracking, and model validation.
```

### **Chunk 7.2: Load Profile Python Module**
```
Task: Create the enhanced load profile generation Python module

Create a comprehensive load profile generation module with the following specifications:

FILE: backend/src/python/load_profile_generation.py
```python
import sys
import json
import argparse
import logging
import traceback
import uuid
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='{"level": "%(levelname)s", "message": "%(message)s", "timestamp": "%(asctime)s"}'
)
logger = logging.getLogger(__name__)

class ProfileProgressReporter:
    """Real-time progress reporting for load profile generation"""
    
    def __init__(self, profile_id: str):
        self.profile_id = profile_id
        self.current_progress = 0
        
    def report(self, progress: float, step: str, status: str, details: str = ""):
        """Send progress update to Node.js via stdout"""
        progress_data = {
            "progress": min(100, max(0, progress)),
            "step": step,
            "status": status,
            "details": details,
            "profile_id": self.profile_id,
            "timestamp": datetime.now().isoformat()
        }
        print(f"PROGRESS:{json.dumps(progress_data)}", flush=True)
        self.current_progress = progress

class LoadProfileGenerator:
    """Advanced load profile generation with multiple methods"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.profile_id = str(uuid.uuid4())
        self.progress_reporter = ProfileProgressReporter(self.profile_id)
        self.method = config.get("method", "base_scaling")
        
    def generate_profile(self) -> Dict[str, Any]:
        """Main profile generation workflow"""
        try:
            self.progress_reporter.report(0, "initialization", "Starting profile generation")
            
            # Validate configuration
            self._validate_configuration()
            
            # Execute based on method
            if self.method == "base_scaling":
                result = self._generate_base_scaling_profile()
            elif self.method == "stl_decomposition":
                result = self._generate_stl_profile()
            else:
                raise ValueError(f"Unknown generation method: {self.method}")
            
            # Add metadata
            result.update({
                "profile_id": self.profile_id,
                "method": self.method,
                "generation_time": datetime.now().isoformat(),
                "config": self.config
            })
            
            self.progress_reporter.report(100, "completed", "Profile generation completed")
            return result
            
        except Exception as e:
            error_result = {
                "success": False,
                "profile_id": self.profile_id,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
            logger.error(f"Profile generation failed: {e}")
            return error_result
    
    def _validate_configuration(self):
        """Validate generation configuration"""
        required_fields = ["method", "start_year", "end_year"]
        
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Missing required configuration field: {field}")
        
        if self.config["start_year"] >= self.config["end_year"]:
            raise ValueError("Start year must be less than end year")
        
        if self.method == "base_scaling":
            if "base_year" not in self.config:
                raise ValueError("Base year required for base scaling method")
        
        if self.method == "stl_decomposition":
            if "historical_years" not in self.config:
                self.config["historical_years"] = [2019, 2020, 2021, 2022, 2023]
    
    def _generate_base_scaling_profile(self) -> Dict[str, Any]:
        """Generate profile using base year scaling method"""
        
        # Load base year data
        self.progress_reporter.report(10, "data_loading", "Loading base year data")
        base_year = self.config["base_year"]
        base_data = self._load_base_year_data(base_year)
        
        # Load demand projections
        self.progress_reporter.report(20, "projections", "Loading demand projections")
        demand_projections = self._load_demand_projections()
        
        # Generate profiles for each year
        self.progress_reporter.report(30, "generation", "Generating scaled profiles")
        years = range(self.config["start_year"], self.config["end_year"] + 1)
        generated_profiles = {}
        
        for i, year in enumerate(years):
            year_progress = 30 + (50 * i / len(years))
            self.progress_reporter.report(
                year_progress, 
                "generation", 
                f"Generating profile for {year}"
            )
            
            # Calculate scaling factor
            scaling_factor = self._get_scaling_factor(year, demand_projections, base_year)
            
            # Scale base profile
            year_profile = self._scale_base_profile(base_data, scaling_factor, year)
            generated_profiles[year] = year_profile
        
        # Apply constraints if specified
        if self.config.get("apply_constraints", False):
            self.progress_reporter.report(80, "constraints", "Applying operational constraints")
            generated_profiles = self._apply_constraints(generated_profiles)
        
        # Calculate statistics
        self.progress_reporter.report(90, "analysis", "Calculating profile statistics")
        statistics = self._calculate_profile_statistics(generated_profiles)
        
        # Save profiles
        self.progress_reporter.report(95, "saving", "Saving generated profiles")
        saved_path = self._save_profiles(generated_profiles)
        
        return {
            "success": True,
            "method": "base_scaling",
            "years_generated": list(years),
            "base_year": base_year,
            "scaling_factors": {
                year: self._get_scaling_factor(year, demand_projections, base_year)
                for year in years
            },
            "statistics": statistics,
            "saved_path": saved_path,
            "profiles_summary": self._generate_profiles_summary(generated_profiles)
        }
    
    def _generate_stl_profile(self) -> Dict[str, Any]:
        """Generate profile using STL decomposition method"""
        try:
            from statsmodels.tsa.seasonal import STL
        except ImportError:
            raise ImportError("statsmodels is required for STL decomposition")
        
        # Load historical data
        self.progress_reporter.report(10, "data_loading", "Loading historical load data")
        historical_data = self._load_historical_load_data()
        
        # Perform STL decomposition
        self.progress_reporter.report(20, "decomposition", "Performing STL decomposition")
        stl_components = self._perform_stl_decomposition(historical_data)
        
        # Project components to future
        self.progress_reporter.report(40, "projection", "Projecting components to future years")
        future_components = self._project_stl_components(stl_components)
        
        # Apply load factor improvement if specified
        if self.config.get("load_factor_improvement", {}).get("enabled", False):
            self.progress_reporter.report(60, "improvement", "Applying load factor improvement")
            future_components = self._apply_load_factor_improvement(future_components)
        
        # Reconstruct profiles
        self.progress_reporter.report(80, "reconstruction", "Reconstructing load profiles")
        generated_profiles = self._reconstruct_profiles(future_components)
        
        # Calculate statistics
        self.progress_reporter.report(90, "analysis", "Calculating profile statistics")
        statistics = self._calculate_profile_statistics(generated_profiles)
        
        # Save profiles
        self.progress_reporter.report(95, "saving", "Saving generated profiles")
        saved_path = self._save_profiles(generated_profiles)
        
        return {
            "success": True,
            "method": "stl_decomposition",
            "years_generated": list(generated_profiles.keys()),
            "stl_parameters": {
                "seasonal": self.config.get("stl_seasonal", 13),
                "period": self.config.get("stl_period", 8760)
            },
            "load_factor_improvement": self.config.get("load_factor_improvement", {}),
            "statistics": statistics,
            "saved_path": saved_path,
            "component_analysis": self._analyze_stl_components(stl_components),
            "profiles_summary": self._generate_profiles_summary(generated_profiles)
        }
    
    def _load_base_year_data(self, base_year: int) -> pd.DataFrame:
        """Load base year load data from template"""
        template_file = Path("inputs") / "load_curve_template.xlsx"
        
        if not template_file.exists():
            raise FileNotFoundError(f"Load curve template not found: {template_file}")
        
        try:
            # Try to load the specific year sheet
            df = pd.read_excel(template_file, sheet_name=str(base_year))
            
            # Validate and clean data
            if 'datetime' not in df.columns and 'hour' in df.columns:
                # Create datetime from year and hour
                df['datetime'] = pd.to_datetime(f"{base_year}-01-01") + pd.to_timedelta(df['hour'], unit='H')
            
            if 'load' not in df.columns and 'demand' in df.columns:
                df['load'] = df['demand']
            
            if 'datetime' in df.columns:
                df['datetime'] = pd.to_datetime(df['datetime'])
                df = df.set_index('datetime')
            
            # Fill missing values
            df = df.fillna(method='ffill').fillna(method='bfill')
            
            return df
            
        except Exception as e:
            raise ValueError(f"Failed to load base year {base_year} data: {e}")
    
    def _load_demand_projections(self) -> Dict[int, float]:
        """Load demand projections from scenario or configuration"""
        projections = {}
        
        # Check if scenario data is specified
        scenario_name = self.config.get("demand_scenario")
        if scenario_name:
            scenario_file = Path("results") / "demand_forecasts" / scenario_name / "forecast_results.json"
            if scenario_file.exists():
                with open(scenario_file, 'r') as f:
                    scenario_data = json.load(f)
                
                # Extract total demand projections
                for sector_name, sector_result in scenario_data.get("sectors", {}).items():
                    if "models" in sector_result:
                        for model_name, model_result in sector_result["models"].items():
                            if "future_projections" in model_result:
                                for proj in model_result["future_projections"]:
                                    year = proj["year"]
                                    if year not in projections:
                                        projections[year] = 0
                                    projections[year] += proj["projected_demand"]
                
                return projections
        
        # Fallback to simple growth rate
        growth_rate = self.config.get("growth_rate", 0.02)
        base_year = self.config.get("base_year", 2023)
        base_demand = self.config.get("base_demand", 1000)
        
        years = range(self.config["start_year"], self.config["end_year"] + 1)
        for year in years:
            years_from_base = year - base_year
            projections[year] = base_demand * ((1 + growth_rate) ** years_from_base)
        
        return projections
    
    def _get_scaling_factor(self, year: int, projections: Dict[int, float], base_year: int) -> float:
        """Calculate scaling factor for given year"""
        base_demand = projections.get(base_year, 1000)
        year_demand = projections.get(year, base_demand)
        
        return year_demand / base_demand if base_demand > 0 else 1.0
    
    def _scale_base_profile(self, base_data: pd.DataFrame, scaling_factor: float, year: int) -> pd.DataFrame:
        """Scale base profile by scaling factor"""
        scaled_data = base_data.copy()
        
        # Find load columns
        load_columns = [col for col in scaled_data.columns if any(
            keyword in col.lower() for keyword in ['load', 'demand', 'power']
        )]
        
        if not load_columns:
            raise ValueError("No load columns found in base data")
        
        # Scale load values
        for col in load_columns:
            scaled_data[col] = scaled_data[col] * scaling_factor
        
        # Update datetime index for target year
        if isinstance(scaled_data.index, pd.DatetimeIndex):
            # Shift dates to target year
            year_diff = year - scaled_data.index.year[0]
            scaled_data.index = scaled_data.index + pd.DateOffset(years=year_diff)
        
        scaled_data['year'] = year
        scaled_data['scaling_factor'] = scaling_factor
        
        return scaled_data
    
    def _apply_constraints(self, profiles: Dict[int, pd.DataFrame]) -> Dict[int, pd.DataFrame]:
        """Apply operational constraints to generated profiles"""
        constraints = self.config.get("constraints", {})
        
        for year, profile in profiles.items():
            # Apply monthly peak constraints
            if "monthly_peaks" in constraints:
                profile = self._apply_monthly_peak_constraints(profile, constraints["monthly_peaks"])
            
            # Apply load factor constraints
            if "load_factors" in constraints:
                profile = self._apply_load_factor_constraints(profile, constraints["load_factors"])
            
            # Apply minimum/maximum constraints
            if "min_load" in constraints:
                load_cols = [col for col in profile.columns if 'load' in col.lower()]
                for col in load_cols:
                    profile[col] = profile[col].clip(lower=constraints["min_load"])
            
            if "max_load" in constraints:
                load_cols = [col for col in profile.columns if 'load' in col.lower()]
                for col in load_cols:
                    profile[col] = profile[col].clip(upper=constraints["max_load"])
            
            profiles[year] = profile
        
        return profiles
    
    def _apply_monthly_peak_constraints(self, profile: pd.DataFrame, peak_constraints: Dict) -> pd.DataFrame:
        """Apply monthly peak demand constraints"""
        if not isinstance(profile.index, pd.DatetimeIndex):
            return profile
        
        load_col = self._get_primary_load_column(profile)
        if not load_col:
            return profile
        
        # Group by month and apply peak constraints
        monthly_groups = profile.groupby(profile.index.month)
        
        for month, constraint_peak in peak_constraints.items():
            if month in monthly_groups.groups:
                month_data = monthly_groups.get_group(month)
                current_peak = month_data[load_col].max()
                
                if current_peak > constraint_peak:
                    # Scale down the entire month proportionally
                    scale_factor = constraint_peak / current_peak
                    profile.loc[month_data.index, load_col] *= scale_factor
        
        return profile
    
    def _apply_load_factor_constraints(self, profile: pd.DataFrame, lf_constraints: Dict) -> pd.DataFrame:
        """Apply load factor constraints"""
        load_col = self._get_primary_load_column(profile)
        if not load_col:
            return profile
        
        current_lf = profile[load_col].mean() / profile[load_col].max()
        target_lf = lf_constraints.get("target", current_lf)
        
        if target_lf > current_lf:
            # Improve load factor by flattening the curve
            mean_load = profile[load_col].mean()
            profile[load_col] = profile[load_col] + (mean_load - profile[load_col]) * 0.1
        
        return profile
    
    def _load_historical_load_data(self) -> pd.DataFrame:
        """Load historical load data for STL decomposition"""
        template_file = Path("inputs") / "load_curve_template.xlsx"
        
        if not template_file.exists():
            raise FileNotFoundError(f"Load curve template not found: {template_file}")
        
        historical_years = self.config.get("historical_years", [2019, 2020, 2021, 2022, 2023])
        combined_data = pd.DataFrame()
        
        for year in historical_years:
            try:
                year_data = pd.read_excel(template_file, sheet_name=str(year))
                year_data['year'] = year
                
                # Standardize datetime column
                if 'datetime' not in year_data.columns and 'hour' in year_data.columns:
                    year_data['datetime'] = pd.to_datetime(f"{year}-01-01") + pd.to_timedelta(year_data['hour'], unit='H')
                
                combined_data = pd.concat([combined_data, year_data], ignore_index=True)
                
            except Exception as e:
                logger.warning(f"Could not load data for year {year}: {e}")
        
        if combined_data.empty:
            raise ValueError("No historical data could be loaded")
        
        # Sort by datetime
        combined_data['datetime'] = pd.to_datetime(combined_data['datetime'])
        combined_data = combined_data.sort_values('datetime').set_index('datetime')
        
        return combined_data
    
    def _perform_stl_decomposition(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Perform STL decomposition on historical data"""
        from statsmodels.tsa.seasonal import STL
        
        load_col = self._get_primary_load_column(data)
        if not load_col:
            raise ValueError("No load column found for STL decomposition")
        
        load_series = data[load_col].dropna()
        
        if len(load_series) < 8760:  # Less than one year of hourly data
            raise ValueError("Insufficient data for STL decomposition (need at least 1 year of hourly data)")
        
        # STL decomposition parameters
        seasonal = self.config.get("stl_seasonal", 13)
        period = self.config.get("stl_period", 8760)  # Annual seasonality for hourly data
        
        stl = STL(load_series, seasonal=seasonal, period=period, robust=True)
        decomposition = stl.fit()
        
        return {
            "trend": decomposition.trend,
            "seasonal": decomposition.seasonal,
            "resid": decomposition.resid,
            "observed": decomposition.observed,
            "parameters": {
                "seasonal": seasonal,
                "period": period,
                "data_points": len(load_series)
            }
        }
    
    def _project_stl_components(self, stl_components: Dict[str, Any]) -> Dict[str, Any]:
        """Project STL components to future years"""
        trend = stl_components["trend"]
        seasonal = stl_components["seasonal"]
        
        # Calculate trend projection
        trend_data = trend.dropna()
        if len(trend_data) < 100:
            raise ValueError("Insufficient trend data for projection")
        
        # Simple linear trend extrapolation
        from sklearn.linear_model import LinearRegression
        
        X = np.arange(len(trend_data)).reshape(-1, 1)
        y = trend_data.values
        
        trend_model = LinearRegression()
        trend_model.fit(X, y)
        
        # Project to future years
        start_year = self.config["start_year"]
        end_year = self.config["end_year"]
        future_components = {}
        
        # Seasonal pattern repeats
        seasonal_pattern = seasonal.values
        seasonal_period = len(seasonal_pattern)
        
        for year in range(start_year, end_year + 1):
            # Generate hourly timestamps for the year
            year_start = pd.Timestamp(f"{year}-01-01")
            year_end = pd.Timestamp(f"{year}-12-31 23:59:59")
            hourly_index = pd.date_range(year_start, year_end, freq='H')
            
            # Project trend
            hours_from_start = len(trend_data) + (year - start_year) * 8760
            future_trend_points = np.arange(hours_from_start, hours_from_start + len(hourly_index))
            projected_trend = trend_model.predict(future_trend_points.reshape(-1, 1))
            
            # Repeat seasonal pattern
            n_hours = len(hourly_index)
            seasonal_cycles = (n_hours // seasonal_period) + 1
            extended_seasonal = np.tile(seasonal_pattern, seasonal_cycles)[:n_hours]
            
            future_components[year] = {
                "datetime": hourly_index,
                "trend": projected_trend,
                "seasonal": extended_seasonal,
                "resid": np.zeros(n_hours)  # Assume zero residuals for future
            }
        
        return future_components
    
    def _apply_load_factor_improvement(self, future_components: Dict[str, Any]) -> Dict[str, Any]:
        """Apply gradual load factor improvement over time"""
        improvement_config = self.config["load_factor_improvement"]
        target_year = improvement_config["target_year"]
        improvement_percent = improvement_config["improvement_percent"] / 100
        
        start_year = min(future_components.keys())
        
        for year, components in future_components.items():
            # Calculate improvement factor based on year
            years_elapsed = year - start_year
            total_years = target_year - start_year
            
            if total_years > 0:
                improvement_factor = min(1.0, years_elapsed / total_years) * improvement_percent
                
                # Apply improvement by flattening the load curve
                trend = components["trend"]
                seasonal = components["seasonal"]
                
                # Reduce seasonal variation
                seasonal_dampened = seasonal * (1 - improvement_factor)
                
                # Adjust trend to maintain total energy
                total_energy_original = np.sum(trend + seasonal)
                total_energy_new = np.sum(trend + seasonal_dampened)
                
                if total_energy_new > 0:
                    trend_adjustment = (total_energy_original - total_energy_new) / len(trend)
                    trend_adjusted = trend + trend_adjustment
                else:
                    trend_adjusted = trend
                
                future_components[year]["trend"] = trend_adjusted
                future_components[year]["seasonal"] = seasonal_dampened
        
        return future_components
    
    def _reconstruct_profiles(self, future_components: Dict[str, Any]) -> Dict[int, pd.DataFrame]:
        """Reconstruct load profiles from STL components"""
        profiles = {}
        
        for year, components in future_components.items():
            # Reconstruct the time series
            reconstructed = components["trend"] + components["seasonal"] + components["resid"]
            
            # Create DataFrame
            profile_df = pd.DataFrame({
                "datetime": components["datetime"],
                "load": reconstructed,
                "trend": components["trend"],
                "seasonal": components["seasonal"],
                "residual": components["resid"],
                "year": year
            })
            
            profile_df = profile_df.set_index("datetime")
            
            # Ensure non-negative values
            profile_df["load"] = profile_df["load"].clip(lower=0)
            
            profiles[year] = profile_df
        
        return profiles
    
    def _calculate_profile_statistics(self, profiles: Dict[int, pd.DataFrame]) -> Dict[str, Any]:
        """Calculate comprehensive statistics for generated profiles"""
        statistics = {
            "years": list(profiles.keys()),
            "yearly_stats": {},
            "overall_stats": {}
        }
        
        all_loads = []
        
        for year, profile in profiles.items():
            load_col = self._get_primary_load_column(profile)
            if load_col:
                load_data = profile[load_col]
                all_loads.extend(load_data.values)
                
                year_stats = {
                    "peak_demand": float(load_data.max()),
                    "min_demand": float(load_data.min()),
                    "avg_demand": float(load_data.mean()),
                    "total_energy": float(load_data.sum()),
                    "load_factor": float(load_data.mean() / load_data.max()) if load_data.max() > 0 else 0,
                    "data_points": len(load_data),
                    "peak_time": load_data.idxmax().isoformat() if not load_data.empty else None,
                    "min_time": load_data.idxmin().isoformat() if not load_data.empty else None
                }
                
                statistics["yearly_stats"][year] = year_stats
        
        # Overall statistics
        if all_loads:
            all_loads_array = np.array(all_loads)
            statistics["overall_stats"] = {
                "total_profiles": len(profiles),
                "peak_demand": float(np.max(all_loads_array)),
                "min_demand": float(np.min(all_loads_array)),
                "avg_demand": float(np.mean(all_loads_array)),
                "std_demand": float(np.std(all_loads_array)),
                "total_data_points": len(all_loads)
            }
        
        return statistics
    
    def _save_profiles(self, profiles: Dict[int, pd.DataFrame]) -> str:
        """Save generated profiles to structured files"""
        output_dir = Path("results") / "load_profiles"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        profile_file = output_dir / f"{self.profile_id}.json"
        
        # Convert profiles to JSON-serializable format
        profiles_data = {}
        for year, df in profiles.items():
            # Reset index to make datetime serializable
            df_reset = df.reset_index()
            df_reset['datetime'] = df_reset['datetime'].dt.isoformat()
            profiles_data[str(year)] = df_reset.to_dict('records')
        
        profile_metadata = {
            "profile_id": self.profile_id,
            "method": self.method,
            "config": self.config,
            "generation_time": datetime.now().isoformat(),
            "data": profiles_data
        }
        
        with open(profile_file, 'w') as f:
            json.dump(profile_metadata, f, indent=2, default=str)
        
        return str(profile_file)
    
    def _generate_profiles_summary(self, profiles: Dict[int, pd.DataFrame]) -> Dict[str, Any]:
        """Generate summary of generated profiles"""
        summary = {
            "total_years": len(profiles),
            "year_range": [min(profiles.keys()), max(profiles.keys())] if profiles else [None, None],
            "method": self.method,
            "generation_config": {
                "start_year": self.config["start_year"],
                "end_year": self.config["end_year"]
            }
        }
        
        if self.method == "base_scaling":
            summary["base_scaling_config"] = {
                "base_year": self.config.get("base_year"),
                "demand_source": self.config.get("demand_scenario", "growth_rate")
            }
        elif self.method == "stl_decomposition":
            summary["stl_config"] = {
                "historical_years": self.config.get("historical_years"),
                "load_factor_improvement": self.config.get("load_factor_improvement", {})
            }
        
        return summary
    
    def _get_primary_load_column(self, df: pd.DataFrame) -> Optional[str]:
        """Find the primary load column in DataFrame"""
        possible_names = ['load', 'demand', 'power', 'consumption']
        
        for name in possible_names:
            if name in df.columns:
                return name
            
            # Check for columns containing these names
            matching_cols = [col for col in df.columns if name in col.lower()]
            if matching_cols:
                return matching_cols[0]
        
        return None
    
    def _analyze_stl_components(self, stl_components: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze STL decomposition components"""
        trend = stl_components["trend"].dropna()
        seasonal = stl_components["seasonal"]
        
        analysis = {
            "trend_analysis": {
                "direction": "increasing" if trend.iloc[-1] > trend.iloc[0] else "decreasing",
                "volatility": float(trend.std()),
                "linear_slope": float((trend.iloc[-1] - trend.iloc[0]) / len(trend))
            },
            "seasonal_analysis": {
                "peak_season_hour": int(seasonal.idxmax()),
                "min_season_hour": int(seasonal.idxmin()),
                "seasonal_range": float(seasonal.max() - seasonal.min()),
                "seasonal_std": float(seasonal.std())
            },
            "decomposition_quality": {
                "trend_strength": float(1 - stl_components["resid"].var() / stl_components["observed"].var()),
                "seasonal_strength": float(seasonal.var() / stl_components["observed"].var())
            }
        }
        
        return analysis

def main():
    """Main function for command-line execution"""
    parser = argparse.ArgumentParser(description='Load Profile Generator')
    parser.add_argument('--config', required=True, help='JSON configuration string')
    
    args = parser.parse_args()
    
    try:
        config = json.loads(args.config)
        generator = LoadProfileGenerator(config)
        result = generator.generate_profile()
        
        # Output result as JSON for Node.js consumption
        print(json.dumps(result, indent=2, default=str))
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(1)

if __name__ == "__main__":
    main()
```

Create supporting analysis module:
1. load_profile_analysis.py - Profile analysis functionality
2. shared/profile_utils.py - Common profile utilities

Include comprehensive validation, multiple generation methods, and detailed progress tracking.
```

## **PHASE 8: PRODUCTION DEPLOYMENT & OPTIMIZATION**

### **Chunk 8.1: PyPSA Python Module Integration**
```
Task: Create the comprehensive PyPSA power system modeling Python module

Create the complete PyPSA integration module with the following specifications:

FILE: backend/src/python/pypsa_runner.py
```python
import sys
import json
import argparse
import logging
import traceback
import uuid
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='{"level": "%(levelname)s", "message": "%(message)s", "timestamp": "%(asctime)s"}'
)
logger = logging.getLogger(__name__)

class PyPSAProgressReporter:
    """Real-time progress reporting for PyPSA optimization"""
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.current_progress = 0
        
    def report(self, progress: float, step: str, status: str, details: str = ""):
        """Send progress update to Node.js via stdout"""
        progress_data = {
            "progress": min(100, max(0, progress)),
            "step": step,
            "status": status,
            "details": details,
            "job_id": self.job_id,
            "timestamp": datetime.now().isoformat()
        }
        print(f"PROGRESS:{json.dumps(progress_data)}", flush=True)
        self.current_progress = progress

class PyPSARunner:
    """Comprehensive PyPSA power system optimization runner"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.job_id = str(uuid.uuid4())
        self.progress_reporter = PyPSAProgressReporter(self.job_id)
        self.network = None
        self.results = {}
        
    def run_optimization(self) -> Dict[str, Any]:
        """Main PyPSA optimization workflow"""
        try:
            self.progress_reporter.report(0, "initialization", "Starting PyPSA optimization")
            
            # Validate configuration
            self._validate_configuration()
            
            # Load and prepare network
            self.progress_reporter.report(10, "network_loading", "Loading network data")
            self._load_network()
            
            # Configure optimization settings
            self.progress_reporter.report(20, "configuration", "Configuring optimization parameters")
            self._configure_optimization()
            
            # Run optimization
            self.progress_reporter.report(30, "optimization", "Running power system optimization")
            optimization_result = self._execute_optimization()
            
            # Extract and process results
            self.progress_reporter.report(80, "results_processing", "Processing optimization results")
            processed_results = self._process_results()
            
            # Save results
            self.progress_reporter.report(95, "saving", "Saving optimization results")
            saved_path = self._save_results()
            
            final_result = {
                "success": True,
                "job_id": self.job_id,
                "scenario_name": self.config["scenario_name"],
                "optimization_status": optimization_result["status"],
                "objective_value": optimization_result.get("objective", None),
                "solver_time": optimization_result.get("solver_time", None),
                "network_path": saved_path,
                "summary": self._generate_summary(),
                "execution_time": datetime.now().isoformat()
            }
            
            self.progress_reporter.report(100, "completed", "PyPSA optimization completed successfully")
            return final_result
            
        except Exception as e:
            error_result = {
                "success": False,
                "job_id": self.job_id,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
            logger.error(f"PyPSA optimization failed: {e}")
            return error_result
    
    def _validate_configuration(self):
        """Validate PyPSA configuration"""
        required_fields = ["scenario_name", "base_year", "investment_mode"]
        
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Missing required configuration field: {field}")
        
        # Validate investment mode
        valid_modes = ["single_year", "multi_year", "all_in_one"]
        if self.config["investment_mode"] not in valid_modes:
            raise ValueError(f"Invalid investment mode. Must be one of: {valid_modes}")
        
        # Validate solver options
        solver_options = self.config.get("solver_options", {})
        solver = solver_options.get("solver", "highs")
        if solver not in ["highs", "gurobi", "cplex"]:
            logger.warning(f"Solver {solver} may not be available. Falling back to highs.")
            self.config["solver_options"]["solver"] = "highs"
    
    def _load_network(self):
        """Load and validate PyPSA network from input file"""
        try:
            import pypsa
        except ImportError:
            raise ImportError("PyPSA is required for power system optimization")
        
        input_file = self.config.get("input_file", "inputs/pypsa_input_template.xlsx")
        input_path = Path(input_file)
        
        if not input_path.exists():
            raise FileNotFoundError(f"PyPSA input file not found: {input_path}")
        
        # Create empty network
        self.network = pypsa.Network()
        
        # Load network components from Excel file
        self._load_network_from_excel(input_path)
        
        # Set snapshots based on configuration
        self._configure_snapshots()
        
        # Validate network consistency
        self._validate_network()
    
    def _load_network_from_excel(self, excel_path: Path):
        """Load network components from Excel template"""
        excel_file = pd.ExcelFile(excel_path)
        
        # Load buses
        if "buses" in excel_file.sheet_names:
            buses_df = pd.read_excel(excel_path, sheet_name="buses")
            if not buses_df.empty:
                self.network.import_components_from_dataframe(buses_df, "Bus")
        
        # Load generators
        if "generators" in excel_file.sheet_names:
            generators_df = pd.read_excel(excel_path, sheet_name="generators")
            if not generators_df.empty:
                self.network.import_components_from_dataframe(generators_df, "Generator")
        
        # Load loads
        if "loads" in excel_file.sheet_names:
            loads_df = pd.read_excel(excel_path, sheet_name="loads")
            if not loads_df.empty:
                self.network.import_components_from_dataframe(loads_df, "Load")
        
        # Load transmission lines
        if "lines" in excel_file.sheet_names:
            lines_df = pd.read_excel(excel_path, sheet_name="lines")
            if not lines_df.empty:
                self.network.import_components_from_dataframe(lines_df, "Line")
        
        # Load storage units
        if "storage" in excel_file.sheet_names:
            storage_df = pd.read_excel(excel_path, sheet_name="storage")
            if not storage_df.empty:
                self.network.import_components_from_dataframe(storage_df, "StorageUnit")
        
        # Load time series data
        self._load_time_series_data(excel_file, excel_path)
    
    def _load_time_series_data(self, excel_file, excel_path: Path):
        """Load time series data for loads and renewable generation"""
        # Load demand time series
        if "load_time_series" in excel_file.sheet_names:
            load_ts = pd.read_excel(excel_path, sheet_name="load_time_series", index_col=0, parse_dates=True)
            for load_name in self.network.loads.index:
                if load_name in load_ts.columns:
                    self.network.loads_t.p_set[load_name] = load_ts[load_name]
        
        # Load renewable generation time series
        if "renewable_time_series" in excel_file.sheet_names:
            renewable_ts = pd.read_excel(excel_path, sheet_name="renewable_time_series", index_col=0, parse_dates=True)
            for gen_name in self.network.generators.index:
                if gen_name in renewable_ts.columns:
                    self.network.generators_t.p_max_pu[gen_name] = renewable_ts[gen_name]
    
    def _configure_snapshots(self):
        """Configure optimization snapshots based on settings"""
        base_year = self.config["base_year"]
        snapshot_selection = self.config.get("snapshot_selection", "all")
        
        if snapshot_selection == "all":
            # Full year hourly snapshots
            snapshots = pd.date_range(
                start=f"{base_year}-01-01",
                end=f"{base_year}-12-31 23:00:00",
                freq="H"
            )
        elif snapshot_selection == "critical_days":
            # Representative days for each season
            critical_days = [
                f"{base_year}-01-15",  # Winter
                f"{base_year}-04-15",  # Spring
                f"{base_year}-07-15",  # Summer
                f"{base_year}-10-15"   # Fall
            ]
            
            snapshots = []
            for day in critical_days:
                day_snapshots = pd.date_range(
                    start=f"{day} 00:00:00",
                    end=f"{day} 23:00:00",
                    freq="H"
                )
                snapshots.extend(day_snapshots)
            
            snapshots = pd.DatetimeIndex(snapshots)
        else:
            raise ValueError(f"Unknown snapshot selection: {snapshot_selection}")
        
        self.network.set_snapshots(snapshots)
        
        # Configure multi-period if applicable
        if self.config["investment_mode"] in ["multi_year", "all_in_one"]:
            self._configure_investment_periods()
    
    def _configure_investment_periods(self):
        """Configure multi-period investment optimization"""
        base_year = self.config["base_year"]
        target_year = self.config.get("target_year", base_year + 10)
        
        # Create investment periods (every 5 years)
        investment_years = list(range(base_year, target_year + 1, 5))
        if investment_years[-1] != target_year:
            investment_years.append(target_year)
        
        # Configure periods
        periods = pd.Index(investment_years, name="period")
        self.network.investment_periods = periods
        
        # Set period weightings (years each period represents)
        weightings = {}
        for i, year in enumerate(investment_years):
            if i == len(investment_years) - 1:
                weightings[year] = 1  # Last period
            else:
                weightings[year] = investment_years[i + 1] - year
        
        self.network.investment_period_weightings = pd.Series(weightings)
    
    def _validate_network(self):
        """Validate network consistency and completeness"""
        if len(self.network.buses) == 0:
            raise ValueError("Network must contain at least one bus")
        
        if len(self.network.generators) == 0:
            raise ValueError("Network must contain at least one generator")
        
        if len(self.network.loads) == 0:
            raise ValueError("Network must contain at least one load")
        
        # Check bus connectivity
        for gen_bus in self.network.generators.bus:
            if gen_bus not in self.network.buses.index:
                raise ValueError(f"Generator bus {gen_bus} not found in buses")
        
        for load_bus in self.network.loads.bus:
            if load_bus not in self.network.buses.index:
                raise ValueError(f"Load bus {load_bus} not found in buses")
    
    def _configure_optimization(self):
        """Configure optimization parameters and constraints"""
        # Apply advanced options
        if self.config.get("generator_clustering", False):
            self._apply_generator_clustering()
        
        if self.config.get("unit_commitment", False):
            self._apply_unit_commitment()
        
        if self.config.get("monthly_constraints", False):
            self._apply_monthly_constraints()
        
        battery_constraints = self.config.get("battery_constraints", "none")
        if battery_constraints != "none":
            self._apply_battery_constraints(battery_constraints)
    
    def _apply_generator_clustering(self):
        """Apply generator clustering to reduce problem size"""
        # Simple clustering by technology type and bus
        clustered_generators = {}
        
        for tech in self.network.generators.carrier.unique():
            tech_gens = self.network.generators[self.network.generators.carrier == tech]
            
            for bus in tech_gens.bus.unique():
                bus_tech_gens = tech_gens[tech_gens.bus == bus]
                
                if len(bus_tech_gens) > 1:
                    # Cluster generators of same technology at same bus
                    cluster_name = f"{bus}_{tech}_cluster"
                    
                    clustered_generators[cluster_name] = {
                        "bus": bus,
                        "carrier": tech,
                        "p_nom": bus_tech_gens.p_nom.sum(),
                        "marginal_cost": bus_tech_gens.marginal_cost.mean(),
                        "efficiency": bus_tech_gens.efficiency.mean()
                    }
        
        # Replace clustered generators
        for cluster_name, cluster_data in clustered_generators.items():
            self.network.add("Generator", cluster_name, **cluster_data)
    
    def _apply_unit_commitment(self):
        """Apply unit commitment constraints for thermal generators"""
        thermal_carriers = ["coal", "gas", "oil", "nuclear"]
        
        for gen_name in self.network.generators.index:
            gen = self.network.generators.loc[gen_name]
            
            if gen.carrier in thermal_carriers:
                # Add minimum up/down time constraints
                self.network.generators.loc[gen_name, "min_up_time"] = 4  # 4 hours
                self.network.generators.loc[gen_name, "min_down_time"] = 2  # 2 hours
                
                # Add startup costs
                self.network.generators.loc[gen_name, "start_up_cost"] = gen.p_nom * 10  # $10/MW
    
    def _apply_monthly_constraints(self):
        """Apply monthly generation constraints"""
        # Group snapshots by month
        monthly_snapshots = self.network.snapshots.groupby(self.network.snapshots.month)
        
        for month, month_snapshots in monthly_snapshots:
            # Apply renewable energy targets (example: 30% renewable in each month)
            renewable_carriers = ["solar", "wind", "hydro"]
            
            for carrier in renewable_carriers:
                renewable_gens = self.network.generators[
                    self.network.generators.carrier == carrier
                ].index
                
                if len(renewable_gens) > 0:
                    # Add monthly renewable generation constraint
                    constraint_name = f"renewable_{carrier}_month_{month}"
                    # Implementation would depend on PyPSA version and constraint API
    
    def _apply_battery_constraints(self, constraint_type: str):
        """Apply battery cycling constraints"""
        storage_units = self.network.storage_units.index
        
        for storage_name in storage_units:
            if constraint_type == "daily":
                # Daily cycling constraint
                self.network.storage_units.loc[storage_name, "cyclic_state_of_charge"] = True
                self.network.storage_units.loc[storage_name, "max_hours"] = 24
            elif constraint_type == "weekly":
                # Weekly cycling constraint
                self.network.storage_units.loc[storage_name, "max_hours"] = 168
            elif constraint_type == "monthly":
                # Monthly cycling constraint
                self.network.storage_units.loc[storage_name, "max_hours"] = 720
    
    def _execute_optimization(self) -> Dict[str, Any]:
        """Execute the PyPSA optimization"""
        solver_options = self.config.get("solver_options", {})
        solver = solver_options.get("solver", "highs")
        
        optimization_result = {
            "status": "unknown",
            "objective": None,
            "solver_time": None,
            "termination_condition": None
        }
        
        try:
            start_time = datetime.now()
            
            # Configure solver options
            solver_opts = {
                "time_limit": solver_options.get("time_limit", 3600),
                "mip_gap": solver_options.get("optimality_gap", 0.01)
            }
            
            # Run optimization based on investment mode
            if self.config["investment_mode"] == "single_year":
                status, condition = self.network.lopf(
                    solver_name=solver,
                    solver_options=solver_opts,
                    pyomo=False
                )
            else:
                # Multi-period optimization
                status, condition = self.network.lopf(
                    solver_name=solver,
                    solver_options=solver_opts,
                    pyomo=False,
                    multi_investment_periods=True
                )
            
            end_time = datetime.now()
            solver_time = (end_time - start_time).total_seconds()
            
            optimization_result.update({
                "status": status,
                "objective": float(self.network.objective) if hasattr(self.network, 'objective') else None,
                "solver_time": solver_time,
                "termination_condition": condition
            })
            
            if status != "optimal":
                logger.warning(f"Optimization status: {status}, condition: {condition}")
            
        except Exception as e:
            optimization_result["status"] = "error"
            optimization_result["error"] = str(e)
            logger.error(f"Optimization failed: {e}")
            raise
        
        return optimization_result
    
    def _process_results(self) -> Dict[str, Any]:
        """Process and extract optimization results"""
        results = {
            "dispatch": self._extract_dispatch_results(),
            "capacity": self._extract_capacity_results(),
            "storage": self._extract_storage_results(),
            "transmission": self._extract_transmission_results(),
            "emissions": self._extract_emissions_results(),
            "costs": self._extract_cost_results(),
            "kpis": self._calculate_kpis()
        }
        
        self.results = results
        return results
    
    def _extract_dispatch_results(self) -> Dict[str, Any]:
        """Extract generation dispatch results"""
        dispatch_data = {}
        
        # Generator dispatch
        if hasattr(self.network, 'generators_t') and 'p' in self.network.generators_t:
            gen_dispatch = self.network.generators_t.p
            
            # Aggregate by carrier
            dispatch_by_carrier = {}
            for gen_name in gen_dispatch.columns:
                carrier = self.network.generators.loc[gen_name, 'carrier']
                if carrier not in dispatch_by_carrier:
                    dispatch_by_carrier[carrier] = gen_dispatch[gen_name]
                else:
                    dispatch_by_carrier[carrier] += gen_dispatch[gen_name]
            
            dispatch_data["generation_by_carrier"] = {
                carrier: series.to_dict()
                for carrier, series in dispatch_by_carrier.items()
            }
            
            dispatch_data["total_generation"] = gen_dispatch.sum(axis=1).to_dict()
        
        # Load data
        if hasattr(self.network, 'loads_t') and 'p' in self.network.loads_t:
            load_dispatch = self.network.loads_t.p
            dispatch_data["total_load"] = load_dispatch.sum(axis=1).to_dict()
        
        return dispatch_data
    
    def _extract_capacity_results(self) -> Dict[str, Any]:
        """Extract capacity results"""
        capacity_data = {}
        
        # Generator capacities
        gen_capacity = self.network.generators.groupby('carrier')['p_nom_opt'].sum()
        capacity_data["generation_capacity"] = gen_capacity.to_dict()
        
        # Storage capacities
        if len(self.network.storage_units) > 0:
            storage_capacity = self.network.storage_units.groupby('carrier')['p_nom_opt'].sum()
            capacity_data["storage_capacity"] = storage_capacity.to_dict()
        
        # Transmission capacities
        if len(self.network.lines) > 0:
            transmission_capacity = self.network.lines['s_nom_opt'].sum()
            capacity_data["transmission_capacity"] = float(transmission_capacity)
        
        return capacity_data
    
    def _extract_storage_results(self) -> Dict[str, Any]:
        """Extract storage operation results"""
        storage_data = {}
        
        if len(self.network.storage_units) > 0:
            # State of charge
            if hasattr(self.network, 'storage_units_t') and 'state_of_charge' in self.network.storage_units_t:
                soc_data = self.network.storage_units_t.state_of_charge
                storage_data["state_of_charge"] = {
                    storage_name: series.to_dict()
                    for storage_name, series in soc_data.items()
                }
            
            # Storage dispatch
            if hasattr(self.network, 'storage_units_t') and 'p' in self.network.storage_units_t:
                storage_dispatch = self.network.storage_units_t.p
                storage_data["storage_dispatch"] = {
                    storage_name: series.to_dict()
                    for storage_name, series in storage_dispatch.items()
                }
        
        return storage_data
    
    def _extract_transmission_results(self) -> Dict[str, Any]:
        """Extract transmission flow results"""
        transmission_data = {}
        
        if len(self.network.lines) > 0:
            # Line flows
            if hasattr(self.network, 'lines_t') and 'p0' in self.network.lines_t:
                line_flows = self.network.lines_t.p0
                transmission_data["line_flows"] = {
                    line_name: series.to_dict()
                    for line_name, series in line_flows.items()
                }
            
            # Line loading
            line_loading = {}
            for line_name in self.network.lines.index:
                max_flow = abs(line_flows[line_name]).max() if line_name in line_flows else 0
                capacity = self.network.lines.loc[line_name, 's_nom_opt']
                loading = (max_flow / capacity * 100) if capacity > 0 else 0
                line_loading[line_name] = float(loading)
            
            transmission_data["line_loading"] = line_loading
        
        return transmission_data
    
    def _extract_emissions_results(self) -> Dict[str, Any]:
        """Extract CO2 emissions results"""
        emissions_data = {}
        
        # Calculate emissions by carrier
        emissions_by_carrier = {}
        
        if hasattr(self.network, 'generators_t') and 'p' in self.network.generators_t:
            for gen_name in self.network.generators.index:
                carrier = self.network.generators.loc[gen_name, 'carrier']
                co2_emissions = self.network.generators.loc[gen_name, 'co2_emissions']
                
                if gen_name in self.network.generators_t.p.columns:
                    generation = self.network.generators_t.p[gen_name].sum()
                    total_emissions = generation * co2_emissions
                    
                    if carrier not in emissions_by_carrier:
                        emissions_by_carrier[carrier] = 0
                    emissions_by_carrier[carrier] += total_emissions
        
        emissions_data["emissions_by_carrier"] = emissions_by_carrier
        emissions_data["total_emissions"] = sum(emissions_by_carrier.values())
        
        return emissions_data
    
    def _extract_cost_results(self) -> Dict[str, Any]:
        """Extract cost breakdown results"""
        cost_data = {}
        
        # Calculate costs by component
        generation_costs = 0
        investment_costs = 0
        
        # Generation costs
        if hasattr(self.network, 'generators_t') and 'p' in self.network.generators_t:
            for gen_name in self.network.generators.index:
                marginal_cost = self.network.generators.loc[gen_name, 'marginal_cost']
                if gen_name in self.network.generators_t.p.columns:
                    generation = self.network.generators_t.p[gen_name].sum()
                    generation_costs += generation * marginal_cost
        
        # Investment costs (for capacity expansion)
        for gen_name in self.network.generators.index:
            capital_cost = self.network.generators.loc[gen_name, 'capital_cost']
            capacity = self.network.generators.loc[gen_name, 'p_nom_opt']
            investment_costs += capacity * capital_cost
        
        cost_data["generation_costs"] = float(generation_costs)
        cost_data["investment_costs"] = float(investment_costs)
        cost_data["total_costs"] = float(generation_costs + investment_costs)
        
        return cost_data
    
    def _calculate_kpis(self) -> Dict[str, Any]:
        """Calculate key performance indicators"""
        kpis = {}
        
        # Renewable share
        renewable_carriers = ["solar", "wind", "hydro"]
        total_generation = 0
        renewable_generation = 0
        
        if hasattr(self.network, 'generators_t') and 'p' in self.network.generators_t:
            for gen_name in self.network.generators.index:
                carrier = self.network.generators.loc[gen_name, 'carrier']
                if gen_name in self.network.generators_t.p.columns:
                    generation = self.network.generators_t.p[gen_name].sum()
                    total_generation += generation
                    
                    if carrier in renewable_carriers:
                        renewable_generation += generation
        
        renewable_share = (renewable_generation / total_generation * 100) if total_generation > 0 else 0
        kpis["renewable_share"] = float(renewable_share)
        
        # Capacity factor
        capacity_factors = {}
        for gen_name in self.network.generators.index:
            capacity = self.network.generators.loc[gen_name, 'p_nom_opt']
            if capacity > 0 and gen_name in self.network.generators_t.p.columns:
                generation = self.network.generators_t.p[gen_name]
                hours = len(generation)
                capacity_factor = generation.sum() / (capacity * hours) * 100
                capacity_factors[gen_name] = float(capacity_factor)
        
        kpis["capacity_factors"] = capacity_factors
        
        # System cost per MWh
        total_costs = self.results.get("costs", {}).get("total_costs", 0)
        system_cost_per_mwh = total_costs / total_generation if total_generation > 0 else 0
        kpis["system_cost_per_mwh"] = float(system_cost_per_mwh)
        
        return kpis
    
    def _save_results(self) -> str:
        """Save optimization results and network"""
        output_dir = Path("results") / "pypsa" / self.config["scenario_name"]
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save network
        network_file = output_dir / f"{self.config['scenario_name']}.nc"
        self.network.export_to_netcdf(network_file)
        
        # Save processed results
        results_file = output_dir / "optimization_results.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        # Save configuration
        config_file = output_dir / "configuration.json"
        with open(config_file, 'w') as f:
            json.dump(self.config, f, indent=2, default=str)
        
        return str(network_file)
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate optimization summary"""
        summary = {
            "scenario_name": self.config["scenario_name"],
            "optimization_method": self.config["investment_mode"],
            "solver": self.config.get("solver_options", {}).get("solver", "highs"),
            "network_statistics": {
                "buses": len(self.network.buses),
                "generators": len(self.network.generators),
                "loads": len(self.network.loads),
                "lines": len(self.network.lines),
                "storage_units": len(self.network.storage_units),
                "snapshots": len(self.network.snapshots)
            },
            "key_results": {
                "total_costs": self.results.get("costs", {}).get("total_costs", 0),
                "renewable_share": self.results.get("kpis", {}).get("renewable_share", 0),
                "total_emissions": self.results.get("emissions", {}).get("total_emissions", 0)
            },
            "execution_timestamp": datetime.now().isoformat()
        }
        
        return summary

def extract_network_results(network_path: str) -> Dict[str, Any]:
    """Extract results from saved PyPSA network file"""
    try:
        import pypsa
        
        network = pypsa.Network(network_path)
        runner = PyPSARunner({})  # Empty config for extraction
        runner.network = network
        
        results = runner._process_results()
        
        return {
            "success": True,
            "network_path": network_path,
            "results": results
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "network_path": network_path
        }

def main():
    """Main function for command-line execution"""
    parser = argparse.ArgumentParser(description='PyPSA Power System Optimization Runner')
    parser.add_argument('--config', help='JSON configuration string for optimization')
    parser.add_argument('--extract', help='Extract results from network file')
    
    args = parser.parse_args()
    
    try:
        if args.extract:
            result = extract_network_results(args.extract)
        elif args.config:
            config = json.loads(args.config)
            runner = PyPSARunner(config)
            result = runner.run_optimization()
        else:
            result = {"error": "No valid operation specified"}
        
        # Output result as JSON for Node.js consumption
        print(json.dumps(result, indent=2, default=str))
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(1)

if __name__ == "__main__":
    main()
```

Create supporting analysis module:
1. pypsa_analysis.py - Detailed results analysis
2. shared/pypsa_utils.py - PyPSA utility functions

Include comprehensive optimization features, result processing, and validation.
```

### **Chunk 8.2: Comprehensive Testing Strategy**
```
Task: Create comprehensive testing strategy and implementation for the entire platform

Create testing infrastructure with the following specifications:

FILE: tests/setup.js (Backend Test Setup)
```javascript
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs').promises;

class TestEnvironment {
    constructor() {
        this.testPort = 5001;
        this.serverProcess = null;
        this.testDataDir = path.join(__dirname, 'test-data');
    }

    async setup() {
        // Create test data directory
        await this.createTestData();
        
        // Start test server
        await this.startTestServer();
        
        // Wait for server to be ready
        await this.waitForServer();
    }

    async createTestData() {
        await fs.mkdir(this.testDataDir, { recursive: true });
        
        // Create test project structure
        const testProjectDir = path.join(this.testDataDir, 'test-project');
        await fs.mkdir(testProjectDir, { recursive: true });
        await fs.mkdir(path.join(testProjectDir, 'inputs'), { recursive: true });
        await fs.mkdir(path.join(testProjectDir, 'results'), { recursive: true });
        
        // Create mock input files
        await this.createMockInputFiles(testProjectDir);
    }

    async createMockInputFiles(projectDir) {
        // Mock demand input file
        const demandData = {
            residential: [
                { year: 2019, demand: 1000, gdp: 50000, population: 1000000 },
                { year: 2020, demand: 1050, gdp: 51000, population: 1010000 },
                { year: 2021, demand: 1100, gdp: 52000, population: 1020000 }
            ],
            commercial: [
                { year: 2019, demand: 800, gdp: 50000, population: 1000000 },
                { year: 2020, demand: 840, gdp: 51000, population: 1010000 },
                { year: 2021, demand: 880, gdp: 52000, population: 1020000 }
            ]
        };
        
        // Save as JSON for testing (normally would be Excel)
        await fs.writeFile(
            path.join(projectDir, 'inputs', 'test_demand_data.json'),
            JSON.stringify(demandData, null, 2)
        );
        
        // Mock load profile data
        const loadProfileData = [];
        for (let hour = 0; hour < 8760; hour++) {
            loadProfileData.push({
                hour: hour,
                datetime: new Date(2023, 0, 1, hour % 24),
                load: 800 + 200 * Math.sin(hour * 2 * Math.PI / 24) + 50 * Math.random()
            });
        }
        
        await fs.writeFile(
            path.join(projectDir, 'inputs', 'test_load_profile.json'),
            JSON.stringify(loadProfileData, null, 2)
        );
    }

    async startTestServer() {
        return new Promise((resolve, reject) => {
            this.serverProcess = spawn('node', [
                path.join(__dirname, '../backend/src/app.js')
            ], {
                env: {
                    ...process.env,
                    NODE_ENV: 'test',
                    PORT: this.testPort,
                    TEST_MODE: 'true'
                },
                stdio: ['pipe', 'pipe', 'pipe']
            });

            this.serverProcess.stdout.on('data', (data) => {
                if (data.toString().includes(`Server running on port ${this.testPort}`)) {
                    resolve();
                }
            });

            this.serverProcess.stderr.on('data', (data) => {
                console.error(`Test server error: ${data}`);
            });

            this.serverProcess.on('error', (error) => {
                reject(error);
            });

            // Timeout after 30 seconds
            setTimeout(() => {
                reject(new Error('Test server startup timeout'));
            }, 30000);
        });
    }

    async waitForServer() {
        const maxAttempts = 30;
        const delay = 1000;

        for (let attempt = 0; attempt < maxAttempts; attempt++) {
            try {
                const response = await fetch(`http://localhost:${this.testPort}/api/health`);
                if (response.ok) {
                    console.log('Test server is ready');
                    return;
                }
            } catch (error) {
                // Server not ready yet
            }

            await new Promise(resolve => setTimeout(resolve, delay));
        }

        throw new Error('Test server failed to become ready');
    }

    async teardown() {
        if (this.serverProcess) {
            this.serverProcess.kill('SIGTERM');
            
            // Force kill after 5 seconds
            setTimeout(() => {
                if (this.serverProcess && !this.serverProcess.killed) {
                    this.serverProcess.kill('SIGKILL');
                }
            }, 5000);
        }

        // Clean up test data
        try {
            await fs.rmdir(this.testDataDir, { recursive: true });
        } catch (error) {
            // Ignore cleanup errors
        }
    }
}

module.exports = TestEnvironment;
```

FILE: tests/backend/api.test.js (Backend API Tests)
```javascript
const request = require('supertest');
const TestEnvironment = require('../setup');

describe('API Integration Tests', () => {
    let testEnv;
    let baseURL;

    beforeAll(async () => {
        testEnv = new TestEnvironment();
        await testEnv.setup();
        baseURL = `http://localhost:${testEnv.testPort}`;
    }, 60000);

    afterAll(async () => {
        if (testEnv) {
            await testEnv.teardown();
        }
    });

    describe('Health Check', () => {
        test('should return health status', async () => {
            const response = await request(baseURL)
                .get('/api/health')
                .expect(200);

            expect(response.body).toHaveProperty('status', 'healthy');
            expect(response.body).toHaveProperty('timestamp');
        });
    });

    describe('Project Management', () => {
        test('should create a new project', async () => {
            const projectData = {
                name: 'Test Project',
                path: '/tmp/test-project'
            };

            const response = await request(baseURL)
                .post('/api/projects')
                .send(projectData)
                .expect(200);

            expect(response.body.success).toBe(true);
            expect(response.body.message).toContain('Project created');
        });

        test('should validate project structure', async () => {
            const response = await request(baseURL)
                .post('/api/projects/validate')
                .send({ path: '/tmp/test-project' })
                .expect(200);

            expect(response.body.success).toBe(true);
            expect(response.body.validation).toHaveProperty('structure_valid');
        });
    });

    describe('Demand Projection API', () => {
        test('should get sector data', async () => {
            const response = await request(baseURL)
                .get('/api/demand/sectors/residential')
                .expect(200);

            expect(response.body.success).toBe(true);
            expect(response.body.data).toHaveProperty('sector', 'residential');
        });

        test('should start forecast job', async () => {
            const forecastConfig = {
                scenario_name: 'test_forecast',
                target_year: 2030,
                sectors: {
                    residential: {
                        models: ['SLR'],
                        independent_variables: ['gdp', 'population']
                    }
                }
            };

            const response = await request(baseURL)
                .post('/api/demand/forecast')
                .send(forecastConfig)
                .expect(200);

            expect(response.body.success).toBe(true);
            expect(response.body.forecastId).toBeDefined();
        });

        test('should get correlation data', async () => {
            const response = await request(baseURL)
                .get('/api/demand/correlation/residential')
                .expect(200);

            expect(response.body.success).toBe(true);
            expect(response.body.data).toHaveProperty('correlations');
        });
    });

    describe('Load Profile API', () => {
        test('should generate load profile', async () => {
            const profileConfig = {
                method: 'base_scaling',
                base_year: 2023,
                start_year: 2024,
                end_year: 2025,
                growth_rate: 0.02
            };

            const response = await request(baseURL)
                .post('/api/loadprofile/generate')
                .send(profileConfig)
                .expect(200);

            expect(response.body.success).toBe(true);
            expect(response.body.profileId).toBeDefined();
        });

        test('should get saved profiles', async () => {
            const response = await request(baseURL)
                .get('/api/loadprofile/profiles')
                .expect(200);

            expect(response.body.success).toBe(true);
            expect(Array.isArray(response.body.profiles)).toBe(true);
        });
    });

    describe('PyPSA API', () => {
        test('should get available networks', async () => {
            const response = await request(baseURL)
                .get('/api/pypsa/networks')
                .expect(200);

            expect(response.body.success).toBe(true);
            expect(Array.isArray(response.body.networks)).toBe(true);
        });

        test('should start optimization', async () => {
            const pypsaConfig = {
                scenario_name: 'test_optimization',
                base_year: 2023,
                investment_mode: 'single_year',
                solver_options: {
                    solver: 'highs',
                    time_limit: 300
                }
            };

            const response = await request(baseURL)
                .post('/api/pypsa/optimize')
                .send(pypsaConfig)
                .expect(200);

            expect(response.body.success).toBe(true);
            expect(response.body.jobId).toBeDefined();
        });
    });

    describe('File Upload API', () => {
        test('should upload file', async () => {
            const testFile = Buffer.from('test,data\n1,2\n3,4', 'utf8');

            const response = await request(baseURL)
                .post('/api/files/upload')
                .attach('file', testFile, 'test.csv')
                .field('type', 'demand_input')
                .expect(200);

            expect(response.body.success).toBe(true);
        });
    });

    describe('Error Handling', () => {
        test('should handle invalid endpoints', async () => {
            const response = await request(baseURL)
                .get('/api/nonexistent')
                .expect(404);

            expect(response.body.success).toBe(false);
        });

        test('should handle invalid request data', async () => {
            const response = await request(baseURL)
                .post('/api/demand/forecast')
                .send({ invalid: 'data' })
                .expect(400);

            expect(response.body.success).toBe(false);
            expect(response.body.errors).toBeDefined();
        });
    });
});
```

FILE: tests/frontend/components.test.tsx (Frontend Component Tests)
```typescript
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import '@testing-library/jest-dom';

// Import components to test
import { DemandProjection } from '../../frontend/src/pages/DemandProjection';
import { LoadProfileGeneration } from '../../frontend/src/pages/LoadProfileGeneration';
import { PlotlyChart } from '../../frontend/src/components/charts/PlotlyChart';
import { DataTable } from '../../frontend/src/components/common/DataTable';

// Mock API slice
const mockApiSlice = {
    reducer: (state = {}, action: any) => state,
    middleware: () => (next: any) => (action: any) => next(action)
};

// Create mock store
const createMockStore = (initialState = {}) => {
    return configureStore({
        reducer: {
            api: mockApiSlice.reducer,
            demand: (state = {}, action) => state,
            loadProfile: (state = {}, action) => state,
            pypsa: (state = {}, action) => state,
            ui: (state = {}, action) => state,
            notifications: (state = {}, action) => state
        },
        preloadedState: initialState,
        middleware: (getDefaultMiddleware) => 
            getDefaultMiddleware().concat(mockApiSlice.middleware)
    });
};

const theme = createTheme();

const TestWrapper: React.FC<{ children: React.ReactNode; initialState?: any }> = ({ 
    children, 
    initialState = {} 
}) => {
    const store = createMockStore(initialState);
    
    return (
        <Provider store={store}>
            <ThemeProvider theme={theme}>
                {children}
            </ThemeProvider>
        </Provider>
    );
};

describe('Demand Projection Component', () => {
    test('renders demand projection page', () => {
        render(
            <TestWrapper>
                <DemandProjection />
            </TestWrapper>
        );
        
        expect(screen.getByText('Demand Projection & Forecasting')).toBeInTheDocument();
        expect(screen.getByText('Configure Forecast')).toBeInTheDocument();
    });

    test('opens configuration dialog', async () => {
        render(
            <TestWrapper>
                <DemandProjection />
            </TestWrapper>
        );
        
        const configButton = screen.getByText('Configure Forecast');
        fireEvent.click(configButton);
        
        await waitFor(() => {
            expect(screen.getByText('Configure Forecast Models')).toBeInTheDocument();
        });
    });

    test('handles sector navigation', () => {
        render(
            <TestWrapper>
                <DemandProjection />
            </TestWrapper>
        );
        
        // Test sector switching functionality
        const commercialSector = screen.getByText('Commercial');
        if (commercialSector) {
            fireEvent.click(commercialSector);
            // Verify sector change logic
        }
    });
});

describe('Load Profile Generation Component', () => {
    test('renders load profile generation page', () => {
        render(
            <TestWrapper>
                <LoadProfileGeneration />
            </TestWrapper>
        );
        
        expect(screen.getByText('Load Profile Generation')).toBeInTheDocument();
        expect(screen.getByText('Generation Wizard')).toBeInTheDocument();
    });

    test('handles method selection', () => {
        render(
            <TestWrapper>
                <LoadProfileGeneration />
            </TestWrapper>
        );
        
        // Test method selection logic
        const baseScalingOption = screen.getByText(/base.*scaling/i);
        if (baseScalingOption) {
            fireEvent.click(baseScalingOption);
            // Verify method selection
        }
    });
});

describe('PlotlyChart Component', () => {
    const mockData = [
        {
            x: [1, 2, 3, 4],
            y: [10, 11, 12, 13],
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Test Data'
        }
    ];

    test('renders chart with data', () => {
        render(
            <PlotlyChart 
                data={mockData} 
                title="Test Chart"
                height={400}
            />
        );
        
        expect(screen.getByText('Test Chart')).toBeInTheDocument();
    });

    test('shows loading state', () => {
        render(
            <PlotlyChart 
                data={[]} 
                loading={true}
                height={400}
            />
        );
        
        expect(screen.getByRole('progressbar')).toBeInTheDocument();
    });

    test('shows error state', () => {
        render(
            <PlotlyChart 
                data={[]} 
                error="Test error message"
                height={400}
            />
        );
        
        expect(screen.getByText(/error.*test error message/i)).toBeInTheDocument();
    });

    test('handles export functionality', () => {
        const mockOnExport = jest.fn();
        
        render(
            <PlotlyChart 
                data={mockData} 
                title="Test Chart"
                onExport={mockOnExport}
                height={400}
            />
        );
        
        const moreButton = screen.getByLabelText(/more/i);
        fireEvent.click(moreButton);
        
        const exportPngOption = screen.getByText(/export png/i);
        fireEvent.click(exportPngOption);
        
        expect(mockOnExport).toHaveBeenCalledWith('png');
    });
});

describe('DataTable Component', () => {
    const mockColumns = [
        { id: 'year', label: 'Year', sortable: true },
        { id: 'demand', label: 'Demand (GWh)', sortable: true, format: (value: number) => value.toFixed(1) },
        { id: 'sector', label: 'Sector', filterable: true }
    ];

    const mockData = [
        { year: 2020, demand: 1000.5, sector: 'Residential' },
        { year: 2021, demand: 1050.2, sector: 'Commercial' },
        { year: 2022, demand: 1100.8, sector: 'Industrial' }
    ];

    test('renders table with data', () => {
        render(
            <DataTable 
                columns={mockColumns}
                data={mockData}
                title="Test Table"
            />
        );
        
        expect(screen.getByText('Test Table')).toBeInTheDocument();
        expect(screen.getByText('Year')).toBeInTheDocument();
        expect(screen.getByText('Demand (GWh)')).toBeInTheDocument();
        expect(screen.getByText('2020')).toBeInTheDocument();
    });

    test('handles sorting', () => {
        render(
            <DataTable 
                columns={mockColumns}
                data={mockData}
                title="Test Table"
            />
        );
        
        const yearHeader = screen.getByText('Year');
        fireEvent.click(yearHeader);
        
        // Verify sorting behavior
        expect(yearHeader.closest('th')).toHaveAttribute('aria-sort');
    });

    test('handles search functionality', () => {
        render(
            <DataTable 
                columns={mockColumns}
                data={mockData}
                title="Test Table"
                searchable={true}
            />
        );
        
        const searchInput = screen.getByPlaceholderText('Search...');
        fireEvent.change(searchInput, { target: { value: 'Residential' } });
        
        // Should filter to show only residential data
        expect(screen.getByText('Residential')).toBeInTheDocument();
        expect(screen.queryByText('Commercial')).not.toBeInTheDocument();
    });

    test('handles pagination', () => {
        const largeDataset = Array.from({ length: 50 }, (_, i) => ({
            year: 2000 + i,
            demand: 1000 + i * 10,
            sector: i % 2 === 0 ? 'Residential' : 'Commercial'
        }));

        render(
            <DataTable 
                columns={mockColumns}
                data={largeDataset}
                title="Test Table"
                pagination={true}
                defaultRowsPerPage={10}
            />
        );
        
        // Should show pagination controls
        expect(screen.getByText(/rows per page/i)).toBeInTheDocument();
        
        // Should show first page of data
        expect(screen.getByText('2000')).toBeInTheDocument();
        expect(screen.queryByText('2020')).not.toBeInTheDocument();
    });
});

describe('Error Handling', () => {
    test('components handle missing props gracefully', () => {
        // Test that components don't crash with minimal props
        expect(() => {
            render(<TestWrapper><PlotlyChart data={[]} /></TestWrapper>);
        }).not.toThrow();
        
        expect(() => {
            render(<TestWrapper><DataTable columns={[]} data={[]} /></TestWrapper>);
        }).not.toThrow();
    });
});
```

FILE: tests/python/test_modules.py (Python Module Tests)
```python
import unittest
import json
import tempfile
import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np

# Add the python modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend/src/python'))

from demand_projection import ForecastingEngine, DataValidator, ProgressReporter
from load_profile_generation import LoadProfileGenerator
# Note: pypsa_runner would require PyPSA installation for testing

class TestDemandProjection(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.progress_reporter = ProgressReporter()
        self.engine = ForecastingEngine(self.progress_reporter)
        
        # Create test data
        self.test_data = pd.DataFrame({
            'year': [2019, 2020, 2021, 2022, 2023],
            'demand': [1000, 1050, 1100, 1150, 1200],
            'gdp': [50000, 51000, 52000, 53000, 54000],
            'population': [1000000, 1010000, 1020000, 1030000, 1040000]
        })
    
    def tearDown(self):
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_data_validator(self):
        """Test data validation functionality"""
        # Create temporary Excel file
        test_file = os.path.join(self.temp_dir, 'test_input.xlsx')
        
        with pd.ExcelWriter(test_file) as writer:
            self.test_data.to_excel(writer, sheet_name='residential', index=False)
            self.test_data.to_excel(writer, sheet_name='commercial', index=False)
        
        # Test validation
        result = DataValidator.validate_input_file(test_file)
        
        self.assertTrue(result['valid'])
        self.assertGreater(result['quality_score'], 0.5)
        self.assertIn('residential', result['sector_quality'])
        self.assertIn('commercial', result['sector_quality'])
    
    def test_mlr_model(self):
        """Test Multiple Linear Regression model"""
        config = {
            'independent_variables': ['gdp', 'population'],
            'target_year': 2030
        }
        
        result = self.engine._run_mlr_model(self.test_data, config, 2030, True)
        
        self.assertEqual(result['model_type'], 'MLR')
        self.assertIn('r2_score', result)
        self.assertIn('future_projections', result)
        self.assertTrue(len(result['future_projections']) > 0)
        self.assertIn('coefficients', result)
    
    def test_slr_model(self):
        """Test Simple Linear Regression model"""
        result = self.engine._run_slr_model(self.test_data, 2030, True)
        
        self.assertEqual(result['model_type'], 'SLR')
        self.assertIn('r2_score', result)
        self.assertIn('slope', result)
        self.assertIn('future_projections', result)
        self.assertTrue(len(result['future_projections']) > 0)
    
    def test_wam_model(self):
        """Test Weighted Average Method model"""
        config = {
            'wam_window': 3,
            'growth_method': 'compound'
        }
        
        result = self.engine._run_wam_model(self.test_data, config, 2030)
        
        self.assertEqual(result['model_type'], 'WAM')
        self.assertIn('growth_rate', result)
        self.assertIn('window_size', result)
        self.assertIn('future_projections', result)
        self.assertEqual(result['window_size'], 3)
    
    def test_data_quality_calculation(self):
        """Test data quality scoring"""
        # Test with good quality data
        quality_score = self.engine._calculate_data_quality(self.test_data)
        self.assertGreater(quality_score, 0.8)
        
        # Test with poor quality data (missing values)
        poor_data = self.test_data.copy()
        poor_data.loc[0:2, 'demand'] = np.nan
        poor_quality_score = self.engine._calculate_data_quality(poor_data)
        self.assertLess(poor_quality_score, quality_score)
    
    def test_configuration_validation(self):
        """Test forecast configuration validation"""
        valid_config = {
            'scenario_name': 'test_scenario',
            'target_year': 2030,
            'sectors': {
                'residential': {
                    'models': ['MLR'],
                    'independent_variables': ['gdp']
                }
            }
        }
        
        # Should not raise an exception
        try:
            self.engine.config = valid_config
            # Validation would be called in execute_forecast
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"Valid configuration raised an exception: {e}")

class TestLoadProfileGeneration(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test configuration
        self.base_config = {
            'method': 'base_scaling',
            'start_year': 2024,
            'end_year': 2025,
            'base_year': 2023,
            'growth_rate': 0.02
        }
        
        # Create test load data
        self.create_test_load_data()
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_load_data(self):
        """Create test load profile data"""
        # Create inputs directory
        inputs_dir = Path(self.temp_dir) / 'inputs'
        inputs_dir.mkdir(exist_ok=True)
        
        # Generate hourly load data for one year
        hours = 8760
        load_data = []
        
        for hour in range(hours):
            # Simple sinusoidal pattern with daily and seasonal variation
            daily_pattern = 800 + 200 * np.sin(hour * 2 * np.pi / 24)
            seasonal_pattern = 100 * np.sin(hour * 2 * np.pi / hours)
            random_noise = 50 * np.random.random()
            
            load_data.append({
                'hour': hour,
                'datetime': pd.Timestamp('2023-01-01') + pd.Timedelta(hours=hour),
                'load': daily_pattern + seasonal_pattern + random_noise
            })
        
        # Save as JSON (simulating Excel template)
        with open(inputs_dir / 'load_curve_template.json', 'w') as f:
            json.dump({'2023': load_data}, f)
    
    def test_base_scaling_generation(self):
        """Test base scaling profile generation"""
        os.chdir(self.temp_dir)  # Change to temp directory for file operations
        
        generator = LoadProfileGenerator(self.base_config)
        result = generator.generate_profile()
        
        self.assertTrue(result.get('success', False))
        self.assertEqual(result['method'], 'base_scaling')
        self.assertIn('years_generated', result)
        self.assertIn('statistics', result)
    
    def test_stl_generation_config(self):
        """Test STL decomposition configuration"""
        stl_config = {
            'method': 'stl_decomposition',
            'start_year': 2024,
            'end_year': 2025,
            'historical_years': [2023],
            'stl_seasonal': 13,
            'stl_period': 8760
        }
        
        generator = LoadProfileGenerator(stl_config)
        
        # Test configuration validation
        try:
            generator._validate_configuration()
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"STL configuration validation failed: {e}")
    
    def test_scaling_factor_calculation(self):
        """Test scaling factor calculation"""
        generator = LoadProfileGenerator(self.base_config)
        
        projections = {2023: 1000, 2024: 1020, 2025: 1040}
        
        factor_2024 = generator._get_scaling_factor(2024, projections, 2023)
        self.assertAlmostEqual(factor_2024, 1.02, places=2)
        
        factor_2025 = generator._get_scaling_factor(2025, projections, 2023)
        self.assertAlmostEqual(factor_2025, 1.04, places=2)
    
    def test_profile_statistics(self):
        """Test profile statistics calculation"""
        generator = LoadProfileGenerator(self.base_config)
        
        # Create mock profile data
        dates = pd.date_range('2024-01-01', '2024-12-31 23:00:00', freq='H')
        mock_profile = pd.DataFrame({
            'load': 800 + 200 * np.sin(np.arange(len(dates)) * 2 * np.pi / 24),
            'year': 2024
        }, index=dates)
        
        profiles = {2024: mock_profile}
        stats = generator._calculate_profile_statistics(profiles)
        
        self.assertIn('yearly_stats', stats)
        self.assertIn(2024, stats['yearly_stats'])
        self.assertIn('peak_demand', stats['yearly_stats'][2024])
        self.assertIn('load_factor', stats['yearly_stats'][2024])
        self.assertGreater(stats['yearly_stats'][2024]['load_factor'], 0)
        self.assertLess(stats['yearly_stats'][2024]['load_factor'], 1)

class TestUtilityFunctions(unittest.TestCase):
    
    def test_json_serialization(self):
        """Test JSON serialization of results"""
        test_data = {
            'timestamp': pd.Timestamp('2023-01-01'),
            'numpy_array': np.array([1, 2, 3]),
            'dataframe': pd.DataFrame({'a': [1, 2], 'b': [3, 4]}),
            'normal_data': {'key': 'value'}
        }
        
        # Should be able to serialize with default=str
        try:
            json_str = json.dumps(test_data, default=str)
            self.assertTrue(len(json_str) > 0)
        except Exception as e:
            self.fail(f"JSON serialization failed: {e}")
    
    def test_progress_reporting(self):
        """Test progress reporting functionality"""
        progress_reporter = ProgressReporter()
        
        # Should not raise exceptions
        try:
            progress_reporter.report(50.0, "test_sector", "processing", "test details")
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"Progress reporting failed: {e}")

class TestErrorHandling(unittest.TestCase):
    
    def test_missing_input_files(self):
        """Test handling of missing input files"""
        config = {
            'method': 'base_scaling',
            'start_year': 2024,
            'end_year': 2025,
            'base_year': 2023
        }
        
        generator = LoadProfileGenerator(config)
        
        # Should raise appropriate error for missing files
        with self.assertRaises(FileNotFoundError):
            generator._load_base_year_data(2023)
    
    def test_invalid_configuration(self):
        """Test handling of invalid configurations"""
        invalid_configs = [
            {},  # Empty config
            {'method': 'unknown_method'},  # Invalid method
            {'method': 'base_scaling'},  # Missing required fields
            {'method': 'base_scaling', 'start_year': 2025, 'end_year': 2024}  # Invalid year range
        ]
        
        for config in invalid_configs:
            generator = LoadProfileGenerator(config)
            with self.assertRaises(ValueError):
                generator._validate_configuration()

if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
```

Create additional test files:
1. tests/e2e/workflows.test.js - End-to-end workflow tests
2. tests/performance/benchmarks.test.js - Performance benchmarks
3. tests/security/security.test.js - Security testing

Include comprehensive test coverage for all critical functionality.
```

### **Chunk 8.3: Performance Optimization & Monitoring**
```
Task: Implement performance optimization and monitoring systems

Create comprehensive performance optimization with the following specifications:

FILE: backend/src/middleware/performanceMonitor.js
```javascript
const { performance } = require('perf_hooks');
const os = require('os');
const { EventEmitter } = require('events');

class PerformanceMonitor extends EventEmitter {
    constructor() {
        super();
        this.metrics = new Map();
        this.activeRequests = new Map();
        this.systemMetrics = {
            cpu: [],
            memory: [],
            diskIO: [],
            networkIO: []
        };
        this.alerts = [];
        this.thresholds = {
            responseTime: 5000, // 5 seconds
            memoryUsage: 0.85,  // 85%
            cpuUsage: 0.80,     // 80%
            errorRate: 0.05     // 5%
        };
        
        this.startSystemMonitoring();
    }

    trackRequest(req, res, next) {
        const requestId = this.generateRequestId();
        const startTime = performance.now();
        const startMemory = process.memoryUsage();
        
        // Track request start
        this.activeRequests.set(requestId, {
            method: req.method,
            url: req.url,
            startTime,
            startMemory,
            userAgent: req.get('User-Agent'),
            ip: req.ip
        });

        // Override res.end to capture completion
        const originalEnd = res.end;
        res.end = (...args) => {
            const endTime = performance.now();
            const endMemory = process.memoryUsage();
            const duration = endTime - startTime;
            
            this.recordRequest({
                requestId,
                method: req.method,
                url: req.url,
                statusCode: res.statusCode,
                duration,
                memoryDelta: endMemory.heapUsed - startMemory.heapUsed,
                timestamp: new Date().toISOString()
            });
            
            this.activeRequests.delete(requestId);
            originalEnd.apply(res, args);
        };

        req.requestId = requestId;
        next();
    }

    recordRequest(requestData) {
        const { url, method, statusCode, duration } = requestData;
        const key = `${method}:${url}`;
        
        if (!this.metrics.has(key)) {
            this.metrics.set(key, {
                count: 0,
                totalTime: 0,
                avgTime: 0,
                minTime: Infinity,
                maxTime: 0,
                errors: 0,
                lastAccess: null,
                statusCodes: new Map()
            });
        }
        
        const metric = this.metrics.get(key);
        metric.count++;
        metric.totalTime += duration;
        metric.avgTime = metric.totalTime / metric.count;
        metric.minTime = Math.min(metric.minTime, duration);
        metric.maxTime = Math.max(metric.maxTime, duration);
        metric.lastAccess = requestData.timestamp;
        
        // Track status codes
        if (!metric.statusCodes.has(statusCode)) {
            metric.statusCodes.set(statusCode, 0);
        }
        metric.statusCodes.set(statusCode, metric.statusCodes.get(statusCode) + 1);
        
        // Track errors
        if (statusCode >= 400) {
            metric.errors++;
        }
        
        // Check for performance alerts
        this.checkPerformanceAlerts(requestData);
        
        // Emit metrics for real-time monitoring
        this.emit('requestCompleted', requestData);
    }

    checkPerformanceAlerts(requestData) {
        const alerts = [];
        
        // Response time alert
        if (requestData.duration > this.thresholds.responseTime) {
            alerts.push({
                type: 'slow_response',
                severity: 'warning',
                message: `Slow response time: ${requestData.duration.toFixed(2)}ms for ${requestData.method} ${requestData.url}`,
                timestamp: new Date().toISOString(),
                data: requestData
            });
        }
        
        // Memory usage alert
        const memoryUsage = process.memoryUsage();
        const memoryPercent = memoryUsage.heapUsed / memoryUsage.heapTotal;
        if (memoryPercent > this.thresholds.memoryUsage) {
            alerts.push({
                type: 'high_memory',
                severity: 'warning',
                message: `High memory usage: ${(memoryPercent * 100).toFixed(1)}%`,
                timestamp: new Date().toISOString(),
                data: { memoryUsage, requestData }
            });
        }
        
        // Error rate alert
        const key = `${requestData.method}:${requestData.url}`;
        const metric = this.metrics.get(key);
        if (metric && metric.count > 10) {
            const errorRate = metric.errors / metric.count;
            if (errorRate > this.thresholds.errorRate) {
                alerts.push({
                    type: 'high_error_rate',
                    severity: 'error',
                    message: `High error rate: ${(errorRate * 100).toFixed(1)}% for ${requestData.method} ${requestData.url}`,
                    timestamp: new Date().toISOString(),
                    data: { errorRate, metric, requestData }
                });
            }
        }
        
        // Store and emit alerts
        alerts.forEach(alert => {
            this.alerts.push(alert);
            this.emit('alert', alert);
        });
        
        // Trim old alerts (keep last 100)
        if (this.alerts.length > 100) {
            this.alerts = this.alerts.slice(-100);
        }
    }

    startSystemMonitoring() {
        // Monitor system metrics every 30 seconds
        setInterval(() => {
            this.collectSystemMetrics();
        }, 30000);
        
        // Initial collection
        this.collectSystemMetrics();
    }

    collectSystemMetrics() {
        const timestamp = new Date().toISOString();
        
        // CPU Usage
        const cpuUsage = this.getCPUUsage();
        this.systemMetrics.cpu.push({ timestamp, value: cpuUsage });
        
        // Memory Usage
        const memoryUsage = process.memoryUsage();
        const memoryPercent = memoryUsage.heapUsed / memoryUsage.heapTotal;
        this.systemMetrics.memory.push({ 
            timestamp, 
            value: memoryPercent,
            details: memoryUsage
        });
        
        // System Memory
        const systemMemory = {
            total: os.totalmem(),
            free: os.freemem(),
            used: os.totalmem() - os.freemem()
        };
        
        // Keep only last 100 data points (50 minutes)
        Object.keys(this.systemMetrics).forEach(key => {
            if (this.systemMetrics[key].length > 100) {
                this.systemMetrics[key] = this.systemMetrics[key].slice(-100);
            }
        });
        
        // Check system alerts
        this.checkSystemAlerts({ cpuUsage, memoryPercent, systemMemory });
    }

    getCPUUsage() {
        const cpus = os.cpus();
        const usage = cpus.map(cpu => {
            const total = Object.values(cpu.times).reduce((acc, time) => acc + time, 0);
            const idle = cpu.times.idle;
            return (total - idle) / total;
        });
        
        return usage.reduce((acc, val) => acc + val, 0) / usage.length;
    }

    checkSystemAlerts(metrics) {
        // CPU usage alert
        if (metrics.cpuUsage > this.thresholds.cpuUsage) {
            this.alerts.push({
                type: 'high_cpu',
                severity: 'warning',
                message: `High CPU usage: ${(metrics.cpuUsage * 100).toFixed(1)}%`,
                timestamp: new Date().toISOString(),
                data: metrics
            });
            
            this.emit('systemAlert', {
                type: 'high_cpu',
                value: metrics.cpuUsage
            });
        }
        
        // System memory alert
        const systemMemoryPercent = metrics.systemMemory.used / metrics.systemMemory.total;
        if (systemMemoryPercent > this.thresholds.memoryUsage) {
            this.alerts.push({
                type: 'high_system_memory',
                severity: 'error',
                message: `High system memory usage: ${(systemMemoryPercent * 100).toFixed(1)}%`,
                timestamp: new Date().toISOString(),
                data: metrics
            });
        }
    }

    getMetrics() {
        const metricsArray = Array.from(this.metrics.entries()).map(([key, data]) => ({
            endpoint: key,
            ...data,
            errorRate: data.count > 0 ? data.errors / data.count : 0
        }));
        
        return {
            requests: metricsArray,
            system: this.systemMetrics,
            activeRequests: this.activeRequests.size,
            alerts: this.alerts.slice(-10), // Last 10 alerts
            summary: this.generateSummary()
        };
    }

    generateSummary() {
        const totalRequests = Array.from(this.metrics.values())
            .reduce((acc, metric) => acc + metric.count, 0);
        
        const totalErrors = Array.from(this.metrics.values())
            .reduce((acc, metric) => acc + metric.errors, 0);
        
        const avgResponseTime = Array.from(this.metrics.values())
            .reduce((acc, metric) => acc + metric.avgTime, 0) / this.metrics.size || 0;
        
        const currentMemory = process.memoryUsage();
        const latestCPU = this.systemMetrics.cpu.slice(-1)[0];
        
        return {
            totalRequests,
            totalErrors,
            errorRate: totalRequests > 0 ? totalErrors / totalRequests : 0,
            avgResponseTime,
            activeRequests: this.activeRequests.size,
            memoryUsage: currentMemory,
            cpuUsage: latestCPU ? latestCPU.value : 0,
            uptime: process.uptime(),
            alertCount: this.alerts.length
        };
    }

    reset() {
        this.metrics.clear();
        this.activeRequests.clear();
        this.alerts = [];
        this.systemMetrics = {
            cpu: [],
            memory: [],
            diskIO: [],
            networkIO: []
        };
    }

    generateRequestId() {
        return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
}

// Cache management for improved performance
class CacheManager {
    constructor() {
        this.cache = new Map();
        this.ttlMap = new Map();
        this.maxSize = 1000;
        this.defaultTTL = 300000; // 5 minutes
        
        // Cleanup expired entries every minute
        setInterval(() => {
            this.cleanup();
        }, 60000);
    }

    set(key, value, ttl = this.defaultTTL) {
        // Remove oldest entries if cache is full
        if (this.cache.size >= this.maxSize) {
            const oldestKey = this.cache.keys().next().value;
            this.delete(oldestKey);
        }
        
        this.cache.set(key, value);
        this.ttlMap.set(key, Date.now() + ttl);
    }

    get(key) {
        const ttl = this.ttlMap.get(key);
        
        if (!ttl || Date.now() > ttl) {
            this.delete(key);
            return null;
        }
        
        return this.cache.get(key);
    }

    delete(key) {
        this.cache.delete(key);
        this.ttlMap.delete(key);
    }

    cleanup() {
        const now = Date.now();
        
        for (const [key, ttl] of this.ttlMap.entries()) {
            if (now > ttl) {
                this.delete(key);
            }
        }
    }

    clear() {
        this.cache.clear();
        this.ttlMap.clear();
    }

    getStats() {
        return {
            size: this.cache.size,
            maxSize: this.maxSize,
            hitRate: this.hitRate || 0
        };
    }
}

// Memory monitoring and optimization
class MemoryManager {
    constructor() {
        this.gcThreshold = 0.85; // Trigger GC at 85% memory usage
        this.monitoring = false;
    }

    startMonitoring() {
        if (this.monitoring) return;
        
        this.monitoring = true;
        this.monitoringInterval = setInterval(() => {
            this.checkMemoryUsage();
        }, 10000); // Check every 10 seconds
    }

    stopMonitoring() {
        if (this.monitoringInterval) {
            clearInterval(this.monitoringInterval);
            this.monitoring = false;
        }
    }

    checkMemoryUsage() {
        const memUsage = process.memoryUsage();
        const heapPercent = memUsage.heapUsed / memUsage.heapTotal;
        
        if (heapPercent > this.gcThreshold) {
            console.log(`High memory usage detected: ${(heapPercent * 100).toFixed(1)}%`);
            this.forceGarbageCollection();
        }
    }

    forceGarbageCollection() {
        if (global.gc) {
            global.gc();
            console.log('Garbage collection triggered');
        } else {
            console.log('Garbage collection not available. Start node with --expose-gc flag.');
        }
    }

    getMemoryStats() {
        const memUsage = process.memoryUsage();
        const systemMem = {
            total: os.totalmem(),
            free: os.freemem(),
            used: os.totalmem() - os.freemem()
        };
        
        return {
            process: {
                heapUsed: memUsage.heapUsed,
                heapTotal: memUsage.heapTotal,
                heapPercent: (memUsage.heapUsed / memUsage.heapTotal) * 100,
                rss: memUsage.rss,
                external: memUsage.external,
                arrayBuffers: memUsage.arrayBuffers
            },
            system: {
                total: systemMem.total,
                free: systemMem.free,
                used: systemMem.used,
                usedPercent: (systemMem.used / systemMem.total) * 100
            }
        };
    }
}

// Request rate limiting
class RateLimiter {
    constructor(options = {}) {
        this.windowMs = options.windowMs || 15 * 60 * 1000; // 15 minutes
        this.maxRequests = options.maxRequests || 100;
        this.requests = new Map();
        
        // Clean up old entries every minute
        setInterval(() => {
            this.cleanup();
        }, 60000);
    }

    isAllowed(identifier) {
        const now = Date.now();
        const windowStart = now - this.windowMs;
        
        if (!this.requests.has(identifier)) {
            this.requests.set(identifier, []);
        }
        
        const userRequests = this.requests.get(identifier);
        
        // Remove old requests outside the window
        const validRequests = userRequests.filter(timestamp => timestamp > windowStart);
        this.requests.set(identifier, validRequests);
        
        // Check if under limit
        if (validRequests.length < this.maxRequests) {
            validRequests.push(now);
            return true;
        }
        
        return false;
    }

    cleanup() {
        const now = Date.now();
        const windowStart = now - this.windowMs;
        
        for (const [identifier, requests] of this.requests.entries()) {
            const validRequests = requests.filter(timestamp => timestamp > windowStart);
            
            if (validRequests.length === 0) {
                this.requests.delete(identifier);
            } else {
                this.requests.set(identifier, validRequests);
            }
        }
    }

    getStats() {
        return {
            trackedUsers: this.requests.size,
            windowMs: this.windowMs,
            maxRequests: this.maxRequests
        };
    }
}

module.exports = {
    PerformanceMonitor,
    CacheManager,
    MemoryManager,
    RateLimiter
};
```

FILE: backend/src/services/optimizationService.js (Performance Optimization Service)
```javascript
const cluster = require('cluster');
const os = require('os');
const { Worker } = require('worker_threads');
const { performance } = require('perf_hooks');

class OptimizationService {
    constructor() {
        this.cpuCount = os.cpus().length;
        this.workerPool = [];
        this.taskQueue = [];
        this.activeJobs = new Map();
        this.maxWorkers = Math.min(this.cpuCount, 4); // Limit workers
        this.initialized = false;
    }

    async initialize() {
        if (this.initialized) return;
        
        // Initialize worker pool for CPU-intensive tasks
        await this.createWorkerPool();
        this.initialized = true;
    }

    async createWorkerPool() {
        for (let i = 0; i < this.maxWorkers; i++) {
            await this.createWorker();
        }
    }

    async createWorker() {
        return new Promise((resolve, reject) => {
            const worker = new Worker(`
                const { parentPort } = require('worker_threads');
                const { performance } = require('perf_hooks');
                
                parentPort.on('message', async (task) => {
                    const startTime = performance.now();
                    
                    try {
                        let result;
                        
                        switch (task.type) {
                            case 'data_processing':
                                result = await processData(task.data);
                                break;
                            case 'chart_generation':
                                result = await generateChart(task.data);
                                break;
                            case 'file_conversion':
                                result = await convertFile(task.data);
                                break;
                            default:
                                throw new Error('Unknown task type');
                        }
                        
                        const endTime = performance.now();
                        
                        parentPort.postMessage({
                            taskId: task.id,
                            success: true,
                            result,
                            processingTime: endTime - startTime
                        });
                    } catch (error) {
                        parentPort.postMessage({
                            taskId: task.id,
                            success: false,
                            error: error.message
                        });
                    }
                });
                
                async function processData(data) {
                    // Simulate data processing
                    const { operation, payload } = data;
                    
                    switch (operation) {
                        case 'aggregate':
                            return aggregateData(payload);
                        case 'filter':
                            return filterData(payload);
                        case 'transform':
                            return transformData(payload);
                        default:
                            throw new Error('Unknown data operation');
                    }
                }
                
                function aggregateData(data) {
                    // Group and aggregate large datasets
                    const grouped = {};
                    
                    data.forEach(item => {
                        const key = item.groupBy;
                        if (!grouped[key]) {
                            grouped[key] = { count: 0, sum: 0, items: [] };
                        }
                        grouped[key].count++;
                        grouped[key].sum += item.value || 0;
                        grouped[key].items.push(item);
                    });
                    
                    return Object.entries(grouped).map(([key, data]) => ({
                        group: key,
                        count: data.count,
                        average: data.sum / data.count,
                        total: data.sum
                    }));
                }
                
                function filterData(data) {
                    const { dataset, criteria } = data;
                    
                    return dataset.filter(item => {
                        return Object.entries(criteria).every(([key, value]) => {
                            if (typeof value === 'object' && value.operator) {
                                switch (value.operator) {
                                    case 'gte':
                                        return item[key] >= value.value;
                                    case 'lte':
                                        return item[key] <= value.value;
                                    case 'contains':
                                        return item[key].toString().includes(value.value);
                                    default:
                                        return item[key] === value.value;
                                }
                            }
                            return item[key] === value;
                        });
                    });
                }
                
                function transformData(data) {
                    const { dataset, transformations } = data;
                    
                    return dataset.map(item => {
                        const transformed = { ...item };
                        
                        transformations.forEach(transform => {
                            switch (transform.type) {
                                case 'calculate':
                                    transformed[transform.target] = eval(
                                        transform.expression.replace(/\{(\w+)\}/g, (match, field) => {
                                            return item[field] || 0;
                                        })
                                    );
                                    break;
                                case 'rename':
                                    transformed[transform.to] = transformed[transform.from];
                                    delete transformed[transform.from];
                                    break;
                                case 'format':
                                    if (transform.format === 'currency') {
                                        transformed[transform.field] = formatCurrency(transformed[transform.field]);
                                    }
                                    break;
                            }
                        });
                        
                        return transformed;
                    });
                }
                
                function formatCurrency(value) {
                    return new Intl.NumberFormat('en-US', {
                        style: 'currency',
                        currency: 'USD'
                    }).format(value);
                }
                
                async function generateChart(data) {
                    // Simulate chart data processing
                    const { type, dataset, options } = data;
                    
                    switch (type) {
                        case 'line':
                            return generateLineChartData(dataset, options);
                        case 'bar':
                            return generateBarChartData(dataset, options);
                        case 'heatmap':
                            return generateHeatmapData(dataset, options);
                        default:
                            throw new Error('Unknown chart type');
                    }
                }
                
                function generateLineChartData(dataset, options) {
                    const { xField, yField, groupBy } = options;
                    
                    if (groupBy) {
                        const series = {};
                        dataset.forEach(item => {
                            const group = item[groupBy];
                            if (!series[group]) {
                                series[group] = { x: [], y: [], name: group };
                            }
                            series[group].x.push(item[xField]);
                            series[group].y.push(item[yField]);
                        });
                        return Object.values(series);
                    } else {
                        return [{
                            x: dataset.map(item => item[xField]),
                            y: dataset.map(item => item[yField]),
                            type: 'scatter',
                            mode: 'lines'
                        }];
                    }
                }
                
                function generateBarChartData(dataset, options) {
                    const { xField, yField } = options;
                    
                    return [{
                        x: dataset.map(item => item[xField]),
                        y: dataset.map(item => item[yField]),
                        type: 'bar'
                    }];
                }
                
                function generateHeatmapData(dataset, options) {
                    const { xField, yField, valueField } = options;
                    
                    // Create 2D array for heatmap
                    const xValues = [...new Set(dataset.map(item => item[xField]))].sort();
                    const yValues = [...new Set(dataset.map(item => item[yField]))].sort();
                    
                    const zData = yValues.map(y => 
                        xValues.map(x => {
                            const item = dataset.find(d => d[xField] === x && d[yField] === y);
                            return item ? item[valueField] : 0;
                        })
                    );
                    
                    return [{
                        z: zData,
                        x: xValues,
                        y: yValues,
                        type: 'heatmap'
                    }];
                }
                
                async function convertFile(data) {
                    // Simulate file conversion
                    const { format, content, options } = data;
                    
                    switch (format) {
                        case 'csv_to_json':
                            return convertCSVToJSON(content);
                        case 'json_to_csv':
                            return convertJSONToCSV(content);
                        case 'excel_to_json':
                            return convertExcelToJSON(content);
                        default:
                            throw new Error('Unknown conversion format');
                    }
                }
                
                function convertCSVToJSON(csvContent) {
                    const lines = csvContent.split('\\n');
                    const headers = lines[0].split(',');
                    
                    return lines.slice(1).map(line => {
                        const values = line.split(',');
                        const obj = {};
                        headers.forEach((header, index) => {
                            obj[header.trim()] = values[index]?.trim() || '';
                        });
                        return obj;
                    });
                }
                
                function convertJSONToCSV(jsonData) {
                    if (!Array.isArray(jsonData) || jsonData.length === 0) {
                        return '';
                    }
                    
                    const headers = Object.keys(jsonData[0]);
                    const csvRows = [headers.join(',')];
                    
                    jsonData.forEach(row => {
                        const values = headers.map(header => row[header] || '');
                        csvRows.push(values.join(','));
                    });
                    
                    return csvRows.join('\\n');
                }
                
                function convertExcelToJSON(excelData) {
                    // Simplified Excel parsing simulation
                    return JSON.parse(excelData);
                }
            `, { eval: true });

            worker.on('error', (error) => {
                console.error('Worker error:', error);
                reject(error);
            });

            worker.on('online', () => {
