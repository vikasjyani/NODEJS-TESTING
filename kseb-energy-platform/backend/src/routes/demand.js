const express = require('express');
const router = express.Router();
const demandController = require('../controllers/demandController');
// Assuming some form of authentication/authorization middleware might be added later
// const { isAuthenticated, authorizeRole } = require('../middleware/auth');

// GET /api/demand/sectors/:sector - Get historical data for a specific sector
router.get('/sectors/:sector', demandController.getSectorData.bind(demandController));

// POST /api/demand/forecast - Run a new demand forecast
// This could be a protected route in a real application
router.post('/forecast', demandController.runForecast.bind(demandController));

// GET /api/demand/forecast/:forecastId/status - Get the status of a specific forecast job
router.get('/forecast/:forecastId/status', demandController.getForecastStatus.bind(demandController));

// GET /api/demand/correlation/:sector - Get correlation data for variables in a sector
router.get('/correlation/:sector', demandController.getCorrelationData.bind(demandController));

// POST /api/demand/forecast/:forecastId/cancel - Cancel an ongoing forecast job
// This could be a protected route
router.post('/forecast/:forecastId/cancel', demandController.cancelForecast.bind(demandController));

// GET /api/demand/forecasts - List all active or recent forecast jobs (optional)
router.get('/forecasts', demandController.listForecastJobs.bind(demandController));


// Example of how you might add role-based authorization if needed:
// router.post('/forecast', isAuthenticated, authorizeRole(['admin', 'planner']), demandController.runForecast);

module.exports = router;
