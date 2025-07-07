// jest.config.js
// This configuration is for the root of the monorepo if running all tests together.
// Individual packages (frontend, backend, electron) might have their own Jest configs
// if tests are run separately per package. For now, a root config example.

module.exports = {
  // Automatically clear mock calls and instances between every test
  clearMocks: true,

  // Indicates whether the coverage information should be collected while executing the test
  collectCoverage: true,

  // An array of glob patterns indicating a set of files for which coverage information should be collected
  // collectCoverageFrom: undefined, // Configure per-project or if needed globally

  // The directory where Jest should output its coverage files
  coverageDirectory: 'coverage',

  // An array of regexp pattern strings used to skip coverage collection
  coveragePathIgnorePatterns: [
    '/node_modules/',
    '/dist/',
    '/build/',
    '.*\\.d\\.ts$' // Ignore TypeScript definition files
  ],

  // Indicates which provider Docusaurus should use to instrument code for coverage
  coverageProvider: 'babel', // or 'v8' if preferred and setup

  // A list of reporter names that Jest uses when writing coverage reports
  // coverageReporters: ["json", "text", "lcov", "clover"],

  // An object that configures minimum threshold enforcement for coverage results
  // coverageThreshold: undefined,

  // A path to a custom dependency extractor
  // dependencyExtractor: undefined,

  // Make calling deprecated APIs throw helpful error messages
  // errorOnDeprecated: false,

  // Preset that is used as a base for Jest's configuration
  // preset: undefined, // e.g., 'ts-jest' if using ts-jest directly for all projects

  // The root directory that Jest should scan for tests and modules within
  rootDir: '.', // Root of the monorepo

  // A list of paths to directories that Jest should use to search for files in
  // roots: ['<rootDir>/frontend/src', '<rootDir>/backend/src', '<rootDir>/electron'], // Example if testing specific src dirs

  // Allows you to use a custom runner instead of Jest's default test runner
  // runner: "jest-runner",

  // The paths to modules that run some code to configure or set up the testing environment before each test
  // setupFiles: [],

  // A list of paths to modules that run some code to configure or set up the testing framework before each test
  // setupFilesAfterEnv: ['<rootDir>/tests/setupTests.js'], // Global setup after env

  // The number of seconds after which a test is considered as slow and reported as such in the results.
  // slowTestThreshold: 5,

  // A list of paths to snapshotSerializers that will be used for snapshot testing
  // snapshotSerializers: [],

  // The test environment that will be used for testing
  testEnvironment: 'node', // Default to node, React components need 'jsdom'

  // Options that will be passed to the testEnvironment
  // testEnvironmentOptions: {},

  // Adds a location field to test results
  // testLocationInResults: false,

  // The glob patterns Jest uses to detect test files
  testMatch: [
    '**/__tests__/**/*.[jt]s?(x)', // Standard Jest pattern
    '**/?(*.)+(spec|test).[tj]s?(x)', // Standard Jest pattern
  ],

  // An array of regexp pattern strings that are matched against all test paths, matched tests are skipped
  testPathIgnorePatterns: [
    '/node_modules/',
    '/dist/',
    '/build/',
    '/coverage/',
    '<rootDir>/frontend/build/', // Ignore CRA build output
  ],

  // The regexp pattern or array of patterns that Jest uses to detect test files
  // testRegex: [],

  // This option allows the use of a custom results processor
  // testResultsProcessor: undefined,

  // This option allows use of a custom test runner
  // testRunner: "jest-circus/runner",

  // This option sets the URL for the jsdom environment. It is reflected in properties such as location.href
  // testURL: "http://localhost",

  // Setting this value to "fake" allows the use of fake timers for functions such as "setTimeout"
  // timers: "real",

  // A map from regular expressions to paths to transformers
  // This is crucial for TypeScript, JSX, etc.
  transform: {
    '^.+\\.(ts|tsx)$': ['ts-jest', { tsconfig: 'tsconfig.json' }], // Adjust tsconfig path if needed for monorepo
    '^.+\\.(js|jsx)$': 'babel-jest', // If you have Babel for JS/JSX files
    // Add transformers for CSS, files, etc. if needed by frontend tests
    // '^.+\\.css$': '<rootDir>/config/jest/cssTransform.js',
    // '^(?!.*\\.(js|jsx|mjs|cjs|ts|tsx|css|json)$)': '<rootDir>/config/jest/fileTransform.js'
  },

  // An array of regexp pattern strings that are matched against all source file paths, matched files will skip transformation
  transformIgnorePatterns: [
    '/node_modules/',
    '\\.pnp\\.[^\\/]+$',
  ],

  // An array of regexp pattern strings that are matched against all modules before the module loader will automatically return a mock for them
  // unmockedModulePathPatterns: undefined,

  // Indicates whether each individual test should be reported during the run
  verbose: true,

  // An array of regexp patterns that are matched against all source file paths before re-running tests in watch mode
  // watchPathIgnorePatterns: [],

  // Whether to use watchman for file crawling
  // watchman: true,

  // Module settings
  moduleFileExtensions: ['js', 'mjs', 'cjs', 'jsx', 'ts', 'tsx', 'json', 'node'],
  // moduleNameMapper: { // If you use path aliases in tsconfig.json
    // '^@components/(.*)$': '<rootDir>/frontend/src/components/$1',
    // '^@services/(.*)$': '<rootDir>/frontend/src/services/$1',
    // etc.
  // },
  // modulePaths: ['<rootDir>'], // Base directory for module resolution

  // Project-specific configurations if running tests for multiple projects (workspaces)
  // projects: [
  //   {
  //     displayName: 'frontend',
  //     testEnvironment: 'jsdom',
  //     rootDir: '<rootDir>/frontend',
  //     setupFilesAfterEnv: ['<rootDir>/frontend/src/setupTests.ts'], // CRA-like setup
  //     transform: {
  //       '^.+\\.(ts|tsx)$': ['ts-jest', { tsconfig: '<rootDir>/frontend/tsconfig.json' }],
  //       // ... other frontend specific transforms
  //     },
  //     moduleNameMapper: { // For CRA related assets
  //        '\\.(css|less|scss|sass)$': 'identity-obj-proxy', // Mocks CSS imports
  //        '\\.(jpg|jpeg|png|gif|eot|otf|webp|svg|ttf|woff|woff2|mp4|webm|wav|mp3|m4a|aac|oga)$': '<rootDir>/__mocks__/fileMock.js'
  //     }
  //   },
  //   {
  //     displayName: 'backend',
  //     testEnvironment: 'node',
  //     rootDir: '<rootDir>/backend',
  //      transform: {
  //       '^.+\\.(ts|js)$': ['ts-jest', { tsconfig: '<rootDir>/backend/tsconfig.json' }], // Assuming backend might have tsconfig
  //     },
  //   },
  //   {
  //     displayName: 'electron',
  //     testEnvironment: 'node', // Electron main/preload tests run in Node
  //     rootDir: '<rootDir>/electron',
  //      transform: {
  //       '^.+\\.ts$': ['ts-jest', { tsconfig: '<rootDir>/electron/tsconfig.json' }],
  //     },
  //   }
  // ],
};
