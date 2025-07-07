# utils/response_utils.py
"""
Enhanced API response utilities with middleware and performance tracking
"""
import logging
import time
import uuid
from datetime import datetime
from functools import wraps
from flask import jsonify, request, g, current_app
from typing import Any, Dict, Optional, Union
from .constants import API_STATUS

logger = logging.getLogger(__name__)

class ResponseMiddleware:
    """
    Response middleware for tracking performance and adding headers
    """
    
    def __init__(self, app=None):
        self.app = app
        self.request_count = 0
        self.total_response_time = 0
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize middleware with Flask app"""
        app.before_request(self._before_request)
        app.after_request(self._after_request)
        app.teardown_appcontext(self._teardown)
        logger.info("ResponseMiddleware initialized")
    
    def _before_request(self):
        """Set up request tracking"""
        g.start_time = time.time()
        g.request_id = str(uuid.uuid4())[:8]
        g.request_start_memory = self._get_memory_usage()
        
        # Log request start
        logger.debug(
            f"[{g.request_id}] {request.method} {request.path} started"
        )
    
    def _after_request(self, response):
        """Add performance headers and logging"""
        try:
            if hasattr(g, 'start_time'):
                duration = time.time() - g.start_time
                
                # Update statistics
                self.request_count += 1
                self.total_response_time += duration
                
                # Add performance headers
                response.headers['X-Request-ID'] = getattr(g, 'request_id', 'unknown')
                response.headers['X-Response-Time'] = f"{duration:.3f}s"
                response.headers['X-Request-Count'] = str(self.request_count)
                
                # Memory usage if available
                if hasattr(g, 'request_start_memory'):
                    current_memory = self._get_memory_usage()
                    memory_delta = current_memory - g.request_start_memory
                    if memory_delta > 0:
                        response.headers['X-Memory-Delta'] = f"{memory_delta:.1f}MB"
                
                # Log response
                log_level = logging.WARNING if duration > 5.0 else logging.INFO
                logger.log(
                    log_level,
                    f"[{g.request_id}] {request.method} {request.path} "
                    f"- {response.status_code} - {duration:.3f}s"
                )
                
                # Log slow requests
                if duration > 10.0:
                    logger.warning(
                        f"[{g.request_id}] SLOW REQUEST: {request.method} {request.path} "
                        f"took {duration:.3f}s"
                    )
        
        except Exception as e:
            logger.error(f"Error in response middleware: {e}")
        
        return response
    
    def _teardown(self, exception):
        """Clean up after request"""
        if exception:
            logger.error(
                f"[{getattr(g, 'request_id', 'unknown')}] Request failed: {exception}"
            )
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            return psutil.Process().memory_info().rss / (1024 * 1024)
        except ImportError:
            return 0.0
        except Exception:
            return 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get middleware statistics"""
        avg_response_time = (
            self.total_response_time / self.request_count 
            if self.request_count > 0 else 0
        )
        
        return {
            'total_requests': self.request_count,
            'total_response_time': round(self.total_response_time, 3),
            'average_response_time': round(avg_response_time, 3),
            'requests_per_second': round(
                self.request_count / max(self.total_response_time, 1), 2
            )
        }

# Global middleware instance
response_middleware = ResponseMiddleware()

def create_response(status: str, message: str = None, data: Any = None, 
                   error: str = None, **kwargs) -> Dict[str, Any]:
    """
    Create a standardized API response withmetadata
    
    Args:
        status: Response status from API_STATUS constants
        message: Human-readable message
        data: Response data
        error: Error details
        **kwargs: Additional response fields
    
    Returns:
        Standardized response dictionary
    """
    response = {
        'status': status,
        'timestamp': datetime.now().isoformat()
    }
    
    # Add request ID if available
    if hasattr(g, 'request_id'):
        response['request_id'] = g.request_id
    
    # Add performance info if available
    if hasattr(g, 'start_time'):
        response['response_time_ms'] = round((time.time() - g.start_time) * 1000, 2)
    
    if message:
        response['message'] = message
    
    if data is not None:
        response['data'] = data
    
    if error:
        response['error'] = error
    
    # Add any additional fields
    response.update(kwargs)
    
    return response

def success_response(message: str = None, data: Any = None, **kwargs) -> Dict[str, Any]:
    """Create a success response with performance tracking"""
    return create_response(API_STATUS['SUCCESS'], message, data, **kwargs)

def error_response(message: str = None, error: str = None, **kwargs) -> Dict[str, Any]:
    """Create an error response with context"""
    return create_response(API_STATUS['ERROR'], message, error=error, **kwargs)

def warning_response(message: str = None, data: Any = None, **kwargs) -> Dict[str, Any]:
    """Create a warning response"""
    return create_response(API_STATUS['WARNING'], message, data, **kwargs)

def info_response(message: str = None, data: Any = None, **kwargs) -> Dict[str, Any]:
    """Create an info response"""
    return create_response(API_STATUS['INFO'], message, data, **kwargs)

def json_response(status: str, message: str = None, data: Any = None, 
                 error: str = None, status_code: int = 200, **kwargs):
    """
    Create a JSON response with Flask jsonify and proper status code
    
    Args:
        status: Response status
        message: Response message
        data: Response data
        error: Error details
        status_code: HTTP status code
        **kwargs: Additional response fields
    
    Returns:
        Flask Response with JSON and status code
    """
    response = create_response(status, message, data, error, **kwargs)
    return jsonify(response), status_code

def success_json(message: str = None, data: Any = None, **kwargs):
    """Create a success JSON response"""
    return json_response(API_STATUS['SUCCESS'], message, data, status_code=200, **kwargs)

def error_json(message: str = None, error: str = None, status_code: int = 500, **kwargs):
    """Create an error JSON response"""
    return json_response(API_STATUS['ERROR'], message, error=error, status_code=status_code, **kwargs)

def warning_json(message: str = None, data: Any = None, status_code: int = 200, **kwargs):
    """Create a warning JSON response"""
    return json_response(API_STATUS['WARNING'], message, data, status_code=status_code, **kwargs)

def validation_error_json(message: str = "Validation failed", errors: list = None, **kwargs):
    """Create a validation error response"""
    return json_response(
        API_STATUS['ERROR'], 
        message, 
        error="Validation Error",
        validation_errors=errors or [],
        status_code=400,
        **kwargs
    )

def not_found_json(message: str = "Resource not found", **kwargs):
    """Create a not found response"""
    return json_response(API_STATUS['ERROR'], message, status_code=404, **kwargs)

def unauthorized_json(message: str = "Unauthorized access", **kwargs):
    """Create an unauthorized response"""
    return json_response(API_STATUS['ERROR'], message, status_code=401, **kwargs)

def handle_exception_response(e: Exception, context: str = "Operation") -> Dict[str, Any]:
    """
    Handle exceptions and create appropriate error responses
    
    Args:
        e: The exception that occurred
        context: Context where the exception occurred
    
    Returns:
        Error response dictionary
    """
    error_message = f"{context} failed: {str(e)}"
    logger.exception(f"Exception in {context}: {e}")
    
    # Add request ID if available
    request_id = getattr(g, 'request_id', None)
    
    # Determine error type and appropriate response
    if isinstance(e, ValueError):
        return error_response(
            message="Invalid input provided",
            error=str(e),
            error_type="ValidationError",
            request_id=request_id
        )
    elif isinstance(e, PermissionError):
        return error_response(
            message="Permission denied",
            error=str(e),
            error_type="PermissionError",
            request_id=request_id
        )
    elif isinstance(e, FileNotFoundError):
        return error_response(
            message="Required file not found",
            error=str(e),
            error_type="FileNotFoundError",
            request_id=request_id
        )
    elif isinstance(e, MemoryError):
        return error_response(
            message="Insufficient memory for operation",
            error=str(e),
            error_type="MemoryError",
            request_id=request_id
        )
    else:
        return error_response(
            message=error_message,
            error=str(e),
            error_type=type(e).__name__,
            request_id=request_id
        )

def handle_exception_json(e: Exception, context: str = "Operation", status_code: int = 500):
    """
    Handle exceptions and create appropriate JSON error responses
    
    Args:
        e: The exception that occurred
        context: Context where the exception occurred
        status_code: HTTP status code to return
    
    Returns:
        Flask Response with JSON error response
    """
    response_data = handle_exception_response(e, context)
    
    # Determine appropriate status code based on exception type
    if isinstance(e, ValueError):
        status_code = 400
    elif isinstance(e, PermissionError):
        status_code = 403
    elif isinstance(e, FileNotFoundError):
        status_code = 404
    elif isinstance(e, MemoryError):
        status_code = 507  # Insufficient Storage
    
    return jsonify(response_data), status_code

def paginated_response(data: list, page: int = 1, per_page: int = 10, 
                      total: int = None, **kwargs) -> Dict[str, Any]:
    """
    Create a paginated response with navigation metadata
    
    Args:
        data: Page data
        page: Current page number
        per_page: Items per page
        total: Total items count
        **kwargs: Additional response fields
    
    Returns:
        Paginated response with navigation info
    """
    if total is None:
        total = len(data)
    
    total_pages = (total + per_page - 1) // per_page
    
    pagination_info = {
        'page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': total_pages,
        'has_next': page < total_pages,
        'has_prev': page > 1,
        'next_page': page + 1 if page < total_pages else None,
        'prev_page': page - 1 if page > 1 else None
    }
    
    return success_response(
        data=data,
        pagination=pagination_info,
        **kwargs
    )

def file_response_info(filename: str, file_path: str, file_size: int = None) -> Dict[str, Any]:
    """
    Create file information for responses
    
    Args:
        filename: Name of the file
        file_path: Path to the file
        file_size: File size in bytes
    
    Returns:
        File information dictionary
    """
    import os
    
    if file_size is None and os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
    
    return {
        'filename': filename,
        'path': file_path,
        'size_bytes': file_size,
        'size_mb': round(file_size / (1024 * 1024), 2) if file_size else None,
        'exists': os.path.exists(file_path),
        'mime_type': get_mime_type(filename)
    }

def get_mime_type(filename: str) -> str:
    """Get MIME type for a filename"""
    import mimetypes
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or 'application/octet-stream'

def progress_response(progress: int, message: str = None, current_step: int = None, 
                     total_steps: int = None, **kwargs) -> Dict[str, Any]:
    """
    Create a progress response for long-running operations
    
    Args:
        progress: Progress percentage (0-100)
        message: Progress message
        current_step: Current step number
        total_steps: Total number of steps
        **kwargs: Additional fields
    
    Returns:
        Progress response with timing estimates
    """
    # Ensure progress is within bounds
    progress = max(0, min(100, progress))
    
    response_data = {
        'progress': progress,
        'message': message or f"Progress: {progress}%",
        'completed': progress >= 100
    }
    
    if current_step is not None and total_steps is not None:
        response_data.update({
            'current_step': current_step,
            'total_steps': total_steps,
            'step_progress': f"{current_step}/{total_steps}"
        })
    
    # Add estimated time remaining if we have timing data
    if hasattr(g, 'start_time') and progress > 0:
        elapsed_time = time.time() - g.start_time
        if progress < 100:
            estimated_total_time = (elapsed_time / progress) * 100
            estimated_remaining = estimated_total_time - elapsed_time
            response_data['estimated_remaining_seconds'] = round(estimated_remaining, 1)
        response_data['elapsed_seconds'] = round(elapsed_time, 1)
    
    return success_response(
        message=response_data['message'],
        data=response_data,
        **kwargs
    )

def streaming_response(generator_func, mimetype: str = 'application/json', 
                      headers: Dict[str, str] = None):
    """
    Create a streaming response for large datasets
    
    Args:
        generator_func: Generator function that yields data chunks
        mimetype: MIME type for the response
        headers: Additional headers
    
    Returns:
        Flask streaming response
    """
    from flask import Response, current_app
    
    def generate_with_error_handling():
        try:
            request_id = getattr(g, 'request_id', 'unknown')
            logger.info(f"[{request_id}] Starting streaming response")
            
            chunk_count = 0
            for chunk in generator_func():
                chunk_count += 1
                yield chunk
            
            logger.info(f"[{request_id}] Streaming completed: {chunk_count} chunks")
            
        except Exception as e:
            logger.exception(f"Error in streaming response: {e}")
            # Yield error in JSON format
            error_chunk = json.dumps({
                'status': 'error',
                'message': 'Streaming failed',
                'error': str(e)
            })
            yield f"data: {error_chunk}\n\n"
    
    response_headers = {
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
    }
    
    if headers:
        response_headers.update(headers)
    
    return Response(
        generate_with_error_handling(),
        mimetype=mimetype,
        headers=response_headers
    )

# Performance tracking decorators
def track_response_time(threshold_ms: float = 1000):
    """
    Decorator to track and log response times
    
    Args:
        threshold_ms: Log warning if response time exceeds this threshold
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = f(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.time() - start_time) * 1000
                if duration_ms > threshold_ms:
                    logger.warning(
                        f"Function {f.__name__} took {duration_ms:.2f}ms "
                        f"(threshold: {threshold_ms}ms)"
                    )
        return wrapper
    return decorator

def cache_response(ttl: int = 300, key_func: callable = None):
    """
    Decorator to cache response data
    
    Args:
        ttl: Time to live in seconds
        key_func: Function to generate cache key
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{f.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            
            # Try to get from cache
            try:
                from .cache_manager import cache_manager
                cached_result = cache_manager.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"Cache hit for {f.__name__}")
                    return cached_result
            except ImportError:
                pass  # Cache manager not available
            
            # Execute function and cache result
            result = f(*args, **kwargs)
            
            try:
                from .cache_manager import cache_manager
                cache_manager.set(cache_key, result, ttl)
                logger.debug(f"Cached result for {f.__name__}")
            except ImportError:
                pass  # Cache manager not available
            
            return result
        return wrapper
    return decorator