const pythonManager = require('../services/pythonProcessManager');
const { validatePyPSAConfig } = require('../middleware/validation'); // Will update validation.js
const { fileService } = require('../services/fileService');
const { cacheGet, cacheSet } = require('../services/cacheService');
const { logger } = require('../utils/logger');
const path = require('path');
const fs = require('fs').promises;

const RESULTS_BASE_DIR = process.env.RESULTS_DIR || path.join(process.cwd(), 'results');
const PYPSA_RESULTS_DIR = path.join(RESULTS_BASE_DIR, 'pypsa');

class PyPSAController {
    constructor() {
        this.activeOptimizationJobs = new Map(); // Stores active PyPSA optimization jobs
        this.availableNetworks = new Map(); // In-memory cache of { scenario_name: network_file_path }
        this.resultsCache = new Map(); // In-memory cache for extracted results from network files

        this._ensureResultsDirExists();
        // this.scanForNetworkFiles().catch(err => logger.error("Error auto-scanning PyPSA networks on startup:", err));
    }

    async _ensureResultsDirExists() {
        try {
            await fs.mkdir(PYPSA_RESULTS_DIR, { recursive: true });
            logger.info(`PyPSA results directory ensured at: ${PYPSA_RESULTS_DIR}`);
        } catch (error) {
            logger.error(`Failed to create PyPSA results directory at ${PYPSA_RESULTS_DIR}:`, error);
        }
    }

    async runOptimization(req, res, next) {
        try {
            const config = req.body;

            const validationResult = validatePyPSAConfig(config); // To be implemented in validation.js
            if (!validationResult.isValid) {
                logger.warn(`PyPSA configuration validation failed. Errors: ${validationResult.errors.join(', ')}`);
                return res.status(400).json({
                    success: false,
                    message: 'Invalid PyPSA configuration.',
                    errors: validationResult.errors
                });
            }

            const jobId = `pypsa_job_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`;
            const io = req.app.get('io');

            logger.info(`Starting new PyPSA optimization job [${jobId}] with config: ${JSON.stringify(config)}`);
            this.activeOptimizationJobs.set(jobId, {
                id: jobId,
                status: 'queued',
                progress: 0,
                startTime: new Date().toISOString(),
                config: config,
                result: null, // Will store { network_path, summary, objective_value etc. }
                error: null
            });

            io.emit('pypsa-job-status', { jobId, status: 'queued', progress: 0 });

            this.executeOptimizationWithProgress(jobId, config, io)
                .then(pythonResult => { // pythonResult includes { network_path, scenario_name, objective_value, etc. }
                    logger.info(`PyPSA optimization job [${jobId}] (Scenario: ${pythonResult.scenario_name}) completed successfully.`);
                    const job = this.activeOptimizationJobs.get(jobId);
                    if (job) {
                        job.status = 'completed';
                        job.progress = 100;
                        job.result = pythonResult;
                        job.completedTime = new Date().toISOString();
                        this.activeOptimizationJobs.set(jobId, job);

                        if (pythonResult.network_path && pythonResult.scenario_name) {
                            this.availableNetworks.set(pythonResult.scenario_name, pythonResult.network_path);
                            logger.info(`Network ${pythonResult.scenario_name} available at ${pythonResult.network_path}`);
                        }

                        io.emit('pypsa-completed', { jobId, result: pythonResult });
                        io.emit('pypsa-job-status', { jobId, status: 'completed', progress: 100, result: pythonResult });
                    }
                })
                .catch(error => {
                    logger.error(`PyPSA optimization job [${jobId}] failed: ${error.message}`);
                    const job = this.activeOptimizationJobs.get(jobId);
                    if (job) {
                        job.status = 'failed';
                        job.error = error.message;
                        job.failedTime = new Date().toISOString();
                        this.activeOptimizationJobs.set(jobId, job);
                        io.emit('pypsa-error', { jobId, error: error.message });
                        io.emit('pypsa-job-status', { jobId, status: 'failed', error: error.message });
                    }
                });

            res.status(202).json({
                success: true,
                jobId: jobId,
                message: 'PyPSA optimization job started successfully.'
            });
        } catch (error) {
            logger.error(`Error in runOptimization: ${error.message}`);
            next(error);
        }
    }

    async executeOptimizationWithProgress(jobId, config, io) {
        const job = this.activeOptimizationJobs.get(jobId);
        if(job) {
            job.status = 'running';
            this.activeOptimizationJobs.set(jobId, job);
            io.emit('pypsa-job-status', { jobId, status: 'running', progress: job.progress });
        }

        const onProgress = (progressData) => {
            const currentJob = this.activeOptimizationJobs.get(jobId);
            if (currentJob) {
                currentJob.progress = progressData.progress || currentJob.progress;
                currentJob.currentStep = progressData.step || currentJob.currentStep; // 'step' from python
                currentJob.statusDetails = progressData.status || currentJob.statusDetails; // 'status' from python is detail
                this.activeOptimizationJobs.set(jobId, currentJob);

                io.emit('pypsa-progress', { // For detailed progress UI
                    jobId, // Main job ID
                    pythonJobId: progressData.job_id, // ID from python script, if any
                    progress: currentJob.progress,
                    step: currentJob.currentStep,
                    status: currentJob.statusDetails
                });
                 io.emit('pypsa-job-status', { // For general job status
                    jobId,
                    status: 'running', // Main job status
                    progress: currentJob.progress,
                    details: currentJob.statusDetails
                });
            }
        };

        return pythonManager.executePythonScript(
            'pypsa_runner.py', // Main PyPSA script
            ['--config', JSON.stringify(config)],
            {
                timeout: config.timeout || 1800000, // 30 minute default timeout
                onProgress
            }
        );
    }

    async getOptimizationStatus(req, res, next) {
        try {
            const { jobId } = req.params;
            const job = this.activeOptimizationJobs.get(jobId);

            if (!job) {
                return res.status(404).json({ success: false, message: 'Optimization job not found.' });
            }
            res.json({ success: true, job });
        } catch (error) {
            logger.error(`Error in getOptimizationStatus for job ID ${req.params.jobId}: ${error.message}`);
            next(error);
        }
    }

    async getAvailableNetworks(req, res, next) {
        try {
            if (this.availableNetworks.size === 0 || req.query.refresh === 'true') {
                await this.scanForNetworkFiles();
            }

            const networksList = [];
            for (const [name, networkPath] of this.availableNetworks.entries()) {
                try {
                    const stats = await fs.stat(networkPath);
                    networksList.push({
                        scenario_name: name,
                        network_path: networkPath, // This path is internal to the server
                        file_size: stats.size,
                        created_time: stats.birthtime || stats.ctime // birthtime might not be available on all systems
                    });
                } catch (statError) {
                    logger.warn(`Could not stat network file ${networkPath} for scenario ${name}: ${statError.message}`);
                    // Optionally remove it from availableNetworks if file is gone
                    // this.availableNetworks.delete(name);
                }
            }
            res.json({ success: true, networks: networksList });
        } catch (error) {
            logger.error('Error in getAvailableNetworks:', error);
            next(error);
        }
    }

    async extractNetworkResults(req, res, next) {
        try {
            const { networkPath, scenarioName } = req.body; // scenarioName can be used as part of cache key
            if (!networkPath && !scenarioName) {
                 return res.status(400).json({ success: false, message: 'Either networkPath or scenarioName is required.' });
            }

            let actualNetworkPath = networkPath;
            if (!actualNetworkPath && scenarioName) {
                actualNetworkPath = this.availableNetworks.get(scenarioName);
                if (!actualNetworkPath) {
                    await this.scanForNetworkFiles(); // Try a refresh
                    actualNetworkPath = this.availableNetworks.get(scenarioName);
                }
            }
            if (!actualNetworkPath) {
                 return res.status(404).json({ success: false, message: `Network for scenario '${scenarioName || networkPath}' not found.` });
            }


            const cacheKey = `pypsa_results_${path.basename(actualNetworkPath, '.nc')}`;

            let results = await cacheGet(cacheKey);
            if (results) {
                logger.info(`Cache hit for PyPSA results: ${cacheKey}`);
                return res.json({ success: true, results: results, source: 'cache' });
            }

            logger.info(`Cache miss for PyPSA results: ${cacheKey}. Extracting from ${actualNetworkPath}.`);
            results = await pythonManager.executePythonScript(
                'pypsa_runner.py', // Main PyPSA script
                ['--extract', actualNetworkPath] // Argument to trigger extraction
            );

            if (results) {
                // Cache results for 30 minutes
                await cacheSet(cacheKey, results, 1800);
                logger.info(`PyPSA results for ${actualNetworkPath} extracted and cached.`);
            }

            res.json({ success: true, results: results, source: 'script' });
        } catch (error) {
            logger.error(`Error in extractNetworkResults: ${error.message}`);
            next(error);
        }
    }

    // Generic method to call PyPSA analysis script
    async _getAnalysisData(analysisType, req, res, next) {
        try {
            const { networkPath: encodedNetworkPath } = req.params; // Network path is part of URL
            const networkPath = decodeURIComponent(encodedNetworkPath);
            const queryParams = req.query; // { startDate, endDate, resolution, metrics etc. }

            if (!this.availableNetworks.has(path.basename(networkPath, '.nc')) && !(await fs.access(networkPath).then(()=>true).catch(()=>false))) {
                 // Check if the path is one of the known networks or if it's an absolute path that exists
                 // This is a basic check; more robust validation might be needed if direct paths are allowed.
                 // For now, we assume networkPath is a key or a direct valid path.
                 // A better approach for direct paths would be to validate it's within a permitted directory.
                 // For simplicity, let's assume networkPath refers to a scenario name for now if not a full path
                let foundPath = this.availableNetworks.get(networkPath);
                if (!foundPath) {
                    await this.scanForNetworkFiles();
                    foundPath = this.availableNetworks.get(networkPath);
                }
                if(!foundPath) {
                    return res.status(404).json({ success: false, message: `Network '${networkPath}' not found or not registered.` });
                }
                 // If networkPath was a scenario name, use the actual path
                 // This part of logic needs refinement based on how networkPath is passed (name vs actual path)
            }


            const pythonArgs = [
                '--network', networkPath, // Actual path to .nc file
                '--analysis', analysisType
            ];

            if (queryParams.startDate) pythonArgs.push('--start-date', queryParams.startDate);
            if (queryParams.endDate) pythonArgs.push('--end-date', queryParams.endDate);
            if (queryParams.resolution) pythonArgs.push('--resolution', queryParams.resolution);
            if (queryParams.metrics && analysisType === 'compare') pythonArgs.push('--metrics', JSON.stringify(queryParams.metrics));
            // For compare, networkPath might be a list of paths or IDs; adjust pypsa_analysis.py accordingly
            if (analysisType === 'compare' && queryParams.networkPaths) { // Assuming networkPaths is an array for compare
                pythonArgs[1] = JSON.stringify(queryParams.networkPaths); // Override networkPath with list for compare
            }


            const result = await pythonManager.executePythonScript('pypsa_analysis.py', pythonArgs);
            res.json({ success: true, data: result });

        } catch (error) {
            logger.error(`Error in get ${analysisType} Data for network ${req.params.networkPath}: ${error.message}`);
            next(error);
        }
    }

    // Specific analysis endpoints
    getDispatchData(req, res, next) { this._getAnalysisData('dispatch', req, res, next); }
    getCapacityData(req, res, next) { this._getAnalysisData('capacity', req, res, next); }
    getStorageData(req, res, next) { this._getAnalysisData('storage', req, res, next); }
    getEmissionsData(req, res, next) { this._getAnalysisData('emissions', req, res, next); }
    getNetworkInfo(req, res, next) { this._getAnalysisData('info', req, res, next); }

    async compareNetworks(req, res, next) {
        try {
            const { networkPaths, metrics } = req.body; // networkPaths is an array of scenario names or direct paths

            if (!Array.isArray(networkPaths) || networkPaths.length < 2) {
                return res.status(400).json({ success: false, message: 'At least 2 network paths/scenarios are required for comparison.' });
            }

            const resolvedNetworkPaths = [];
            for (const np of networkPaths) {
                let actualPath = this.availableNetworks.get(np); // Try as scenario name first
                if (!actualPath) {
                    // If not a known scenario name, assume it might be a direct path (needs validation)
                    // For now, we'll just use it as is if it's not in availableNetworks.
                    // A robust solution would check if 'np' is a valid file path within allowed directories.
                     if (await fs.access(np).then(()=>true).catch(()=>false)) {
                        actualPath = np;
                    } else {
                         return res.status(404).json({ success: false, message: `Network '${np}' not found.` });
                    }
                }
                resolvedNetworkPaths.push(actualPath);
            }

            const pythonArgs = [
                '--compare-paths', JSON.stringify(resolvedNetworkPaths), // Pass actual file paths
            ];
            if (metrics && Array.isArray(metrics) && metrics.length > 0) {
                pythonArgs.push('--metrics', JSON.stringify(metrics));
            } else {
                 pythonArgs.push('--metrics', JSON.stringify(['cost', 'emissions', 'renewable_share'])); // Default metrics
            }

            const result = await pythonManager.executePythonScript('pypsa_analysis.py', pythonArgs);
            res.json({ success: true, comparison: result });

        } catch (error) {
            logger.error(`Error in compareNetworks: ${error.message}`);
            next(error);
        }
    }


    async cancelOptimization(req, res, next) {
        try {
            const { jobId } = req.params;
            const job = this.activeOptimizationJobs.get(jobId);

            if (!job) {
                return res.status(404).json({ success: false, message: 'Optimization job not found.' });
            }

            if (job.status === 'running' || job.status === 'queued') {
                // pythonManager.cancelProcess might need the specific PID or a way to map jobId to its internal process ID
                const cancelled = pythonManager.cancelProcess(jobId); // This assumes jobId is known to pythonManager or mapped
                if (cancelled) {
                    job.status = 'cancelled';
                    job.cancelledTime = new Date().toISOString();
                    this.activeOptimizationJobs.set(jobId, job);

                    const io = req.app.get('io');
                    io.emit('pypsa-cancelled', { jobId });
                    io.emit('pypsa-job-status', { jobId, status: 'cancelled' });

                    logger.info(`PyPSA job [${jobId}] cancelled successfully.`);
                    return res.json({ success: true, message: 'Optimization job cancelled successfully.' });
                } else {
                     logger.warn(`Could not cancel Python process for PyPSA job [${jobId}].`);
                    return res.status(500).json({ success: false, message: 'Could not cancel the PyPSA process.' });
                }
            } else {
                return res.status(400).json({ success: false, message: `Job is already ${job.status}.` });
            }
        } catch (error) {
            logger.error(`Error in cancelOptimization for job ID ${req.params.jobId}: ${error.message}`);
            next(error);
        }
    }

    async scanForNetworkFiles() {
        logger.info(`Scanning for PyPSA network files in ${PYPSA_RESULTS_DIR}`);
        try {
            const scenarioDirs = await fs.readdir(PYPSA_RESULTS_DIR, { withFileTypes: true });
            let foundCount = 0;
            for (const dirent of scenarioDirs) {
                if (dirent.isDirectory()) {
                    const scenarioName = dirent.name;
                    const networkFilePath = path.join(PYPSA_RESULTS_DIR, scenarioName, `${scenarioName}.nc`);
                    try {
                        await fs.access(networkFilePath); // Check if the .nc file exists
                        this.availableNetworks.set(scenarioName, networkFilePath);
                        logger.debug(`Found network for scenario: ${scenarioName} at ${networkFilePath}`);
                        foundCount++;
                    } catch (e) {
                        // .nc file not found in this directory, skip
                        logger.debug(`No .nc file found for scenario ${scenarioName} in its directory.`);
                    }
                }
            }
             logger.info(`Scan complete. Found ${foundCount} PyPSA networks.`);
        } catch (error) {
            if (error.code === 'ENOENT') {
                logger.info('PyPSA results directory does not exist. No networks loaded.');
            } else {
                logger.error('Failed to scan PyPSA results directory:', error);
            }
        }
    }
}

module.exports = new PyPSAController();
