# blueprints/loadprofile_analysis_bp.py (OPTIMIZED)
"""
Optimized Load Profile Analysis Blueprint with ServiceBlueprint integration
error handling, response formatting, and performance optimization
"""
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from utils.base_blueprint import ServiceBlueprint, with_service

from utils.common_decorators import (
    require_project, validate_json_request, handle_exceptions,
    api_route, track_performance, cache_route, memory_efficient_operation
)
from utils.response_utils import success_json, error_json, validation_error_json
from utils.error_handlers import ValidationError, ProcessingError, ResourceNotFoundError
from utils.constants import UNIT_FACTORS, SUCCESS_MESSAGES, ERROR_MESSAGES
from services.loadprofile_analysis_service import LoadProfileAnalysisService

logger = logging.getLogger(__name__)

class LoadProfileAnalysisBlueprint(ServiceBlueprint):
    """
    Optimized Load Profile Analysis Blueprint with comprehensive analytics
    """
    
    def __init__(self):
        super().__init__(
            'loadprofile_analysis',
            __name__,
            service_class=LoadProfileAnalysisService,
            template_folder='../templates',
            static_folder='../static',
            url_prefix='/load_profile_analysis'
        )
    
    def register_routes(self):
        """Register optimized load profile analysis routes"""
        
        # Main dashboard route
        @self.blueprint.route('/')
        @require_project
        @handle_exceptions('loadprofile_analysis')
        @track_performance(threshold_ms=2000)
        def analysis_dashboard():
            return self._render_dashboard()
        
        # Profile Management APIs
        @self.blueprint.route('/api/available_profiles')
        @api_route(cache_ttl=300)
        def get_available_profiles_api():
            return self._get_available_profiles()
        
        @self.blueprint.route('/api/profile_data/<profile_id>')
        @api_route(cache_ttl=300)
        def get_profile_data_api(profile_id):
            return self._get_profile_data(profile_id)
        
        @self.blueprint.route('/api/profile_metadata/<profile_id>')
        @api_route(cache_ttl=600)
        def get_profile_metadata_api(profile_id):
            return self._get_profile_metadata(profile_id)
        
        # Analysis APIs
        @self.blueprint.route('/api/profile_analysis/<profile_id>/<analysis_type>')
        @api_route(cache_ttl=600)
        def get_profile_analysis_api(profile_id, analysis_type):
            return self._get_profile_analysis(profile_id, analysis_type)
        
        @self.blueprint.route('/api/comprehensive_analysis/<profile_id>')
        @api_route(cache_ttl=1200)
        def get_comprehensive_analysis_api(profile_id):
            return self._get_comprehensive_analysis(profile_id)
        
        @self.blueprint.route('/api/statistical_summary/<profile_id>')
        @api_route(cache_ttl=600)
        def get_statistical_summary_api(profile_id):
            return self._get_statistical_summary(profile_id)
        
        # Comparison APIs
        @self.blueprint.route('/api/compare_profiles', methods=['POST'])
        @api_route(
            required_json_fields=['profile_ids'],
            max_concurrent=2
        )
        def compare_profiles_api():
            return self._compare_profiles()
        
        @self.blueprint.route('/api/benchmark_profile/<profile_id>')
        @api_route(cache_ttl=600)
        def benchmark_profile_api(profile_id):
            return self._benchmark_profile(profile_id)
        
        # Temporal Analysis APIs
        @self.blueprint.route('/api/fiscal_years/<profile_id>')
        @api_route(cache_ttl=600)
        def get_profile_fiscal_years_api(profile_id):
            return self._get_profile_fiscal_years(profile_id)
        
        @self.blueprint.route('/api/seasonal_analysis/<profile_id>')
        @api_route(cache_ttl=600)
        def get_seasonal_analysis_api(profile_id):
            return self._get_seasonal_analysis(profile_id)
        
        @self.blueprint.route('/api/time_series_decomposition/<profile_id>')
        @api_route(cache_ttl=1200)
        def get_time_series_decomposition_api(profile_id):
            return self._get_time_series_decomposition(profile_id)
        
        # Quality Assessment APIs
        @self.blueprint.route('/api/profile_validation/<profile_id>')
        @api_route(cache_ttl=300)
        def validate_profile_api(profile_id):
            return self._validate_profile(profile_id)
        
        @self.blueprint.route('/api/data_quality_report/<profile_id>')
        @api_route(cache_ttl=600)
        def get_data_quality_report_api(profile_id):
            return self._get_data_quality_report(profile_id)
        
        # Export APIs
        @self.blueprint.route('/api/export_analysis/<profile_id>')
        @require_project
        @handle_exceptions('loadprofile_analysis')
        def export_analysis_api(profile_id):
            return self._export_analysis(profile_id)
        
        @self.blueprint.route('/api/export_comparison', methods=['POST'])
        @api_route(required_json_fields=['profile_ids'])
        def export_comparison_api():
            return self._export_comparison()
        
        # Batch Operations APIs
        @self.blueprint.route('/api/batch_analysis', methods=['POST'])
        @api_route(
            required_json_fields=['profile_ids', 'analysis_types'],
            max_concurrent=1
        )
        def batch_analysis_api():
            return self._batch_analysis()
        
        @self.blueprint.route('/api/generate_report', methods=['POST'])
        @api_route(
            required_json_fields=['profile_ids'],
            max_concurrent=1
        )
        def generate_report_api():
            return self._generate_comprehensive_report()
    
    def _render_dashboard(self):
        """Render the main analysis dashboard"""
        try:
            # Get cached dashboard data
            dashboard_data = self._get_cached_dashboard_data()
            
            if 'error' in dashboard_data:
                return self._render_error_page(dashboard_data['error'])
            
            return self._render_template('load_profile_analysis.html', **dashboard_data)
            
        except Exception as e:
            logger.exception(f"Error rendering dashboard: {e}")
            return self._render_error_page(str(e))
    
    @with_service
    def _get_available_profiles(self) -> Dict[str, Any]:
        """Get all available load profiles with metadata"""
        try:
            profiles = self.service.get_available_profiles()
            
            # Enhance with validation status
            for profile in profiles:
                try:
                    validation = self.service.quick_validate_profile(profile['profile_id'])
                    profile['validation_status'] = validation
                except Exception as validation_error:
                    profile['validation_status'] = {
                        'valid': False,
                        'error': str(validation_error)
                    }
            
            # Calculate summary statistics
            total_profiles = len(profiles)
            valid_profiles = sum(1 for p in profiles if p.get('validation_status', {}).get('valid', False))
            
            # Group by method
            method_groups = {}
            for profile in profiles:
                method = profile.get('method', 'Unknown')
                if method not in method_groups:
                    method_groups[method] = []
                method_groups[method].append(profile)
            
            return success_json(
                "Available profiles retrieved successfully",
                {
                    'profiles': profiles,
                    'summary': {
                        'total_profiles': total_profiles,
                        'valid_profiles': valid_profiles,
                        'invalid_profiles': total_profiles - valid_profiles,
                        'method_groups': {k: len(v) for k, v in method_groups.items()},
                        'total_size_mb': sum(p.get('file_info', {}).get('size_mb', 0) for p in profiles)
                    },
                    'method_groups': method_groups
                }
            )
            
        except Exception as e:
            logger.exception(f"Error getting available profiles: {e}")
            return error_json(f"Failed to get profiles: {str(e)}")
    
    @with_service
    def _get_profile_data(self, profile_id: str) -> Dict[str, Any]:
        """Get profile data with error handling and validation"""
        try:
            if not self._validate_profile_id(profile_id):
                raise ValidationError("Invalid profile ID format")
            
            # Extract filters from request
            filters = self._extract_data_filters()
            unit = filters.get('unit', 'kW')
            
            if unit not in UNIT_FACTORS:
                raise ValidationError(f"Invalid unit: {unit}")
            
            # Load and process data
            profile_data = self.service.get_profile_data(profile_id, filters)
            
            return success_json(
                f"Profile data retrieved for '{profile_id}'",
                profile_data
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except ResourceNotFoundError as e:
            return error_json(str(e), status_code=404)
        except ProcessingError as e:
            return error_json(f"Data processing failed: {str(e)}")
        except Exception as e:
            logger.exception(f"Error getting profile data: {e}")
            return error_json(f"Failed to get profile data: {str(e)}")
    
    @with_service
    def _get_profile_metadata(self, profile_id: str) -> Dict[str, Any]:
        """Get profile metadata and configuration"""
        try:
            if not self._validate_profile_id(profile_id):
                raise ValidationError("Invalid profile ID format")
            
            metadata = self.service.get_profile_metadata(profile_id)
            
            return success_json(
                f"Profile metadata retrieved for '{profile_id}'",
                metadata
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except ResourceNotFoundError as e:
            return error_json(str(e), status_code=404)
        except Exception as e:
            logger.exception(f"Error getting profile metadata: {e}")
            return error_json(f"Failed to get profile metadata: {str(e)}")
    
    @memory_efficient_operation
    def _get_profile_analysis(self, profile_id: str, analysis_type: str) -> Dict[str, Any]:
        """Get specific analysis for a profile"""
        try:
            if not self._validate_profile_id(profile_id):
                raise ValidationError("Invalid profile ID format")
            
            valid_analysis_types = [
                'overview', 'peak_analysis', 'weekday_weekend', 
                'seasonal', 'monthly', 'duration_curve', 'heatmap',
                'load_factor', 'demand_profile', 'variability'
            ]
            
            if analysis_type not in valid_analysis_types:
                raise ValidationError(f"Invalid analysis type. Must be one of: {valid_analysis_types}")
            
            # Extract analysis parameters
            params = self._extract_analysis_parameters()
            
            # Perform analysis
            analysis_result = self.service.perform_analysis(profile_id, analysis_type, params)
            
            return success_json(
                f"{analysis_type} analysis completed for '{profile_id}'",
                analysis_result
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except ResourceNotFoundError as e:
            return error_json(str(e), status_code=404)
        except ProcessingError as e:
            return error_json(f"Analysis failed: {str(e)}")
        except Exception as e:
            logger.exception(f"Error performing analysis: {e}")
            return error_json(f"Analysis failed: {str(e)}")
    
    @memory_efficient_operation
    def _get_comprehensive_analysis(self, profile_id: str) -> Dict[str, Any]:
        """Get comprehensive analysis covering all aspects"""
        try:
            if not self._validate_profile_id(profile_id):
                raise ValidationError("Invalid profile ID format")
            
            comprehensive_analysis = self.service.get_comprehensive_analysis(profile_id)
            
            return success_json(
                f"Comprehensive analysis completed for '{profile_id}'",
                comprehensive_analysis
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except ResourceNotFoundError as e:
            return error_json(str(e), status_code=404)
        except ProcessingError as e:
            return error_json(f"Comprehensive analysis failed: {str(e)}")
        except Exception as e:
            logger.exception(f"Error in comprehensive analysis: {e}")
            return error_json(f"Comprehensive analysis failed: {str(e)}")
    
    @with_service
    def _get_statistical_summary(self, profile_id: str) -> Dict[str, Any]:
        """Get statistical summary of profile"""
        try:
            if not self._validate_profile_id(profile_id):
                raise ValidationError("Invalid profile ID format")
            
            unit = request.args.get('unit', 'kW')
            if unit not in UNIT_FACTORS:
                raise ValidationError(f"Invalid unit: {unit}")
            
            statistical_summary = self.service.get_statistical_summary(profile_id, unit)
            
            return success_json(
                f"Statistical summary completed for '{profile_id}'",
                statistical_summary
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except ResourceNotFoundError as e:
            return error_json(str(e), status_code=404)
        except Exception as e:
            logger.exception(f"Error getting statistical summary: {e}")
            return error_json(f"Failed to get statistical summary: {str(e)}")
    
    @memory_efficient_operation
    def _compare_profiles(self) -> Dict[str, Any]:
        """Compare multiple load profiles"""
        try:
            from flask import request
            data = request.get_json()
            
            profile_ids = data.get('profile_ids', [])
            comparison_type = data.get('comparison_type', 'overview')
            
            # Validation
            if len(profile_ids) < 2:
                raise ValidationError("At least 2 profiles required for comparison")
            
            if len(profile_ids) > 5:
                raise ValidationError("Maximum 5 profiles can be compared")
            
            for profile_id in profile_ids:
                if not self._validate_profile_id(profile_id):
                    raise ValidationError(f"Invalid profile ID: {profile_id}")
            
            # Extract comparison parameters
            comparison_params = {
                'unit': data.get('unit', 'kW'),
                'filters': data.get('filters', {}),
                'metrics': data.get('metrics', ['basic', 'statistical']),
                'include_charts': data.get('include_charts', True)
            }
            
            # Perform comparison
            comparison_result = self.service.compare_profiles(
                profile_ids=profile_ids,
                comparison_type=comparison_type,
                parameters=comparison_params
            )
            
            return success_json(
                "Profile comparison completed successfully",
                comparison_result
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except ProcessingError as e:
            return error_json(f"Comparison failed: {str(e)}")
        except Exception as e:
            logger.exception(f"Error comparing profiles: {e}")
            return error_json(f"Comparison failed: {str(e)}")
    
    @with_service
    def _benchmark_profile(self, profile_id: str) -> Dict[str, Any]:
        """Benchmark profile against standard metrics"""
        try:
            if not self._validate_profile_id(profile_id):
                raise ValidationError("Invalid profile ID format")
            
            benchmark_type = request.args.get('type', 'industry_standard')
            unit = request.args.get('unit', 'kW')
            
            benchmark_result = self.service.benchmark_profile(profile_id, benchmark_type, unit)
            
            return success_json(
                f"Profile benchmarking completed for '{profile_id}'",
                benchmark_result
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except ResourceNotFoundError as e:
            return error_json(str(e), status_code=404)
        except Exception as e:
            logger.exception(f"Error benchmarking profile: {e}")
            return error_json(f"Benchmarking failed: {str(e)}")
    
    @with_service
    def _get_profile_fiscal_years(self, profile_id: str) -> Dict[str, Any]:
        """Get available fiscal years for profile"""
        try:
            if not self._validate_profile_id(profile_id):
                raise ValidationError("Invalid profile ID format")
            
            fiscal_years = self.service.get_profile_fiscal_years(profile_id)
            
            return success_json(
                f"Fiscal years retrieved for '{profile_id}'",
                {
                    'fiscal_years': fiscal_years,
                    'total_years': len(fiscal_years),
                    'year_range': {
                        'start': min(fiscal_years) if fiscal_years else None,
                        'end': max(fiscal_years) if fiscal_years else None
                    }
                }
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except ResourceNotFoundError as e:
            return error_json(str(e), status_code=404)
        except Exception as e:
            logger.exception(f"Error getting fiscal years: {e}")
            return error_json(f"Failed to get fiscal years: {str(e)}")
    
    @memory_efficient_operation
    def _get_seasonal_analysis(self, profile_id: str) -> Dict[str, Any]:
        """Get seasonal analysis for profile"""
        try:
            if not self._validate_profile_id(profile_id):
                raise ValidationError("Invalid profile ID format")
            
            analysis_params = self._extract_analysis_parameters()
            seasonal_analysis = self.service.get_seasonal_analysis(profile_id, analysis_params)
            
            return success_json(
                f"Seasonal analysis completed for '{profile_id}'",
                seasonal_analysis
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except ResourceNotFoundError as e:
            return error_json(str(e), status_code=404)
        except Exception as e:
            logger.exception(f"Error in seasonal analysis: {e}")
            return error_json(f"Seasonal analysis failed: {str(e)}")
    
    @memory_efficient_operation
    def _get_time_series_decomposition(self, profile_id: str) -> Dict[str, Any]:
        """Get time series decomposition analysis"""
        try:
            if not self._validate_profile_id(profile_id):
                raise ValidationError("Invalid profile ID format")
            
            decomposition_params = {
                'method': request.args.get('method', 'STL'),
                'period': request.args.get('period', 'auto'),
                'seasonal': request.args.get('seasonal', 'additive')
            }
            
            decomposition_result = self.service.get_time_series_decomposition(
                profile_id, decomposition_params
            )
            
            return success_json(
                f"Time series decomposition completed for '{profile_id}'",
                decomposition_result
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except ResourceNotFoundError as e:
            return error_json(str(e), status_code=404)
        except Exception as e:
            logger.exception(f"Error in time series decomposition: {e}")
            return error_json(f"Time series decomposition failed: {str(e)}")
    
    @with_service
    def _validate_profile(self, profile_id: str) -> Dict[str, Any]:
        """Validate profile data quality"""
        try:
            if not self._validate_profile_id(profile_id):
                raise ValidationError("Invalid profile ID format")
            
            validation_result = self.service.validate_profile_comprehensive(profile_id)
            
            return success_json(
                f"Profile validation completed for '{profile_id}'",
                validation_result
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except ResourceNotFoundError as e:
            return error_json(str(e), status_code=404)
        except Exception as e:
            logger.exception(f"Error validating profile: {e}")
            return error_json(f"Profile validation failed: {str(e)}")
    
    @with_service
    def _get_data_quality_report(self, profile_id: str) -> Dict[str, Any]:
        """Get comprehensive data quality report"""
        try:
            if not self._validate_profile_id(profile_id):
                raise ValidationError("Invalid profile ID format")
            
            quality_report = self.service.generate_data_quality_report(profile_id)
            
            return success_json(
                f"Data quality report generated for '{profile_id}'",
                quality_report
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except ResourceNotFoundError as e:
            return error_json(str(e), status_code=404)
        except Exception as e:
            logger.exception(f"Error generating quality report: {e}")
            return error_json(f"Quality report generation failed: {str(e)}")
    
    @with_service
    def _export_analysis(self, profile_id: str):
        """Export analysis results"""
        try:
            if not self._validate_profile_id(profile_id):
                raise ValidationError("Invalid profile ID format")
            
            export_format = request.args.get('format', 'csv').lower()
            analysis_types = request.args.getlist('analysis_types')
            
            if export_format not in ['csv', 'xlsx', 'json']:
                raise ValidationError("Invalid export format. Must be csv, xlsx, or json")
            
            return self.service.export_analysis_results(
                profile_id=profile_id,
                export_format=export_format,
                analysis_types=analysis_types
            )
            
        except ValidationError as e:
            return error_json(str(e), status_code=400)
        except ResourceNotFoundError as e:
            return error_json(str(e), status_code=404)
        except Exception as e:
            logger.exception(f"Error exporting analysis: {e}")
            return error_json(f"Export failed: {str(e)}")
    
    @with_service
    def _export_comparison(self):
        """Export comparison results"""
        try:
            from flask import request
            data = request.get_json()
            
            profile_ids = data.get('profile_ids', [])
            export_format = data.get('format', 'xlsx')
            
            if len(profile_ids) < 2:
                raise ValidationError("At least 2 profiles required for comparison export")
            
            return self.service.export_comparison_results(profile_ids, export_format)
            
        except ValidationError as e:
            return error_json(str(e), status_code=400)
        except Exception as e:
            logger.exception(f"Error exporting comparison: {e}")
            return error_json(f"Comparison export failed: {str(e)}")
    
    @memory_efficient_operation
    def _batch_analysis(self) -> Dict[str, Any]:
        """Perform batch analysis on multiple profiles"""
        try:
            from flask import request
            data = request.get_json()
            
            profile_ids = data.get('profile_ids', [])
            analysis_types = data.get('analysis_types', [])
            
            if len(profile_ids) > 10:
                raise ValidationError("Maximum 10 profiles can be processed in batch")
            
            batch_result = self.service.perform_batch_analysis(profile_ids, analysis_types)
            
            return success_json(
                "Batch analysis completed successfully",
                batch_result
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except Exception as e:
            logger.exception(f"Error in batch analysis: {e}")
            return error_json(f"Batch analysis failed: {str(e)}")
    
    @memory_efficient_operation
    def _generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive analysis report"""
        try:
            from flask import request
            data = request.get_json()
            
            profile_ids = data.get('profile_ids', [])
            report_type = data.get('report_type', 'comprehensive')
            
            report_result = self.service.generate_comprehensive_report(profile_ids, report_type)
            
            return success_json(
                "Comprehensive report generated successfully",
                report_result
            )
            
        except ValidationError as e:
            return validation_error_json(str(e))
        except Exception as e:
            logger.exception(f"Error generating report: {e}")
            return error_json(f"Report generation failed: {str(e)}")
    
    # Helper methods
    def _validate_profile_id(self, profile_id: str) -> bool:
        """Validate profile ID format"""
        if not profile_id or '..' in profile_id or '/' in profile_id:
            return False
        return True
    
    def _extract_data_filters(self) -> Dict[str, Any]:
        """Extract data filters from request parameters"""
        from flask import request
        
        filters = {}
        
        # Optional filters
        if request.args.get('year'):
            filters['year'] = request.args.get('year')
        if request.args.get('month'):
            filters['month'] = request.args.get('month')
        if request.args.get('season'):
            filters['season'] = request.args.get('season')
        if request.args.get('day_type'):
            filters['day_type'] = request.args.get('day_type')
        if request.args.get('start_date'):
            filters['start_date'] = request.args.get('start_date')
        if request.args.get('end_date'):
            filters['end_date'] = request.args.get('end_date')
        
        filters['unit'] = request.args.get('unit', 'kW')
        
        return filters
    
    def _extract_analysis_parameters(self) -> Dict[str, Any]:
        """Extract analysis parameters from request"""
        from flask import request
        
        return {
            'unit': request.args.get('unit', 'kW'),
            'aggregation': request.args.get('aggregation', 'hourly'),
            'include_charts': request.args.get('include_charts', 'true').lower() == 'true',
            'detailed': request.args.get('detailed', 'false').lower() == 'true',
            'filters': self._extract_data_filters()
        }
    
    @cache_route(ttl=300, key_func=lambda: "loadprofile_analysis_dashboard")
    def _get_cached_dashboard_data(self) -> Dict[str, Any]:
        """Get cached dashboard data"""
        try:
            if not self.service:
                return {'error': 'Service not available'}
            
            return self.service.get_dashboard_data()
            
        except Exception as e:
            logger.error(f"Error getting dashboard data: {e}")
            return {'error': str(e)}
    
    def _render_template(self, template: str, **kwargs):
        """Render template with error handling"""
        try:
            from flask import render_template
            return render_template(template, **kwargs)
        except Exception as e:
            logger.exception(f"Error rendering template {template}: {e}")
            return self._render_error_page(str(e))
    
    def _render_error_page(self, error_message: str):
        """Render error page"""
        try:
            from flask import render_template
            return render_template('errors/loadprofile_analysis_error.html', error=error_message), 500
        except Exception:
            return f"<h1>Load Profile Analysis Error</h1><p>{error_message}</p>", 500

# Create the optimized blueprint
loadprofile_analysis_blueprint = LoadProfileAnalysisBlueprint()
loadprofile_analysis_bp = loadprofile_analysis_blueprint.blueprint

# Export for Flask app registration
def register_loadprofile_analysis_bp(app):
    """Register the load profile analysis blueprint with optimizations"""
    loadprofile_analysis_blueprint.register(app)