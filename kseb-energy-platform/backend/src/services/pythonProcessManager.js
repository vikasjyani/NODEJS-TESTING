const { spawn } = require('child_process');
const path = require('path');
const { EventEmitter } = require('events');
const { logger } = require('../utils/logger'); // Assuming logger is set up

class PythonProcessManager extends EventEmitter {
    constructor() {
        super();
        this.activeProcesses = new Map();
        // In a real application, this might be configurable or dynamically determined
        this.maxConcurrentProcesses = parseInt(process.env.MAX_PYTHON_PROCESSES, 10) || 3;
        this.pythonPath = this.findPythonPath(); // Detect python path
    }

    findPythonPath() {
        // In production, this needs a more robust way to find Python,
        // especially if it's bundled or in a virtual environment.
        // For Electron, this might point to a bundled Python interpreter.
        if (process.env.PYTHON_PATH) {
            return process.env.PYTHON_PATH;
        }
        // Basic detection, might not be sufficient for all environments
        const pythonCommands = ['python3', 'python', 'py'];
        // For now, let's default to 'python'. This should be improved.
        // A more robust approach would involve checking if 'python' works, then 'python3', etc.
        // or using a library like 'python-shell' which handles this.
        return pythonCommands[0];
    }

    async executePythonScript(scriptName, args = [], options = {}) {
        return new Promise((resolve, reject) => {
            if (this.activeProcesses.size >= this.maxConcurrentProcesses) {
                logger.warn('Max concurrent Python processes reached. Queueing or rejecting task.');
                // Simple rejection for now. A queueing system could be implemented.
                return reject(new Error('Maximum concurrent Python processes reached. Please try again later.'));
            }

            const processId = this.generateProcessId(scriptName);
            // Resolve script path relative to the 'python' directory within 'src'
            const scriptDir = path.join(__dirname, '../python');
            const fullScriptPath = path.join(scriptDir, scriptName);

            logger.info(`Starting Python process [${processId}]: ${scriptName} with args: [${args.join(', ')}]`);

            const pythonProcess = spawn(this.pythonPath, [fullScriptPath, ...args], {
                stdio: ['pipe', 'pipe', 'pipe'], // stdin, stdout, stderr
                cwd: scriptDir, // Set working directory to the python scripts' directory
                env: {
                    ...process.env,
                    PYTHONPATH: scriptDir, // Add scriptDir to PYTHONPATH
                    PYTHONUNBUFFERED: "1" // Ensure output is not buffered
                }
            });

            let stdout = '';
            let stderr = '';

            pythonProcess.stdout.on('data', (data) => {
                const chunk = data.toString();
                stdout += chunk;

                // Handle real-time progress updates if options.onProgress is provided
                // Progress messages are expected to be prefixed with "PROGRESS:" and be valid JSON
                if (options.onProgress && chunk.includes('PROGRESS:')) {
                    const progressMessages = chunk.split('PROGRESS:').slice(1);
                    progressMessages.forEach(msgPart => {
                        try {
                            // Attempt to parse only the JSON part, handling potential trailing newlines or other text
                            const jsonMatch = msgPart.match(/\{.*\}/s);
                            if (jsonMatch) {
                                const progressData = JSON.parse(jsonMatch[0]);
                                options.onProgress(progressData);
                            }
                        } catch (e) {
                            logger.warn(`Failed to parse progress JSON from Python script [${processId}]: ${msgPart.substring(0,100)}... Error: ${e.message}`);
                        }
                    });
                }
            });

            pythonProcess.stderr.on('data', (data) => {
                const errorChunk = data.toString();
                stderr += errorChunk;
                logger.error(`Python script [${processId}] stderr: ${errorChunk}`);
            });

            pythonProcess.on('close', (code) => {
                this.activeProcesses.delete(processId);
                logger.info(`Python process [${processId}] exited with code ${code}.`);

                if (code === 0) {
                    try {
                        // Attempt to parse the entire stdout as JSON.
                        // Python scripts should output their final result as a single JSON object.
                        // If progress messages were also sent to stdout, they need to be filtered out
                        // or the Python script should ensure only the final JSON result is printed without "PROGRESS:"
                        const finalOutput = stdout.replace(/PROGRESS:\{.*?\}(\r\n|\n|\r)?/gs, '').trim();
                        const result = JSON.parse(finalOutput);
                        resolve(result);
                    } catch (error) {
                        logger.error(`Invalid JSON output from Python script [${processId}]. Error: ${error.message}. Output: ${stdout.substring(0, 500)}...`);
                        reject(new Error(`Invalid JSON output: ${stdout.substring(0, 200)}...`));
                    }
                } else {
                    logger.error(`Python script [${processId}] failed with code ${code}. Stderr: ${stderr}`);
                    reject(new Error(`Python script [${scriptName}] failed with code ${code}: ${stderr.substring(0,500)}...`));
                }
            });

            pythonProcess.on('error', (err) => {
                this.activeProcesses.delete(processId);
                logger.error(`Failed to start Python process [${processId}] for script ${scriptName}. Error: ${err.message}`);
                reject(new Error(`Failed to start Python process for ${scriptName}: ${err.message}`));
            });


            this.activeProcesses.set(processId, {
                process: pythonProcess,
                startTime: Date.now(),
                script: scriptName,
                args: args
            });

            if (options.timeout) {
                const timeoutId = setTimeout(() => {
                    if (this.activeProcesses.has(processId)) {
                        logger.warn(`Python process [${processId}] for script ${scriptName} timed out after ${options.timeout}ms. Killing process.`);
                        pythonProcess.kill('SIGTERM'); // Send SIGTERM first for graceful shutdown

                        // Force kill if not terminated after a short delay
                        setTimeout(() => {
                            if (this.activeProcesses.has(processId) && !pythonProcess.killed) {
                                logger.warn(`Python process [${processId}] did not terminate gracefully. Force killing with SIGKILL.`);
                                pythonProcess.kill('SIGKILL');
                            }
                        }, 2000); // 2 seconds grace period

                        this.activeProcesses.delete(processId);
                        reject(new Error(`Python process for ${scriptName} timed out after ${options.timeout}ms`));
                    }
                }, options.timeout);
                // Store timeoutId to clear it if process finishes early
                this.activeProcesses.get(processId).timeoutId = timeoutId;
            }
        });
    }

    cancelProcess(processId) {
        const job = this.activeProcesses.get(processId);
        if (job) {
            logger.info(`Attempting to cancel Python process [${processId}] for script ${job.script}`);
            job.process.kill('SIGTERM'); // Or 'SIGKILL' for forceful termination
            if (job.timeoutId) {
                clearTimeout(job.timeoutId);
            }
            this.activeProcesses.delete(processId);
            return true;
        }
        logger.warn(`Attempted to cancel non-existent Python process [${processId}]`);
        return false;
    }

    generateProcessId(scriptName) {
        return `py_${scriptName.replace('.py', '')}_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`;
    }

    getActiveProcesses() {
        return Array.from(this.activeProcesses.values()).map(p => ({
            id: Array.from(this.activeProcesses.keys()).find(key => this.activeProcesses.get(key) === p),
            script: p.script,
            args: p.args,
            startTime: p.startTime,
            pid: p.process.pid
        }));
    }
}

// Export a singleton instance
module.exports = new PythonProcessManager();
