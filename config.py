import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    PROJECT_ROOT_NAME = 'projects'
    PROJECT_ROOT_ABS = os.path.join(BASE_DIR, PROJECT_ROOT_NAME)
    USER_DATA_DIR_NAME = 'users'
    USER_DATA_DIR_ABS = os.path.join(BASE_DIR, USER_DATA_DIR_NAME)
    CURRENT_PROJECT_NAME = None
    CURRENT_PROJECT_FOLDER = None
    CURRENT_PROJECT_PATH_ABS = None
    CELERY_BROKER_URL = 'redis://localhost:6379/0'  # Placeholder
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'  # Placeholder

    # Logging Configuration
    LOG_TO_STDOUT = True  # Set to False in production if file logging is preferred
    LOG_FILE = 'logs/kseb_platform.log' # Path relative to BASE_DIR
    LOG_LEVEL_FILE = 'INFO'    # e.g., DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_LEVEL_STDOUT = 'DEBUG' # For console output
    LOG_ROTATING_FILE_MAX_BYTES = 1024 * 1024 * 10  # 10 MB
    LOG_ROTATING_FILE_BACKUP_COUNT = 5 # Number of backup log files
