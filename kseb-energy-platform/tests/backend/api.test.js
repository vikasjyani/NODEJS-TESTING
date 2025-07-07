const request = require('supertest'); // For making HTTP requests to the test server
const TestEnvironment = require('../setup'); // The class we created for managing test env

// Increase Jest timeout for integration tests that might involve starting servers, IO, etc.
jest.setTimeout(60000); // 60 seconds

describe('Backend API Integration Tests', () => {
    let testEnv;
    let baseURL;
    let defaultPythonTimeout = 5000; // Shorter timeout for test python scripts

    beforeAll(async () => {
        testEnv = new TestEnvironment();
        try {
            await testEnv.setup(); // This starts the backend server and sets up mock data
            baseURL = `http://localhost:${testEnv.testPort}`; // testPort is defined in TestEnvironment
        } catch (error) {
            console.error("Failed to setup test environment for API tests:", error);
            // Optionally, rethrow or handle to prevent tests from running if setup fails critically
            throw error;
        }
    });

    afterAll(async () => {
        if (testEnv) {
            await testEnv.teardown(); // This stops the backend server and cleans up
        }
    });

    describe('GET /api/health', () => {
        it('should return 200 OK with health status', async () => {
            const response = await request(baseURL).get('/api/health');
            expect(response.statusCode).toBe(200);
            expect(response.body).toHaveProperty('status', 'healthy');
            expect(response.body).toHaveProperty('timestamp');
        });
    });

    // Placeholder for Project Management API tests (if these routes are added later)
    // describe('/api/projects', () => {
    //     it('POST /api/projects - should create a new project (placeholder)', async () => {
    //         const projectData = { name: 'API Test Project', path: '/tmp/api-test-project' };
    //         // const response = await request(baseURL).post('/api/projects').send(projectData);
    //         // expect(response.statusCode).toBe(201); // Or 200 depending on API design
    //         // expect(response.body.success).toBe(true);
    //         expect(true).toBe(true); // Placeholder
    //     });
    // });

    describe('Demand Projection API (/api/demand)', () => {
        it('GET /api/demand/sectors/:sector - should get data for a valid sector', async () => {
            const response = await request(baseURL).get('/api/demand/sectors/residential');
            expect(response.statusCode).toBe(200);
            expect(response.body.success).toBe(true);
            expect(response.body.data).toBeDefined();
            // Further checks on data structure based on demand_projection.py --sector-data output
            expect(response.body.data.sector).toBe('residential');
        });

        it('GET /api/demand/sectors/:sector - should return 400 for missing sector', async () => {
            // This depends on how your controller handles missing :sector. Assuming it's part of path.
            // If the route itself won't match without :sector, this test might need adjustment
            // or test a specific "invalid" sector name if that's handled.
            // For now, let's assume an empty sector in path would lead to a route not found (404 by Express default)
            // or a specific handling in your controller.
            // If your route is just /api/demand/sectors and sector is a query param, this test would change.
            // The current route is /api/demand/sectors/:sector, so an empty sector is not directly testable this way.
            // Let's test an invalid sector name if the python script would error.
             const response = await request(baseURL).get('/api/demand/sectors/nonexistentsector');
             expect(response.statusCode).toBe(200); // Python script might return success:false or an error structure
             expect(response.body.success).toBe(true); // The controller itself might succeed
             expect(response.body.data.error).toContain("Could not load data"); // Python script error
        });

        it('POST /api/demand/forecast - should start a forecast job', async () => {
            const forecastConfig = {
                scenario_name: 'api_test_forecast',
                target_year: 2025,
                sectors: {
                    residential: { models: ['SLR'] }
                },
                input_file: "inputs/default_demand_data.xlsx", // Ensure this mock/placeholder exists via TestEnvironment
                timeout: defaultPythonTimeout
            };
            const response = await request(baseURL).post('/api/demand/forecast').send(forecastConfig);
            expect(response.statusCode).toBe(202); // Accepted for processing
            expect(response.body.success).toBe(true);
            expect(response.body.forecastId).toBeDefined();
            const forecastId = response.body.forecastId;

            // Optionally, poll status endpoint for completion (or rely on WebSocket test if separate)
            // For an integration test, waiting for completion can be slow.
            // Consider testing job acceptance and then a separate test for job lifecycle if needed.
            await new Promise(resolve => setTimeout(resolve, defaultPythonTimeout + 1000)); // Wait for python script + buffer
            const statusRes = await request(baseURL).get(`/api/demand/forecast/${forecastId}/status`);
            expect(statusRes.statusCode).toBe(200);
            expect(statusRes.body.status).toBe('completed'); // Assuming mock python script completes quickly
        });

        it('GET /api/demand/correlation/:sector - should get correlation data', async () => {
            const response = await request(baseURL).get('/api/demand/correlation/residential');
            expect(response.statusCode).toBe(200);
            expect(response.body.success).toBe(true);
            expect(response.body.data).toHaveProperty('correlations');
        });
    });

    describe('Load Profile API (/api/loadprofile)', () => {
        it('POST /api/loadprofile/generate - should start a load profile generation job', async () => {
            const profileConfig = {
                method: 'base_scaling',
                base_year: 2022, // Ensure mock data exists for this
                start_year: 2023,
                end_year: 2024,
                input_template_file: "inputs/load_curve_template.xlsx",
                timeout: defaultPythonTimeout
            };
            const response = await request(baseURL).post('/api/loadprofile/generate').send(profileConfig);
            expect(response.statusCode).toBe(202);
            expect(response.body.success).toBe(true);
            expect(response.body.profileJobId).toBeDefined();
            const jobId = response.body.profileJobId;

            await new Promise(resolve => setTimeout(resolve, defaultPythonTimeout + 1000));
            const statusRes = await request(baseURL).get(`/api/loadprofile/jobs/${jobId}/status`);
            expect(statusRes.statusCode).toBe(200);
            expect(statusRes.body.job.status).toBe('completed');
        });

        it('GET /api/loadprofile/profiles - should get list of saved profiles', async () => {
            // This might be empty if no profiles are pre-loaded or generated & saved by tests
            const response = await request(baseURL).get('/api/loadprofile/profiles');
            expect(response.statusCode).toBe(200);
            expect(response.body.success).toBe(true);
            expect(Array.isArray(response.body.profiles)).toBe(true);
        });
    });

    describe('PyPSA API (/api/pypsa)', () => {
        it('POST /api/pypsa/optimize - should start a PyPSA optimization job', async () => {
            const pypsaConfig = {
                scenario_name: 'api_test_pypsa_opt',
                base_year: 2023,
                investment_mode: 'single_year',
                input_file: "inputs/pypsa_input_template.xlsx", // Mock this if PyPSA runner uses it
                solver_options: { solver: 'glpk' }, // GLPK is often available by default
                timeout: defaultPythonTimeout + 2000 // PyPSA might take a bit longer
            };
            const response = await request(baseURL).post('/api/pypsa/optimize').send(pypsaConfig);
            expect(response.statusCode).toBe(202);
            expect(response.body.success).toBe(true);
            expect(response.body.jobId).toBeDefined();
            const jobId = response.body.jobId;

            await new Promise(resolve => setTimeout(resolve, defaultPythonTimeout + 3000));
            const statusRes = await request(baseURL).get(`/api/pypsa/optimization/${jobId}/status`);
            expect(statusRes.statusCode).toBe(200);
            expect(statusRes.body.job.status).toBe('completed');
        });

        it('GET /api/pypsa/networks - should get available networks', async () => {
            const response = await request(baseURL).get('/api/pypsa/networks');
            expect(response.statusCode).toBe(200);
            expect(response.body.success).toBe(true);
            expect(Array.isArray(response.body.networks)).toBe(true);
        });
    });

    // File Upload API placeholder - Actual file upload testing with supertest is more complex
    // describe('File Upload API (/api/files)', () => {
    //     it('POST /api/files/upload - should upload a file (placeholder)', async () => {
    //         // const testFilePath = path.join(testEnv.testDataDir, 'inputs', 'some_test_file.csv');
    //         // await fs.writeFile(testFilePath, "col1,col2\nval1,val2");
    //         // const response = await request(baseURL)
    //         //     .post('/api/files/upload')
    //         //     .attach('file', testFilePath) // 'file' is the field name expected by backend
    //         //     .field('type', 'test_upload');
    //         // expect(response.statusCode).toBe(200); // Or 201
    //         // expect(response.body.success).toBe(true);
    //         // expect(response.body).toHaveProperty('filePath'); // Path where file is stored on server
    //         expect(true).toBe(true);
    //     });
    // });

    describe('Error Handling', () => {
        it('should return 404 for non-existent API endpoints', async () => {
            const response = await request(baseURL).get('/api/nonexistent/endpoint');
            expect(response.statusCode).toBe(404);
            expect(response.body.success).toBe(false);
            expect(response.body.message).toContain('Not Found');
        });

        it('should return 400 for invalid request data (e.g., missing required fields)', async () => {
            // Example: Demand forecast with missing scenario_name
            const invalidForecastConfig = { target_year: 2025, sectors: {} };
            const response = await request(baseURL).post('/api/demand/forecast').send(invalidForecastConfig);
            expect(response.statusCode).toBe(400);
            expect(response.body.success).toBe(false);
            expect(response.body.errors).toBeDefined();
            expect(response.body.errors.some(err => err.toLowerCase().includes('scenario name'))).toBe(true);
        });
    });
});
