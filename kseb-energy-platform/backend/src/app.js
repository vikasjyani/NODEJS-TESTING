const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const { createServer } = require('http');
const { Server } = require('socket.io');

// Import custom modules
const routes = require('./routes');
const { errorHandler } = require('./middleware/errorHandler'); // Will be created next
const { logger } = require('./utils/logger'); // Will be created next

const app = express();
const server = createServer(app);

// Initialize Socket.IO
const io = new Server(server, {
    cors: {
        origin: process.env.NODE_ENV === 'production' ? false : 'http://localhost:3000',
        methods: ['GET', 'POST']
    }
});

// Security middleware
app.use(helmet());
app.use(cors({
    origin: process.env.NODE_ENV === 'production' ? false : 'http://localhost:3000',
    credentials: true
}));

// Performance middleware
app.use(compression());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Rate limiting
const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100, // limit each IP to 100 requests per windowMs
    standardHeaders: true, // Return rate limit info in the `RateLimit-*` headers
    legacyHeaders: false, // Disable the `X-RateLimit-*` headers
});
app.use('/api/', limiter);

// Store io instance for use in routes
app.set('io', io);

// Routes
app.use('/api', routes); // Will be created next

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.status(200).json({ status: 'healthy', timestamp: new Date().toISOString() });
});

// Error handling
app.use(errorHandler);

// Socket.IO connection handling
io.on('connection', (socket) => {
    logger.info(`Client connected: ${socket.id}`);

    socket.on('disconnect', () => {
        logger.info(`Client disconnected: ${socket.id}`);
    });

    // Example: Listen for a custom event from client
    socket.on('custom-event', (data) => {
        logger.info(`Received custom-event from ${socket.id} with data:`, data);
        // Broadcast to other clients or handle data
        socket.broadcast.emit('event-update', { from: socket.id, data });
    });
});

const PORT = process.env.PORT || 5000;
server.listen(PORT, () => {
    logger.info(`Server running on port ${PORT}`);
});

module.exports = { app, server, io };
