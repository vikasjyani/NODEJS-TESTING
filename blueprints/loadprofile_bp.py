# blueprints/loadprofile_bp.py (FIXED STL ROUTES)
"""
Optimized Load Profile Blueprint with Service Layer Integration
Fixed STL-related routes and historical data summary
"""
import os
import logging
from datetime import datetime
from flask import Blueprint, jsonify, render_template, request, send_file, g
from utils.base_blueprint import ServiceBlueprint, with_service
from utils.common_decorators import (
    require_project, validate_json_request, validate_file_upload,
    handle_exceptions, api_route, track_performance, cache_route
)
from utils.response_utils import error_response, success_json, error_json, success_response, validation_error_json
from utils.constants import ALLOWED_EXTENSIONS, UNIT_FACTORS
from services.loadprofile_service import LoadProfileService

logger = logging.getLogger(__name__)

class LoadProfileBlueprint(ServiceBlueprint):
    """Optimized Load Profile Blueprint with comprehensive caching and error handling"""
    
    def __init__(self):
        super().__init__(
            'loadprofile',
            __name__,
            service_class=LoadProfileService,
            template_folder='../templates',
            static_folder='../static',
            url_prefix='/load_profile'
        )
    
    def register_routes(self):
        """Register optimized load profile routes"""
        
        # Main page route
        @self.blueprint.route('/')
        @require_project
        @handle_exceptions('loadprofile')
        @track_performance()
        def generate_profile():
            return self._render_main_page()
        
        # Template and scenario info routes (cached)
        @self.blueprint.route('/api/template_info')
        @api_route(cache_ttl=600)
        def get_template_info():
            return self._get_template_info()
        
        @self.blueprint.route('/api/available_base_years')
        @api_route(cache_ttl=600)
        def get_available_base_years():
            return self._get_available_base_years()
        
        @self.blueprint.route('/api/scenario_info/<scenario_name>')
        @api_route(cache_ttl=600)
        def get_scenario_info(scenario_name):
            return self._get_scenario_info(scenario_name)
        
        # Profile generation routes
        @self.blueprint.route('/api/preview_base_profiles', methods=['POST'])
        @api_route(required_json_fields=['base_year'])
        def preview_base_profiles():
            return self._preview_base_profiles()
        
        @self.blueprint.route('/api/generate_base_profile', methods=['POST'])
        @api_route(
            required_json_fields=['base_year', 'start_fy', 'end_fy', 'demand_source'],
            max_concurrent=2
        )
        def generate_base_profile():
            return self._generate_base_profile()
        
        @self.blueprint.route('/api/generate_stl_profile', methods=['POST'])
        @api_route(
            required_json_fields=['start_fy', 'end_fy', 'demand_source'],
            max_concurrent=2
        )
        def generate_stl_profile():
            return self._generate_stl_profile()
        
        # Profile management routes
        @self.blueprint.route('/api/saved_profiles')
        @api_route(cache_ttl=600)
        def get_saved_profiles():
            return self._get_saved_profiles()
        
        @self.blueprint.route('/api/profile_data/<profile_id>')
        @api_route(cache_ttl=600)
        def get_profile_data_route(profile_id):
            return self._get_profile_data(profile_id)
        
        @self.blueprint.route('/api/download_profile/<profile_id>')
        @require_project
        @handle_exceptions('loadprofile')
        def download_profile(profile_id):
            return self._download_profile(profile_id)
        
        @self.blueprint.route('/api/delete_profile/<profile_id>', methods=['DELETE'])
        @api_route()
        def delete_profile(profile_id):
            return self._delete_profile(profile_id)
        
        # File upload route
        @self.blueprint.route('/api/upload_template', methods=['POST'])
        @require_project
        @validate_file_upload({'.xlsx'}, 50)
        @handle_exceptions('loadprofile')
        def upload_template():
            return self._upload_template()
        
        # Analysis routes
        @self.blueprint.route('/api/profile_analysis/<profile_id>')
        @api_route(cache_ttl=600)
        def get_profile_analysis(profile_id):
            return self._get_profile_analysis(profile_id)
        
        @self.blueprint.route('/api/compare_profiles', methods=['POST'])
        @api_route(required_json_fields=['profile_ids'])
        def compare_profiles():
            return self._compare_profiles()
        
        # FIXED STL-related routes
        @self.blueprint.route('/api/historical_summary')
        @api_route(cache_ttl=600)
        def get_historical_summary():
            """Get summary of all historical data"""
            return self._get_historical_summary()
        
        @self.blueprint.route('/api/base_year_info/<int:year>')
        @api_route(cache_ttl=600)
        def get_base_year_info(year):
            """Get detailed information about a specific base year"""
            return self._get_base_year_info(year)
    
    def _render_main_page(self):
        """Render main load profile page with cached data"""
        try:
            # Get cached page data
            page_data = self._get_cached_page_data()
            
            if 'error' in page_data:
                return self._render_error_page(page_data['error'])
            
            return render_template('load_profile_generation.html', **page_data)
            
        except Exception as e:
            logger.exception(f"Error rendering load profile page: {e}")
            return self._render_error_page(str(e))
    
    @with_service
    def _get_template_info(self):
        """Get comprehensive template information with caching"""
        try:
            template_info = self.service.get_template_analysis()
            
            return success_json(
                "Template information retrieved successfully",
                template_info
            )
        except FileNotFoundError:
            return error_json(
                "Template file not found. Please upload load_curve_template.xlsx",
                status_code=404
            )
        except Exception as e:
            logger.exception(f"Error getting template info: {e}")
            return error_json(f"Failed to load template: {str(e)}")
    
    @with_service
    def _get_available_base_years(self):
        """Get available base years with caching"""
        try:
            base_years_info = self.service.get_available_base_years()
            
            return success_json(
                "Available base years retrieved",
                base_years_info
            )
        except Exception as e:
            logger.exception(f"Error getting base years: {e}")
            return error_json(f"Failed to get base years: {str(e)}")
    
    @with_service
    def _get_scenario_info(self, scenario_name: str):
        """Get scenario information with validation"""
        try:
            if not scenario_name or '..' in scenario_name:
                return validation_error_json("Invalid scenario name")
            
            scenario_info = self.service.get_scenario_analysis(scenario_name)
            
            return success_json(
                "Scenario information retrieved",
                scenario_info
            )
        except FileNotFoundError:
            return error_json("Scenario file not found", status_code=404)
        except Exception as e:
            logger.exception(f"Error getting scenario info: {e}")
            return error_json(f"Failed to get scenario info: {str(e)}")
    
    @with_service
    def _preview_base_profiles(self):
        """Preview base profiles with analysis"""
        try:
            data = request.get_json()
            base_year = data.get('base_year')
            
            if not base_year:
                return validation_error_json("Base year is required")
            
            preview_data = self.service.generate_base_profile_preview(int(base_year))
            
            return success_json(
                "Base profile preview generated",
                preview_data
            )
        except ValueError as e:
            return validation_error_json(str(e))
        except Exception as e:
            logger.exception(f"Error previewing base profiles: {e}")
            return error_json(f"Failed to generate preview: {str(e)}")
    
    @with_service
    def _generate_base_profile(self):
        """Generate base profile with comprehensive validation"""
        try:
            data = request.get_json()
            
            # validation
            validation_result = self.service.validate_generation_request(data, 'base_profile')
            if not validation_result['valid']:
                return validation_error_json(
                    "Configuration validation failed",
                    errors=validation_result['errors']
                )
            
            # Generate profile
            generation_result = self.service.generate_base_profile(data)
            
            if generation_result['success']:
                # Invalidate cache
                self._invalidate_profile_cache()
                
                return success_json(
                    "Base profile generated and saved successfully",
                    generation_result['data']
                )
            else:
                return error_json(generation_result['error'])
                
        except Exception as e:
            logger.exception(f"Error generating base profile: {e}")
            return error_json(f"Failed to generate profile: {str(e)}")
    
    @with_service
    def _generate_stl_profile(self):
        """Generate STL profile with advanced configuration"""
        try:
            data = request.get_json()
            
            # validation
            validation_result = self.service.validate_generation_request(data, 'stl_profile')
            if not validation_result['valid']:
                return validation_error_json(
                    "Configuration validation failed",
                    errors=validation_result['errors']
                )
            
            # Generate profile
            generation_result = self.service.generate_stl_profile(data)
            
            if generation_result['success']:
                # Invalidate cache
                self._invalidate_profile_cache()
                
                return success_json(
                    "STL profile generated and saved successfully",
                    generation_result['data']
                )
            else:
                return error_json(generation_result['error'])
                
        except Exception as e:
            logger.exception(f"Error generating STL profile: {e}")
            return error_json(f"Failed to generate profile: {str(e)}")
    
    @with_service
    def _get_saved_profiles(self):
        """Get saved profiles with metadata"""
        try:
            profiles_data = self.service.get_saved_profiles_with_metadata()
            
            return success_json(
                "Saved profiles retrieved",
                profiles_data
            )
        except Exception as e:
            logger.exception(f"Error getting saved profiles: {e}")
            return error_json(f"Failed to get profiles: {str(e)}")
    
    @with_service
    def _get_profile_data(self, profile_id: str):
        """Get detailed profile data with analysis"""
        try:
            if not profile_id or '..' in profile_id:
                return validation_error_json("Invalid profile ID")
            
            profile_data = self.service.get_profile_detailed_data(profile_id)
            
            return success_json(
                "Profile data retrieved successfully",
                profile_data
            )
        except FileNotFoundError:
            return error_json("Profile not found", status_code=404)
        except Exception as e:
            logger.exception(f"Error getting profile data: {e}")
            return error_json(f"Failed to get profile data: {str(e)}")
    
    @with_service
    def _download_profile(self, profile_id: str):
        """Download profile with security validation"""
        try:
            if not profile_id or '..' in profile_id:
                return error_json("Invalid profile ID", status_code=400)
            
            file_path = self.service.get_profile_file_path(profile_id)
            
            if not file_path or not os.path.exists(file_path):
                return error_json("Profile not found", status_code=404)
            
            return send_file(
                file_path,
                as_attachment=True,
                download_name=f"{profile_id}.csv",
                mimetype='text/csv'
            )
        except Exception as e:
            logger.exception(f"Error downloading profile: {e}")
            return error_json(f"Download failed: {str(e)}")
    
    @with_service
    def _delete_profile(self, profile_id: str):
        """Delete profile with validation"""
        try:
            if not profile_id or '..' in profile_id:
                return validation_error_json("Invalid profile ID")
            
            deletion_result = self.service.delete_profile(profile_id)
            
            if deletion_result['success']:
                # Invalidate cache
                self._invalidate_profile_cache()
                
                return success_json(f"Profile {profile_id} deleted successfully")
            else:
                return error_json(deletion_result['error'])
                
        except Exception as e:
            logger.exception(f"Error deleting profile: {e}")
            return error_json(f"Failed to delete profile: {str(e)}")
    
    @with_service
    def _upload_template(self):
        """Upload template with comprehensive validation"""
        try:
            file = request.files['file']
            
            if not file or file.filename == '':
                return validation_error_json("No file selected")
            
            upload_result = self.service.upload_and_validate_template(file)
            
            if upload_result['success']:
                # Invalidate template cache
                self._invalidate_template_cache()
                
                return success_json(
                    "Template uploaded and validated successfully",
                    upload_result['data']
                )
            else:
                return validation_error_json(upload_result['error'])
                
        except Exception as e:
            logger.exception(f"Error uploading template: {e}")
            return error_json(f"Failed to upload template: {str(e)}")
    
    @with_service
    def _get_profile_analysis(self, profile_id: str):
        """Get comprehensive profile analysis"""
        try:
            if not profile_id or '..' in profile_id:
                return validation_error_json("Invalid profile ID")
            
            analysis_data = self.service.analyze_profile(profile_id)
            
            return success_json(
                "Profile analysis completed",
                analysis_data
            )
        except FileNotFoundError:
            return error_json("Profile not found", status_code=404)
        except Exception as e:
            logger.exception(f"Error analyzing profile: {e}")
            return error_json(f"Analysis failed: {str(e)}")
    
    @with_service
    def _compare_profiles(self):
        """Compare multiple profiles"""
        try:
            data = request.get_json()
            profile_ids = data.get('profile_ids', [])
            
            if len(profile_ids) < 2:
                return validation_error_json("At least 2 profiles required for comparison")
            
            if len(profile_ids) > 5:
                return validation_error_json("Maximum 5 profiles can be compared")
            
            comparison_result = self.service.compare_profiles(profile_ids)
            
            return success_json(
                "Profile comparison completed",
                comparison_result
            )
        except Exception as e:
            logger.exception(f"Error comparing profiles: {e}")
            return error_json(f"Comparison failed: {str(e)}")
    
    # FIXED STL-related methods
    @with_service
    def _get_historical_summary(self):
        """Get summary of all historical data for STL method"""
        try:
            summary = self.service.get_historical_data_summary()
            
            return success_json(
                "Historical summary retrieved successfully",
                summary
            )
        except Exception as e:
            logger.exception(f"Error getting historical summary: {e}")
            return error_json(f"Failed to get historical summary: {str(e)}")
    
    @with_service
    def _get_base_year_info(self, year: int):
        """Get detailed information about a specific base year"""
        try:
            base_year_info = self.service.get_base_year_detailed_info(year)
            
            return success_json(
                "Base year information retrieved successfully",
                base_year_info
            )
        except ValueError as e:
            return error_json(f"Invalid year: {str(e)}", status_code=404)
        except Exception as e:
            logger.exception(f"Error getting base year info for {year}: {e}")
            return error_json(f"Failed to get base year info: {str(e)}")
    
    # Helper methods
    @cache_route(ttl=600, key_func=lambda: "loadprofile_page_data")
    def _get_cached_page_data(self) -> dict:
        """Get cached page data for main template"""
        try:
            if not self.service:
                return {'error': 'Service not available'}
            
            # Get all necessary data for page rendering
            page_data = self.service.get_main_page_data()
            
            # Add context data
            page_data.update({
                'unit_factors': UNIT_FACTORS,
                'available_methods': ['base_profile_scaling', 'stl_decomposition'],
                'available_frequencies': ['hourly', '15min', '30min', 'daily']
            })
            
            return page_data
            
        except Exception as e:
            logger.error(f"Error getting cached page data: {e}")
            return {'error': str(e)}
    
    def _render_error_page(self, error_message: str):
        """Render error page with consistent styling"""
        from flask import render_template
        return render_template('errors/loadprofile_error.html', 
                             error=error_message), 500
    
    def _invalidate_profile_cache(self):
        """Invalidate profile-related caches"""
        # Implementation would clear relevant cache entries
        pass
    
    def _invalidate_template_cache(self):
        """Invalidate template-related caches"""
        # Implementation would clear relevant cache entries
        pass


# Create the optimized blueprint
loadprofile_blueprint = LoadProfileBlueprint()
loadprofile_bp = loadprofile_blueprint.blueprint

# Export for Flask app registration
def register_loadprofile_bp(app):
    """Register the load profile blueprint with optimizations"""
    loadprofile_blueprint.register(app)