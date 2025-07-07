# --- Stage 1: Build Dependencies & Python Environment ---
FROM node:18-alpine AS deps
LABEL stage="dependencies"

# Install OS-level dependencies for Python build and runtime
# git is for npm packages that might pull from git
# build-base, python3-dev for compiling some Python native extensions
# libffi-dev, openssl-dev for certain crypto/ctypes related python packages
RUN apk add --no-cache \
    git \
    python3 \
    py3-pip \
    build-base \
    python3-dev \
    libffi-dev \
    openssl-dev \
    # Add any other OS deps needed by Python packages (e.g., for PyPSA solvers if bundled)
    # For example, if using GLPK or CBC solver with PyPSA:
    # glpk-dev \
    # coin-or-cbc-dev \
    # For Gurobi/CPLEX, you'd typically use their official Docker images or install from their archives.

# Set Python path explicitly (Alpine usually puts it here)
ENV PYTHON_PATH=/usr/bin/python3
ENV PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

# Copy Python requirements first to leverage Docker cache
# Assuming Python requirements are managed centrally or per module if very different
# For this project, we'll list them directly.
# In a real project, this would be: COPY backend/src/python/requirements.txt .
# RUN pip3 install -r requirements.txt
# For now, installing packages as listed in the prompt:
RUN pip3 install --no-cache-dir \
    pandas \
    numpy \
    scikit-learn \
    statsmodels \
    openpyxl \
    # PyPSA and its dependencies can be complex. Ensure versions are compatible.
    # It often needs specific solver interfaces as well.
    # For simplicity, assuming basic PyPSA without heavy solver deps here.
    # If specific solvers are bundled, their installation would be more involved.
    pypsa # This will pull its own dependencies like scipy, networkx etc.
    # Add any other specific Python packages needed by your scripts

# --- Stage 2: Build Frontend ---
FROM node:18-alpine AS frontend-builder
LABEL stage="frontend-build"
WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./frontend/
RUN cd frontend && npm ci

COPY frontend ./frontend/
RUN cd frontend && npm run build

# --- Stage 3: Build Backend ---
# (Backend doesn't have a separate build step in this project, just JS files)

# --- Stage 4: Final Application Image ---
FROM node:18-alpine AS final
LABEL stage="production"
WORKDIR /app

# Copy Python environment from 'deps' stage
COPY --from=deps /usr/lib/python3.*/site-packages/ /usr/lib/python3.*/site-packages/
COPY --from=deps /usr/local/lib/python3.*/site-packages/ /usr/local/lib/python3.*/site-packages/
COPY --from=deps /usr/bin/python3 /usr/bin/python3
COPY --from=deps /usr/bin/pip3 /usr/bin/pip3
# If any other Python related binaries or shared libs were installed system-wide in deps, copy them too.
# e.g. COPY --from=deps /usr/lib/libglpk.so* /usr/lib/

# Copy root package.json and install ONLY production dependencies for the root (if any)
COPY package.json package-lock.json* ./
RUN npm ci --only=production --ignore-scripts # Ignore scripts if they are dev-only

# Copy backend code and install its production dependencies
COPY backend ./backend/
RUN cd backend && npm ci --only=production --ignore-scripts

# Copy built frontend static assets
COPY --from=frontend-builder /app/frontend/build ./frontend/build
# This path (frontend/build) should align with how your backend serves static files,
# or how Nginx (if used) expects them.

# Copy Python scripts (assuming they are needed at runtime with the backend)
# Python scripts are within backend/src/python
# The backend code already copied includes this.

# Create necessary runtime directories if your app expects them
# (though it's better if the app creates them on first run if they don't exist)
RUN mkdir -p logs results storage data

# Set environment variables
ENV NODE_ENV=production
ENV PORT=5000
ENV PYTHON_PATH=/usr/bin/python3 # Path to Python inside this container
ENV RESULTS_DIR=/app/results
ENV STORAGE_PATH=/app/storage
ENV LOG_DIR=/app/logs
# Add any other runtime environment variables needed by your application

# Expose the port the app runs on
EXPOSE 5000

# Healthcheck (optional, but good practice)
# This assumes your backend has a /api/health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:5000/api/health || exit 1

# User to run the application (optional, for better security)
# RUN addgroup -S appgroup && adduser -S appuser -G appgroup
# USER appuser

# Command to run the application
# This should start your Node.js backend server.
# If using PM2, the CMD would be different, e.g., ["pm2-runtime", "ecosystem.config.js", "--env", "production"]
# For now, assuming direct Node start as per ecosystem.config.js for non-Docker scenario.
# In Docker, often simpler to just run the node process.
CMD ["node", "backend/src/app.js"]
```
