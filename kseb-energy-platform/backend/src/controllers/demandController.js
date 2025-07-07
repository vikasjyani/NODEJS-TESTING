const pythonManager = require('../services/pythonProcessManager');
const { validateForecastConfig } = require('../middleware/validation'); // Will be created
const { cacheGet, cacheSet } = require('../services/cacheService'); // Will be created
const { logger } = require('../utils/logger');

class DemandController {
    constructor() {
        // Stores active forecast jobs. Key: forecastId, Value: job details
        this.activeForecastJobs = new Map();
    }

    async getSectorData(req, res, next) {
        try {
            const { sector } = req.params;
            if (!sector) {
                return res.status(400).json({ success: false, message: 'Sector parameter is required.' });
            }
            const cacheKey = `demand_data_${sector}`;

            // Check cache first
            let data = await cacheGet(cacheKey);
            if (data) {
                logger.info(`Cache hit for sector data: ${sector}`);
                return res.json({ success: true, data: data, source: 'cache' });
            }

            logger.info(`Cache miss for sector data: ${sector}. Fetching from Python script.`);
            // If not in cache, execute Python script
            // Assuming 'demand_projection.py' is the main script handling various actions based on args
            data = await pythonManager.executePythonScript(
                'demand_projection.py', // Main script
                ['--sector-data', sector] // Arguments to specify action and sector
            );

            if (data) {
                await cacheSet(cacheKey, data, 300); // Cache for 5 minutes (300 seconds)
                logger.info(`Sector data for ${sector} fetched and cached.`);
            }

            res.json({
                success: true,
                data: data,
                source: 'script'
            });
        } catch (error) {
            logger.error(`Error in getSectorData for sector ${req.params.sector}: ${error.message}`);
            next(error); // Pass error to the centralized error handler
        }
    }

    async runForecast(req, res, next) {
        try {
            const config = req.body;

            // Validate configuration
            const validationResult = validateForecastConfig(config); // This function needs to be implemented
            if (!validationResult.isValid) {
                logger.warn(`Forecast configuration validation failed for: ${JSON.stringify(config)} Errors: ${validationResult.errors.join(', ')}`);
                return res.status(400).json({
                    success: false,
                    message: 'Invalid forecast configuration.',
                    errors: validationResult.errors
                });
            }

            const forecastId = `forecast_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`;
            const io = req.app.get('io'); // Get Socket.IO instance from app

            logger.info(`Starting new forecast [${forecastId}] with config: ${JSON.stringify(config)}`);
            this.activeForecastJobs.set(forecastId, {
                id: forecastId,
                status: 'queued',
                progress: 0,
                startTime: new Date().toISOString(),
                config: config,
                result: null,
                error: null
            });

            // Emit event that forecast is queued/starting
            io.emit('forecast-status', { forecastId, status: 'queued', progress: 0 });

            // Run forecast asynchronously
            this.executeForecastWithProgress(forecastId, config, io)
                .then(result => {
                    logger.info(`Forecast [${forecastId}] completed successfully.`);
                    const job = this.activeForecastJobs.get(forecastId);
                    if (job) {
                        job.status = 'completed';
                        job.progress = 100;
                        job.result = result;
                        job.completedTime = new Date().toISOString();
                        this.activeForecastJobs.set(forecastId, job);
                        io.emit('forecast-completed', { forecastId, result });
                        io.emit('forecast-status', { forecastId, status: 'completed', progress: 100, result: result });
                    }
                })
                .catch(error => {
                    logger.error(`Forecast [${forecastId}] failed: ${error.message}`);
                    const job = this.activeForecastJobs.get(forecastId);
                    if (job) {
                        job.status = 'failed';
                        job.error = error.message;
                        job.failedTime = new Date().toISOString();
                        this.activeForecastJobs.set(forecastId, job);
                        io.emit('forecast-error', { forecastId, error: error.message });
                        io.emit('forecast-status', { forecastId, status: 'failed', error: error.message });
                    }
                });

            res.status(202).json({ // 202 Accepted: request accepted for processing
                success: true,
                forecastId: forecastId,
                message: 'Forecast job accepted and started successfully.'
            });
        } catch (error) {
            logger.error(`Error in runForecast: ${error.message}`);
            next(error);
        }
    }

    async executeForecastWithProgress(forecastId, config, io) {
        const job = this.activeForecastJobs.get(forecastId);
        if(job) {
            job.status = 'running';
            this.activeForecastJobs.set(forecastId, job);
            io.emit('forecast-status', { forecastId, status: 'running', progress: job.progress });
        }

        const onProgress = (progressData) => {
            const currentJob = this.activeForecastJobs.get(forecastId);
            if (currentJob) {
                currentJob.progress = progressData.progress || currentJob.progress;
                currentJob.currentSector = progressData.sector || currentJob.currentSector;
                currentJob.statusDetails = progressData.status || currentJob.statusDetails; // 'status' from python is more like a detail message
                this.activeForecastJobs.set(forecastId, currentJob);

                // Emit progress to client
                io.emit('forecast-progress', {
                    forecastId,
                    progress: currentJob.progress,
                    sector: currentJob.currentSector,
                    status: currentJob.statusDetails // status from python script
                });
                 io.emit('forecast-status', { // also emit to general status
                    forecastId,
                    status: 'running', // main job status
                    progress: currentJob.progress,
                    details: currentJob.statusDetails
                });
            }
        };

        // The Python script 'demand_projection.py' will handle the '--config' argument
        return pythonManager.executePythonScript(
            'demand_projection.py', // Main script
            ['--config', JSON.stringify(config)], // Arguments
            {
                timeout: config.timeout || 300000, // 5 minute default timeout, can be overridden by config
                onProgress // Callback for progress updates
            }
        );
    }

    async getForecastStatus(req, res, next) {
        try {
            const { forecastId } = req.params;
            const job = this.activeForecastJobs.get(forecastId);

            if (!job) {
                logger.warn(`Forecast status request for unknown ID: ${forecastId}`);
                return res.status(404).json({
                    success: false,
                    message: 'Forecast job not found.'
                });
            }

            res.json({
                success: true,
                forecastId: job.id,
                status: job.status,
                progress: job.progress,
                startTime: job.startTime,
                completedTime: job.completedTime,
                failedTime: job.failedTime,
                currentSector: job.currentSector,
                statusDetails: job.statusDetails,
                result: job.status === 'completed' ? job.result : null,
                error: job.status === 'failed' ? job.error : null,
                // config: job.config // Optionally return config, consider security implications
            });
        } catch (error) {
            logger.error(`Error in getForecastStatus for ID ${req.params.forecastId}: ${error.message}`);
            next(error);
        }
    }

    async getCorrelationData(req, res, next) {
        try {
            const { sector } = req.params;
             if (!sector) {
                return res.status(400).json({ success: false, message: 'Sector parameter is required.' });
            }
            const cacheKey = `correlation_data_${sector}`;

            let data = await cacheGet(cacheKey);
            if (data) {
                logger.info(`Cache hit for correlation data: ${sector}`);
                return res.json({ success: true, data: data, source: 'cache' });
            }

            logger.info(`Cache miss for correlation data: ${sector}. Fetching from Python script.`);
            data = await pythonManager.executePythonScript(
                'demand_projection.py', // Main script
                ['--correlation', sector] // Arguments
            );

            if (data) {
                await cacheSet(cacheKey, data, 600); // Cache for 10 minutes
                logger.info(`Correlation data for ${sector} fetched and cached.`);
            }

            res.json({
                success: true,
                data: data,
                source: 'script'
            });
        } catch (error) {
            logger.error(`Error in getCorrelationData for sector ${req.params.sector}: ${error.message}`);
            next(error);
        }
    }

    async cancelForecast(req, res, next) {
        try {
            const { forecastId } = req.params;
            const job = this.activeForecastJobs.get(forecastId);

            if (!job) {
                logger.warn(`Attempt to cancel non-existent forecast job: ${forecastId}`);
                return res.status(404).json({
                    success: false,
                    message: 'Forecast job not found.'
                });
            }

            if (job.status === 'running' || job.status === 'queued') {
                const cancelled = pythonManager.cancelProcess(forecastId); // Assuming pythonManager can map this ID or uses its own
                if (cancelled) {
                    job.status = 'cancelled';
                    job.cancelledTime = new Date().toISOString();
                    this.activeForecastJobs.set(forecastId, job);

                    const io = req.app.get('io');
                    io.emit('forecast-cancelled', { forecastId });
                    io.emit('forecast-status', { forecastId, status: 'cancelled' });

                    logger.info(`Forecast job [${forecastId}] cancelled successfully.`);
                    return res.json({
                        success: true,
                        message: 'Forecast job cancelled successfully.'
                    });
                } else {
                    // This case might occur if the process already finished or couldn't be found by pythonManager
                    logger.warn(`Could not cancel Python process for forecast job [${forecastId}]. It might have already finished or an issue occurred.`);
                     return res.status(500).json({
                        success: false,
                        message: 'Could not cancel the forecast Python process. It may have already completed or an error occurred.'
                    });
                }
            } else {
                logger.warn(`Attempt to cancel forecast job [${forecastId}] that is not running or queued. Status: ${job.status}`);
                return res.status(400).json({
                    success: false,
                    message: `Forecast job cannot be cancelled as it is already ${job.status}.`
                });
            }
        } catch (error) {
            logger.error(`Error in cancelForecast for ID ${req.params.forecastId}: ${error.message}`);
            next(error);
        }
    }

    // Method to list all active/recent jobs (optional)
    async listForecastJobs(req, res, next) {
        try {
            const jobs = Array.from(this.activeForecastJobs.values()).map(job => ({
                id: job.id,
                status: job.status,
                progress: job.progress,
                startTime: job.startTime,
                // Be cautious about returning full config/results in a list
            }));
            res.json({ success: true, jobs });
        } catch (error) {
            logger.error(`Error in listForecastJobs: ${error.message}`);
            next(error);
        }
    }
}

module.exports = new DemandController();
