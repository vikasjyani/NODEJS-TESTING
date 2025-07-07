const { logger } = require('../utils/logger');

// Simple in-memory cache implementation
// For production, consider using Redis or Memcached

class InMemoryCache {
    constructor() {
        this.cache = new Map();
        this.ttlMap = new Map(); // Stores Time-To-Live for cache entries
        logger.info('In-memory cache service initialized.');

        // Optional: Periodically clean up expired keys
        // setInterval(() => this.cleanupExpired(), 60 * 1000); // Clean up every minute
    }

    /**
     * Get a value from the cache.
     * @param {string} key - The cache key.
     * @returns {Promise<any|null>} - The cached value or null if not found or expired.
     */
    async get(key) {
        if (this.ttlMap.has(key) && this.ttlMap.get(key) < Date.now()) {
            // Key has expired
            logger.debug(`Cache expired for key: ${key}`);
            this.cache.delete(key);
            this.ttlMap.delete(key);
            return null;
        }
        const value = this.cache.get(key);
        if (value !== undefined) {
            logger.debug(`Cache hit for key: ${key}`);
            return Promise.resolve(JSON.parse(JSON.stringify(value))); // Return a copy to prevent mutation
        }
        logger.debug(`Cache miss for key: ${key}`);
        return Promise.resolve(null);
    }

    /**
     * Set a value in the cache with an optional TTL.
     * @param {string} key - The cache key.
     * @param {any} value - The value to cache.
     * @param {number} [ttlSeconds=300] - Optional Time-To-Live in seconds. Defaults to 5 minutes.
     * @returns {Promise<void>}
     */
    async set(key, value, ttlSeconds = 300) {
        if (typeof key !== 'string' || key.trim() === '') {
            logger.error('Cache key must be a non-empty string.');
            return Promise.reject(new Error('Invalid cache key.'));
        }
        try {
            // Store a copy to prevent external mutations affecting the cache
            const storedValue = JSON.parse(JSON.stringify(value));
            this.cache.set(key, storedValue);
            if (ttlSeconds > 0) {
                this.ttlMap.set(key, Date.now() + ttlSeconds * 1000);
            }
            logger.debug(`Cache set for key: ${key} with TTL: ${ttlSeconds}s`);
            return Promise.resolve();
        } catch (error) {
            logger.error(`Error setting cache for key ${key}: ${error.message}. Value not serializable?`);
            return Promise.reject(error);
        }
    }

    /**
     * Delete a value from the cache.
     * @param {string} key - The cache key.
     * @returns {Promise<void>}
     */
    async del(key) {
        this.cache.delete(key);
        this.ttlMap.delete(key);
        logger.debug(`Cache deleted for key: ${key}`);
        return Promise.resolve();
    }

    /**
     * Clear the entire cache.
     * @returns {Promise<void>}
     */
    async flush() {
        this.cache.clear();
        this.ttlMap.clear();
        logger.info('In-memory cache flushed.');
        return Promise.resolve();
    }

    /**
     * Get all keys currently in the cache (excluding expired ones).
     * @returns {Promise<string[]>}
     */
    async keys() {
        const now = Date.now();
        const validKeys = [];
        for (const key of this.cache.keys()) {
            if (!this.ttlMap.has(key) || this.ttlMap.get(key) >= now) {
                validKeys.push(key);
            }
        }
        return Promise.resolve(validKeys);
    }

    /**
     * Clean up expired cache entries.
     */
    cleanupExpired() {
        const now = Date.now();
        let cleanedCount = 0;
        for (const [key, expiryTime] of this.ttlMap.entries()) {
            if (expiryTime < now) {
                this.cache.delete(key);
                this.ttlMap.delete(key);
                cleanedCount++;
            }
        }
        if (cleanedCount > 0) {
            logger.info(`Cache cleanup: Removed ${cleanedCount} expired entries.`);
        }
    }
}

const cacheInstance = new InMemoryCache();

module.exports = {
    cacheGet: (key) => cacheInstance.get(key),
    cacheSet: (key, value, ttlSeconds) => cacheInstance.set(key, value, ttlSeconds),
    cacheDel: (key) => cacheInstance.del(key),
    cacheFlush: () => cacheInstance.flush(),
    cacheKeys: () => cacheInstance.keys(),
    cacheInstance // Export instance if direct access is needed elsewhere
};
