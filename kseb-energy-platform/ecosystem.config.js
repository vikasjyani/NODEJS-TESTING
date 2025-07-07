// PM2 Ecosystem Configuration File
// For managing and running the Node.js backend application in production.
// This file assumes the KSEB Energy Futures Platform will be run directly via Node.js,
// managed by PM2. If running inside Docker, PM2 might still be used within the container,
// or Docker's own restart policies could be sufficient.

// Ensure paths are relative to the root of the project where pm2 is started.
const path = require('path');

module.exports = {
  apps: [
    {
      name: 'kseb-energy-platform-backend', // Specific name for the backend process
      script: path.join(__dirname, 'backend/src/app.js'), // Path to your backend entry point
      // cwd: path.join(__dirname, 'backend'), // Set current working directory for the backend
      instances: process.env.PM2_INSTANCES || 'max', // 'max' to use all available CPUs, or a specific number like 2, 4.
      exec_mode: 'cluster', // Enables clustering for Node.js applications to leverage multiple cores.

      // Environment variables for all environments (can be overridden by specific env_ sections)
      env: {
        NODE_ENV: 'development', // Default NODE_ENV
        PORT: 5000, // Default port
        LOG_LEVEL: 'info', // Default log level
        // Add other common environment variables here
        // e.g., PYTHON_PATH for the bundled python if applicable and not set globally
        // PYTHON_PATH: path.join(__dirname, 'python-runtime', 'bin', 'python') // Example for bundled Python
      },
      // Environment variables specific to production
      env_production: {
        NODE_ENV: 'production',
        PORT: process.env.PROD_PORT || 5000, // Use environment variable for production port or default
        LOG_LEVEL: 'warn', // Less verbose logging in production
        // Increase Node.js heap size if needed for large datasets/many users
        // This is passed via node_args below.
        // MAX_OLD_SPACE_SIZE: 4096, // Example: 4GB
        // Add production specific DB connection strings, API keys, etc.
        // DB_CONNECTION_STRING: process.env.PROD_DB_CONNECTION_STRING,
        // API_KEY_SECRET: process.env.PROD_API_KEY_SECRET,
      },

      // Logging configuration
      // PM2 will manage log rotation for these files.
      error_file: path.join(__dirname, 'logs/pm2-backend-error.log'), // Path for error logs
      out_file: path.join(__dirname, 'logs/pm2-backend-out.log'),   // Path for standard output logs
      // log_file: path.join(__dirname, 'logs/pm_combined.log'), // Merged out and error (optional)
      combine_logs: true, // If true, out_file will contain both stdout and stderr
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z', // ISO8601 format with timezone
      time: true, // Prefix logs with timestamp (PM2's own timestamp)

      // Monitoring and Restart Strategy
      watch: false, // Disable watching in production; use deployment process for updates.
                    // Can be true or an array of paths for development auto-restart.
      // ignore_watch: ['node_modules', 'logs', 'results', 'frontend', 'electron', '.git'], // If watch is enabled
      max_memory_restart: process.env.PM2_MAX_MEM_RESTART || '500M', // Restart if process exceeds this memory (e.g., '1G')

      // Advanced Node.js arguments
      node_args: [
        '--max-old-space-size=1024', // Default to 1GB, can be overridden by env like process.env.MAX_OLD_SPACE_SIZE_ARG
        // '--expose-gc', // If your MemoryManager uses global.gc()
        // '--optimize_for_size',
        // '--max_semi_space_size=128'
      ],

      // Restart behavior
      autorestart: true, // Restart on crash
      max_restarts: 10, // Limit restarts within a short time
      restart_delay: 5000, // Delay (ms) between restarts
      min_uptime: '30s', // Minimum uptime before considering a process "stable" (e.g., '60s')

      // Useful for graceful shutdown
      kill_timeout: 5000, // Time (ms) to wait for process to gracefully shutdown before force killing
      wait_ready: true, // Wait for 'ready' signal from process (if app emits process.send('ready'))
      listen_timeout: 10000, // If app doesn't send 'ready' within this time, it's considered failed

      // Deployment specific (if using PM2's deployment features - less common with Docker)
      // deploy: {
      //   production: {
      //     user: 'your_server_user',
      //     host: ['your_server_ip'],
      //     ref: 'origin/main',
      //     repo: 'git@github.com:your_repo.git',
      //     path: '/var/www/kseb-platform',
      //     'post-deploy': 'npm install && npm run build:backend && pm2 reload ecosystem.config.js --env production',
      //   }
      // }
    }
    // You could add other apps here, for example, if you had a separate worker service
    // or if the frontend was also Node.js based and served via PM2 (though usually it's static files via Nginx).
  ]
};

// To use this file:
// 1. Install PM2 globally: `npm install pm2 -g`
// 2. Navigate to the project root directory.
// 3. Start development environment: `pm2 start ecosystem.config.js` (uses default env)
// 4. Start production environment: `pm2 start ecosystem.config.js --env production`
//
// Common PM2 commands:
// `pm2 list` - Show all running processes
// `pm2 logs kseb-energy-platform-backend` - View logs for this app
// `pm2 stop kseb-energy-platform-backend` - Stop the app
// `pm2 restart kseb-energy-platform-backend` - Restart the app
// `pm2 delete kseb-energy-platform-backend` - Remove app from PM2 list
// `pm2 startup` - Configure PM2 to start on system boot
// `pm2 save` - Save current PM2 process list for startup
// `pm2 monit` - Monitor CPU/Memory usage of processes
```
