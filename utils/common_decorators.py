# utils/common_decorators.py
"""
Common decorators for blueprint optimization
Centralized validation, error handling, and caching
"""
import os
import time
import logging
import gc
from functools import wraps
from flask import current_app, request, g
from typing import Dict, Any, Optional, Callable

from utils.response_utils import error_json, validation_error_json
from utils.constants import ERROR_MESSAGES

# Optional imports for performance monitoring
try:
    import psutil
except ImportError:
    psutil = None

try:
    from utils.cache_manager import cache_manager
except ImportError:
    cache_manager = None

try:
    from utils.performance_profiler import profiler
except ImportError:
    profiler = None

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom validation error for decorator use"""
    pass

class ProcessingError(Exception):
    """Custom processing error"""
    pass

class ResourceNotFoundError(Exception):
    """Custom resource not found error"""
    def __init__(self, resource_type: str, identifier: str):
        self.resource_type = resource_type
        self.identifier = identifier
        super().__init__(f"{resource_type.title()} '{identifier}' not found")

def memory_efficient_operation(f: Callable) -> Callable:
    """
    Decorator for memory-efficient operations with garbage collection
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Force garbage collection before operation
        gc.collect()
        
        # Get memory usage before
        memory_before = 0
        if psutil:
            try:
                process = psutil.Process()
                memory_before = process.memory_info().rss
            except:
                pass
        
        try:
            result = f(*args, **kwargs)
            return result
        finally:
            # Force garbage collection after operation
            gc.collect()
            
            # Log memory usage if significant
            if psutil:
                try:
                    memory_after = process.memory_info().rss
                    memory_delta = (memory_after - memory_before) / (1024 * 1024)  # MB
                    if memory_delta > 50:  # Log if >50MB increase
                        logger.info(f"Memory usage increased by {memory_delta:.1f}MB in {f.__name__}")
                except:
                    pass
    
    return wrapper

def require_project(f: Callable) -> Callable:
    """
    Decorator to ensure a project is selected before executing route
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_app.config.get('CURRENT_PROJECT_PATH'):
            if request.is_json:
                return error_json(ERROR_MESSAGES['NO_PROJECT'], status_code=400)
            else:
                from flask import flash, redirect, url_for
                flash(ERROR_MESSAGES['NO_PROJECT'], 'warning')
                return redirect(url_for('core.home'))
        
        # Verify project path still exists
        project_path = current_app.config['CURRENT_PROJECT_PATH']
        if not os.path.exists(project_path):
            current_app.config['CURRENT_PROJECT'] = None
            current_app.config['CURRENT_PROJECT_PATH'] = None
            
            if request.is_json:
                return error_json("Selected project no longer exists", status_code=404)
            else:
                from flask import flash, redirect, url_for
                flash("Selected project no longer exists", 'danger')
                return redirect(url_for('core.home'))
        
        return f(*args, **kwargs)
    return wrapper

def validate_json_request(required_fields: list = None, optional_fields: list = None):
    """
    Decorator to validate JSON request data
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not request.is_json:
                return validation_error_json("Request must be JSON")
            
            try:
                data = request.get_json()
                if not data:
                    return validation_error_json("No JSON data provided")
            except Exception as e:
                return validation_error_json(f"Invalid JSON: {str(e)}")
            
            # Validate required fields
            missing_fields = []
            if required_fields:
                for field in required_fields:
                    if field not in data:
                        missing_fields.append(field)
            
            if missing_fields:
                return validation_error_json(
                    f"Missing required fields: {', '.join(missing_fields)}"
                )
            
            # Add validated data to request context
            g.json_data = data
            return f(*args, **kwargs)
        return wrapper
    return decorator

def handle_exceptions(blueprint_name: str = None):
    """
    Decorator for consistent exception handling across blueprints
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except ValidationError as e:
                logger.warning(f"[{blueprint_name}] Validation error in {f.__name__}: {e}")
                if request.is_json:
                    return validation_error_json(str(e))
                else:
                    from flask import flash, redirect, url_for
                    flash(str(e), 'warning')
                    return redirect(url_for('core.home'))
            
            except FileNotFoundError as e:
                logger.error(f"[{blueprint_name}] File not found in {f.__name__}: {e}")
                if request.is_json:
                    return error_json("Required file not found", status_code=404)
                else:
                    from flask import flash, redirect, url_for
                    flash("Required file not found", 'danger')
                    return redirect(url_for('core.home'))
            
            except PermissionError as e:
                logger.error(f"[{blueprint_name}] Permission error in {f.__name__}: {e}")
                if request.is_json:
                    return error_json("Permission denied", status_code=403)
                else:
                    from flask import flash, redirect, url_for
                    flash("Permission denied", 'danger')
                    return redirect(url_for('core.home'))
            
            except Exception as e:
                logger.exception(f"[{blueprint_name}] Unexpected error in {f.__name__}: {e}")
                if request.is_json:
                    return error_json("An unexpected error occurred", status_code=500)
                else:
                    from flask import flash, redirect, url_for
                    flash("An unexpected error occurred", 'danger')
                    return redirect(url_for('core.home'))
        return wrapper
    return decorator

def cache_route(ttl: int = 300, key_func: Callable = None):
    """
    Decorator for route-level caching
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            # If no cache manager, just execute function
            if not cache_manager:
                return f(*args, **kwargs)
            
            # Initialize cache_key
            cache_key = None
            
            # Generate cache key
            if key_func:
                try:
                    # Check if key_func expects arguments
                    import inspect
                    sig = inspect.signature(key_func)
                    if len(sig.parameters) == 0:
                        # No parameters expected, call without args
                        cache_key = key_func()
                    else:
                        # Parameters expected, call with args
                        cache_key = key_func(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"Error generating cache key: {e}")
                    # Fallback to default key generation
                    cache_key = None
            
            if not cache_key:
                # Default key generation
                key_parts = [f.__name__, str(args), str(sorted(request.args.items()))]
                if hasattr(g, 'json_data'):
                    key_parts.append(str(sorted(g.json_data.items())))
                cache_key = f"route:{'_'.join(str(part) for part in key_parts)}"
            
            # Try cache first
            try:
                cached_result = cache_manager.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"Cache hit for route {f.__name__}")
                    return cached_result
            except:
                pass
            
            # Execute function
            result = f(*args, **kwargs)
            
            # Cache successful results
            try:
                if hasattr(result, 'status_code') and result.status_code == 200:
                    cache_manager.set(cache_key, result, ttl)
                    logger.debug(f"Cached result for route {f.__name__}")
            except:
                pass
            
            return result
        return wrapper
    return decorator


def track_performance(threshold_ms: int = 1000):
    """
    Decorator to track route performance
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = f(*args, **kwargs)
                status = 'success'
                return result
            except Exception as e:
                status = 'error'
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                
                # Record performance metrics
                if profiler:
                    try:
                        profiler.record_endpoint_metric(
                            endpoint=f.__name__,
                            duration_ms=duration_ms,
                            memory_delta_mb=0,  # Could bewith actual memory tracking
                            status=status
                        )
                    except:
                        pass
                
                # Log slow routes
                if duration_ms > threshold_ms:
                    logger.warning(f"Slow route: {f.__name__} took {duration_ms:.2f}ms")
        return wrapper
    return decorator

def limit_concurrent_requests(max_requests: int = 5):
    """
    Decorator to limit concurrent requests to a route
    """
    request_counters = {}
    
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            route_name = f.__name__
            
            # Initialize counter if not exists
            if route_name not in request_counters:
                request_counters[route_name] = 0
            
            # Check if limit exceeded
            if request_counters[route_name] >= max_requests:
                if request.is_json:
                    return error_json(
                        "Too many concurrent requests. Please try again later.",
                        status_code=429
                    )
                else:
                    from flask import flash, redirect, url_for
                    flash("Server is busy. Please try again later.", 'warning')
                    return redirect(url_for('core.home'))
            
            # Increment counter
            request_counters[route_name] += 1
            
            try:
                return f(*args, **kwargs)
            finally:
                # Decrement counter
                request_counters[route_name] -= 1
        return wrapper
    return decorator

def validate_file_upload(allowed_extensions: set = None, max_size_mb: int = 100):
    """
    Decorator to validate file uploads
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'file' not in request.files:
                raise ValidationError("No file provided")
            
            file = request.files['file']
            if file.filename == '':
                raise ValidationError("No file selected")
            
            # Check extension
            if allowed_extensions:
                ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                if ext not in allowed_extensions:
                    raise ValidationError(f"File type not allowed. Allowed: {', '.join(allowed_extensions)}")
            
            # Check size
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            
            if file_size > max_size_mb * 1024 * 1024:
                raise ValidationError(f"File too large. Maximum size: {max_size_mb}MB")
            
            return f(*args, **kwargs)
        return wrapper
    return decorator

# Combine multiple decorators for common patterns
def api_route(require_project_check: bool = True, 
              cache_ttl: int = None,
              required_json_fields: list = None,
              max_concurrent: int = None):
    """
    Combined decorator for common API route patterns
    """
    def decorator(f: Callable) -> Callable:
        # Apply decorators in reverse order (bottom to top execution)
        decorated_func = f
        
        # Performance tracking (always applied)
        decorated_func = track_performance()(decorated_func)
        
        # Exception handling (always applied)
        decorated_func = handle_exceptions()(decorated_func)
        
        # Concurrent request limiting
        if max_concurrent:
            decorated_func = limit_concurrent_requests(max_concurrent)(decorated_func)
        
        # JSON validation
        if required_json_fields:
            decorated_func = validate_json_request(required_json_fields)(decorated_func)
        
        # Caching
        if cache_ttl:
            decorated_func = cache_route(cache_ttl)(decorated_func)
        
        # Project requirement
        if require_project_check:
            decorated_func = require_project(decorated_func)
        
        return decorated_func
    return decorator