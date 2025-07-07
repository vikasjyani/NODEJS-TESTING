#!/bin/bash

# Basic Deployment Script for KSEB Energy Futures Platform
# This script provides a conceptual outline. Actual deployment will depend heavily on
# the target environment (e.g., specific cloud provider, on-premise server) and
# chosen deployment strategy (Docker Compose, Kubernetes, serverless, etc.).

# --- Configuration - Adjust these variables as needed ---
# APP_NAME: A short name for your application, used for Docker Compose project name, etc.
APP_NAME="kseb_platform"
# DEPLOY_USER: The user on the remote server to deploy as (should have Docker/sudo privileges if needed).
# DEPLOY_HOST: The hostname or IP address of the deployment server.
# DEPLOY_PATH: The root directory on the server where the application will be deployed.
# Example: DEPLOY_USER="deployer"
# Example: DEPLOY_HOST="server1.kseb.in"
# Example: DEPLOY_PATH="/opt/kseb-energy-platform"

# GIT_REPO_URL: The URL of your Git repository.
# GIT_BRANCH: The branch to deploy (e.g., 'main' for production, 'develop' for staging).
# Example: GIT_REPO_URL="git@github.com:your-org/kseb-energy-platform.git"
# Example: GIT_BRANCH="main"

# DOCKER_COMPOSE_FILE: Path to your docker-compose.yml file (relative to project root after checkout).
DOCKER_COMPOSE_FILE="docker-compose.yml" # Assuming it's at the root

# ENV_FILE_PATH: Path to the .env file containing production environment variables.
# This file should be securely managed and copied to the server.
# Example: ENV_FILE_PATH=".env.production"

# BACKUP_DIR: Directory on the server to store backups of previous versions.
# Example: BACKUP_DIR="/opt/backups/kseb-energy-platform"

# --- Script Functions ---

# Function to log messages with a timestamp
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] - $1"
}

# Function to execute a command and exit if it fails
run_cmd() {
  log "Executing: $@"
  "$@"
  local status=$?
  if [ $status -ne 0 ]; then
    log "Error: Command '$@' failed with status $status."
    exit $status
  fi
  return $status
}

# Function to execute a command on the remote server via SSH
# Assumes SSH key-based authentication is set up for DEPLOY_USER@DEPLOY_HOST.
run_remote_cmd() {
  if [ -z "$DEPLOY_USER" ] || [ -z "$DEPLOY_HOST" ]; then
    log "Error: DEPLOY_USER and DEPLOY_HOST must be set for remote commands."
    exit 1
  fi
  log "Remote Exec on $DEPLOY_HOST: $@"
  ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
      "$DEPLOY_USER@$DEPLOY_HOST" "$@"
  local status=$?
  if [ $status -ne 0 ]; then
    log "Error: Remote command '$@' on $DEPLOY_HOST failed with status $status."
    exit $status
  fi
  return $status
}

# --- Main Deployment Steps ---

# 1. Pre-flight checks (local)
log "Starting deployment script..."
if [ -z "$DEPLOY_USER" ] || [ -z "$DEPLOY_HOST" ] || [ -z "$DEPLOY_PATH" ] || [ -z "$GIT_REPO_URL" ] || [ -z "$GIT_BRANCH" ]; then
    log "ERROR: DEPLOY_USER, DEPLOY_HOST, DEPLOY_PATH, GIT_REPO_URL, and GIT_BRANCH environment variables must be set."
    log "Example: export DEPLOY_HOST='your.server.com'"
    exit 1
fi

log "Deployment Target: $DEPLOY_USER@$DEPLOY_HOST:$DEPLOY_PATH"
log "Repository: $GIT_REPO_URL (Branch: $GIT_BRANCH)"

# 2. Connect to remote server and prepare directories
log "Preparing remote server..."
run_remote_cmd "mkdir -p $DEPLOY_PATH"
run_remote_cmd "mkdir -p $BACKUP_DIR" # Ensure backup directory exists

# 3. Backup current version (if exists) on remote server
TIMESTAMP=$(date '+%Y%m%d%H%M%S')
BACKUP_FILE="$BACKUP_DIR/${APP_NAME}-backup-${TIMESTAMP}.tar.gz"
run_remote_cmd "if [ -d \"$DEPLOY_PATH/app\" ]; then \
                  log 'Backing up current version on remote server...'; \
                  tar -czf $BACKUP_FILE -C $DEPLOY_PATH .; \
                  log 'Backup complete: $BACKUP_FILE'; \
                else \
                  log 'No existing version found at $DEPLOY_PATH to backup.'; \
                fi"

# 4. Deploy new version
# This could involve:
#    a) Git clone/pull on the server
#    b) Copying built artifacts (e.g., from a CI/CD pipeline) to the server
# For this example, we'll assume a Git pull strategy.

log "Deploying new version from Git..."
run_remote_cmd "cd $DEPLOY_PATH && \
                if [ -d .git ]; then \
                  log 'Git repository exists, pulling latest changes from branch $GIT_BRANCH...'; \
                  git fetch origin && git reset --hard origin/$GIT_BRANCH && git pull origin $GIT_BRANCH; \
                else \
                  log 'Git repository does not exist, cloning $GIT_REPO_URL...'; \
                  git clone --branch $GIT_BRANCH $GIT_REPO_URL .; \
                fi"

# 5. Copy environment file (if it's not part of the repo and managed separately)
# This step is crucial and depends on your .env file management strategy.
# Example: using scp from where this script is run, or from a secure vault.
if [ -f "$ENV_FILE_PATH" ]; then
  log "Copying environment file ($ENV_FILE_PATH) to remote server..."
  scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
      "$ENV_FILE_PATH" "$DEPLOY_USER@$DEPLOY_HOST:$DEPLOY_PATH/.env"
  REMOTE_ENV_SETUP_STATUS=$?
  if [ $REMOTE_ENV_SETUP_STATUS -ne 0 ]; then
      log "Error: Failed to copy environment file to $DEPLOY_HOST."
      exit $REMOTE_ENV_SETUP_STATUS
  fi
else
  log "Warning: Local environment file ($ENV_FILE_PATH) not found. Assuming .env file is already on server or part of the repo (not recommended for secrets)."
fi


# 6. Build and Start Application using Docker Compose on remote server
log "Building and starting application with Docker Compose on remote server..."
run_remote_cmd "cd $DEPLOY_PATH && \
                log 'Bringing down old containers (if any)...' && \
                docker-compose -f $DOCKER_COMPOSE_FILE -p $APP_NAME down --remove-orphans && \
                log 'Pulling latest images specified in compose file (if any)...' && \
                docker-compose -f $DOCKER_COMPOSE_FILE -p $APP_NAME pull && \
                log 'Building images defined in compose file (if any)...' && \
                docker-compose -f $DOCKER_COMPOSE_FILE -p $APP_NAME build --no-cache && \
                log 'Starting new containers in detached mode...' && \
                docker-compose -f $DOCKER_COMPOSE_FILE -p $APP_NAME up -d --force-recreate && \
                log 'Docker Compose up complete. Application should be starting.'"

# 7. Post-deployment checks (optional)
log "Waiting a few seconds for services to initialize..."
sleep 15 # Adjust as needed

log "Checking application status on remote server..."
# This could be a curl to a health check endpoint or checking `docker-compose ps`
run_remote_cmd "cd $DEPLOY_PATH && docker-compose -p $APP_NAME ps"
# Example health check:
# run_remote_cmd "curl -sSf http://localhost:$(grep APP_PORT $DEPLOY_PATH/.env | cut -d '=' -f2 || echo 5000)/api/health || (log 'Health check failed!' && exit 1)"


# 8. Cleanup (optional: remove old Docker images/containers on remote server)
log "Performing cleanup of old Docker resources on remote server..."
run_remote_cmd "docker image prune -af" # Remove dangling images
run_remote_cmd "docker container prune -f" # Remove stopped containers

log "Deployment script finished successfully!"
exit 0

# --- Usage ---
# 1. Set the configuration variables at the top of this script OR pass them as environment variables.
# 2. Ensure you have SSH access (key-based recommended) to the DEPLOY_HOST as DEPLOY_USER.
# 3. Ensure Docker and Docker Compose are installed on the DEPLOY_HOST.
# 4. Run the script: `./scripts/deploy.sh`
#
# --- Important Security Notes ---
# - Managing .env files: Never commit .env files with sensitive production secrets to Git.
#   Use a secure method to transfer them to the server (e.g., scp as shown, Ansible Vault, HashiCorp Vault).
# - SSH Access: Use SSH keys instead of passwords for authentication.
# - Server Hardening: Ensure your deployment server is properly hardened.
# - This script is a basic template. Adapt it thoroughly for your specific needs and security requirements.
```
