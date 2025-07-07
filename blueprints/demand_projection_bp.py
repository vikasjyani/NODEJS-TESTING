# blueprints/demand_projection_bp.py
"""
 Demand Projection Blueprint - Production Ready with Complete Configuration Support
Clean, organized routes with real data processing via service layer
"""
import os
import threading
import uuid
import time
import logging
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app

from utils.base_blueprint import ServiceBlueprint, with_service
from utils.common_decorators import (
    require_project, validate_json_request, handle_exceptions, 
    api_route, track_performance, memory_efficient_operation
)
from utils.response_utils import success_json, error_json, validation_error_json
from utils.constants import JOB_STATUS, FORECAST_MODELS, ERROR_MESSAGES
from services.demand_projection_service import (
    DemandProjectionService, ForecastJobConfig, job_manager
)

logger = logging.getLogger(__name__)

class DemandProjectionBlueprint(ServiceBlueprint):
    """
    Demand Projection Blueprint with complete configuration management
    """
    
    def __init__(self):
        super().__init__(
            'demand_projection',
            __name__,
            service_class=DemandProjectionService,
            template_folder='../templates',
            static_folder='../static'
        )
    
    def register_routes(self):
        """Register all routes for this blueprint"""
        
        # Main page route
        @self.blueprint.route('/')
        @require_project
        @handle_exceptions('demand_projection')
        @track_performance()
        @memory_efficient_operation
        def demand_projection_route():
            return self._render_main_page()
        
        # API Routes with optimized decorators
        @self.blueprint.route('/api/independent_variables/<sector>')
        @api_route(cache_ttl=300)
        def get_independent_variables_api(sector):
            return self._get_independent_variables(sector)
        
        @self.blueprint.route('/api/correlation_data/<sector>')
        @api_route(cache_ttl=300)
        def get_correlation_data_api(sector):
            return self._get_correlation_data(sector)
        
        @self.blueprint.route('/api/chart_data/<sector>')
        @api_route(cache_ttl=300)
        def get_chart_data_api(sector):
            return self._get_chart_data(sector)
        
        @self.blueprint.route('/api/run_forecast', methods=['POST'])
        @api_route(
            required_json_fields=['scenarioName', 'targetYear', 'sectorConfigs'],
            max_concurrent=3
        )
        def run_forecast_api():
            return self._run_forecast()
        
        @self.blueprint.route('/api/forecast_status/<job_id>')
        @api_route(cache_ttl=5)  # Very short cache for status
        def get_forecast_status_api(job_id):
            return self._get_forecast_status(job_id)
        
        @self.blueprint.route('/api/cancel_forecast/<job_id>', methods=['POST'])
        @api_route()
        def cancel_forecast_api(job_id):
            return self._cancel_forecast(job_id)
        
        @self.blueprint.route('/api/jobs/summary')
        @api_route(cache_ttl=30)
        def get_jobs_summary_api():
            return self._get_jobs_summary()
        
        # utility routes
        @self.blueprint.route('/api/validate_scenario_name', methods=['POST'])
        @api_route(required_json_fields=['scenarioName'])
        def validate_scenario_name_api():
            return self._validate_scenario_name()
        
        @self.blueprint.route('/api/data_summary')
        @api_route(cache_ttl=120)
        def get_data_summary_api():
            return self._get_data_summary()
        
        # New configuration management routes
        @self.blueprint.route('/api/configuration/<scenario_name>')
        @api_route(cache_ttl=60)
        def get_scenario_configuration_api(scenario_name):
            return self._get_scenario_configuration(scenario_name)
        
        @self.blueprint.route('/api/configuration/validate', methods=['POST'])
        @api_route(required_json_fields=['scenarioName', 'targetYear', 'sectorConfigs'])
        def validate_configuration_api():
            return self._validate_complete_configuration()
    
    @memory_efficient_operation
    def _render_main_page(self):
        """Render the main demand projection page with real data"""
        try:
            # Get comprehensive input data summary
            data_summary = self.service.get_input_data_summary()
            
            if 'error' in data_summary:
                flash(f'Error loading input data: {data_summary["error"]}', 'danger')
                return redirect(url_for('core.home'))
            
            if not data_summary['data_available']:
                flash('No input data available. Please upload input_demand_file.xlsx', 'warning')
                return redirect(url_for('core.home'))
            
            # Prepare sector tables for display
            sector_tables = self._prepare_sector_tables(data_summary['sectors'])
            
            # Prepare aggregated table if available
            aggregated_table = self._prepare_aggregated_table()
            
            # Get job statistics
            job_stats = job_manager.get_jobs_summary()
            
            # Prepare chart data structure
            chart_data = {
                'sectors': data_summary['sectors'],
                'has_data': data_summary['data_available'],
                'missing_sectors': data_summary['missing_sectors'],
                'data_quality': self._assess_overall_data_quality(data_summary)
            }
            
            # context with configuration support
            context = {
                'sectors': data_summary['sectors'],
                'missing_sectors': data_summary['missing_sectors'],
                'param_dict': data_summary['parameters'],
                'sector_tables': sector_tables,
                'aggregated_table': aggregated_table,
                'job_statistics': job_stats,
                'available_models': FORECAST_MODELS,
                'chart_data': chart_data,
                'data_summary': data_summary,
                'page_title': 'Demand Projection & Forecasting',
                'file_info': data_summary.get('file_validation', {}),
                # configuration metadata
                'configuration_metadata': {
                    'auto_save_enabled': True,
                    'tracking_enabled': True,
                    'version': '2.0.0',
                    'features': ['complete_config_saving', 'validation', 'progress_tracking']
                }
            }
            
            logger.info(f"Successfully prepared demand projection page with {len(data_summary['sectors'])} sectors")
            return render_template('demand_projection.html', **context)
            
        except Exception as e:
            logger.exception(f"Error rendering main page: {e}")
            flash(f'Error loading page: {str(e)}', 'danger')
            return redirect(url_for('core.home'))
    
    def _prepare_sector_tables(self, sectors):
        """Prepare sector tables for display with error handling"""
        sector_tables = {}
        
        for sector in sectors:
            try:
                sector_data = self.service.get_sector_data(sector)
                df_data = sector_data['data']
                
                if df_data:
                    import pandas as pd
                    df = pd.DataFrame(df_data)
                    
                    # Clean data for display
                    display_df = df.copy()
                    for col in display_df.columns:
                        if display_df[col].dtype == 'object':
                            display_df[col] = display_df[col].astype(str).replace('nan', 'N/A')
                        else:
                            display_df[col] = display_df[col].fillna('N/A')
                    
                    # Limit rows for display performance
                    if len(display_df) > 100:
                        display_df = display_df.tail(50)  # Show last 50 rows
                        table_note = f"<p class='text-info small'>Showing last 50 rows of {len(df)} total rows</p>"
                    else:
                        table_note = ""
                    
                    table_html = display_df.to_html(
                        classes='table table-striped table-hover table-sm',
                        index=False,
                        escape=False,
                        table_id=f'sector-table-{sector.replace(" ", "-").lower()}'
                    )
                    
                    sector_tables[sector] = table_note + table_html
                else:
                    sector_tables[sector] = "<p class='text-info'>No data available</p>"
                    
            except Exception as table_error:
                logger.warning(f"Error creating table for sector {sector}: {table_error}")
                sector_tables[sector] = f"<p class='text-warning'>Error displaying {sector}: {str(table_error)}</p>"
        
        return sector_tables
    
    def _prepare_aggregated_table(self):
        """Prepare aggregated data table"""
        try:
            aggregated_data = self.service.get_chart_data('aggregated')
            
            if aggregated_data.get('type') == 'aggregated' and aggregated_data.get('years'):
                # Create DataFrame from chart data
                import pandas as pd
                
                table_data = {'Year': aggregated_data['years']}
                
                for dataset in aggregated_data.get('datasets', []):
                    table_data[dataset['label']] = dataset['data']
                
                if aggregated_data.get('total_consumption'):
                    table_data['Total'] = aggregated_data['total_consumption']
                
                df = pd.DataFrame(table_data)
                
                # Format numbers and limit rows for display
                for col in df.columns:
                    if col != 'Year':
                        df[col] = df[col].apply(lambda x: f"{x:,.1f}" if isinstance(x, (int, float)) and x != 0 else "0")
                
                if len(df) > 50:
                    df = df.tail(25)  # Show last 25 years
                    table_note = f"<p class='text-info small'>Showing last 25 years of {len(table_data['Year'])} total years</p>"
                else:
                    table_note = ""
                
                table_html = df.to_html(
                    classes='table table-striped table-hover table-sm',
                    index=False,
                    escape=False,
                    table_id='aggregated-table'
                )
                
                return table_note + table_html
            else:
                return "<p class='text-info'>No aggregated data available</p>"
                
        except Exception as agg_error:
            logger.warning(f"Error creating aggregated table: {agg_error}")
            return "<p class='text-warning'>Error displaying aggregated data</p>"
    
    def _assess_overall_data_quality(self, data_summary):
        """Assess overall data quality for the project"""
        try:
            total_sectors = data_summary.get('total_sectors', 0)
            missing_count = data_summary.get('missing_count', 0)
            
            if total_sectors == 0:
                return {'quality': 'no_data', 'score': 0, 'description': 'No data available'}
            
            completeness_score = ((total_sectors - missing_count) / total_sectors) * 100
            
            if completeness_score >= 90:
                quality = 'excellent'
                description = 'All sectors have data available'
            elif completeness_score >= 75:
                quality = 'good'
                description = 'Most sectors have data available'
            elif completeness_score >= 50:
                quality = 'fair'
                description = 'Some sectors missing data'
            else:
                quality = 'poor'
                description = 'Many sectors missing data'
            
            return {
                'quality': quality,
                'score': completeness_score,
                'description': description,
                'total_sectors': total_sectors,
                'available_sectors': total_sectors - missing_count,
                'missing_sectors': missing_count
            }
            
        except Exception as e:
            logger.warning(f"Error assessing data quality: {e}")
            return {'quality': 'unknown', 'score': 0, 'description': 'Unable to assess data quality'}
    
    @with_service
    def _get_independent_variables(self, sector: str):
        """Get independent variables for a sector with analysis"""
        try:
            if not sector or not isinstance(sector, str):
                return validation_error_json("Invalid sector parameter")
            
            result = self.service.get_independent_variables(sector)
            
            return success_json(
                f"Retrieved {result['suitable_count']} suitable variables for sector '{sector}'",
                result
            )
            
        except ValueError as e:
            return error_json(str(e), status_code=404)
        except Exception as e:
            logger.exception(f"Error getting independent variables for {sector}: {e}")
            return error_json(f"Failed to get variables: {str(e)}")
    
    @with_service
    def _get_correlation_data(self, sector: str):
        """Get correlation data for a sector"""
        try:
            if not sector:
                return validation_error_json("Sector parameter is required")
            
            result = self.service.get_correlation_data(sector)
            
            if 'error' in result:
                return error_json(result['error'], status_code=404)
            
            return success_json(
                f"Correlation analysis completed for {result['display_name']}",
                result
            )
            
        except ValueError as e:
            return error_json(str(e), status_code=404)
        except Exception as e:
            logger.exception(f"Error getting correlation data for {sector}: {e}")
            return error_json(f"Failed to get correlations: {str(e)}")
    
    @with_service
    def _get_chart_data(self, sector: str):
        """Get comprehensive chart data for a sector"""
        try:
            if not sector:
                return validation_error_json("Sector parameter is required")
            
            result = self.service.get_chart_data(sector)
            
            return success_json(
                f"Chart data retrieved for {sector}",
                result
            )
            
        except ValueError as e:
            return error_json(str(e), status_code=404)
        except Exception as e:
            logger.exception(f"Error getting chart data for {sector}: {e}")
            return error_json(f"Failed to get chart data: {str(e)}")

    @with_service
    def _run_forecast(self):
        """Start a new forecast job with complete configuration management"""
        try:
            if not request.is_json:
                return validation_error_json("Request must be JSON")
            
            data = request.get_json()
            
            # debug logging
            logger.info("=== FORECAST REQUEST DEBUG ===")
            logger.info(f"Raw request data: {data}")
            logger.info(f"Request headers: {dict(request.headers)}")
            logger.info(f"Content type: {request.content_type}")
            
            if not data:
                logger.error("ERROR: No JSON data received")
                return validation_error_json("No data received")
                
            logger.info(f"Scenario name: {data.get('scenarioName')}")
            logger.info(f"Target year: {data.get('targetYear')}")
            logger.info(f"Sector configs: {data.get('sectorConfigs')}")
            logger.info(f"Number of sectors: {len(data.get('sectorConfigs', {}))}")
            logger.info(f"Detailed configuration: {data.get('detailedConfiguration', {})}")
            
            # configuration validation
            required_fields = ['scenarioName', 'targetYear', 'sectorConfigs']
            missing_fields = [field for field in required_fields if not data.get(field)]
            
            if missing_fields:
                return validation_error_json(
                    f"Missing required fields: {missing_fields}",
                    errors={'missing_fields': missing_fields}
                )
            
            # Create forecast configuration
            config = ForecastJobConfig(
                scenario_name=data['scenarioName'].strip(),
                target_year=int(data['targetYear']),
                exclude_covid_years=data.get('excludeCovidYears', True),
                sector_configs=data['sectorConfigs'],
                detailed_configuration=data.get('detailedConfiguration', {}),
                user_metadata={
                    'request_source': 'web_ui',
                    'configuration_version': '2.0.0',
                    'ip_address': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', 'unknown'),
                    'request_timestamp': datetime.now().isoformat()
                }
            )
            
            # Comprehensive validation
            validation_errors = self.service.validate_forecast_config(config)
            if validation_errors:
                return validation_error_json(
                    "  configuration validation failed",
                    errors=validation_errors
                )
            
            # Check for scenario replacement
            existing_scenario_path = os.path.join(
                self.get_project_path(), 'results', 'demand_projection', config.scenario_name
            )
            if os.path.exists(existing_scenario_path):
                logger.info(f"Will overwrite existing scenario '{config.scenario_name}'")
            
            # Check concurrent job limits
            active_jobs = job_manager.get_jobs_summary()['active_jobs']
            if active_jobs >= 3:
                return error_json(
                    "Too many active forecast jobs. Please wait for current jobs to complete.",
                    status_code=429
                )
            
            # Create job
            job_id = str(uuid.uuid4())
            job = job_manager.create_job(job_id, config)
            
            # CRITICAL FIX: Capture app instance BEFORE starting thread
            app = current_app._get_current_object()
            
            # Start background execution with app instance
            forecast_thread = threading.Thread(
                target=self._execute_forecast_job,
                args=(config, job_id, app),  # Pass app instance to thread
                name=f" ForecastJob-{config.scenario_name}-{job_id[:8]}",
                daemon=True
            )
            forecast_thread.start()
            
            # Update job status
            job_manager.update_job(job_id,
                status=JOB_STATUS['RUNNING'],
                message=f' forecast job started for {len(config.sector_configs)} sectors with complete configuration tracking'
            )
            
            logger.info(f"Started forecast job {job_id} for scenario '{config.scenario_name}'")
            
            return success_json(
                f" forecast job started for scenario '{config.scenario_name}'",
                {
                    'job_id': job_id,
                    'scenario_name': config.scenario_name,
                    'target_year': config.target_year,
                    'total_sectors': len(config.sector_configs),
                    'estimated_duration_minutes': len(config.sector_configs) * 2,
                    'configuration_tracking': True,
                    'auto_save_enabled': True,
                    'status_url': url_for('demand_projection.get_forecast_status_api', job_id=job_id),
                    'cancel_url': url_for('demand_projection.cancel_forecast_api', job_id=job_id),
                    'features': [
                        'complete_configuration_saving',
                        'progress_tracking',
                        'detailed_metadata_collection'
                    ]
                }
            )
            
        except ValueError as e:
            return validation_error_json(str(e))
        except Exception as e:
            logger.exception(f"Error starting forecast: {e}")
            return error_json(f"Failed to start forecast: {str(e)}")

    def _execute_forecast_job(self, config: ForecastJobConfig, job_id: str, app):
        """Execute forecast job in background thread with complete configuration management"""
        with app.app_context():  # Use the passed app instance
            try:
                logger.info(f"Executing forecast job {job_id} for scenario '{config.scenario_name}'")
                
                # Execute forecast using service
                result = self.service.execute_forecast(config, job_manager, job_id)
                
                if result['status'] == 'success':
                    logger.info(f" forecast job {job_id} completed successfully")
                elif result['status'] == 'cancelled':
                    logger.info(f" forecast job {job_id} was cancelled")
                else:
                    logger.error(f" forecast job {job_id} failed: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                error_msg = f"Critical error in forecast job {job_id}: {str(e)}"
                logger.exception(error_msg)
                
                job_manager.update_job(job_id,
                    status=JOB_STATUS['FAILED'],
                    error=error_msg,
                    message='Critical error occurred during forecast execution'
                )

    def _get_forecast_status(self, job_id: str):
        """Get comprehensive status of a forecast job"""
        try:
            if not job_id:
                return validation_error_json("Job ID is required")
            
            job = job_manager.get_job(job_id)
            if not job:
                return error_json(f"Job '{job_id}' not found", status_code=404)
            
            # Check for timeout or stalled jobs
            current_time = time.time()
            job_age = current_time - job['start_time']
            
            if job_age > 7200:  # 2 hours timeout
                job_manager.update_job(job_id,
                    status=JOB_STATUS['FAILED'],
                    error='Job timed out after 2 hours'
                )
                job = job_manager.get_job(job_id)  # Get updated job
            
            # Prepare comprehensive response
            response_data = {
                'job_id': job_id,
                'status': job['status'],
                'progress': job['progress'],
                'current_sector': job['current_sector'],
                'message': job['message'],
                'scenario_name': job['scenario_name'],
                'target_year': job['target_year'],
                'elapsed_time_seconds': job['elapsed_time_seconds'],
                'elapsed_time_formatted': job['elapsed_time_formatted'],
                'processed_sectors': job['processed_sectors'],
                'total_sectors': job['total_sectors'],
                'start_time': job['start_time_formatted'],
                'last_update': job['last_update_formatted'],
                'completion_rate': job.get('completion_rate', 0),
                'success_rate': job.get('success_rate', 0),
                'performance_metrics': job.get('performance_metrics', {}),
                # status information
                'configuration_tracking': True,
                'auto_save_status': 'enabled'
            }
            
            # Add timing estimates for running jobs
            if job['status'] == JOB_STATUS['RUNNING']:
                if 'estimated_remaining_seconds' in job:
                    response_data['estimated_remaining_seconds'] = job['estimated_remaining_seconds']
                    response_data['estimated_remaining_formatted'] = job['estimated_remaining_formatted']
                if 'estimated_completion' in job:
                    response_data['estimated_completion'] = job['estimated_completion']
            
            # Add result data for completed jobs
            if job['status'] == JOB_STATUS['COMPLETED']:
                response_data['result'] = job.get('result', {})
                response_data['sectors_completed'] = job.get('sectors_completed', [])
                response_data['sectors_existing_data'] = job.get('sectors_existing_data', [])
                response_data['sectors_failed'] = job.get('sectors_failed', [])
                # completion information
                if 'result' in job and 'config_path' in job['result']:
                    response_data['configuration_saved'] = True
                    response_data['config_file_path'] = job['result']['config_path']
            
            # Add error details for failed jobs
            elif job['status'] == JOB_STATUS['FAILED']:
                response_data['error'] = job.get('error')
                response_data['detailed_log'] = job.get('detailed_log', [])[-5:]  # Last 5 log entries
            
            return success_json(
                f"Status retrieved for job '{job_id}'",
                response_data
            )
            
        except Exception as e:
            logger.exception(f"Error getting forecast status for {job_id}: {e}")
            return error_json(f"Failed to get status: {str(e)}")
    
    def _cancel_forecast(self, job_id: str):
        """Cancel a forecast job with validation"""
        try:
            if not job_id:
                return validation_error_json("Job ID is required")
            
            job = job_manager.get_job(job_id)
            if not job:
                return error_json(f"Job '{job_id}' not found", status_code=404)
            
            if job['status'] not in [JOB_STATUS['RUNNING'], JOB_STATUS['STARTING']]:
                return error_json(f"Cannot cancel job with status '{job['status']}'", status_code=400)
            
            success = job_manager.cancel_job(job_id)
            if success:
                logger.info(f" forecast job {job_id} cancelled successfully")
                return success_json(
                    f" forecast job '{job_id}' cancelled successfully",
                    {
                        'job_id': job_id,
                        'previous_status': job['status'],
                        'new_status': JOB_STATUS['CANCELLED'],
                        'cancelled_at': datetime.now().isoformat(),
                        'scenario_name': job['scenario_name']
                    }
                )
            else:
                return error_json("Failed to cancel forecast job")
                
        except Exception as e:
            logger.exception(f"Error cancelling forecast {job_id}: {e}")
            return error_json(f"Failed to cancel: {str(e)}")
    
    def _get_jobs_summary(self):
        """Get comprehensive summary of all jobs"""
        try:
            summary = job_manager.get_jobs_summary()
            
            return success_json(
                " jobs summary retrieved successfully",
                summary
            )
            
        except Exception as e:
            logger.exception(f"Error getting jobs summary: {e}")
            return error_json(f"Failed to get summary: {str(e)}")
    
    def _validate_scenario_name(self):
        """ scenario name validation"""
        try:
            data = request.get_json()
            scenario_name = data['scenarioName'].strip()
            
            # format validation
            import re
            if not re.match(r'^[a-zA-Z0-9_\-\s]+$', scenario_name):
                return validation_error_json("Scenario name contains invalid characters")
            
            if len(scenario_name) < 2:
                return validation_error_json("Scenario name must be at least 2 characters long")
            
            if len(scenario_name) > 50:
                return validation_error_json("Scenario name must be 50 characters or less")
            
            # Check for existing scenario
            existing_path = os.path.join(
                self.get_project_path(), 'results', 'demand_projection', scenario_name
            )
            
            scenario_exists = os.path.exists(existing_path)
            
            # response with replacement warning
            response_data = {
                'scenario_name': scenario_name,
                'valid': True,
                'suggested_name': scenario_name,
                'will_replace': scenario_exists
            }
            
            if scenario_exists:
                response_data['warning'] = f"Scenario '{scenario_name}' already exists and will be replaced"
                return success_json(
                    f"Scenario name is valid but will replace existing scenario",
                    response_data
                )
            else:
                return success_json(
                    "Scenario name is valid and available",
                    response_data
                )
            
        except Exception as e:
            logger.exception(f"Error validating scenario name: {e}")
            return error_json(f"Validation failed: {str(e)}")
    
    @with_service
    def _get_data_summary(self):
        """Get comprehensive data summary for the project"""
        try:
            summary = self.service.get_input_data_summary()
            
            return success_json(
                " data summary retrieved successfully",
                summary
            )
            
        except Exception as e:
            logger.exception(f"Error getting data summary: {e}")
            return error_json(f"Failed to get data summary: {str(e)}")
    
    def _get_scenario_configuration(self, scenario_name: str):
        """Get saved configuration for a specific scenario"""
        try:
            if not scenario_name:
                return validation_error_json("Scenario name is required")
            
            scenario_path = os.path.join(
                self.get_project_path(), 'results', 'demand_projection', scenario_name
            )
            
            if not os.path.exists(scenario_path):
                return error_json(f"Scenario '{scenario_name}' not found", status_code=404)
            
            config_path = os.path.join(scenario_path, 'forecast_config.json')
            
            if not os.path.exists(config_path):
                return error_json(f"Configuration file not found for scenario '{scenario_name}'", status_code=404)
            
            # Load and return the configuration
            import json
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            
            return success_json(
                f"Configuration retrieved for scenario '{scenario_name}'",
                {
                    'scenario_name': scenario_name,
                    'configuration': config_data,
                    'config_file_path': config_path,
                    'last_modified': datetime.fromtimestamp(os.path.getmtime(config_path)).isoformat()
                }
            )
            
        except Exception as e:
            logger.exception(f"Error getting scenario configuration for {scenario_name}: {e}")
            return error_json(f"Failed to get configuration: {str(e)}")
    
    def _validate_complete_configuration(self):
        """Validate complete configuration without starting forecast"""
        try:
            if not request.is_json:
                return validation_error_json("Request must be JSON")
            
            data = request.get_json()
            
            # Create configuration object for validation
            config = ForecastJobConfig(
                scenario_name=data['scenarioName'].strip(),
                target_year=int(data['targetYear']),
                exclude_covid_years=data.get('excludeCovidYears', True),
                sector_configs=data['sectorConfigs'],
                detailed_configuration=data.get('detailedConfiguration', {})
            )
            
            # Run validation
            validation_errors = self.service.validate_forecast_config(config)
            
            if validation_errors:
                return validation_error_json(
                    "Configuration validation failed",
                    errors=validation_errors
                )
            else:
                return success_json(
                    "Configuration validation passed",
                    {
                        'valid': True,
                        'scenario_name': config.scenario_name,
                        'target_year': config.target_year,
                        'total_sectors': len(config.sector_configs),
                        'validation_timestamp': datetime.now().isoformat()
                    }
                )
                
        except Exception as e:
            logger.exception(f"Error validating configuration: {e}")
            return error_json(f"Configuration validation failed: {str(e)}")

# Create and register the blueprint
demand_projection_blueprint = DemandProjectionBlueprint()

# Export for Flask app registration  
demand_projection_bp = demand_projection_blueprint.blueprint

def register_demand_projection_bp(app):
    """Register the demand projection blueprint with the Flask app"""
    try:
        # Register with URL prefix
        demand_projection_blueprint.register(app, url_prefix='/demand_projection')
        logger.info(" Demand Projection Blueprint registered successfully with complete configuration support")
    except Exception as e:
        logger.error(f"Failed to register Demand Projection Blueprint: {e}")
        raise