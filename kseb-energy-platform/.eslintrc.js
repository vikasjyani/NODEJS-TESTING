module.exports = {
  env: {
    browser: true, // For frontend code (React)
    es2021: true,
    node: true, // For backend and Electron main/preload
    jest: true, // For test files
  },
  extends: [
    'eslint:recommended',
    'plugin:react/recommended', // For React specific linting
    'plugin:@typescript-eslint/recommended', // For TypeScript specific linting
    // 'plugin:prettier/recommended', // Enables eslint-plugin-prettier and eslint-config-prettier. THIS MUST BE LAST IN EXTENDS.
  ],
  parser: '@typescript-eslint/parser', // Specifies the ESLint parser for TypeScript
  parserOptions: {
    ecmaFeatures: {
      jsx: true, // Allows for the parsing of JSX
    },
    ecmaVersion: 'latest', // Allows for the parsing of modern ECMAScript features
    sourceType: 'module', // Allows for the use of imports
    project: ['./tsconfig.json', './frontend/tsconfig.json', './backend/tsconfig.json', './electron/tsconfig.json'], // Point to your tsconfig files for type-aware linting
  },
  plugins: [
    'react', // ESLint plugin for React
    '@typescript-eslint', // ESLint plugin for TypeScript
    // 'prettier', // Runs Prettier as an ESLint rule
    'import', // Plugin to help with import/export syntax
    'jsx-a11y', // Accessibility rules for JSX
    'react-hooks' // Enforces rules of Hooks
  ],
  settings: {
    react: {
      version: 'detect', // Automatically detects the React version
    },
    'import/resolver': { // Helps eslint-plugin-import resolve paths defined in tsconfig.json
      typescript: {}, // Uses tsconfig.json settings
      node: {
        extensions: ['.js', '.jsx', '.ts', '.tsx']
      }
    }
  },
  rules: {
    // General ESLint rules
    'no-console': process.env.NODE_ENV === 'production' ? 'warn' : 'off', // Warn about console.log in production
    'no-debugger': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
    'no-unused-vars': 'off', // Handled by @typescript-eslint/no-unused-vars
    'indent': 'off', // Usually handled by Prettier if used

    // TypeScript specific rules
    '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }], // Warn on unused vars, allow _ prefix
    '@typescript-eslint/no-explicit-any': 'warn', // Warn on usage of 'any' type, prefer 'unknown' or specific types
    '@typescript-eslint/explicit-module-boundary-types': 'off', // Allows inferring return types for functions
    '@typescript-eslint/no-non-null-assertion': 'warn', // Warn on non-null assertions (!)

    // React specific rules
    'react/prop-types': 'off', // Not needed with TypeScript
    'react/react-in-jsx-scope': 'off', // Not needed with React 17+ new JSX transform
    'react-hooks/rules-of-hooks': 'error', // Checks rules of Hooks
    'react-hooks/exhaustive-deps': 'warn', // Checks effect dependencies

    // Import rules
    'import/order': [
      'warn',
      {
        groups: ['builtin', 'external', 'internal', ['parent', 'sibling', 'index']],
        pathGroups: [{ pattern: 'react', group: 'external', position: 'before' }],
        pathGroupsExcludedImportTypes: ['react'],
        'newlines-between': 'always',
        alphabetize: { order: 'asc', caseInsensitive: true },
      },
    ],
    'import/no-duplicates': 'error',

    // JSX Accessibility rules (examples, configure as needed)
    'jsx-a11y/accessible-emoji': 'warn',
    'jsx-a11y/alt-text': 'warn',
    'jsx-a11y/anchor-has-content': 'warn',
    // ... more jsx-a11y rules

    // Prettier rules (if using eslint-plugin-prettier)
    // 'prettier/prettier': ['error', {
    //   // Prettier options here, e.g.,
    //   // "singleQuote": true,
    //   // "trailingComma": "all",
    //   // "arrowParens": "always"
    // }],
  },
  overrides: [
    { // Specific overrides for backend (Node.js) if needed
      files: ['backend/**/*.js', 'backend/**/*.ts'],
      rules: {
        '@typescript-eslint/no-var-requires': 'off', // Allow require() in backend commonJS modules
      }
    },
    { // Specific overrides for Electron main/preload
      files: ['electron/**/*.ts'],
      rules: {
        '@typescript-eslint/no-var-requires': 'off',
      }
    },
    { // Specific overrides for test files
        files: ['**/__tests__/**/*.[jt]s?(x)', '**/?(*.)+(spec|test).[jt]s?(x)'],
        extends: ['plugin:jest/recommended'],
        rules: {
            'jest/no-disabled-tests': 'warn',
            'jest/no-focused-tests': 'error',
            'jest/no-identical-title': 'error',
            'jest/prefer-to-have-length': 'warn',
            'jest/valid-expect': 'error'
        }
    }
  ],
  ignorePatterns: [ // Files/directories to ignore
    'node_modules/',
    'dist/',
    'build/',
    'coverage/',
    '**/vite-env.d.ts', // Example for Vite if used in frontend
    '*.log'
  ],
};
