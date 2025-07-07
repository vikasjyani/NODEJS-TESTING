const express = require('express');
const router = express.Router();
const pypsaController = require('../controllers/pypsaController');
// const { isAuthenticated, authorizeRole } = require('../middleware/auth'); // Optional auth

// POST /api/pypsa/optimize - Run a new PyPSA optimization
router.post('/optimize', pypsaController.runOptimization.bind(pypsaController));

// GET /api/pypsa/optimization/:jobId/status - Get status of an optimization job
router.get('/optimization/:jobId/status', pypsaController.getOptimizationStatus.bind(pypsaController));

// POST /api/pypsa/optimization/:jobId/cancel - Cancel an ongoing optimization job
router.post('/optimization/:jobId/cancel', pypsaController.cancelOptimization.bind(pypsaController));

// GET /api/pypsa/networks - Get list of available (completed) PyPSA networks/scenarios
router.get('/networks', pypsaController.getAvailableNetworks.bind(pypsaController));

// POST /api/pypsa/extract-results - Extract results from a specific network file path
// The request body should contain { networkPath: "path/to/network.nc" } or { scenarioName: "name" }
router.post('/extract-results', pypsaController.extractNetworkResults.bind(pypsaController));

// Analysis Endpoints for a specific network (identified by its path or scenario name)
// The :networkPath parameter should be URL-encoded if it contains special characters.
// It can be a scenario name which the controller resolves to a path, or a direct (validated) path.

// GET /api/pypsa/analysis/:networkPath/dispatch - Get dispatch data
router.get('/analysis/:networkPath/dispatch', pypsaController.getDispatchData.bind(pypsaController));

// GET /api/pypsa/analysis/:networkPath/capacity - Get capacity data
router.get('/analysis/:networkPath/capacity', pypsaController.getCapacityData.bind(pypsaController));

// GET /api/pypsa/analysis/:networkPath/storage - Get storage operation data
router.get('/analysis/:networkPath/storage', pypsaController.getStorageData.bind(pypsaController));

// GET /api/pypsa/analysis/:networkPath/emissions - Get emissions data
router.get('/analysis/:networkPath/emissions', pypsaController.getEmissionsData.bind(pypsaController));

// GET /api/pypsa/analysis/:networkPath/info - Get general network information
router.get('/analysis/:networkPath/info', pypsaController.getNetworkInfo.bind(pypsaController));

// POST /api/pypsa/compare-networks - Compare results from multiple networks
// Request body: { networkPaths: ["path1", "path2"], metrics: ["metric1", "metric2"] }
router.post('/compare-networks', pypsaController.compareNetworks.bind(pypsaController));


module.exports = router;
