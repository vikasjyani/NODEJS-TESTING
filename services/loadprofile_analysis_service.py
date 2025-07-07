# services/loadprofile_analysis_service.py
"""
Load Profile Analysis Service Layer
Handles all business logic for load profile analysis, comparison, and reporting
"""
import os
import json
import pandas as pd
import numpy as np
import logging
import tempfile
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from utils.load_profile_analyzer import LoadProfileAnalyzer
from utils.constants import UNIT_FACTORS, VALIDATION_RULES
from utils.helpers import get_file_info, ensure_directory
from utils.error_handlers import ValidationError, ProcessingError, ResourceNotFoundError

logger = logging.getLogger(__name__)

class LoadProfileAnalysisService:
    """
    Service layer for load profile analysis operations
    Handles comprehensive analytics, comparison, and reporting
    """
    
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.analyzer = LoadProfileAnalyzer(Path(project_path))
        
        # Cache for expensive operations
        self._analysis_cache = {}
        self._profile_cache = {}
        self._cache_timestamps = {}
        self._cache_ttl = 300  # 5 minutes
        
        # Analysis configuration
        self.supported_analysis_types = [
            'overview', 'peak_analysis', 'weekday_weekend', 
            'seasonal', 'monthly', 'duration_curve', 'heatmap',
            'load_factor', 'demand_profile', 'variability'
        ]
        
        self.export_formats = ['csv', 'xlsx', 'json']
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get all data needed for dashboard rendering"""
        try:
            # Get available profiles with metadata
            profiles = self.get_available_profiles()
            
            # Calculate summary statistics
            total_profiles = len(profiles)
            total_size_mb = sum(p.get('file_info', {}).get('size_mb', 0) for p in profiles)
            
            # Get method distribution
            methods = [p.get('method', 'Unknown') for p in profiles]
            method_counts = {method: methods.count(method) for method in set(methods)}
            
            # Get unit distribution
            units = [p.get('units', 'kW') for p in profiles]
            unit_counts = {unit: units.count(unit) for unit in set(units)}
            
            # Calculate date range across all profiles
            date_ranges = []
            for profile in profiles:
                if profile.get('start_fy') and profile.get('end_fy'):
                    date_ranges.extend([profile['start_fy'], profile['end_fy']])
            
            overall_date_range = {
                'start': min(date_ranges) if date_ranges else None,
                'end': max(date_ranges) if date_ranges else None
            }
            
            return {
                'project_name': os.path.basename(self.project_path),
                'available_profiles': profiles,
                'total_profiles': total_profiles,
                'total_size_mb': round(total_size_mb, 2),
                'method_distribution': method_counts,
                'unit_distribution': unit_counts,
                'overall_date_range': overall_date_range,
                'available_units': list(UNIT_FACTORS.keys()),
                'analysis_types': [
                    {'id': 'overview', 'name': 'Overview', 'description': 'Complete time series view with peak/min analysis'},
                    {'id': 'peak_analysis', 'name': 'Peak Analysis', 'description': 'Peak vs off-peak day comparison'},
                    {'id': 'weekday_weekend', 'name': 'Day Type Analysis', 'description': 'Weekday vs weekend patterns'},
                    {'id': 'seasonal', 'name': 'Seasonal Analysis', 'description': 'Seasonal load variations and patterns'},
                    {'id': 'monthly', 'name': 'Monthly Analysis', 'description': 'Monthly load patterns and trends'},
                    {'id': 'duration_curve', 'name': 'Duration Curve', 'description': 'Load duration curve analysis'},
                    {'id': 'heatmap', 'name': 'Pattern Heatmap', 'description': 'Weekly load pattern visualization'},
                    {'id': 'load_factor', 'name': 'Load Factor Analysis', 'description': 'Load factor metrics and trends'},
                    {'id': 'demand_profile', 'name': 'Demand Profile', 'description': 'Detailed demand pattern analysis'},
                    {'id': 'variability', 'name': 'Variability Analysis', 'description': 'Load variability and volatility metrics'}
                ],
                'seasons': ['All', 'Summer', 'Monsoon', 'Winter'],
                'comparison_types': [
                    {'id': 'overview', 'name': 'Overview Metrics', 'description': 'Basic load statistics comparison'},
                    {'id': 'statistical', 'name': 'Statistical Comparison', 'description': 'Detailed statistical analysis'},
                    {'id': 'patterns', 'name': 'Pattern Analysis', 'description': 'Temporal pattern comparison'},
                    {'id': 'performance', 'name': 'Performance Metrics', 'description': 'Load factor and efficiency comparison'}
                ]
            }
            
        except Exception as e:
            logger.exception(f"Error getting dashboard data: {e}")
            return {'error': str(e)}
    
    def get_available_profiles(self) -> List[Dict[str, Any]]:
        """Get all available profiles withmetadata"""
        cache_key = 'available_profiles'
        
        if self._is_cache_valid(cache_key):
            return self._profile_cache[cache_key]
        
        try:
            profiles = self.analyzer.get_available_profiles()
            
            # Enhance with additional metadata
            profiles = []
            for profile in profiles:
                profile = profile.copy()
                
                # Add validation status
                try:
                    validation = self.quick_validate_profile(profile['profile_id'])
                    profile['validation'] = validation
                except Exception as validation_error:
                    profile['validation'] = {
                        'valid': False,
                        'error': str(validation_error)
                    }
                
                # Add file analysis
                csv_path = os.path.join(
                    self.project_path, 'results', 'load_profiles',
                    f"{profile['profile_id']}.csv"
                )
                
                if os.path.exists(csv_path):
                    file_info = get_file_info(csv_path)
                    profile['file_info'] = file_info
                    
                    # Quick data preview
                    try:
                        df_preview = pd.read_csv(csv_path, nrows=100)
                        profile['data_preview'] = {
                            'total_records': len(df_preview),
                            'columns': df_preview.columns.tolist(),
                            'has_demand_data': 'demand' in df_preview.columns,
                            'has_datetime': any('time' in col.lower() or 'date' in col.lower() 
                                              for col in df_preview.columns)
                        }
                    except Exception:
                        profile['data_preview'] = {'error': 'Could not preview data'}
                
                profiles.append(profile)
            
            # Sort by creation date (newest first)
            profiles.sort(
                key=lambda x: x.get('created_at', ''),
                reverse=True
            )
            
            # Cache result
            self._profile_cache[cache_key] = profiles
            self._cache_timestamps[cache_key] = datetime.now().timestamp()
            
            return profiles
            
        except Exception as e:
            logger.exception(f"Error getting available profiles: {e}")
            return []
    
    def quick_validate_profile(self, profile_id: str) -> Dict[str, Any]:
        """Quick validation of profile data"""
        try:
            csv_path = os.path.join(
                self.project_path, 'results', 'load_profiles',
                f"{profile_id}.csv"
            )
            
            if not os.path.exists(csv_path):
                return {'valid': False, 'error': 'Profile file not found'}
            
            # Quick check
            df_sample = pd.read_csv(csv_path, nrows=10)
            
            validation = {
                'valid': True,
                'has_data': len(df_sample) > 0,
                'has_demand_column': 'demand' in df_sample.columns,
                'has_datetime': any('time' in col.lower() or 'date' in col.lower() 
                                  for col in df_sample.columns)
            }
            
            if not validation['has_demand_column']:
                validation['valid'] = False
                validation['error'] = 'No demand column found'
            
            return validation
            
        except Exception as e:
            return {'valid': False, 'error': str(e)}
    
    def get_profile_data(self, profile_id: str, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get profile data with filtering and processing"""
        try:
            # Load data using analyzer
            df = self.analyzer.load_profile_data(profile_id, filters)
            
            if df.empty:
                raise ProcessingError("No data available after applying filters")
            
            # Calculate statistics
            unit = filters.get('unit', 'kW') if filters else 'kW'
            statistics = self.analyzer.calculate_comprehensive_statistics(df, unit)
            
            # Prepare sample data for display
            sample_size = min(1000, len(df))
            sample_df = df.head(sample_size)
            
            # Convert to JSON serializable format
            sample_data = []
            for _, row in sample_df.iterrows():
                row_dict = {}
                for col, val in row.items():
                    if pd.isna(val):
                        row_dict[col] = None
                    elif isinstance(val, (pd.Timestamp, datetime)):
                        row_dict[col] = val.isoformat()
                    else:
                        row_dict[col] = val
                sample_data.append(row_dict)
            
            return {
                'profile_id': profile_id,
                'statistics': statistics,
                'data': sample_data,
                'metadata': {
                    'total_records': len(df),
                    'sample_records': len(sample_data),
                    'unit': unit,
                    'filters_applied': filters or {},
                    'date_range': {
                        'start': df['ds'].min().isoformat() if 'ds' in df.columns and not df['ds'].empty else None,
                        'end': df['ds'].max().isoformat() if 'ds' in df.columns and not df['ds'].empty else None
                    } if 'ds' in df.columns else None,
                    'columns': df.columns.tolist()
                }
            }
            
        except Exception as e:
            logger.exception(f"Error getting profile data for {profile_id}: {e}")
            raise
    
    def get_profile_metadata(self, profile_id: str) -> Dict[str, Any]:
        """Get profile metadata and configuration"""
        try:
            # Check if profile exists
            csv_path = os.path.join(
                self.project_path, 'results', 'load_profiles',
                f"{profile_id}.csv"
            )
            
            if not os.path.exists(csv_path):
                raise ResourceNotFoundError(f"Profile '{profile_id}' not found")
            
            # Get file info
            file_info = get_file_info(csv_path)
            
            # Check for metadata file
            metadata_path = os.path.join(
                self.project_path, 'config',
                f"{profile_id}_metadata.json"
            )
            
            metadata = {}
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                except Exception as e:
                    logger.warning(f"Error reading metadata for {profile_id}: {e}")
            
            # Get basic data info
            try:
                df_info = pd.read_csv(csv_path, nrows=5)
                data_info = {
                    'columns': df_info.columns.tolist(),
                    'data_types': df_info.dtypes.to_dict(),
                    'sample_values': df_info.head(3).to_dict('records')
                }
            except Exception:
                data_info = {'error': 'Could not read data info'}
            
            return {
                'profile_id': profile_id,
                'file_info': file_info,
                'metadata': metadata,
                'data_info': data_info,
                'validation': self.quick_validate_profile(profile_id)
            }
            
        except Exception as e:
            logger.exception(f"Error getting profile metadata for {profile_id}: {e}")
            raise
    
    def perform_analysis(self, profile_id: str, analysis_type: str, 
                        parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Perform specific analysis on profile"""
        cache_key = f'analysis_{profile_id}_{analysis_type}_{str(parameters)}'
        
        if self._is_cache_valid(cache_key):
            return self._analysis_cache[cache_key]
        
        try:
            if analysis_type not in self.supported_analysis_types:
                raise ValidationError(f"Unsupported analysis type: {analysis_type}")
            
            # Load profile data
            filters = parameters.get('filters', {}) if parameters else {}
            df = self.analyzer.load_profile_data(profile_id, filters)
            
            if df.empty:
                raise ProcessingError("No data available for analysis")
            
            # Get unit
            unit = parameters.get('unit', 'kW') if parameters else 'kW'
            
            # Perform analysis based on type
            if analysis_type == 'overview':
                result = self._perform_overview_analysis(df, unit, parameters)
            elif analysis_type == 'peak_analysis':
                result = self._perform_peak_analysis(df, unit, parameters)
            elif analysis_type == 'weekday_weekend':
                result = self._perform_weekday_weekend_analysis(df, unit, parameters)
            elif analysis_type == 'seasonal':
                result = self._perform_seasonal_analysis(df, unit, parameters)
            elif analysis_type == 'monthly':
                result = self._perform_monthly_analysis(df, unit, parameters)
            elif analysis_type == 'duration_curve':
                result = self._perform_duration_curve_analysis(df, unit, parameters)
            elif analysis_type == 'heatmap':
                result = self._perform_heatmap_analysis(df, unit, parameters)
            elif analysis_type == 'load_factor':
                result = self._perform_load_factor_analysis(df, unit, parameters)
            elif analysis_type == 'demand_profile':
                result = self._perform_demand_profile_analysis(df, unit, parameters)
            elif analysis_type == 'variability':
                result = self._perform_variability_analysis(df, unit, parameters)
            else:
                # Fallback to analyzer's method
                result = self.analyzer.generate_analysis_data(df, analysis_type, unit)
            
            # Add metadata
            result['metadata'] = {
                'profile_id': profile_id,
                'analysis_type': analysis_type,
                'unit': unit,
                'data_points': len(df),
                'parameters': parameters,
                'generated_at': datetime.now().isoformat()
            }
            
            # Cache result
            self._analysis_cache[cache_key] = result
            self._cache_timestamps[cache_key] = datetime.now().timestamp()
            
            return result
            
        except Exception as e:
            logger.exception(f"Error performing {analysis_type} analysis: {e}")
            raise
    
    def get_comprehensive_analysis(self, profile_id: str) -> Dict[str, Any]:
        """Get comprehensive analysis covering all aspects"""
        try:
            # Load profile data
            df = self.analyzer.load_profile_data(profile_id)
            
            if df.empty:
                raise ProcessingError("No data available for comprehensive analysis")
            
            # Perform all analysis types
            comprehensive_result = {
                'profile_id': profile_id,
                'analysis_summary': {},
                'detailed_results': {}
            }
            
            # Basic statistics
            statistics = self.analyzer.calculate_comprehensive_statistics(df, 'kW')
            comprehensive_result['statistics'] = statistics
            
            # Perform key analyses
            key_analyses = ['overview', 'peak_analysis', 'seasonal', 'load_factor']
            
            for analysis_type in key_analyses:
                try:
                    analysis_result = self.perform_analysis(profile_id, analysis_type)
                    comprehensive_result['detailed_results'][analysis_type] = analysis_result
                except Exception as e:
                    logger.warning(f"Failed {analysis_type} analysis: {e}")
                    comprehensive_result['detailed_results'][analysis_type] = {'error': str(e)}
            
            # Create summary
            comprehensive_result['analysis_summary'] = self._create_analysis_summary(
                comprehensive_result['detailed_results']
            )
            
            return comprehensive_result
            
        except Exception as e:
            logger.exception(f"Error in comprehensive analysis for {profile_id}: {e}")
            raise
    
    def get_statistical_summary(self, profile_id: str, unit: str = 'kW') -> Dict[str, Any]:
        """Get statistical summary of profile"""
        try:
            df = self.analyzer.load_profile_data(profile_id)
            
            if df.empty:
                raise ProcessingError("No data available for statistical analysis")
            
            statistics = self.analyzer.calculate_comprehensive_statistics(df, unit)
            
            # Enhance with additional statistical measures
            if 'demand' in df.columns:
                demand_data = df['demand'] * UNIT_FACTORS.get(unit, 1)
                
                stats = {
                    'descriptive_statistics': {
                        'count': len(demand_data),
                        'mean': float(demand_data.mean()),
                        'median': float(demand_data.median()),
                        'std': float(demand_data.std()),
                        'variance': float(demand_data.var()),
                        'skewness': float(demand_data.skew()),
                        'kurtosis': float(demand_data.kurtosis()),
                        'min': float(demand_data.min()),
                        'max': float(demand_data.max()),
                        'range': float(demand_data.max() - demand_data.min())
                    },
                    'percentiles': {
                        'p5': float(demand_data.quantile(0.05)),
                        'p10': float(demand_data.quantile(0.10)),
                        'p25': float(demand_data.quantile(0.25)),
                        'p50': float(demand_data.quantile(0.50)),
                        'p75': float(demand_data.quantile(0.75)),
                        'p90': float(demand_data.quantile(0.90)),
                        'p95': float(demand_data.quantile(0.95)),
                        'p99': float(demand_data.quantile(0.99))
                    },
                    'distribution_metrics': {
                        'coefficient_of_variation': float(demand_data.std() / demand_data.mean()) if demand_data.mean() != 0 else 0,
                        'interquartile_range': float(demand_data.quantile(0.75) - demand_data.quantile(0.25)),
                        'mad': float(demand_data.mad()),  # Mean Absolute Deviation
                    }
                }
                
                statistics.update(stats)
            
            return {
                'profile_id': profile_id,
                'unit': unit,
                'statistics': statistics,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.exception(f"Error getting statistical summary for {profile_id}: {e}")
            raise
    
    def compare_profiles(self, profile_ids: List[str], comparison_type: str = 'overview',
                        parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Compare multiple profiles withanalysis"""
        try:
            if len(profile_ids) < 2:
                raise ValidationError("At least 2 profiles required for comparison")
            
            if len(profile_ids) > 5:
                raise ValidationError("Maximum 5 profiles can be compared")
            
            # Load data for all profiles
            profiles_data = {}
            for profile_id in profile_ids:
                try:
                    filters = parameters.get('filters', {}) if parameters else {}
                    df = self.analyzer.load_profile_data(profile_id, filters)
                    if not df.empty:
                        profiles_data[profile_id] = df
                except Exception as e:
                    logger.warning(f"Could not load profile {profile_id}: {e}")
            
            if len(profiles_data) < 2:
                raise ProcessingError("Insufficient valid profiles for comparison")
            
            # Perform comparison using analyzer
            unit = parameters.get('unit', 'kW') if parameters else 'kW'
            comparison_result = self.analyzer.compare_profiles(
                profile_ids=list(profiles_data.keys()),
                comparison_type=comparison_type,
                unit=unit,
                filters=parameters.get('filters') if parameters else None
            )
            
            # Enhance with additional metrics
            comparison = self._enhance_comparison_result(
                comparison_result, profiles_data, comparison_type, parameters
            )
            
            return comparison
            
        except Exception as e:
            logger.exception(f"Error comparing profiles: {e}")
            raise
    
    def benchmark_profile(self, profile_id: str, benchmark_type: str = 'industry_standard',
                         unit: str = 'kW') -> Dict[str, Any]:
        """Benchmark profile against standard metrics"""
        try:
            df = self.analyzer.load_profile_data(profile_id)
            
            if df.empty:
                raise ProcessingError("No data available for benchmarking")
            
            # Calculate profile metrics
            statistics = self.analyzer.calculate_comprehensive_statistics(df, unit)
            
            # Define benchmark standards
            benchmarks = self._get_benchmark_standards(benchmark_type)
            
            # Perform benchmarking
            benchmark_result = {
                'profile_id': profile_id,
                'benchmark_type': benchmark_type,
                'unit': unit,
                'profile_metrics': statistics,
                'benchmark_standards': benchmarks,
                'comparison': {},
                'performance_score': 0,
                'recommendations': []
            }
            
            # Compare against benchmarks
            if 'basic' in statistics and benchmarks:
                profile_basic = statistics['basic']
                
                # Load Factor comparison
                if 'average_load_factor' in profile_basic and 'load_factor' in benchmarks:
                    profile_lf = profile_basic['average_load_factor']
                    benchmark_lf = benchmarks['load_factor']
                    
                    benchmark_result['comparison']['load_factor'] = {
                        'profile_value': profile_lf,
                        'benchmark_value': benchmark_lf,
                        'difference': profile_lf - benchmark_lf,
                        'performance': 'good' if profile_lf >= benchmark_lf * 0.9 else 'poor'
                    }
                
                # Peak to Average ratio
                if 'peak_to_average_ratio' in profile_basic and 'peak_to_average_ratio' in benchmarks:
                    profile_par = profile_basic['peak_to_average_ratio']
                    benchmark_par = benchmarks['peak_to_average_ratio']
                    
                    benchmark_result['comparison']['peak_to_average_ratio'] = {
                        'profile_value': profile_par,
                        'benchmark_value': benchmark_par,
                        'difference': profile_par - benchmark_par,
                        'performance': 'good' if profile_par <= benchmark_par * 1.1 else 'poor'
                    }
            
            # Calculate overall performance score
            benchmark_result['performance_score'] = self._calculate_performance_score(
                benchmark_result['comparison']
            )
            
            # Generate recommendations
            benchmark_result['recommendations'] = self._generate_benchmark_recommendations(
                benchmark_result['comparison']
            )
            
            return benchmark_result
            
        except Exception as e:
            logger.exception(f"Error benchmarking profile {profile_id}: {e}")
            raise
    
    def get_profile_fiscal_years(self, profile_id: str) -> List[int]:
        """Get available fiscal years for profile"""
        try:
            return self.analyzer.get_profile_fiscal_years(profile_id)
        except Exception as e:
            logger.exception(f"Error getting fiscal years for {profile_id}: {e}")
            raise
    
    def get_seasonal_analysis(self, profile_id: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get seasonal analysis for profile"""
        return self.perform_analysis(profile_id, 'seasonal', parameters)
    
    def get_time_series_decomposition(self, profile_id: str, 
                                    decomposition_params: Dict[str, Any]) -> Dict[str, Any]:
        """Get time series decomposition analysis"""
        try:
            df = self.analyzer.load_profile_data(profile_id)
            
            if df.empty:
                raise ProcessingError("No data available for decomposition")
            
            # Perform time series decomposition
            decomposition_result = self._perform_time_series_decomposition(
                df, decomposition_params
            )
            
            return {
                'profile_id': profile_id,
                'decomposition_method': decomposition_params.get('method', 'STL'),
                'parameters': decomposition_params,
                'result': decomposition_result,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.exception(f"Error in time series decomposition for {profile_id}: {e}")
            raise
    
    def validate_profile_comprehensive(self, profile_id: str) -> Dict[str, Any]:
        """Comprehensive profile validation"""
        try:
            df = self.analyzer.load_profile_data(profile_id)
            
            validation_result = {
                'profile_id': profile_id,
                'overall_score': 100,
                'validation_checks': {},
                'issues': [],
                'warnings': [],
                'recommendations': [],
                'data_quality_metrics': {}
            }
            
            # Data existence check
            if df.empty:
                validation_result['validation_checks']['data_exists'] = False
                validation_result['issues'].append("No data found in profile")
                validation_result['overall_score'] = 0
                return validation_result
            
            validation_result['validation_checks']['data_exists'] = True
            
            # Data completeness
            if 'demand' in df.columns:
                demand_completeness = df['demand'].count() / len(df)
                validation_result['data_quality_metrics']['demand_completeness'] = demand_completeness
                validation_result['validation_checks']['demand_complete'] = demand_completeness > 0.95
                
                if demand_completeness < 0.95:
                    validation_result['warnings'].append(f"Demand data completeness: {demand_completeness:.1%}")
                    validation_result['overall_score'] -= (1 - demand_completeness) * 20
            
            # Temporal consistency
            if 'ds' in df.columns:
                validation_result['validation_checks']['has_timestamps'] = True
                
                # Check for duplicates
                duplicates = df['ds'].duplicated().sum()
                if duplicates > 0:
                    validation_result['warnings'].append(f"Found {duplicates} duplicate timestamps")
                    validation_result['overall_score'] -= min(duplicates / len(df) * 30, 15)
            else:
                validation_result['validation_checks']['has_timestamps'] = False
                validation_result['warnings'].append("No timestamp column found")
                validation_result['overall_score'] -= 10
            
            # Data quality checks
            if 'demand' in df.columns:
                demand_data = df['demand'].dropna()
                
                # Negative values
                negative_count = (demand_data < 0).sum()
                if negative_count > 0:
                    validation_result['issues'].append(f"Found {negative_count} negative demand values")
                    validation_result['overall_score'] -= min(negative_count / len(demand_data) * 20, 10)
                
                # Zero values
                zero_count = (demand_data == 0).sum()
                zero_percentage = (zero_count / len(demand_data)) * 100
                validation_result['data_quality_metrics']['zero_percentage'] = zero_percentage
                
                if zero_percentage > 15:
                    validation_result['warnings'].append(f"High percentage of zero values: {zero_percentage:.1f}%")
                    validation_result['overall_score'] -= min(zero_percentage / 5, 10)
                
                # Outliers
                q99 = demand_data.quantile(0.99)
                q01 = demand_data.quantile(0.01)
                outliers = ((demand_data > q99 * 2) | (demand_data < q01 * 0.1)).sum()
                outlier_percentage = (outliers / len(demand_data)) * 100
                validation_result['data_quality_metrics']['outlier_percentage'] = outlier_percentage
                
                if outlier_percentage > 5:
                    validation_result['warnings'].append(f"High percentage of outliers: {outlier_percentage:.1f}%")
                    validation_result['overall_score'] -= min(outlier_percentage, 8)
            
            # Determine validation status
            if validation_result['overall_score'] >= 90:
                status = "excellent"
            elif validation_result['overall_score'] >= 75:
                status = "good"
            elif validation_result['overall_score'] >= 50:
                status = "fair"
            else:
                status = "poor"
            
            validation_result['status'] = status
            
            # Generate recommendations
            if validation_result['issues']:
                validation_result['recommendations'].extend([
                    "Review and clean data quality issues",
                    "Check data collection process"
                ])
            
            if validation_result['warnings']:
                validation_result['recommendations'].append(
                    "Consider data preprocessing to address warnings"
                )
            
            return validation_result
            
        except Exception as e:
            logger.exception(f"Error validating profile {profile_id}: {e}")
            raise
    
    def generate_data_quality_report(self, profile_id: str) -> Dict[str, Any]:
        """Generate comprehensive data quality report"""
        try:
            # Get validation results
            validation = self.validate_profile_comprehensive(profile_id)
            
            # Get statistical summary
            statistics = self.get_statistical_summary(profile_id)
            
            # Create comprehensive report
            quality_report = {
                'profile_id': profile_id,
                'report_type': 'data_quality',
                'generated_at': datetime.now().isoformat(),
                'executive_summary': {
                    'overall_quality': validation['status'],
                    'quality_score': validation['overall_score'],
                    'key_issues': len(validation['issues']),
                    'warnings': len(validation['warnings'])
                },
                'validation_results': validation,
                'statistical_analysis': statistics,
                'recommendations': self._generate_quality_recommendations(validation, statistics),
                'action_items': self._generate_action_items(validation)
            }
            
            return quality_report
            
        except Exception as e:
            logger.exception(f"Error generating quality report for {profile_id}: {e}")
            raise
    
    def export_analysis_results(self, profile_id: str, export_format: str = 'xlsx',
                              analysis_types: List[str] = None) -> Any:
        """Export analysis results in specified format"""
        try:
            if export_format not in self.export_formats:
                raise ValidationError(f"Unsupported export format: {export_format}")
            
            # Get analysis results
            if not analysis_types:
                analysis_types = ['overview', 'statistical']
            
            export_data = {
                'profile_id': profile_id,
                'export_format': export_format,
                'export_timestamp': datetime.now().isoformat(),
                'analysis_results': {}
            }
            
            # Collect analysis data
            for analysis_type in analysis_types:
                try:
                    if analysis_type == 'statistical':
                        export_data['analysis_results'][analysis_type] = self.get_statistical_summary(profile_id)
                    else:
                        export_data['analysis_results'][analysis_type] = self.perform_analysis(profile_id, analysis_type)
                except Exception as e:
                    logger.warning(f"Could not export {analysis_type}: {e}")
                    export_data['analysis_results'][analysis_type] = {'error': str(e)}
            
            # Create export file
            return self._create_export_file(export_data, export_format)
            
        except Exception as e:
            logger.exception(f"Error exporting analysis for {profile_id}: {e}")
            raise
    
    def export_comparison_results(self, profile_ids: List[str], export_format: str = 'xlsx') -> Any:
        """Export comparison results"""
        try:
            comparison_result = self.compare_profiles(profile_ids)
            
            export_data = {
                'comparison_type': 'multi_profile',
                'profile_ids': profile_ids,
                'export_format': export_format,
                'export_timestamp': datetime.now().isoformat(),
                'comparison_results': comparison_result
            }
            
            return self._create_export_file(export_data, export_format)
            
        except Exception as e:
            logger.exception(f"Error exporting comparison: {e}")
            raise
    
    def perform_batch_analysis(self, profile_ids: List[str], 
                              analysis_types: List[str]) -> Dict[str, Any]:
        """Perform batch analysis on multiple profiles"""
        try:
            batch_results = {
                'batch_id': str(uuid.uuid4()),
                'profile_ids': profile_ids,
                'analysis_types': analysis_types,
                'started_at': datetime.now().isoformat(),
                'results': {},
                'summary': {
                    'total_profiles': len(profile_ids),
                    'total_analyses': len(analysis_types),
                    'successful': 0,
                    'failed': 0
                }
            }
            
            # Process each profile
            for profile_id in profile_ids:
                profile_results = {}
                
                for analysis_type in analysis_types:
                    try:
                        result = self.perform_analysis(profile_id, analysis_type)
                        profile_results[analysis_type] = result
                        batch_results['summary']['successful'] += 1
                    except Exception as e:
                        profile_results[analysis_type] = {'error': str(e)}
                        batch_results['summary']['failed'] += 1
                        logger.warning(f"Batch analysis failed for {profile_id} - {analysis_type}: {e}")
                
                batch_results['results'][profile_id] = profile_results
            
            batch_results['completed_at'] = datetime.now().isoformat()
            return batch_results
            
        except Exception as e:
            logger.exception(f"Error in batch analysis: {e}")
            raise
    
    def generate_comprehensive_report(self, profile_ids: List[str], 
                                    report_type: str = 'comprehensive') -> Dict[str, Any]:
        """Generate comprehensive analysis report"""
        try:
            report = {
                'report_id': str(uuid.uuid4()),
                'report_type': report_type,
                'profile_ids': profile_ids,
                'generated_at': datetime.now().isoformat(),
                'executive_summary': {},
                'detailed_analysis': {},
                'recommendations': [],
                'appendices': {}
            }
            
            # Generate summary statistics
            summary_stats = {}
            for profile_id in profile_ids:
                try:
                    stats = self.get_statistical_summary(profile_id)
                    summary_stats[profile_id] = stats
                except Exception as e:
                    logger.warning(f"Could not get stats for {profile_id}: {e}")
            
            report['executive_summary'] = self._create_executive_summary(summary_stats)
            
            # Detailed analysis for each profile
            for profile_id in profile_ids:
                try:
                    detailed = self.get_comprehensive_analysis(profile_id)
                    report['detailed_analysis'][profile_id] = detailed
                except Exception as e:
                    logger.warning(f"Could not get detailed analysis for {profile_id}: {e}")
                    report['detailed_analysis'][profile_id] = {'error': str(e)}
            
            # Generate recommendations
            report['recommendations'] = self._generate_report_recommendations(
                report['detailed_analysis']
            )
            
            return report
            
        except Exception as e:
            logger.exception(f"Error generating comprehensive report: {e}")
            raise
    
    # Private helper methods
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is valid"""
        if cache_key not in self._cache_timestamps:
            return False
        
        age = datetime.now().timestamp() - self._cache_timestamps[cache_key]
        return age < self._cache_ttl
    
    # Analysis implementation methods (simplified - can be expanded)
    def _perform_overview_analysis(self, df: pd.DataFrame, unit: str, parameters: Dict) -> Dict:
        """Perform overview analysis"""
        return self.analyzer.generate_analysis_data(df, 'overview', unit)
    
    def _perform_peak_analysis(self, df: pd.DataFrame, unit: str, parameters: Dict) -> Dict:
        """Perform peak analysis"""
        return self.analyzer.generate_analysis_data(df, 'peak_analysis', unit)
    
    def _perform_weekday_weekend_analysis(self, df: pd.DataFrame, unit: str, parameters: Dict) -> Dict:
        """Perform weekday vs weekend analysis"""
        return self.analyzer.generate_analysis_data(df, 'weekday_weekend', unit)
    
    def _perform_seasonal_analysis(self, df: pd.DataFrame, unit: str, parameters: Dict) -> Dict:
        """Perform seasonal analysis"""
        return self.analyzer.generate_analysis_data(df, 'seasonal', unit)
    
    def _perform_monthly_analysis(self, df: pd.DataFrame, unit: str, parameters: Dict) -> Dict:
        """Perform monthly analysis"""
        return self.analyzer.generate_analysis_data(df, 'monthly', unit)
    
    def _perform_duration_curve_analysis(self, df: pd.DataFrame, unit: str, parameters: Dict) -> Dict:
        """Perform duration curve analysis"""
        return self.analyzer.generate_analysis_data(df, 'duration_curve', unit)
    
    def _perform_heatmap_analysis(self, df: pd.DataFrame, unit: str, parameters: Dict) -> Dict:
        """Perform heatmap analysis"""
        return self.analyzer.generate_analysis_data(df, 'heatmap', unit)
    
    def _perform_load_factor_analysis(self, df: pd.DataFrame, unit: str, parameters: Dict) -> Dict:
        """Perform load factor analysis"""
        if 'demand' not in df.columns:
            return {'error': 'No demand data available'}
        
        demand_data = df['demand'] * UNIT_FACTORS.get(unit, 1)
        
        # Calculate load factors by different time periods
        load_factor_analysis = {
            'overall_load_factor': float(demand_data.mean() / demand_data.max()) if demand_data.max() > 0 else 0,
            'monthly_load_factors': {},
            'seasonal_load_factors': {},
            'trends': {}
        }
        
        # Monthly load factors
        if 'ds' in df.columns:
            df_copy = df.copy()
            df_copy['month'] = pd.to_datetime(df_copy['ds']).dt.month
            
            for month in range(1, 13):
                month_data = df_copy[df_copy['month'] == month]['demand']
                if not month_data.empty:
                    month_data_scaled = month_data * UNIT_FACTORS.get(unit, 1)
                    load_factor_analysis['monthly_load_factors'][month] = {
                        'load_factor': float(month_data_scaled.mean() / month_data_scaled.max()) if month_data_scaled.max() > 0 else 0,
                        'avg_demand': float(month_data_scaled.mean()),
                        'peak_demand': float(month_data_scaled.max())
                    }
        
        return load_factor_analysis
    
    def _perform_demand_profile_analysis(self, df: pd.DataFrame, unit: str, parameters: Dict) -> Dict:
        """Perform demand profile analysis"""
        if 'demand' not in df.columns:
            return {'error': 'No demand data available'}
        
        demand_data = df['demand'] * UNIT_FACTORS.get(unit, 1)
        
        profile_analysis = {
            'demand_characteristics': {
                'base_load': float(demand_data.quantile(0.1)),
                'average_load': float(demand_data.mean()),
                'peak_load': float(demand_data.max()),
                'load_range': float(demand_data.max() - demand_data.min())
            },
            'utilization_metrics': {
                'capacity_factor': float(demand_data.mean() / demand_data.max()) if demand_data.max() > 0 else 0,
                'diversity_factor': 1.0,  # Would need multiple profiles to calculate
                'demand_factor': float(demand_data.max() / demand_data.max()) if demand_data.max() > 0 else 0
            }
        }
        
        return profile_analysis
    
    def _perform_variability_analysis(self, df: pd.DataFrame, unit: str, parameters: Dict) -> Dict:
        """Perform variability analysis"""
        if 'demand' not in df.columns:
            return {'error': 'No demand data available'}
        
        demand_data = df['demand'] * UNIT_FACTORS.get(unit, 1)
        
        variability_analysis = {
            'volatility_metrics': {
                'coefficient_of_variation': float(demand_data.std() / demand_data.mean()) if demand_data.mean() != 0 else 0,
                'standard_deviation': float(demand_data.std()),
                'variance': float(demand_data.var()),
                'range_ratio': float((demand_data.max() - demand_data.min()) / demand_data.mean()) if demand_data.mean() != 0 else 0
            },
            'stability_metrics': {
                'median_absolute_deviation': float(demand_data.mad()),
                'interquartile_range': float(demand_data.quantile(0.75) - demand_data.quantile(0.25)),
                'relative_range': float((demand_data.quantile(0.9) - demand_data.quantile(0.1)) / demand_data.median()) if demand_data.median() != 0 else 0
            }
        }
        
        return variability_analysis
    
    def _perform_time_series_decomposition(self, df: pd.DataFrame, params: Dict) -> Dict:
        """Perform time series decomposition"""
        if 'demand' not in df.columns or 'ds' not in df.columns:
            return {'error': 'Insufficient data for decomposition'}
        
        try:
            from statsmodels.tsa.seasonal import seasonal_decompose
            
            # Prepare data
            ts_data = df.set_index('ds')['demand']
            ts_data = ts_data.asfreq('H')  # Hourly frequency
            
            # Handle missing values
            ts_data = ts_data.interpolate()
            
            # Perform decomposition
            method = params.get('method', 'STL')
            model = params.get('seasonal', 'additive')
            
            if method == 'STL':
                # Use STL decomposition if available
                try:
                    from statsmodels.tsa.seasonal import STL
                    decomposition = STL(ts_data, seasonal=13).fit()
                except ImportError:
                    # Fallback to classical decomposition
                    decomposition = seasonal_decompose(ts_data, model=model, period=24)
            else:
                decomposition = seasonal_decompose(ts_data, model=model, period=24)
            
            return {
                'trend': decomposition.trend.dropna().to_dict(),
                'seasonal': decomposition.seasonal.dropna().to_dict(),
                'residual': decomposition.resid.dropna().to_dict(),
                'observed': decomposition.observed.dropna().to_dict(),
                'method': method,
                'model': model
            }
            
        except Exception as e:
            return {'error': f'Decomposition failed: {str(e)}'}
    
    def _create_analysis_summary(self, detailed_results: Dict) -> Dict:
        """Create summary of detailed analysis results"""
        summary = {
            'completed_analyses': list(detailed_results.keys()),
            'failed_analyses': [k for k, v in detailed_results.items() if 'error' in v],
            'key_insights': [],
            'data_quality_flags': []
        }
        
        # Extract key insights
        for analysis_type, result in detailed_results.items():
            if 'error' not in result and 'metadata' in result:
                summary['key_insights'].append({
                    'analysis': analysis_type,
                    'data_points': result['metadata'].get('data_points', 0)
                })
        
        return summary
    
    def _enhance_comparison_result(self, comparison_result: Dict, profiles_data: Dict,
                                 comparison_type: str, parameters: Dict) -> Dict:
        """Enhance comparison result with additional metrics"""
        comparison_result = comparison_result.copy()
        
        # Add profile data summary
        comparison_result['profiles_summary'] = {}
        for profile_id, df in profiles_data.items():
            comparison_result['profiles_summary'][profile_id] = {
                'data_points': len(df),
                'date_range': {
                    'start': df['ds'].min().isoformat() if 'ds' in df.columns else None,
                    'end': df['ds'].max().isoformat() if 'ds' in df.columns else None
                } if 'ds' in df.columns else None
            }
        
        # Add comparison metadata
        comparison_result['comparison_metadata'] = {
            'comparison_type': comparison_type,
            'total_profiles': len(profiles_data),
            'parameters': parameters,
            'generated_at': datetime.now().isoformat()
        }
        
        return 
    
    def _get_benchmark_standards(self, benchmark_type: str) -> Dict:
        """Get benchmark standards for comparison"""
        benchmarks = {
            'industry_standard': {
                'load_factor': 0.65,  # Typical industrial load factor
                'peak_to_average_ratio': 1.8,
                'capacity_factor': 0.75
            },
            'residential': {
                'load_factor': 0.25,
                'peak_to_average_ratio': 3.5,
                'capacity_factor': 0.30
            },
            'commercial': {
                'load_factor': 0.55,
                'peak_to_average_ratio': 2.2,
                'capacity_factor': 0.60
            }
        }
        
        return benchmarks.get(benchmark_type, benchmarks['industry_standard'])
    
    def _calculate_performance_score(self, comparison: Dict) -> float:
        """Calculate overall performance score from benchmark comparison"""
        if not comparison:
            return 50.0  # Neutral score
        
        scores = []
        for metric, data in comparison.items():
            if data['performance'] == 'good':
                scores.append(85)
            else:
                scores.append(40)
        
        return sum(scores) / len(scores) if scores else 50.0
    
    def _generate_benchmark_recommendations(self, comparison: Dict) -> List[str]:
        """Generate recommendations based on benchmark comparison"""
        recommendations = []
        
        for metric, data in comparison.items():
            if data['performance'] == 'poor':
                if metric == 'load_factor':
                    recommendations.append("Consider load balancing strategies to improve load factor")
                elif metric == 'peak_to_average_ratio':
                    recommendations.append("Implement peak shaving measures to reduce peak-to-average ratio")
        
        if not recommendations:
            recommendations.append("Profile performance meets benchmark standards")
        
        return recommendations
    
    def _generate_quality_recommendations(self, validation: Dict, statistics: Dict) -> List[str]:
        """Generate data quality recommendations"""
        recommendations = []
        
        if validation['overall_score'] < 75:
            recommendations.append("Improve data quality through validation and cleaning")
        
        if validation['issues']:
            recommendations.append("Address critical data issues before analysis")
        
        if validation['warnings']:
            recommendations.append("Review and resolve data quality warnings")
        
        return recommendations
    
    def _generate_action_items(self, validation: Dict) -> List[str]:
        """Generate actionable items from validation"""
        actions = []
        
        for issue in validation['issues']:
            actions.append(f"CRITICAL: {issue}")
        
        for warning in validation['warnings']:
            actions.append(f"REVIEW: {warning}")
        
        return actions
    
    def _create_export_file(self, export_data: Dict, export_format: str) -> Any:
        """Create export file in specified format"""
        try:
            from flask import send_file
            import tempfile
            
            temp_dir = tempfile.mkdtemp()
            
            if export_format == 'json':
                file_path = os.path.join(temp_dir, f"analysis_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                
                with open(file_path, 'w') as f:
                    json.dump(export_data, f, indent=2, default=str)
                
                return send_file(
                    file_path,
                    as_attachment=True,
                    download_name=os.path.basename(file_path),
                    mimetype='application/json'
                )
            
            elif export_format == 'csv':
                file_path = os.path.join(temp_dir, f"analysis_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
                
                # Flatten data for CSV
                flattened_data = self._flatten_export_data(export_data)
                df = pd.DataFrame(flattened_data)
                df.to_csv(file_path, index=False)
                
                return send_file(
                    file_path,
                    as_attachment=True,
                    download_name=os.path.basename(file_path),
                    mimetype='text/csv'
                )
            
            elif export_format == 'xlsx':
                file_path = os.path.join(temp_dir, f"analysis_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
                
                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                    # Create multiple sheets for different data
                    summary_data = {
                        'Profile ID': export_data.get('profile_id', 'Multiple'),
                        'Export Timestamp': export_data['export_timestamp'],
                        'Export Format': export_format
                    }
                    
                    summary_df = pd.DataFrame([summary_data])
                    summary_df.to_excel(writer, sheet_name='Export_Summary', index=False)
                    
                    # Add analysis results sheets
                    for analysis_type, result in export_data.get('analysis_results', {}).items():
                        if 'error' not in result:
                            try:
                                # Convert result to DataFrame
                                result_df = self._convert_analysis_to_df(result)
                                sheet_name = analysis_type[:31]  # Excel sheet name limit
                                result_df.to_excel(writer, sheet_name=sheet_name, index=False)
                            except Exception as e:
                                logger.warning(f"Could not export {analysis_type} to Excel: {e}")
                
                return send_file(
                    file_path,
                    as_attachment=True,
                    download_name=os.path.basename(file_path),
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
            
        except Exception as e:
            logger.exception(f"Error creating export file: {e}")
            raise
    
    def _flatten_export_data(self, data: Dict) -> List[Dict]:
        """Flatten nested export data for CSV format"""
        flattened = []
        
        # Basic info
        base_info = {
            'profile_id': data.get('profile_id', ''),
            'export_timestamp': data.get('export_timestamp', ''),
            'export_format': data.get('export_format', '')
        }
        
        # Analysis results
        for analysis_type, result in data.get('analysis_results', {}).items():
            if 'error' not in result:
                row = base_info.copy()
                row['analysis_type'] = analysis_type
                
                # Flatten statistics if available
                if 'statistics' in result:
                    stats = result['statistics']
                    if 'basic' in stats:
                        for key, value in stats['basic'].items():
                            row[f'basic_{key}'] = value
                
                flattened.append(row)
        
        return flattened if flattened else [base_info]
    
    def _convert_analysis_to_df(self, analysis_result: Dict) -> pd.DataFrame:
        """Convert analysis result to DataFrame for Excel export"""
        try:
            # Try to extract tabular data
            if 'statistics' in analysis_result:
                stats = analysis_result['statistics']
                if isinstance(stats, dict):
                    # Flatten statistics
                    flattened_stats = {}
                    for category, data in stats.items():
                        if isinstance(data, dict):
                            for key, value in data.items():
                                flattened_stats[f"{category}_{key}"] = value
                        else:
                            flattened_stats[category] = data
                    
                    return pd.DataFrame([flattened_stats])
            
            # Fallback: convert to key-value pairs
            if isinstance(analysis_result, dict):
                items = []
                for key, value in analysis_result.items():
                    if not isinstance(value, (dict, list)):
                        items.append({'Metric': key, 'Value': value})
                
                return pd.DataFrame(items)
            
            # Last resort: empty DataFrame with info
            return pd.DataFrame([{'Info': 'Analysis data could not be converted to tabular format'}])
            
        except Exception as e:
            return pd.DataFrame([{'Error': f'Could not convert analysis data: {str(e)}'}])
    
    def _create_executive_summary(self, summary_stats: Dict) -> Dict:
        """Create executive summary from profile statistics"""
        summary = {
            'total_profiles_analyzed': len(summary_stats),
            'key_metrics': {},
            'insights': [],
            'overall_assessment': 'satisfactory'
        }
        
        if summary_stats:
            # Calculate aggregate metrics
            load_factors = []
            peak_demands = []
            
            for profile_id, stats in summary_stats.items():
                if 'statistics' in stats and 'basic' in stats['statistics']:
                    basic_stats = stats['statistics']['basic']
                    if 'average_load_factor' in basic_stats:
                        load_factors.append(basic_stats['average_load_factor'])
                    if 'peak_demand' in basic_stats:
                        peak_demands.append(basic_stats['peak_demand'])
            
            if load_factors:
                summary['key_metrics']['average_load_factor'] = sum(load_factors) / len(load_factors)
            
            if peak_demands:
                summary['key_metrics']['total_peak_demand'] = sum(peak_demands)
        
        return summary
    
    def _generate_report_recommendations(self, detailed_analysis: Dict) -> List[str]:
        """Generate recommendations from detailed analysis"""
        recommendations = []
        
        successful_analyses = sum(1 for result in detailed_analysis.values() if 'error' not in result)
        total_analyses = len(detailed_analysis)
        
        if successful_analyses < total_analyses:
            recommendations.append(f"Review {total_analyses - successful_analyses} failed analyses")
        
        recommendations.append("Regular monitoring and analysis recommended")
        recommendations.append("Consider implementing energy efficiency measures")
        
        return recommendations