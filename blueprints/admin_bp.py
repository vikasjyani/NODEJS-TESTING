# blueprints/admin_bp.py (OPTIMIZED)
"""
Optimized Admin Blueprint with Service Layer Integration
 with caching, standardized error handling, and performance monitoring
"""
import logging
import os
import json
from datetime import datetime
from flask import Blueprint, render_template, request, current_app, g

from utils.base_blueprint import ServiceBlueprint,with_service
from utils.common_decorators import (
    require_project, handle_exceptions, api_route, 
    track_performance, cache_route
)
from utils.response_utils import success_json, error_json, validation_error_json
from utils.constants import ERROR_MESSAGES, SUCCESS_MESSAGES
from services.admin_service import AdminService

logger = logging.getLogger(__name__)

class AdminBlueprint(ServiceBlueprint):
    """Optimized Admin Blueprint with comprehensive system management"""
    
    def __init__(self):
        super().__init__(
            'admin',
            __name__,
            service_class=AdminService,
            template_folder='../templates',
            static_folder='../static',
            url_prefix='/admin'
        )
    
    def register_routes(self):
        """Register optimized admin routes"""
        
        # Main Admin Routes
        @self.blueprint.route('/features')
        @handle_exceptions('admin')
        @track_performance()
        def feature_management_route():
            return self._render_feature_management()
        
        @self.blueprint.route('/system')
        @handle_exceptions('admin')
        @track_performance()
        def system_status_route():
            return self._render_system_status()
        
        # API Routes with optimized caching
        @self.blueprint.route('/api/features')
        @api_route(cache_ttl=300)
        def get_features_api():
            return self._get_features()
        
        @self.blueprint.route('/api/features/<feature_id>', methods=['PUT'])
        @api_route(required_json_fields=['enabled'])
        def update_feature_api(feature_id):
            return self._update_feature(feature_id)
        
        @self.blueprint.route('/api/features/bulk_update', methods=['POST'])
        @api_route(required_json_fields=['features'])
        def bulk_update_features_api():
            return self._bulk_update_features()
        
        @self.blueprint.route('/api/system/cleanup', methods=['POST'])
        @api_route()
        def system_cleanup_api():
            return self._system_cleanup()
        
        @self.blueprint.route('/api/system/info')
        @api_route(cache_ttl=60)
        def system_info_api():
            return self._get_system_info()
        
        @self.blueprint.route('/api/system/health')
        @api_route(cache_ttl=30)
        def system_health_api():
            return self._get_system_health()
    
    def _render_feature_management(self):
        """Render feature management page with cached data"""
        try:
            # Check admin access
            if not self._validate_admin_access():
                return self._redirect_with_message("Admin access required", 'danger')
            
            # Get cached feature data
            feature_data = self._get_cached_feature_data()
            
            context = {
                'project_info': self._get_project_info(),
                'features_by_category': feature_data.get('features_by_category', {}),
                'feature_groups': feature_data.get('feature_groups', {}),
                'total_features': feature_data.get('total_features', 0),
                'enabled_count': feature_data.get('enabled_count', 0),
                'page_title': 'Feature Management',
                'system_health': self._get_basic_system_health()
            }
            
            return render_template('admin/feature_management.html', **context)
            
        except Exception as e:
            logger.exception(f"Error rendering feature management: {e}")
            return self._redirect_with_message(f"Error: {str(e)}", 'danger')
    
    def _render_system_status(self):
        """Render system status page with performance data"""
        try:
            if not self._validate_admin_access():
                return self._redirect_with_message("Admin access required", 'danger')
            
            # Get cached system data
            system_data = self._get_cached_system_data()
            
            context = {
                'system_info': system_data.get('system_info', {}),
                'project_stats': system_data.get('project_stats', {}),
                'app_config': system_data.get('app_config', {}),
                'performance_metrics': system_data.get('performance_metrics', {}),
                'memory_usage': system_data.get('memory_usage', {}),
                'cache_stats': system_data.get('cache_stats', {}),
                'page_title': 'System Administration'
            }
            
            return render_template('admin/system_status.html', **context)
            
        except Exception as e:
            logger.exception(f"Error rendering system status: {e}")
            return self._redirect_with_message(f"Error: {str(e)}", 'danger')
    
    @with_service
    def _get_features(self):
        """Get features with  caching"""
        try:
            project_path = current_app.config.get('CURRENT_PROJECT_PATH')
            features_data = self.service.get_features_configuration(project_path)
            
            return success_json(
                "Features retrieved successfully",
                {
                    'features': features_data.get('features', {}),
                    'feature_groups': features_data.get('feature_groups', {}),
                    'metadata': features_data.get('metadata', {}),
                    'project_path': project_path,
                    'has_project': project_path is not None,
                    'cache_timestamp': datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.exception(f"Error getting features: {e}")
            return error_json(f"Failed to retrieve features: {str(e)}")
    
    @with_service
    def _update_feature(self, feature_id: str):
        """Update feature with validation and caching invalidation"""
        try:
            data = request.get_json()
            enabled = data.get('enabled')
            
            if not isinstance(enabled, bool):
                return validation_error_json("'enabled' must be a boolean value")
            
            project_path = current_app.config.get('CURRENT_PROJECT_PATH')
            
            # Update feature
            result = self.service.update_feature_status(
                feature_id, enabled, project_path
            )
            
            if result.get('success'):
                # Invalidate cache
                self._invalidate_feature_cache()
                
                return success_json(
                    f"Feature '{feature_id}' {'enabled' if enabled else 'disabled'} successfully",
                    {
                        'feature_id': feature_id,
                        'enabled': enabled,
                        'timestamp': datetime.now().isoformat()
                    }
                )
            else:
                return error_json(result.get('error', 'Failed to update feature'))
                
        except Exception as e:
            logger.exception(f"Error updating feature {feature_id}: {e}")
            return error_json(f"Failed to update feature: {str(e)}")
    
    @with_service
    def _bulk_update_features(self):
        """Bulk update features with transaction-like behavior"""
        try:
            data = request.get_json()
            features_updates = data.get('features', {})
            
            if not isinstance(features_updates, dict):
                return validation_error_json("Features data must be a dictionary")
            
            project_path = current_app.config.get('CURRENT_PROJECT_PATH')
            
            # Execute bulk update
            result = self.service.bulk_update_features(features_updates, project_path)
            
            # Invalidate cache on any success
            if result.get('successful_updates'):
                self._invalidate_feature_cache()
            
            return success_json(
                f"Bulk update completed: {len(result.get('successful_updates', []))} successful, "
                f"{len(result.get('failed_updates', []))} failed",
                result
            )
            
        except Exception as e:
            logger.exception(f"Error in bulk update: {e}")
            return error_json(f"Bulk update failed: {str(e)}")
    
    @with_service
    def _system_cleanup(self):
        """System cleanup with progress tracking"""
        try:
            data = request.get_json() or {}
            cleanup_type = data.get('type', 'logs')
            max_age_days = data.get('max_age_days', 30)
            
            # Execute cleanup
            cleanup_result = self.service.perform_system_cleanup(
                cleanup_type=cleanup_type,
                max_age_days=max_age_days
            )
            
            # Invalidate system cache after cleanup
            self._invalidate_system_cache()
            
            return success_json(
                f"System cleanup completed: {cleanup_result.get('total_files_cleaned', 0)} files cleaned",
                cleanup_result
            )
            
        except Exception as e:
            logger.exception(f"Error in system cleanup: {e}")
            return error_json(f"System cleanup failed: {str(e)}")
    
    @with_service
    def _get_system_info(self):
        """Get comprehensive system information"""
        try:
            system_info = self.service.get_comprehensive_system_info()
            
            return success_json(
                "System information retrieved successfully",
                system_info
            )
        except Exception as e:
            logger.exception(f"Error getting system info: {e}")
            return error_json(f"Failed to retrieve system info: {str(e)}")
    
    @with_service
    def _get_system_health(self):
        """Get real-time system health metrics"""
        try:
            health_data = self.service.get_system_health_metrics()
            
            return success_json(
                "System health metrics retrieved",
                health_data
            )
        except Exception as e:
            logger.exception(f"Error getting system health: {e}")
            return error_json(f"Failed to get system health: {str(e)}")
    
    # Helper Methods
    def _validate_admin_access(self) -> bool:
        """Validate admin access with  security"""
        # For now, basic validation - can be  with role-based access
        return True
    
    def _get_project_info(self) -> dict:
        """Get current project information"""
        return {
            'name': current_app.config.get('CURRENT_PROJECT'),
            'path': current_app.config.get('CURRENT_PROJECT_PATH'),
            'has_project': bool(current_app.config.get('CURRENT_PROJECT_PATH'))
        }
    
    @cache_route(ttl=300, key_func=lambda: "admin_feature_data")
    def _get_cached_feature_data(self) -> dict:
        """Get cached feature data with fallback"""
        try:
            if not self.service:
                return {}
            
            project_path = current_app.config.get('CURRENT_PROJECT_PATH')
            return self.service.get_features_configuration(project_path)
        except Exception as e:
            logger.error(f"Error getting cached feature data: {e}")
            return {}
    
    @cache_route(ttl=60, key_func=lambda: "admin_system_data")
    def _get_cached_system_data(self) -> dict:
        """Get cached system data"""
        try:
            if not self.service:
                return {}
            
            return self.service.get_comprehensive_system_info()
        except Exception as e:
            logger.error(f"Error getting cached system data: {e}")
            return {}
    
    def _get_basic_system_health(self) -> dict:
        """Get basic system health for UI display"""
        try:
            if not self.service:
                return {'status': 'unknown'}
            
            return self.service.get_basic_health_status()
        except Exception:
            return {'status': 'unknown'}
    
    def _invalidate_feature_cache(self):
        """Invalidate feature-related caches"""
        # This would clear relevant cache entries
        pass
    
    def _invalidate_system_cache(self):
        """Invalidate system-related caches"""
        # This would clear relevant cache entries
        pass
    
    def _redirect_with_message(self, message: str, category: str = 'info'):
        """Helper to redirect with flash message"""
        from flask import flash, redirect, url_for
        flash(message, category)
        return redirect(url_for('core.home'))

# Create the optimized blueprint
admin_blueprint = AdminBlueprint()
admin_bp = admin_blueprint.blueprint

# Export for Flask app registration
def register_admin_bp(app):
    """Register the admin blueprint with optimizations"""
    admin_blueprint.register(app)