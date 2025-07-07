const winston = require('winston');
const path = require('path');

// Determine log directory
const logDir = path.join(__dirname, '../../logs'); // Store logs in backend/logs

// Define log format
const logFormat = winston.format.combine(
    winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
    winston.format.errors({ stack: true }), // Log stack traces
    winston.format.splat(),
    winston.format.json()
);

// Create logger instance
const logger = winston.createLogger({
    level: process.env.LOG_LEVEL || (process.env.NODE_ENV === 'production' ? 'warn' : 'info'),
    format: logFormat,
    defaultMeta: { service: 'kseb-backend' },
    transports: [
        // Console transport (for development and general output)
        new winston.transports.Console({
            format: winston.format.combine(
                winston.format.colorize(),
                winston.format.printf(
                    info => `${info.timestamp} ${info.level}: ${info.message}` + (info.stack ? `\n${info.stack}` : '')
                )
            ),
            level: process.env.NODE_ENV === 'production' ? 'info' : 'debug', // More verbose in dev
        }),
        // File transport for errors
        new winston.transports.File({
            filename: path.join(logDir, 'error.log'),
            level: 'error',
            maxsize: 5242880, // 5MB
            maxFiles: 5,
            tailable: true,
        }),
        // File transport for all logs
        new winston.transports.File({
            filename: path.join(logDir, 'combined.log'),
            maxsize: 5242880, // 5MB
            maxFiles: 5,
            tailable: true,
        }),
    ],
    exceptionHandlers: [
        new winston.transports.File({ filename: path.join(logDir, 'exceptions.log') })
    ],
    rejectionHandlers: [
        new winston.transports.File({ filename: path.join(logDir, 'rejections.log') })
    ],
    exitOnError: false, // Do not exit on handled exceptions
});

// Stream for Morgan (HTTP request logger) if used
logger.stream = {
    write: function(message, encoding) {
        logger.info(message.trim());
    },
};

module.exports = { logger };
