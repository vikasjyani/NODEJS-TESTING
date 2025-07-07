const winston = require('winston'); // Assuming logger is Winston-based as per plan

// Basic logger configuration if not already set up in utils/logger.js
// This is a fallback, ideally logger.js handles this.
let logger;
try {
    logger = require('../utils/logger').logger;
} catch (e) {
    logger = winston.createLogger({
        level: 'info',
        format: winston.format.json(),
        transports: [
            new winston.transports.Console({
                format: winston.format.simple(),
            }),
        ],
    });
    logger.warn("Falling back to basic logger in errorHandler.js. Ensure utils/logger.js is correctly configured.");
}

const errorHandler = (err, req, res, next) => {
    const statusCode = err.statusCode || 500;
    const message = err.message || 'Internal Server Error';

    // Log the error
    logger.error(`${statusCode} - ${message} - ${req.originalUrl} - ${req.method} - ${req.ip}`, {
        stack: err.stack,
        requestBody: req.body,
        requestParams: req.params,
        requestQuery: req.query,
    });

    // Construct error response
    const errorResponse = {
        success: false,
        status: statusCode,
        message: message,
    };

    // Include stack trace in development
    if (process.env.NODE_ENV === 'development' || process.env.NODE_ENV === 'test') {
        errorResponse.stack = err.stack;
    }

    // Specific error handling (can be expanded)
    if (err.name === 'ValidationError') { // Example for Mongoose or Joi validation
        errorResponse.status = 400;
        errorResponse.details = err.details || {};
    } else if (err.name === 'UnauthorizedError') { // Example for JWT errors
        errorResponse.status = 401;
        errorResponse.message = 'Unauthorized';
    } else if (err.code === 'LIMIT_FILE_SIZE') { // Example for Multer file size limit
        errorResponse.status = 400;
        errorResponse.message = 'File too large';
    }


    res.status(errorResponse.status).json(errorResponse);
};

module.exports = { errorHandler };
