const rateLimit = require('express-rate-limit');
const helmet = require('helmet');
const cors = require('cors');
const validator = require('validator'); // For input validation/sanitization
const crypto = require('crypto'); // For generating request IDs or other crypto needs
const path = require('path'); // For path validation
const { logger } = require('../utils/logger');


// --- Rate Limiting Configurations ---
const createRateLimiter = (windowMs, max, message, keyGenerator = (req) => req.ip) => {
  return rateLimit({
    windowMs,
    max, // Max requests per windowMs per key
    message: { success: false, error: message || 'Too many requests, please try again later.' },
    standardHeaders: true, // Return rate limit info in the `RateLimit-*` headers
    legacyHeaders: false, // Disable the `X-RateLimit-*` headers
    keyGenerator, // Use IP address as the default key
    handler: (req, res, next, options) => {
      logger.warn(`Rate limit exceeded for IP ${req.ip} on ${req.method} ${req.originalUrl}. Message: ${options.message.error}`);
      res.status(options.statusCode).json(options.message);
    }
  });
};

// Define different rate limiters for various parts of the API
const rateLimiters = {
  // Stricter limit for authentication attempts
  authLimiter: createRateLimiter(15 * 60 * 1000, 10, 'Too many authentication attempts from this IP, please try again after 15 minutes.'),
  // General API limiter for most endpoints
  apiLimiter: createRateLimiter(15 * 60 * 1000, 200, 'Too many requests from this IP, please try again after 15 minutes.'),
  // Stricter limiter for computationally expensive tasks or sensitive data modification
  sensitiveOperationLimiter: createRateLimiter(60 * 60 * 1000, 20, 'Too many sensitive operations from this IP, please try again after an hour.'),
  // File upload limiter
  fileUploadLimiter: createRateLimiter(60 * 60 * 1000, 50, 'Too many file uploads from this IP, please try again after an hour.')
};


// --- Input Sanitization Middleware ---
// Basic sanitizer, can be expanded or replaced with more robust libraries like DOMPurify for HTML or dedicated sanitizers.
const sanitizeInput = (req, res, next) => {
  const sanitizeValue = (value) => {
    if (typeof value === 'string') {
      // validator.escape replaces <, >, &, ', " and / with HTML entities.
      // Consider also validator.trim()
      return validator.escape(validator.trim(value));
    } else if (Array.isArray(value)) {
      return value.map(sanitizeValue);
    } else if (typeof value === 'object' && value !== null) {
      const sanitizedObject = {};
      for (const key in value) {
        if (Object.prototype.hasOwnProperty.call(value, key)) {
          sanitizedObject[key] = sanitizeValue(value[key]);
        }
      }
      return sanitizedObject;
    }
    return value; // Return non-string, non-array, non-object values as is
  };

  if (req.body) req.body = sanitizeValue(req.body);
  if (req.query) req.query = sanitizeValue(req.query);
  if (req.params) req.params = sanitizeValue(req.params); // Path params are often numbers or specific strings, but good to sanitize if dynamic

  next();
};


// --- File Upload Validation Middleware (Basic) ---
// This is a conceptual placeholder. Actual file upload handling (e.g., with multer)
// would have its own validation mechanisms for file types, sizes, etc.
const validateFileUpload = (options = {}) => {
    const {
        allowedMimeTypes = [
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // .xlsx
            'application/vnd.ms-excel', // .xls
            'text/csv', // .csv
            'application/json', // .json
            'application/zip', // .zip (for project import/export perhaps)
            'application/x-netcdf', // .nc for PyPSA
        ],
        maxFileSizeMb = 16, // Default 16MB
    } = options;
    const MAX_SIZE_BYTES = maxFileSizeMb * 1024 * 1024;

    return (req, res, next) => {
        if (!req.file && (!req.files || Object.keys(req.files).length === 0)) {
            return next(); // No files to validate
        }

        const filesToValidate = req.files ? Object.values(req.files).flat() : [req.file];

        for (const file of filesToValidate) {
            if (!file) continue;

            if (!allowedMimeTypes.includes(file.mimetype)) {
                logger.warn(`Invalid file type uploaded: ${file.mimetype} for ${file.originalname} by ${req.ip}`);
                return res.status(400).json({ success: false, error: `Invalid file type: ${file.mimetype}. Allowed: ${allowedMimeTypes.join(', ')}` });
            }

            if (file.size > MAX_SIZE_BYTES) {
                logger.warn(`File too large: ${file.originalname} (${file.size} bytes) by ${req.ip}`);
                return res.status(400).json({ success: false, error: `File too large. Maximum size is ${maxFileSizeMb}MB.` });
            }

            // Validate filename characters (simple example, can be more restrictive)
            if (!/^[a-zA-Z0-9_.\-()\s]+$/.test(file.originalname) || file.originalname.length > 255) {
                logger.warn(`Invalid filename: ${file.originalname} by ${req.ip}`);
                return res.status(400).json({ success: false, error: 'Invalid filename: Contains disallowed characters or is too long.' });
            }
        }
        next();
    };
};


// --- Path Traversal Protection Middleware ---
// Checks common request parts for path traversal attempts.
const protectPathTraversal = (req, res, next) => {
  const checkPath = (value, source) => {
    if (typeof value === 'string') {
      // Decode URI components first to catch encoded traversal attempts
      const decodedValue = decodeURIComponent(value);
      // Normalize path to resolve segments like '.' and '..'
      const normalizedPath = path.normalize(decodedValue);
      // If normalized path starts with '..' or an absolute path (on Unix-like), it's suspicious
      // On Windows, also check for backslashes and drive letters if not expected
      if (normalizedPath.includes('..') || (path.isAbsolute(normalizedPath) && !normalizedPath.startsWith(process.cwd()))) { // Be careful with cwd check logic
        logger.warn(`Path traversal attempt detected in ${source}: '${value}' (normalized: '${normalizedPath}') from IP ${req.ip}`);
        return res.status(400).json({ success: false, error: 'Invalid path parameter detected.' });
      }
    }
    return null; // No issue
  };

  const sources = [
    { name: 'params', data: req.params },
    { name: 'query', data: req.query },
    { name: 'body', data: req.body }
  ];

  for (const source of sources) {
    if (source.data && typeof source.data === 'object') {
      for (const key in source.data) {
        const errResponse = checkPath(source.data[key], `${source.name}.${key}`);
        if (errResponse) return errResponse; // checkPath returns response if error
      }
    }
  }
  next();
};


// --- Request ID Middleware ---
// Generates a unique ID for each request, useful for logging and tracing.
const assignRequestId = (req, res, next) => {
  // Use existing X-Request-ID header if present (e.g., from load balancer), otherwise generate one.
  const existingId = req.get('X-Request-ID');
  req.requestId = existingId || crypto.randomBytes(12).toString('hex'); // Shorter ID for logging
  res.setHeader('X-Request-ID', req.requestId);
  next();
};


// --- Helmet Security Headers Configuration ---
// Provides various security headers to protect against common web vulnerabilities.
const helmetConfig = helmet({
  contentSecurityPolicy: { // Define a Content Security Policy
    directives: {
      defaultSrc: ["'self'"], // Only allow resources from own origin by default
      scriptSrc: ["'self'"], // Add other trusted script sources if needed, e.g. CDNs for client libraries
      styleSrc: ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"], // Allow inline styles and Google Fonts
      imgSrc: ["'self'", "data:"], // Allow images from self and data URIs
      fontSrc: ["'self'", "https://fonts.gstatic.com"], // Allow fonts from self and Google Fonts
      connectSrc: ["'self'", "ws://localhost:5000", "wss://localhost:5000"], // Allow connections to self, and WS for Socket.IO (adjust ports/domains for prod)
      frameAncestors: ["'none'"], // Disallow embedding in iframes from other origins
      objectSrc: ["'none'"], // Disallow <object>, <embed>, <applet>
      upgradeInsecureRequests: [], // In production, you'd likely enable this with HTTPS
    },
  },
  crossOriginEmbedderPolicy: false, // Set to true if you don't need to embed cross-origin resources
  crossOriginOpenerPolicy: { policy: "same-origin-allow-popups" },
  crossOriginResourcePolicy: { policy: "same-origin" },
  dnsPrefetchControl: { allow: false },
  frameguard: { action: 'deny' }, // Equivalent to X-Frame-Options: DENY
  hsts: { maxAge: 60 * 60 * 24 * 365, includeSubDomains: true, preload: true }, // 1 year HSTS (use only with HTTPS)
  ieNoOpen: true,
  noSniff: true,
  originAgentCluster: true,
  permittedCrossDomainPolicies: { permittedPolicies: "none" },
  referrerPolicy: { policy: "no-referrer" }, // Stricter referrer policy
  xssFilter: false, // Deprecated, rely on CSP. Helmet sets X-XSS-Protection: 0
});

// --- CORS Configuration ---
// Configures Cross-Origin Resource Sharing.
const productionFrontendUrl = process.env.FRONTEND_URL || 'https://your-production-frontend.com'; // Replace with actual URL
const developmentOrigins = ['http://localhost:3000', 'http://127.0.0.1:3000']; // React dev server
if (process.env.ELECTRON_APP === 'true' && isDevElectron()) { // isDevElectron() would be a helper
    // Allow any file:// origin if it's an Electron app in development for ease of use.
    // THIS IS POTENTIALLY INSECURE if not handled carefully.
    // A better way for Electron is to serve frontend from a local http server (even in dev)
    // or use custom protocol and ensure it's validated.
    // For now, we'll allow file:// in dev Electron mode.
    // developmentOrigins.push('file://'); // Be very cautious with this.
}


const corsOptions = {
  origin: (origin, callback) => {
    // Allow requests with no origin (like mobile apps or curl requests) if desired
    // if (!origin) return callback(null, true);

    const allowedOrigins = process.env.NODE_ENV === 'production'
        ? [productionFrontendUrl]
        : developmentOrigins;

    if (allowedOrigins.includes(origin) || !origin /* allow no origin for tools like Postman in dev */) {
      callback(null, true);
    } else {
      logger.warn(`CORS: Blocked origin - ${origin}`);
      callback(new Error('Not allowed by CORS'));
    }
  },
  credentials: true, // Allow cookies/authorization headers
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-Request-ID', 'X-CSRF-Token'], // Add any custom headers
  optionsSuccessStatus: 204, // For pre-flight requests
};

function isDevElectron() {
    // A simple check. More robust might involve checking main process env vars.
    return process.env.ELECTRON_APP === 'true' && process.env.NODE_ENV !== 'production';
}


module.exports = {
  rateLimiters,
  sanitizeInput,
  validateFileUpload, // This is a function that returns middleware, call as validateFileUpload({options})
  protectPathTraversal,
  assignRequestId,
  helmetConfig, // This is the helmet middleware itself
  configuredCors: cors(corsOptions), // This is the cors middleware itself
};

// Example usage in app.js:
// const securityMiddleware = require('./middleware/security');
// app.use(securityMiddleware.assignRequestId);
// app.use(securityMiddleware.helmetConfig);
// app.use(securityMiddleware.configuredCors);
// app.use(express.json()); // Body parser after CORS, before sanitizers
// app.use(express.urlencoded({ extended: true }));
// app.use(securityMiddleware.sanitizeInput); // Sanitize after parsing
// app.use(securityMiddleware.protectPathTraversal);
//
// app.post('/login', securityMiddleware.rateLimiters.authLimiter, authController.login);
// app.use('/api', securityMiddleware.rateLimiters.apiLimiter, apiRoutes);
// app.post('/upload', securityMiddleware.validateFileUpload({maxFileSizeMb: 20}), uploadController.handleUpload);
