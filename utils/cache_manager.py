# utils/cache_manager.py
"""
Advanced caching system with Redis fallback and intelligent cache management
"""
import redis
import json
import hashlib
import pickle
import time
import logging
from functools import wraps
from typing import Any, Optional, Callable, Dict, Union
from collections import OrderedDict
import threading
import psutil

logger = logging.getLogger(__name__)

class TTLCache:
    """Thread-safe TTL cache implementation"""
    
    def __init__(self, maxsize: int = 1000, default_ttl: int = 300):
        self.maxsize = maxsize
        self.default_ttl = default_ttl
        self.cache = OrderedDict()
        self.timestamps = {}
        self.lock = threading.RLock()
    
    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired"""
        if key not in self.timestamps:
            return True
        return time.time() - self.timestamps[key] > self.default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self.lock:
            if key in self.cache and not self._is_expired(key):
                # Move to end (LRU)
                value = self.cache.pop(key)
                self.cache[key] = value
                return value
            elif key in self.cache:
                # Expired, remove
                del self.cache[key]
                del self.timestamps[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        with self.lock:
            if len(self.cache) >= self.maxsize:
                # Remove oldest
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                del self.timestamps[oldest_key]
            
            self.cache[key] = value
            self.timestamps[key] = time.time()
    
    def clear(self) -> None:
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()
            self.timestamps.clear()

class CacheManager:
    """
    Multi-tier caching system with Redis primary and memory fallback
    """
    
    def __init__(self, redis_url: str = None, memory_cache_size: int = 1000):
        self.redis_client = None
        self.memory_cache = TTLCache(maxsize=memory_cache_size)
        self.hit_stats = {'redis': 0, 'memory': 0, 'miss': 0}
        self.lock = threading.RLock()
        
        # Try to connect to Redis
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                self.redis_client.ping()
                logger.info("Redis cache connected successfully")
            except Exception as e:
                logger.warning(f"Redis connection failed, falling back to memory cache: {e}")
                self.redis_client = None
        
        # Monitor memory usage
        self.memory_threshold = 0.8  # 80% of available memory
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate deterministic cache key"""
        key_data = f"{prefix}:{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _serialize_value(self, value: Any) -> str:
        """Serialize value for storage"""
        try:
            # Try JSON first (faster)
            return json.dumps(value, default=str)
        except (TypeError, ValueError):
            # Fallback to pickle (more flexible)
            return pickle.dumps(value).hex()
    
    def _deserialize_value(self, serialized: str) -> Any:
        """Deserialize value from storage"""
        try:
            # Try JSON first
            return json.loads(serialized)
        except (json.JSONDecodeError, ValueError):
            try:
                # Try pickle
                return pickle.loads(bytes.fromhex(serialized))
            except Exception:
                # Return as string if all else fails
                return serialized
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache (Redis -> Memory -> None)"""
        with self.lock:
            # Try Redis first
            if self.redis_client:
                try:
                    value = self.redis_client.get(key)
                    if value is not None:
                        self.hit_stats['redis'] += 1
                        return self._deserialize_value(value)
                except Exception as e:
                    logger.debug(f"Redis get error: {e}")
            
            # Try memory cache
            value = self.memory_cache.get(key)
            if value is not None:
                self.hit_stats['memory'] += 1
                return value
            
            self.hit_stats['miss'] += 1
            return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache (both Redis and Memory)"""
        try:
            serialized = self._serialize_value(value)
            
            # Store in Redis if available
            if self.redis_client:
                try:
                    self.redis_client.setex(key, ttl, serialized)
                except Exception as e:
                    logger.debug(f"Redis set error: {e}")
            
            # Store in memory cache
            self.memory_cache.set(key, value, ttl)
            return True
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from all cache layers"""
        success = False
        
        if self.redis_client:
            try:
                self.redis_client.delete(key)
                success = True
            except Exception as e:
                logger.debug(f"Redis delete error: {e}")
        
        # Remove from memory cache
        with self.memory_cache.lock:
            if key in self.memory_cache.cache:
                del self.memory_cache.cache[key]
                del self.memory_cache.timestamps[key]
                success = True
        
        return success
    
    def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern"""
        cleared = 0
        
        if self.redis_client:
            try:
                keys = self.redis_client.keys(pattern)
                if keys:
                    cleared += self.redis_client.delete(*keys)
            except Exception as e:
                logger.debug(f"Redis pattern clear error: {e}")
        
        # Clear from memory cache
        with self.memory_cache.lock:
            keys_to_remove = [
                k for k in self.memory_cache.cache.keys() 
                if pattern.replace('*', '') in k
            ]
            for key in keys_to_remove:
                del self.memory_cache.cache[key]
                del self.memory_cache.timestamps[key]
                cleared += 1
        
        return cleared
    
    def get_stats(self) -> Dict[str, Union[int, float]]:
        """Get cache statistics"""
        total_requests = sum(self.hit_stats.values())
        hit_rate = (self.hit_stats['redis'] + self.hit_stats['memory']) / max(total_requests, 1)
        
        return {
            'hit_rate': round(hit_rate * 100, 2),
            'redis_hits': self.hit_stats['redis'],
            'memory_hits': self.hit_stats['memory'],
            'misses': self.hit_stats['miss'],
            'total_requests': total_requests,
            'memory_cache_size': len(self.memory_cache.cache),
            'redis_connected': self.redis_client is not None
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on cache system"""
        status = {
            'healthy': True,
            'redis_available': False,
            'memory_usage_mb': psutil.Process().memory_info().rss / 1024 / 1024,
            'cache_stats': self.get_stats()
        }
        
        # Test Redis connection
        if self.redis_client:
            try:
                self.redis_client.ping()
                status['redis_available'] = True
            except Exception as e:
                status['redis_error'] = str(e)
                status['healthy'] = False
        
        # Check memory usage
        memory_percent = psutil.virtual_memory().percent
        if memory_percent > self.memory_threshold * 100:
            status['memory_warning'] = f"High memory usage: {memory_percent}%"
            status['healthy'] = False
        
        return status

# Global cache manager instance
cache_manager = CacheManager()

def cached(ttl: int = 300, prefix: str = "default", use_args: bool = True, use_kwargs: bool = True):
    """
    Decorator for caching function results
    
    Args:
        ttl: Time to live in seconds
        prefix: Cache key prefix
        use_args: Include function arguments in cache key
        use_kwargs: Include function keyword arguments in cache key
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key_parts = [prefix, func.__name__]
            
            if use_args:
                cache_key_parts.extend(str(arg) for arg in args)
            
            if use_kwargs:
                cache_key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            
            cache_key = cache_manager._generate_key(*cache_key_parts)
            
            # Try to get from cache
            result = cache_manager.get(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl)
            
            return result
        
        # Add cache control methods to function
        wrapper.cache_clear = lambda: cache_manager.clear_pattern(f"{prefix}:{func.__name__}*")
        wrapper.cache_info = lambda: cache_manager.get_stats()
        
        return wrapper
    return decorator

# ================================
# utils/performance_profiler.py
"""
Performance profiling and monitoring utilities
"""
import time
import cProfile
import pstats
import io
import psutil
import threading
from functools import wraps
from collections import defaultdict, deque
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class PerformanceProfiler:
    """
    Advanced performance profiler with real-time monitoring
    """
    
    def __init__(self, max_records: int = 1000):
        self.max_records = max_records
        self.metrics = defaultdict(deque)
        self.slow_queries = deque(maxlen=100)
        self.endpoint_stats = defaultdict(lambda: {
            'count': 0, 'total_time': 0, 'min_time': float('inf'),
            'max_time': 0, 'avg_time': 0, 'error_count': 0
        })
        self.lock = threading.RLock()
        self.profiling_enabled = True
        
        # System monitoring
        self.system_metrics = deque(maxlen=300)  # 5 minutes at 1 sample/second
        self._start_system_monitoring()
    
    def _start_system_monitoring(self):
        """Start background system monitoring"""
        def monitor():
            while self.profiling_enabled:
                try:
                    cpu_percent = psutil.cpu_percent(interval=1)
                    memory = psutil.virtual_memory()
                    disk = psutil.disk_usage('/')
                    
                    self.system_metrics.append({
                        'timestamp': time.time(),
                        'cpu_percent': cpu_percent,
                        'memory_percent': memory.percent,
                        'memory_available_gb': memory.available / (1024**3),
                        'disk_percent': disk.percent
                    })
                except Exception as e:
                    logger.debug(f"System monitoring error: {e}")
                    time.sleep(1)
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
    
    def profile_function(self, func: Callable, *args, **kwargs) -> tuple:
        """Profile a function call and return (result, profile_stats)"""
        profiler = cProfile.Profile()
        
        try:
            profiler.enable()
            result = func(*args, **kwargs)
            profiler.disable()
            
            # Get profile statistics
            stats_stream = io.StringIO()
            stats = pstats.Stats(profiler, stream=stats_stream)
            stats.sort_stats('cumulative')
            stats.print_stats(20)  # Top 20 functions
            
            profile_data = {
                'function_name': func.__name__,
                'stats_text': stats_stream.getvalue(),
                'timestamp': datetime.now().isoformat()
            }
            
            return result, profile_data
            
        except Exception as e:
            profiler.disable()
            logger.error(f"Profiling error: {e}")
            return None, {'error': str(e)}
    
    def record_endpoint_metric(self, endpoint: str, duration_ms: float, 
                             memory_delta_mb: float, status: str = 'success'):
        """Record endpoint performance metric"""
        with self.lock:
            # Update endpoint statistics
            stats = self.endpoint_stats[endpoint]
            stats['count'] += 1
            stats['total_time'] += duration_ms
            stats['min_time'] = min(stats['min_time'], duration_ms)
            stats['max_time'] = max(stats['max_time'], duration_ms)
            stats['avg_time'] = stats['total_time'] / stats['count']
            
            if status == 'error':
                stats['error_count'] += 1
            
            # Record individual metric
            metric_data = {
                'endpoint': endpoint,
                'duration_ms': duration_ms,
                'memory_delta_mb': memory_delta_mb,
                'status': status,
                'timestamp': time.time(),
                'datetime': datetime.now().isoformat()
            }
            
            self.metrics[endpoint].append(metric_data)
            
            # Maintain max records
            while len(self.metrics[endpoint]) > self.max_records:
                self.metrics[endpoint].popleft()
            
            # Track slow queries
            if duration_ms > 1000:  # > 1 second
                self.slow_queries.append(metric_data)
    
    def get_endpoint_summary(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """Get performance summary for endpoint(s)"""
        with self.lock:
            if endpoint:
                if endpoint in self.endpoint_stats:
                    return dict(self.endpoint_stats[endpoint])
                return {}
            
            # Return summary for all endpoints
            summary = {}
            for ep, stats in self.endpoint_stats.items():
                summary[ep] = dict(stats)
            
            return summary
    
    def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get slowest queries"""
        with self.lock:
            sorted_queries = sorted(
                list(self.slow_queries),
                key=lambda x: x['duration_ms'],
                reverse=True
            )
            return sorted_queries[:limit]
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get current system health metrics"""
        try:
            current_metrics = list(self.system_metrics)[-1] if self.system_metrics else {}
            
            # Calculate averages over last 5 minutes
            recent_metrics = [
                m for m in self.system_metrics 
                if time.time() - m['timestamp'] < 300
            ]
            
            if recent_metrics:
                avg_cpu = sum(m['cpu_percent'] for m in recent_metrics) / len(recent_metrics)
                avg_memory = sum(m['memory_percent'] for m in recent_metrics) / len(recent_metrics)
            else:
                avg_cpu = avg_memory = 0
            
            return {
                'current': current_metrics,
                'averages_5min': {
                    'cpu_percent': round(avg_cpu, 2),
                    'memory_percent': round(avg_memory, 2)
                },
                'healthy': avg_cpu < 80 and avg_memory < 85,
                'data_points': len(recent_metrics)
            }
            
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {'error': str(e), 'healthy': False}
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        with self.lock:
            report = {
                'timestamp': datetime.now().isoformat(),
                'endpoints': {},
                'slow_queries': self.get_slow_queries(),
                'system_health': self.get_system_health(),
                'summary': {
                    'total_endpoints': len(self.endpoint_stats),
                    'total_requests': sum(stats['count'] for stats in self.endpoint_stats.values()),
                    'total_errors': sum(stats['error_count'] for stats in self.endpoint_stats.values()),
                    'slowest_endpoint': None,
                    'fastest_endpoint': None
                }
            }
            
            # Add endpoint details
            for endpoint, stats in self.endpoint_stats.items():
                report['endpoints'][endpoint] = {
                    **dict(stats),
                    'error_rate': (stats['error_count'] / max(stats['count'], 1)) * 100,
                    'requests_per_minute': stats['count'] / max(
                        (time.time() - (list(self.metrics[endpoint])[0]['timestamp'] if self.metrics[endpoint] else time.time())) / 60, 
                        1
                    ) if self.metrics[endpoint] else 0
                }
            
            # Find extremes
            if self.endpoint_stats:
                slowest = max(self.endpoint_stats.items(), key=lambda x: x[1]['avg_time'])
                fastest = min(self.endpoint_stats.items(), key=lambda x: x[1]['avg_time'])
                
                report['summary']['slowest_endpoint'] = {
                    'name': slowest[0], 
                    'avg_time_ms': slowest[1]['avg_time']
                }
                report['summary']['fastest_endpoint'] = {
                    'name': fastest[0], 
                    'avg_time_ms': fastest[1]['avg_time']
                }
            
            return report
    
    def clear_metrics(self):
        """Clear all collected metrics"""
        with self.lock:
            self.metrics.clear()
            self.slow_queries.clear()
            self.endpoint_stats.clear()
            self.system_metrics.clear()

def profile_endpoint(threshold_ms: int = 1000, include_memory: bool = True):
    """
    Decorator to profile endpoint performance
    
    Args:
        threshold_ms: Threshold for logging slow endpoints
        include_memory: Whether to track memory usage
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            memory_before = psutil.Process().memory_info().rss if include_memory else 0
            
            try:
                result = func(*args, **kwargs)
                status = 'success'
            except Exception as e:
                result = None
                status = 'error'
                raise
            finally:
                end_time = time.time()
                duration_ms = (end_time - start_time) * 1000
                
                memory_after = psutil.Process().memory_info().rss if include_memory else 0
                memory_delta_mb = (memory_after - memory_before) / (1024 * 1024) if include_memory else 0
                
                # Record metrics
                profiler.record_endpoint_metric(
                    endpoint=func.__name__,
                    duration_ms=duration_ms,
                    memory_delta_mb=memory_delta_mb,
                    status=status
                )
                
                # Log slow endpoints
                if duration_ms > threshold_ms:
                    logger.warning(
                        f"Slow endpoint: {func.__name__} took {duration_ms:.2f}ms "
                        f"(memory delta: {memory_delta_mb:.2f}MB)"
                    )
            
            return result
        
        return wrapper
    return decorator

# Global profiler instance
profiler = PerformanceProfiler()

# ================================
# utils/memory_manager.py
"""
Memory management and optimization utilities
"""
import gc
import psutil
import weakref
import threading
import time
import logging
from functools import wraps
from typing import Any, Callable, Dict, List, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

class MemoryManager:
    """
    Advanced memory management system
    """
    
    def __init__(self, max_memory_percent: float = 0.8, cleanup_interval: int = 300):
        self.max_memory_percent = max_memory_percent
        self.cleanup_interval = cleanup_interval
        self.tracked_objects = weakref.WeakSet()
        self.memory_alerts = []
        self.lock = threading.RLock()
        
        # Memory usage history
        self.memory_history = []
        self.max_history = 1000
        
        # Start background monitoring
        self._start_memory_monitor()
    
    def _start_memory_monitor(self):
        """Start background memory monitoring"""
        def monitor():
            while True:
                try:
                    memory_info = self.check_memory_usage()
                    
                    with self.lock:
                        self.memory_history.append({
                            'timestamp': time.time(),
                            **memory_info
                        })
                        
                        # Maintain history size
                        if len(self.memory_history) > self.max_history:
                            self.memory_history = self.memory_history[-self.max_history//2:]
                    
                    # Auto cleanup if memory is critical
                    if memory_info['is_critical']:
                        logger.warning("Critical memory usage detected, performing cleanup")
                        self.emergency_cleanup()
                    
                    time.sleep(30)  # Check every 30 seconds
                    
                except Exception as e:
                    logger.error(f"Memory monitoring error: {e}")
                    time.sleep(60)  # Wait longer on error
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
    
    def check_memory_usage(self) -> Dict[str, Any]:
        """Get current memory usage information"""
        try:
            # System memory
            system_memory = psutil.virtual_memory()
            
            # Process memory
            process = psutil.Process()
            process_memory = process.memory_info()
            
            # Calculate metrics
            is_critical = system_memory.percent > (self.max_memory_percent * 100)
            is_warning = system_memory.percent > (self.max_memory_percent * 0.8 * 100)
            
            return {
                'system_total_gb': round(system_memory.total / (1024**3), 2),
                'system_available_gb': round(system_memory.available / (1024**3), 2),
                'system_used_percent': round(system_memory.percent, 2),
                'process_rss_mb': round(process_memory.rss / (1024**2), 2),
                'process_vms_mb': round(process_memory.vms / (1024**2), 2),
                'is_critical': is_critical,
                'is_warning': is_warning,
                'gc_stats': {
                    'gen0': gc.get_count()[0],
                    'gen1': gc.get_count()[1],
                    'gen2': gc.get_count()[2]
                }
            }
            
        except Exception as e:
            logger.error(f"Error checking memory usage: {e}")
            return {
                'error': str(e),
                'is_critical': True,  # Assume critical if we can't check
                'is_warning': True
            }
    
    def track_object(self, obj: Any, description: str = None):
        """Track an object for memory management"""
        try:
            self.tracked_objects.add(obj)
            if description:
                # Store description in object if possible
                if hasattr(obj, '__dict__'):
                    obj._memory_description = description
        except Exception as e:
            logger.debug(f"Error tracking object: {e}")
    
    def emergency_cleanup(self):
        """Perform emergency memory cleanup"""
        logger.info("Starting emergency memory cleanup")
        
        try:
            # Force garbage collection
            collected = gc.collect()
            logger.info(f"Garbage collection freed {collected} objects")
            
            # Clear tracked objects
            self.cleanup_large_objects()
            
            # Clear caches if available
            if hasattr(cache_manager, 'memory_cache'):
                cache_manager.memory_cache.clear()
                logger.info("Cleared memory cache")
            
            # Final memory check
            memory_info = self.check_memory_usage()
            logger.info(f"Post-cleanup memory usage: {memory_info['system_used_percent']}%")
            
        except Exception as e:
            logger.error(f"Error during emergency cleanup: {e}")
    
    def cleanup_large_objects(self):
        """Clean up tracked large objects"""
        cleaned_count = 0
        
        try:
            # Get a list of tracked objects (weak references may have died)
            objects_to_clean = list(self.tracked_objects)
            
            for obj in objects_to_clean:
                try:
                    # Try to clean up the object
                    if hasattr(obj, 'close'):
                        obj.close()
                    elif hasattr(obj, 'clear'):
                        obj.clear()
                    elif hasattr(obj, '__del__'):
                        del obj
                    
                    cleaned_count += 1
                    
                except Exception as e:
                    logger.debug(f"Error cleaning object: {e}")
            
            # Force garbage collection
            gc.collect()
            
            logger.info(f"Cleaned up {cleaned_count} large objects")
            
        except Exception as e:
            logger.error(f"Error during large object cleanup: {e}")
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics"""
        try:
            current_memory = self.check_memory_usage()
            
            # Calculate trends from history
            recent_history = [
                m for m in self.memory_history 
                if time.time() - m['timestamp'] < 3600  # Last hour
            ]
            
            if len(recent_history) >= 2:
                trend = (recent_history[-1]['system_used_percent'] - 
                        recent_history[0]['system_used_percent'])
            else:
                trend = 0
            
            peak_usage = max(
                (m['system_used_percent'] for m in recent_history),
                default=current_memory.get('system_used_percent', 0)
            )
            
            return {
                'current': current_memory,
                'trend_percent_per_hour': round(trend, 2),
                'peak_usage_last_hour': round(peak_usage, 2),
                'tracked_objects_count': len(self.tracked_objects),
                'history_data_points': len(self.memory_history),
                'recommendations': self._generate_recommendations(current_memory, trend)
            }
            
        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return {'error': str(e)}
    
    def _generate_recommendations(self, current_memory: Dict, trend: float) -> List[str]:
        """Generate memory optimization recommendations"""
        recommendations = []
        
        try:
            if current_memory.get('is_critical', False):
                recommendations.append("CRITICAL: Immediate memory cleanup required")
                recommendations.append("Consider restarting the application")
            
            if current_memory.get('is_warning', False):
                recommendations.append("WARNING: High memory usage detected")
                recommendations.append("Enable aggressive caching cleanup")
            
            if trend > 5:  # Growing by more than 5% per hour
                recommendations.append("Memory usage is trending upward")
                recommendations.append("Check for memory leaks in recent code changes")
            
            if current_memory.get('process_rss_mb', 0) > 1000:  # > 1GB
                recommendations.append("Process memory usage is high")
                recommendations.append("Consider implementing data streaming")
            
            gc_stats = current_memory.get('gc_stats', {})
            if gc_stats.get('gen2', 0) > 100:
                recommendations.append("High generation 2 garbage collection count")
                recommendations.append("Consider manual garbage collection calls")
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            recommendations.append(f"Error analyzing memory: {e}")
        
        return recommendations

def memory_efficient_operation(func: Callable) -> Callable:
    """
    Decorator for memory-efficient operations
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Pre-operation memory check
        memory_status = memory_manager.check_memory_usage()
        
        if memory_status['is_critical']:
            # Try cleanup before proceeding
            gc.collect()
            
            # Recheck after cleanup
            memory_status = memory_manager.check_memory_usage()
            if memory_status['is_critical']:
                raise MemoryError(
                    f"Insufficient memory for operation. "
                    f"Current usage: {memory_status.get('system_used_percent', 'unknown')}%"
                )
        
        try:
            # Execute operation
            result = func(*args, **kwargs)
            
            # Track result if it's a large object
            if hasattr(result, '__sizeof__'):
                size_bytes = result.__sizeof__()
                if size_bytes > 1024 * 1024:  # > 1MB
                    memory_manager.track_object(result, f"Result from {func.__name__}")
            
            return result
            
        finally:
            # Post-operation cleanup
            if memory_status.get('is_warning', False):
                gc.collect()
    
    return wrapper

# Global memory manager instance
memory_manager = MemoryManager()

# ================================
# utils/error_handlers.py
"""
Standardized error handling system
"""
import logging
import traceback
from functools import wraps
from flask import request, jsonify
from typing import Callable, Dict, Any
from utils.response_utils import error_json, validation_error_json

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom validation error"""
    pass

class BusinessLogicError(Exception):
    """Custom business logic error"""
    pass

class StandardErrorHandler:
    """
    Centralized error handling with categorization and logging
    """
    
    def __init__(self):
        self.error_counts = {}
        self.error_history = []
    
    def handle_blueprint_error(self, blueprint_name: str):
        """Decorator for standardized blueprint error handling"""
        def decorator(f: Callable) -> Callable:
            @wraps(f)
            def wrapper(*args, **kwargs):
                try:
                    return f(*args, **kwargs)
                    
                except ValidationError as e:
                    error_msg = f"[{blueprint_name}] Validation error: {str(e)}"
                    logger.warning(error_msg)
                    self._record_error('validation', blueprint_name, str(e))
                    
                    if request.is_json:
                        return validation_error_json(str(e))
                    else:
                        from flask import flash, redirect, url_for
                        flash(str(e), 'warning')
                        return redirect(url_for('core.home'))
                
                except BusinessLogicError as e:
                    error_msg = f"[{blueprint_name}] Business logic error: {str(e)}"
                    logger.error(error_msg)
                    self._record_error('business_logic', blueprint_name, str(e))
                    
                    if request.is_json:
                        return error_json(str(e), status_code=400)
                    else:
                        from flask import flash, redirect, url_for
                        flash(str(e), 'danger')
                        return redirect(url_for('core.home'))
                
                except FileNotFoundError as e:
                    error_msg = f"[{blueprint_name}] File not found: {str(e)}"
                    logger.error(error_msg)
                    self._record_error('file_not_found', blueprint_name, str(e))
                    
                    if request.is_json:
                        return error_json("Required file not found", status_code=404)
                    else:
                        from flask import flash, redirect, url_for
                        flash("Required file not found", 'danger')
                        return redirect(url_for('core.home'))
                
                except MemoryError as e:
                    error_msg = f"[{blueprint_name}] Memory error: {str(e)}"
                    logger.critical(error_msg)
                    self._record_error('memory', blueprint_name, str(e))
                    
                    if request.is_json:
                        return error_json("Insufficient memory to complete operation", status_code=507)
                    else:
                        from flask import flash, redirect, url_for
                        flash("System temporarily overloaded. Please try again later.", 'danger')
                        return redirect(url_for('core.home'))
                
                except Exception as e:
                    error_msg = f"[{blueprint_name}] Unexpected error: {str(e)}"
                    logger.exception(error_msg)
                    self._record_error('unexpected', blueprint_name, str(e))
                    
                    if request.is_json:
                        return error_json("An unexpected error occurred", status_code=500)
                    else:
                        from flask import flash, redirect, url_for
                        flash("An unexpected error occurred", 'danger')
                        return redirect(url_for('core.home'))
            
            return wrapper
        return decorator
    
    def _record_error(self, error_type: str, blueprint: str, message: str):
        """Record error for analytics"""
        error_key = f"{error_type}:{blueprint}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        self.error_history.append({
            'type': error_type,
            'blueprint': blueprint,
            'message': message,
            'timestamp': time.time(),
            'traceback': traceback.format_exc()
        })
        
        # Keep only recent errors
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-500:]
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        return {
            'error_counts': dict(self.error_counts),
            'recent_errors': self.error_history[-10:],
            'total_errors': len(self.error_history),
            'most_common_errors': sorted(
                self.error_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }