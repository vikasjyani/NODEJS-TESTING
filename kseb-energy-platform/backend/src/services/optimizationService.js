// const cluster = require('cluster'); // For multi-process parallelism (more complex than worker_threads for this use case)
const os = require('os');
const { Worker, isMainThread, parentPort, workerData } = require('worker_threads');
const path = require('path');
const { logger } = require('../utils/logger'); // Assuming logger is available

// --- Worker Thread Code ---
// This code will be executed in each worker thread.
// It's embedded here as a string for simplicity in a single-file service.
// In a larger setup, this would be in its own .js file.
const workerScript = `
const { parentPort, workerData } = require('worker_threads');
const { performance } = require('perf_hooks');
// Potentially import heavy libraries here if they are only used by workers
// const someHeavyLibrary = require('some-heavy-library');

async function simulateComplexCalculation(data) {
    // Example: Simulate a CPU-bound task
    const { durationMs = 1000, payloadSize = 100 } = data;
    let result = 0;
    for (let i = 0; i < payloadSize * 100000; i++) { // Adjust loop for desired intensity
        result += Math.sqrt(i) * Math.sin(i);
    }
    // Simulate varied task duration
    await new Promise(resolve => setTimeout(resolve, Math.random() * durationMs));
    return { inputData: data, calculatedResult: result, charactersProcessed: payloadSize * 100 };
}

async function processGenericTask(taskData) {
    // This function would dispatch to specific handlers based on taskData.operation
    // For now, it's a generic placeholder for any offloaded computation.
    // Example: if (taskData.operation === 'image_resize') return resizeImage(taskData.payload);
    logger.debug(\`Worker [Thread \${require('worker_threads').threadId}] processing generic task: \${taskData.operation || 'unknown_op'}\`);
    return await simulateComplexCalculation(taskData.payload || {});
}


parentPort.on('message', async (task) => {
    const { taskId, type, data } = task;
    const startTime = performance.now();
    logger.debug(\`Worker [Thread \${require('worker_threads').threadId}] received task: \${taskId} (\${type})\`);

    try {
        let result;
        // In a real scenario, 'type' would determine which function to call.
        // e.g. if (type === 'DEMAND_MODEL_TRAINING') result = await trainDemandModel(data);
        // For now, using a generic processor.
        result = await processGenericTask(data); // 'data' here is task.data from main thread

        const endTime = performance.now();
        parentPort.postMessage({
            taskId,
            status: 'completed',
            result,
            processingTimeMs: endTime - startTime,
            threadId: require('worker_threads').threadId
        });
    } catch (error) {
        parentPort.postMessage({
            taskId,
            status: 'failed',
            error: { message: error.message, stack: error.stack }, // Send serializable error info
            threadId: require('worker_threads').threadId
        });
    }
});

// Signal main thread that worker is ready (optional)
parentPort.postMessage({ status: 'ready', threadId: require('worker_threads').threadId });
`;


class OptimizationService {
    constructor(options = {}) {
        // Determine number of workers: default to numCPUs - 1, min 1, max as configured or reasonable limit
        const numCPUs = os.cpus().length;
        this.maxWorkers = options.maxWorkers || Math.min(Math.max(1, numCPUs - 1), 8); // Default max 8 workers

        this.workerPool = []; // Stores { worker: Worker, busy: boolean, id: number }
        this.taskQueue = [];  // Stores tasks waiting for a worker: { taskId, type, data, resolve, reject, priority }
        this.activeTasks = new Map(); // Stores promise resolve/reject for active tasks: { taskId -> {resolve, reject} }

        this.isShuttingDown = false;
        this.logger = options.logger || logger;

        this.initializeWorkerPool();
        this.logger.info(`OptimizationService initialized with ${this.maxWorkers} worker threads.`);
    }

    initializeWorkerPool() {
        for (let i = 0; i < this.maxWorkers; i++) {
            this._createWorker(i);
        }
    }

    _createWorker(workerId) {
        // Using `eval` for the worker script is generally okay for self-contained worker code
        // that doesn't change dynamically based on external input.
        // For more complex workers, a separate worker file is better: new Worker(path.resolve(__dirname, 'worker.js'))
        const worker = new Worker(workerScript, { eval: true, workerData: { workerId } });
        const workerInfo = { worker, busy: false, id: worker.threadId, createdAt: Date.now() };
        this.workerPool.push(workerInfo);

        worker.on('message', (message) => {
            if (message.status === 'ready') {
                this.logger.info(`Worker [Thread ${message.threadId}] ready.`);
                this._tryAssignTask(); // Try to assign if tasks are queued
                return;
            }
            this._handleWorkerMessage(message);
        });

        worker.on('error', (error) => {
            this.logger.error(`Worker [Thread ${worker.threadId}] error: ${error.message}`, { stack: error.stack });
            this._handleWorkerError(worker.threadId, error);
            // Optionally, try to replace the crashed worker
            // this._replaceWorker(workerInfo);
        });

        worker.on('exit', (code) => {
            if (code !== 0 && !this.isShuttingDown) {
                this.logger.warn(`Worker [Thread ${worker.threadId}] exited unexpectedly with code ${code}.`);
                this._handleWorkerError(worker.threadId, new Error(`Exited with code ${code}`));
                // Optionally, replace the worker
                // this._replaceWorker(workerInfo);
            } else {
                 this.logger.info(`Worker [Thread ${worker.threadId}] exited cleanly.`);
            }
            // Remove from pool
            this.workerPool = this.workerPool.filter(w => w.worker !== worker);
            if (!this.isShuttingDown && this.workerPool.length < this.maxWorkers) {
                this.logger.info(`Attempting to replace exited worker.`);
                this._createWorker(this.workerPool.length); // Create a new one
            }
        });
    }

    // _replaceWorker(failedWorkerInfo) {
    //     this.logger.info(`Replacing failed/exited worker [Thread ${failedWorkerInfo.id}].`);
    //     this.workerPool = this.workerPool.filter(w => w !== failedWorkerInfo);
    //     this._createWorker(this.workerPool.length); // Simple replacement
    // }

    _handleWorkerMessage(message) {
        const { taskId, status, result, error, processingTimeMs, threadId } = message;
        const promiseControls = this.activeTasks.get(taskId);

        if (!promiseControls) {
            this.logger.warn(`Received message for unknown or timed-out task ID: ${taskId} from worker ${threadId}.`);
            return;
        }

        if (status === 'completed') {
            promiseControls.resolve(result);
            this.logger.info(`Task ${taskId} completed by Worker [${threadId}] in ${processingTimeMs?.toFixed(2)}ms.`);
        } else if (status === 'failed') {
            const err = new Error(error?.message || 'Worker task failed');
            if(error?.stack) err.stack = error.stack; // Preserve stack if available
            promiseControls.reject(err);
            this.logger.error(`Task ${taskId} failed in Worker [${threadId}]: ${err.message}`);
        }
        this.activeTasks.delete(taskId);

        // Mark worker as free and try to assign next task
        const workerInfo = this.workerPool.find(w => w.worker.threadId === threadId);
        if (workerInfo) {
            workerInfo.busy = false;
        }
        this._tryAssignTask();
    }

    _handleWorkerError(threadId, error) {
        // If a worker errors out, find any task it might have been running and reject it.
        let taskFoundAndRejected = false;
        for (const [taskId, promiseControls] of this.activeTasks.entries()) {
            // This assumes we can map threadId back to a task if the worker dies mid-task.
            // A more robust way is for workerInfo to store currentTaskId.
            const workerInfo = this.workerPool.find(w => w.worker.threadId === threadId);
            if (workerInfo && workerInfo.currentTaskId === taskId) { // Assuming workerInfo.currentTaskId exists
                promiseControls.reject(new Error(`Worker [${threadId}] crashed during task ${taskId}: ${error.message}`));
                this.activeTasks.delete(taskId);
                taskFoundAndRejected = true;
                break;
            }
        }
        if (!taskFoundAndRejected) {
            this.logger.warn(`Worker [${threadId}] errored, but no active task was directly associated or already handled.`);
        }
    }


    _tryAssignTask() {
        if (this.taskQueue.length === 0) return; // No tasks to assign
        const availableWorker = this.workerPool.find(w => !w.busy);
        if (!availableWorker) return; // No free workers

        const taskToRun = this.taskQueue.shift(); // Get highest priority (if sorted) or oldest
        if (taskToRun) {
            availableWorker.busy = true;
            // availableWorker.currentTaskId = taskToRun.taskId; // Track current task on worker
            this.logger.debug(`Assigning Task ${taskToRun.taskId} (${taskToRun.type}) to Worker [${availableWorker.worker.threadId}]`);
            availableWorker.worker.postMessage(taskToRun);
        }
    }

    /**
     * Offloads a CPU-intensive task to a worker thread.
     * @param {string} type - A type identifier for the task (e.g., 'DEMAND_CALCULATION', 'PYPSA_PREPROCESS').
     * @param {any} data - Data required for the task. Must be serializable.
     * @param {object} [options] - Task options.
     * @param {'high'|'normal'|'low'} [options.priority='normal'] - Task priority.
     * @param {number} [options.timeoutMs=60000] - Timeout for the task in milliseconds.
     * @returns {Promise<any>} A promise that resolves with the task result or rejects on error/timeout.
     */
    async offloadTask(type, data, options = {}) {
        if (this.isShuttingDown) {
            return Promise.reject(new Error("OptimizationService is shutting down. Not accepting new tasks."));
        }

        const { priority = 'normal', timeoutMs = 60000 } = options; // Default 1 min timeout
        const taskId = `task_${type}_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`;

        this.logger.info(`Queueing task ${taskId} (Type: ${type}, Priority: ${priority})`);

        return new Promise((resolve, reject) => {
            const task = { taskId, type, data, priority };
            this.activeTasks.set(taskId, { resolve, reject });

            // Add to queue (priority queue could be implemented here if needed)
            // For simplicity, adding to end and relying on _tryAssignTask to pick.
            // If using priority, sort the queue:
            this.taskQueue.push(task);
            this.taskQueue.sort((a, b) => { // Higher priority first
                 const pOrder = { high: 3, normal: 2, low: 1 };
                 return (pOrder[b.priority] || 0) - (pOrder[a.priority] || 0);
            });

            this._tryAssignTask();

            // Task timeout
            const timeoutId = setTimeout(() => {
                if (this.activeTasks.has(taskId)) {
                    this.logger.warn(`Task ${taskId} (Type: ${type}) timed out after ${timeoutMs}ms.`);
                    this.activeTasks.get(taskId).reject(new Error(`Task ${type} timed out after ${timeoutMs/1000}s.`));
                    this.activeTasks.delete(taskId);
                    // Note: This doesn't kill the worker thread, just rejects the promise.
                    // Worker might still be busy. A more robust timeout would involve worker termination/recreation.
                }
            }, timeoutMs);

            // Store timeoutId to clear it if task completes/fails early
            this.activeTasks.get(taskId).timeoutId = timeoutId;
        }).finally(() => {
            // Clear timeout when promise settles (either resolved or rejected)
            const promiseControls = this.activeTasks.get(taskId);
            if (promiseControls && promiseControls.timeoutId) {
                clearTimeout(promiseControls.timeoutId);
            }
        });
    }

    getStats() {
        return {
            maxWorkers: this.maxWorkers,
            currentWorkers: this.workerPool.length,
            idleWorkers: this.workerPool.filter(w => !w.busy).length,
            busyWorkers: this.workerPool.filter(w => w.busy).length,
            queuedTasks: this.taskQueue.length,
            processingTasks: this.activeTasks.size, // Tasks currently assigned and promise not settled
        };
    }

    async shutdown(graceful = true) {
        this.logger.info(`OptimizationService shutting down (graceful: ${graceful})...`);
        this.isShuttingDown = true;

        // Reject any pending tasks in the queue
        this.taskQueue.forEach(task => {
            const promiseControls = this.activeTasks.get(task.taskId);
            if (promiseControls) {
                promiseControls.reject(new Error("Service shutting down; task cancelled from queue."));
                this.activeTasks.delete(task.taskId);
            }
        });
        this.taskQueue = [];

        // Wait for active tasks to complete if graceful, or terminate workers
        if (graceful && this.activeTasks.size > 0) {
            this.logger.info(`Waiting for ${this.activeTasks.size} active tasks to complete...`);
            // This is a simplified wait; a more robust one would use Promise.allSettled
            // on the promises stored in this.activeTasks.
            await new Promise(resolve => setTimeout(resolve, 5000)); // Wait 5s for tasks
        }

        await Promise.all(this.workerPool.map(async (workerInfo) => {
            try {
                await workerInfo.worker.terminate();
                this.logger.info(`Worker [Thread ${workerInfo.id}] terminated.`);
            } catch (err) {
                this.logger.error(`Error terminating worker [Thread ${workerInfo.id}]: ${err.message}`);
            }
        }));

        this.workerPool = [];
        this.activeTasks.clear(); // Clear any remaining, though they should be handled
        this.logger.info("OptimizationService shutdown complete.");
    }
}

// Export a singleton instance if appropriate for the application
// const optimizationServiceInstance = new OptimizationService();
// module.exports = optimizationServiceInstance;

// Or export the class to be instantiated by the main application
module.exports = { OptimizationService };
