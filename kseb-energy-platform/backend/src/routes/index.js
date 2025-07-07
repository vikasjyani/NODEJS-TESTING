const express = require('express');
const router = express.Router();

// Import individual route handlers
const demandRoutes = require('./demand'); // Will be created in Chunk 2.1
const loadProfileRoutes = require('./loadProfile'); // Will be created in Chunk 2.2
const pypsaRoutes = require('./pypsa'); // Will be created in Chunk 2.3
// const projectRoutes = require('./project'); // Example for future project management
// const fileRoutes = require('./files'); // Example for future file uploads

// Mount the routes
router.use('/demand', demandRoutes);
router.use('/loadprofile', loadProfileRoutes);
router.use('/pypsa', pypsaRoutes);
// router.use('/projects', projectRoutes);
// router.use('/files', fileRoutes);

// Default API response for the root
router.get('/', (req, res) => {
    res.json({
        message: 'Welcome to KSEB Energy Futures Platform API',
        version: '1.0.0',
        documentation: '/api-docs' // Placeholder for API documentation
    });
});

// Fallback for unhandled API routes
router.use((req, res, next) => {
    const error = new Error('Not Found - API endpoint does not exist');
    error.statusCode = 404;
    next(error);
});

module.exports = router;
