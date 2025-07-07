# blueprints/core_bp.py (OPTIMIZED)
"""
Optimized Core Blueprint with ServiceBlueprint integration
Implements standardized patterns, caching, and performance monitoring
"""
import time
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor

from utils.base_blueprint import ServiceBlueprint, with_service
from utils.common_decorators import (
    handle_exceptions, api_route, track_performance, 
    cache_route, memory_efficient_operation
)
from utils.response_utils import success_json, error_json, streaming_response, validation_error_json
from utils.constants import SUCCESS_MESSAGES, ERROR_MESSAGES

# Create dummy service for now - will be replaced when services are implemented
class CoreService:
    def __init__(self, project_path=None):
        self.project_path = project_path
    
    def get_dashboard_data(self, include_details=False):
        return {"message": "Dashboard data placeholder"}
    
    def get_cached_dashboard_data(self):
        return {"message": "Cached dashboard data placeholder"}
    
    def get_heavy_dashboard_data(self):
        return {"message": "Heavy dashboard data placeholder"}
    
    def get_project_status(self, include_details=False):
        return {"message": "Project status placeholder"}
    
    def get_project_details(self):
        return {"message": "Project details placeholder"}
    
    def get_system_info(self):
        return {"message": "System info placeholder"}
    
    def get_health_status(self):
        return {"healthy": True, "status": "OK"}
    
    def get_navigation_data(self):
        return {"navigation": []}
    
    def get_recent_activities(self, limit=10, activity_type='all'):
        return []
    
    def get_performance_metrics(self):
        return {"metrics": {}}
    
    def clear_caches(self, cache_types):
        return cache_types
    
    def get_feature_flags(self):
        return {"flags": {}}
    
    def get_notifications(self):
        return {"notifications": []}
    
    def get_essential_feature_flags(self):
        return {
            'demand_projection_enabled': True,
            'load_profiles_enabled': True,
            'pypsa_enabled': True,
            'visualization_enabled': True,
            'advanced_analytics_enabled': False
        }

logger = logging.getLogger(__name__)

class CoreBlueprint(ServiceBlueprint):
    """
    Optimized Core Blueprint with comprehensive system management
    """
    
    def __init__(self):
        super().__init__(
            'core',
            __name__,
            service_class=CoreService,
            template_folder='../templates',
            static_folder='../static'
        )
        
        # Thread pool for background operations
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="core-async")
    
    def register_routes(self):
        """Register optimized core routes with standardized patterns"""
        
        # Main interface routes
        @self.blueprint.route('/')
        @handle_exceptions('core')
        @track_performance(threshold_ms=1000)
        @memory_efficient_operation
        def home():
            return self._render_home_page()
        
        @self.blueprint.route('/user_guide')
        @handle_exceptions('core')
        @track_performance(threshold_ms=500)
        def user_guide():
            return self._render_user_guide()
        
        @self.blueprint.route('/about')
        @handle_exceptions('core')
        @track_performance(threshold_ms=300)
        def about():
            return self._render_about_page()
        
        @self.blueprint.route('/settings')
        @handle_exceptions('core')
        @track_performance(threshold_ms=400)
        def settings():
            return self._render_settings_page()
        
        @self.blueprint.route('/tutorials')
        @handle_exceptions('core')
        def tutorials():
            return self._render_tutorials_page()
        
        # API Routes
        @self.blueprint.route('/api/dashboard_data')
        @api_route(cache_ttl=120)
        def get_dashboard_data_api():
            return self._get_dashboard_data()
        
        @self.blueprint.route('/api/dashboard_stream')
        @api_route()
        def get_dashboard_stream_api():
            return self._get_dashboard_stream()
        
        @self.blueprint.route('/api/project_status')
        @api_route(cache_ttl=60)
        def get_project_status_api():
            return self._get_project_status()
        
        @self.blueprint.route('/api/project_details')
        @api_route(cache_ttl=300)
        def get_project_details_api():
            return self._get_project_details()
        
        @self.blueprint.route('/api/system_info')
        @api_route(cache_ttl=60)
        def get_system_info_api():
            return self._get_system_info()
        
        @self.blueprint.route('/api/health')
        @api_route()
        def health_check_api():
            return self._health_check()
        
        @self.blueprint.route('/api/navigation')
        @api_route(cache_ttl=300)
        def get_navigation_api():
            return self._get_navigation_data()
        
        @self.blueprint.route('/api/recent_activities')
        @api_route(cache_ttl=60)
        def get_recent_activities_api():
            return self._get_recent_activities()
        
        @self.blueprint.route('/api/performance_metrics')
        @api_route(cache_ttl=30)
        def get_performance_metrics_api():
            return self._get_performance_metrics()
        
        # Utility APIs
        @self.blueprint.route('/api/clear_cache', methods=['POST'])
        @api_route()
        def clear_cache_api():
            return self._clear_cache()
        
        @self.blueprint.route('/api/feature_flags')
        @api_route(cache_ttl=180)
        def get_feature_flags_api():
            return self._get_feature_flags()
        
        @self.blueprint.route('/api/notifications')
        @api_route(cache_ttl=30)
        def get_notifications_api():
            return self._get_notifications()
        # Color Management APIs
        @self.blueprint.route('/api/colors/get-all')
        @api_route(cache_ttl=3600) # Cache for an hour
        def get_all_colors_api():
            return self._get_all_colors()

        @self.blueprint.route('/api/colors/save-all', methods=['POST'])
        @api_route()
        def save_all_colors_api():
            return self._save_all_colors()




    @memory_efficient_operation
    def _render_home_page(self):
        """Render optimized home page with async data loading"""
        try:
            # Get essential data synchronously
            essential_data = self._get_essential_home_data()
            
            # Load heavy data asynchronously
            heavy_data_future = self.executor.submit(self._load_heavy_dashboard_data)
            
            # Get cached dashboard data
            dashboard_data = self._get_cached_dashboard_data()
            
            # Combine essential data with dashboard data
            page_data = {**essential_data, **dashboard_data}
            
            # Try to get heavy data with timeout
            try:
                heavy_data = heavy_data_future.result(timeout=2.0)
                page_data.update(heavy_data)
            except Exception as e:
                logger.warning(f"Heavy data loading failed or timed out: {e}")
                page_data['heavy_data_error'] = str(e)
            
            return self._render_template('home.html', **page_data)
            
        except Exception as e:
            logger.exception(f"Error rendering home page: {e}")
            return self._render_template('home.html', error=str(e))
    
    def _render_user_guide(self):
        """Render user guide page with contextual help"""
        try:
            guide_data = self._get_user_guide_data()
            return self._render_template('user_guide.html', **guide_data)
            
        except Exception as e:
            logger.exception(f"Error rendering user guide: {e}")
            return self._render_template('errors/500.html', error=str(e)), 500
    
    def _render_about_page(self):
        """Render about page with application information"""
        try:
            about_data = self._get_about_page_data()
            return self._render_template('about.html', **about_data)
            
        except Exception as e:
            logger.exception(f"Error rendering about page: {e}")
            return self._render_template('errors/500.html', error=str(e)), 500
    
    def _render_settings_page(self):
        """Render settings page with configuration options"""
        try:
            settings_data = self._get_settings_page_data()
            return self._render_template('settings.html', **settings_data)
            
        except Exception as e:
            logger.exception(f"Error rendering settings page: {e}")
            return self._render_template('errors/500.html', error=str(e)), 500
    
    def _render_tutorials_page(self):
        """Render tutorials page"""
        try:
            # For now, redirect to user guide with message
            from flask import flash, redirect, url_for
            flash('Tutorials section is under development. Please check the User Guide for now.', 'info')
            return redirect(url_for('core.user_guide'))
            
        except Exception as e:
            logger.exception(f"Error accessing tutorials: {e}")
            from flask import flash, redirect, url_for
            flash(f"Error accessing tutorials: {str(e)}", 'danger')
            return redirect(url_for('core.home'))
    
    @with_service
    def _get_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard data with performance optimization"""
        try:
            from flask import request, g
            
            # Check for streaming request
            stream_requested = request.args.get('stream', 'false').lower() == 'true'
            include_details = request.args.get('include_details', 'false').lower() == 'true'
            
            if stream_requested:
                return self._get_dashboard_stream()
            
            # Get cached dashboard data
            dashboard_data = self.service.get_dashboard_data(include_details)
            
            # Add performance information
            performance_info = {}
            if hasattr(g, 'start_time'):
                performance_info['response_time_ms'] = (time.time() - g.start_time) * 1000
            
            # Add memory usage
            try:
                import psutil
                performance_info['memory_usage_mb'] = psutil.Process().memory_info().rss / 1024 / 1024
            except ImportError:
                pass
            
            return success_json(
                "Dashboard data retrieved successfully",
                data=dashboard_data,
                performance_info=performance_info,
                cached=True
            )
            
        except Exception as e:
            logger.exception(f"Error getting dashboard data: {e}")
            return error_json(f"Dashboard data error: {str(e)}")
    
    def _get_dashboard_stream(self):
        """Get dashboard data as stream for large datasets"""
        def generate_dashboard_stream():
            try:
                yield '{"status": "success", "data": {'
                
                # Basic data first
                basic_data = self._get_essential_home_data()
                yield f'"basic": {json.dumps(basic_data)},'
                
                # Project data
                if self.get_project_path():
                    yield '"project_data": ['
                    
                    activities = self.service.get_recent_activities()
                    for i, activity in enumerate(activities):
                        if i > 0:
                            yield ','
                        yield json.dumps(activity)
                    
                    yield '],'
                    
                    # Statistics
                    stats = self.service.get_project_statistics() if hasattr(self.service, 'get_project_statistics') else {}
                    yield f'"statistics": {json.dumps(stats)}'
                
                yield '}}'
                
            except Exception as e:
                logger.error(f"Error streaming dashboard data: {e}")
                yield f'{{"status": "error", "error": "{str(e)}"}}'
        
        return streaming_response(
            generate_dashboard_stream,
            mimetype='application/json'
        )
    
    @with_service
    def _get_project_status(self) -> Dict[str, Any]:
        """Get project status with lazy loading"""
        try:
            from flask import request
            
            include_details = request.args.get('include_details', 'false').lower() == 'true'
            
            project_status = self.service.get_project_status(include_details)
            
            return success_json(
                "Project status retrieved successfully",
                project_status
            )
            
        except Exception as e:
            logger.exception(f"Error getting project status: {e}")
            return error_json(f"Project status error: {str(e)}")
    
    @with_service
    def _get_project_details(self) -> Dict[str, Any]:
        """Get detailed project information"""
        try:
            project_details = self.service.get_project_details()
            
            return success_json(
                "Project details retrieved successfully",
                project_details
            )
            
        except Exception as e:
            logger.exception(f"Error getting project details: {e}")
            return error_json(f"Project details error: {str(e)}")
    
    @with_service
    def _get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information"""
        try:
            system_info = self.service.get_system_info()
            
            return success_json(
                "System information retrieved successfully",
                system_info
            )
            
        except Exception as e:
            logger.exception(f"Error getting system info: {e}")
            return error_json(f"System info error: {str(e)}")
    
    @with_service
    def _health_check(self) -> Dict[str, Any]:
        """Comprehensive health check endpoint"""
        try:
            health_data = self.service.get_health_status()
            
            # Determine status code based on health
            status_code = 200 if health_data.get('healthy', True) else 503
            
            return success_json(
                "Health check completed",
                health_data
            ), status_code
            
        except Exception as e:
            logger.exception("Health check failed")
            return error_json(
                "Health check failed",
                error=str(e)
            ), 503
    
    @with_service
    def _get_navigation_data(self) -> Dict[str, Any]:
        """Get navigation data with feature flags"""
        try:
            navigation_data = self.service.get_navigation_data()
            
            return success_json(
                "Navigation data retrieved successfully",
                navigation_data
            )
            
        except Exception as e:
            logger.exception(f"Error getting navigation data: {e}")
            return error_json(f"Navigation data error: {str(e)}")
    
    @with_service
    def _get_recent_activities(self) -> Dict[str, Any]:
        """Get recent activities with optimization"""
        try:
            from flask import request
            
            limit = request.args.get('limit', 10, type=int)
            activity_type = request.args.get('type', 'all')
            
            activities = self.service.get_recent_activities(limit, activity_type)
            
            return success_json(
                "Recent activities retrieved successfully",
                {
                    'activities': activities,
                    'total_count': len(activities),
                    'limit': limit,
                    'activity_type': activity_type
                }
            )
            
        except Exception as e:
            logger.exception(f"Error getting recent activities: {e}")
            return error_json(f"Recent activities error: {str(e)}")
    
    @with_service
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        try:
            performance_metrics = self.service.get_performance_metrics()
            
            return success_json(
                "Performance metrics retrieved successfully",
                performance_metrics
            )
            
        except Exception as e:
            logger.exception(f"Error getting performance metrics: {e}")
            return error_json(f"Performance metrics error: {str(e)}")
    
    @with_service
    def _clear_cache(self) -> Dict[str, Any]:
        """Clear application caches"""
        try:
            from flask import request
            
            data = request.get_json() or {}
            cache_types = data.get('cache_types', ['memory_cache'])
            
            cleared_caches = self.service.clear_caches(cache_types)
            
            return success_json(
                f"Cleared caches: {', '.join(cleared_caches)}",
                {
                    'cleared_caches': cleared_caches,
                    'timestamp': datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.exception(f"Error clearing cache: {e}")
            return error_json(f"Cache clear error: {str(e)}")
    
    @with_service
    def _get_feature_flags(self) -> Dict[str, Any]:
        """Get feature flags for UI"""
        try:
            feature_flags = self.service.get_feature_flags()
            
            return success_json(
                "Feature flags retrieved successfully",
                feature_flags
            )
            
        except Exception as e:
            logger.exception(f"Error getting feature flags: {e}")
            return error_json(f"Feature flags error: {str(e)}")
    
    @with_service
    def _get_notifications(self) -> Dict[str, Any]:
        """Get system notifications"""
        try:
            notifications = self.service.get_notifications()
            
            return success_json(
                "Notifications retrieved successfully",
                notifications
            )
            
        except Exception as e:
            logger.exception(f"Error getting notifications: {e}")
            return error_json(f"Notifications error: {str(e)}")
    




    def _get_all_colors(self) -> Dict[str, Any]:
        """Get all colors from the JSON file."""
        try:
            from flask import current_app

            colors_path = os.path.join(current_app.static_folder, 'config', 'colors.json')
            if not os.path.exists(colors_path):
                logger.error("colors.json file not found at %s", colors_path)
                return error_json(ERROR_MESSAGES['FILE_NOT_FOUND'], status_code=404)

            with open(colors_path, 'r', encoding='utf-8') as f:
                colors_data = json.load(f)
            
            return success_json("Colors fetched successfully", colors_data)
        except Exception as e:
            logger.exception(f"Error reading colors.json: {e}")
            return error_json(f"Failed to read colors file: {str(e)}")

    def _save_all_colors(self) -> Dict[str, Any]:
        """Save all colors to the JSON file."""
        try:
            from flask import current_app, request

            colors_data = request.get_json()
            if not colors_data:
                return validation_error_json("No color data provided in request.")

            # Ensure the target directory exists
            config_dir = os.path.join(current_app.static_folder, 'config')
            os.makedirs(config_dir, exist_ok=True)
            
            colors_path = os.path.join(config_dir, 'colors.json')
            # Basic validation
            if not isinstance(colors_data, dict):
                 return validation_error_json("Invalid color data format. Expected a dictionary.")

            with open(colors_path, 'w', encoding='utf-8') as f:
                json.dump(colors_data, f, indent=2, ensure_ascii=False)
                f.write('\n')
            
            logger.info("Successfully saved colors to colors.json")
            return success_json("Colors saved successfully", {'saved_at': datetime.now().isoformat()})
        except Exception as e:
            logger.exception(f"Error saving colors.json: {e}")
            return error_json(f"Failed to save colors file: {str(e)}")
    

    # Helper methods
    def _get_essential_home_data(self) -> Dict[str, Any]:
        """Get essential data that must load quickly"""
        try:
            return {
                'page_title': 'Energy Futures Dashboard',
                'app_version': '1.0.0',
                'current_user': 'default',
                'navigation_items': self._get_navigation_items(),
                'feature_flags': self._get_essential_feature_flags(),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting essential data: {e}")
            return {'error': str(e)}
    
    def _load_heavy_dashboard_data(self) -> Dict[str, Any]:
        """Load computationally expensive dashboard data in background"""
        try:
            if not self.service:
                return {'heavy_data_error': 'Service not available'}
            
            return self.service.get_heavy_dashboard_data()
            
        except Exception as e:
            logger.error(f"Error loading heavy dashboard data: {e}")
            return {'heavy_data_error': str(e)}
    
    @cache_route(ttl=300, key_func=lambda: "core_dashboard_data")
    def _get_cached_dashboard_data(self) -> Dict[str, Any]:
        """Get cached dashboard data"""
        try:
            if not self.service:
                return {'error': 'Service not available'}
            
            return self.service.get_cached_dashboard_data()
            
        except Exception as e:
            logger.error(f"Error getting cached dashboard data: {e}")
            return {'error': str(e)}
    
    @cache_route(ttl=180, key_func=lambda: "navigation_items")
    def _get_navigation_items(self) -> List[Dict[str, str]]:
        """Get navigation items with caching"""
        return [
            {'name': 'Home', 'url': '/', 'icon': 'fas fa-home'},
            {'name': 'Demand Projection', 'url': '/demand_projection', 'icon': 'fas fa-chart-line'},
            {'name': 'Load Profiles', 'url': '/load_profile', 'icon': 'fas fa-bolt'},
            {'name': 'PyPSA Modeling', 'url': '/pypsa/modeling', 'icon': 'fas fa-network-wired'},
            {'name': 'Results', 'url': '/demand_visualization', 'icon': 'fas fa-chart-bar'}
        ]
    
    def _get_essential_feature_flags(self) -> Dict[str, bool]:
        """Get essential feature flags for UI rendering"""
        try:
            if not self.service:
                return self._get_default_feature_flags()
            
            return self.service.get_essential_feature_flags()
            
        except Exception as e:
            logger.debug(f"Error getting feature flags: {e}")
            return self._get_default_feature_flags()
    
    def _get_default_feature_flags(self) -> Dict[str, bool]:
        """Get default feature flags"""
        return {
            'demand_projection_enabled': True,
            'load_profiles_enabled': True,
            'pypsa_enabled': True,
            'visualization_enabled': True,
            'advanced_analytics_enabled': False
        }
    
    def _get_user_guide_data(self) -> Dict[str, Any]:
        """Get user guide page data"""
        try:
            return {
                'has_project': self.get_project_path() is not None,
                'current_project': self._get_project_info().get('name'),
                'features_enabled': self._get_essential_feature_flags(),
                'guide_sections': [
                    {'id': 'getting_started', 'title': 'Getting Started', 'icon': 'fas fa-play'},
                    {'id': 'project_management', 'title': 'Project Management', 'icon': 'fas fa-folder'},
                    {'id': 'demand_forecasting', 'title': 'Demand Forecasting', 'icon': 'fas fa-chart-line'},
                    {'id': 'load_profiling', 'title': 'Load Profiling', 'icon': 'fas fa-bolt'},
                    {'id': 'pypsa_modeling', 'title': 'Power System Modeling', 'icon': 'fas fa-network-wired'},
                    {'id': 'results_analysis', 'title': 'Results & Analysis', 'icon': 'fas fa-chart-bar'}
                ]
            }
        except Exception as e:
            logger.error(f"Error getting user guide data: {e}")
            return {'error': str(e)}
    
    def _get_about_page_data(self) -> Dict[str, Any]:
        """Get about page data"""
        try:
            return {
                'app_name': 'KSEB Energy Futures Platform',
                'version': '1.0.0',
                'description': 'Advanced electricity demand forecasting and power system modeling platform',
                'features': [
                    'Electricity demand projection with multiple forecasting models',
                    'Load profile generation using Base Profile Scaling and STL decomposition',
                    'Power system modeling with PyPSA integration',
                    'Interactive visualization and analysis tools',
                    'Project-based file management system'
                ],
                'technologies': [
                    'Python Flask for backend',
                    'Pandas & NumPy for data processing',
                    'PyPSA for power system modeling',
                    'Scikit-learn for machine learning',
                    'Matplotlib & Plotly for visualization'
                ],
                'system_info': self._get_basic_system_status()
            }
        except Exception as e:
            logger.error(f"Error getting about page data: {e}")
            return {'error': str(e)}
    
    def _get_settings_page_data(self) -> Dict[str, Any]:
        """Get settings page data"""
        try:
            from flask import current_app
            
            settings_data = {
                'current_project': current_app.config.get('CURRENT_PROJECT'),
                'project_path': current_app.config.get('CURRENT_PROJECT_PATH'),
                'upload_folder': current_app.config.get('UPLOAD_FOLDER'),
                'max_file_size_mb': current_app.config.get('MAX_CONTENT_LENGTH', 0) / (1024 * 1024),
                'fy_start_month': current_app.config.get('FY_START_MONTH', 4),
                'debug_mode': current_app.debug,
                'features_available': len(self._get_essential_feature_flags())
            }
            
            # Add performance stats if available
            try:
                import psutil
                memory = psutil.virtual_memory()
                settings_data['system_health'] = {
                    'memory_percent': memory.percent,
                    'available_memory_gb': memory.available / (1024**3)
                }
            except ImportError:
                pass
            
            return settings_data
            
        except Exception as e:
            logger.error(f"Error getting settings data: {e}")
            return {'error': str(e)}
    
    def _get_basic_system_status(self) -> Dict[str, Any]:
        """Get basic system status without heavy operations"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return {
                'memory_percent': round(memory.percent, 1),
                'available_memory_gb': round(memory.available / (1024**3), 2),
                'cpu_count': psutil.cpu_count(),
                'disk_usage_percent': round(psutil.disk_usage('/').percent, 1)
            }
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return {'error': str(e)}
    
    def _get_project_info(self) -> Dict[str, Any]:
        """Get current project information"""
        from flask import current_app
        return {
            'name': current_app.config.get('CURRENT_PROJECT'),
            'path': current_app.config.get('CURRENT_PROJECT_PATH'),
            'has_project': bool(current_app.config.get('CURRENT_PROJECT_PATH'))
        }
    
    def _render_template(self, template: str, **kwargs):
        """Render template with error handling"""
        try:
            from flask import render_template
            return render_template(template, **kwargs)
        except Exception as e:
            logger.exception(f"Error rendering template {template}: {e}")
            return f"<h1>Template Error</h1><p>{str(e)}</p>", 500

# Create the optimized blueprint
core_blueprint = CoreBlueprint()
core_bp = core_blueprint.blueprint

# Export for Flask app registration
def register_core_bp(app):
    """Register the core blueprint with optimizations"""
    core_blueprint.register(app)