const { performance, PerformanceObserver } = require('perf_hooks');
const os = require('os');
const { EventEmitter } = require('events');
const { logger } = require('../utils/logger'); // Assuming logger is available

// Simple moving average helper
class MovingAverage {
    constructor(size = 100) {
        this.size = size;
        this.buffer = [];
        this.sum = 0;
    }
    add(value) {
        this.buffer.push(value);
        this.sum += value;
        if (this.buffer.length > this.size) {
            this.sum -= this.buffer.shift();
        }
    }
    getAverage() {
        return this.buffer.length > 0 ? this.sum / this.buffer.length : 0;
    }
    getCount() {
        return this.buffer.length;
    }
}


class PerformanceMonitor extends EventEmitter {
    constructor(options = {}) {
        super();
        this.metrics = new Map(); // Stores aggregated metrics per endpoint
        this.activeRequests = new Map(); // Tracks currently active requests

        this.systemMetrics = { // Stores time series of system metrics
            cpuUsage: new MovingAverage(60), // Avg CPU over last ~30 mins (if 1 sample / 30s)
            freeMemoryMB: new MovingAverage(60),
            eventLoopLagMs: new MovingAverage(60), // Avg event loop lag
            activeHandles: new MovingAverage(60),
        };
        this.alerts = []; // Stores recent alerts

        this.thresholds = {
            responseTimeMs: options.responseTimeMs || 5000, // 5 seconds
            memoryUsagePercent: options.memoryUsagePercent || 0.85,  // 85% of heap or total system
            cpuUsagePercent: options.cpuUsagePercent || 0.80,     // 80%
            errorRatePercent: options.errorRatePercent || 5,     // 5%
            eventLoopLagMs: options.eventLoopLagMs || 100, // 100ms lag
        };

        this.systemMonitorInterval = null;
        this.eventLoopMonitor = null;
        this.logger = options.logger || logger; // Use injected logger or default

        this.startSystemMonitoring();
        this.startEventLoopMonitoring();

        this.logger.info('PerformanceMonitor initialized.');
    }

    // Middleware to track individual requests
    trackRequest(req, res, next) {
        const requestId = req.id || this.generateRequestId(); // Use existing req.id (e.g. from requestId middleware) or generate one
        req.requestId = requestId; // Ensure it's on req
        const startTime = performance.now();
        const startMemory = process.memoryUsage();

        this.activeRequests.set(requestId, {
            method: req.method,
            url: req.originalUrl, // Use originalUrl for more accurate endpoint logging
            startTime,
            startMemory,
            ip: req.ip,
        });
        this.emit('requestStart', { requestId, method: req.method, url: req.originalUrl, ip: req.ip });

        const originalEnd = res.end;
        res.end = (...args) => {
            // Ensure this runs only once per request, even if 'end' is called multiple times (though it shouldn't)
            if (!res.finished) { // 'finished' is a good flag from Node.js HTTP response
                const endTime = performance.now();
                const endMemory = process.memoryUsage();
                const duration = endTime - startTime;

                this.recordRequestMetrics({
                    requestId,
                    method: req.method,
                    url: req.originalUrl,
                    statusCode: res.statusCode,
                    duration,
                    memoryDeltaBytes: endMemory.heapUsed - startMemory.heapUsed,
                    timestamp: new Date().toISOString(),
                });
                this.activeRequests.delete(requestId);
            }
            originalEnd.apply(res, args);
        };
        next();
    }

    recordRequestMetrics(requestData) {
        const { url, method, statusCode, duration } = requestData;
        // Normalize URL to group similar endpoints, e.g., remove UUIDs if necessary
        // For now, using originalUrl as key. This could be refined.
        const endpointKey = `${method}:${url.split('?')[0]}`; // Group by path without query params

        if (!this.metrics.has(endpointKey)) {
            this.metrics.set(endpointKey, {
                count: 0,
                totalTimeMs: 0,
                avgTimeMs: 0,
                minTimeMs: Infinity,
                maxTimeMs: 0,
                errorCount: 0,
                successCount: 0,
                lastAccessed: null,
                statusCodes: new Map(), // Store counts per status code
                avgMemoryDeltaBytes: new MovingAverage(100),
            });
        }

        const endpointMetric = this.metrics.get(endpointKey);
        endpointMetric.count++;
        endpointMetric.totalTimeMs += duration;
        endpointMetric.avgTimeMs = endpointMetric.totalTimeMs / endpointMetric.count;
        endpointMetric.minTimeMs = Math.min(endpointMetric.minTimeMs, duration);
        endpointMetric.maxTimeMs = Math.max(endpointMetric.maxTimeMs, duration);
        endpointMetric.lastAccessed = requestData.timestamp;
        endpointMetric.avgMemoryDeltaBytes.add(requestData.memoryDeltaBytes);

        endpointMetric.statusCodes.set(statusCode, (endpointMetric.statusCodes.get(statusCode) || 0) + 1);

        if (statusCode >= 400) {
            endpointMetric.errorCount++;
        } else {
            endpointMetric.successCount++;
        }

        this.checkPerformanceAlerts(endpointKey, requestData, endpointMetric);
        this.emit('requestCompleted', { endpoint: endpointKey, ...requestData });
    }

    checkPerformanceAlerts(endpointKey, requestData, metric) {
        const alertsTriggered = [];
        if (requestData.duration > this.thresholds.responseTimeMs) {
            alertsTriggered.push(this._createAlert('slow_response', 'warning',
                `Slow response: ${requestData.duration.toFixed(0)}ms for ${endpointKey}`,
                { endpointKey, duration: requestData.duration }
            ));
        }

        const errorRate = metric.count > 10 ? (metric.errorCount / metric.count) * 100 : 0;
        if (errorRate > this.thresholds.errorRatePercent) {
            alertsTriggered.push(this._createAlert('high_error_rate', 'error',
                `High error rate: ${errorRate.toFixed(1)}% for ${endpointKey}`,
                { endpointKey, errorRate, totalRequests: metric.count }
            ));
        }
        // Add more specific alerts (e.g., memory per request if needed)
    }

    _createAlert(type, severity, message, data) {
        const alert = { type, severity, message, timestamp: new Date().toISOString(), data };
        this.alerts.push(alert);
        if (this.alerts.length > 200) this.alerts.shift(); // Keep last 200 alerts
        this.emit('alert', alert);
        this.logger.warn(`ALERT [${type}|${severity}]: ${message}`, data || '');
        return alert;
    }


    startSystemMonitoring(intervalMs = 30000) { // Monitor every 30 seconds
        if (this.systemMonitorInterval) clearInterval(this.systemMonitorInterval);
        this.systemMonitorInterval = setInterval(() => {
            this.collectSystemMetrics();
        }, intervalMs);
        this.collectSystemMetrics(); // Initial collection
        this.logger.info(`System monitoring started. Interval: ${intervalMs}ms`);
    }

    collectSystemMetrics() {
        const timestamp = new Date().toISOString();

        // CPU Usage (simplified - this is tricky to get accurately for the Node process itself without native modules)
        // os.cpus() gives info for all cores, not just current process load.
        // For a more accurate process CPU usage, a library like `pidusage` would be needed.
        // This is a system-wide average idle time inversion.
        const avgCpuIdle = os.cpus().reduce((acc, cpu) => acc + cpu.times.idle, 0) / os.cpus().length;
        const avgCpuTotal = os.cpus().reduce((acc, cpu) => acc + Object.values(cpu.times).reduce((s, t) => s + t, 0), 0) / os.cpus().length;
        // This is a very rough system-wide CPU usage indicator, not Node process specific.
        // const cpuUsagePercent = this.lastCpuTimes ? (1 - (avgCpuIdle - this.lastCpuTimes.idle) / (avgCpuTotal - this.lastCpuTimes.total)) * 100 : 0;
        // this.lastCpuTimes = { idle: avgCpuIdle, total: avgCpuTotal };
        // this.systemMetrics.cpuUsage.add(cpuUsagePercent > 0 ? cpuUsagePercent : 0);

        // For a simpler approach, just log total/free memory
        const freeMemoryMB = Math.round(os.freemem() / (1024 * 1024));
        this.systemMetrics.freeMemoryMB.add(freeMemoryMB);

        const processMemory = process.memoryUsage();
        const heapUsedPercent = (processMemory.heapUsed / processMemory.heapTotal) * 100;

        // Active Handles (from process._getActiveHandles().length - undocumented, use with care or find alternative)
        if (typeof process._getActiveHandles === 'function') {
            this.systemMetrics.activeHandles.add(process._getActiveHandles().length);
        }

        this.emit('systemMetricsUpdate', { timestamp, freeMemoryMB, heapUsedPercent, activeHandles: this.systemMetrics.activeHandles.getAverage() });
        this.checkSystemAlerts({ heapUsedPercent, freeMemoryMB });
    }

    startEventLoopMonitoring(intervalMs = 5000, lagThresholdMs = 70) {
        if (this.eventLoopMonitor) this.eventLoopMonitor.disable(); // Disable existing if any

        // Perf hooks event loop utilization (ELU) is available in Node 16+
        if (performance.eventLoopUtilization) {
            let lastELU = performance.eventLoopUtilization();
            this.eventLoopMonitor = setInterval(() => {
                const elu = performance.eventLoopUtilization(lastELU);
                lastELU = performance.eventLoopUtilization(); // Update for next diff
                // elu.idle, elu.active, elu.utilization are available
                this.systemMetrics.eventLoopLagMs.add(elu.active); // 'active' time can be an indicator of busyness
                if (elu.active > this.thresholds.eventLoopLagMs) { // Or use elu.utilization
                    this._createAlert('high_event_loop_activity', 'warning',
                        `High event loop activity detected: ${elu.active.toFixed(2)}ms active time. Utilization: ${(elu.utilization * 100).toFixed(1)}%`,
                        { elu }
                    );
                }
            }, intervalMs);
             this.logger.info(`Event loop utilization monitoring started. Interval: ${intervalMs}ms`);
        } else {
            // Fallback to simple lag detection for older Node versions
            this.eventLoopMonitor = setInterval(() => {
                const start = performance.now();
                setImmediate(() => { // Should execute very quickly
                    const lag = performance.now() - start;
                    this.systemMetrics.eventLoopLagMs.add(lag);
                    if (lag > this.thresholds.eventLoopLagMs) {
                        this._createAlert('high_event_loop_lag', 'warning',
                            `High event loop lag detected: ${lag.toFixed(2)}ms`,
                            { lag }
                        );
                    }
                });
            }, intervalMs);
            this.logger.info(`Event loop simple lag monitoring started. Interval: ${intervalMs}ms`);
        }
    }


    checkSystemAlerts(currentSysMetrics) {
        if (currentSysMetrics.heapUsedPercent > this.thresholds.memoryUsagePercent) {
            this._createAlert('high_process_memory', 'warning',
                `Node.js process memory usage high: ${currentSysMetrics.heapUsedPercent.toFixed(1)}% of heap.`,
                { heapUsed: process.memoryUsage().heapUsed, heapTotal: process.memoryUsage().heapTotal }
            );
        }
        // Add CPU alert if a reliable process CPU metric is implemented
    }

    getMetricsSnapshot() {
        const endpointMetrics = Array.from(this.metrics.entries()).map(([key, data]) => {
            const { avgMemoryDeltaBytes, statusCodes, ...rest } = data; // Exclude MovingAverage object itself
            return {
                endpoint: key,
                ...rest,
                avgTimeMs: parseFloat(data.avgTimeMs.toFixed(2)),
                minTimeMs: data.minTimeMs === Infinity ? 0 : parseFloat(data.minTimeMs.toFixed(2)),
                maxTimeMs: parseFloat(data.maxTimeMs.toFixed(2)),
                errorRatePercent: data.count > 0 ? parseFloat(((data.errorCount / data.count) * 100).toFixed(2)) : 0,
                statusCodes: Object.fromEntries(data.statusCodes), // Convert Map to object
                avgMemoryDeltaBytes: parseFloat(data.avgMemoryDeltaBytes.getAverage().toFixed(0)),
            };
        });

        return {
            timestamp: new Date().toISOString(),
            overallSummary: this.generateOverallSummary(),
            endpointMetrics: endpointMetrics,
            system: {
                avgCpuUsagePercent: parseFloat(this.systemMetrics.cpuUsage.getAverage().toFixed(2)), // Note: current CPU is system-wide rough estimate
                avgFreeMemoryMB: parseFloat(this.systemMetrics.freeMemoryMB.getAverage().toFixed(0)),
                avgEventLoopLagMs: parseFloat(this.systemMetrics.eventLoopLagMs.getAverage().toFixed(2)),
                avgActiveHandles: parseFloat(this.systemMetrics.activeHandles.getAverage().toFixed(1)),
            },
            activeRequestCount: this.activeRequests.size,
            recentAlerts: this.alerts.slice(-20), // Last 20 alerts
        };
    }

    generateOverallSummary() {
        let totalRequests = 0, totalErrors = 0, sumOfAvgTimes = 0, weightedSumOfAvgTimes = 0;
        this.metrics.forEach(metric => {
            totalRequests += metric.count;
            totalErrors += metric.errorCount;
            sumOfAvgTimes += metric.avgTimeMs * metric.count; // Weighted average component
            weightedSumOfAvgTimes += metric.avgTimeMs * metric.count;

        });
        return {
            totalRequests,
            totalErrors,
            overallErrorRatePercent: totalRequests > 0 ? parseFloat(((totalErrors / totalRequests) * 100).toFixed(2)) : 0,
            averageResponseTimeMs: totalRequests > 0 ? parseFloat((sumOfAvgTimes / totalRequests).toFixed(2)) : 0,
            uptimeSeconds: Math.floor(process.uptime()),
            activeRequestCount: this.activeRequests.size,
        };
    }

    generateRequestId() { // Simple request ID generator
        return `req_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
    }

    stopMonitoring() {
        if (this.systemMonitorInterval) clearInterval(this.systemMonitorInterval);
        if (this.eventLoopMonitor) {
            // PerfObserver based one needs `eluMonitor.unobserve()` if that was used.
            // For setInterval based, clearInterval is enough.
            if (typeof this.eventLoopMonitor.unobserve === 'function') { // For PerformanceObserver
                 // eluMonitor.disconnect(); // if it were a PerformanceObserver instance
            } else { // For setInterval
                clearInterval(this.eventLoopMonitor);
            }
        }
        this.systemMonitorInterval = null;
        this.eventLoopMonitor = null;
        this.logger.info('PerformanceMonitor stopped.');
    }
}


// Export a single instance or the class depending on usage pattern
// For middleware, an instance is often convenient.
const performanceMonitorInstance = new PerformanceMonitor();

module.exports = {
    PerformanceMonitor, // Export class for potential extension or multiple instances
    performanceMonitorInstance, // Export singleton instance for direct use
    // Expose the trackRequest middleware directly
    trackRequestMiddleware: (req, res, next) => performanceMonitorInstance.trackRequest(req, res, next),
};

// The CacheManager, MemoryManager, RateLimiter from the prompt are good utilities
// but are separate concerns from this specific PerformanceMonitor middleware.
// They would typically be instantiated and used elsewhere in the application.
// For example, CacheManager might be used by service layers, RateLimiter by routing/auth.
// MemoryManager could be a standalone service initialized in app.js.

// If they were meant to be PART of PerformanceMonitor, they'd be instantiated in its constructor:
// this.cacheManager = new CacheManager();
// this.memoryManager = new MemoryManager(); this.memoryManager.startMonitoring();
// this.rateLimiter = new RateLimiter();
// And their stats could be included in getMetricsSnapshot().
// But for now, keeping PerformanceMonitor focused on request/system metrics.
