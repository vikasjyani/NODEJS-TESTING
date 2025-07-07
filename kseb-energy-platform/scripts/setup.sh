#!/bin/bash

# KSEB Energy Futures Platform - Environment Setup Script
# This script helps in setting up the necessary environment for development or a new deployment.
# It's intended to be run on a Linux-based system (e.g., Ubuntu, CentOS).
# Adaptations might be needed for macOS or Windows (WSL).

set -e # Exit immediately if a command exits with a non-zero status.

# --- Configuration ---
NODE_VERSION_TARGET="18" # Major version, e.g., "18"
PYTHON_VERSION_TARGET="3.9" # Target Python version, e.g., "3.9"
# Add other dependencies like Docker, Docker Compose, Nginx if this script should handle their installation.
INSTALL_DOCKER=true
INSTALL_DOCKER_COMPOSE=true
INSTALL_NGINX=false # Set to true if Nginx is managed by this script outside Docker

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." &> /dev/null && pwd )" # Project root directory

# --- Helper Functions ---
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] [SETUP] - $1"
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# --- Main Setup Steps ---

log "Starting KSEB Energy Futures Platform environment setup..."
cd "$PROJECT_DIR" # Ensure we are in the project root

# 1. Update System Packages
log "Updating system package list..."
sudo apt-get update -y || { log "Error: Failed to update package list. Check sudo privileges or network."; exit 1; }

# 2. Install Git (if not already present)
if ! command_exists git; then
  log "Installing Git..."
  sudo apt-get install -y git || { log "Error: Failed to install Git."; exit 1; }
  log "Git installed successfully."
else
  log "Git is already installed."
fi

# 3. Install Node.js and npm
log "Checking Node.js version..."
NODE_CURRENT_VERSION=$(node -v 2>/dev/null || echo "none")
if [[ "$NODE_CURRENT_VERSION" != v$NODE_VERSION_TARGET* ]]; then
  log "Node.js v${NODE_VERSION_TARGET}.x not found or version mismatch (Found: $NODE_CURRENT_VERSION). Installing/Updating Node.js..."
  # Using NodeSource setup script for specific Node.js version
  curl -fsSL "https://deb.nodesource.com/setup_${NODE_VERSION_TARGET}.x" | sudo -E bash -
  sudo apt-get install -y nodejs || { log "Error: Failed to install Node.js."; exit 1; }
  log "Node.js v$(node -v) and npm v$(npm -v) installed successfully."
else
  log "Node.js v${NODE_VERSION_TARGET}.x (Found: $NODE_CURRENT_VERSION) is already installed."
fi

# 4. Install Python and pip
log "Checking Python version..."
PYTHON_CURRENT_VERSION=$(python3 -V 2>&1 || echo "none") # python3 -V outputs to stderr for some versions
if [[ "$PYTHON_CURRENT_VERSION" != Python\ $PYTHON_VERSION_TARGET* ]]; then
    log "Python ${PYTHON_VERSION_TARGET} not found or version mismatch (Found: $PYTHON_CURRENT_VERSION). Installing Python ${PYTHON_VERSION_TARGET}..."
    sudo apt-get install -y python${PYTHON_VERSION_TARGET} python${PYTHON_VERSION_TARGET}-dev python${PYTHON_VERSION_TARGET}-venv python3-pip || { log "Error: Failed to install Python ${PYTHON_VERSION_TARGET}."; exit 1; }
    # Ensure python3 points to the correct version or use python3.9 directly
    # sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1 # Example
    log "Python $(python3 -V) and pip $(pip3 --version) installed/updated."
else
    log "Python ${PYTHON_VERSION_TARGET} (Found: $PYTHON_CURRENT_VERSION) is already installed."
fi
# Upgrade pip
log "Upgrading pip..."
python3 -m pip install --upgrade pip

# 5. Install Docker (optional)
if [ "$INSTALL_DOCKER" = true ]; then
  if ! command_exists docker; then
    log "Installing Docker..."
    # Add Docker's official GPG key:
    sudo apt-get install -y ca-certificates curl gnupg
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    # Add the repository to Apt sources:
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin || { log "Error: Failed to install Docker."; exit 1; }
    # Add current user to docker group (requires logout/login or new shell to take effect)
    sudo usermod -aG docker $USER || log "Warning: Failed to add $USER to docker group. Docker commands might need sudo."
    log "Docker installed. You might need to log out and log back in for group changes to take effect."
  else
    log "Docker is already installed."
  fi
fi

# 6. Install Docker Compose (if not installed as a plugin with Docker) (optional)
if [ "$INSTALL_DOCKER_COMPOSE" = true ] && ! command_exists docker-compose; then
    if ! (docker compose version >/dev/null 2>&1) ; then # Check if docker compose (plugin) exists
        log "Docker Compose (standalone) not found. Installing..."
        # Check latest version from https://github.com/docker/compose/releases
        LATEST_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
        if [ -z "$LATEST_COMPOSE_VERSION" ]; then
            log "Warning: Could not fetch latest Docker Compose version. Using a fallback."
            LATEST_COMPOSE_VERSION="v2.20.0" # Example fallback, check for actual latest
        fi
        sudo curl -L "https://github.com/docker/compose/releases/download/${LATEST_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
        log "Docker Compose $(docker-compose --version) installed successfully."
    else
        log "Docker Compose (plugin or standalone) is already available."
    fi
fi

# 7. Install Nginx (optional, if not using Dockerized Nginx)
if [ "$INSTALL_NGINX" = true ]; then
  if ! command_exists nginx; then
    log "Installing Nginx..."
    sudo apt-get install -y nginx || { log "Error: Failed to install Nginx."; exit 1; }
    sudo systemctl enable nginx
    sudo systemctl start nginx
    log "Nginx installed and started."
  else
    log "Nginx is already installed."
  fi
fi

# 8. Install Project Dependencies
log "Installing Node.js project dependencies (root and workspaces)..."
npm install --workspaces --if-present && npm install || { log "Error: Failed to install Node.js dependencies."; exit 1; }

log "Installing Python project dependencies..."
# This assumes Python dependencies are listed in a requirements.txt file in backend/src/python
PYTHON_REQS_FILE="${PROJECT_DIR}/backend/src/python/requirements.txt"
if [ -f "$PYTHON_REQS_FILE" ]; then
  python3 -m pip install -r "$PYTHON_REQS_FILE" || { log "Error: Failed to install Python dependencies from $PYTHON_REQS_FILE."; exit 1; }
else
  log "Python requirements.txt not found at $PYTHON_REQS_FILE. Installing core packages..."
  python3 -m pip install pandas numpy scikit-learn statsmodels openpyxl pypsa || { log "Error: Failed to install core Python packages."; exit 1; }
fi
log "Python dependencies installed."

# 9. Create .env file from .env.example (if it exists)
ENV_EXAMPLE_FILE="${PROJECT_DIR}/.env.example"
ENV_FILE="${PROJECT_DIR}/.env"
if [ -f "$ENV_EXAMPLE_FILE" ] && [ ! -f "$ENV_FILE" ]; then
  log "Creating .env file from .env.example. Please review and update .env with your settings."
  cp "$ENV_EXAMPLE_FILE" "$ENV_FILE"
elif [ -f "$ENV_FILE" ]; then
  log ".env file already exists. Skipping creation from example."
else
  log "No .env.example found. Please create a .env file manually with necessary environment variables."
fi

# 10. Create necessary directories for runtime (if not handled by app or Docker)
log "Ensuring runtime directories exist..."
mkdir -p "${PROJECT_DIR}/logs"
mkdir -p "${PROJECT_DIR}/results/demand_forecasts"
mkdir -p "${PROJECT_DIR}/results/load_profiles"
mkdir -p "${PROJECT_DIR}/results/pypsa"
mkdir -p "${PROJECT_DIR}/storage"
mkdir -p "${PROJECT_DIR}/data/samples" # If sample data is part of the repo and needs to be in a writable location
mkdir -p "${PROJECT_DIR}/backend/src/python/inputs" # For Python script inputs
mkdir -p "${PROJECT_DIR}/templates" # For user-facing templates

log "Runtime directories ensured."

# Final instructions
log "---------------------------------------------------------------------"
log "KSEB Energy Futures Platform setup script finished!"
log "---------------------------------------------------------------------"
if [ "$INSTALL_DOCKER" = true ] && ! groups | grep -q '\bdocker\b'; then
  log "IMPORTANT: You were added to the 'docker' group. You may need to log out and log back in for this change to take effect, or run 'newgrp docker' in your current shell."
fi
log "Next steps:"
log "1. Review and update the .env file with your specific configurations (database, API keys, etc.)."
log "2. To start the application in development mode: npm run dev"
log "3. To build for production and run with Docker: (Ensure Docker is running)"
log "   - Build Docker image: docker-compose build"
log "   - Start services: docker-compose up -d"
log "4. To run Electron app (after npm run build): npm run package (or specific os package script) then run built app."
log "---------------------------------------------------------------------"

exit 0
```
