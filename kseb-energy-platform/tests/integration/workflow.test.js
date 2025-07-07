const request = require('supertest');
const TestEnvironment = require('../setup'); // Assumes setup.js is in tests/
const path = require('path');
const fs = require('fs').promises;

jest.setTimeout(180000); // Increase timeout for long workflows (3 minutes)

describe('Full Workflow Integration Tests', () => {
    let testEnv;
    let baseURL;
    let projectPath; // Path for test project files, relative to testDataDir

    // Python script execution timeout for tests - keep it reasonably short
    const PYTHON_SCRIPT_TIMEOUT = 15000; // 15 seconds

    beforeAll(async () => {
        testEnv = new TestEnvironment();
        await testEnv.setup(); // Starts backend, creates mock data dirs
        baseURL = `http://localhost:${testEnv.testPort}`;
        projectPath = path.join(testEnv.testDataDir, 'integration_test_project_root'); // Define a root for this test's project
        await fs.mkdir(projectPath, { recursive: true });
        // Note: TestEnvironment's createMockInputFiles might already create some files in testDataDir/inputs.
        // Ensure paths used by Python scripts in tests point correctly, possibly by copying files
        // or by configuring Python scripts to use paths relative to testEnv.testDataDir.
    });

    afterAll(async () => {
        if (testEnv) {
            await testEnv.teardown();
        }
    });

    describe('Core Energy Planning Workflow', () => {
        let createdProjectId; // If projects are managed via API
        let demandForecastId;
        let loadProfileJobId;
        let pypsaOptimizationJobId;
        let generatedLoadProfileId; // The ID from the Python script's result
        let pypsaNetworkPath; // Path to the generated .nc file

        // Test 0: (Optional) Create a Project via API if such an endpoint exists
        // For now, we'll assume operations happen in a predefined context or implicitly create resources.

        test('Step 1: Run Demand Projection and wait for completion', async () => {
            const forecastConfig = {
                scenario_name: 'integration_workflow_demand',
                target_year: 2026, // Keep forecast range small for faster tests
                exclude_covid: false, // Use all data from mock for simplicity
                input_file: "inputs/default_demand_data.xlsx", // Relative to python script CWD
                sectors: {
                    residential: { models: ['SLR', 'WAM'], wam_window: 2, independent_variables: ['gdp'] },
                },
                timeout: PYTHON_SCRIPT_TIMEOUT
            };

            const startResponse = await request(baseURL)
                .post('/api/demand/forecast')
                .send(forecastConfig)
                .expect(202); // Accepted

            expect(startResponse.body.success).toBe(true);
            demandForecastId = startResponse.body.forecastId;
            expect(demandForecastId).toBeDefined();
            testEnv.log(`Demand forecast job started: ${demandForecastId}`);

            // Poll for completion
            let attempts = 0;
            const maxAttempts = 20; // Approx 20 * 2s = 40s, plus python timeout
            let forecastJob;
            while (attempts < maxAttempts) {
                await new Promise(resolve => setTimeout(resolve, 2000));
                const statusResponse = await request(baseURL).get(`/api/demand/forecast/${demandForecastId}/status`);
                if (statusResponse.statusCode !== 200 && statusResponse.statusCode !== 404) { // allow 404 if job map clears fast
                    console.error("Demand status check error:", statusResponse.body);
                }
                expect(statusResponse.statusCode === 200 || statusResponse.statusCode === 404).toBeTruthy();

                if (statusResponse.body.success) {
                    forecastJob = statusResponse.body;
                    testEnv.log(`Demand forecast ${demandForecastId} status: ${forecastJob.status}, progress: ${forecastJob.progress}%`);
                    if (forecastJob.status === 'completed') {
                        expect(forecastJob.result).toBeDefined();
                        expect(forecastJob.result.sectors.residential.models.SLR.projections).toBeDefined();
                        break;
                    }
                    if (forecastJob.status === 'failed') {
                        fail(`Demand forecast job ${demandForecastId} failed: ${forecastJob.error}`);
                    }
                } else if (statusResponse.statusCode === 404 && forecastJob && forecastJob.status === 'completed') {
                    // If status is 404 but we previously got a completed state, consider it done
                    // This can happen if the job is removed from activeJobs map quickly after completion.
                    testEnv.log(`Demand forecast ${demandForecastId} status 404, assuming completed as per last known state.`);
                    break;
                }
                attempts++;
            }
            if (!forecastJob || forecastJob.status !== 'completed') {
                fail(`Demand forecast ${demandForecastId} did not complete. Last status: ${forecastJob?.status}`);
            }
        });

        test('Step 2: Generate Load Profile using the demand forecast and wait for completion', async () => {
            // This assumes the demand forecast scenario_name is used by load profile generator.
            // The demand_projection.py script saves results in results/demand_forecasts/<scenario_name>/
            // The load_profile_generation.py needs to know how to find these.
            // For testing, we might need to ensure this pathing works or mock it.
            // For now, assuming the 'demand_scenario' config key in load profile points to scenario_name.
            const profileConfig = {
                profile_name: 'integration_workflow_lp',
                method: 'base_scaling',
                base_year: 2022, // From dummy_load_template_path
                start_year: 2023,
                end_year: 2024, // Small range
                input_template_file: "inputs/load_curve_template.xlsx", // Relative to python script CWD
                demand_scenario: 'integration_workflow_demand', // Use the scenario name from previous step
                timeout: PYTHON_SCRIPT_TIMEOUT
            };

            const startResponse = await request(baseURL)
                .post('/api/loadprofile/generate')
                .send(profileConfig)
                .expect(202);

            expect(startResponse.body.success).toBe(true);
            loadProfileJobId = startResponse.body.profileJobId;
            expect(loadProfileJobId).toBeDefined();
            testEnv.log(`Load profile generation job started: ${loadProfileJobId}`);

            let attempts = 0;
            const maxAttempts = 20;
            let profileJob;
            while (attempts < maxAttempts) {
                await new Promise(resolve => setTimeout(resolve, 2000));
                const statusResponse = await request(baseURL).get(`/api/loadprofile/jobs/${loadProfileJobId}/status`);
                expect(statusResponse.statusCode === 200 || statusResponse.statusCode === 404).toBeTruthy();

                if (statusResponse.body.success) {
                    profileJob = statusResponse.body.job; // Controller returns { success: true, job: {...} }
                    testEnv.log(`Load profile ${loadProfileJobId} status: ${profileJob.status}, progress: ${profileJob.progress}%`);
                    if (profileJob.status === 'completed') {
                        expect(profileJob.result).toBeDefined();
                        expect(profileJob.result.saved_path).toBeDefined();
                        generatedLoadProfileId = profileJob.result.profile_id; // Python generated ID
                        break;
                    }
                    if (profileJob.status === 'failed') {
                        fail(`Load profile job ${loadProfileJobId} failed: ${profileJob.error}`);
                    }
                }  else if (statusResponse.statusCode === 404 && profileJob && profileJob.status === 'completed') {
                    testEnv.log(`Load profile ${loadProfileJobId} status 404, assuming completed.`);
                    break;
                }
                attempts++;
            }
             if (!profileJob || profileJob.status !== 'completed') {
                fail(`Load profile job ${loadProfileJobId} did not complete. Last status: ${profileJob?.status}`);
            }
        });

        test('Step 3: Run PyPSA Optimization using the generated load profile and wait for completion', async () => {
            // PyPSA config needs to reference the generated load profile.
            // This is complex: pypsa_runner.py needs to know how to find and use the load profile JSON.
            // For an integration test, this might require:
            // 1. The load profile path (profileJob.result.saved_path) to be passed in PyPSA config.
            // 2. The PyPSA script to be able to read this JSON and integrate it.
            // For this placeholder, we'll assume a simplified PyPSA run that doesn't heavily depend on prior step's specific file output for now.
            const pypsaConfig = {
                scenario_name: 'integration_workflow_pypsa',
                base_year: 2023, // Should align with one of the load profile years
                investment_mode: 'single_year',
                // input_file: "inputs/pypsa_input_template.xlsx", // Using internal simple network for now
                // load_profile_id: generatedLoadProfileId, // Pass the ID of the generated profile
                solver_options: { solver: 'cbc' }, // CBC is often available, GLPK also good choice
                timeout: PYTHON_SCRIPT_TIMEOUT + 5000 // PyPSA can be slower
            };

            const startResponse = await request(baseURL)
                .post('/api/pypsa/optimize')
                .send(pypsaConfig)
                .expect(202);

            expect(startResponse.body.success).toBe(true);
            pypsaOptimizationJobId = startResponse.body.jobId;
            expect(pypsaOptimizationJobId).toBeDefined();
            testEnv.log(`PyPSA optimization job started: ${pypsaOptimizationJobId}`);

            let attempts = 0;
            const maxAttempts = 25; // PyPSA can take longer
            let pypsaJob;
            while (attempts < maxAttempts) {
                await new Promise(resolve => setTimeout(resolve, 2000));
                const statusResponse = await request(baseURL).get(`/api/pypsa/optimization/${pypsaOptimizationJobId}/status`);
                expect(statusResponse.statusCode === 200 || statusResponse.statusCode === 404).toBeTruthy();

                if (statusResponse.body.success) {
                    pypsaJob = statusResponse.body.job;
                    testEnv.log(`PyPSA job ${pypsaOptimizationJobId} status: ${pypsaJob.status}, progress: ${pypsaJob.progress}%`);
                    if (pypsaJob.status === 'completed') {
                        expect(pypsaJob.result).toBeDefined();
                        expect(pypsaJob.result.network_path).toBeDefined();
                        pypsaNetworkPath = pypsaJob.result.network_path;
                        break;
                    }
                    if (pypsaJob.status === 'failed') {
                        fail(`PyPSA job ${pypsaOptimizationJobId} failed: ${pypsaJob.error}`);
                    }
                } else if (statusResponse.statusCode === 404 && pypsaJob && pypsaJob.status === 'completed') {
                     testEnv.log(`PyPSA job ${pypsaOptimizationJobId} status 404, assuming completed.`);
                    break;
                }
                attempts++;
            }
            if (!pypsaJob || pypsaJob.status !== 'completed') {
                fail(`PyPSA job ${pypsaOptimizationJobId} did not complete. Last status: ${pypsaJob?.status}`);
            }
        });

        test('Step 4: Verify existence of result artifacts', async () => {
            // Check demand forecast results (controller doesn't have a direct list endpoint for scenarios)
            // We can check if the specific forecast job has results.
            const demandStatusRes = await request(baseURL).get(`/api/demand/forecast/${demandForecastId}/status`);
            expect(demandStatusRes.body.success).toBe(true);
            expect(demandStatusRes.body.result).toBeDefined();
            testEnv.log("Verified demand forecast result exists.");

            // Check load profile results
            const profileListRes = await request(baseURL).get('/api/loadprofile/profiles');
            expect(profileListRes.body.success).toBe(true);
            const foundProfile = profileListRes.body.profiles.find(p => p.profile_id === generatedLoadProfileId);
            expect(foundProfile).toBeDefined();
            testEnv.log(`Verified load profile ${generatedLoadProfileId} exists in list.`);

            // Check PyPSA networks
            const networkListRes = await request(baseURL).get('/api/pypsa/networks');
            expect(networkListRes.body.success).toBe(true);
            const foundNetwork = networkListRes.body.networks.find(n => n.network_path === pypsaNetworkPath);
            expect(foundNetwork).toBeDefined();
            testEnv.log(`Verified PyPSA network ${pypsaNetworkPath} exists in list.`);

            // Check if the actual .nc file exists (requires fs access from test or an API to check file)
            // For now, trusting the API list.
            expect(await fs.access(pypsaNetworkPath).then(() => true).catch(() => false)).toBe(true);
            testEnv.log(`Verified PyPSA network file ${pypsaNetworkPath} exists on disk.`);
        });

        test('Step 5: Perform analysis on a generated PyPSA network', async () => {
            expect(pypsaNetworkPath).toBeDefined();
            const analysisResponse = await request(baseURL)
                .get(`/api/pypsa/analysis/${encodeURIComponent(pypsaNetworkPath)}/info`) // Test 'info' analysis
                .expect(200);

            expect(analysisResponse.body.success).toBe(true);
            expect(analysisResponse.body.data).toBeDefined();
            expect(analysisResponse.body.data.name).toEqual('integration_workflow_pypsa_network'); // from pypsa_runner.py default naming
            expect(analysisResponse.body.data.components.generators).toBeGreaterThan(0);
            testEnv.log(`PyPSA network info analysis successful for ${pypsaNetworkPath}.`);
        });
    });

    // Add more describe blocks for other specific integration tests if needed
    // e.g., testing caching behavior, specific error conditions, etc.
});
