// This file is intended for global Jest setup, but given the problem description's
// `TestEnvironment` class seems more like a backend-specific integration test helper,
// I will implement that class structure here.
// For true global Jest setup (e.g., polyfills, global mocks), this file would be configured
// in jest.config.js's `setupFilesAfterEnv` array.

const { spawn, execSync } = require('child_process');
const path = require('path');
const fs = require('fs').promises; // Using promises API of fs
const http = require('http'); // For a simple health check utility

class TestEnvironment {
    constructor() {
        this.testPort = process.env.TEST_BACKEND_PORT || 5001; // Use a different port for test server
        this.serverProcess = null;
        this.testDataDir = path.join(__dirname, 'test-data-generated'); // __dirname is tests/
        this.backendRootDir = path.join(__dirname, '../backend'); // Path to backend root
        this.isServerReady = false;
        this.serverLogs = [];
        this.maxLogLines = 50;
    }

    log(message) {
        // console.log(`[TestEnv] ${message}`); // For Jest console
        this.serverLogs.push(`[${new Date().toISOString()}] ${message}`);
        if (this.serverLogs.length > this.maxLogLines) {
            this.serverLogs.shift();
        }
    }

    async setup() {
        this.log('Setting up test environment...');
        try {
            await this.cleanupTestData(); // Clean up from previous runs first
            await this.createTestDataDirectory();
            await this.createMockInputFiles(); // Create general mock files

            // For Python scripts, ensure a Python executable is findable or configured
            // This might involve checking process.env.PYTHON_PATH or trying common commands
            this.log(`Python executable for tests will be: ${this.getTestPythonPath()}`);

            await this.startTestServer();
            await this.waitForServerReady();
            this.log('Test environment setup complete.');
        } catch (error) {
            this.log(`Error during test environment setup: ${error.message}`);
            await this.teardown(); // Attempt cleanup on setup failure
            throw error; // Re-throw to fail tests if setup fails
        }
    }

    async createTestDataDirectory() {
        await fs.mkdir(this.testDataDir, { recursive: true });
        this.log(`Test data directory created/ensured at: ${this.testDataDir}`);

        // Create subdirectories expected by services (e.g., for fileService or python scripts)
        // These paths should align with how services might expect them, potentially using this.testDataDir as a root.
        await fs.mkdir(path.join(this.testDataDir, 'inputs'), { recursive: true });
        await fs.mkdir(path.join(this.testDataDir, 'results', 'load_profiles'), { recursive: true });
        await fs.mkdir(path.join(this.testDataDir, 'results', 'demand_forecasts'), { recursive: true });
        await fs.mkdir(path.join(this.testDataDir, 'results', 'pypsa'), { recursive: true });
        // This 'python' dir inside testDataDir could be where scripts are copied or where they output if CWD is changed for them
        await fs.mkdir(path.join(this.testDataDir, 'python', 'shared'), { recursive: true });
    }

    getTestPythonPath() {
        if (process.env.TEST_PYTHON_PATH) return process.env.TEST_PYTHON_PATH;
        try {
            // Simple check for python3 then python
            execSync('python3 --version', { stdio: 'ignore' });
            return 'python3';
        } catch (e) {
            try {
                execSync('python --version', { stdio: 'ignore' });
                return 'python';
            } catch (e2) {
                this.log("Warning: Neither 'python3' nor 'python' found in PATH for tests. Python script tests might fail.");
                return 'python'; // Default, will likely fail if not present
            }
        }
    }


    async createMockInputFiles() {
        // Mock for demand_projection.py input (e.g., default_demand_data.xlsx)
        // For simplicity, creating a JSON, Python script would need to handle this or use a mock Excel
        const mockDemandExcelDir = path.join(this.testDataDir, 'inputs');
        const mockDemandData = {
            'residential': pd.DataFrame({'year': [2020, 2021], 'demand': [100, 110], 'gdp': [1000,1020]}).to_dict(orient='list'),
            'commercial': pd.DataFrame({'year': [2020, 2021], 'demand': [200, 220]}).to_dict(orient='list'),
        };
        // In a real test, you'd use pandas to_excel to create a small xlsx file.
        // For now, we'll just note that the Python scripts expect an Excel file.
        // Or, we can use the actual placeholder files if they exist in backend/src/python/inputs
        const sourceInputsDir = path.join(this.backendRootDir, 'src', 'python', 'inputs');
        try {
            if ((await fs.stat(sourceInputsDir)).isDirectory()) {
                 this.log(`Copying placeholder input files from ${sourceInputsDir} to ${mockDemandExcelDir}`);
                 await fs.cp(sourceInputsDir, mockDemandExcelDir, {recursive: true});
            }
        } catch (e) {
            this.log(`Could not copy placeholder inputs: ${e.message}. Creating dummy file marker.`);
            await fs.writeFile(path.join(mockDemandExcelDir, 'default_demand_data.xlsx.mock'), "This is a mock excel for testing.");
            await fs.writeFile(path.join(mockDemandExcelDir, 'load_curve_template.xlsx.mock'), "This is a mock excel for testing.");
        }


        // Mock for load_profile_generation.py input (e.g., load_curve_template.xlsx)
        // Similar to above, use actual placeholder or a mock file.

        this.log('Mock input files setup (or placeholders copied).');
    }

    async startTestServer() {
        return new Promise((resolve, reject) => {
            this.log(`Starting test backend server on port ${this.testPort}...`);
            const backendAppScript = path.join(this.backendRootDir, 'src', 'app.js');

            this.serverProcess = spawn('node', [backendAppScript], {
                env: {
                    ...process.env,
                    NODE_ENV: 'test',
                    PORT: String(this.testPort),
                    RESULTS_DIR: path.join(this.testDataDir, 'results'), // Point results to test data
                    STORAGE_PATH: path.join(this.testDataDir, 'storage'), // Point storage to test data
                    PYTHON_PATH: this.getTestPythonPath(), // Ensure Python scripts use a known Python for tests
                    // Override other env vars if needed for testing
                },
                cwd: this.backendRootDir, // Run backend from its own root
                // detached: true, // Might cause issues with auto-termination on some OS
            });

            this.serverProcess.stdout.on('data', (data) => {
                const output = data.toString().trim();
                this.log(`Server STDOUT: ${output}`);
                if (output.includes(`Server running on port ${this.testPort}`)) {
                    this.log('Test server reported as running.');
                    this.isServerReady = true;
                    resolve();
                }
            });

            this.serverProcess.stderr.on('data', (data) => {
                const errorOutput = data.toString().trim();
                this.log(`Server STDERR: ${errorOutput}`);
                // Optionally reject on specific startup errors
            });

            this.serverProcess.on('error', (error) => {
                this.log(`Failed to start test server process: ${error.message}`);
                this.isServerReady = false;
                reject(error);
            });

            this.serverProcess.on('exit', (code, signal) => {
                this.log(`Test server process exited with code ${code}, signal ${signal}.`);
                this.isServerReady = false;
                this.serverProcess = null;
            });

            // Safety timeout for server start
            setTimeout(() => {
                if (!this.isServerReady) {
                    this.log('Test server startup timed out.');
                    reject(new Error('Test server startup timeout'));
                }
            }, 30000); // 30 seconds
        });
    }

    async waitForServerReady(timeout = 30000, interval = 500) {
        if (this.isServerReady) return; // Already ready from stdout parsing

        this.log('Waiting for test server to be ready via health check...');
        const startTime = Date.now();
        while (Date.now() - startTime < timeout) {
            try {
                // Use a simple HTTP GET to the health endpoint
                await new Promise((resolveGet, rejectGet) => {
                    http.get(`http://localhost:${this.testPort}/api/health`, (res) => {
                        if (res.statusCode === 200) {
                            this.isServerReady = true;
                            resolveGet(true);
                        } else {
                            rejectGet(new Error(`Health check failed with status: ${res.statusCode}`));
                        }
                    }).on('error', rejectGet);
                });

                if (this.isServerReady) {
                    this.log('Test server health check successful.');
                    return;
                }
            } catch (error) {
                // Server not ready yet, or health check failed
                this.log(`Health check attempt failed: ${error.message}. Retrying...`);
            }
            await new Promise(resolveDelay => setTimeout(resolveDelay, interval));
        }
        throw new Error(`Test server failed to become ready on port ${this.testPort} after ${timeout}ms.`);
    }

    async cleanupTestData() {
        if (fs.existsSync(this.testDataDir)) { // fs.existsSync is sync, use fs.access for async if preferred
            this.log(`Cleaning up test data directory: ${this.testDataDir}`);
            await fs.rm(this.testDataDir, { recursive: true, force: true });
        }
    }

    async teardown() {
        this.log('Tearing down test environment...');
        if (this.serverProcess) {
            this.log(`Stopping test server process (PID: ${this.serverProcess.pid})...`);
            const killed = this.serverProcess.kill('SIGTERM'); // Send SIGTERM for graceful shutdown
            if (!killed) {
                 this.log("Failed to send SIGTERM, attempting SIGKILL.");
                 this.serverProcess.kill('SIGKILL');
            }
            // Add a small delay or wait for exit event if needed, but Jest usually handles process termination
            await new Promise(resolve => setTimeout(resolve, 500)); // Small delay
            this.serverProcess = null;
            this.isServerReady = false;
        }
        await this.cleanupTestData();
        this.log('Test environment teardown complete.');
        // console.log("Final Server Logs from TestEnv:\n", this.serverLogs.join('\n')); // For debugging in Jest
    }
}

// This makes the class available if this file is require()'d.
// For Jest globalSetup/globalTeardown, you'd export async functions.
// For this setup, individual test files will instantiate TestEnvironment.
module.exports = TestEnvironment;

// Example of how this might be used in a Jest global setup (not the current plan for this file)
// async function globalSetup() {
//   const testEnv = new TestEnvironment();
//   global.__TEST_ENV__ = testEnv; // Make it available globally
//   await testEnv.setup();
// }
// async function globalTeardown() {
//   if (global.__TEST_ENV__) {
//     await global.__TEST_ENV__.teardown();
//   }
// }
// module.exports = { globalSetup, globalTeardown };
