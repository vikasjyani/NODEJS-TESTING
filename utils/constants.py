# utils/constants.py
"""
Shared constants for the KSEB Energy Futures Platform
"""

# COVID years for exclusion in forecasting
COVID_YEARS = [2021, 2022]

# Default forecast parameters
DEFAULT_TARGET_YEAR = 2037
DEFAULT_START_YEAR = 2006
DEFAULT_WINDOW_SIZE = 10

# File extensions and limits
ALLOWED_EXTENSIONS = {'xlsx', 'csv', 'json'}
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB

# Unit conversion factors (base unit: kWh)
UNIT_FACTORS = {
    'TWh': 1000000000,
    'GWh': 1000000,
    'MWh': 1000,
    'kWh': 1
}

# Model types
FORECAST_MODELS = ['MLR', 'SLR', 'WAM', 'TimeSeries']

# Project structure
PROJECT_STRUCTURE = {
    'inputs': {},
    'results': {
        'demand_projection': {},
        'load_profiles': {},
        'PyPSA_Modeling': {},
        'Pypsa_results': {}
    },
    'logs': {},
    'config': {}
}

# File templates
TEMPLATE_FILES = {
    'input_demand_file.xlsx': 'input_demand_file.xlsx',
    'load_curve_template.xlsx': 'load_curve_template.xlsx', 
    'pypsa_input_template.xlsx': 'pypsa_input_template.xlsx',
    'input_demand_file.xlsx': 'input_demand_file.xlsx',
    'load_profile.xlsx': 'load_profile.xlsx'
}

# Excel sheet names
REQUIRED_SHEETS = {
    'INPUTS': 'Inputs',
    'RESULTS': 'Results', 
    'CORRELATIONS': 'Correlations',
    'TEST_RESULTS': 'Test Results',
    'INDEPENDENT_PARAMS': 'Independent Parameters',
    'MAIN': 'main',
    'ECONOMIC_INDICATORS': 'Economic_Indicators'
}

# API response status codes
API_STATUS = {
    'SUCCESS': 'success',
    'ERROR': 'error', 
    'WARNING': 'warning',
    'INFO': 'info'
}

# Forecast job statuses
JOB_STATUS = {
    'STARTING': 'starting',
    'RUNNING': 'running',
    'COMPLETED': 'completed',
    'FAILED': 'failed',
    'CANCELLED': 'cancelled',
    'QUEUED': 'queued'
}

# Time limits (in seconds)
MAX_JOB_RUNTIME = 3600  # 1 hour
CLEANUP_INTERVAL = 300  # 5 minutes
POLLING_INTERVAL = 2500  # 2.5 seconds
MAX_POLLING_RETRIES = 10
JOB_TIMEOUT = 1800  # 30 minutes

# Correlation strength thresholds
CORRELATION_THRESHOLDS = {
    'STRONG': 0.7,
    'MODERATE': 0.4,
    'WEAK': 0.0
}

# Chart colors for sectors
SECTOR_COLORS = [
    {'bg': 'rgba(99, 102, 241, 0.7)', 'border': 'rgba(99, 102, 241, 1)'},
    {'bg': 'rgba(244, 63, 94, 0.7)', 'border': 'rgba(244, 63, 94, 1)'},
    {'bg': 'rgba(59, 130, 246, 0.7)', 'border': 'rgba(59, 130, 246, 1)'},
    {'bg': 'rgba(245, 158, 11, 0.7)', 'border': 'rgba(245, 158, 11, 1)'},
    {'bg': 'rgba(139, 92, 246, 0.7)', 'border': 'rgba(139, 92, 246, 1)'},
    {'bg': 'rgba(34, 197, 94, 0.7)', 'border': 'rgba(34, 197, 94, 1)'},
    {'bg': 'rgba(168, 85, 247, 0.7)', 'border': 'rgba(168, 85, 247, 1)'},
    {'bg': 'rgba(239, 68, 68, 0.7)', 'border': 'rgba(239, 68, 68, 1)'}
]

# Model colors for charts  
MODEL_COLORS = {
    'MLR': 'rgba(99, 102, 241, 0.8)',
    'SLR': 'rgba(244, 63, 94, 0.8)', 
    'TimeSeries': 'rgba(59, 130, 246, 0.8)',
    'WAM': 'rgba(245, 158, 11, 0.8)',
    'User Data': 'rgba(139, 92, 246, 0.8)'
}

# Validation rules
VALIDATION_RULES = {
    'MIN_DATA_POINTS': 2,
    'MIN_TRAINING_SIZE': 0.7,
    'MIN_WINDOW_SIZE': 2,
    'MAX_WINDOW_SIZE': 50,
    'MAX_INDEPENDENT_VARS': 20,
    'MIN_YEAR': 1990,
    'MAX_YEAR': 2100
}

# Default configuration
DEFAULT_CONFIG = {
    'FY_START_MONTH': 4,
    'EXCLUDE_COVID': True,
    'DEFAULT_MODELS': ['WAM'],
    'AUTO_SAVE': True,
    'DEBUG_MODE': False,
    'LOG_LEVEL': 'INFO'
}

# Path constants
DEFAULT_PATHS = {
    'PROJECT_ROOT': 'projects',
    'TEMPLATE_FOLDER': 'static/templates',
    'UPLOAD_FOLDER': 'static/user_uploads',
    'LOGS_FOLDER': 'logs'
}

# Error messages
ERROR_MESSAGES = {
    'NO_PROJECT': 'Please select or create a project first.',
    'FILE_NOT_FOUND': 'Required file not found.',
    'INVALID_FILE': 'Invalid file format or content.',
    'PROCESSING_ERROR': 'Error processing data.',
    'VALIDATION_FAILED': 'Data validation failed.',
    'UNAUTHORIZED': 'Unauthorized access.'
}

# Success messages
SUCCESS_MESSAGES = {
    'PROJECT_CREATED': 'Project created successfully.',
    'PROJECT_LOADED': 'Project loaded successfully.',
    'FILE_UPLOADED': 'File uploaded successfully.',
    'DATA_PROCESSED': 'Data processed successfully.',
    'FORECAST_COMPLETED': 'Forecast completed successfully.'
}
