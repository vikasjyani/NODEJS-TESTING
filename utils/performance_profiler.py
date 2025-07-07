# utils/performance_profiler.py
"""
Performance profiling and monitoring utilities for KSEB Energy Platform
"""
import time
import cProfile
import pstats
import io
import psutil
import threading
import logging
from functools import wraps
from collections import defaultdict, deque
from typing import Dict, List, Any, Optional, Callable, Tuple
from datetime import datetime, timedelta
import json
import weakref

logger = logging.getLogger(__name__)

class PerformanceProfiler:
    """
    Advanced performance profiler with real-time monitoring and analytics
    """
    
    def __init__(self, max_records: int = 1000):
        self.max_records = max_records
        self.metrics = defaultdict(deque)
        self.slow_queries = deque(maxlen=100)
        self.endpoint_stats = defaultdict(lambda: {
            'count': 0, 'total_time': 0, 'min_time': float('inf'),
            'max_time': 0, 'avg_time': 0, 'error_count': 0,
            'memory_usage': [], 'cpu_usage': []
        })
        self.lock = threading.RLock()
        self.profiling_enabled = True
        
        # System monitoring
        self.system_metrics = deque(maxlen=300)  # 5 minutes at 1 sample/second
        self.resource_alerts = []
        
        # Background monitoring
        self._start_system_monitoring()
        
        logger.info("PerformanceProfiler initialized")
    
    def _start_system_monitoring(self):
        """Start background system monitoring"""
        def monitor():
            while self.profiling_enabled:
                try:
                    # Collect system metrics
                    cpu_percent = psutil.cpu_percent(interval=1)
                    memory = psutil.virtual_memory()
                    disk = psutil.disk_usage('/')
                    
                    metric_data = {
                        'timestamp': time.time(),
                        'datetime': datetime.now().isoformat(),
                        'cpu_percent': cpu_percent,
                        'memory_percent': memory.percent,
                        'memory_available_gb': memory.available / (1024**3),
                        'memory_used_gb': memory.used / (1024**3),
                        'disk_percent': disk.percent,
                        'disk_free_gb': disk.free / (1024**3)
                    }
                    
                    self.system_metrics.append(metric_data)
                    
                    # Check for resource alerts
                    self._check_resource_alerts(metric_data)
                    
                except Exception as e:
                    logger.debug(f"System monitoring error: {e}")
                    time.sleep(1)
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        logger.debug("System monitoring thread started")
    
    def _check_resource_alerts(self, metrics: Dict[str, Any]):
        """Check for resource usage alerts"""
        current_time = time.time()
        
        # CPU usage alert
        if metrics['cpu_percent'] > 90:
            self.resource_alerts.append({
                'type': 'high_cpu',
                'timestamp': current_time,
                'value': metrics['cpu_percent'],
                'message': f"High CPU usage: {metrics['cpu_percent']:.1f}%"
            })
        
        # Memory usage alert
        if metrics['memory_percent'] > 85:
            self.resource_alerts.append({
                'type': 'high_memory',
                'timestamp': current_time,
                'value': metrics['memory_percent'],
                'message': f"High memory usage: {metrics['memory_percent']:.1f}%"
            })
        
        # Disk usage alert
        if metrics['disk_percent'] > 90:
            self.resource_alerts.append({
                'type': 'high_disk',
                'timestamp': current_time,
                'value': metrics['disk_percent'],
                'message': f"High disk usage: {metrics['disk_percent']:.1f}%"
            })
        
        # Clean old alerts (keep last hour)
        cutoff_time = current_time - 3600
        self.resource_alerts = [
            alert for alert in self.resource_alerts 
            if alert['timestamp'] > cutoff_time
        ]
    
    def profile_function(self, func: Callable, *args, **kwargs) -> Tuple[Any, Dict[str, Any]]:
        """Profile a function call and return (result, profile_stats)"""
        profiler = cProfile.Profile()
        
        try:
            profiler.enable()
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            profiler.disable()
            
            # Get profile statistics
            stats_stream = io.StringIO()
            stats = pstats.Stats(profiler, stream=stats_stream)
            stats.sort_stats('cumulative')
            stats.print_stats(20)  # Top 20 functions
            
            profile_data = {
                'function_name': func.__name__,
                'execution_time_ms': (end_time - start_time) * 1000,
                'stats_text': stats_stream.getvalue(),
                'timestamp': datetime.now().isoformat(),
                'call_count': stats.total_calls,
                'primitive_calls': stats.prim_calls
            }
            
            return result, profile_data
            
        except Exception as e:
            profiler.disable()
            logger.error(f"Profiling error: {e}")
            return None, {'error': str(e)}
    
    def record_endpoint_metric(self, endpoint: str, duration_ms: float, 
                             memory_delta_mb: float = 0, cpu_percent: float = 0,
                             status: str = 'success', request_size_kb: float = 0,
                             response_size_kb: float = 0):
        """Record comprehensive endpoint performance metric"""
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
            
            # Track memory and CPU usage
            if memory_delta_mb > 0:
                stats['memory_usage'].append(memory_delta_mb)
                # Keep only last 100 measurements
                if len(stats['memory_usage']) > 100:
                    stats['memory_usage'] = stats['memory_usage'][-100:]
            
            if cpu_percent > 0:
                stats['cpu_usage'].append(cpu_percent)
                if len(stats['cpu_usage']) > 100:
                    stats['cpu_usage'] = stats['cpu_usage'][-100:]
            
            # Record individual metric
            metric_data = {
                'endpoint': endpoint,
                'duration_ms': duration_ms,
                'memory_delta_mb': memory_delta_mb,
                'cpu_percent': cpu_percent,
                'request_size_kb': request_size_kb,
                'response_size_kb': response_size_kb,
                'status': status,
                'timestamp': time.time(),
                'datetime': datetime.now().isoformat()
            }
            
            self.metrics[endpoint].append(metric_data)
            
            # Maintain max records per endpoint
            while len(self.metrics[endpoint]) > self.max_records:
                self.metrics[endpoint].popleft()
            
            # Track slow queries
            if duration_ms > 1000:  # > 1 second
                self.slow_queries.append(metric_data)
                logger.warning(f"Slow endpoint: {endpoint} took {duration_ms:.2f}ms")
    
    def get_endpoint_summary(self, endpoint: Optional[str] = None) -> Dict[str, Any]:
        """Get performance summary for endpoint(s)"""
        with self.lock:
            if endpoint:
                if endpoint in self.endpoint_stats:
                    stats = dict(self.endpoint_stats[endpoint])
                    
                    # Add calculated metrics
                    if stats['memory_usage']:
                        stats['avg_memory_mb'] = sum(stats['memory_usage']) / len(stats['memory_usage'])
                        stats['max_memory_mb'] = max(stats['memory_usage'])
                    
                    if stats['cpu_usage']:
                        stats['avg_cpu_percent'] = sum(stats['cpu_usage']) / len(stats['cpu_usage'])
                        stats['max_cpu_percent'] = max(stats['cpu_usage'])
                    
                    # Error rate
                    stats['error_rate'] = (stats['error_count'] / max(stats['count'], 1)) * 100
                    
                    return stats
                return {}
            
            # Return summary for all endpoints
            summary = {}
            for ep, stats in self.endpoint_stats.items():
                endpoint_summary = dict(stats)
                
                # Add calculated metrics
                if stats['memory_usage']:
                    endpoint_summary['avg_memory_mb'] = sum(stats['memory_usage']) / len(stats['memory_usage'])
                
                if stats['cpu_usage']:
                    endpoint_summary['avg_cpu_percent'] = sum(stats['cpu_usage']) / len(stats['cpu_usage'])
                
                endpoint_summary['error_rate'] = (stats['error_count'] / max(stats['count'], 1)) * 100
                
                summary[ep] = endpoint_summary
            
            return summary
    
    def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get slowest queries withdetails"""
        with self.lock:
            sorted_queries = sorted(
                list(self.slow_queries),
                key=lambda x: x['duration_ms'],
                reverse=True
            )
            return sorted_queries[:limit]
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get current system health metrics with trend analysis"""
        try:
            current_metrics = list(self.system_metrics)[-1] if self.system_metrics else {}
            
            # Calculate averages over different time periods
            recent_metrics_5min = [
                m for m in self.system_metrics 
                if time.time() - m['timestamp'] < 300
            ]
            
            recent_metrics_1min = [
                m for m in self.system_metrics 
                if time.time() - m['timestamp'] < 60
            ]
            
            def calculate_averages(metrics_list):
                if not metrics_list:
                    return {}
                
                return {
                    'cpu_percent': sum(m['cpu_percent'] for m in metrics_list) / len(metrics_list),
                    'memory_percent': sum(m['memory_percent'] for m in metrics_list) / len(metrics_list),
                    'disk_percent': sum(m['disk_percent'] for m in metrics_list) / len(metrics_list)
                }
            
            averages_5min = calculate_averages(recent_metrics_5min)
            averages_1min = calculate_averages(recent_metrics_1min)
            
            # Health status determination
            health_status = self._determine_health_status(averages_1min)
            
            # Resource trends
            trends = self._calculate_resource_trends()
            
            return {
                'current': current_metrics,
                'averages_1min': {k: round(v, 2) for k, v in averages_1min.items()},
                'averages_5min': {k: round(v, 2) for k, v in averages_5min.items()},
                'health_status': health_status,
                'healthy': health_status == 'healthy',
                'trends': trends,
                'recent_alerts': self.resource_alerts[-10:],
                'data_points': len(recent_metrics_5min)
            }
            
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {'error': str(e), 'healthy': False}
    
    def _determine_health_status(self, metrics: Dict[str, float]) -> str:
        """Determine health status based on current metrics"""
        if not metrics:
            return 'unknown'
        
        cpu = metrics.get('cpu_percent', 0)
        memory = metrics.get('memory_percent', 0)
        disk = metrics.get('disk_percent', 0)
        
        # Critical thresholds
        if cpu > 95 or memory > 95 or disk > 95:
            return 'critical'
        
        # Warning thresholds
        if cpu > 80 or memory > 85 or disk > 90:
            return 'warning'
        
        # Degraded thresholds
        if cpu > 60 or memory > 70 or disk > 80:
            return 'degraded'
        
        return 'healthy'
    
    def _calculate_resource_trends(self) -> Dict[str, Any]:
        """Calculate resource usage trends"""
        try:
            if len(self.system_metrics) < 2:
                return {'insufficient_data': True}
            
            # Get metrics for trend calculation
            recent_count = min(60, len(self.system_metrics))  # Last 60 data points
            recent_metrics = list(self.system_metrics)[-recent_count:]
            
            # Calculate trends for each metric
            def calculate_trend(values: List[float]) -> Dict[str, Any]:
                if len(values) < 2:
                    return {'trend': 'stable', 'change': 0}
                
                # Simple linear trend
                first_half_avg = sum(values[:len(values)//2]) / (len(values)//2)
                second_half_avg = sum(values[len(values)//2:]) / (len(values) - len(values)//2)
                
                change = second_half_avg - first_half_avg
                
                if abs(change) < 1:  # Less than 1% change
                    trend = 'stable'
                elif change > 0:
                    trend = 'increasing'
                else:
                    trend = 'decreasing'
                
                return {
                    'trend': trend,
                    'change': round(change, 2),
                    'first_half_avg': round(first_half_avg, 2),
                    'second_half_avg': round(second_half_avg, 2)
                }
            
            cpu_values = [m['cpu_percent'] for m in recent_metrics]
            memory_values = [m['memory_percent'] for m in recent_metrics]
            disk_values = [m['disk_percent'] for m in recent_metrics]
            
            return {
                'cpu': calculate_trend(cpu_values),
                'memory': calculate_trend(memory_values),
                'disk': calculate_trend(disk_values),
                'data_points': len(recent_metrics)
            }
            
        except Exception as e:
            logger.error(f"Error calculating trends: {e}")
            return {'error': str(e)}
    
    def generate_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        with self.lock:
            cutoff_time = time.time() - (hours * 3600)
            
            # Filter metrics by time period
            period_metrics = {}
            for endpoint, metrics in self.metrics.items():
                period_metrics[endpoint] = [
                    m for m in metrics if m['timestamp'] > cutoff_time
                ]
            
            # Calculate report statistics
            total_requests = sum(len(metrics) for metrics in period_metrics.values())
            
            # Performance summary
            performance_summary = {
                'time_period_hours': hours,
                'total_requests': total_requests,
                'unique_endpoints': len(period_metrics),
                'requests_per_hour': total_requests / max(hours, 1)
            }
            
            # Endpoint performance
            endpoint_performance = {}
            for endpoint, metrics in period_metrics.items():
                if not metrics:
                    continue
                
                durations = [m['duration_ms'] for m in metrics]
                memory_usage = [m['memory_delta_mb'] for m in metrics if m['memory_delta_mb'] > 0]
                errors = [m for m in metrics if m['status'] == 'error']
                
                endpoint_performance[endpoint] = {
                    'request_count': len(metrics),
                    'avg_duration_ms': round(sum(durations) / len(durations), 2),
                    'min_duration_ms': min(durations),
                    'max_duration_ms': max(durations),
                    'p95_duration_ms': self._calculate_percentile(durations, 95),
                    'p99_duration_ms': self._calculate_percentile(durations, 99),
                    'error_count': len(errors),
                    'error_rate': (len(errors) / len(metrics)) * 100,
                    'avg_memory_mb': round(sum(memory_usage) / len(memory_usage), 2) if memory_usage else 0,
                    'requests_per_hour': len(metrics) / max(hours, 1)
                }
            
            # System health summary
            system_health = self.get_system_health()
            
            # Top performers and problem areas
            if endpoint_performance:
                # Fastest endpoints
                fastest_endpoints = sorted(
                    endpoint_performance.items(),
                    key=lambda x: x[1]['avg_duration_ms']
                )[:5]
                
                # Slowest endpoints
                slowest_endpoints = sorted(
                    endpoint_performance.items(),
                    key=lambda x: x[1]['avg_duration_ms'],
                    reverse=True
                )[:5]
                
                # Highest error rates
                error_prone_endpoints = sorted(
                    [(ep, data) for ep, data in endpoint_performance.items() if data['error_count'] > 0],
                    key=lambda x: x[1]['error_rate'],
                    reverse=True
                )[:5]
            else:
                fastest_endpoints = []
                slowest_endpoints = []
                error_prone_endpoints = []
            
            return {
                'report_generated': datetime.now().isoformat(),
                'summary': performance_summary,
                'endpoint_performance': endpoint_performance,
                'system_health': system_health,
                'top_performers': {
                    'fastest_endpoints': fastest_endpoints,
                    'slowest_endpoints': slowest_endpoints,
                    'error_prone_endpoints': error_prone_endpoints
                },
                'slow_queries': self.get_slow_queries(),
                'recommendations': self._generate_performance_recommendations(endpoint_performance, system_health)
            }
    
    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile for a list of values"""
        if not values:
            return 0
        
        sorted_values = sorted(values)
        index = int((percentile / 100) * len(sorted_values))
        index = min(index, len(sorted_values) - 1)
        
        return round(sorted_values[index], 2)
    
    def _generate_performance_recommendations(self, endpoint_performance: Dict, system_health: Dict) -> List[str]:
        """Generate performance recommendations based on metrics"""
        recommendations = []
        
        # System-level recommendations
        health_status = system_health.get('health_status', 'unknown')
        
        if health_status in ['critical', 'warning']:
            recommendations.append(f"System health is {health_status}. Monitor resource usage closely.")
        
        if system_health.get('trends', {}).get('memory', {}).get('trend') == 'increasing':
            recommendations.append("Memory usage is trending upward. Check for memory leaks.")
        
        if system_health.get('trends', {}).get('cpu', {}).get('trend') == 'increasing':
            recommendations.append("CPU usage is trending upward. Consider optimizing compute-intensive operations.")
        
        # Endpoint-level recommendations
        if endpoint_performance:
            # Slow endpoints
            slow_endpoints = [
                ep for ep, data in endpoint_performance.items() 
                if data['avg_duration_ms'] > 5000  # > 5 seconds
            ]
            
            if slow_endpoints:
                recommendations.append(f"Slow endpoints detected: {', '.join(slow_endpoints[:3])}. Consider optimization.")
            
            # High error rates
            high_error_endpoints = [
                ep for ep, data in endpoint_performance.items() 
                if data['error_rate'] > 5  # > 5% error rate
            ]
            
            if high_error_endpoints:
                recommendations.append(f"High error rates in: {', '.join(high_error_endpoints[:3])}. Review error handling.")
            
            # Memory-intensive endpoints
            memory_intensive = [
                ep for ep, data in endpoint_performance.items() 
                if data['avg_memory_mb'] > 100  # > 100MB average
            ]
            
            if memory_intensive:
                recommendations.append(f"Memory-intensive endpoints: {', '.join(memory_intensive[:3])}. Optimize memory usage.")
        
        return recommendations
    
    def clear_metrics(self):
        """Clear all collected metrics"""
        with self.lock:
            self.metrics.clear()
            self.slow_queries.clear()
            self.endpoint_stats.clear()
            self.system_metrics.clear()
            self.resource_alerts.clear()
            logger.info("All performance metrics cleared")
    
    def export_metrics(self, format: str = 'json') -> str:
        """Export metrics in specified format"""
        with self.lock:
            data = {
                'endpoint_stats': dict(self.endpoint_stats),
                'system_health': self.get_system_health(),
                'slow_queries': list(self.slow_queries),
                'export_timestamp': datetime.now().isoformat()
            }
            
            if format.lower() == 'json':
                return json.dumps(data, indent=2, default=str)
            else:
                raise ValueError(f"Unsupported export format: {format}")

def profile_endpoint(threshold_ms: int = 1000, include_memory: bool = True, 
                    include_cpu: bool = False):
    """
    Decorator to profile endpoint performance with comprehensive metrics
    
    Args:
        threshold_ms: Threshold for logging slow endpoints
        include_memory: Whether to track memory usage
        include_cpu: Whether to track CPU usage
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            memory_before = psutil.Process().memory_info().rss if include_memory else 0
            cpu_before = psutil.cpu_percent() if include_cpu else 0
            
            try:
                result = f(*args, **kwargs)
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
                
                cpu_after = psutil.cpu_percent() if include_cpu else 0
                cpu_percent = max(cpu_after, cpu_before) if include_cpu else 0  # Take max to account for spikes
                
                # Record metrics
                profiler.record_endpoint_metric(
                    endpoint=f.__name__,
                    duration_ms=duration_ms,
                    memory_delta_mb=memory_delta_mb,
                    cpu_percent=cpu_percent,
                    status=status
                )
                
                # Log slow endpoints
                if duration_ms > threshold_ms:
                    logger.warning(
                        f"Slow endpoint: {f.__name__} took {duration_ms:.2f}ms "
                        f"(memory delta: {memory_delta_mb:.2f}MB)"
                    )
            
            return result
        
        return wrapper
    return decorator

# Global profiler instance
profiler = PerformanceProfiler()