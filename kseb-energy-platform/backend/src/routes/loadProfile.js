const express = require('express');
const router = express.Router();
const loadProfileController = require('../controllers/loadProfileController');
// const { isAuthenticated, authorizeRole } = require('../middleware/auth'); // Optional auth

// POST /api/loadprofile/generate - Generate a new load profile
router.post('/generate', loadProfileController.generateProfile.bind(loadProfileController));

// GET /api/loadprofile/jobs/:profileJobId/status - Get status of a generation job
router.get('/jobs/:profileJobId/status', loadProfileController.getGenerationStatus.bind(loadProfileController));

// GET /api/loadprofile/profiles - Get list of saved/generated profiles (metadata)
router.get('/profiles', loadProfileController.getSavedProfiles.bind(loadProfileController));

// GET /api/loadprofile/profiles/:profileId - Get detailed data for a specific profile
router.get('/profiles/:profileId', loadProfileController.getProfileData.bind(loadProfileController));

// GET /api/loadprofile/analyze/:profileId - Perform analysis on a profile
router.get('/analyze/:profileId', loadProfileController.analyzeProfile.bind(loadProfileController));

// DELETE /api/loadprofile/profiles/:profileId - Delete a saved profile
router.delete('/profiles/:profileId', loadProfileController.deleteProfile.bind(loadProfileController));

// POST /api/loadprofile/compare - Compare multiple profiles
router.post('/compare', loadProfileController.compareProfiles.bind(loadProfileController));

module.exports = router;
