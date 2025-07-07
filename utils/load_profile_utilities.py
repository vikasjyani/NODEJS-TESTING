# utils/load_profile_utilities.py
"""
Utilities for load profile analysis and data processing
Enhanced for the new project-based structure
"""

import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import zipfile
import tempfile
from typing import Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

class LoadProfileAnalyzer:
    """
    Comprehensive load profile analyzer with advanced analytics
    """
    
    def __init__(self, project_path: str):
        """
        Initialize analyzer for a specific project
        
        Args:
            project_path (str): Path to the project directory
        """
        self.project_path = Path(project_path)
        self.profiles_dir = self.project_path / 'results' / 'load_profiles'
        self.config_dir = self.project_path / 'config'
        
        # Ensure directories exist
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def get_profile_list(self) -> List[Dict]:
        """Get list of all available profiles with metadata"""
        profiles = []
        
        for csv_file in self.profiles_dir.glob('*.csv'):
            profile_id = csv_file.stem
            
            # Get file info
            file_stat = csv_file.stat()
            file_info = {
                'size_bytes': file_stat.st_size,
                'size_mb': file_stat.st_size / (1024 * 1024),
                'modified': datetime.fromtimestamp(file_stat.st_mtime),
                'created': datetime.fromtimestamp(file_stat.st_ctime)
            }
            
            # Load metadata if available
            metadata_file = self.config_dir / f"{profile_id}_metadata.json"
            metadata = {}
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to load metadata for {profile_id}: {e}")
            
            # Quick data preview
            try:
                preview_df = pd.read_csv(csv_file, nrows=10)
                data_preview = self._get_data_preview(preview_df)
            except Exception as e:
                logger.warning(f"Failed to preview data for {profile_id}: {e}")
                data_preview = {}
            
            profiles.append({
                'profile_id': profile_id,
                'file_info': file_info,
                'metadata': metadata,
                'data_preview': data_preview
            })
        
        return sorted(profiles, key=lambda x: x['file_info']['modified'], reverse=True)
    
    def _get_data_preview(self, df: pd.DataFrame) -> Dict:
        """Get quick preview of data"""
        preview = {
            'total_rows': len(df),
            'columns': list(df.columns),
            'has_datetime': any('date' in col.lower() or 'time' in col.lower() for col in df.columns),
            'has_demand': any('demand' in col.lower() or 'load' in col.lower() for col in df.columns)
        }
        
        # Try to identify demand column and get basic stats
        demand_cols = [col for col in df.columns if any(term in col.lower() for term in ['demand', 'load', 'power'])]
        if demand_cols:
            demand_col = demand_cols[0]
            try:
                preview['demand_stats'] = {
                    'min': float(df[demand_col].min()),
                    'max': float(df[demand_col].max()),
                    'mean': float(df[demand_col].mean())
                }
            except:
                pass
        
        return preview
    
    def load_profile_data(self, profile_id: str, standardize: bool = True) -> pd.DataFrame:
        """
        Load and optionally standardize profile data
        
        Args:
            profile_id (str): Profile identifier
            standardize (bool): Whether to standardize column names and add derived columns
            
        Returns:
            pd.DataFrame: Loaded profile data
        """
        csv_path = self.profiles_dir / f"{profile_id}.csv"
        
        if not csv_path.exists():
            raise FileNotFoundError(f"Profile {profile_id} not found")
        
        # Load data
        df = pd.read_csv(csv_path)
        
        if standardize:
            df = self._standardize_profile_data(df)
        
        return df
    
    def _standardize_profile_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize profile data columns and add derived columns"""
        df = df.copy()
        
        # Column mapping for standardization
        column_mapping = {
            'Demand (kW)': 'demand',
            'Demand': 'demand',
            'Load': 'demand',
            'load': 'demand',
            'Power': 'demand',
            'datetime': 'ds',
            'timestamp': 'ds',
            'Date': 'date_str',
            'Time': 'time_str',
            'Fiscal_Year': 'financial_year',
            'Year': 'year'
        }
        
        # Rename columns
        df = df.rename(columns=column_mapping)
        
        # Ensure datetime column
        if 'ds' not in df.columns:
            if 'date_str' in df.columns and 'time_str' in df.columns:
                # Combine date and time strings
                df['ds'] = pd.to_datetime(
                    df['date_str'] + ' ' + df['time_str'],
                    format='%d-%m-%Y %H:%M:%S',
                    dayfirst=True,
                    errors='coerce'
                )
            elif 'date_str' in df.columns:
                df['ds'] = pd.to_datetime(df['date_str'], dayfirst=True)
            else:
                # Try to create from index
                if df.index.name == 'datetime' or 'datetime' in str(type(df.index)):
                    df['ds'] = pd.to_datetime(df.index)
                else:
                    logger.warning("No datetime column found, creating sequential timestamps")
                    df['ds'] = pd.date_range(start='2025-04-01', periods=len(df), freq='H')
        
        # Ensure datetime is properly formatted
        if 'ds' in df.columns:
            df['ds'] = pd.to_datetime(df['ds'])
            
            # Add derived time columns
            df['date'] = df['ds'].dt.date
            df['time'] = df['ds'].dt.time
            df['hour'] = df['ds'].dt.hour
            df['day_of_week'] = df['ds'].dt.dayofweek
            df['day_name'] = df['ds'].dt.day_name()
            df['month'] = df['ds'].dt.month
            df['month_name'] = df['ds'].dt.month_name()
            df['year'] = df['ds'].dt.year
            df['quarter'] = df['ds'].dt.quarter
            
            # Calculate financial year (April to March)
            df['financial_year'] = df['ds'].apply(
                lambda x: x.year + 1 if x.month >= 4 else x.year
            )
            
            # Add season based on month
            season_mapping = {
                12: 'Winter', 1: 'Winter', 2: 'Winter',
                3: 'Summer', 4: 'Summer', 5: 'Summer', 6: 'Summer',
                7: 'Monsoon', 8: 'Monsoon', 9: 'Monsoon', 10: 'Monsoon', 11: 'Monsoon'
            }
            df['season'] = df['month'].map(season_mapping)
            
            # Add day type
            df['is_weekend'] = df['day_of_week'].isin([5, 6])  # Saturday=5, Sunday=6
            df['day_type'] = df['is_weekend'].map({True: 'Weekend', False: 'Weekday'})
            
            # Add time of day categories
            df['time_period'] = pd.cut(
                df['hour'],
                bins=[0, 6, 12, 18, 24],
                labels=['Night', 'Morning', 'Afternoon', 'Evening'],
                right=False
            )
        
        # Ensure demand column exists and is numeric
        if 'demand' in df.columns:
            df['demand'] = pd.to_numeric(df['demand'])
        elif any('demand' in col.lower() for col in df.columns):
            # Find first column with 'demand' in name
            demand_col = next(col for col in df.columns if 'demand' in col.lower())
            df['demand'] = pd.to_numeric(df[demand_col])
        
        # Remove rows with invalid data
        if 'demand' in df.columns:
            df = df.dropna(subset=['demand'])
            df = df[df['demand'] >= 0]  # Remove negative demands
        
        return df
    
    def calculate_comprehensive_statistics(self, df: pd.DataFrame) -> Dict:
        """Calculate comprehensive statistics for a load profile"""
        if df.empty or 'demand' not in df.columns:
            return {}
        
        stats = {}
        demand = df['demand']
        
        # Basic statistics
        stats['basic'] = {
            'count': len(df),
            'peak_load': float(demand.max()),
            'min_load': float(demand.min()),
            'average_load': float(demand.mean()),
            'median_load': float(demand.median()),
            'std_dev': float(demand.std()),
            'variance': float(demand.var()),
            'coefficient_of_variation': float(demand.std() / demand.mean()) if demand.mean() > 0 else 0,
            'load_factor': float((demand.mean() / demand.max()) * 100) if demand.max() > 0 else 0,
            'total_energy': float(demand.sum()),
            'peak_to_average_ratio': float(demand.max() / demand.mean()) if demand.mean() > 0 else 0
        }
        
        # Time-based statistics
        if 'ds' in df.columns:
            peak_idx = demand.idxmax()
            min_idx = demand.idxmin()
            
            stats['temporal'] = {
                'peak_datetime': df.loc[peak_idx, 'ds'].isoformat(),
                'min_datetime': df.loc[min_idx, 'ds'].isoformat(),
                'date_range_start': df['ds'].min().isoformat(),
                'date_range_end': df['ds'].max().isoformat(),
                'duration_hours': len(df),
                'duration_days': (df['ds'].max() - df['ds'].min()).days,
                'data_frequency': self._infer_frequency(df['ds'])
            }
        
        # Hourly patterns
        if 'hour' in df.columns:
            hourly_stats = df.groupby('hour')['demand'].agg(['mean', 'max', 'min', 'std', 'count'])
            stats['hourly'] = {
                'patterns': hourly_stats.to_dict('index'),
                'peak_hour': int(hourly_stats['mean'].idxmax()),
                'min_hour': int(hourly_stats['mean'].idxmin()),
                'morning_peak': self._find_peak_in_range(hourly_stats['mean'], 6, 12),
                'evening_peak': self._find_peak_in_range(hourly_stats['mean'], 18, 23)
            }
        
        # Daily patterns
        if 'day_type' in df.columns:
            daily_stats = df.groupby('day_type')['demand'].agg(['mean', 'max', 'min', 'std'])
            stats['daily'] = daily_stats.to_dict('index')
            
            # Weekday vs weekend hourly patterns
            if 'hour' in df.columns:
                weekday_pattern = df[df['day_type'] == 'Weekday'].groupby('hour')['demand'].mean()
                weekend_pattern = df[df['day_type'] == 'Weekend'].groupby('hour')['demand'].mean()
                
                stats['daily_hourly_patterns'] = {
                    'weekday': weekday_pattern.to_dict(),
                    'weekend': weekend_pattern.to_dict(),
                    'weekend_to_weekday_ratio': float(weekend_pattern.mean() / weekday_pattern.mean()) if weekday_pattern.mean() > 0 else 0
                }
        
        # Seasonal patterns
        if 'season' in df.columns:
            seasonal_stats = df.groupby('season')['demand'].agg(['mean', 'max', 'min', 'sum', 'std'])
            stats['seasonal'] = seasonal_stats.to_dict('index')
            
            # Calculate seasonal load factors
            seasonal_lf = {}
            for season in seasonal_stats.index:
                season_data = df[df['season'] == season]['demand']
                seasonal_lf[season] = float((season_data.mean() / season_data.max()) * 100) if season_data.max() > 0 else 0
            stats['seasonal_load_factors'] = seasonal_lf
        
        # Monthly patterns
        if 'month' in df.columns:
            monthly_stats = df.groupby('month')['demand'].agg(['mean', 'max', 'min', 'sum', 'std'])
            stats['monthly'] = monthly_stats.to_dict('index')
        
        # Annual patterns (if multiple years)
        if 'financial_year' in df.columns and df['financial_year'].nunique() > 1:
            annual_stats = df.groupby('financial_year')['demand'].agg(['mean', 'max', 'min', 'sum', 'std'])
            stats['annual'] = annual_stats.to_dict('index')
            
            # Calculate growth rates
            years = sorted(annual_stats.index)
            if len(years) > 1:
                growth_rates = {}
                for i in range(1, len(years)):
                    prev_year = years[i-1]
                    curr_year = years[i]
                    growth_rate = ((annual_stats.loc[curr_year, 'sum'] - annual_stats.loc[prev_year, 'sum']) / 
                                 annual_stats.loc[prev_year, 'sum']) * 100
                    growth_rates[f"{prev_year}_to_{curr_year}"] = float(growth_rate)
                stats['annual_growth_rates'] = growth_rates
        
        # Load duration analysis
        sorted_demands = np.sort(demand.values)[::-1]  # Descending order
        total_hours = len(sorted_demands)
        
        percentiles = [1, 5, 10, 25, 50, 75, 90, 95, 99]
        duration_percentiles = {}
        for p in percentiles:
            idx = int((p / 100) * total_hours)
            if idx < total_hours:
                duration_percentiles[f'p{p}'] = float(sorted_demands[idx])
        
        stats['load_duration'] = {
            'percentiles': duration_percentiles,
            'base_load': float(np.percentile(sorted_demands, 10)),  # Bottom 10%
            'intermediate_load': float(np.percentile(sorted_demands, 50)),  # Median
            'peak_load_hours': int(total_hours * 0.1),  # Top 10% hours
            'capacity_factor': float(demand.mean() / demand.max()) if demand.max() > 0 else 0
        }
        
        # Variability analysis
        if len(demand) > 1:
            # Calculate autocorrelation (lag-1)
            autocorr = demand.autocorr(lag=1) if hasattr(demand, 'autocorr') else np.corrcoef(demand[:-1], demand[1:])[0, 1]
            
            stats['variability'] = {
                'range': float(demand.max() - demand.min()),
                'interquartile_range': float(demand.quantile(0.75) - demand.quantile(0.25)),
                'coefficient_of_variation': float(demand.std() / demand.mean()) if demand.mean() > 0 else 0,
                'autocorrelation_lag1': float(autocorr) if not np.isnan(autocorr) else 0,
                'ramp_rate_mean': float(demand.diff().abs().mean()),
                'ramp_rate_max': float(demand.diff().abs().max())
            }
        
        return stats
    
    def _infer_frequency(self, timestamps: pd.Series) -> str:
        """Infer the frequency of timestamp data"""
        if len(timestamps) < 2:
            return "unknown"
        
        diff = timestamps.diff().dropna()
        if diff.empty:
            return "unknown"
        
        mode_diff = diff.mode()
        if mode_diff.empty:
            return "unknown"
        
        mode_seconds = mode_diff.iloc[0].total_seconds()
        
        if mode_seconds == 3600:
            return "hourly"
        elif mode_seconds == 1800:
            return "30min"
        elif mode_seconds == 900:
            return "15min"
        elif mode_seconds == 86400:
            return "daily"
        else:
            return f"{mode_seconds}s"
    
    def _find_peak_in_range(self, hourly_data: pd.Series, start_hour: int, end_hour: int) -> Dict:
        """Find peak within a specific hour range"""
        range_data = hourly_data.loc[start_hour:end_hour]
        if range_data.empty:
            return {'hour': None, 'value': None}
        
        peak_hour = range_data.idxmax()
        peak_value = range_data.max()
        
        return {
            'hour': int(peak_hour),
            'value': float(peak_value)
        }
    
    def compare_profiles(self, profile_ids: List[str], metrics: List[str] = None) -> Dict:
        """
        Compare multiple load profiles
        
        Args:
            profile_ids (List[str]): List of profile IDs to compare
            metrics (List[str]): List of metrics to compare (optional)
            
        Returns:
            Dict: Comparison results
        """
        if len(profile_ids) < 2:
            raise ValueError("At least 2 profiles required for comparison")
        
        comparison_data = {}
        all_stats = {}
        
        # Load data and calculate statistics for each profile
        for profile_id in profile_ids:
            try:
                df = self.load_profile_data(profile_id)
                stats = self.calculate_comprehensive_statistics(df)
                all_stats[profile_id] = stats
                comparison_data[profile_id] = {
                    'data': df,
                    'statistics': stats
                }
            except Exception as e:
                logger.warning(f"Failed to load profile {profile_id}: {e}")
                continue
        
        if len(comparison_data) < 2:
            raise ValueError("Failed to load sufficient profiles for comparison")
        
        # Define default metrics if not provided
        if metrics is None:
            metrics = [
                'peak_load', 'average_load', 'min_load', 'load_factor', 
                'total_energy', 'peak_to_average_ratio', 'coefficient_of_variation'
            ]
        
        # Create comparison matrix
        comparison_matrix = {}
        for metric in metrics:
            comparison_matrix[metric] = {}
            for profile_id in comparison_data.keys():
                try:
                    value = all_stats[profile_id]['basic'][metric]
                    comparison_matrix[metric][profile_id] = value
                except KeyError:
                    comparison_matrix[metric][profile_id] = None
        
        # Calculate relative differences
        relative_differences = {}
        base_profile = list(comparison_data.keys())[0]
        
        for metric in metrics:
            relative_differences[metric] = {}
            base_value = comparison_matrix[metric].get(base_profile)
            
            if base_value and base_value != 0:
                for profile_id in comparison_data.keys():
                    if profile_id != base_profile:
                        profile_value = comparison_matrix[metric].get(profile_id)
                        if profile_value is not None:
                            diff_percent = ((profile_value - base_value) / base_value) * 100
                            relative_differences[metric][profile_id] = diff_percent
        
        # Find best and worst performers for each metric
        rankings = {}
        for metric in metrics:
            metric_values = {pid: val for pid, val in comparison_matrix[metric].items() if val is not None}
            if metric_values:
                # Assume higher is better for most metrics (except CV)
                ascending = metric in ['coefficient_of_variation', 'peak_to_average_ratio']
                sorted_profiles = sorted(metric_values.items(), key=lambda x: x[1], reverse=not ascending)
                
                rankings[metric] = {
                    'best': sorted_profiles[0],
                    'worst': sorted_profiles[-1],
                    'ranking': sorted_profiles
                }
        
        return {
            'profiles_compared': list(comparison_data.keys()),
            'comparison_matrix': comparison_matrix,
            'relative_differences': relative_differences,
            'rankings': rankings,
            'summary_statistics': {
                profile_id: stats['basic'] for profile_id, stats in all_stats.items()
            }
        }
    
    def export_profile_data(self, profile_id: str, export_format: str = 'csv', 
                          include_metadata: bool = True) -> str:
        """
        Export profile data in various formats
        
        Args:
            profile_id (str): Profile identifier
            export_format (str): Export format ('csv', 'excel', 'json')
            include_metadata (bool): Whether to include metadata
            
        Returns:
            str: Path to exported file
        """
        df = self.load_profile_data(profile_id)
        
        # Create temporary file
        temp_dir = tempfile.mkdtemp()
        
        if export_format.lower() == 'csv':
            export_path = Path(temp_dir) / f"{profile_id}_export.csv"
            df.to_csv(export_path, index=False)
            
        elif export_format.lower() == 'excel':
            export_path = Path(temp_dir) / f"{profile_id}_export.xlsx"
            
            with pd.ExcelWriter(export_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Load_Profile', index=False)
                
                # Add statistics sheet
                stats = self.calculate_comprehensive_statistics(df)
                if stats:
                    stats_df = self._flatten_statistics_for_export(stats)
                    stats_df.to_excel(writer, sheet_name='Statistics', index=False)
                
                # Add metadata if available and requested
                if include_metadata:
                    metadata_file = self.config_dir / f"{profile_id}_metadata.json"
                    if metadata_file.exists():
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        metadata_df = pd.DataFrame(list(metadata.items()), columns=['Key', 'Value'])
                        metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
                        
        elif export_format.lower() == 'json':
            export_path = Path(temp_dir) / f"{profile_id}_export.json"
            
            export_data = {
                'profile_id': profile_id,
                'data': df.to_dict('records'),
                'statistics': self.calculate_comprehensive_statistics(df)
            }
            
            if include_metadata:
                metadata_file = self.config_dir / f"{profile_id}_metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        export_data['metadata'] = json.load(f)
            
            with open(export_path, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
        
        else:
            raise ValueError(f"Unsupported export format: {export_format}")
        
        return str(export_path)
    
    def _flatten_statistics_for_export(self, stats: Dict) -> pd.DataFrame:
        """Flatten nested statistics dictionary for Excel export"""
        flattened = []
        
        def flatten_dict(d, prefix=''):
            for key, value in d.items():
                if isinstance(value, dict):
                    flatten_dict(value, f"{prefix}{key}.")
                else:
                    flattened.append({
                        'Category': prefix.rstrip('.'),
                        'Metric': key,
                        'Value': value
                    })
        
        flatten_dict(stats)
        return pd.DataFrame(flattened)
    
    def create_consolidated_view(self, profile_ids: List[str] = None) -> pd.DataFrame:
        """
        Create a consolidated view of multiple profiles for easy comparison
        
        Args:
            profile_ids (List[str]): List of profile IDs (optional, uses all if None)
            
        Returns:
            pd.DataFrame: Consolidated statistics table
        """
        if profile_ids is None:
            profile_list = self.get_profile_list()
            profile_ids = [p['profile_id'] for p in profile_list]
        
        consolidated_data = []
        
        for profile_id in profile_ids:
            try:
                df = self.load_profile_data(profile_id)
                stats = self.calculate_comprehensive_statistics(df)
                
                # Load metadata
                metadata_file = self.config_dir / f"{profile_id}_metadata.json"
                metadata = {}
                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                
                # Create consolidated row
                row = {
                    'Profile_ID': profile_id,
                    'Generation_Method': metadata.get('method', 'Unknown'),
                    'Generated_Date': metadata.get('generated_at', 'Unknown'),
                    'Start_FY': metadata.get('start_fy', None),
                    'End_FY': metadata.get('end_fy', None),
                    'Total_Records': stats['basic']['count'],
                    'Peak_Load_kW': stats['basic']['peak_load'],
                    'Average_Load_kW': stats['basic']['average_load'],
                    'Min_Load_kW': stats['basic']['min_load'],
                    'Load_Factor_Percent': stats['basic']['load_factor'],
                    'Total_Energy_kWh': stats['basic']['total_energy'],
                    'Peak_to_Average_Ratio': stats['basic']['peak_to_average_ratio'],
                    'Coefficient_of_Variation': stats['basic']['coefficient_of_variation'],
                    'Data_Duration_Days': stats.get('temporal', {}).get('duration_days', 0),
                    'Data_Frequency': stats.get('temporal', {}).get('data_frequency', 'Unknown')
                }
                
                # Add seasonal information if available
                if 'seasonal' in stats:
                    for season in ['Summer', 'Monsoon', 'Winter']:
                        if season in stats['seasonal']:
                            row[f'{season}_Avg_kW'] = stats['seasonal'][season]['mean']
                            row[f'{season}_Peak_kW'] = stats['seasonal'][season]['max']
                
                # Add hourly peak information
                if 'hourly' in stats:
                    row['Peak_Hour'] = stats['hourly']['peak_hour']
                    row['Min_Hour'] = stats['hourly']['min_hour']
                
                consolidated_data.append(row)
                
            except Exception as e:
                logger.warning(f"Failed to process profile {profile_id}: {e}")
                continue
        
        return pd.DataFrame(consolidated_data)

class LoadProfileValidator:
    """
    Validator for load profile data quality and consistency
    """
    
    def __init__(self):
        self.validation_rules = {
            'data_completeness': self._check_data_completeness,
            'temporal_consistency': self._check_temporal_consistency,
            'demand_validity': self._check_demand_validity,
            'pattern_consistency': self._check_pattern_consistency,
            'outlier_detection': self._check_outliers
        }
    
    def validate_profile(self, df: pd.DataFrame) -> Dict:
        """
        Validate a load profile dataset
        
        Args:
            df (pd.DataFrame): Load profile data
            
        Returns:
            Dict: Validation results
        """
        results = {
            'overall_score': 0,
            'issues': [],
            'warnings': [],
            'passed_checks': [],
            'detailed_results': {}
        }
        
        total_checks = len(self.validation_rules)
        passed_checks = 0
        
        for check_name, check_function in self.validation_rules.items():
            try:
                check_result = check_function(df)
                results['detailed_results'][check_name] = check_result
                
                if check_result['status'] == 'pass':
                    passed_checks += 1
                    results['passed_checks'].append(check_name)
                elif check_result['status'] == 'warning':
                    results['warnings'].extend(check_result.get('issues', []))
                else:
                    results['issues'].extend(check_result.get('issues', []))
                    
            except Exception as e:
                logger.error(f"Validation check {check_name} failed: {e}")
                results['issues'].append(f"Validation check {check_name} failed: {str(e)}")
        
        results['overall_score'] = (passed_checks / total_checks) * 100
        
        return results
    
    def _check_data_completeness(self, df: pd.DataFrame) -> Dict:
        """Check data completeness"""
        issues = []
        
        # Check for required columns
        required_columns = ['demand']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            issues.append(f"Missing required columns: {missing_columns}")
        
        # Check for missing values
        if 'demand' in df.columns:
            missing_demand = df['demand'].isna().sum()
            if missing_demand > 0:
                missing_percent = (missing_demand / len(df)) * 100
                if missing_percent > 5:
                    issues.append(f"High percentage of missing demand values: {missing_percent:.1f}%")
                elif missing_percent > 1:
                    issues.append(f"Some missing demand values: {missing_percent:.1f}%")
        
        # Check data length
        if len(df) < 24:
            issues.append("Dataset too small (less than 24 records)")
        
        status = 'pass' if not issues else ('warning' if len(issues) == 1 and 'Some missing' in issues[0] else 'fail')
        
        return {
            'status': status,
            'issues': issues,
            'metrics': {
                'total_records': len(df),
                'missing_demand_count': df['demand'].isna().sum() if 'demand' in df.columns else 0,
                'completeness_ratio': 1 - (df['demand'].isna().sum() / len(df)) if 'demand' in df.columns and len(df) > 0 else 0
            }
        }
    
    def _check_temporal_consistency(self, df: pd.DataFrame) -> Dict:
        """Check temporal consistency"""
        issues = []
        
        if 'ds' in df.columns:
            # Check for duplicates
            duplicates = df['ds'].duplicated().sum()
            if duplicates > 0:
                issues.append(f"Found {duplicates} duplicate timestamps")
            
            # Check for gaps
            df_sorted = df.sort_values('ds')
            time_diffs = df_sorted['ds'].diff().dropna()
            
            if len(time_diffs) > 1:
                mode_diff = time_diffs.mode()
                if not mode_diff.empty:
                    expected_diff = mode_diff.iloc[0]
                    tolerance = expected_diff * 0.1  # 10% tolerance
                    
                    irregular_gaps = (time_diffs < expected_diff - tolerance) | (time_diffs > expected_diff + tolerance)
                    gap_count = irregular_gaps.sum()
                    
                    if gap_count > len(time_diffs) * 0.1:  # More than 10% irregular
                        issues.append(f"Irregular time intervals detected: {gap_count} gaps")
        else:
            issues.append("No timestamp column found for temporal analysis")
        
        status = 'pass' if not issues else ('warning' if len(issues) == 1 and 'irregular' in issues[0].lower() else 'fail')
        
        return {
            'status': status,
            'issues': issues,
            'metrics': {
                'duplicate_timestamps': duplicates if 'ds' in df.columns else 0,
                'temporal_coverage': (df['ds'].max() - df['ds'].min()).days if 'ds' in df.columns and len(df) > 1 else 0
            }
        }
    
    def _check_demand_validity(self, df: pd.DataFrame) -> Dict:
        """Check demand value validity"""
        issues = []
        
        if 'demand' in df.columns:
            demand = df['demand'].dropna()
            
            # Check for negative values
            negative_count = (demand < 0).sum()
            if negative_count > 0:
                issues.append(f"Found {negative_count} negative demand values")
            
            # Check for zero values
            zero_count = (demand == 0).sum()
            if zero_count > len(demand) * 0.1:  # More than 10% zeros
                issues.append(f"High number of zero demand values: {zero_count}")
            
            # Check for extremely high values (outliers)
            if len(demand) > 0:
                q99 = demand.quantile(0.99)
                q01 = demand.quantile(0.01)
                mean_val = demand.mean()
                
                extreme_high = (demand > q99 * 3).sum()
                if extreme_high > 0:
                    issues.append(f"Found {extreme_high} extremely high demand values")
                
                # Check coefficient of variation
                cv = demand.std() / mean_val if mean_val > 0 else 0
                if cv > 2:
                    issues.append(f"Very high demand variability (CV: {cv:.2f})")
        else:
            issues.append("No demand column found")
        
        status = 'pass' if not issues else ('warning' if all('high' in issue.lower() for issue in issues) else 'fail')
        
        return {
            'status': status,
            'issues': issues,
            'metrics': {
                'negative_values': negative_count if 'demand' in df.columns else 0,
                'zero_values': zero_count if 'demand' in df.columns else 0,
                'coefficient_of_variation': cv if 'demand' in df.columns and len(df) > 0 else 0
            }
        }
    
    def _check_pattern_consistency(self, df: pd.DataFrame) -> Dict:
        """Check for consistent load patterns"""
        issues = []
        
        if 'demand' in df.columns and 'hour' in df.columns and len(df) > 24:
            # Check for consistent daily patterns
            daily_patterns = df.groupby(df['ds'].dt.date)['demand'].apply(list) if 'ds' in df.columns else None
            
            if daily_patterns is not None and len(daily_patterns) > 7:
                # Check pattern similarity (simplified)
                hourly_means = df.groupby('hour')['demand'].mean()
                hourly_stds = df.groupby('hour')['demand'].std()
                
                # Check if any hour has extremely high variability
                high_var_hours = (hourly_stds > hourly_means).sum()
                if high_var_hours > 12:  # More than half the hours
                    issues.append("Inconsistent hourly patterns detected")
                
                # Check for reasonable peak hours
                peak_hour = hourly_means.idxmax()
                if peak_hour < 6 or peak_hour > 23:
                    issues.append(f"Unusual peak hour: {peak_hour}:00")
        
        status = 'pass' if not issues else 'warning'
        
        return {
            'status': status,
            'issues': issues,
            'metrics': {
                'pattern_consistency_score': 1 - (len(issues) / 3)  # Simple scoring
            }
        }
    
    def _check_outliers(self, df: pd.DataFrame) -> Dict:
        """Check for statistical outliers"""
        issues = []
        
        if 'demand' in df.columns and len(df) > 10:
            demand = df['demand'].dropna()
            
            # IQR method
            Q1 = demand.quantile(0.25)
            Q3 = demand.quantile(0.75)
            IQR = Q3 - Q1
            
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outliers = ((demand < lower_bound) | (demand > upper_bound)).sum()
            outlier_percentage = (outliers / len(demand)) * 100
            
            if outlier_percentage > 5:
                issues.append(f"High percentage of outliers: {outlier_percentage:.1f}%")
            elif outlier_percentage > 2:
                issues.append(f"Some outliers detected: {outlier_percentage:.1f}%")
        
        status = 'pass' if not issues else ('warning' if 'Some outliers' in str(issues) else 'fail')
        
        return {
            'status': status,
            'issues': issues,
            'metrics': {
                'outlier_count': outliers if 'demand' in df.columns and len(df) > 10 else 0,
                'outlier_percentage': outlier_percentage if 'demand' in df.columns and len(df) > 10 else 0
            }
        }