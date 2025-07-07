# services/loadprofile_service.py
"""
Load Profile Service Layer
Handles all business logic for load profile generation and management
"""
import os
import json
import pandas as pd
import numpy as np
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from werkzeug.datastructures import FileStorage

from models.load_profile_generator import LoadProfileGenerator
from utils.helpers import get_file_info, ensure_directory
from utils.constants import VALIDATION_RULES, UNIT_FACTORS

logger = logging.getLogger(__name__)

class LoadProfileService:
    """
    Service layer for load profile operations with caching and analysis
    """
    
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.generator = LoadProfileGenerator(project_path)
        
        # Cache for expensive operations
        self._template_cache = {}
        self._scenario_cache = {}
        self._profile_cache = {}
        self._cache_timestamps = {}
        self._cache_ttl = 300  # 5 minutes
    
    def get_main_page_data(self) -> Dict[str, Any]:
        """Get all data needed for main page rendering"""
        try:
            # Get available demand scenarios
            available_scenarios = self._get_available_scenarios()
            
            # Get saved profiles
            saved_profiles = self.get_saved_profiles_with_metadata()
            
            # Check template availability
            template_info = self._get_template_availability()
            
            return {
                'project_name': os.path.basename(self.project_path),
                'template_exists': template_info['exists'],
                'template_info': template_info,
                'available_scenarios': available_scenarios,
                'saved_profiles': saved_profiles['profiles'],
                'total_saved_profiles': saved_profiles['total_count'],
                'stl_available': hasattr(self.generator, 'generate_stl_forecast'),
                'page_loaded_at': datetime.now().isoformat()
            }
        except Exception as e:
            logger.exception(f"Error getting main page data: {e}")
            return {'error': str(e)}
    
    def get_template_analysis(self) -> Dict[str, Any]:
        """Get comprehensive template analysis with caching"""
        cache_key = 'template_analysis'
        
        # Check cache
        if self._is_cache_valid(cache_key):
            return self._template_cache[cache_key]
        
        try:
            template_data = self.generator.load_template_data()
            
            # analysis
            analysis = self._analyze_template_data(template_data)
            
            # Cache result
            self._template_cache[cache_key] = analysis
            self._cache_timestamps[cache_key] = datetime.now().timestamp()
            
            return analysis
            
        except Exception as e:
            logger.exception(f"Error analyzing template: {e}")
            raise
    
    def get_available_base_years(self) -> Dict[str, Any]:
        """Get available base years with analysis"""
        cache_key = 'base_years'
        
        if self._is_cache_valid(cache_key):
            return self._template_cache[cache_key]
        
        try:
            template_data = self.generator.load_template_data()
            historical_data = template_data['historical_demand']
            
            # Get complete years
            available_years = self.generator.get_available_base_years(historical_data)
            
            # Analyze each year
            year_analysis = {}
            for year in available_years:
                try:
                    year_data = historical_data[historical_data['financial_year'] == year]
                    if year_data.empty:
                        continue
                        
                    # Safe calculations with error handling
                    total_records = len(year_data)
                    
                    # Date range
                    try:
                        start_date = year_data['ds'].min()
                        end_date = year_data['ds'].max()
                        date_range = {
                            'start': start_date.isoformat() if pd.notna(start_date) else None,
                            'end': end_date.isoformat() if pd.notna(end_date) else None
                        }
                    except Exception as e:
                        logger.warning(f"Error getting date range for year {year}: {e}")
                        date_range = {'start': None, 'end': None}
                    
                    # Data quality metrics with safe calculations
                    try:
                        demand_series = year_data['demand']
                        missing_values = int(demand_series.isna().sum())
                        zero_values = int((demand_series == 0).sum())
                        negative_values = int((demand_series < 0).sum())
                        
                        # Only calculate stats if we have valid data
                        if not demand_series.empty and demand_series.notna().sum() > 0:
                            valid_demand = demand_series.dropna()
                            peak = float(valid_demand.max()) if len(valid_demand) > 0 else 0.0
                            min_val = float(valid_demand.min()) if len(valid_demand) > 0 else 0.0
                            avg = float(valid_demand.mean()) if len(valid_demand) > 0 else 0.0
                            std = float(valid_demand.std()) if len(valid_demand) > 1 else 0.0
                        else:
                            peak = min_val = avg = std = 0.0
                            
                    except Exception as e:
                        logger.warning(f"Error calculating stats for year {year}: {e}")
                        missing_values = zero_values = negative_values = 0
                        peak = min_val = avg = std = 0.0
                    
                    year_analysis[year] = {
                        'total_records': total_records,
                        'date_range': date_range,
                        'data_quality': {
                            'missing_values': missing_values,
                            'zero_values': zero_values,
                            'negative_values': negative_values,
                            'peak': peak,
                            'min': min_val,
                            'avg': avg,
                            'std': std
                        }
                    }
                    
                except Exception as e:
                    logger.error(f"Error analyzing year {year}: {e}")
                    # Provide minimal data for this year
                    year_analysis[year] = {
                        'total_records': 0,
                        'date_range': {'start': None, 'end': None},
                        'data_quality': {
                            'missing_values': 0,
                            'zero_values': 0,
                            'negative_values': 0,
                            'peak': 0.0,
                            'min': 0.0,
                            'avg': 0.0,
                            'std': 0.0
                        }
                    }
            
            result = {
                'available_years': available_years,
                'year_analysis': year_analysis,
                'recommended_year': available_years[-1] if available_years else None,
                'total_years': len(available_years)
            }
            
            # Cache result
            self._template_cache[cache_key] = result
            self._cache_timestamps[cache_key] = datetime.now().timestamp()
            
            return result
            
        except Exception as e:
            logger.exception(f"Error getting base years: {e}")
            # Return a safe fallback
            return {
                'available_years': [],
                'year_analysis': {},
                'recommended_year': None,
                'total_years': 0,
                'error': str(e)
            }
    
    def get_scenario_analysis(self, scenario_name: str) -> Dict[str, Any]:
        """Get comprehensive scenario analysis"""
        cache_key = f'scenario_{scenario_name}'
        
        if self._is_cache_valid(cache_key):
            return self._scenario_cache[cache_key]
        
        try:
            scenario_path = os.path.join(
                self.project_path, 'results', 'demand_projection',
                scenario_name, 'consolidated_results.csv'
            )
            
            if not os.path.exists(scenario_path):
                raise FileNotFoundError(f"Scenario file not found: {scenario_path}")
            
            # Load and analyze scenario
            scenario_df = pd.read_csv(scenario_path)
            analysis = self._analyze_scenario_data(scenario_df, scenario_name, scenario_path)
            
            # Cache result
            self._scenario_cache[cache_key] = analysis
            self._cache_timestamps[cache_key] = datetime.now().timestamp()
            
            return analysis
            
        except Exception as e:
            logger.exception(f"Error analyzing scenario {scenario_name}: {e}")
            raise
    
    def generate_base_profile_preview(self, base_year: int) -> Dict[str, Any]:
        """Generate base profile preview"""
        try:
            template_data = self.generator.load_template_data()
            historical_data = template_data['historical_demand']
            
            # Extract and analyze profiles for base year
            profiles = self.generator.extract_base_profiles(historical_data, base_year)
            
            # analysis
            preview_data = {
                'base_year': base_year,
                'total_patterns': len(profiles),
                'patterns_by_type': {
                    'weekday_patterns': len(profiles[profiles['is_special_day'] == 0]),
                    'weekend_holiday_patterns': len(profiles[profiles['is_special_day'] == 1])
                },
                'monthly_statistics': {},
                'sample_patterns': [],
                'data_quality': {
                    'missing_hours': 0,
                    'duplicate_hours': 0,
                    'outlier_values': 0
                }
            }
            
            # Monthly analysis
            for month in range(1, 13):
                month_profiles = profiles[profiles['financial_month'] == month]
                if not month_profiles.empty:
                    preview_data['monthly_statistics'][f'month_{month}'] = {
                        'peak_fraction': float(month_profiles['fraction'].max()),
                        'avg_fraction': float(month_profiles['fraction'].mean()),
                        'min_fraction': float(month_profiles['fraction'].min()),
                        'total_patterns': len(month_profiles)
                    }
            
            # Sample patterns for visualization
            sample_months = [1, 4, 7, 10]  # Representative months
            for month in sample_months:
                month_data = profiles[profiles['financial_month'] == month]
                if not month_data.empty:
                    weekday_pattern = month_data[month_data['is_special_day'] == 0]
                    weekend_pattern = month_data[month_data['is_special_day'] == 1]
                    
                    preview_data['sample_patterns'].append({
                        'month': month,
                        'month_name': ['', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 
                                     'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar'][month],
                        'weekday': weekday_pattern[['hour', 'fraction']].to_dict('records') if not weekday_pattern.empty else [],
                        'weekend': weekend_pattern[['hour', 'fraction']].to_dict('records') if not weekend_pattern.empty else []
                    })
            
            return preview_data
            
        except Exception as e:
            logger.exception(f"Error generating preview for base year {base_year}: {e}")
            raise
    
    def validate_generation_request(self, data: Dict, profile_type: str) -> Dict[str, Any]:
        """Comprehensive validation for generation requests"""
        errors = []
        warnings = []
        
        try:
            # Common validations
            if profile_type == 'base_profile':
                base_year = data.get('base_year')
                if not base_year or not isinstance(base_year, int):
                    errors.append("Valid base year is required")
                elif base_year < 2000 or base_year > 2030:
                    errors.append("Base year must be between 2000 and 2030")
            
            # STL specific validations
            elif profile_type == 'stl_profile':
                # STL parameters validation
                stl_params = data.get('stl_params', {})
                if stl_params:
                    period = stl_params.get('period')
                    if period and (period < 24 or period > 8760):
                        errors.append("STL period must be between 24 and 8760 hours")
                    
                    seasonal = stl_params.get('seasonal')
                    if seasonal and (seasonal < 3 or seasonal > 100):
                        errors.append("STL seasonal parameter must be between 3 and 100")
                
                # Load factor improvement validation
                lf_improvement = data.get('lf_improvement')
                if lf_improvement and lf_improvement.get('enabled'):
                    target_year = lf_improvement.get('target_year')
                    improvement_percent = lf_improvement.get('improvement_percent')
                    
                    if not target_year or target_year < 2025 or target_year > 2050:
                        errors.append("Load factor target year must be between 2025 and 2050")
                    
                    if not improvement_percent or improvement_percent <= 0 or improvement_percent > 50:
                        errors.append("Load factor improvement must be between 0 and 50 percent")
            
            # Year range validation
            start_fy = data.get('start_fy')
            end_fy = data.get('end_fy')
            
            if not start_fy or not isinstance(start_fy, int):
                errors.append("Valid start financial year is required")
            if not end_fy or not isinstance(end_fy, int):
                errors.append("Valid end financial year is required")
            
            if start_fy and end_fy:
                if int(start_fy) >= int(end_fy):
                    errors.append("Start financial year must be before end financial year")
                if int(end_fy) - int(start_fy) > 50:
                    warnings.append("Long forecast period may affect accuracy")
            
            # Demand source validation
            demand_source = data.get('demand_source')
            if demand_source not in ['template', 'scenario']:
                errors.append("Demand source must be 'template' or 'scenario'")
            
            if demand_source == 'scenario':
                scenario_name = data.get('scenario_name')
                if not scenario_name:
                    errors.append("Scenario name is required when using scenario data")
                else:
                    # Check if scenario exists
                    scenario_path = os.path.join(
                        self.project_path, 'results', 'demand_projection',
                        scenario_name, 'consolidated_results.csv'
                    )
                    if not os.path.exists(scenario_path):
                        errors.append(f"Scenario '{scenario_name}' not found")
            
            # Frequency validation
            frequency = data.get('frequency', 'hourly')
            if frequency not in ['hourly', '15min', '30min', 'daily']:
                errors.append("Invalid frequency specified")
            
            # Custom name validation
            custom_name = data.get('custom_name', '').strip()
            if custom_name:
                if len(custom_name) < 2:
                    errors.append("Custom name must be at least 2 characters")
                if len(custom_name) > 50:
                    errors.append("Custom name must be less than 50 characters")
                # Check for invalid characters
                invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
                if any(char in custom_name for char in invalid_chars):
                    errors.append("Custom name contains invalid characters")
            
            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings
            }
            
        except Exception as e:
            logger.exception(f"Error validating generation request: {e}")
            return {
                'valid': False,
                'errors': [f"Validation error: {str(e)}"],
                'warnings': warnings
            }

    def get_base_year_detailed_info(self, year: int) -> Dict[str, Any]:
        """Get detailed information about a specific base year"""
        try:
            template_data = self.generator.load_template_data()
            historical_data = template_data['historical_demand']
            
            # Filter for specific year
            year_data = historical_data[historical_data['financial_year'] == year]
            
            if year_data.empty:
                raise ValueError(f"No data found for year {year}")
            
            # Safe calculations
            try:
                start_date = year_data['ds'].min()
                end_date = year_data['ds'].max()
                date_range = {
                    'start': start_date.isoformat() if pd.notna(start_date) else None,
                    'end': end_date.isoformat() if pd.notna(end_date) else None
                }
            except Exception:
                date_range = {'start': None, 'end': None}
            
            try:
                demand_series = year_data['demand']
                data_quality = {
                    'missing_values': int(demand_series.isna().sum()),
                    'zero_values': int((demand_series == 0).sum()),
                    'negative_values': int((demand_series < 0).sum())
                }
                
                # Only calculate stats if we have valid data
                if not demand_series.empty and demand_series.notna().sum() > 0:
                    valid_demand = demand_series.dropna()
                    demand_stats = {
                        'peak': float(valid_demand.max()) if len(valid_demand) > 0 else 0.0,
                        'min': float(valid_demand.min()) if len(valid_demand) > 0 else 0.0,
                        'avg': float(valid_demand.mean()) if len(valid_demand) > 0 else 0.0,
                        'std': float(valid_demand.std()) if len(valid_demand) > 1 else 0.0
                    }
                else:
                    demand_stats = {'peak': 0.0, 'min': 0.0, 'avg': 0.0, 'std': 0.0}
                    
            except Exception as e:
                logger.warning(f"Error calculating stats for year {year}: {e}")
                data_quality = {'missing_values': 0, 'zero_values': 0, 'negative_values': 0}
                demand_stats = {'peak': 0.0, 'min': 0.0, 'avg': 0.0, 'std': 0.0}
            
            # Calculate statistics
            info = {
                'year': year,
                'total_records': len(year_data),
                'date_range': date_range,
                'data_quality': data_quality,
                'demand_stats': demand_stats
            }
            
            # Create pattern preview for heatmap
            try:
                pattern_preview = self._create_pattern_preview(year_data)
                if pattern_preview:
                    info['pattern_preview'] = pattern_preview
            except Exception as e:
                logger.warning(f"Error creating pattern preview for year {year}: {e}")
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting base year info: {e}")
            raise

    def get_historical_data_summary(self) -> Dict[str, Any]:
        """Get summary of all historical data"""
        try:
            template_data = self.generator.load_template_data()
            historical_data = template_data['historical_demand']
            
            if historical_data.empty:
                return {
                    'total_years': 0,
                    'total_records': 0,
                    'avg_load_factor': 0,
                    'peak_demand': 0,
                    'date_range': {'start': None, 'end': None},
                    'yearly_stats': []
                }
            
            # Safe calculations with error handling
            try:
                total_years = len(historical_data['financial_year'].unique())
                total_records = len(historical_data)
                
                # Date range calculation
                try:
                    start_date = historical_data['ds'].min()
                    end_date = historical_data['ds'].max()
                    date_range = {
                        'start': start_date.isoformat() if pd.notna(start_date) else None,
                        'end': end_date.isoformat() if pd.notna(end_date) else None
                    }
                except Exception:
                    date_range = {'start': None, 'end': None}
                
                # Demand statistics
                try:
                    demand_series = historical_data['demand'].dropna()
                    if len(demand_series) > 0:
                        peak_demand = float(demand_series.max())
                        avg_demand = float(demand_series.mean())
                        avg_load_factor = (avg_demand / peak_demand * 100) if peak_demand > 0 else 0
                    else:
                        peak_demand = avg_load_factor = 0
                except Exception as e:
                    logger.warning(f"Error calculating demand stats: {e}")
                    peak_demand = avg_load_factor = 0
                
                # Yearly statistics
                try:
                    yearly_stats = self._calculate_yearly_stats(historical_data)
                except Exception as e:
                    logger.warning(f"Error calculating yearly stats: {e}")
                    yearly_stats = []
                
                summary = {
                    'total_years': total_years,
                    'total_records': total_records,
                    'date_range': date_range,
                    'avg_load_factor': float(avg_load_factor),
                    'peak_demand': float(peak_demand),
                    'yearly_stats': yearly_stats
                }
                
                return summary
                
            except Exception as e:
                logger.error(f"Error in summary calculations: {e}")
                return {
                    'total_years': 0,
                    'total_records': 0,
                    'avg_load_factor': 0,
                    'peak_demand': 0,
                    'date_range': {'start': None, 'end': None},
                    'yearly_stats': [],
                    'error': str(e)
                }
            
        except Exception as e:
            logger.error(f"Error getting historical summary: {e}")
            return {
                'total_years': 0,
                'total_records': 0,
                'avg_load_factor': 0,
                'peak_demand': 0,
                'date_range': {'start': None, 'end': None},
                'yearly_stats': [],
                'error': str(e)
            }

    def _create_pattern_preview(self, year_data: pd.DataFrame) -> Dict[str, Any]:
        """Create pattern data for heatmap visualization"""
        try:
            # Check if we have the required columns
            if 'financial_month' not in year_data.columns or 'hour' not in year_data.columns or 'demand' not in year_data.columns:
                logger.warning("Missing required columns for pattern preview")
                return None
                
            # Group by month and hour - use safe aggregation
            pattern_data = year_data.groupby(['financial_month', 'hour'])['demand'].mean().reset_index()
            
            if pattern_data.empty:
                logger.warning("No pattern data available")
                return None
            
            # Pivot for heatmap
            try:
                heatmap_matrix = pattern_data.pivot(
                    index='financial_month', 
                    columns='hour', 
                    values='demand'
                )
                
                # Fill NaN values with 0
                heatmap_matrix = heatmap_matrix.fillna(0)
                
                # Convert to format for Plotly
                return {
                    'values': heatmap_matrix.values.tolist(),
                    'hours': list(range(24)),
                    'months': ['Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 
                            'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar']
                }
            except Exception as e:
                logger.warning(f"Error creating pivot table: {e}")
                return None
            
        except Exception as e:
            logger.error(f"Error creating pattern preview: {e}")
            return None

    def _calculate_yearly_stats(self, historical_data: pd.DataFrame) -> List[Dict]:
        """Calculate statistics for each year"""
        yearly_stats = []
        
        try:
            unique_years = sorted(historical_data['financial_year'].unique())
            
            for year in unique_years:
                try:
                    year_data = historical_data[historical_data['financial_year'] == year]
                    
                    if year_data.empty:
                        continue
                    
                    # Safe calculations
                    demand_series = year_data['demand'].dropna()
                    
                    if len(demand_series) == 0:
                        continue
                    
                    records = len(year_data)
                    peak = float(demand_series.max())
                    avg = float(demand_series.mean())
                    load_factor = (avg / peak * 100) if peak > 0 else 0
                    
                    stats = {
                        'year': int(year),
                        'records': records,
                        'peak': peak,
                        'avg': avg,
                        'load_factor': float(load_factor)
                    }
                    
                    yearly_stats.append(stats)
                    
                except Exception as e:
                    logger.warning(f"Error calculating stats for year {year}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error in yearly stats calculation: {e}")
        
        return yearly_stats

    def generate_base_profile(self, config: Dict) -> Dict[str, Any]:
        """Generate base profile with error handling"""
        try:
            # Load template data
            template_data = self.generator.load_template_data()
            historical_data = template_data['historical_demand']
            
            # Prepare demand scenarios
            if config['demand_source'] == 'template':
                demand_scenarios = template_data['total_demand']
            else:
                scenario_path = os.path.join(
                    self.project_path, 'results', 'demand_projection',
                    config['scenario_name'], 'consolidated_results.csv'
                )
                demand_scenarios = self.generator.load_scenario_data(scenario_path)
            
            # Prepare constraints
            constraints = self._prepare_constraints(config, template_data)
            
            # Generate forecast
            result = self.generator.generate_base_profile_forecast(
                historical_data=historical_data,
                demand_scenarios=demand_scenarios,
                base_year=int(config['base_year']),
                start_fy=int(config['start_fy']),
                end_fy=int(config['end_fy']),
                frequency=config.get('frequency', 'hourly'),
                constraints=constraints
            )
            
            if result['status'] == 'success':
                # saving with custom name
                custom_name = config.get('custom_name', '').strip()
                profile_id = None
                
                if custom_name:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    safe_name = self._sanitize_name(custom_name)
                    profile_id = f"{safe_name}_{timestamp}"
                
                save_info = self.generator.save_forecast(result['data'], profile_id=profile_id)
                
                # Clear cache
                self._clear_profile_cache()
                
                forecast_df = result['data']['forecast']

                return {
                    'success': True,
                    'data': {
                        'save_info': save_info,
                        'profile_id': save_info['profile_id'],
                        'generation_config': config,
                        'summary': self._create_generation_summary(result['data']),
                        'forecast': forecast_df.head(720).to_dict('records') # Sample first 720 records (30 days of hourly data)
                    }
                }
            else:
                return {'success': False, 'error': result['message']}
                
        except Exception as e:
            logger.exception(f"Error generating base profile: {e}")
            return {'success': False, 'error': str(e)}
    
    def generate_stl_profile(self, config: Dict) -> Dict[str, Any]:
        """Generate STL profile with advanced configuration and load factor improvement"""
        try:
            # Load template data
            template_data = self.generator.load_template_data()
            historical_data = template_data['historical_demand']
            
            # Prepare demand scenarios
            if config['demand_source'] == 'template':
                demand_scenarios = template_data['total_demand']
            else:
                scenario_path = os.path.join(
                    self.project_path, 'results', 'demand_projection',
                    config['scenario_name'], 'consolidated_results.csv'
                )
                demand_scenarios = self.generator.load_scenario_data(scenario_path)
            
            # Prepare constraints and STL parameters
            constraints = self._prepare_constraints(config, template_data)
            stl_params = config.get('stl_params', {})
            
            # Prepare load factor improvement parameters
            lf_improvement = None
            if config.get('lf_improvement') and config['lf_improvement'].get('enabled'):
                lf_improvement = config['lf_improvement']
                logger.info(f"Load factor improvement enabled: {lf_improvement}")
            
            # Generate forecast with optimized STL
            result = self.generator.generate_stl_forecast(
                historical_data=historical_data,
                demand_scenarios=demand_scenarios,
                start_fy=int(config['start_fy']),
                end_fy=int(config['end_fy']),
                frequency=config.get('frequency', 'hourly'),
                stl_params=stl_params,
                constraints=constraints,
                lf_improvement=lf_improvement
            )
            
            if result['status'] == 'success':
                # saving with custom name
                custom_name = config.get('custom_name', '').strip()
                profile_id = None
                
                if custom_name:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    safe_name = self._sanitize_name(custom_name)
                    profile_id = f"{safe_name}_{timestamp}"
                
                save_info = self.generator.save_forecast(result['data'], profile_id=profile_id)
                
                # Clear cache
                self._clear_profile_cache()
                
                forecast_df = result['data']['forecast']
                
                return {
                    'success': True,
                    'data': {
                        'save_info': save_info,
                        'profile_id': save_info['profile_id'],
                        'generation_config': config,
                        'summary': self._create_generation_summary(result['data']),
                        'stl_components': result['data'].get('stl_components', {}),
                        'load_factor_improvement': result['data'].get('load_factor_improvement'),
                        'validation': result['data'].get('validation', {}),
                        'forecast': forecast_df.head(720).to_dict('records') # Sample first 720 records
                    }
                }
            else:
                return {'success': False, 'error': result['message']}
                
        except Exception as e:
            logger.exception(f"Error generating STL profile: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_saved_profiles_with_metadata(self) -> Dict[str, Any]:
        """Get saved profiles with metadata"""
        try:
            profiles = self.generator.get_saved_profiles()
            
            # Enhance with additional metadata
            enhanced_profiles = []
            for profile in profiles:
                profile = profile.copy()
                
                # Add file analysis
                csv_path = os.path.join(
                    self.project_path, 'results', 'load_profiles',
                    f"{profile['profile_id']}.csv"
                )
                
                if os.path.exists(csv_path):
                    file_info = get_file_info(csv_path)
                    profile['file_info'] = file_info
                    
                    # Quick data analysis
                    try:
                        df = pd.read_csv(csv_path, nrows=1000)  # Sample for quick analysis
                        profile['data_preview'] = {
                            'total_records': len(df),
                            'columns': df.columns.tolist(),
                            'date_range': {
                                'start': df['datetime'].min() if 'datetime' in df.columns else None,
                                'end': df['datetime'].max() if 'datetime' in df.columns else None
                            }
                        }
                    except Exception:
                        pass
                
                enhanced_profiles.append(profile)
            
            # Sort by creation date (newest first)
            enhanced_profiles.sort(
                key=lambda x: x.get('generated_at', ''),
                reverse=True
            )
            
            return {
                'profiles': enhanced_profiles,
                'total_count': len(enhanced_profiles),
                'by_method': self._group_profiles_by_method(enhanced_profiles)
            }
            
        except Exception as e:
            logger.exception(f"Error getting saved profiles: {e}")
            return {'profiles': [], 'total_count': 0, 'error': str(e)}
    
    def get_profile_detailed_data(self, profile_id: str) -> Dict[str, Any]:
        """Get detailed profile data with comprehensive analysis"""
        cache_key = f'profile_detail_{profile_id}'
        
        if self._is_cache_valid(cache_key):
            return self._profile_cache[cache_key]
        
        try:
            # Get basic profile data
            profile_data = self.generator.get_profile_data(profile_id)
            
            # analysis
            detailed_data = self._analyze_profile_data(profile_data, profile_id)
            
            # Cache result
            self._profile_cache[cache_key] = detailed_data
            self._cache_timestamps[cache_key] = datetime.now().timestamp()
            
            return detailed_data
            
        except Exception as e:
            logger.exception(f"Error getting detailed profile data: {e}")
            raise
    
    def analyze_profile(self, profile_id: str) -> Dict[str, Any]:
        """Comprehensive profile analysis"""
        try:
            csv_path = os.path.join(
                self.project_path, 'results', 'load_profiles',
                f"{profile_id}.csv"
            )
            
            if not os.path.exists(csv_path):
                raise FileNotFoundError(f"Profile not found: {profile_id}")
            
            # Load profile data
            df = pd.read_csv(csv_path)
            
            # Comprehensive analysis
            analysis = {
                'profile_id': profile_id,
                'basic_stats': self._calculate_basic_stats(df),
                'temporal_analysis': self._analyze_temporal_patterns(df),
                'load_factor_analysis': self._analyze_load_factors(df),
                'peak_analysis': self._analyze_peaks(df),
                'seasonality_analysis': self._analyze_seasonality(df),
                'data_quality': self._assess_data_quality(df)
            }
            
            return analysis
            
        except Exception as e:
            logger.exception(f"Error analyzing profile {profile_id}: {e}")
            raise
    
    def compare_profiles(self, profile_ids: List[str]) -> Dict[str, Any]:
        """Compare multiple profiles with detailed analysis"""
        try:
            profiles_data = {}
            
            # Load all profiles
            for profile_id in profile_ids:
                csv_path = os.path.join(
                    self.project_path, 'results', 'load_profiles',
                    f"{profile_id}.csv"
                )
                
                if os.path.exists(csv_path):
                    profiles_data[profile_id] = pd.read_csv(csv_path)
            
            if len(profiles_data) < 2:
                raise ValueError("Need at least 2 valid profiles for comparison")
            
            # Perform comparison analysis
            comparison = {
                'profile_ids': list(profiles_data.keys()),
                'comparison_summary': self._compare_profile_summaries(profiles_data),
                'peak_comparison': self._compare_peaks(profiles_data),
                'load_factor_comparison': self._compare_load_factors(profiles_data),
                'correlation_analysis': self._analyze_profile_correlations(profiles_data),
                'temporal_comparison': self._compare_temporal_patterns(profiles_data)
            }
            
            return comparison
            
        except Exception as e:
            logger.exception(f"Error comparing profiles: {e}")
            raise
    
    def upload_and_validate_template(self, file: FileStorage) -> Dict[str, Any]:
        """Upload and validate template with comprehensive checks"""
        try:
            # Save file
            filename = 'load_curve_template.xlsx'
            file_path = os.path.join(self.project_path, 'inputs', filename)
            
            # Ensure inputs directory exists
            ensure_directory(os.path.dirname(file_path))
            
            file.save(file_path)
            
            # Validate template structure
            try:
                # Create new generator instance to test
                test_generator = LoadProfileGenerator(self.project_path)
                template_data = test_generator.load_template_data()
                
                # Comprehensive validation
                validation_result = self._validate_template_structure(template_data)
                
                if validation_result['valid']:
                    # Clear template cache
                    self._clear_template_cache()
                    
                    return {
                        'success': True,
                        'data': {
                            'file_path': file_path,
                            'file_info': get_file_info(file_path),
                            'validation': validation_result,
                            'uploaded_at': datetime.now().isoformat()
                        }
                    }
                else:
                    # Remove invalid file
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    return {
                        'success': False,
                        'error': f"Template validation failed: {'; '.join(validation_result['errors'])}"
                    }
                    
            except Exception as validation_error:
                # Remove invalid file
                if os.path.exists(file_path):
                    os.remove(file_path)
                return {
                    'success': False,
                    'error': f"Template validation failed: {str(validation_error)}"
                }
                
        except Exception as e:
            logger.exception(f"Error uploading template: {e}")
            return {'success': False, 'error': str(e)}
    
    def delete_profile(self, profile_id: str) -> Dict[str, Any]:
        """Delete profile with comprehensive cleanup"""
        try:
            # Delete CSV file
            csv_path = os.path.join(
                self.project_path, 'results', 'load_profiles',
                f"{profile_id}.csv"
            )
            files_deleted = []
            
            if os.path.exists(csv_path):
                os.remove(csv_path)
                files_deleted.append('profile_data.csv')
            
            # Delete metadata file
            metadata_path = os.path.join(
                self.project_path, 'config',
                f"{profile_id}_metadata.json"
            )
            
            if os.path.exists(metadata_path):
                os.remove(metadata_path)
                files_deleted.append('metadata.json')
            
            # Clear cache
            self._clear_profile_cache()
            
            return {
                'success': True,
                'files_deleted': files_deleted,
                'deleted_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.exception(f"Error deleting profile {profile_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_profile_file_path(self, profile_id: str) -> Optional[str]:
        """Get secure file path for profile"""
        try:
            csv_path = os.path.join(
                self.project_path, 'results', 'load_profiles',
                f"{profile_id}.csv"
            )
            
            # Security check - ensure path is within project
            abs_project = os.path.abspath(self.project_path)
            abs_file = os.path.abspath(csv_path)
            
            if not abs_file.startswith(abs_project):
                return None
            
            return csv_path if os.path.exists(csv_path) else None
            
        except Exception as e:
            logger.exception(f"Error getting file path for {profile_id}: {e}")
            return None
    
    # Private helper methods
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is valid"""
        if cache_key not in self._cache_timestamps:
            return False
        
        age = datetime.now().timestamp() - self._cache_timestamps[cache_key]
        return age < self._cache_ttl
    
    def _clear_template_cache(self):
        """Clear template-related cache entries"""
        keys_to_clear = [k for k in self._template_cache.keys() if 'template' in k or 'base_years' in k]
        for key in keys_to_clear:
            self._template_cache.pop(key, None)
            self._cache_timestamps.pop(key, None)
    
    def _clear_profile_cache(self):
        """Clear profile-related cache entries"""
        keys_to_clear = [k for k in self._profile_cache.keys()]
        for key in keys_to_clear:
            self._profile_cache.pop(key, None)
            self._cache_timestamps.pop(key, None)
    
    def _get_available_scenarios(self) -> List[Dict[str, Any]]:
        """Get available demand scenarios with metadata"""
        try:
            scenarios_path = os.path.join(self.project_path, 'results', 'demand_projection')
            available_scenarios = []
            
            if os.path.exists(scenarios_path):
                for item in os.listdir(scenarios_path):
                    scenario_dir = os.path.join(scenarios_path, item)
                    if os.path.isdir(scenario_dir):
                        consolidated_file = os.path.join(scenario_dir, 'consolidated_results.csv')
                        if os.path.exists(consolidated_file):
                            available_scenarios.append({
                                'name': item,
                                'path': consolidated_file,
                                'file_info': get_file_info(consolidated_file)
                            })
            
            return available_scenarios
        except Exception as e:
            logger.exception(f"Error getting available scenarios: {e}")
            return []
    
    def _get_template_availability(self) -> Dict[str, Any]:
        """Check template availability with details"""
        template_path = os.path.join(self.project_path, 'inputs', 'load_curve_template.xlsx')
        
        return {
            'exists': os.path.exists(template_path),
            'path': template_path,
            'file_info': get_file_info(template_path) if os.path.exists(template_path) else None
        }
    
    def _analyze_template_data(self, template_data: Dict) -> Dict[str, Any]:
        """Comprehensive template data analysis"""
        return {
            'historical_data': {
                'records': len(template_data['historical_demand']),
                'date_range': {
                    'start': template_data['historical_demand']['ds'].min().isoformat(),
                    'end': template_data['historical_demand']['ds'].max().isoformat()
                },
                'available_years': sorted(template_data['historical_demand']['financial_year'].unique().tolist()),
                'complete_years': self.generator.get_available_base_years(template_data['historical_demand'])
            },
            'total_demand': {
                'years': len(template_data['total_demand']),
                'year_range': {
                    'start': int(template_data['total_demand']['Financial_Year'].min()),
                    'end': int(template_data['total_demand']['Financial_Year'].max())
                }
            },
            'constraints_available': {
                'monthly_peaks': template_data['monthly_peaks'] is not None or template_data['calculated_monthly_peaks'] is not None,
                'monthly_load_factors': template_data['monthly_load_factors'] is not None or template_data['calculated_load_factors'] is not None,
                'monthly_peaks_source': 'template' if template_data['monthly_peaks'] is not None else 'calculated' if template_data['calculated_monthly_peaks'] is not None else 'none',
                'load_factors_source': 'template' if template_data['monthly_load_factors'] is not None else 'calculated' if template_data['calculated_load_factors'] is not None else 'none'
            },
            'template_info': template_data['template_info']
        }
    
    def _analyze_scenario_data(self, scenario_df: pd.DataFrame, scenario_name: str, scenario_path: str) -> Dict[str, Any]:
        """Comprehensive scenario data analysis"""
        # Find demand column
        demand_cols = [col for col in scenario_df.columns 
                      if col in ['Total_On_Grid_Demand', 'Total', 'Total_Demand']]
        
        if not demand_cols:
            raise ValueError("No total demand column found in scenario")
        
        demand_col = demand_cols[0]
        
        return {
            'scenario_name': scenario_name,
            'file_path': scenario_path,
            'file_info': get_file_info(scenario_path),
            'data_summary': {
                'total_years': len(scenario_df),
                'year_range': {
                    'start': int(scenario_df['Year'].min()),
                    'end': int(scenario_df['Year'].max())
                },
                'demand_range': {
                    'min': float(scenario_df[demand_col].min()),
                    'max': float(scenario_df[demand_col].max()),
                    'unit': 'kWh'
                },
                'demand_column': demand_col,
                'growth_analysis': self._analyze_demand_growth(scenario_df, demand_col)
            },
            'years_data': scenario_df[['Year', demand_col]].to_dict('records')
        }
    
    def _analyze_demand_growth(self, df: pd.DataFrame, demand_col: str) -> Dict[str, Any]:
        """Analyze demand growth patterns"""
        try:
            df_sorted = df.sort_values('Year')
            demand_values = df_sorted[demand_col].values
            
            # Calculate year-over-year growth
            growth_rates = []
            for i in range(1, len(demand_values)):
                if demand_values[i-1] != 0:
                    growth_rate = ((demand_values[i] - demand_values[i-1]) / demand_values[i-1]) * 100
                    growth_rates.append(growth_rate)
            
            if growth_rates:
                return {
                    'average_growth_rate': float(np.mean(growth_rates)),
                    'max_growth_rate': float(np.max(growth_rates)),
                    'min_growth_rate': float(np.min(growth_rates)),
                    'growth_volatility': float(np.std(growth_rates))
                }
            else:
                return {'average_growth_rate': 0, 'max_growth_rate': 0, 'min_growth_rate': 0, 'growth_volatility': 0}
                
        except Exception as e:
            logger.debug(f"Error analyzing demand growth: {e}")
            return {}
    
    def _prepare_constraints(self, config: Dict, template_data: Dict) -> Optional[Dict]:
        """Prepare constraints for profile generation"""
        apply_monthly_peaks = config.get('apply_monthly_peaks', False)
        apply_load_factors = config.get('apply_load_factors', False)
        
        if not apply_monthly_peaks and not apply_load_factors:
            return None
        
        constraints = {}
        
        if apply_monthly_peaks:
            if template_data['monthly_peaks'] is not None:
                constraints['monthly_peaks'] = template_data['monthly_peaks']
            else:
                constraints['calculated_monthly_peaks'] = template_data['calculated_monthly_peaks']
        
        if apply_load_factors:
            if template_data['monthly_load_factors'] is not None:
                constraints['monthly_load_factors'] = template_data['monthly_load_factors']
            else:
                constraints['calculated_load_factors'] = template_data['calculated_load_factors']
        
        return constraints
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize custom name for file system"""
        # Remove invalid characters and limit length
        safe_name = ''.join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        return safe_name[:30]  # Limit length
    
    def _create_generation_summary(self, data: Dict) -> Dict[str, Any]:
        """Create summary of generation results"""
        try:
            forecast_data = data.get('forecast', [])
            
            return {
                'method': data.get('method', 'unknown'),
                'start_fy': data.get('start_fy'),
                'end_fy': data.get('end_fy'),
                'frequency': data.get('frequency', 'hourly'),
                'total_records': len(forecast_data),
                'validation': data.get('validation', {}),
                'stl_components': data.get('stl_components', {}),
                'load_factor_improvement': data.get('load_factor_improvement')
            }
        except Exception:
            return {}
    
    def _group_profiles_by_method(self, profiles: List[Dict]) -> Dict[str, int]:
        """Group profiles by generation method"""
        method_counts = {}
        for profile in profiles:
            method = profile.get('method', 'unknown')
            method_counts[method] = method_counts.get(method, 0) + 1
        return method_counts
    
    def _validate_template_structure(self, template_data: Dict) -> Dict[str, Any]:
        """Validate template structure comprehensively"""
        errors = []
        warnings = []
        
        # Check required data
        if template_data['historical_demand'].empty:
            errors.append("No historical demand data found")
        
        if template_data['total_demand'].empty:
            errors.append("No total demand data found")
        
        # Check data quality
        historical_data = template_data['historical_demand']
        if not historical_data.empty:
            # Check for required columns
            required_cols = ['ds', 'demand', 'financial_year']
            missing_cols = [col for col in required_cols if col not in historical_data.columns]
            if missing_cols:
                errors.append(f"Missing required columns: {missing_cols}")
            
            # Check data completeness
            if 'demand' in historical_data.columns:
                null_demands = historical_data['demand'].isna().sum()
                if null_demands > len(historical_data) * 0.1:  # More than 10% missing
                    warnings.append(f"High number of missing demand values: {null_demands}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    # Analysis helper methods (placeholders for future implementation)
    def _analyze_profile_data(self, profile_data: Dict, profile_id: str) -> Dict[str, Any]:
        """Detailed analysis of profile data"""
        return profile_data
    
    def _calculate_basic_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate basic statistics for profile"""
        return {}
    
    def _analyze_temporal_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze temporal patterns in profile"""
        return {}
    
    def _analyze_load_factors(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze load factors"""
        return {}
    
    def _analyze_peaks(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze peak patterns"""
        return {}
    
    def _analyze_seasonality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze seasonal patterns"""
        return {}
    
    def _assess_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Assess data quality metrics"""
        return {}
    
    def _compare_profile_summaries(self, profiles_data: Dict) -> Dict[str, Any]:
        """Compare profile summaries"""
        return {}
    
    def _compare_peaks(self, profiles_data: Dict) -> Dict[str, Any]:
        """Compare peak patterns across profiles"""
        return {}
    
    def _compare_load_factors(self, profiles_data: Dict) -> Dict[str, Any]:
        """Compare load factors across profiles"""
        return {}
    
    def _analyze_profile_correlations(self, profiles_data: Dict) -> Dict[str, Any]:
        """Analyze correlations between profiles"""
        return {}
    
    def _compare_temporal_patterns(self, profiles_data: Dict) -> Dict[str, Any]:
        """Compare temporal patterns across profiles"""
        return {}