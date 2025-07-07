"""
Main Flask application for KSEB Energy Futures Platform
with better error handling, configuration management, and standardized responses
"""
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, current_app
import os
import logging
from datetime import datetime
from werkzeug.exceptions import HTTPException as WerkzeugHTTPException

# Import configuration and utilities
from utils.constants import DEFAULT_CONFIG, DEFAULT_PATHS, ERROR_MESSAGES
from utils.response_utils import error_json, success_json
from utils.features_manager import FeatureManager
from utils.helpers import ensure_directory
def setup_template_filters(app):
    """Setup custom template filters"""
    
    @app.template_filter('strftime')
    def strftime_filter(value, format='%Y-%m-%d %H:%M:%S'):
        """
        Custom strftime filter for Jinja2 templates
        Usage: {{ 'now'|strftime('%H:%M:%S') }} or {{ some_datetime|strftime('%Y-%m-%d') }}
        """
        from datetime import datetime
        
        if value == 'now':
            return datetime.now().strftime(format)
        elif isinstance(value, datetime):
            return value.strftime(format)
        elif isinstance(value, str):
            # Try to parse string as datetime
            try:
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                return dt.strftime(format)
            except:
                return value  # Return as-is if can't parse
        else:
            return str(value)
    
    app.logger.debug("Custom template filters registered")
def create_app(config_class=None):
    """
    Application factory with configuration
    """
    app = Flask(__name__)
    
    # Basic configuration
    app.secret_key = os.environ.get('SECRET_KEY', 'energy_demand_forecasting_secret_key_change_in_production')
    
    # configuration from constants and environment
    app.config.update(DEFAULT_CONFIG)
    app.config.update(DEFAULT_PATHS)
    
    # Override with environment variables if available
    app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', DEFAULT_PATHS['UPLOAD_FOLDER'])
    app.config['TEMPLATE_FOLDER'] = os.environ.get('TEMPLATE_FOLDER', DEFAULT_PATHS['TEMPLATE_FOLDER'])
    app.config['PROJECT_ROOT'] = os.environ.get('PROJECT_ROOT', DEFAULT_PATHS['PROJECT_ROOT'])
    app.config['LOGS_FOLDER'] = os.environ.get('LOGS_FOLDER', DEFAULT_PATHS['LOGS_FOLDER'])
    
    # File handling configuration
    app.config['ALLOWED_EXTENSIONS'] = {'xlsx', 'csv', 'json'}
    app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB
    
    # Project state
    app.config['CURRENT_PROJECT'] = None
    app.config['CURRENT_PROJECT_PATH'] = None
    
    # Apply external config if provided
    if config_class:
        app.config.from_object(config_class)
    
    # Initialize logging
    setup_logging(app)
    
    # Ensure required directories exist
    setup_directories(app)
    
    # Validate configuration
    validate_app_config(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Initialize features manager
    setup_features_manager(app)
    
    # Setup context processors
    setup_context_processors(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Setup legacy route redirects
    setup_legacy_redirects(app)
    setup_template_filters(app)
    app.logger.info("KSEB Energy Futures Platform initialized successfully")
    return app

def setup_logging(app):
    """Setup application logging"""
    try:
        log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO').upper())
        log_dir = app.config['LOGS_FOLDER']
        ensure_directory(log_dir)
        
        log_file = os.path.join(log_dir, f'app_{datetime.now().strftime("%Y%m%d")}.log')
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(name)s - [%(filename)s:%(lineno)d] - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        logger = logging.getLogger(__name__)
        logger.info("Logging configured successfully")
        
    except Exception as e:
        print(f"Failed to setup logging: {e}")

def setup_directories(app):
    """Ensure all required directories exist"""
    directories = [
        app.config['UPLOAD_FOLDER'],
        app.config['PROJECT_ROOT'],
        app.config['LOGS_FOLDER'],
        os.path.join(app.config['UPLOAD_FOLDER'], 'recent_projects'),
        os.path.join(app.root_path, 'config')
    ]
    
    for directory in directories:
        if not ensure_directory(directory):
            app.logger.error(f"Failed to create directory: {directory}")
        else:
            app.logger.debug(f"Directory ensured: {directory}")

def validate_app_config(app):
    """Validate application configuration"""
    app.logger.info("Validating application configuration")
    
    required_config = ['UPLOAD_FOLDER', 'ALLOWED_EXTENSIONS', 'PROJECT_ROOT']
    missing = [key for key in required_config if not app.config.get(key)]
    
    if missing:
        app.logger.critical(f"Missing required configuration keys: {missing}")
        raise ValueError(f"Missing required configuration: {missing}")
    
    # Validate paths exist
    for key in ['UPLOAD_FOLDER', 'PROJECT_ROOT', 'LOGS_FOLDER']:
        folder = app.config.get(key)
        if folder and not os.path.exists(folder):
            app.logger.warning(f"Folder for {key} does not exist: {folder}")
            try:
                ensure_directory(folder)
                app.logger.info(f"Created missing folder: {folder}")
            except Exception as e:
                app.logger.error(f"Failed to create folder {folder}: {str(e)}")
    
    app.logger.info("Configuration validation completed")

def register_blueprints(app):
    """Register all application blueprints"""
    # Import the register functions (avoiding circular imports)
    from blueprints.core_bp import register_core_bp
    from blueprints.project_bp import register_project_bp  
    from blueprints.data_bp import register_data_bp
    from blueprints.demand_projection_bp import register_demand_projection_bp
    from blueprints.demand_visualization_bp import register_demand_visualization_bp
    from blueprints.loadprofile_bp import register_loadprofile_bp
    from blueprints.loadprofile_analysis_bp import register_loadprofile_analysis_bp
    from blueprints.pypsa_bp import register_pypsa_bp
    from blueprints.admin_bp import register_admin_bp
    from blueprints.color_management_bp import register_color_management_bp
    
    # Register blueprints using their register functions
    blueprint_registrars = [
        ('core', register_core_bp),
        ('project', register_project_bp),
        ('data', register_data_bp),
        ('demand_projection', register_demand_projection_bp),
        ('demand_visualization', register_demand_visualization_bp),
        ('loadprofile', register_loadprofile_bp),
        ('loadprofile_analysis', register_loadprofile_analysis_bp),
        ('pypsa', register_pypsa_bp),
        ('admin', register_admin_bp),
        ('color_management', register_color_management_bp)
    ]
    
    for name, register_func in blueprint_registrars:
        try:
            register_func(app)
            app.logger.debug(f"Registered blueprint: {name}")
        except Exception as e:
            app.logger.error(f"Failed to register blueprint {name}: {e}")
    
    app.logger.info("All blueprints registered successfully")

def setup_features_manager(app):
    """Initialize the features manager"""
    try:
        if not hasattr(app, 'feature_manager'):
            app.feature_manager = FeatureManager(app)
            app.logger.info("FeatureManager initialized")
        else:
            app.logger.debug("FeatureManager already exists")
    except Exception as e:
        app.logger.error(f"Failed to initialize FeatureManager: {e}")

def setup_context_processors(app):
    """Setup template context processors"""
    @app.context_processor
    def inject_feature_utilities():
        """Inject feature management utilities into templates"""
        def is_feature_enabled(feature_id):
            try:
                project_path = app.config.get('CURRENT_PROJECT_PATH')
                if hasattr(app, 'feature_manager') and app.feature_manager:
                    return app.feature_manager.is_feature_enabled(feature_id, project_path)
                return False
            except Exception as e:
                app.logger.error(f"Error checking feature {feature_id}: {e}")
                return False
        
        def get_enabled_features():
            try:
                project_path = app.config.get('CURRENT_PROJECT_PATH')
                if hasattr(app, 'feature_manager') and app.feature_manager:
                    return app.feature_manager.get_enabled_features(project_path)
                return []
            except Exception as e:
                app.logger.error(f"Error getting enabled features: {e}")
                return []
        
        def get_current_project_info():
            return {
                'name': app.config.get('CURRENT_PROJECT'),
                'path': app.config.get('CURRENT_PROJECT_PATH'),
                'has_project': app.config.get('CURRENT_PROJECT_PATH') is not None
            }
        
        return dict(
            is_feature_enabled=is_feature_enabled,
            get_enabled_features=get_enabled_features,
            get_current_project_info=get_current_project_info,
            current_project=app.config.get('CURRENT_PROJECT'),
            FY_START_MONTH=app.config.get('FY_START_MONTH', 4),
            app_version='1.0.0'
        )
    
    app.logger.debug("Context processors registered")

def register_error_handlers(app):
    """Register error handlers"""
    
    @app.errorhandler(400)
    def bad_request(e):
        app.logger.warning(f"400 Bad Request: {request.url} - {str(e)}")
        if request.is_json:
            return error_json("Bad request", status_code=400)
        return render_template('errors/400.html', error=e), 400
    
    @app.errorhandler(401)
    def unauthorized(e):
        app.logger.warning(f"401 Unauthorized: {request.url} - {str(e)}")
        if request.is_json:
            return error_json(ERROR_MESSAGES['UNAUTHORIZED'], status_code=401)
        return render_template('errors/401.html', error=e), 401
    
    @app.errorhandler(403)
    def forbidden(e):
        app.logger.warning(f"403 Forbidden: {request.url} - {str(e)}")
        if request.is_json:
            return error_json("Access forbidden", status_code=403)
        return render_template('errors/403.html', error=e), 403
    
    @app.errorhandler(404)
    def not_found(e):
        app.logger.warning(f"404 Not Found: {request.url} - {str(e)}")
        if request.is_json:
            return error_json("Resource not found", status_code=404)
        return render_template('errors/404.html', error=e), 404
    
    @app.errorhandler(405)
    def method_not_allowed(e):
        app.logger.warning(f"405 Method Not Allowed: {request.method} {request.url}")
        if request.is_json:
            return error_json("Method not allowed for this endpoint", status_code=405)
        return render_template('errors/405.html', error=e), 405
    
    @app.errorhandler(413)
    def payload_too_large(e):
        app.logger.warning(f"413 Payload Too Large: {request.url}")
        if request.is_json:
            return error_json("File too large", status_code=413)
        return render_template('errors/413.html', error=e), 413
    
    @app.errorhandler(500)
    def internal_server_error(e):
        app.logger.error(f"500 Internal Server Error: {request.url} - {str(e)}", exc_info=True)
        if request.is_json:
            return error_json("Internal server error", status_code=500)
        return render_template('errors/500.html', error=e), 500
    
    @app.errorhandler(Exception)
    def handle_unexpected_exception(e):
        """Handle unexpected exceptions"""
        if isinstance(e, WerkzeugHTTPException):
            return e
        
        app.logger.exception(f"Unhandled exception: {str(e)}")
        if request.is_json:
            return error_json("An unexpected error occurred", status_code=500)
        return render_template('errors/500.html', error=e), 500
    
    @app.before_request
    def ignore_chrome_devtools_probe():
        if request.path == '/.well-known/appspecific/com.chrome.devtools.json':
            return '', 204  # No Content (quiet success)
    
    app.logger.debug("Error handlers registered")

def setup_legacy_redirects(app):
    """Setup legacy route redirects for backward compatibility"""
    
    @app.route('/demand/projection')
    def legacy_demand_projection():
        """Redirect legacy demand projection route"""
        app.logger.info("Redirecting legacy demand projection route")
        return redirect(url_for('demand_projection.demand_projection_route'))

    @app.route('/demand/visualization')  
    def legacy_demand_visualization():
        """Redirect legacy demand visualization route"""
        app.logger.info("Redirecting legacy demand visualization route")
        return redirect(url_for('demand_visualization.demand_visualization_route'))

    @app.route('/demand/api/<path:api_path>')
    def legacy_demand_api(api_path):
        """Redirect legacy demand API routes to appropriate blueprint"""
        app.logger.info(f"Redirecting legacy demand API route: {api_path}")
        
        # Routes that belong to projection
        projection_routes = [
            'independent_variables', 'correlation_data', 'chart_data', 
            'run_forecast', 'forecast_status', 'cancel_forecast'
        ]
        
        # Routes that belong to visualization  
        visualization_routes = [
            'forecast_data', 'scenario_details', 'workflow_status',
            'save_model_config', 'get_model_config', 'save_td_losses', 
            'get_td_losses', 'save_consolidated_results', 'get_consolidated_results',
            'available_scenarios', 'download_csv', 'download_consolidated_csv',
            'download_summary'
        ]
        
        # Determine which blueprint to redirect to
        route_base = api_path.split('/')[0]
        
        try:
            if any(route_base.startswith(route) for route in projection_routes):
                return redirect(url_for(f'demand_projection.{api_path.replace("/", "_")}_api', **request.args))
            elif any(route_base.startswith(route) for route in visualization_routes):
                return redirect(url_for(f'demand_visualization.{api_path.replace("/", "_")}_api', **request.args))
            else:
                # Default to projection for unknown routes
                app.logger.warning(f"Unknown legacy API route: {api_path}, defaulting to projection")
                return redirect(url_for('demand_projection.demand_projection_route'))
        except Exception as e:
            app.logger.error(f"Error redirecting legacy route {api_path}: {e}")
            return redirect(url_for('core.home'))
    
    app.logger.debug("Legacy redirects registered")

# Create the main app instance
app = create_app()

if __name__ == '__main__':
    try:
        port = int(os.environ.get('PORT', 5000))
        debug = os.environ.get('DEBUG', 'True').lower() == 'true'
        host = os.environ.get('HOST', '0.0.0.0')
        
        app.logger.info(f"Starting KSEB Energy Futures Platform on {host}:{port} (debug={debug})")
        app.run(debug=debug, host=host, port=port, threaded=True)
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to start application: {e}")
        import traceback
        traceback.print_exc()