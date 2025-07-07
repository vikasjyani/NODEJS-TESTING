const pythonManager = require('../services/pythonProcessManager');
const { validateProfileConfig } = require('../middleware/validation');
const { fileService } = require('../services/fileService'); // Will be created
const { logger } = require('../utils/logger');
const path = require('path');
const fs = require('fs').promises; // Using fs.promises for async file operations

// Define a base directory for storing results, e.g., within the project or a configurable path
const RESULTS_BASE_DIR = process.env.RESULTS_DIR || path.join(process.cwd(), 'results');
const LOAD_PROFILES_DIR = path.join(RESULTS_BASE_DIR, 'load_profiles');

class LoadProfileController {
    constructor() {
        this.activeGenerationJobs = new Map(); // Stores active generation jobs
        this.savedProfiles = new Map(); // In-memory cache of loaded profile metadata/summaries

        // Ensure the directory for saving profiles exists
        this._ensureResultsDirExists();
        // Load any existing profiles from disk on startup (optional, can be lazy-loaded)
        // this.loadSavedProfilesFromDisk().catch(err => logger.error("Error auto-loading profiles on startup:", err));
    }

    async _ensureResultsDirExists() {
        try {
            await fs.mkdir(LOAD_PROFILES_DIR, { recursive: true });
            logger.info(`Load profiles directory ensured at: ${LOAD_PROFILES_DIR}`);
        } catch (error) {
            logger.error(`Failed to create load profiles directory at ${LOAD_PROFILES_DIR}:`, error);
        }
    }

    async generateProfile(req, res, next) {
        try {
            const config = req.body;

            const validationResult = validateProfileConfig(config); // Implemented in validation.js
            if (!validationResult.isValid) {
                logger.warn(`Load profile configuration validation failed. Errors: ${validationResult.errors.join(', ')}`);
                return res.status(400).json({
                    success: false,
                    message: 'Invalid profile configuration.',
                    errors: validationResult.errors
                });
            }

            const profileJobId = `profile_job_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`;
            const io = req.app.get('io');

            logger.info(`Starting new load profile generation job [${profileJobId}] with config: ${JSON.stringify(config)}`);
            this.activeGenerationJobs.set(profileJobId, {
                id: profileJobId,
                status: 'queued',
                progress: 0,
                startTime: new Date().toISOString(),
                config: config,
                result: null, // This will store the Python script's output (metadata, path to file, etc.)
                error: null
            });

            io.emit('profile-generation-status', { profileJobId, status: 'queued', progress: 0 });

            this.executeGenerationWithProgress(profileJobId, config, io)
                .then(pythonResult => { // pythonResult contains { profile_id (from python), saved_path, statistics, etc. }
                    logger.info(`Profile generation job [${profileJobId}] (Python Profile ID: ${pythonResult.profile_id}) completed successfully.`);
                    const job = this.activeGenerationJobs.get(profileJobId);
                    if (job) {
                        job.status = 'completed';
                        job.progress = 100;
                        job.result = pythonResult; // Store Python's output
                        job.completedTime = new Date().toISOString();
                        this.activeGenerationJobs.set(profileJobId, job);

                        // Cache the generated profile's metadata (not the full data)
                        this.savedProfiles.set(pythonResult.profile_id, {
                            profile_id: pythonResult.profile_id,
                            method: pythonResult.method,
                            generation_time: pythonResult.generation_time,
                            years_generated: pythonResult.years_generated,
                            summary: pythonResult.statistics, // Assuming python returns a summary
                            filePath: pythonResult.saved_path // Path to the detailed profile data file
                        });

                        io.emit('profile-generated', { profileJobId, result: pythonResult });
                        io.emit('profile-generation-status', { profileJobId, status: 'completed', progress: 100, result: pythonResult });
                    }
                })
                .catch(error => {
                    logger.error(`Profile generation job [${profileJobId}] failed: ${error.message}`);
                    const job = this.activeGenerationJobs.get(profileJobId);
                    if (job) {
                        job.status = 'failed';
                        job.error = error.message;
                        job.failedTime = new Date().toISOString();
                        this.activeGenerationJobs.set(profileJobId, job);
                        io.emit('profile-error', { profileJobId, error: error.message });
                        io.emit('profile-generation-status', { profileJobId, status: 'failed', error: error.message });
                    }
                });

            res.status(202).json({
                success: true,
                profileJobId: profileJobId,
                message: 'Profile generation job started successfully.'
            });
        } catch (error) {
            logger.error(`Error in generateProfile: ${error.message}`);
            next(error);
        }
    }

    async executeGenerationWithProgress(profileJobId, config, io) {
        const job = this.activeGenerationJobs.get(profileJobId);
        if(job) {
            job.status = 'running';
            this.activeGenerationJobs.set(profileJobId, job);
            io.emit('profile-generation-status', { profileJobId, status: 'running', progress: job.progress });
        }

        const onProgress = (progressData) => {
            const currentJob = this.activeGenerationJobs.get(profileJobId);
            if (currentJob) {
                currentJob.progress = progressData.progress || currentJob.progress;
                currentJob.currentStep = progressData.step || currentJob.currentStep;
                currentJob.statusDetails = progressData.status || currentJob.statusDetails;
                this.activeGenerationJobs.set(profileJobId, currentJob);

                io.emit('profile-progress', { // For detailed progress UI
                    profileJobId, // This is the job ID for tracking on frontend
                    pythonProfileId: progressData.profile_id, // This is the ID from Python, useful if Python generates it early
                    progress: currentJob.progress,
                    step: currentJob.currentStep,
                    status: currentJob.statusDetails
                });
                io.emit('profile-generation-status', { // For general job status
                    profileJobId,
                    status: 'running',
                    progress: currentJob.progress,
                    details: currentJob.statusDetails
                });
            }
        };

        // Python script name for load profile generation
        return pythonManager.executePythonScript(
            'load_profile_generation.py',
            ['--config', JSON.stringify(config)],
            {
                timeout: config.timeout || 600000, // 10 minute default timeout
                onProgress
            }
        );
    }

    async getGenerationStatus(req, res, next) {
        try {
            const { profileJobId } = req.params;
            const job = this.activeGenerationJobs.get(profileJobId);

            if (!job) {
                return res.status(404).json({ success: false, message: 'Profile generation job not found.' });
            }
            res.json({ success: true, job });
        } catch (error) {
            logger.error(`Error in getGenerationStatus for job ID ${req.params.profileJobId}: ${error.message}`);
            next(error);
        }
    }

    async getSavedProfiles(req, res, next) {
        try {
            // Load profiles from file system if not in memory or if a refresh is needed
            if (this.savedProfiles.size === 0 || req.query.refresh === 'true') {
                 await this.loadSavedProfilesFromDisk();
            }

            const profilesList = Array.from(this.savedProfiles.values()).map(profile => ({
                profile_id: profile.profile_id, // This is the ID generated by Python
                method: profile.method,
                generation_time: profile.generation_time,
                years_generated: profile.years_generated,
                summary: profile.summary // Key statistics
            }));

            res.json({ success: true, profiles: profilesList });
        } catch (error) {
            logger.error('Error in getSavedProfiles:', error);
            next(error);
        }
    }

    async getProfileData(req, res, next) {
        try {
            const { profileId } = req.params; // This is the Python-generated profile_id
            let profile = this.savedProfiles.get(profileId);

            if (!profile || !profile.filePath) {
                // Try loading from disk if not in memory cache or path is missing
                const loadedProfile = await this.loadProfileFromDisk(profileId);
                if (!loadedProfile) {
                     return res.status(404).json({ success: false, message: 'Profile not found or file path missing.' });
                }
                profile = loadedProfile; // Use the fully loaded profile
            }

            // Read the detailed profile data from the file
            const detailedData = await fileService.readJsonFile(profile.filePath);

            res.json({
                success: true,
                profile: { // Send metadata and detailed data
                    ...profile, // metadata from this.savedProfiles
                    data: detailedData // actual data from file
                }
            });
        } catch (error)
        {
            logger.error(`Error in getProfileData for profile ID ${req.params.profileId}: ${error.message}`);
            if (error.code === 'ENOENT') {
                return res.status(404).json({ success: false, message: 'Profile data file not found.' });
            }
            next(error);
        }
    }

    async analyzeProfile(req, res, next) {
        try {
            const { profileId } = req.params;
            const { analysisType } = req.query; // e.g., 'overview', 'seasonal', 'peak_analysis'

            // Ensure profile exists (at least its metadata/path)
            const profileMeta = this.savedProfiles.get(profileId) || await this.loadProfileFromDisk(profileId);
            if (!profileMeta || !profileMeta.filePath) {
                 return res.status(404).json({ success: false, message: 'Profile metadata not found for analysis.' });
            }

            // Call Python script for analysis, passing the profile_id or path to its data file
            const result = await pythonManager.executePythonScript(
                'load_profile_analysis.py', // Analysis script
                ['--profile-id', profileId, '--analysis-type', analysisType || 'overview', '--profile-path', profileMeta.filePath]
            );

            res.json({ success: true, analysis: result });
        } catch (error) {
            logger.error(`Error in analyzeProfile for ID ${req.params.profileId}: ${error.message}`);
            next(error);
        }
    }

    async deleteProfile(req, res, next) {
        try {
            const { profileId } = req.params;
            const profileMeta = this.savedProfiles.get(profileId);

            // Remove from memory
            this.savedProfiles.delete(profileId);

            // Remove from disk
            // The actual file path should be stored in profileMeta when profile is generated/loaded
            const filePath = profileMeta ? profileMeta.filePath : path.join(LOAD_PROFILES_DIR, `${profileId}.json`);

            try {
                await fileService.deleteFile(filePath);
                logger.info(`Profile ${profileId} (file: ${filePath}) deleted successfully.`);
            } catch (fileError) {
                // Log if file deletion failed but proceed if it didn't exist (idempotency)
                if (fileError.code !== 'ENOENT') {
                     logger.warn(`Failed to delete profile file ${filePath} for ID ${profileId}, but removing from records. Error: ${fileError.message}`);
                } else {
                    logger.info(`Profile file ${filePath} for ID ${profileId} not found on disk, removed from records.`);
                }
            }

            res.json({ success: true, message: 'Profile deleted successfully.' });
        } catch (error) {
            logger.error(`Error in deleteProfile for ID ${req.params.profileId}: ${error.message}`);
            next(error);
        }
    }

    async compareProfiles(req, res, next) {
        try {
            const { profileIds } = req.body; // Expect an array of profile IDs

            if (!Array.isArray(profileIds) || profileIds.length < 2) {
                return res.status(400).json({ success: false, message: 'At least 2 profile IDs are required for comparison.' });
            }

            // Fetch file paths for profiles
            const profileFilePaths = [];
            for (const pId of profileIds) {
                const meta = this.savedProfiles.get(pId) || await this.loadProfileFromDisk(pId);
                if (meta && meta.filePath) {
                    profileFilePaths.push(meta.filePath);
                } else {
                    return res.status(404).json({ success: false, message: `Profile ${pId} not found or file path missing.` });
                }
            }

            const result = await pythonManager.executePythonScript(
                'load_profile_analysis.py', // Analysis script
                ['--compare-paths', JSON.stringify(profileFilePaths)] // Pass file paths
            );

            res.json({ success: true, comparison: result });
        } catch (error) {
            logger.error(`Error in compareProfiles: ${error.message}`);
            next(error);
        }
    }

    async loadSavedProfilesFromDisk() {
        logger.info(`Attempting to load saved profiles from ${LOAD_PROFILES_DIR}`);
        try {
            const files = await fs.readdir(LOAD_PROFILES_DIR);
            let loadedCount = 0;
            for (const file of files) {
                if (file.endsWith('.json')) {
                    const profileIdFromFile = file.replace('.json', '');
                    // Load if not already in memory or if a force refresh is needed
                    if (!this.savedProfiles.has(profileIdFromFile)) {
                       const loaded = await this.loadProfileFromDisk(profileIdFromFile);
                       if(loaded) loadedCount++;
                    }
                }
            }
            logger.info(`Loaded ${loadedCount} profiles from disk.`);
        } catch (error) {
            if (error.code === 'ENOENT') {
                logger.info('Load profiles directory does not exist yet. No profiles loaded.');
            } else {
                logger.error('Failed to scan saved profiles directory:', error);
            }
        }
    }

    async loadProfileFromDisk(profileId) {
        const profilePath = path.join(LOAD_PROFILES_DIR, `${profileId}.json`);
        try {
            const profileDataString = await fs.readFile(profilePath, 'utf-8');
            const profileFromFile = JSON.parse(profileDataString); // This is the full data including { profile_id, method, data: { year1: [...], year2: [...] }}

            // Cache metadata
            const metadata = {
                profile_id: profileFromFile.profile_id || profileId,
                method: profileFromFile.method,
                generation_time: profileFromFile.generation_time,
                years_generated: profileFromFile.config ? [profileFromFile.config.start_year, profileFromFile.config.end_year] : Object.keys(profileFromFile.data),
                summary: profileFromFile.statistics || this._calculateSummaryFromData(profileFromFile.data), // Calculate if not present
                filePath: profilePath, // Store the path
                config: profileFromFile.config
            };
            this.savedProfiles.set(profileId, metadata);
            logger.info(`Loaded profile ${profileId} from disk: ${profilePath}`);
            return metadata; // Return the metadata
        } catch (error) {
            logger.error(`Failed to load profile ${profileId} from disk (${profilePath}):`, error);
            return null; // Return null if loading fails
        }
    }

    _calculateSummaryFromData(profileDataByYear) {
        // Basic summary if 'statistics' field is missing from the JSON file
        if (!profileDataByYear || typeof profileDataByYear !== 'object') return {};
        let totalEnergy = 0;
        let peakDemand = 0;
        const years = Object.keys(profileDataByYear);
        if (years.length === 0) return {};

        for (const year in profileDataByYear) {
            const yearData = profileDataByYear[year]; // Array of {datetime, load, ...}
            if (Array.isArray(yearData)) {
                yearData.forEach(rec => {
                    totalEnergy += rec.load || 0;
                    if ((rec.load || 0) > peakDemand) peakDemand = rec.load;
                });
            }
        }
        const avgDemand = totalEnergy / (years.length * 8760); // Approximate
        return {
            peak_demand: peakDemand,
            total_energy: totalEnergy,
            load_factor: peakDemand > 0 ? avgDemand / peakDemand : 0,
        };
    }
}

module.exports = new LoadProfileController();
