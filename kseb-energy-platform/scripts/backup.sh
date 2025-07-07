#!/bin/bash

# Basic Backup Script for KSEB Energy Futures Platform
# This script outlines how to back up key components:
# - Docker volumes (e.g., Redis data)
# - Mounted persistent data directories (results, storage, logs)
# - (Optionally) Database if a separate DB like PostgreSQL/MongoDB is used

# --- Configuration - Adjust these variables ---
APP_NAME="kseb_platform" # Should match the project name in docker-compose.yml for volume naming
BACKUP_ROOT_DIR="/opt/kseb_backups" # Root directory on the server to store all backups
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
CURRENT_BACKUP_DIR="${BACKUP_ROOT_DIR}/${APP_NAME}_backup_${TIMESTAMP}"

# Directories mounted as volumes in docker-compose.yml that need backing up
# These paths are on the HOST machine where Docker is running.
PERSISTENT_DATA_DIRS=(
  "/opt/kseb-energy-platform/results"  # Assuming this is the host path for results
  "/opt/kseb-energy-platform/storage" # Assuming this is the host path for general storage
  "/opt/kseb-energy-platform/logs"    # Assuming this is the host path for application logs
  # Add other critical host-mounted directories here
)

# Docker named volumes to back up (e.g., Redis data, database data)
# The name usually is <projectname>_<volumename> e.g., kseb_platform_redis_data
DOCKER_VOLUMES_TO_BACKUP=(
  "${APP_NAME}_redis_data"
  # "${APP_NAME}_postgres_data" # Example if using PostgreSQL
)

# Retention policy: Number of old backups to keep (0 to keep all)
RETENTION_DAYS=7 # Keep backups for 7 days

# --- Script Functions ---
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] - $1"
}

run_cmd() {
  log "Executing: $@"
  "$@"
  local status=$?
  if [ $status -ne 0 ]; then
    log "Error: Command '$@' failed with status $status."
    # Decide if script should exit on error or just log and continue
    # exit $status # Uncomment to exit on any command failure
  fi
  return $status
}

# --- Main Backup Steps ---

log "Starting KSEB Energy Futures Platform backup process..."

# 1. Create current backup directory
log "Creating backup directory: $CURRENT_BACKUP_DIR"
mkdir -p "$CURRENT_BACKUP_DIR"
if [ $? -ne 0 ]; then
  log "Error: Failed to create backup directory $CURRENT_BACKUP_DIR. Exiting."
  exit 1
fi

# 2. Backup Host-Mounted Persistent Data Directories
log "Backing up host-mounted persistent data directories..."
for data_dir in "${PERSISTENT_DATA_DIRS[@]}"; do
  if [ -d "$data_dir" ]; then
    dir_basename=$(basename "$data_dir")
    backup_file_path="${CURRENT_BACKUP_DIR}/${dir_basename}_${TIMESTAMP}.tar.gz"
    log "Backing up $data_dir to $backup_file_path..."
    run_cmd tar -czf "$backup_file_path" -C "$(dirname "$data_dir")" "$dir_basename"
    if [ $? -eq 0 ]; then
        log "Successfully backed up $data_dir."
    else
        log "Warning: Failed to back up $data_dir."
    fi
  else
    log "Warning: Persistent data directory $data_dir not found. Skipping."
  fi
done

# 3. Backup Docker Named Volumes
# This method involves stopping the relevant container, running a temporary container
# to access the volume, creating a tarball, and then restarting the container.
# This ensures data consistency.
log "Backing up Docker named volumes..."
for volume_name in "${DOCKER_VOLUMES_TO_BACKUP[@]}"; do
  log "Processing Docker volume: $volume_name"

  # Find container(s) using this volume (this is a bit complex to do generically)
  # For simplicity, we might need to know which service uses which volume.
  # Example: if $volume_name is "kseb_platform_redis_data", the service might be "kseb_platform_redis_1" or similar.
  # We can try to infer service name from volume name if convention is followed.
  service_name_guess=$(echo "$volume_name" | sed "s/${APP_NAME}_// ; s/_data//") # e.g., kseb_platform_redis_data -> redis
  container_name="${APP_NAME}_${service_name_guess}_1" # Common Docker Compose naming

  log "Attempting to backup volume $volume_name (associated with container guess: $container_name)"

  # Check if the guessed container exists and is running
  # docker ps -q -f name="^/${container_name}$" -f status=running
  # This is complex. A simpler, though potentially data-inconsistent way for some dbs, is to backup live.
  # For live backup of Redis (if RDB/AOF is configured):
  if [[ "$volume_name" == *redis* ]]; then
    log "Attempting live backup for Redis volume $volume_name..."
    # This assumes redis-cli is available on the host or in another container.
    # Or, more simply, just copy the RDB file from the volume if its path is known.
    # The most straightforward way is to use a temporary container that mounts the volume.
  fi

  # Generic Docker volume backup using a temporary container:
  backup_file_path_volume="${CURRENT_BACKUP_DIR}/volume_${volume_name}_${TIMESTAMP}.tar.gz"
  log "Backing up $volume_name to $backup_file_path_volume..."

  # Note: `docker volume inspect $volume_name` gives Mountpoint, but it's often inside /var/lib/docker...
  # Using a temporary container is often easier and more portable.
  run_cmd docker run --rm \
           -v "${volume_name}:/volume_data_to_backup:ro" \
           -v "${CURRENT_BACKUP_DIR}:/backup_destination" \
           alpine \
           tar -czf "/backup_destination/volume_${volume_name}_${TIMESTAMP}.tar.gz" -C /volume_data_to_backup .

  if [ $? -eq 0 ]; then
    log "Successfully backed up Docker volume $volume_name."
  else
    log "Warning: Failed to back up Docker volume $volume_name."
  fi
done

# (Optional) 4. Database Specific Backup (if not covered by Docker volume backup)
# If using a separate SQL database (PostgreSQL, MySQL), use their specific dump tools.
# Example for PostgreSQL:
# DB_USER="your_db_user"
# DB_NAME="your_db_name"
# DB_BACKUP_FILE="${CURRENT_BACKUP_DIR}/db_${DB_NAME}_${TIMESTAMP}.sql.gz"
# log "Backing up PostgreSQL database $DB_NAME..."
# run_cmd docker exec -t $(docker ps -q -f name="${APP_NAME}_postgres") pg_dump -U $DB_USER -d $DB_NAME | gzip > $DB_BACKUP_FILE
# This assumes a running PostgreSQL container named appropriately.

# 5. Compress the entire backup directory for this timestamp (optional, if individual tar.gz are not enough)
# log "Compressing all backup files for ${TIMESTAMP}..."
# FINAL_BACKUP_ARCHIVE="${BACKUP_ROOT_DIR}/${APP_NAME}_full_backup_${TIMESTAMP}.tar.gz"
# run_cmd tar -czf "$FINAL_BACKUP_ARCHIVE" -C "$BACKUP_ROOT_DIR" "${APP_NAME}_backup_${TIMESTAMP}"
# if [ $? -eq 0 ]; then
#   log "Successfully created final archive: $FINAL_BACKUP_ARCHIVE"
#   log "Removing intermediate backup directory: $CURRENT_BACKUP_DIR"
#   run_cmd rm -rf "$CURRENT_BACKUP_DIR"
# else
#   log "Warning: Failed to create final archive. Individual backups remain in $CURRENT_BACKUP_DIR."
# fi


# 6. Retention Policy: Remove old backups
if [ "$RETENTION_DAYS" -gt 0 ]; then
  log "Applying retention policy: Keeping last $RETENTION_DAYS days of backups..."
  # This find command removes directories older than RETENTION_DAYS.
  # Assumes backup directory names start with ${APP_NAME}_backup_
  find "$BACKUP_ROOT_DIR" -maxdepth 1 -type d -name "${APP_NAME}_backup_*" -mtime +"$RETENTION_DAYS" -exec echo "Deleting old backup: {}" \; -exec rm -rf {} \;
  # If using single archive files:
  # find "$BACKUP_ROOT_DIR" -maxdepth 1 -type f -name "${APP_NAME}_full_backup_*.tar.gz" -mtime +"$RETENTION_DAYS" -exec echo "Deleting old backup archive: {}" \; -exec rm -f {} \;
  log "Old backups cleanup finished."
else
  log "Retention policy not applied (RETENTION_DAYS is 0 or not set)."
fi

log "Backup process finished for ${APP_NAME}."
echo "Backup completed. Check logs for details."
echo "Backup stored in: ${CURRENT_BACKUP_DIR} (or as a single archive if implemented)"

exit 0

# --- Usage ---
# 1. Configure variables at the top.
# 2. Ensure this script has execute permissions (`chmod +x scripts/backup.sh`).
# 3. Run it manually: `./scripts/backup.sh`
# 4. Schedule it with cron: `0 2 * * * /path/to/kseb-energy-platform/scripts/backup.sh >> /var/log/kseb_platform_backup_cron.log 2>&1` (Example: daily at 2 AM)
#
# --- Important Notes ---
# - Test this script thoroughly in a non-production environment first.
# - Ensure the user running this script has necessary permissions to read data directories, Docker volumes, and write to backup directory.
# - For databases, using their native dump tools is generally preferred for consistency.
# - Consider off-site backups: copy the created backup files to a remote storage location (S3, another server, etc.).
# - Monitor backup success/failure (e.g., through cron job output or a monitoring system).
```
