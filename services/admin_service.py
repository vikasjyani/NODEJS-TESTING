# services/admin_service.py
"""
Admin Service Layer
Handles system administration, feature management, and monitoring
"""
import os
import json
import time
import psutil
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from utils.features_manager import FeatureManager
from utils.memory_manager import memory_manager
from utils.performance_profiler import profiler
from utils.cache_manager import cache_manager
from utils.helpers import cleanup_old_files, get_file_info

logger = logging.getLogger(__name__)

class AdminService:
    """
    Service layer for admin operations with optimized performance
    """
    
    def __init__(self, project_path: str = None):
        self.project_path = project_path
        
        # Initialize managers
        self.feature_manager = None
        self._init_feature_manager()
        
    def _init_feature_manager(self):
        """Initialize feature manager with error handling"""
        try:
            from flask import current_app
            if hasattr(current_app, 'feature_manager'):
                self.feature_manager = current_app.feature_manager
            else:
                self.feature_manager = FeatureManager(current_app)
                current_app.feature_manager = self.feature_manager
        except Exception as e:
            logger.error(f"Failed to initialize feature manager: {e}")
            self.feature_manager = None
    
    def get_features_configuration(self, project_path: str = None) -> Dict[str, Any]:
        """Get comprehensive features configuration with caching"""
        try:
            if not self.feature_manager:
                return {'features': {}, 'feature_groups': {}, 'error': 'Feature manager not available'}
            
            # Get merged features
            features_config = self.feature_manager.get_merged_features(project_path)
            
            # Organize features by category
            features_by_category = {}
            for feature_id, feature_config in features_config.get('features', {}).items():
                category = feature_config.get('category', 'general')
                if category not in features_by_category:
                    features_by_category[category] = []
                
                feature_info = {
                    'id': feature_id,
                    'description': feature_config.get('description', ''),
                    'enabled': feature_config.get('enabled', False),
                    'category': category,
                    'last_modified': feature_config.get('last_modified', '')
                }
                features_by_category[category].append(feature_info)
            
            # Calculate statistics
            total_features = len(features_config.get('features', {}))
            enabled_count = len([f for f in features_config.get('features', {}).values() 
                               if f.get('enabled', False)])
            
            return {
                'features': features_config.get('features', {}),
                'features_by_category': features_by_category,
                'feature_groups': features_config.get('feature_groups', {}),
                'total_features': total_features,
                'enabled_count': enabled_count,
                'metadata': features_config.get('metadata', {}),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.exception(f"Error getting features configuration: {e}")
            return {'error': str(e), 'features': {}, 'feature_groups': {}}
    
    def update_feature_status(self, feature_id: str, enabled: bool, 
                            project_path: str = None) -> Dict[str, Any]:
        """Update feature status with validation"""
        try:
            if not self.feature_manager:
                return {'success': False, 'error': 'Feature manager not available'}
            
            # Update feature
            success = self.feature_manager.set_feature_enabled(
                feature_id, enabled, project_path
            )
            
            if success:
                # Get updated feature info
                updated_feature = self.feature_manager.get_feature_info(feature_id, project_path)
                
                logger.info(f"Feature {feature_id} updated: enabled={enabled}")
                
                return {
                    'success': True,
                    'feature_id': feature_id,
                    'enabled': enabled,
                    'feature_info': updated_feature,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {'success': False, 'error': 'Feature update operation failed'}
                
        except Exception as e:
            logger.exception(f"Error updating feature {feature_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def bulk_update_features(self, features_updates: Dict[str, Dict], 
                           project_path: str = None) -> Dict[str, Any]:
        """Bulk update features with transaction-like behavior"""
        try:
            if not self.feature_manager:
                return {
                    'successful_updates': [],
                    'failed_updates': [{'error': 'Feature manager not available'}]
                }
            
            successful_updates = []
            failed_updates = []
            
            # Process each feature update
            for feature_id, feature_config in features_updates.items():
                try:
                    if 'enabled' in feature_config:
                        success = self.feature_manager.set_feature_enabled(
                            feature_id, feature_config['enabled'], project_path
                        )
                        
                        if success:
                            successful_updates.append({
                                'feature_id': feature_id,
                                'enabled': feature_config['enabled']
                            })
                        else:
                            failed_updates.append({
                                'feature_id': feature_id,
                                'error': 'Update operation failed'
                            })
                            
                except Exception as feature_error:
                    failed_updates.append({
                        'feature_id': feature_id,
                        'error': str(feature_error)
                    })
            
            logger.info(f"Bulk update: {len(successful_updates)} successful, {len(failed_updates)} failed")
            
            return {
                'successful_updates': successful_updates,
                'failed_updates': failed_updates,
                'total_processed': len(features_updates),
                'success_rate': len(successful_updates) / len(features_updates) if features_updates else 0
            }
            
        except Exception as e:
            logger.exception(f"Error in bulk feature update: {e}")
            return {
                'successful_updates': [],
                'failed_updates': [{'error': str(e)}],
                'total_processed': len(features_updates)
            }
    
    def perform_system_cleanup(self, cleanup_type: str = 'logs', 
                             max_age_days: int = 30) -> Dict[str, Any]:
        """Perform comprehensive system cleanup"""
        try:
            from flask import current_app
            
            cleanup_results = {}
            total_cleaned = 0
            
            # Clean up log files
            if cleanup_type in ['all', 'logs']:
                logs_folder = current_app.config.get('LOGS_FOLDER', 'logs')
                if os.path.exists(logs_folder):
                    logs_result = cleanup_old_files(
                        logs_folder,
                        max_age_days=max_age_days,
                        file_patterns=['.log']
                    )
                    cleanup_results['logs'] = logs_result
                    total_cleaned += len(logs_result.get('cleaned_files', []))
            
            # Clean up temporary files
            if cleanup_type in ['all', 'temp']:
                upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/user_uploads')
                if os.path.exists(upload_folder):
                    temp_result = cleanup_old_files(
                        upload_folder,
                        max_age_days=7,  # More aggressive for temp files
                        file_patterns=['.tmp', '.temp']
                    )
                    cleanup_results['temp'] = temp_result
                    total_cleaned += len(temp_result.get('cleaned_files', []))
            
            # Clear caches
            if cleanup_type in ['all', 'cache']:
                cache_result = {'success': True, 'message': 'Caches cleared'}
                
                # Clear feature manager cache
                if self.feature_manager:
                    self.feature_manager.clear_cache()
                
                # Clear other caches
                if hasattr(cache_manager, 'memory_cache'):
                    cache_manager.memory_cache.clear()
                
                cleanup_results['cache'] = cache_result
            
            # Memory cleanup
            if cleanup_type in ['all', 'memory']:
                memory_result = memory_manager.force_cleanup()
                cleanup_results['memory'] = {
                    'success': True,
                    'message': 'Memory cleanup performed'
                }
            
            return {
                'cleanup_results': cleanup_results,
                'total_files_cleaned': total_cleaned,
                'cleanup_type': cleanup_type,
                'max_age_days': max_age_days,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.exception(f"Error during system cleanup: {e}")
            return {
                'cleanup_results': {},
                'total_files_cleaned': 0,
                'error': str(e)
            }
    
    def get_comprehensive_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information with performance data"""
        try:
            import platform
            
            # Basic system info
            system_info = {
                'platform': {
                    'system': platform.system(),
                    'release': platform.release(),
                    'machine': platform.machine(),
                    'processor': platform.processor(),
                    'python_version': platform.python_version()
                },
                'resources': self._get_resource_info(),
                'disk': self._get_disk_info(),
                'application': self._get_application_info()
            }
            
            # Performance metrics
            performance_metrics = self._get_performance_metrics()
            
            # Memory usage
            memory_usage = memory_manager.get_memory_stats() if memory_manager else {}
            
            # Cache statistics
            cache_stats = cache_manager.get_stats() if cache_manager else {}
            
            # Project statistics
            project_stats = self._get_project_statistics()
            
            return {
                'system_info': system_info,
                'performance_metrics': performance_metrics,
                'memory_usage': memory_usage,
                'cache_stats': cache_stats,
                'project_stats': project_stats,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.exception(f"Error getting comprehensive system info: {e}")
            return {'error': str(e)}
    
    def get_system_health_metrics(self) -> Dict[str, Any]:
        """Get real-time system health metrics"""
        try:
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk_usage = psutil.disk_usage('/')
            
            # Application health
            app_health = self._check_application_health()
            
            # Determine overall health status
            health_status = self._determine_health_status(cpu_percent, memory.percent, app_health)
            
            return {
                'overall_health': health_status,
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'disk_percent': disk_usage.percent,
                'disk_free_gb': disk_usage.free / (1024**3),
                'application_health': app_health,
                'active_processes': len(psutil.pids()),
                'uptime_seconds': time.time() - psutil.boot_time(),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.exception(f"Error getting system health: {e}")
            return {'error': str(e), 'overall_health': 'unknown'}
    
    def get_basic_health_status(self) -> Dict[str, Any]:
        """Get basic health status for UI display"""
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent()
            
            if cpu_percent > 90 or memory.percent > 90:
                status = 'critical'
            elif cpu_percent > 70 or memory.percent > 80:
                status = 'warning'
            else:
                status = 'healthy'
            
            return {
                'status': status,
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent
            }
        except Exception:
            return {'status': 'unknown'}
    
    # Private helper methods
    def _get_resource_info(self) -> Dict[str, Any]:
        """Get system resource information"""
        try:
            return {
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': round(psutil.virtual_memory().total / (1024**3), 2),
                'memory_available_gb': round(psutil.virtual_memory().available / (1024**3), 2),
                'memory_percent': psutil.virtual_memory().percent
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _get_disk_info(self) -> Dict[str, Any]:
        """Get disk usage information"""
        try:
            from flask import current_app
            project_root = current_app.config.get('PROJECT_ROOT', '.')
            disk_usage = psutil.disk_usage(project_root)
            
            return {
                'total_gb': round(disk_usage.total / (1024**3), 2),
                'used_gb': round(disk_usage.used / (1024**3), 2),
                'free_gb': round(disk_usage.free / (1024**3), 2),
                'percent_used': round((disk_usage.used / disk_usage.total) * 100, 1)
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _get_application_info(self) -> Dict[str, Any]:
        """Get application-specific information"""
        try:
            from flask import current_app
            
            return {
                'version': '1.0.0',
                'debug_mode': current_app.debug,
                'environment': os.environ.get('FLASK_ENV', 'production'),
                'features_available': len(self.feature_manager.get_enabled_features()) if self.feature_manager else 0
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics from profiler"""
        try:
            if profiler:
                return profiler.get_stats()
            return {}
        except Exception as e:
            logger.debug(f"Error getting performance metrics: {e}")
            return {}
    
    def _get_project_statistics(self) -> Dict[str, Any]:
        """Get project-related statistics"""
        try:
            from flask import current_app
            project_root = current_app.config.get('PROJECT_ROOT', 'projects')
            
            if not os.path.exists(project_root):
                return {'total_projects': 0, 'projects': []}
            
            projects = []
            total_size = 0
            
            for item in os.listdir(project_root):
                item_path = os.path.join(project_root, item)
                if os.path.isdir(item_path):
                    try:
                        # Calculate project size
                        project_size = 0
                        for root, dirs, files in os.walk(item_path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                try:
                                    project_size += os.path.getsize(file_path)
                                except (OSError, IOError):
                                    pass
                        
                        projects.append({
                            'name': item,
                            'path': item_path,
                            'size_mb': round(project_size / (1024 * 1024), 2)
                        })
                        total_size += project_size
                        
                    except Exception as project_error:
                        logger.warning(f"Error processing project {item}: {project_error}")
            
            return {
                'total_projects': len(projects),
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'projects': projects
            }
            
        except Exception as e:
            logger.exception(f"Error getting project statistics: {e}")
            return {'error': str(e)}
    
    def _check_application_health(self) -> Dict[str, Any]:
        """Check application-specific health indicators"""
        try:
            health_indicators = {}
            
            # Check feature manager
            health_indicators['feature_manager'] = self.feature_manager is not None
            
            # Check cache manager
            health_indicators['cache_manager'] = hasattr(cache_manager, 'get_stats')
            
            # Check memory manager
            health_indicators['memory_manager'] = hasattr(memory_manager, 'check_memory_usage')
            
            # Overall application health
            app_healthy = all(health_indicators.values())
            
            return {
                'healthy': app_healthy,
                'components': health_indicators
            }
            
        except Exception as e:
            return {'healthy': False, 'error': str(e)}
    
    def _determine_health_status(self, cpu_percent: float, memory_percent: float, 
                               app_health: Dict) -> str:
        """Determine overall system health status"""
        try:
            # Critical thresholds
            if cpu_percent > 95 or memory_percent > 95:
                return 'critical'
            
            # Warning thresholds
            if cpu_percent > 80 or memory_percent > 85:
                return 'warning'
            
            # Application health check
            if not app_health.get('healthy', True):
                return 'degraded'
            
            # Degraded thresholds
            if cpu_percent > 60 or memory_percent > 70:
                return 'degraded'
            
            return 'healthy'
            
        except Exception:
            return 'unknown'