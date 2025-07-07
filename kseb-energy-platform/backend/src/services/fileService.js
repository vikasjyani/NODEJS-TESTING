const fs = require('fs').promises;
const path = require('path');
const { logger } = require('../utils/logger');

class FileService {
    constructor() {
        // Base directory for storing files, can be configured via environment variable
        this.baseStoragePath = process.env.STORAGE_PATH || path.join(process.cwd(), 'storage');
        this._ensureBaseDirExists();
    }

    async _ensureBaseDirExists() {
        try {
            await fs.mkdir(this.baseStoragePath, { recursive: true });
            logger.info(`Base storage directory ensured at: ${this.baseStoragePath}`);
        } catch (error) {
            logger.error(`Failed to create base storage directory at ${this.baseStoragePath}:`, error);
            // Depending on the app's needs, this could be a fatal error
        }
    }

    /**
     * Resolves a relative path to an absolute path within the base storage directory.
     * Protects against directory traversal.
     * @param {string} relativePath - The relative path from the base storage directory.
     * @returns {string} The resolved absolute path.
     * @throws {Error} If the path attempts to escape the base directory.
     */
    _resolvePath(relativePath) {
        const absolutePath = path.resolve(this.baseStoragePath, relativePath);
        if (!absolutePath.startsWith(this.baseStoragePath)) {
            logger.warn(`Attempted directory traversal: ${relativePath}`);
            throw new Error('Invalid file path: Access denied.');
        }
        return absolutePath;
    }

    /**
     * Saves a file to a specified path within the storage.
     * @param {string} relativePath - Relative path where the file should be saved (e.g., 'user_uploads/data.csv').
     * @param {Buffer|string} content - The content to save.
     * @param {object} [options={}] - fs.writeFile options.
     * @returns {Promise<string>} The full path to the saved file.
     */
    async saveFile(relativePath, content, options = {}) {
        const filePath = this._resolvePath(relativePath);
        try {
            await fs.mkdir(path.dirname(filePath), { recursive: true }); // Ensure directory exists
            await fs.writeFile(filePath, content, options);
            logger.info(`File saved successfully: ${filePath}`);
            return filePath;
        } catch (error) {
            logger.error(`Error saving file to ${filePath}: ${error.message}`);
            throw error; // Re-throw to be handled by the caller
        }
    }

    /**
     * Reads a file from the specified path within the storage.
     * @param {string} relativePath - Relative path of the file to read.
     * @param {object|string} [options='utf8'] - fs.readFile options or encoding.
     * @returns {Promise<Buffer|string>} The file content.
     */
    async readFile(relativePath, options = 'utf8') {
        const filePath = this._resolvePath(relativePath);
        try {
            const content = await fs.readFile(filePath, options);
            logger.debug(`File read successfully: ${filePath}`);
            return content;
        } catch (error) {
            logger.error(`Error reading file from ${filePath}: ${error.message}`);
            if (error.code === 'ENOENT') {
                throw new Error(`File not found: ${relativePath}`);
            }
            throw error;
        }
    }

    /**
     * Reads and parses a JSON file.
     * @param {string} relativePath - Relative path of the JSON file.
     * @returns {Promise<object>} The parsed JSON object.
     */
    async readJsonFile(relativePath) {
        const jsonString = await this.readFile(relativePath, 'utf8');
        try {
            return JSON.parse(jsonString);
        } catch (error) {
            logger.error(`Error parsing JSON file ${relativePath}: ${error.message}`);
            throw new Error(`Invalid JSON content in file: ${relativePath}`);
        }
    }

    /**
     * Saves an object as a JSON file.
     * @param {string} relativePath - Relative path to save the JSON file.
     * @param {object} data - The object to save.
     * @returns {Promise<string>} The full path to the saved file.
     */
    async saveJsonFile(relativePath, data) {
        try {
            const jsonString = JSON.stringify(data, null, 2); // Pretty print with 2 spaces
            return await this.saveFile(relativePath, jsonString, 'utf8');
        } catch (error) {
            logger.error(`Error serializing data to JSON for ${relativePath}: ${error.message}`);
            throw error;
        }
    }


    /**
     * Deletes a file from the specified path.
     * @param {string} relativePath - Relative path of the file to delete.
     * @returns {Promise<void>}
     */
    async deleteFile(relativePath) {
        const filePath = this._resolvePath(relativePath);
        try {
            await fs.unlink(filePath);
            logger.info(`File deleted successfully: ${filePath}`);
        } catch (error) {
            logger.error(`Error deleting file ${filePath}: ${error.message}`);
            if (error.code === 'ENOENT') {
                // Optionally, consider it success if file doesn't exist (idempotent delete)
                logger.warn(`Attempted to delete non-existent file: ${filePath}`);
                // throw new Error(`File not found for deletion: ${relativePath}`);
                return; // Or resolve if non-existence is acceptable
            }
            throw error;
        }
    }

    /**
     * Checks if a file or directory exists.
     * @param {string} relativePath - Relative path to check.
     * @returns {Promise<boolean>} True if exists, false otherwise.
     */
    async pathExists(relativePath) {
        const filePath = this._resolvePath(relativePath);
        try {
            await fs.access(filePath);
            return true;
        } catch {
            return false;
        }
    }

    /**
     * Creates a directory.
     * @param {string} relativePath - Relative path of the directory to create.
     * @returns {Promise<void>}
     */
    async createDirectory(relativePath) {
        const dirPath = this._resolvePath(relativePath);
        try {
            await fs.mkdir(dirPath, { recursive: true });
            logger.info(`Directory created (or already exists): ${dirPath}`);
        } catch (error) {
            logger.error(`Error creating directory ${dirPath}: ${error.message}`);
            throw error;
        }
    }

    /**
     * Lists files and directories in a given path.
     * @param {string} relativePath - Relative path of the directory to list.
     * @returns {Promise<string[]>} Array of file/directory names.
     */
    async listDirectory(relativePath) {
        const dirPath = this._resolvePath(relativePath);
        try {
            const entries = await fs.readdir(dirPath);
            return entries;
        } catch (error) {
            logger.error(`Error listing directory ${dirPath}: ${error.message}`);
            if (error.code === 'ENOENT') {
                throw new Error(`Directory not found: ${relativePath}`);
            }
            throw error;
        }
    }
}

// Export a singleton instance
module.exports = {
    fileService: new FileService()
};
