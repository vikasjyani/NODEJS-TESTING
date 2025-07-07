# utils/memory_manager.py
"""
Advanced Memory Management System for KSEB Energy Futures Platform
Provides intelligent memory monitoring, cleanup, and optimization
"""
import gc
import psutil
import weakref
import threading
import time
import logging
import os
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import pickle
import json

logger = logging.getLogger(__name__)

@dataclass
class MemorySnapshot:
    """Memory usage snapshot"""
    timestamp: float
    rss_mb: float
    vms_mb: float
    percent: float
    available_mb: float
    swap_percent: float
    gc_stats: Dict[str, int]
    process_count: int

@dataclass
class ObjectTracker:
    """Track memory-intensive objects"""
    obj_id: str
    obj_type: str
    size_estimate_mb: float
    created_at: float
    last_accessed: float
    description: str = ""
    cleanup_method: Optional[str] = None

class MemoryManager:
    """
    Advanced memory management system with proactive monitoring and cleanup
    """
    
    def __init__(self, 
                 warning_threshold: float = 0.75,  # 75% of available memory
                 critical_threshold: float = 0.90,  # 90% of available memory
                 cleanup_interval: int = 300):      # 5 minutes
        
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.cleanup_interval = cleanup_interval
        
        # Memory tracking
        self.memory_history = deque(maxlen=2880)  # 48 hours at 1 sample/minute
        self.tracked_objects = {}  # obj_id -> ObjectTracker
        self.large_objects = weakref.WeakSet()
        
        # Alerts and thresholds
        self.memory_alerts = deque(maxlen=1000)
        self.alert_counts = defaultdict(int)
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Background monitoring
        self.monitoring_active = True
        self._start_memory_monitor()
        
        # Cleanup strategies
        self.cleanup_strategies = {
            'pandas_dataframes': self._cleanup_pandas_objects,
            'large_lists': self._cleanup_large_lists,
            'cache_objects': self._cleanup_cache_objects,
            'temporary_files': self._cleanup_temp_files
        }
        
        logger.info(f"MemoryManager initialized (warning: {warning_threshold*100}%, critical: {critical_threshold*100}%)")
    
    def _start_memory_monitor(self):
        """Start background memory monitoring thread"""
        def monitor_memory():
            while self.monitoring_active:
                try:
                    snapshot = self._capture_memory_snapshot()
                    
                    with self.lock:
                        self.memory_history.append(snapshot)
                        self._check_memory_thresholds(snapshot)
                        self._cleanup_old_tracking_data()
                    
                    # Automatic cleanup if memory is high
                    if snapshot.percent > self.critical_threshold * 100:
                        logger.warning(f"Critical memory usage: {snapshot.percent:.1f}%")
                        self._emergency_cleanup()
                    elif snapshot.percent > self.warning_threshold * 100:
                        logger.info(f"High memory usage: {snapshot.percent:.1f}%")
                        self._gentle_cleanup()
                    
                    time.sleep(60)  # Monitor every minute
                    
                except Exception as e:
                    logger.error(f"Memory monitoring error: {e}")
                    time.sleep(120)  # Wait longer on error
        
        monitor_thread = threading.Thread(target=monitor_memory, daemon=True)
        monitor_thread.start()
    
    def _capture_memory_snapshot(self) -> MemorySnapshot:
        """Capture current memory state"""
        try:
            # System memory
            system_memory = psutil.virtual_memory()
            swap_memory = psutil.swap_memory()
            
            # Process memory
            process = psutil.Process()
            process_memory = process.memory_info()
            
            # Garbage collection stats
            gc_stats = {
                f'gen{i}': count for i, count in enumerate(gc.get_count())
            }
            gc_stats['collections'] = sum(gc.get_stats()[i]['collections'] for i in range(3))
            
            return MemorySnapshot(
                timestamp=time.time(),
                rss_mb=round(process_memory.rss / (1024**2), 2),
                vms_mb=round(process_memory.vms / (1024**2), 2),
                percent=round(system_memory.percent, 2),
                available_mb=round(system_memory.available / (1024**2), 2),
                swap_percent=round(swap_memory.percent, 2),
                gc_stats=gc_stats,
                process_count=len(psutil.pids())
            )
            
        except Exception as e:
            logger.error(f"Error capturing memory snapshot: {e}")
            return MemorySnapshot(
                timestamp=time.time(),
                rss_mb=0, vms_mb=0, percent=0, available_mb=0,
                swap_percent=0, gc_stats={}, process_count=0
            )
    
    def _check_memory_thresholds(self, snapshot: MemorySnapshot):
        """Check if memory thresholds are exceeded and generate alerts"""
        current_time = time.time()
        
        # Check for critical memory usage
        if snapshot.percent > self.critical_threshold * 100:
            alert = {
                'level': 'CRITICAL',
                'message': f'Critical memory usage: {snapshot.percent:.1f}%',
                'timestamp': current_time,
                'memory_percent': snapshot.percent,
                'available_mb': snapshot.available_mb,
                'rss_mb': snapshot.rss_mb
            }
            self.memory_alerts.append(alert)
            self.alert_counts['critical'] += 1
            
        elif snapshot.percent > self.warning_threshold * 100:
            alert = {
                'level': 'WARNING',
                'message': f'High memory usage: {snapshot.percent:.1f}%',
                'timestamp': current_time,
                'memory_percent': snapshot.percent,
                'available_mb': snapshot.available_mb,
                'rss_mb': snapshot.rss_mb
            }
            self.memory_alerts.append(alert)
            self.alert_counts['warning'] += 1
        
        # Check for rapid memory growth
        if len(self.memory_history) >= 5:
            recent_snapshots = list(self.memory_history)[-5:]
            growth_rate = (recent_snapshots[-1].rss_mb - recent_snapshots[0].rss_mb) / 5  # MB per minute
            
            if growth_rate > 50:  # Growing by more than 50MB per minute
                alert = {
                    'level': 'WARNING',
                    'message': f'Rapid memory growth detected: {growth_rate:.1f}MB/min',
                    'timestamp': current_time,
                    'growth_rate_mb_per_min': growth_rate
                }
                self.memory_alerts.append(alert)
                self.alert_counts['growth'] += 1
    
    def _cleanup_old_tracking_data(self):
        """Clean up old tracking data to prevent memory leaks"""
        current_time = time.time()
        cutoff_time = current_time - (24 * 3600)  # 24 hours ago
        
        # Clean up old object tracking
        expired_objects = [
            obj_id for obj_id, tracker in self.tracked_objects.items()
            if tracker.last_accessed < cutoff_time
        ]
        
        for obj_id in expired_objects:
            del self.tracked_objects[obj_id]
        
        if expired_objects:
            logger.debug(f"Cleaned up {len(expired_objects)} expired object trackers")
    
    def check_memory_usage(self) -> Dict[str, Any]:
        """
        Get current memory usage information with recommendations
        """
        try:
            snapshot = self._capture_memory_snapshot()
            
            # Calculate memory pressure level
            if snapshot.percent > self.critical_threshold * 100:
                pressure = 'critical'
            elif snapshot.percent > self.warning_threshold * 100:
                pressure = 'high'
            elif snapshot.percent > 50:
                pressure = 'moderate'
            else:
                pressure = 'low'
            
            # Memory trends
            trend = self._calculate_memory_trend()
            
            # Top memory consumers
            top_objects = self._get_top_memory_objects()
            
            return {
                'timestamp': snapshot.timestamp,
                'system_total_gb': round(psutil.virtual_memory().total / (1024**3), 2),
                'system_available_gb': round(snapshot.available_mb / 1024, 2),
                'system_used_percent': snapshot.percent,
                'process_rss_mb': snapshot.rss_mb,
                'process_vms_mb': snapshot.vms_mb,
                'swap_percent': snapshot.swap_percent,
                'pressure': pressure,
                'is_warning': snapshot.percent > self.warning_threshold * 100,
                'is_critical': snapshot.percent > self.critical_threshold * 100,
                'trend': trend,
                'gc_stats': snapshot.gc_stats,
                'tracked_objects_count': len(self.tracked_objects),
                'large_objects_count': len(self.large_objects),
                'top_objects': top_objects,
                'recommendations': self._generate_memory_recommendations(snapshot, pressure)
            }
            
        except Exception as e:
            logger.error(f"Error checking memory usage: {e}")
            return {
                'error': str(e),
                'is_critical': True,  # Assume critical if we can't check
                'is_warning': True
            }
    
    def _calculate_memory_trend(self) -> Dict[str, Any]:
        """Calculate memory usage trend over time"""
        if len(self.memory_history) < 10:
            return {'trend': 'insufficient_data', 'samples': len(self.memory_history)}
        
        try:
            recent_snapshots = list(self.memory_history)[-10:]  # Last 10 minutes
            
            # Calculate linear trend
            times = [(s.timestamp - recent_snapshots[0].timestamp) / 60 for s in recent_snapshots]  # Minutes
            memory_values = [s.rss_mb for s in recent_snapshots]
            
            # Simple linear regression
            n = len(times)
            sum_x = sum(times)
            sum_y = sum(memory_values)
            sum_xy = sum(t * m for t, m in zip(times, memory_values))
            sum_x2 = sum(t * t for t in times)
            
            if sum_x2 * n - sum_x * sum_x != 0:
                slope = (sum_xy * n - sum_x * sum_y) / (sum_x2 * n - sum_x * sum_x)
                
                # Classify trend
                if abs(slope) < 1:  # Less than 1MB/min change
                    trend = 'stable'
                elif slope > 5:  # Growing by more than 5MB/min
                    trend = 'rapidly_increasing'
                elif slope > 1:
                    trend = 'increasing'
                elif slope < -5:
                    trend = 'rapidly_decreasing'
                else:
                    trend = 'decreasing'
                
                return {
                    'trend': trend,
                    'slope_mb_per_min': round(slope, 2),
                    'samples': len(recent_snapshots),
                    'timeframe_minutes': round(times[-1], 1)
                }
            else:
                return {'trend': 'stable', 'samples': len(recent_snapshots)}
                
        except Exception as e:
            logger.debug(f"Error calculating memory trend: {e}")
            return {'trend': 'calculation_error', 'error': str(e)}
    
    def _get_top_memory_objects(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top memory-consuming tracked objects"""
        try:
            with self.lock:
                # Sort tracked objects by estimated size
                sorted_objects = sorted(
                    self.tracked_objects.values(),
                    key=lambda x: x.size_estimate_mb,
                    reverse=True
                )
                
                return [
                    {
                        'id': obj.obj_id,
                        'type': obj.obj_type,
                        'size_mb': obj.size_estimate_mb,
                        'age_minutes': round((time.time() - obj.created_at) / 60, 1),
                        'description': obj.description
                    }
                    for obj in sorted_objects[:limit]
                ]
                
        except Exception as e:
            logger.debug(f"Error getting top memory objects: {e}")
            return []
    
    def _generate_memory_recommendations(self, snapshot: MemorySnapshot, 
                                       pressure: str) -> List[str]:
        """Generate memory optimization recommendations"""
        recommendations = []
        
        try:
            if pressure == 'critical':
                recommendations.extend([
                    "URGENT: Memory usage is critical - immediate action required",
                    "Consider restarting the application to free memory",
                    "Review and terminate any non-essential processes"
                ])
            
            if pressure in ['critical', 'high']:
                recommendations.extend([
                    "Enable aggressive garbage collection",
                    "Clear application caches and temporary data",
                    "Review large objects and data structures"
                ])
            
            # Specific recommendations based on GC stats
            gc_gen2 = snapshot.gc_stats.get('gen2', 0)
            if gc_gen2 > 100:
                recommendations.append(
                    f"High generation 2 GC objects ({gc_gen2}) - consider manual gc.collect()"
                )
            
            # Process memory recommendations
            if snapshot.rss_mb > 2000:  # More than 2GB
                recommendations.append(
                    "Process memory usage is very high - consider data streaming approaches"
                )
            
            # Swap usage recommendations
            if snapshot.swap_percent > 10:
                recommendations.append(
                    f"High swap usage ({snapshot.swap_percent:.1f}%) - add more RAM or optimize memory usage"
                )
            
            # Object tracking recommendations
            if len(self.tracked_objects) > 1000:
                recommendations.append(
                    "Large number of tracked objects - review object lifecycle management"
                )
            
            # Trend-based recommendations
            trend_info = self._calculate_memory_trend()
            if trend_info.get('trend') == 'rapidly_increasing':
                recommendations.append(
                    f"Memory rapidly increasing ({trend_info.get('slope_mb_per_min', 0):.1f}MB/min) - check for memory leaks"
                )
            
        except Exception as e:
            logger.debug(f"Error generating recommendations: {e}")
            recommendations.append(f"Error analyzing memory: {e}")
        
        return recommendations
    
    def track_object(self, obj: Any, description: str = "", 
                    cleanup_method: Optional[str] = None) -> str:
        """
        Track a memory-intensive object
        
        Args:
            obj: Object to track
            description: Human-readable description
            cleanup_method: Method to call for cleanup
            
        Returns:
            Object tracking ID
        """
        try:
            obj_id = f"obj_{id(obj)}_{int(time.time() * 1000)}"
            
            # Estimate object size
            size_estimate = self._estimate_object_size(obj)
            
            tracker = ObjectTracker(
                obj_id=obj_id,
                obj_type=type(obj).__name__,
                size_estimate_mb=size_estimate,
                created_at=time.time(),
                last_accessed=time.time(),
                description=description,
                cleanup_method=cleanup_method
            )
            
            with self.lock:
                self.tracked_objects[obj_id] = tracker
                
                # Add to large objects set if significant
                if size_estimate > 10:  # Objects larger than 10MB
                    self.large_objects.add(obj)
            
            logger.debug(f"Tracking object {obj_id}: {description} ({size_estimate:.1f}MB)")
            return obj_id
            
        except Exception as e:
            logger.error(f"Error tracking object: {e}")
            return ""
    
    def _estimate_object_size(self, obj: Any) -> float:
        """Estimate object size in MB"""
        try:
            # Try different methods to estimate size
            if hasattr(obj, 'memory_usage'):
                # Pandas objects
                if hasattr(obj.memory_usage, '__call__'):
                    return obj.memory_usage(deep=True).sum() / (1024**2)
                else:
                    return obj.memory_usage / (1024**2)
            
            elif hasattr(obj, '__sizeof__'):
                # Use __sizeof__ method
                size_bytes = obj.__sizeof__()
                
                # For containers, try to get a better estimate
                if hasattr(obj, '__len__'):
                    try:
                        # Sample a few items to estimate
                        if len(obj) > 0:
                            if isinstance(obj, (list, tuple)):
                                sample_size = min(10, len(obj))
                                sample_avg = sum(getattr(item, '__sizeof__', lambda: 100)() 
                                               for item in obj[:sample_size]) / sample_size
                                size_bytes = sample_avg * len(obj)
                            elif isinstance(obj, dict):
                                sample_items = list(obj.items())[:10]
                                if sample_items:
                                    avg_item_size = sum(
                                        getattr(k, '__sizeof__', lambda: 50)() + 
                                        getattr(v, '__sizeof__', lambda: 50)()
                                        for k, v in sample_items
                                    ) / len(sample_items)
                                    size_bytes = avg_item_size * len(obj)
                    except:
                        pass
                
                return size_bytes / (1024**2)
            
            else:
                # Fallback: try pickle size
                try:
                    pickled = pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)
                    return len(pickled) / (1024**2)
                except:
                    # Last resort: rough estimate based on type
                    if isinstance(obj, str):
                        return len(obj.encode('utf-8')) / (1024**2)
                    elif isinstance(obj, (list, tuple)):
                        return len(obj) * 0.1  # Rough estimate: 100 bytes per item
                    elif isinstance(obj, dict):
                        return len(obj) * 0.2  # Rough estimate: 200 bytes per item
                    else:
                        return 0.1  # 100KB default estimate
                        
        except Exception as e:
            logger.debug(f"Error estimating object size: {e}")
            return 0.1  # Default to 100KB
    
    def untrack_object(self, obj_id: str):
        """Stop tracking an object"""
        with self.lock:
            if obj_id in self.tracked_objects:
                del self.tracked_objects[obj_id]
                logger.debug(f"Stopped tracking object {obj_id}")
    
    def update_object_access(self, obj_id: str):
        """Update last access time for tracked object"""
        with self.lock:
            if obj_id in self.tracked_objects:
                self.tracked_objects[obj_id].last_accessed = time.time()
    
    def _gentle_cleanup(self):
        """Perform gentle memory cleanup"""
        logger.info("Performing gentle memory cleanup")
        
        try:
            # Run garbage collection
            collected = gc.collect()
            logger.debug(f"Garbage collection freed {collected} objects")
            
            # Clean up old tracked objects
            self._cleanup_old_objects(age_threshold_minutes=30)
            
            # Try cache cleanup strategies
            for strategy_name, strategy_func in self.cleanup_strategies.items():
                try:
                    cleaned = strategy_func(aggressive=False)
                    if cleaned:
                        logger.debug(f"Cleanup strategy '{strategy_name}' freed {cleaned} items")
                except Exception as e:
                    logger.debug(f"Cleanup strategy '{strategy_name}' failed: {e}")
            
        except Exception as e:
            logger.error(f"Error during gentle cleanup: {e}")
    
    def _emergency_cleanup(self):
        """Perform aggressive memory cleanup"""
        logger.warning("Performing emergency memory cleanup")
        
        try:
            # Force aggressive garbage collection
            for _ in range(3):
                collected = gc.collect()
                logger.debug(f"Aggressive GC round freed {collected} objects")
            
            # Clean up all old tracked objects
            self._cleanup_old_objects(age_threshold_minutes=5)
            
            # Run all cleanup strategies aggressively
            total_cleaned = 0
            for strategy_name, strategy_func in self.cleanup_strategies.items():
                try:
                    cleaned = strategy_func(aggressive=True)
                    total_cleaned += cleaned or 0
                    logger.debug(f"Aggressive cleanup '{strategy_name}' freed {cleaned} items")
                except Exception as e:
                    logger.error(f"Aggressive cleanup '{strategy_name}' failed: {e}")
            
            # Clear large objects set
            self.large_objects.clear()
            
            logger.info(f"Emergency cleanup completed. Total items cleaned: {total_cleaned}")
            
        except Exception as e:
            logger.error(f"Error during emergency cleanup: {e}")
    
    def _cleanup_old_objects(self, age_threshold_minutes: int = 30):
        """Clean up tracked objects older than threshold"""
        current_time = time.time()
        cutoff_time = current_time - (age_threshold_minutes * 60)
        
        with self.lock:
            old_objects = [
                obj_id for obj_id, tracker in self.tracked_objects.items()
                if tracker.last_accessed < cutoff_time
            ]
            
            for obj_id in old_objects:
                tracker = self.tracked_objects[obj_id]
                
                # Try to call cleanup method if specified
                if tracker.cleanup_method:
                    try:
                        # This is a simplified approach - in practice, you'd need
                        # to maintain references to objects for cleanup
                        logger.debug(f"Would call cleanup method {tracker.cleanup_method} for {obj_id}")
                    except Exception as e:
                        logger.debug(f"Cleanup method failed for {obj_id}: {e}")
                
                del self.tracked_objects[obj_id]
            
            if old_objects:
                logger.debug(f"Cleaned up {len(old_objects)} old tracked objects")
    
    def _cleanup_pandas_objects(self, aggressive: bool = False) -> int:
        """Cleanup pandas DataFrames and Series"""
        # This would need to be implemented with actual object references
        # For now, just return 0
        return 0
    
    def _cleanup_large_lists(self, aggressive: bool = False) -> int:
        """Cleanup large list objects"""
        # This would need to be implemented with actual object references
        return 0
    
    def _cleanup_cache_objects(self, aggressive: bool = False) -> int:
        """Cleanup cache objects"""
        # This would interface with the cache manager
        try:
            from utils.cache_manager import cache_manager
            if hasattr(cache_manager, 'memory_cache'):
                initial_size = len(cache_manager.memory_cache.cache)
                if aggressive:
                    cache_manager.memory_cache.clear()
                    return initial_size
                else:
                    # Clear half the cache (LRU)
                    items_to_remove = initial_size // 2
                    cache_items = list(cache_manager.memory_cache.cache.items())
                    for key, _ in cache_items[:items_to_remove]:
                        del cache_manager.memory_cache.cache[key]
                        if key in cache_manager.memory_cache.timestamps:
                            del cache_manager.memory_cache.timestamps[key]
                    return items_to_remove
        except Exception as e:
            logger.debug(f"Error cleaning cache objects: {e}")
        return 0
    
    def _cleanup_temp_files(self, aggressive: bool = False) -> int:
        """Cleanup temporary files"""
        cleaned = 0
        try:
            import tempfile
            temp_dir = tempfile.gettempdir()
            
            # Clean files older than threshold
            age_hours = 1 if aggressive else 6
            cutoff_time = time.time() - (age_hours * 3600)
            
            for filename in os.listdir(temp_dir):
                if filename.startswith(('kseb_', 'pypsa_', 'demand_')):
                    file_path = os.path.join(temp_dir, filename)
                    try:
                        if os.path.getmtime(file_path) < cutoff_time:
                            os.remove(file_path)
                            cleaned += 1
                    except (OSError, IOError):
                        pass
        except Exception as e:
            logger.debug(f"Error cleaning temp files: {e}")
        
        return cleaned
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics"""
        try:
            current_status = self.check_memory_usage()
            
            # Historical analysis
            if len(self.memory_history) >= 2:
                history_snapshots = list(self.memory_history)
                
                # Calculate peak usage in last 24 hours
                peak_rss = max(s.rss_mb for s in history_snapshots)
                peak_percent = max(s.percent for s in history_snapshots)
                
                # Memory efficiency (how much memory freed by GC)
                gc_collections = [s.gc_stats.get('collections', 0) for s in history_snapshots]
                if len(gc_collections) >= 2:
                    gc_efficiency = gc_collections[-1] - gc_collections[0]
                else:
                    gc_efficiency = 0
            else:
                peak_rss = current_status.get('process_rss_mb', 0)
                peak_percent = current_status.get('system_used_percent', 0)
                gc_efficiency = 0
            
            # Alert summary
            with self.lock:
                recent_alerts = [
                    alert for alert in self.memory_alerts
                    if time.time() - alert['timestamp'] < 3600  # Last hour
                ]
            
            return {
                'current': current_status,
                'peak_usage_24h': {
                    'rss_mb': peak_rss,
                    'system_percent': peak_percent
                },
                'tracking': {
                    'tracked_objects': len(self.tracked_objects),
                    'large_objects': len(self.large_objects),
                    'total_estimated_mb': sum(
                        tracker.size_estimate_mb 
                        for tracker in self.tracked_objects.values()
                    )
                },
                'alerts': {
                    'recent_count': len(recent_alerts),
                    'total_counts': dict(self.alert_counts),
                    'recent_alerts': recent_alerts[-5:]  # Last 5 alerts
                },
                'gc_efficiency': gc_efficiency,
                'history_points': len(self.memory_history),
                'recommendations': current_status.get('recommendations', [])
            }
            
        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return {'error': str(e)}
    
    def force_cleanup(self, strategy: Optional[str] = None):
        """Force memory cleanup with optional strategy"""
        if strategy and strategy in self.cleanup_strategies:
            logger.info(f"Forcing cleanup with strategy: {strategy}")
            try:
                cleaned = self.cleanup_strategies[strategy](aggressive=True)
                logger.info(f"Strategy '{strategy}' cleaned {cleaned} items")
            except Exception as e:
                logger.error(f"Forced cleanup strategy '{strategy}' failed: {e}")
        else:
            logger.info("Forcing emergency cleanup")
            self._emergency_cleanup()
    
    def clear_tracking(self):
        """Clear all object tracking data"""
        with self.lock:
            self.tracked_objects.clear()
            self.large_objects.clear()
            logger.info("Cleared all memory tracking data")
    
    def get_recommendations(self) -> List[str]:
        """Get current memory optimization recommendations"""
        current_status = self.check_memory_usage()
        return current_status.get('recommendations', [])
    
    def shutdown(self):
        """Graceful shutdown of memory manager"""
        self.monitoring_active = False
        self.clear_tracking()
        logger.info("MemoryManager shutdown completed")

def memory_efficient_operation(func: Callable) -> Callable:
    """
    Decorator for memory-efficient operations with automatic cleanup
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Pre-operation memory check
        memory_status = memory_manager.check_memory_usage()
        
        if memory_status['is_critical']:
            # Try cleanup before proceeding
            memory_manager._gentle_cleanup()
            
            # Recheck after cleanup
            memory_status = memory_manager.check_memory_usage()
            if memory_status['is_critical']:
                raise MemoryError(
                    f"Insufficient memory for operation. "
                    f"Current usage: {memory_status.get('system_used_percent', 'unknown')}%"
                )
        
        # Track function execution
        start_time = time.time()
        initial_memory = psutil.Process().memory_info().rss
        
        try:
            # Execute operation
            result = func(*args, **kwargs)
            
            # Track result if it's a large object
            if hasattr(result, '__sizeof__'):
                size_bytes = result.__sizeof__()
                if size_bytes > 10 * 1024 * 1024:  # > 10MB
                    memory_manager.track_object(
                        result, 
                        f"Result from {func.__name__}",
                        cleanup_method="del"
                    )
            
            return result
            
        finally:
            # Post-operation analysis
            final_memory = psutil.Process().memory_info().rss
            duration = time.time() - start_time
            memory_delta_mb = (final_memory - initial_memory) / (1024 * 1024)
            
            # Log if operation used significant memory
            if memory_delta_mb > 100:  # More than 100MB
                logger.info(
                    f"Memory-intensive operation: {func.__name__} used "
                    f"{memory_delta_mb:.1f}MB in {duration:.2f}s"
                )
            
            # Post-operation cleanup if memory is high
            post_status = memory_manager.check_memory_usage()
            if post_status.get('is_warning', False):
                memory_manager._gentle_cleanup()
    
    return wrapper

# Global memory manager instance
memory_manager = MemoryManager()

# Convenience functions
def check_memory_usage() -> Dict[str, Any]:
    """Check current memory usage"""
    return memory_manager.check_memory_usage()

def track_large_object(obj: Any, description: str = "") -> str:
    """Track a large object for memory management"""
    return memory_manager.track_object(obj, description)

def force_memory_cleanup(strategy: Optional[str] = None):
    """Force memory cleanup"""
    memory_manager.force_cleanup(strategy)

def get_memory_recommendations() -> List[str]:
    """Get memory optimization recommendations"""
    return memory_manager.get_recommendations()