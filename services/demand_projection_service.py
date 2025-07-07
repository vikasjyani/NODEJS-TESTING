# services/demand_projection_service.py -  with Configuration Saving
"""
 Demand Projection Service Layer with Complete Configuration Saving
Handles all business logic for demand forecasting and projection with real data processing
"""
import os
import json
import threading
import uuid
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, asdict

from utils.constants import JOB_STATUS, FORECAST_MODELS, VALIDATION_RULES, ERROR_MESSAGES
from utils.data_loading import input_demand_data, validate_input_file
from utils.demand_utils import (
    handle_nan_values, safe_numeric_conversion, create_summary,
    validate_project_path, validate_year_range
)
from utils.response_utils import handle_exception_response
from models.forecasting import Main_forecasting_function

logger = logging.getLogger(__name__)

@dataclass
class ForecastJobConfig:
    """ configuration for a forecast job with complete parameter storage"""
    scenario_name: str
    target_year: int
    exclude_covid_years: bool
    sector_configs: Dict[str, Any]
    detailed_configuration: Dict[str, Any] = None
    request_timestamp: str = None
    user_metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.detailed_configuration is None:
            self.detailed_configuration = {}
        if self.request_timestamp is None:
            self.request_timestamp = datetime.now().isoformat()
        if self.user_metadata is None:
            self.user_metadata = {}

@dataclass
class SectorProcessingResult:
    """Result of processing a single sector"""
    sector_name: str
    status: str  # 'success', 'existing_data', 'failed'
    message: str
    models_used: List[str] = None
    error: str = None
    processing_time_seconds: float = 0
    configuration_used: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.models_used is None:
            self.models_used = []
        if self.configuration_used is None:
            self.configuration_used = {}

class ForecastJobManager:
    """ job manager with comprehensive tracking and thread safety"""
    
    def __init__(self):
        self.jobs = {}
        self.lock = threading.RLock()
        self.cleanup_running = False
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """Start background cleanup thread"""
        if not self.cleanup_running:
            def cleanup_worker():
                self.cleanup_running = True
                while self.cleanup_running:
                    try:
                        time.sleep(300)  # 5 minutes
                        self._cleanup_old_jobs()
                    except Exception as e:
                        logger.error(f"Error in cleanup thread: {e}")
                
            cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
            cleanup_thread.start()
            logger.info("job cleanup thread started")
    
    def create_job(self, job_id: str, config: ForecastJobConfig, **kwargs):
        """Create a new forecast job with comprehensive tracking"""
        with self.lock:
            job_data = {
                'id': job_id,
                'status': JOB_STATUS['STARTING'],
                'progress': 0,
                'current_sector': None,
                'processed_sectors': 0,
                'total_sectors': len(config.sector_configs),
                'scenario_name': config.scenario_name,
                'target_year': config.target_year,
                'start_time': time.time(),
                'last_update': time.time(),
                'result': None,
                'error': None,
                'message': 'Initializing forecast job...',
                'configuration': asdict(config),
                'sectors_completed': [],
                'sectors_failed': [],
                'sectors_existing_data': [],
                'progress_history': [],
                'detailed_log': [],
                'performance_metrics': {
                    'total_processing_time': 0,
                    'average_sector_time': 0,
                    'memory_usage_mb': 0
                },
                **kwargs
            }
            
            self.jobs[job_id] = job_data
            logger.info(f"Created forecast job {job_id} for scenario '{config.scenario_name}' with {len(config.sector_configs)} sectors")
            return job_data
    
    def update_job(self, job_id: str, **updates):
        """Update job with validation and progress tracking"""
        with self.lock:
            if job_id not in self.jobs:
                logger.warning(f"Attempted to update non-existent job: {job_id}")
                return False
            
            job = self.jobs[job_id]
            old_progress = job.get('progress', 0)
            
            # Validate and clamp progress
            if 'progress' in updates:
                progress = max(0, min(100, safe_numeric_conversion(updates['progress'], 0)))
                updates['progress'] = progress
                
                # Track progress history
                if progress != old_progress:
                    progress_entry = {
                        'timestamp': time.time(),
                        'progress': progress,
                        'sector': updates.get('current_sector', job['current_sector']),
                        'message': updates.get('message', job['message'])
                    }
                    job['progress_history'].append(progress_entry)
                    
                    # Keep history manageable
                    if len(job['progress_history']) > 50:
                        job['progress_history'] = job['progress_history'][-25:]
            
            # Update job data
            job.update(updates)
            job['last_update'] = time.time()
            
            # Add to detailed log if message provided
            if 'message' in updates:
                log_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'message': updates['message'],
                    'status': job['status'],
                    'progress': job['progress'],
                    'sector': job['current_sector']
                }
                job['detailed_log'].append(log_entry)
                
                # Keep log size manageable
                if len(job['detailed_log']) > 100:
                    job['detailed_log'] = job['detailed_log'][-50:]
            
            return True
    
    def mark_sector_result(self, job_id: str, result: SectorProcessingResult):
        """Mark sector processing result with detailed tracking"""
        with self.lock:
            if job_id not in self.jobs:
                return False
            
            job = self.jobs[job_id]
            sector_name = result.sector_name
            
            # Update appropriate list based on result status
            if result.status == 'success':
                if sector_name not in job['sectors_completed']:
                    job['sectors_completed'].append(sector_name)
                    # Remove from other lists if present
                    for list_name in ['sectors_failed', 'sectors_existing_data']:
                        if sector_name in job[list_name]:
                            job[list_name].remove(sector_name)
            
            elif result.status == 'existing_data':
                if sector_name not in job['sectors_existing_data']:
                    job['sectors_existing_data'].append(sector_name)
                    # Remove from other lists if present
                    for list_name in ['sectors_failed', 'sectors_completed']:
                        if sector_name in job[list_name]:
                            job[list_name].remove(sector_name)
            
            elif result.status == 'failed':
                if sector_name not in job['sectors_failed']:
                    job['sectors_failed'].append(sector_name)
                    # Remove from other lists if present
                    for list_name in ['sectors_completed', 'sectors_existing_data']:
                        if sector_name in job[list_name]:
                            job[list_name].remove(sector_name)
            
            # Update processed sectors count
            job['processed_sectors'] = len(job['sectors_completed']) + len(job['sectors_failed']) + len(job['sectors_existing_data'])
            
            # Update performance metrics
            if result.processing_time_seconds > 0:
                total_time = job['performance_metrics']['total_processing_time'] + result.processing_time_seconds
                job['performance_metrics']['total_processing_time'] = total_time
                
                processed_count = job['processed_sectors']
                if processed_count > 0:
                    job['performance_metrics']['average_sector_time'] = total_time / processed_count
            
            logger.debug(f"Job {job_id}: Sector {sector_name} marked as {result.status}")
            return True
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """Get job with computed fields for frontend compatibility"""
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return None
            
            # Create copy with computed fields
            job = job.copy()
            
            # Calculate timing information
            current_time = time.time()
            elapsed_time = current_time - job['start_time']
            job['elapsed_time_seconds'] = elapsed_time
            job['elapsed_time_formatted'] = str(timedelta(seconds=int(elapsed_time)))
            
            # Calculate estimated completion time
            if job['progress'] > 0 and job['status'] == JOB_STATUS['RUNNING']:
                estimated_total = (elapsed_time / job['progress']) * 100
                estimated_remaining = max(0, estimated_total - elapsed_time)
                job['estimated_remaining_seconds'] = estimated_remaining
                job['estimated_remaining_formatted'] = str(timedelta(seconds=int(estimated_remaining)))
                job['estimated_completion'] = datetime.fromtimestamp(job['start_time'] + estimated_total).isoformat()
            
            # Add completion rate
            if job['total_sectors'] > 0:
                job['completion_rate'] = (job['processed_sectors'] / job['total_sectors'])
                job['success_rate'] = len(job['sectors_completed']) / job['total_sectors']
                job['existing_data_rate'] = len(job['sectors_existing_data']) / job['total_sectors']
                job['failure_rate'] = len(job['sectors_failed']) / job['total_sectors']
            
            # Add human-readable timestamps
            job['start_time_formatted'] = datetime.fromtimestamp(job['start_time']).isoformat()
            job['last_update_formatted'] = datetime.fromtimestamp(job['last_update']).isoformat()
            
            return job
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job"""
        with self.lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                if job['status'] in [JOB_STATUS['RUNNING'], JOB_STATUS['STARTING']]:
                    job['status'] = JOB_STATUS['CANCELLED']
                    job['message'] = 'Job cancelled by user request'
                    job['last_update'] = time.time()
                    logger.info(f"Job {job_id} marked for cancellation")
                    return True
            return False
    
    def _cleanup_old_jobs(self):
        """Clean up old completed or failed jobs"""
        with self.lock:
            current_time = time.time()
            jobs_to_remove = []
            
            for job_id, job in self.jobs.items():
                job_age = current_time - job['start_time']
                last_update_age = current_time - job['last_update']
                
                # Remove very old jobs (4+ hours)
                if job_age > 14400:
                    jobs_to_remove.append(job_id)
                
                # Remove completed/failed jobs older than 1 hour
                elif (job['status'] in [JOB_STATUS['COMPLETED'], JOB_STATUS['FAILED'], JOB_STATUS['CANCELLED']] 
                      and last_update_age > 3600):
                    jobs_to_remove.append(job_id)
                
                # Mark stalled jobs as failed
                elif (job['status'] in [JOB_STATUS['RUNNING'], JOB_STATUS['STARTING']] 
                      and last_update_age > 900):  # 15 minutes without update
                    logger.warning(f"Job {job_id} appears stalled, marking as failed")
                    job['status'] = JOB_STATUS['FAILED']
                    job['error'] = 'Job appears to have stalled'
                    job['message'] = 'Job stopped responding - possible thread crash'
                    job['last_update'] = current_time
            
            for job_id in jobs_to_remove:
                del self.jobs[job_id]
                logger.debug(f"Cleaned up old job: {job_id}")
    
    def get_jobs_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of all jobs"""
        with self.lock:
            summary = {
                'total_jobs': len(self.jobs),
                'active_jobs': 0,
                'completed_jobs': 0,
                'failed_jobs': 0,
                'cancelled_jobs': 0,
                'average_processing_time': 0,
                'recent_jobs': []
            }
            
            total_processing_time = 0
            completed_jobs_count = 0
            
            for job in self.jobs.values():
                status = job['status']
                if status in [JOB_STATUS['RUNNING'], JOB_STATUS['STARTING']]:
                    summary['active_jobs'] += 1
                elif status == JOB_STATUS['COMPLETED']:
                    summary['completed_jobs'] += 1
                    if 'performance_metrics' in job:
                        total_processing_time += job['performance_metrics'].get('total_processing_time', 0)
                        completed_jobs_count += 1
                elif status == JOB_STATUS['FAILED']:
                    summary['failed_jobs'] += 1
                elif status == JOB_STATUS['CANCELLED']:
                    summary['cancelled_jobs'] += 1
                
                # Add to recent jobs (last 5)
                if len(summary['recent_jobs']) < 5:
                    summary['recent_jobs'].append({
                        'id': job['id'],
                        'scenario_name': job['scenario_name'],
                        'status': job['status'],
                        'start_time': datetime.fromtimestamp(job['start_time']).isoformat(),
                        'progress': job['progress']
                    })
            
            # Calculate average processing time
            if completed_jobs_count > 0:
                summary['average_processing_time'] = total_processing_time / completed_jobs_count
            
            # Sort recent jobs by start time (newest first)
            summary['recent_jobs'].sort(key=lambda x: x['start_time'], reverse=True)
            
            return summary

class DemandProjectionService:
    """ Demand Projection Service with complete configuration management"""
    
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.input_file_path = os.path.join(project_path, 'inputs', 'input_demand_file.xlsx')
        self._cached_data = None
        self._cache_timestamp = None
        self._cache_ttl = 300  # 5 minutes
        
    def _load_input_data(self, force_reload: bool = False) -> Tuple[List[str], List[str], Dict, Dict, Any]:
        """Load input data with caching and validation"""
        current_time = time.time()
        
        # Check cache validity
        if (not force_reload and 
            self._cached_data and 
            self._cache_timestamp and 
            current_time - self._cache_timestamp < self._cache_ttl):
            logger.debug("Using cached input data")
            return self._cached_data
        
        # Load fresh data
        try:
            if not os.path.exists(self.input_file_path):
                raise FileNotFoundError(f"Input file not found: {self.input_file_path}")
            
            # Validate file first
            validation_result = validate_input_file(self.input_file_path)
            if not validation_result['valid']:
                raise ValueError(f"Input file validation failed: {'; '.join(validation_result['errors'])}")
            
            # Log any warnings
            for warning in validation_result.get('warnings', []):
                logger.warning(f"Input file warning: {warning}")
            
            # Load data using the real data loading function
            data = input_demand_data(self.input_file_path)
            self._cached_data = data
            self._cache_timestamp = current_time
            
            sectors, missing_sectors, param_dict, sector_data_map, aggregated_ele = data
            logger.info(f"Loaded input data: {len(sectors)} sectors, {len(missing_sectors)} missing")
            return data
            
        except Exception as e:
            logger.exception(f"Error loading input data: {e}")
            raise
    
    def get_input_data_summary(self) -> Dict[str, Any]:
        """Get comprehensive summary of input data"""
        try:
            sectors, missing_sectors, param_dict, sector_data_map, aggregated_ele = self._load_input_data()
            
            # Calculate data quality metrics
            total_sectors = len(sectors) + len(missing_sectors)
            data_completeness = len(sectors) / total_sectors if total_sectors > 0 else 0
            
            # Analyze year ranges
            year_ranges = {}
            for sector_name, df in sector_data_map.items():
                if 'Year' in df.columns and 'Electricity' in df.columns:
                    valid_data = df[['Year', 'Electricity']].dropna()
                    if not valid_data.empty:
                        year_ranges[sector_name] = {
                            'start': int(valid_data['Year'].min()),
                            'end': int(valid_data['Year'].max()),
                            'count': len(valid_data)
                        }
            
            return {
                'sectors': sectors,
                'missing_sectors': missing_sectors,
                'total_sectors': len(sectors),
                'missing_count': len(missing_sectors),
                'data_completeness': data_completeness,
                'parameters': param_dict,
                'data_available': len(sectors) > 0,
                'year_range': {
                    'start': param_dict.get('Start_Year'),
                    'end': param_dict.get('End_Year')
                },
                'sector_year_ranges': year_ranges,
                'aggregated_data_available': not aggregated_ele.empty,
                'file_validation': {
                    'valid': True,
                    'file_path': self.input_file_path,
                    'last_modified': datetime.fromtimestamp(os.path.getmtime(self.input_file_path)).isoformat()
                }
            }
        except Exception as e:
            logger.exception(f"Error getting input data summary: {e}")
            return {
                'error': str(e), 
                'data_available': False,
                'sectors': [],
                'missing_sectors': [],
                'total_sectors': 0
            }
    
    def get_sector_data(self, sector: str) -> Dict[str, Any]:
        """Get comprehensive data for a specific sector"""
        try:
            _, _, _, sector_data_map, _ = self._load_input_data()
            
            if sector not in sector_data_map:
                raise ValueError(f"Sector '{sector}' not found")
            
            df = sector_data_map[sector]
            
            # Analyze data quality
            quality_metrics = {
                'total_rows': len(df),
                'missing_data_percentage': df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100,
                'numeric_columns': len(df.select_dtypes(include=['number']).columns),
                'text_columns': len(df.select_dtypes(include=['object']).columns)
            }
            
            # Year and electricity analysis
            electricity_analysis = {}
            if 'Year' in df.columns and 'Electricity' in df.columns:
                elec_data = df[['Year', 'Electricity']].dropna()
                if not elec_data.empty:
                    electricity_analysis = {
                        'data_points': len(elec_data),
                        'year_range': {
                            'start': int(elec_data['Year'].min()),
                            'end': int(elec_data['Year'].max())
                        },
                        'electricity_range': {
                            'min': float(elec_data['Electricity'].min()),
                            'max': float(elec_data['Electricity'].max()),
                            'mean': float(elec_data['Electricity'].mean())
                        },
                        'growth_trend': self._calculate_growth_trend(elec_data)
                    }
            
            return {
                'sector': sector,
                'columns': df.columns.tolist(),
                'data': df.to_dict('records'),
                'quality_metrics': quality_metrics,
                'electricity_analysis': electricity_analysis,
                'summary': {
                    'has_year': 'Year' in df.columns,
                    'has_electricity': 'Electricity' in df.columns,
                    'can_forecast': 'Year' in df.columns and 'Electricity' in df.columns
                }
            }
        except Exception as e:
            logger.exception(f"Error getting sector data for {sector}: {e}")
            raise
    
    def _calculate_growth_trend(self, elec_data) -> str:
        """Calculate electricity growth trend for a sector"""
        try:
            if len(elec_data) < 2:
                return "insufficient_data"
            
            # Calculate year-over-year growth rates
            elec_data_sorted = elec_data.sort_values('Year')
            growth_rates = []
            
            for i in range(1, len(elec_data_sorted)):
                prev_value = elec_data_sorted.iloc[i-1]['Electricity']
                curr_value = elec_data_sorted.iloc[i]['Electricity']
                
                if prev_value > 0:
                    growth_rate = ((curr_value - prev_value) / prev_value) * 100
                    growth_rates.append(growth_rate)
            
            if not growth_rates:
                return "no_trend"
            
            avg_growth = sum(growth_rates) / len(growth_rates)
            
            if avg_growth > 2:
                return "increasing"
            elif avg_growth < -2:
                return "decreasing"
            else:
                return "stable"
                
        except Exception:
            return "calculation_error"
    
    def get_independent_variables(self, sector: str) -> Dict[str, Any]:
        """Get independent variables and correlations for MLR model"""
        try:
            _, _, _, sector_data_map, _ = self._load_input_data()
            
            if sector not in sector_data_map:
                raise ValueError(f"Sector '{sector}' not found")
            
            df = sector_data_map[sector]
            variables = df.columns.tolist()
            correlations = {}
            
            # Calculate correlations with electricity consumption
            if 'Electricity' in df.select_dtypes(include=['number']).columns:
                import pandas as pd
                electricity_data = pd.to_numeric(df['Electricity'], errors='coerce')
                
                for var in variables:
                    if var != 'Electricity':
                        try:
                            var_data = pd.to_numeric(df[var], errors='coerce')
                            
                            if not var_data.isna().all() and not electricity_data.isna().all():
                                combined_data = pd.DataFrame({
                                    'electricity': electricity_data,
                                    'variable': var_data
                                }).dropna()
                                
                                if len(combined_data) > 1:
                                    correlation = combined_data['electricity'].corr(combined_data['variable'])
                                    if not pd.isna(correlation):
                                        correlations[var] = float(correlation)
                        except Exception:
                            continue
            
            # Filter suitable variables for modeling
            suitable_variables = []
            for var in variables:
                if var != 'Electricity':
                    try:
                        var_data = pd.to_numeric(df[var], errors='coerce')
                        if var_data.count() >= VALIDATION_RULES['MIN_DATA_POINTS']:
                            suitable_variables.append(var)
                    except Exception:
                        continue
            
            # Categorize variables by correlation strength
            correlation_categories = {
                'strong': [],      # |correlation| >= 0.7
                'moderate': [],    # 0.4 <= |correlation| < 0.7
                'weak': []         # |correlation| < 0.4
            }
            
            for var, corr in correlations.items():
                abs_corr = abs(corr)
                if abs_corr >= 0.7:
                    correlation_categories['strong'].append(var)
                elif abs_corr >= 0.4:
                    correlation_categories['moderate'].append(var)
                else:
                    correlation_categories['weak'].append(var)
            
            return {
                'sector': sector,
                'all_variables': variables,
                'suitable_variables': suitable_variables,
                'correlations': correlations,
                'correlation_categories': correlation_categories,
                'total_variables': len(variables),
                'suitable_count': len(suitable_variables),
                'recommendations': {
                    'recommended_for_mlr': correlation_categories['strong'] + correlation_categories['moderate'],
                    'max_recommended': min(5, len(correlation_categories['strong']) + len(correlation_categories['moderate']))
                }
            }
        except Exception as e:
            logger.exception(f"Error getting independent variables for {sector}: {e}")
            raise
    
    def get_correlation_data(self, sector: str) -> Dict[str, Any]:
        """Get detailed correlation analysis for a sector"""
        try:
            _, _, _, sector_data_map, aggregated_ele_df = self._load_input_data()
            
            # Determine dataset
            if sector == 'aggregated':
                df_corr = aggregated_ele_df
                display_name = 'Aggregated Data'
            else:
                if sector not in sector_data_map:
                    raise ValueError(f"Sector '{sector}' not found")
                df_corr = sector_data_map[sector]
                display_name = sector
            
            if df_corr is None or df_corr.empty:
                return {
                    'sector': sector,
                    'display_name': display_name,
                    'variables': [],
                    'correlations': [],
                    'error': 'No data available'
                }
            
            import pandas as pd
            
            # Get numeric columns only
            numeric_df = df_corr.select_dtypes(include=['number'])
            
            if 'Electricity' not in numeric_df.columns:
                return {
                    'sector': sector,
                    'display_name': display_name,
                    'variables': [],
                    'correlations': [],
                    'error': 'No electricity data found'
                }
            
            # Calculate correlation matrix
            corr_matrix = numeric_df.corr()
            elec_corr = corr_matrix['Electricity'].drop('Electricity', errors='ignore')
            
            variables = []
            correlations = []
            
            for var, corr_value in elec_corr.items():
                if pd.isna(corr_value):
                    continue
                
                corr_abs = abs(corr_value)
                
                # Determine strength and styling
                if corr_abs >= 0.7:
                    strength = "Strong"
                    strength_class = "success"
                    priority = 3
                elif corr_abs >= 0.4:
                    strength = "Moderate"
                    strength_class = "warning"
                    priority = 2
                else:
                    strength = "Weak"
                    strength_class = "secondary"
                    priority = 1
                
                variables.append(var)
                correlations.append({
                    'value': round(float(corr_value), 4),
                    'abs_value': round(corr_abs, 4),
                    'strength': strength,
                    'strength_class': strength_class,
                    'direction': 'Positive' if corr_value > 0 else 'Negative',
                    'priority': priority,
                    'recommended_for_mlr': corr_abs >= 0.4
                })
            
            # Sort by absolute correlation (strongest first)
            if correlations:
                combined = list(zip(variables, correlations))
                combined.sort(key=lambda x: x[1]['abs_value'], reverse=True)
                variables, correlations = zip(*combined)
                variables, correlations = list(variables), list(correlations)
            
            # Calculate summary statistics
            summary_stats = {
                'total_variables': len(variables),
                'strong_correlations': sum(1 for c in correlations if c['strength'] == 'Strong'),
                'moderate_correlations': sum(1 for c in correlations if c['strength'] == 'Moderate'),
                'weak_correlations': sum(1 for c in correlations if c['strength'] == 'Weak'),
                'recommended_for_mlr': sum(1 for c in correlations if c['recommended_for_mlr']),
                'max_correlation': max([c['abs_value'] for c in correlations]) if correlations else 0,
                'min_correlation': min([c['abs_value'] for c in correlations]) if correlations else 0
            }
            
            return {
                'sector': sector,
                'display_name': display_name,
                'variables': variables,
                'correlations': correlations,
                'summary_stats': summary_stats
            }
        except Exception as e:
            logger.exception(f"Error getting correlation data for {sector}: {e}")
            raise
    
    def get_chart_data(self, sector: str) -> Dict[str, Any]:
        """Get comprehensive chart data for visualization"""
        try:
            sectors_list, _, param_dict, sector_data_map, aggregated_ele = self._load_input_data()
            
            target_year = int(param_dict.get('End_Year', 2037))
            start_year = int(param_dict.get('Start_Year', 2006))
            
            if sector == 'aggregated':
                return self._get_aggregated_chart_data(aggregated_ele, sectors_list, target_year, start_year)
            else:
                return self._get_individual_chart_data(sector, sector_data_map, target_year, start_year)
                
        except Exception as e:
            logger.exception(f"Error getting chart data for {sector}: {e}")
            raise
    
    def _get_aggregated_chart_data(self, aggregated_ele, sectors_list, target_year, start_year):
        """Get chart data for aggregated view"""
        if aggregated_ele.empty or 'Year' not in aggregated_ele.columns:
            return {
                'type': 'aggregated',
                'years': [],
                'datasets': [],
                'error': 'No aggregated data available'
            }
        
        years_agg = aggregated_ele['Year'].tolist()
        datasets_agg = []
        
        from utils.constants import SECTOR_COLORS
        for i, sector_name in enumerate(sectors_list):
            if sector_name in aggregated_ele.columns:
                color_idx = i % len(SECTOR_COLORS)
                color = SECTOR_COLORS[color_idx]
                
                sector_values = [
                    safe_numeric_conversion(val, 0) 
                    for val in aggregated_ele[sector_name].tolist()
                ]
                
                # Calculate some basic statistics
                non_zero_values = [v for v in sector_values if v > 0]
                sector_stats = {
                    'total_consumption': sum(sector_values),
                    'average_consumption': sum(sector_values) / len(sector_values) if sector_values else 0,
                    'max_consumption': max(sector_values) if sector_values else 0,
                    'data_points': len(non_zero_values)
                }
                
                datasets_agg.append({
                    'label': sector_name,
                    'data': sector_values,
                    'backgroundColor': color['bg'],
                    'borderColor': color['border'],
                    'borderWidth': 2,
                    'fill': False,
                    'statistics': sector_stats
                })
        
        # Calculate total consumption if available
        total_data = []
        if 'Total' in aggregated_ele.columns:
            total_data = [safe_numeric_conversion(val, 0) for val in aggregated_ele['Total'].tolist()]
        
        return {
            'type': 'aggregated',
            'years': years_agg,
            'datasets': datasets_agg,
            'total_consumption': total_data,
            'summary': {
                'total_sectors': len(datasets_agg),
                'year_range': f"{min(years_agg)}-{max(years_agg)}" if years_agg else "No data",
                'data_points': len(years_agg)
            }
        }
    
    def _get_individual_chart_data(self, sector, sector_data_map, target_year, start_year):
        """Get chart data for individual sector"""
        if sector not in sector_data_map:
            raise ValueError(f"Sector '{sector}' not found")
        
        df_sector = sector_data_map[sector].copy()
        
        if 'Year' not in df_sector.columns:
            raise ValueError(f"No 'Year' column found in sector '{sector}'")
        
        years = df_sector['Year'].tolist()
        electricity = []
        
        if 'Electricity' in df_sector.columns:
            electricity = [
                safe_numeric_conversion(val, 0) 
                for val in df_sector['Electricity'].tolist()
            ]
        
        # Analyze data completeness and forecast requirements
        data_analysis = self._analyze_sector_data_completeness(
            years, electricity, target_year, start_year, sector
        )
        
        # Get additional variables for potential correlations
        additional_variables = {}
        for col in df_sector.columns:
            if col not in ['Year', 'Electricity']:
                try:
                    var_data = pd.to_numeric(df_sector[col], errors='coerce')
                    if not var_data.isna().all():
                        additional_variables[col] = var_data.tolist()
                except:
                    continue
        
        return {
            'type': 'individual',
            'sector': sector,
            'years': years,
            'electricity': electricity,
            'additional_variables': additional_variables,
            'data_analysis': data_analysis
        }
    
    def _analyze_sector_data_completeness(self, years, electricity, target_year, start_year, sector_name):
        """Analyze data completeness and forecast requirements"""
        import pandas as pd
        
        analysis = {
            'has_complete_data': False,
            'max_year': 0,
            'target_year': target_year,
            'start_year': start_year,
            'data_points': 0,
            'forecast_needed': True,
            'data_quality': 'unknown',
            'missing_years': [],
            'coverage_percentage': 0
        }
        
        if not electricity or not years:
            analysis['data_quality'] = 'no_data'
            return analysis
        
        # Find valid data points
        valid_data_points = [
            (y, e) for y, e in zip(years, electricity) 
            if e is not None and not pd.isna(e) and e > 0
        ]
        
        analysis['data_points'] = len(valid_data_points)
        
        if not valid_data_points:
            analysis['data_quality'] = 'no_valid_data'
            return analysis
        
        # Calculate coverage
        analysis['max_year'] = max(y for y, _ in valid_data_points)
        min_year_data = min(y for y, _ in valid_data_points)
        
        analysis['has_complete_data'] = analysis['max_year'] >= target_year
        analysis['forecast_needed'] = not analysis['has_complete_data']
        
        # Calculate coverage percentage
        expected_years = target_year - start_year + 1
        actual_years = len(set(y for y, _ in valid_data_points))
        analysis['coverage_percentage'] = (actual_years / expected_years) * 100
        
        # Determine data quality
        if analysis['coverage_percentage'] >= 80:
            analysis['data_quality'] = 'excellent'
        elif analysis['coverage_percentage'] >= 60:
            analysis['data_quality'] = 'good'
        elif analysis['coverage_percentage'] >= 40:
            analysis['data_quality'] = 'fair'
        else:
            analysis['data_quality'] = 'poor'
        
        # Find missing years in the range
        all_years_needed = set(range(start_year, target_year + 1))
        years_with_data = set(y for y, _ in valid_data_points)
        analysis['missing_years'] = sorted(list(all_years_needed - years_with_data))
        
        return analysis




    def validate_forecast_config(self, config: ForecastJobConfig) -> List[str]:
        """Validate forecast configuration with checks"""
        errors = []
        
        # Validate scenario name
        if not config.scenario_name or len(config.scenario_name.strip()) < 2:
            errors.append("Scenario name must be at least 2 characters long")
        
        # Check for invalid characters in scenario name
        import re
        if not re.match(r'^[a-zA-Z0-9_\-\s]+$', config.scenario_name):
            errors.append("Scenario name contains invalid characters (only letters, numbers, spaces, hyphens, and underscores allowed)")
        
        # Validate target year
        if config.target_year < 2020 or config.target_year > 2100:
            errors.append("Target year must be between 2020 and 2100")
        
        # Validate sector configurations
        if not config.sector_configs:
            errors.append("No sector configurations provided")
        
        if len(config.sector_configs) > 20:
            errors.append("Too many sectors (maximum 20 allowed)")
        
        # Load input data to validate sectors exist
        try:
            sectors, _, param_dict, sector_data_map, _ = self._load_input_data()
            
            # REMOVED: Global target year validation
            # OLD CODE (REMOVE THESE LINES):
            # data_end_year = param_dict.get('End_Year', 2023)
            # if config.target_year <= data_end_year:
            #     errors.append(f"Target year ({config.target_year}) should be after data end year ({data_end_year})")
            
            # NEW: Let sector-specific logic handle target year validation
            # Each sector will decide whether to use existing data or forecast
            
            # Validate each sector configuration
            for sector_name, sector_config in config.sector_configs.items():
                if sector_name not in sector_data_map:
                    errors.append(f"Sector '{sector_name}' not found in input data")
                    continue
                
                if not isinstance(sector_config, dict):
                    errors.append(f"Invalid configuration for sector '{sector_name}'")
                    continue
                
                models = sector_config.get('models', [])
                if not models:
                    errors.append(f"No models specified for sector '{sector_name}'")
                
                for model in models:
                    if model not in FORECAST_MODELS:
                        errors.append(f"Invalid model '{model}' for sector '{sector_name}'")
                
                # Validate MLR configuration
                if 'MLR' in models:
                    independent_vars = sector_config.get('independentVars', [])
                    if len(independent_vars) > VALIDATION_RULES['MAX_INDEPENDENT_VARS']:
                        errors.append(f"Too many independent variables for sector '{sector_name}' (maximum {VALIDATION_RULES['MAX_INDEPENDENT_VARS']})")
                    
                    # Check if independent variables exist in sector data
                    sector_df = sector_data_map[sector_name]
                    for var in independent_vars:
                        if var not in sector_df.columns:
                            errors.append(f"Independent variable '{var}' not found in sector '{sector_name}' data")
                
                # Validate WAM configuration
                if 'WAM' in models:
                    window_size = sector_config.get('windowSize', 10)
                    if not isinstance(window_size, int) or window_size < VALIDATION_RULES['MIN_WINDOW_SIZE'] or window_size > VALIDATION_RULES['MAX_WINDOW_SIZE']:
                        errors.append(f"Invalid window size for sector '{sector_name}' (must be between {VALIDATION_RULES['MIN_WINDOW_SIZE']} and {VALIDATION_RULES['MAX_WINDOW_SIZE']})")
        
        except Exception as validation_error:
            errors.append(f"Error validating against input data: {str(validation_error)}")
        
        return errors
    def execute_forecast(self, config: ForecastJobConfig, job_manager: ForecastJobManager, job_id: str) -> Dict[str, Any]:
        """Execute forecast with comprehensive progress tracking, error handling, and configuration saving"""
        try:
            # Update job status
            job_manager.update_job(job_id,
                status=JOB_STATUS['RUNNING'],
                progress=5,
                message='Loading and validating input data...'
            )
            
            # Load and validate data
            sectors, _, param_dict, sector_data_map, _ = self._load_input_data()
            
            start_year = int(param_dict.get('Start_Year', 2006))
            end_year = int(param_dict.get('End_Year', 2023))
            
            # Validate sectors exist
            missing_sectors = [
                sector for sector in config.sector_configs.keys()
                if sector not in sector_data_map
            ]
            
            if missing_sectors:
                raise ValueError(f"Sectors not found in input data: {missing_sectors}")
            
            job_manager.update_job(job_id,
                progress=10,
                message=f'Data validation complete. Processing {len(config.sector_configs)} sectors...'
            )
            
            # Create results directory
            forecast_dir = os.path.join(
                self.project_path, 'results', 'demand_projection', 
                config.scenario_name
            )
            os.makedirs(forecast_dir, exist_ok=True)
            
            # CRITICAL ENHANCEMENT: Save complete configuration first
            job_manager.update_job(job_id,
                progress=12,
                message='Saving forecast configuration...'
            )
            
            config_data = self._create_complete_configuration(config, sectors, param_dict)
            config_path = os.path.join(forecast_dir, 'forecast_config.json')
            
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=4, default=str)
            
            logger.info(f"Saved complete configuration to {config_path}")
            
            # Track results
            sector_results = []
            total_sectors = len(config.sector_configs)
            
            # Create progress callback for forecasting function
            def progress_callback(progress_percent, current_sector, message):
                """Callback for progress updates from forecasting function"""
                try:
                    job_manager.update_job(job_id,
                        progress=15 + int((progress_percent / 100) * 70),  # Scale to 15-85%
                        current_sector=current_sector,
                        message=f'{current_sector}: {message}'
                    )
                except Exception as callback_error:
                    logger.warning(f"Error in progress callback: {callback_error}")
            
            # Process each sector
            for idx, (sector_name, sector_config) in enumerate(config.sector_configs.items()):
                sector_start_time = time.time()
                
                # Check for cancellation
                current_job = job_manager.get_job(job_id)
                if current_job and current_job['status'] == JOB_STATUS['CANCELLED']:
                    logger.info(f"Job {job_id} cancelled during sector processing")
                    return {'status': 'cancelled'}
                
                # Update progress
                base_progress = 15 + int((idx / total_sectors) * 70)
                job_manager.update_job(job_id,
                    current_sector=sector_name,
                    processed_sectors=idx,
                    progress=base_progress,
                    message=f'Processing {sector_name} ({idx+1}/{total_sectors})...'
                )
                
                try:
                    # Execute forecasting for this sector
                    result = self._execute_sector_forecast(
                        sector_name, sector_config, forecast_dir,
                        sector_data_map[sector_name], config, progress_callback
                    )
                    
                    # Create sector result with configuration details
                    sector_processing_time = time.time() - sector_start_time
                    sector_result = SectorProcessingResult(
                        sector_name=sector_name,
                        status='existing_data' if result.get('used_existing_data', False) else 'success',
                        message=result.get('message', 'Processing completed'),
                        models_used=result.get('models_used', sector_config.get('models', [])),
                        processing_time_seconds=sector_processing_time,
                        configuration_used=sector_config
                    )
                    
                    sector_results.append(sector_result)
                    job_manager.mark_sector_result(job_id, sector_result)
                    
                    logger.info(f"Sector {sector_name} processed successfully in {sector_processing_time:.2f}s")
                    
                except Exception as sector_error:
                    sector_processing_time = time.time() - sector_start_time
                    error_msg = str(sector_error)
                    
                    logger.exception(f"Error processing sector {sector_name}: {error_msg}")
                    
                    sector_result = SectorProcessingResult(
                        sector_name=sector_name,
                        status='failed',
                        message=f'Processing failed: {error_msg}',
                        error=error_msg,
                        processing_time_seconds=sector_processing_time,
                        configuration_used=sector_config
                    )
                    
                    sector_results.append(sector_result)
                    job_manager.mark_sector_result(job_id, sector_result)
                    
                    # Continue processing other sectors
                    job_manager.update_job(job_id,
                        message=f'Error in {sector_name}, continuing with other sectors...'
                    )
                    continue
            
            # Create comprehensive summary
            job_manager.update_job(job_id,
                progress=90,
                current_sector='Summary',
                message='Creating comprehensive forecast summary...'
            )
            
            summary = self._create_summary(
                config, sector_results, forecast_dir, start_year, end_year
            )
            
            # Save summary
            summary_path = os.path.join(forecast_dir, 'forecast_summary.json')
            with open(summary_path, 'w') as f:
                json.dump(summary, f, indent=4, default=str)
            
            # ENHANCEMENT: Save additional metadata files
            metadata_path = os.path.join(forecast_dir, 'execution_metadata.json')
            execution_metadata = {
                'job_id': job_id,
                'execution_start': datetime.fromtimestamp(job_manager.get_job(job_id)['start_time']).isoformat(),
                'execution_end': datetime.now().isoformat(),
                'total_processing_time_seconds': sum(r.processing_time_seconds for r in sector_results),
                'sectors_processed': len(sector_results),
                'configuration_file': 'forecast_config.json',
                'summary_file': 'forecast_summary.json',
                'version_info': {
                    'platform_version': '1.0.0',
                    'forecasting_models': FORECAST_MODELS
                }
            }
            
            with open(metadata_path, 'w') as f:
                json.dump(execution_metadata, f, indent=4, default=str)
            
            # Categorize results
            successful_sectors = [r for r in sector_results if r.status in ['success', 'existing_data']]
            failed_sectors = [r for r in sector_results if r.status == 'failed']
            
            # Determine final job status
            if failed_sectors and not successful_sectors:
                final_status = JOB_STATUS['FAILED']
                final_message = f'All {len(failed_sectors)} sectors failed to process'
                error_message = f'Processing failed for all sectors: {[r.sector_name for r in failed_sectors]}'
            elif failed_sectors:
                final_status = JOB_STATUS['COMPLETED']
                final_message = f'Forecast completed with {len(failed_sectors)} errors out of {total_sectors} sectors'
                error_message = None
            else:
                final_status = JOB_STATUS['COMPLETED']
                final_message = f'Forecast completed successfully for all {total_sectors} sectors'
                error_message = None
            
            # Prepare final result
            final_result = {
                'scenario_name': config.scenario_name,
                'target_year': config.target_year,
                'total_sectors': total_sectors,
                'successful_sectors': len(successful_sectors),
                'failed_sectors': len(failed_sectors),
                'forecast_dir': forecast_dir,
                'config_path': config_path,
                'summary_path': summary_path,
                'metadata_path': metadata_path,
                'sector_results': [asdict(r) for r in sector_results],
                'processing_summary': summary,
                'performance_metrics': {
                    'total_processing_time': sum(r.processing_time_seconds for r in sector_results),
                    'average_sector_time': sum(r.processing_time_seconds for r in sector_results) / len(sector_results) if sector_results else 0,
                    'fastest_sector': min(sector_results, key=lambda r: r.processing_time_seconds).sector_name if sector_results else None,
                    'slowest_sector': max(sector_results, key=lambda r: r.processing_time_seconds).sector_name if sector_results else None
                }
            }
            
            # Update final job status
            job_manager.update_job(job_id,
                status=final_status,
                progress=100,
                message=final_message,
                result=final_result,
                error=error_message
            )
            
            logger.info(f"Forecast job {job_id} completed: {len(successful_sectors)} successful, {len(failed_sectors)} failed")
            
            return {
                'status': 'success' if final_status == JOB_STATUS['COMPLETED'] else 'failed',
                **final_result
            }
            
        except Exception as e:
            error_msg = f"Critical error in forecast execution: {str(e)}"
            logger.exception(error_msg)
            
            job_manager.update_job(job_id,
                status=JOB_STATUS['FAILED'],
                error=error_msg,
                message='Critical error occurred during forecast execution'
            )
            
            return {'status': 'error', 'error': error_msg}
    
    def _create_complete_configuration(self, config: ForecastJobConfig, sectors: List[str], param_dict: Dict) -> Dict[str, Any]:
        """Create complete configuration data structure for saving"""
        
        # Get current timestamp
        current_time = datetime.now()
        
        # Build comprehensive configuration
        complete_config = {
            # Basic forecast parameters
            'forecast_parameters': {
                'scenario_name': config.scenario_name,
                'target_year': config.target_year,
                'exclude_covid_years': config.exclude_covid_years,
                'request_timestamp': config.request_timestamp,
                'created_timestamp': current_time.isoformat(),
                'created_by': 'KSEB Energy Futures Platform'
            },
            
            # Data context
            'data_context': {
                'input_file_path': self.input_file_path,
                'data_start_year': param_dict.get('Start_Year'),
                'data_end_year': param_dict.get('End_Year'),
                'available_sectors': sectors,
                'total_sectors_configured': len(config.sector_configs),
                'data_file_last_modified': datetime.fromtimestamp(os.path.getmtime(self.input_file_path)).isoformat() if os.path.exists(self.input_file_path) else None
            },
            
            # Detailed sector configurations
            'sector_configurations': {},
            
            # Global configuration settings
            'global_settings': config.detailed_configuration,
            
            # User metadata
            'user_metadata': config.user_metadata,
            
            # Platform information
            'platform_info': {
                'version': '1.0.0',
                'available_models': FORECAST_MODELS,
                'validation_rules': VALIDATION_RULES
            }
        }
        
        # Detailed sector configuration breakdown
        for sector_name, sector_config in config.sector_configs.items():
            detailed_sector_config = {
                'sector_name': sector_name,
                'selected_models': sector_config.get('models', []),
                'model_configurations': {},
                'data_analysis': {},
                'advanced_settings': {}
            }
            
            # MLR Configuration
            if 'MLR' in sector_config.get('models', []):
                detailed_sector_config['model_configurations']['MLR'] = {
                    'independent_variables': sector_config.get('independentVars', []),
                    'total_variables_selected': len(sector_config.get('independentVars', [])),
                    'variable_selection_method': 'user_selected',
                    'correlation_threshold': 0.4  # Standard threshold
                }
            
            # WAM Configuration
            if 'WAM' in sector_config.get('models', []):
                window_size = sector_config.get('windowSize', 10)
                detailed_sector_config['model_configurations']['WAM'] = {
                    'window_size_years': window_size,
                    'weighting_method': 'linear_increasing',
                    'window_type': 'custom' if window_size not in [5, 10, 15] else 'preset'
                }
            
            # SLR Configuration
            if 'SLR' in sector_config.get('models', []):
                detailed_sector_config['model_configurations']['SLR'] = {
                    'regression_type': 'simple_linear',
                    'predictor_variable': 'Year',
                    'method': 'least_squares'
                }
            
            # Time Series Configuration
            if 'TimeSeries' in sector_config.get('models', []):
                detailed_sector_config['model_configurations']['TimeSeries'] = {
                    'decomposition_method': 'automatic',
                    'forecasting_algorithm': 'auto_select',
                    'seasonality_detection': 'enabled'
                }
            
            # Add data analysis context if available
            try:
                _, _, _, sector_data_map, _ = self._load_input_data()
                if sector_name in sector_data_map:
                    sector_df = sector_data_map[sector_name]
                    if 'Year' in sector_df.columns and 'Electricity' in sector_df.columns:
                        elec_data = sector_df[['Year', 'Electricity']].dropna()
                        if not elec_data.empty:
                            detailed_sector_config['data_analysis'] = {
                                'data_start_year': int(elec_data['Year'].min()),
                                'data_end_year': int(elec_data['Year'].max()),
                                'total_data_points': len(elec_data),
                                'forecast_needed': int(elec_data['Year'].max()) < config.target_year,
                                'forecast_years_count': max(0, config.target_year - int(elec_data['Year'].max())),
                                'data_quality_indicators': {
                                    'has_missing_values': elec_data.isnull().any().any(),
                                    'data_completeness_percentage': round((len(elec_data) / (int(elec_data['Year'].max()) - int(elec_data['Year'].min()) + 1)) * 100, 2)
                                }
                            }
            except Exception as analysis_error:
                logger.warning(f"Could not add data analysis for sector {sector_name}: {analysis_error}")
                detailed_sector_config['data_analysis'] = {
                    'analysis_error': str(analysis_error)
                }
            
            complete_config['sector_configurations'][sector_name] = detailed_sector_config
        
        return complete_config
    
    def _execute_sector_forecast(self, sector_name: str, sector_config: Dict,
                                forecast_dir: str, sector_data, config: ForecastJobConfig,
                                progress_callback: Callable = None) -> Dict:
        """Execute forecast for a single sector using the real forecasting function"""
        selected_models = sector_config.get('models', ['MLR', 'SLR', 'WAM', 'TimeSeries'])
        
        # Prepare model parameters
        model_params_config = {}
        if 'MLR' in selected_models:
            independent_vars = sector_config.get('independentVars', [])
            model_params_config['MLR'] = {'independent_vars': independent_vars}
        
        if 'WAM' in selected_models:
            window_size = int(sector_config.get('windowSize', 10))
            model_params_config['WAM'] = {'window_size': window_size}
        
        # Execute the real forecasting function with progress callback
        return Main_forecasting_function(
            sheet_name=sector_name,
            forecast_path=forecast_dir,
            main_df=sector_data,
            selected_models=selected_models,
            model_params=model_params_config,
            target_year=config.target_year,
            exclude_covid=config.exclude_covid_years,
            progress_callback=progress_callback
        )
    
    def _create_summary(self, config: ForecastJobConfig, sector_results: List[SectorProcessingResult],
                       forecast_dir: str, start_year: int, end_year: int) -> Dict[str, Any]:
        """Create  summary with detailed analysis"""
        
        # Categorize results
        successful_sectors = [r for r in sector_results if r.status == 'success']
        existing_data_sectors = [r for r in sector_results if r.status == 'existing_data']
        failed_sectors = [r for r in sector_results if r.status == 'failed']
        
        # Calculate performance metrics
        processing_times = [r.processing_time_seconds for r in sector_results if r.processing_time_seconds > 0]
        
        # Analyze model usage
        model_usage = {}
        for result in sector_results:
            for model in result.models_used:
                model_usage[model] = model_usage.get(model, 0) + 1
        
        # Create comprehensive summary using the utility function
        base_summary = create_summary(
            asdict(config), config.sector_configs, forecast_dir,
            [r.sector_name for r in existing_data_sectors],
            [r.sector_name for r in successful_sectors],
            [r.sector_name for r in failed_sectors],
            start_year, end_year
        )
        
        # Enhance with additional details
        summary = {
            **base_summary,
            'detailed_results': {
                'sector_performance': [
                    {
                        'sector_name': r.sector_name,
                        'status': r.status,
                        'processing_time': r.processing_time_seconds,
                        'models_used': r.models_used,
                        'message': r.message,
                        'error': r.error,
                        'configuration_used': r.configuration_used
                    }
                    for r in sector_results
                ],
                'performance_analysis': {
                    'total_processing_time': sum(processing_times),
                    'average_processing_time': sum(processing_times) / len(processing_times) if processing_times else 0,
                    'fastest_processing_time': min(processing_times) if processing_times else 0,
                    'slowest_processing_time': max(processing_times) if processing_times else 0,
                    'processing_efficiency': len(successful_sectors + existing_data_sectors) / len(sector_results) if sector_results else 0
                },
                'model_analysis': {
                    'model_usage_distribution': model_usage,
                    'most_used_model': max(model_usage.keys(), key=model_usage.get) if model_usage else None,
                    'total_model_instances': sum(model_usage.values())
                }
            },
            'configuration_summary': {
                'scenario_name': config.scenario_name,
                'target_year': config.target_year,
                'exclude_covid_years': config.exclude_covid_years,
                'total_sectors_configured': len(config.sector_configs),
                'configuration_complexity': 'Advanced' if any(
                    len(sc.get('independentVars', [])) > 3 or sc.get('windowSize', 10) != 10 
                    for sc in config.sector_configs.values()
                ) else 'Standard'
            }
        }
        
        return summary

# Global job manager instance
job_manager = ForecastJobManager()