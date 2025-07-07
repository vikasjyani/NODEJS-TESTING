# utils/error_handlers.py
"""
Standardized error handling system with categorization and logging
"""
import logging
import traceback
import time
from functools import wraps
from flask import request, jsonify, g, current_app
from typing import Callable, Dict, Any, List, Optional
from collections import defaultdict, deque
from datetime import datetime

logger = logging.getLogger(__name__)

# ========== Custom Exception Classes ==========

class ValidationError(Exception):
    """Custom validation error for input validation failures"""
    
    def __init__(self, message: str, field: str = None, value: Any = None):
        super().__init__(message)
        self.field = field
        self.value = value
        self.message = message
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'type': 'ValidationError',
            'message': self.message,
            'field': self.field,
            'value': str(self.value) if self.value is not None else None
        }

class BusinessLogicError(Exception):
    """Custom business logic error for application-specific failures"""
    
    def __init__(self, message: str, error_code: str = None, context: Dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'type': 'BusinessLogicError',
            'message': self.message,
            'error_code': self.error_code,
            'context': self.context
        }

class ResourceNotFoundError(Exception):
    """Custom error for missing resources"""
    
    def __init__(self, resource_type: str, resource_id: str = None, message: str = None):
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.message = message or f"{resource_type} not found"
        if resource_id:
            self.message += f": {resource_id}"
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'type': 'ResourceNotFoundError',
            'message': self.message,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id
        }

class ConfigurationError(Exception):
    """Custom error for configuration issues"""
    
    def __init__(self, message: str, config_key: str = None, expected_value: str = None):
        super().__init__(message)
        self.message = message
        self.config_key = config_key
        self.expected_value = expected_value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'type': 'ConfigurationError',
            'message': self.message,
            'config_key': self.config_key,
            'expected_value': self.expected_value
        }

class ProcessingError(Exception):
    """Custom error for data processing failures"""
    
    def __init__(self, message: str, operation: str = None, data_info: Dict = None):
        super().__init__(message)
        self.message = message
        self.operation = operation
        self.data_info = data_info or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'type': 'ProcessingError',
            'message': self.message,
            'operation': self.operation,
            'data_info': self.data_info
        }

# ========== Error Statistics and Tracking ==========

class ErrorTracker:
    """Track and analyze error patterns"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.error_history = deque(maxlen=max_history)
        self.error_counts = defaultdict(int)
        self.error_rates = defaultdict(list)
        self.last_cleanup = time.time()
    
    def record_error(self, error_type: str, blueprint: str, message: str, 
                    request_path: str = None, user_id: str = None):
        """Record an error occurrence"""
        timestamp = time.time()
        
        error_record = {
            'timestamp': timestamp,
            'datetime': datetime.fromtimestamp(timestamp).isoformat(),
            'error_type': error_type,
            'blueprint': blueprint,
            'message': message,
            'request_path': request_path or getattr(request, 'path', 'unknown'),
            'user_id': user_id,
            'request_id': getattr(g, 'request_id', None),
            'traceback': traceback.format_exc()
        }
        
        self.error_history.append(error_record)
        
        # Update counters
        error_key = f"{error_type}:{blueprint}"
        self.error_counts[error_key] += 1
        
        # Track error rates (errors per hour)
        current_hour = int(timestamp // 3600)
        self.error_rates[error_key].append(current_hour)
        
        # Clean up old rate data periodically
        if timestamp - self.last_cleanup > 3600:  # Every hour
            self._cleanup_rate_data(current_hour)
            self.last_cleanup = timestamp
    
    def _cleanup_rate_data(self, current_hour: int):
        """Clean up old error rate data (keep last 24 hours)"""
        cutoff_hour = current_hour - 24
        
        for error_key in self.error_rates:
            self.error_rates[error_key] = [
                hour for hour in self.error_rates[error_key] 
                if hour > cutoff_hour
            ]
    
    def get_error_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get error statistics for the specified time period"""
        cutoff_time = time.time() - (hours * 3600)
        
        # Filter recent errors
        recent_errors = [
            error for error in self.error_history 
            if error['timestamp'] > cutoff_time
        ]
        
        # Calculate statistics
        total_errors = len(recent_errors)
        
        # Error counts by type
        error_by_type = defaultdict(int)
        error_by_blueprint = defaultdict(int)
        
        for error in recent_errors:
            error_by_type[error['error_type']] += 1
            error_by_blueprint[error['blueprint']] += 1
        
        # Most common errors
        most_common_errors = sorted(
            self.error_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # Error rate (errors per hour)
        error_rate = total_errors / hours if hours > 0 else 0
        
        return {
            'time_period_hours': hours,
            'total_errors': total_errors,
            'error_rate_per_hour': round(error_rate, 2),
            'errors_by_type': dict(error_by_type),
            'errors_by_blueprint': dict(error_by_blueprint),
            'most_common_errors': most_common_errors,
            'recent_errors': recent_errors[-10:],  # Last 10 errors
            'error_trends': self._calculate_error_trends(hours)
        }
    
    def _calculate_error_trends(self, hours: int) -> Dict[str, Any]:
        """Calculate error trends over time"""
        current_hour = int(time.time() // 3600)
        hourly_counts = defaultdict(int)
        
        # Count errors by hour
        cutoff_hour = current_hour - hours
        for error in self.error_history:
            error_hour = int(error['timestamp'] // 3600)
            if error_hour > cutoff_hour:
                hourly_counts[error_hour] += 1
        
        # Calculate trend
        if len(hourly_counts) > 1:
            hours_list = sorted(hourly_counts.keys())
            if len(hours_list) >= 2:
                recent_rate = hourly_counts[hours_list[-1]]
                previous_rate = sum(hourly_counts[h] for h in hours_list[-6:-1]) / 5 if len(hours_list) > 5 else hourly_counts[hours_list[-2]]
                
                if previous_rate > 0:
                    trend_percentage = ((recent_rate - previous_rate) / previous_rate) * 100
                else:
                    trend_percentage = 0
            else:
                trend_percentage = 0
        else:
            trend_percentage = 0
        
        return {
            'hourly_counts': dict(hourly_counts),
            'trend_percentage': round(trend_percentage, 1),
            'is_increasing': trend_percentage > 10,
            'is_decreasing': trend_percentage < -10
        }

# Global error tracker
error_tracker = ErrorTracker()

# ========== Standard Error Handler ==========

class StandardErrorHandler:
    """
    Centralized error handling with categorization, logging, and analytics
    """
    
    def __init__(self):
        self.tracker = error_tracker
        logger.info("StandardErrorHandler initialized")
    
    def handle_blueprint_error(self, blueprint_name: str):
        """Decorator for standardized blueprint error handling"""
        def decorator(f: Callable) -> Callable:
            @wraps(f)
            def wrapper(*args, **kwargs):
                try:
                    return f(*args, **kwargs)
                
                except ValidationError as e:
                    return self._handle_validation_error(e, blueprint_name, f.__name__)
                
                except BusinessLogicError as e:
                    return self._handle_business_logic_error(e, blueprint_name, f.__name__)
                
                except ResourceNotFoundError as e:
                    return self._handle_resource_not_found_error(e, blueprint_name, f.__name__)
                
                except ConfigurationError as e:
                    return self._handle_configuration_error(e, blueprint_name, f.__name__)
                
                except ProcessingError as e:
                    return self._handle_processing_error(e, blueprint_name, f.__name__)
                
                except FileNotFoundError as e:
                    return self._handle_file_not_found_error(e, blueprint_name, f.__name__)
                
                except PermissionError as e:
                    return self._handle_permission_error(e, blueprint_name, f.__name__)
                
                except MemoryError as e:
                    return self._handle_memory_error(e, blueprint_name, f.__name__)
                
                except ValueError as e:
                    return self._handle_value_error(e, blueprint_name, f.__name__)
                
                except TypeError as e:
                    return self._handle_type_error(e, blueprint_name, f.__name__)
                
                except Exception as e:
                    return self._handle_unexpected_error(e, blueprint_name, f.__name__)
            
            return wrapper
        return decorator
    
    def _handle_validation_error(self, e: ValidationError, blueprint: str, function: str):
        """Handle validation errors"""
        error_msg = f"[{blueprint}.{function}] Validation error: {e.message}"
        logger.warning(error_msg)
        
        self.tracker.record_error('validation', blueprint, str(e))
        
        if request.is_json:
            from .response_utils import validation_error_json
            return validation_error_json(
                message=e.message,
                errors=[e.to_dict()],
                field=e.field
            )
        else:
            from flask import flash, redirect, url_for
            flash(e.message, 'warning')
            return redirect(url_for('core.home'))
    
    def _handle_business_logic_error(self, e: BusinessLogicError, blueprint: str, function: str):
        """Handle business logic errors"""
        error_msg = f"[{blueprint}.{function}] Business logic error: {e.message}"
        logger.error(error_msg)
        
        self.tracker.record_error('business_logic', blueprint, str(e))
        
        if request.is_json:
            from .response_utils import error_json
            return error_json(
                message=e.message,
                error=e.to_dict(),
                status_code=400
            )
        else:
            from flask import flash, redirect, url_for
            flash(e.message, 'danger')
            return redirect(url_for('core.home'))
    
    def _handle_resource_not_found_error(self, e: ResourceNotFoundError, blueprint: str, function: str):
        """Handle resource not found errors"""
        error_msg = f"[{blueprint}.{function}] Resource not found: {e.message}"
        logger.warning(error_msg)
        
        self.tracker.record_error('resource_not_found', blueprint, str(e))
        
        if request.is_json:
            from .response_utils import not_found_json
            return not_found_json(
                message=e.message,
                resource_type=e.resource_type,
                resource_id=e.resource_id
            )
        else:
            from flask import flash, redirect, url_for
            flash(e.message, 'warning')
            return redirect(url_for('core.home'))
    
    def _handle_configuration_error(self, e: ConfigurationError, blueprint: str, function: str):
        """Handle configuration errors"""
        error_msg = f"[{blueprint}.{function}] Configuration error: {e.message}"
        logger.error(error_msg)
        
        self.tracker.record_error('configuration', blueprint, str(e))
        
        if request.is_json:
            from .response_utils import error_json
            return error_json(
                message="System configuration error",
                error=e.to_dict(),
                status_code=500
            )
        else:
            from flask import flash, redirect, url_for
            flash("System configuration error occurred", 'danger')
            return redirect(url_for('core.home'))
    
    def _handle_processing_error(self, e: ProcessingError, blueprint: str, function: str):
        """Handle data processing errors"""
        error_msg = f"[{blueprint}.{function}] Processing error: {e.message}"
        logger.error(error_msg)
        
        self.tracker.record_error('processing', blueprint, str(e))
        
        if request.is_json:
            from .response_utils import error_json
            return error_json(
                message=f"Data processing failed: {e.message}",
                error=e.to_dict(),
                status_code=500
            )
        else:
            from flask import flash, redirect, url_for
            flash(f"Data processing failed: {e.message}", 'danger')
            return redirect(url_for('core.home'))
    
    def _handle_file_not_found_error(self, e: FileNotFoundError, blueprint: str, function: str):
        """Handle file not found errors"""
        error_msg = f"[{blueprint}.{function}] File not found: {str(e)}"
        logger.error(error_msg)
        
        self.tracker.record_error('file_not_found', blueprint, str(e))
        
        if request.is_json:
            from .response_utils import error_json
            return error_json("Required file not found", status_code=404)
        else:
            from flask import flash, redirect, url_for
            flash("Required file not found", 'danger')
            return redirect(url_for('core.home'))
    
    def _handle_permission_error(self, e: PermissionError, blueprint: str, function: str):
        """Handle permission errors"""
        error_msg = f"[{blueprint}.{function}] Permission denied: {str(e)}"
        logger.error(error_msg)
        
        self.tracker.record_error('permission', blueprint, str(e))
        
        if request.is_json:
            from .response_utils import error_json
            return error_json("Permission denied", status_code=403)
        else:
            from flask import flash, redirect, url_for
            flash("Permission denied", 'danger')
            return redirect(url_for('core.home'))
    
    def _handle_memory_error(self, e: MemoryError, blueprint: str, function: str):
        """Handle memory errors"""
        error_msg = f"[{blueprint}.{function}] Memory error: {str(e)}"
        logger.critical(error_msg)
        
        self.tracker.record_error('memory', blueprint, str(e))
        
        # Try to clean up memory
        try:
            import gc
            gc.collect()
        except:
            pass
        
        if request.is_json:
            from .response_utils import error_json
            return error_json("Insufficient memory to complete operation", status_code=507)
        else:
            from flask import flash, redirect, url_for
            flash("System temporarily overloaded. Please try again later.", 'danger')
            return redirect(url_for('core.home'))
    
    def _handle_value_error(self, e: ValueError, blueprint: str, function: str):
        """Handle value errors (often input validation issues)"""
        error_msg = f"[{blueprint}.{function}] Value error: {str(e)}"
        logger.warning(error_msg)
        
        self.tracker.record_error('value_error', blueprint, str(e))
        
        if request.is_json:
            from .response_utils import validation_error_json
            return validation_error_json(f"Invalid input: {str(e)}")
        else:
            from flask import flash, redirect, url_for
            flash(f"Invalid input: {str(e)}", 'warning')
            return redirect(url_for('core.home'))
    
    def _handle_type_error(self, e: TypeError, blueprint: str, function: str):
        """Handle type errors"""
        error_msg = f"[{blueprint}.{function}] Type error: {str(e)}"
        logger.error(error_msg)
        
        self.tracker.record_error('type_error', blueprint, str(e))
        
        if request.is_json:
            from .response_utils import error_json
            return error_json("Internal processing error", status_code=500)
        else:
            from flask import flash, redirect, url_for
            flash("An internal error occurred", 'danger')
            return redirect(url_for('core.home'))
    
    def _handle_unexpected_error(self, e: Exception, blueprint: str, function: str):
        """Handle unexpected errors"""
        error_msg = f"[{blueprint}.{function}] Unexpected error: {str(e)}"
        logger.exception(error_msg)
        
        self.tracker.record_error('unexpected', blueprint, str(e))
        
        if request.is_json:
            from .response_utils import error_json
            return error_json("An unexpected error occurred", status_code=500)
        else:
            from flask import flash, redirect, url_for
            flash("An unexpected error occurred", 'danger')
            return redirect(url_for('core.home'))
    
    def get_error_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive error statistics"""
        return self.tracker.get_error_stats(hours)
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get a summary of recent error activity"""
        stats = self.tracker.get_error_stats(24)
        
        return {
            'total_errors_24h': stats['total_errors'],
            'error_rate_per_hour': stats['error_rate_per_hour'],
            'most_common_error': stats['most_common_errors'][0] if stats['most_common_errors'] else None,
            'trending_up': stats['error_trends']['is_increasing'],
            'trending_down': stats['error_trends']['is_decreasing'],
            'health_status': self._determine_health_status(stats)
        }
    
    def _determine_health_status(self, stats: Dict[str, Any]) -> str:
        """Determine overall system health based on error statistics"""
        error_rate = stats['error_rate_per_hour']
        is_increasing = stats['error_trends']['is_increasing']
        
        if error_rate > 50:
            return 'critical'
        elif error_rate > 20 or is_increasing:
            return 'warning'
        elif error_rate > 5:
            return 'degraded'
        else:
            return 'healthy'

# ========== Error Reporting and Alerting ==========

class ErrorAlerting:
    """Handle error alerting and notifications"""
    
    def __init__(self, error_handler: StandardErrorHandler):
        self.error_handler = error_handler
        self.alert_thresholds = {
            'critical_errors_per_hour': 50,
            'memory_errors_per_hour': 5,
            'error_rate_increase_percentage': 100  # 100% increase
        }
    
    def check_alert_conditions(self) -> List[Dict[str, Any]]:
        """Check if any alert conditions are met"""
        alerts = []
        stats = self.error_handler.get_error_stats(1)  # Last hour
        
        # Critical error rate
        if stats['error_rate_per_hour'] > self.alert_thresholds['critical_errors_per_hour']:
            alerts.append({
                'type': 'critical_error_rate',
                'message': f"High error rate: {stats['error_rate_per_hour']} errors/hour",
                'severity': 'critical',
                'data': {'error_rate': stats['error_rate_per_hour']}
            })
        
        # Memory errors
        memory_errors = stats['errors_by_type'].get('memory', 0)
        if memory_errors > self.alert_thresholds['memory_errors_per_hour']:
            alerts.append({
                'type': 'memory_errors',
                'message': f"Multiple memory errors: {memory_errors} in last hour",
                'severity': 'critical',
                'data': {'memory_errors': memory_errors}
            })
        
        # Error rate trend
        if stats['error_trends']['is_increasing']:
            trend_pct = stats['error_trends']['trend_percentage']
            if trend_pct > self.alert_thresholds['error_rate_increase_percentage']:
                alerts.append({
                    'type': 'error_rate_spike',
                    'message': f"Error rate increased by {trend_pct:.1f}%",
                    'severity': 'warning',
                    'data': {'trend_percentage': trend_pct}
                })
        
        return alerts

# Global instances
standard_error_handler = StandardErrorHandler()
error_alerting = ErrorAlerting(standard_error_handler)

# ========== Utility Functions ==========

def log_error_context(error: Exception, context: Dict[str, Any] = None):
    """Log error with additional context information"""
    context = context or {}
    
    # Add request context if available
    try:
        context.update({
            'request_method': request.method,
            'request_path': request.path,
            'request_args': dict(request.args),
            'request_id': getattr(g, 'request_id', None),
            'user_agent': request.headers.get('User-Agent'),
            'remote_addr': request.remote_addr
        })
    except RuntimeError:
        # Outside request context
        pass
    
    logger.error(
        f"Error occurred: {type(error).__name__}: {str(error)}",
        extra={'context': context},
        exc_info=True
    )

def create_error_report(hours: int = 24) -> Dict[str, Any]:
    """Create a comprehensive error report"""
    stats = standard_error_handler.get_error_stats(hours)
    alerts = error_alerting.check_alert_conditions()
    summary = standard_error_handler.get_error_summary()
    
    return {
        'report_generated': datetime.now().isoformat(),
        'time_period_hours': hours,
        'summary': summary,
        'detailed_stats': stats,
        'active_alerts': alerts,
        'recommendations': generate_error_recommendations(stats, alerts)
    }

def generate_error_recommendations(stats: Dict[str, Any], alerts: List[Dict[str, Any]]) -> List[str]:
    """Generate recommendations based on error patterns"""
    recommendations = []
    
    # High error rate
    if stats['error_rate_per_hour'] > 20:
        recommendations.append("High error rate detected. Review recent code changes and increase monitoring.")
    
    # Memory issues
    if stats['errors_by_type'].get('memory', 0) > 2:
        recommendations.append("Memory errors detected. Check for memory leaks and optimize data processing.")
    
    # Validation errors
    if stats['errors_by_type'].get('validation', 0) > stats['total_errors'] * 0.3:
        recommendations.append("High validation error rate. Review input validation and user documentation.")
    
    # Configuration errors
    if stats['errors_by_type'].get('configuration', 0) > 0:
        recommendations.append("Configuration errors detected. Verify system configuration and environment variables.")
    
    # Trending issues
    if stats['error_trends']['is_increasing']:
        recommendations.append("Error rate is increasing. Investigate recent changes and monitor system resources.")
    
    # Blueprint-specific issues
    blueprint_errors = stats['errors_by_blueprint']
    if blueprint_errors:
        top_error_blueprint = max(blueprint_errors.items(), key=lambda x: x[1])
        if top_error_blueprint[1] > stats['total_errors'] * 0.4:
            recommendations.append(f"High error concentration in {top_error_blueprint[0]} blueprint. Focus debugging efforts here.")
    
    return recommendations