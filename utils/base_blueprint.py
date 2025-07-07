# utils/base_blueprint.py
"""
Base Blueprint class with common functionality
Provides shared methods and utilities for all blueprints
"""
import os
import time
import logging
from functools import wraps
from flask import Blueprint, current_app, request, g
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod

from utils.response_utils import success_json, error_json
from utils.constants import ERROR_MESSAGES

logger = logging.getLogger(__name__)

class BaseBlueprint(ABC):
    """
    Base class for all blueprints providing common functionality
    """
    
    def __init__(self, name: str, import_name: str, **kwargs):
        self.blueprint = Blueprint(name, import_name, **kwargs)
        self.name = name
        self._setup_common_functionality()
    
    def _setup_common_functionality(self):
        """Setup common functionality for all blueprints"""
        
        # Add context processors
        @self.blueprint.context_processor
        def inject_common_context():
            return self._get_common_context()
        
        # Add before request handlers
        @self.blueprint.before_request
        def before_request():
            g.start_time = time.time()
            g.blueprint_name = self.name
        
        # Add after request handlers
        @self.blueprint.after_request
        def after_request(response):
            return self._after_request_handler(response)
        
        # Add error handlers
        self._register_error_handlers()
    
    def _get_common_context(self) -> Dict[str, Any]:
        """Get common template context variables"""
        return {
            'current_project': current_app.config.get('CURRENT_PROJECT'),
            'current_project_path': current_app.config.get('CURRENT_PROJECT_PATH'),
            'has_project': bool(current_app.config.get('CURRENT_PROJECT_PATH')),
            'blueprint_name': self.name
        }
    
    def _after_request_handler(self, response):
        """Common after request processing"""
        try:
            # Log slow requests
            if hasattr(g, 'start_time'):
                duration = time.time() - g.start_time
                if duration > 2.0:  # Log requests over 2 seconds
                    logger.warning(f"Slow request in {self.name}: {request.endpoint} took {duration:.2f}s")
            
            # Add common headers
            response.headers['X-Blueprint'] = self.name
            
            return response
        except Exception as e:
            logger.exception(f"Error in after_request for {self.name}: {e}")
            return response
    
    def _register_error_handlers(self):
        """Register common error handlers"""
        
        @self.blueprint.errorhandler(404)
        def handle_not_found(e):
            logger.warning(f"404 in {self.name}: {request.path}")
            if request.is_json:
                return error_json("Resource not found", status_code=404)
            return self._render_error_template('404.html', error=e), 404
        
        @self.blueprint.errorhandler(500)
        def handle_internal_error(e):
            logger.exception(f"500 in {self.name}: {e}")
            if request.is_json:
                return error_json("Internal server error", status_code=500)
            return self._render_error_template('500.html', error=e), 500
        
        @self.blueprint.errorhandler(Exception)
        def handle_generic_exception(e):
            logger.exception(f"Unhandled exception in {self.name}: {e}")
            if request.is_json:
                return error_json("An unexpected error occurred", status_code=500)
            return self._render_error_template('500.html', error=e), 500
    
    def _render_error_template(self, template: str, **kwargs):
        """Render error template with common context"""
        try:
            from flask import render_template
            return render_template(f'errors/{template}', **kwargs)
        except Exception:
            # Fallback to simple error message
            return f"<h1>Error</h1><p>An error occurred in {self.name}</p>"
    
    def get_project_path(self) -> Optional[str]:
            """Get current project path with validation"""
            try:
                # Check if we're in an application context
                from flask import has_app_context
                if not has_app_context():
                    return None
                
                project_path = current_app.config.get('CURRENT_PROJECT_PATH')
                if not project_path or not os.path.exists(project_path):
                    return None
                return project_path
            except Exception as e:
                logger.debug(f"Error getting project path: {e}")
                return None
    
    def validate_project_selected(self) -> tuple[bool, Optional[str]]:
        """Validate that a project is selected and accessible"""
        project_path = self.get_project_path()
        if not project_path:
            return False, ERROR_MESSAGES['NO_PROJECT']
        return True, None
    
    def get_project_file_path(self, *path_parts: str) -> str:
        """Get file path within current project"""
        project_path = self.get_project_path()
        if not project_path:
            raise ValueError("No project selected")
        return os.path.join(project_path, *path_parts)
    
    def ensure_project_directory(self, *path_parts: str) -> str:
        """Ensure directory exists within project and return path"""
        dir_path = self.get_project_file_path(*path_parts)
        os.makedirs(dir_path, exist_ok=True)
        return dir_path
    
    def list_project_files(self, *path_parts: str, extensions: List[str] = None) -> List[Dict[str, Any]]:
        """List files in project directory with metadata"""
        try:
            dir_path = self.get_project_file_path(*path_parts)
            if not os.path.exists(dir_path):
                return []
            
            files = []
            for filename in os.listdir(dir_path):
                file_path = os.path.join(dir_path, filename)
                if os.path.isfile(file_path):
                    # Filter by extensions if specified
                    if extensions:
                        ext = os.path.splitext(filename)[1].lower()
                        if ext not in extensions:
                            continue
                    
                    try:
                        stat = os.stat(file_path)
                        files.append({
                            'name': filename,
                            'path': file_path,
                            'size_bytes': stat.st_size,
                            'size_mb': round(stat.st_size / (1024 * 1024), 2),
                            'modified': stat.st_mtime,
                            'extension': os.path.splitext(filename)[1].lower()
                        })
                    except OSError:
                        continue
            
            return sorted(files, key=lambda x: x['modified'], reverse=True)
        except Exception as e:
            logger.exception(f"Error listing project files: {e}")
            return []
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get comprehensive file information"""
        try:
            if not os.path.exists(file_path):
                return {'exists': False, 'path': file_path}
            
            stat = os.stat(file_path)
            return {
                'exists': True,
                'path': file_path,
                'name': os.path.basename(file_path),
                'size_bytes': stat.st_size,
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'modified': stat.st_mtime,
                'extension': os.path.splitext(file_path)[1].lower(),
                'is_file': os.path.isfile(file_path),
                'is_directory': os.path.isdir(file_path)
            }
        except Exception as e:
            logger.exception(f"Error getting file info for {file_path}: {e}")
            return {'exists': False, 'path': file_path, 'error': str(e)}
    
    @abstractmethod
    def register_routes(self):
        """Abstract method to register blueprint routes"""
        pass
    
    def register(self, app, **options):
        """Register blueprint with Flask app"""
        self.register_routes()
        app.register_blueprint(self.blueprint, **options)
        logger.info(f"Registered blueprint: {self.name}")

class ServiceBlueprint(BaseBlueprint):
    """
    Extended base blueprint with service layer integration
    """
    
    def __init__(self, name: str, import_name: str, service_class=None, **kwargs):
        super().__init__(name, import_name, **kwargs)
        self.service_class = service_class
        self._service_instance = None
    
    @property
    def service(self):
        """Get service instance (lazy loading)"""
        if self._service_instance is None and self.service_class:
            try:
                # Check if we're in an application context
                from flask import has_app_context
                if has_app_context():
                    project_path = self.get_project_path()
                else:
                    project_path = None
                
                self._service_instance = self.service_class(
                    project_path=project_path
                )
            except Exception as e:
                logger.exception(f"Error initializing service for {self.name}: {e}")
                self._service_instance = None
        return self._service_instance
    
    def invalidate_service(self):
        """Invalidate service instance (force reload)"""
        self._service_instance = None

def with_service(func):
    """Decorator to ensure service is available"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.service:
            if request.is_json:
                return error_json("Service not available", status_code=503)
            else:
                from flask import flash, redirect, url_for
                flash("Service temporarily unavailable", 'danger')
                return redirect(url_for('core.home'))
        return func(self, *args, **kwargs)
    return wrapper