# utils/load_profile_analyzer.py
"""
Enhanced Load Profile Analyzer with improved error handling and column detection
Fixed issues with profile loading and visualization
"""

import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class LoadProfileAnalyzer:
    """
   load profile analyzer with improved error handling
    """
    
    def __init__(self, project_path: str):
        """Initialize analyzer for a specific project"""
        self.project_path = Path(project_path)
        self.profiles_dir = self.project_path / 'results' / 'load_profiles'
        self.config_dir = self.project_path / 'config'
        
        # Ensure directories exist
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Unit conversion factors
        self.unit_factors = {
            'kW': 1,
            'MW': 1000,
            'GW': 1000000
        }
        
        logger.info(f"LoadProfileAnalyzer initialized for: {project_path}")
    
    def get_available_profiles(self) -> List[Dict[str, Any]]:
        """Get all available profiles with comprehensive metadata"""
        profiles = []
        
        if not self.profiles_dir.exists():
            logger.warning(f"Profiles directory does not exist: {self.profiles_dir}")
            return profiles
        
        for csv_file in self.profiles_dir.glob('*.csv'):
            profile_id = csv_file.stem
            
            try:
                # Get file information
                file_stat = csv_file.stat()
                file_info = {
                    'size_bytes': file_stat.st_size,
                    'size_mb': round(file_stat.st_size / (1024 * 1024), 2),
                    'modified': datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                    'created': datetime.fromtimestamp(file_stat.st_ctime).isoformat()
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
                
                # Quick data preview for statistics
                preview_stats = self._get_quick_preview(csv_file)
                
                profile_info = {
                    'profile_id': profile_id,
                    'file_info': file_info,
                    'metadata': metadata,
                    'preview_stats': preview_stats,
                    'method': metadata.get('method', 'Unknown'),
                    'generated_at': metadata.get('generated_at', 'Unknown'),
                    'start_fy': metadata.get('start_fy'),
                    'end_fy': metadata.get('end_fy'),
                    'frequency': metadata.get('output_format', {}).get('total_hours', 'Unknown'),
                    'units': metadata.get('output_format', {}).get('demand_unit', 'kW')
                }
                
                profiles.append(profile_info)
                
            except Exception as e:
                logger.error(f"Error processing profile {profile_id}: {e}")
                continue
        
        # Sort by creation date (newest first)
        return sorted(profiles, key=lambda x: x['file_info']['created'], reverse=True)
    

    def _get_quick_preview(self, csv_file: Path) -> Dict[str, Any]:
        """Quickly previews a CSV file, robustly checking for a demand column."""
        try:
            # FIX: Replace the removed 'sniff_delimiter' with the modern method.
            # Use sep=None and engine='python' to auto-detect the delimiter.
            df = pd.read_csv(csv_file, sep=None, engine='python', on_bad_lines='warn', nrows=100)

            if df.empty:
                return {'error': 'File is empty'}
            
            # Standardize and find demand column
            df_std = self._standardize_columns(df.copy())
            demand_col_std = 'demand' if 'demand' in df_std.columns else None

            if not demand_col_std:
                return {'error': 'No demand column found', 'columns': list(df.columns)}

            demand_data = pd.to_numeric(df_std[demand_col_std], errors='coerce').dropna()
            if demand_data.empty:
                return {'error': 'Demand data is not numeric'}

            return {
                'peak_demand': float(demand_data.max()),
                'avg_demand': float(demand_data.mean()),
                'valid_data_points': len(demand_data)
            }
        except Exception as e:
            logger.warning(f"Failed to generate preview for {csv_file}: {e}")
            return {'error': str(e)}

    def _identify_demand_column(self, df: pd.DataFrame) -> Optional[str]:
        """ demand column identification"""
        if df.empty:
            return None
            
        # Priority order for demand column names (expanded list)
        demand_candidates = [
            'Demand (kW)', 'demand', 'Demand', 'Load', 'load', 
            'Power', 'power', 'kW', 'MW', 'GW',
            'Demand_kW', 'demand_kw', 'Load_kW', 'load_kw',
            'consumption', 'Consumption', 'energy', 'Energy',
            'load_kw', 'load_mw', 'demand_mw'
        ]
        
        # Check exact matches first (case sensitive)
        for candidate in demand_candidates:
            if candidate in df.columns:
                logger.debug(f"Found exact match for demand column: {candidate}")
                return candidate
        
        # Check case-insensitive matches
        for candidate in demand_candidates:
            for col in df.columns:
                if col.lower() == candidate.lower():
                    logger.debug(f"Found case-insensitive match for demand column: {col}")
                    return col
        
        # Look for columns containing demand-related keywords
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['demand', 'load', 'power', 'consumption', 'energy']):
                logger.debug(f"Found keyword match for demand column: {col}")
                return col
        
        # If still no match, check for numeric columns (might be unlabeled demand data)
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        if len(numeric_columns) > 0:
            # Return first numeric column as potential demand column
            logger.warning(f"No demand column found by name, using first numeric column: {numeric_columns[0]}")
            return numeric_columns[0]
        
        return None
    
    def _identify_datetime_column(self, df: pd.DataFrame) -> Optional[str]:
        """Identify datetime column in the dataframe"""
        if df.empty:
            return None
        
        # Priority order for datetime column names
        datetime_candidates = [
            'datetime', 'timestamp', 'ds', 'date_time', 'time', 'date'
        ]
        
        # Check exact matches first
        for candidate in datetime_candidates:
            if candidate in df.columns:
                return candidate
        
        # Check case-insensitive matches
        for candidate in datetime_candidates:
            for col in df.columns:
                if col.lower() == candidate.lower():
                    return col
        
        # Look for columns that might contain datetime data
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['date', 'time', 'timestamp']):
                return col
        
        return None


    def load_profile_data(self, profile_id: str, filters: Optional[Dict] = None) -> pd.DataFrame:
        """Loads, standardizes, and cleans profile data with robust error handling."""
        csv_path = self.profiles_dir / f"{profile_id}.csv"
        if not csv_path.exists():
            raise FileNotFoundError(f"Profile '{profile_id}' not found.")
        
        try:
            # FIX: Replace the removed 'sniff_delimiter' with the modern method.
            df = pd.read_csv(csv_path, sep=None, engine='python', on_bad_lines='warn')

            if df.empty:
                raise ValueError("CSV file is empty.")

            df = self._standardize_columns(df)
            df = self._clean_data(df)

            if df.empty:
                raise ValueError("No valid data remains after cleaning.")

            if filters:
                df = self._apply_filters(df, filters)
                if df.empty:
                    raise ValueError(f"No data available after applying filters: {filters}")
            
            return df
        except (FileNotFoundError, ValueError) as e:
            raise e # Re-raise known errors
        except Exception as e:
            logger.exception(f"Unexpected error loading profile {profile_id}: {e}")
            raise ValueError(f"Failed to parse CSV file for profile '{profile_id}'. It may be corrupted.")

    def _standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        FIX: Rewritten for maximum robustness.
        Cleans column names and maps them to standard internal names.
        """
        # Create a mapping from various possible names (lowercase) to a standard name.
        column_map = {
            'demand (kw)': 'demand', 'demand': 'demand', 'load': 'demand', 'power': 'demand',
            'datetime': 'ds', 'timestamp': 'ds', 'date': 'date', 'time': 'time',
            'fiscal_year': 'financial_year', 'year': 'year', 'hour': 'hour'
        }
        
        # Create a dictionary to rename columns, after stripping whitespace and converting to lowercase.
        rename_dict = {col: column_map[col.strip().lower()] for col in df.columns if col.strip().lower() in column_map}
        df = df.rename(columns=rename_dict)
        
        # Ensure 'ds' (datetime) column exists, creating it if necessary.
        if 'ds' not in df.columns:
            if 'date' in df.columns and 'time' in df.columns:
                df['ds'] = pd.to_datetime(df['date'].astype(str) + ' ' + df['time'].astype(str), errors='coerce')
            elif 'date' in df.columns:
                df['ds'] = pd.to_datetime(df['date'], errors='coerce')

        # Add time features if 'ds' is available and valid.
        if 'ds' in df.columns:
            df['ds'] = pd.to_datetime(df['ds'], errors='coerce')
            df.dropna(subset=['ds'], inplace=True) # Remove rows where date could not be parsed
            if not df.empty:
                df = self._add_time_features(df)
                
        return df

    def _create_datetime_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """ datetime column creation with better error handling"""
        logger.debug("Creating datetime column")
        
        # Try to find existing datetime column first
        datetime_col = self._identify_datetime_column(df)
        if datetime_col:
            logger.debug(f"Found existing datetime column: {datetime_col}")
            df['ds'] = df[datetime_col]
            return df
        
        # Try to create from date and time columns
        if 'date_str' in df.columns and 'time_str' in df.columns:
            logger.debug("Creating datetime from separate date and time columns")
            try:
                df['ds'] = pd.to_datetime(
                    df['date_str'].astype(str) + ' ' + df['time_str'].astype(str),
                    format='%Y-%m-%d %H:%M:%S',
                    errors='coerce'
                )
                if df['ds'].isna().all():
                    # Try alternative format
                    df['ds'] = pd.to_datetime(
                        df['date_str'].astype(str) + ' ' + df['time_str'].astype(str),
                        dayfirst=True,
                        errors='coerce'
                    )
            except Exception as e:
                logger.warning(f"Failed to parse datetime from date/time columns: {e}")
        
        elif 'date_str' in df.columns:
            logger.debug("Creating datetime from date column only")
            try:
                df['ds'] = pd.to_datetime(df['date_str'], errors='coerce')
            except Exception as e:
                logger.warning(f"Failed to parse datetime from date column: {e}")
        
        # If still no valid datetime column, create sequential timestamps
        if 'ds' not in df.columns or df['ds'].isna().all():
            logger.info("Creating sequential hourly timestamps")
            start_date = datetime(2025, 4, 1)  # April 1st
            df['ds'] = pd.date_range(start=start_date, periods=len(df), freq='H')
        
        return df
    

    def _add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Adds derived time-based columns for analysis."""
        df['hour'] = df['ds'].dt.hour
        df['day_of_week'] = df['ds'].dt.dayofweek
        df['month'] = df['ds'].dt.month
        df['year'] = df['ds'].dt.year
        df['day_name'] = df['ds'].dt.day_name()
        df['financial_year'] = df['ds'].apply(lambda x: x.year + 1 if x.month >= 4 else x.year)
        season_map = {
            12: 'Winter', 1: 'Winter', 2: 'Winter', 3: 'Summer', 4: 'Summer',
            5: 'Summer', 6: 'Summer', 7: 'Monsoon', 8: 'Monsoon',
            9: 'Monsoon', 10: 'Monsoon', 11: 'Monsoon'
        }
        df['season'] = df['month'].map(season_map)
        df['day_type'] = np.where(df['day_of_week'].isin([5, 6]), 'Weekend', 'Weekday')
        return df


    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensures the demand column is numeric and removes invalid values."""
        if 'demand' not in df.columns:
            raise ValueError("Standardization failed: 'demand' column not found.")
        
        original_count = len(df)
        df['demand'] = pd.to_numeric(df['demand'], errors='coerce')
        
        # Remove rows with non-numeric or negative demand values
        df.dropna(subset=['demand'], inplace=True)
        df = df[df['demand'] >= 0]
        
        cleaned_count = len(df)
        if original_count != cleaned_count:
            logger.info(f"Data cleaning removed {original_count - cleaned_count} invalid rows.")
        
        return df.sort_values('ds').reset_index(drop=True) if 'ds' in df.columns else df

    def _apply_filters(self, df: pd.DataFrame, filters: Dict) -> pd.DataFrame:
        """ filter application with validation"""
        filtered_df = df.copy()
        applied_filters = []
        
        try:
            # Year filter
            if filters.get('year') and 'financial_year' in filtered_df.columns:
                year = int(filters['year'])
                before_count = len(filtered_df)
                filtered_df = filtered_df[filtered_df['financial_year'] == year]
                after_count = len(filtered_df)
                applied_filters.append(f"year={year} ({before_count}->{after_count})")
            
            # Month filter
            if filters.get('month') and 'month' in filtered_df.columns:
                month = int(filters['month'])
                before_count = len(filtered_df)
                filtered_df = filtered_df[filtered_df['month'] == month]
                after_count = len(filtered_df)
                applied_filters.append(f"month={month} ({before_count}->{after_count})")
            
            # Season filter
            if filters.get('season') and filters['season'] != 'all' and 'season' in filtered_df.columns:
                season = filters['season']
                before_count = len(filtered_df)
                filtered_df = filtered_df[filtered_df['season'] == season]
                after_count = len(filtered_df)
                applied_filters.append(f"season={season} ({before_count}->{after_count})")
            
            # Day type filter
            if filters.get('day_type') and filters['day_type'] != 'all' and 'day_type' in filtered_df.columns:
                day_type = filters['day_type']
                before_count = len(filtered_df)
                filtered_df = filtered_df[filtered_df['day_type'] == day_type]
                after_count = len(filtered_df)
                applied_filters.append(f"day_type={day_type} ({before_count}->{after_count})")
            
            # Date range filter
            if filters.get('start_date') and filters.get('end_date') and 'ds' in filtered_df.columns:
                start_date = pd.to_datetime(filters['start_date'])
                end_date = pd.to_datetime(filters['end_date'])
                before_count = len(filtered_df)
                filtered_df = filtered_df[
                    (filtered_df['ds'] >= start_date) & 
                    (filtered_df['ds'] <= end_date)
                ]
                after_count = len(filtered_df)
                applied_filters.append(f"date_range ({before_count}->{after_count})")
            
            if applied_filters:
                logger.info(f"Applied filters: {', '.join(applied_filters)}")
            
        except Exception as e:
            logger.error(f"Error applying filters: {e}")
            
        return filtered_df
    

    
    def calculate_comprehensive_statistics(self, df: pd.DataFrame, unit: str = 'kW') -> Dict[str, Any]:
        """Calculate comprehensive statistics for visualization"""
        if df.empty or 'demand' not in df.columns:
            return {'error': 'No valid data for statistics calculation'}
        
        # Apply unit conversion
        unit_factor = self.unit_factors.get(unit, 1)
        demand_values = df['demand'] * unit_factor
        
        stats = {}
        
        try:
            # Basic statistics
            stats['basic'] = {
                'count': len(df),
                'peak_load': float(demand_values.max()),
                'min_load': float(demand_values.min()),
                'average_load': float(demand_values.mean()),
                'median_load': float(demand_values.median()),
                'std_dev': float(demand_values.std()),
                'variance': float(demand_values.var()),
                'coefficient_of_variation': float(demand_values.std() / demand_values.mean()) if demand_values.mean() > 0 else 0,
                'load_factor': float((demand_values.mean() / demand_values.max()) * 100) if demand_values.max() > 0 else 0,
                'total_energy': float(demand_values.sum()),
                'peak_to_average_ratio': float(demand_values.max() / demand_values.mean()) if demand_values.mean() > 0 else 0,
                'unit': unit
            }
            
            # Time-based statistics
            if 'ds' in df.columns:
                peak_idx = demand_values.idxmax()
                min_idx = demand_values.idxmin()
                
                stats['temporal'] = {
                    'peak_datetime': df.loc[peak_idx, 'ds'].isoformat() if pd.notna(df.loc[peak_idx, 'ds']) else None,
                    'min_datetime': df.loc[min_idx, 'ds'].isoformat() if pd.notna(df.loc[min_idx, 'ds']) else None,
                    'date_range_start': df['ds'].min().isoformat() if pd.notna(df['ds'].min()) else None,
                    'date_range_end': df['ds'].max().isoformat() if pd.notna(df['ds'].max()) else None,
                    'duration_hours': len(df),
                    'duration_days': (df['ds'].max() - df['ds'].min()).days + 1 if pd.notna(df['ds'].max()) and pd.notna(df['ds'].min()) else 0,
                    'data_frequency': self._infer_frequency(df['ds'])
                }
            
            # Pattern analysis with error handling
            if 'hour' in df.columns:
                try:
                    stats['hourly_patterns'] = self._calculate_hourly_patterns(df, unit_factor)
                except Exception as e:
                    logger.warning(f"Failed to calculate hourly patterns: {e}")
            
            if 'day_type' in df.columns:
                try:
                    stats['daily_patterns'] = self._calculate_daily_patterns(df, unit_factor)
                except Exception as e:
                    logger.warning(f"Failed to calculate daily patterns: {e}")
            
            if 'season' in df.columns:
                try:
                    stats['seasonal_patterns'] = self._calculate_seasonal_patterns(df, unit_factor)
                except Exception as e:
                    logger.warning(f"Failed to calculate seasonal patterns: {e}")
            
            if 'month' in df.columns:
                try:
                    stats['monthly_patterns'] = self._calculate_monthly_patterns(df, unit_factor)
                except Exception as e:
                    logger.warning(f"Failed to calculate monthly patterns: {e}")
            
            if 'financial_year' in df.columns and df['financial_year'].nunique() > 1:
                try:
                    stats['annual_patterns'] = self._calculate_annual_patterns(df, unit_factor)
                except Exception as e:
                    logger.warning(f"Failed to calculate annual patterns: {e}")
            
            # Load duration analysis
            try:
                stats['load_duration'] = self._calculate_load_duration(demand_values)
            except Exception as e:
                logger.warning(f"Failed to calculate load duration: {e}")
            
            # Variability analysis
            try:
                stats['variability'] = self._calculate_variability(demand_values)
            except Exception as e:
                logger.warning(f"Failed to calculate variability: {e}")
            
        except Exception as e:
            logger.error(f"Error calculating statistics: {e}")
            stats['error'] = str(e)
        
        return stats
    
    # Include all the other calculation methods from the original code...
    # (They remain the same but should be included for completeness)
    
    def _calculate_hourly_patterns(self, df: pd.DataFrame, unit_factor: float) -> Dict[str, Any]:
        """Calculate hourly patterns"""
        hourly_stats = df.groupby('hour')['demand'].agg(['mean', 'max', 'min', 'std', 'count']).round(4)
        
        # Apply unit conversion
        for col in ['mean', 'max', 'min', 'std']:
            hourly_stats[col] = hourly_stats[col] * unit_factor
        
        return {
            'patterns': hourly_stats.to_dict('index'),
            'peak_hour': int(hourly_stats['mean'].idxmax()),
            'min_hour': int(hourly_stats['mean'].idxmin()),
            'morning_peak': self._find_peak_in_range(hourly_stats['mean'], 6, 12),
            'evening_peak': self._find_peak_in_range(hourly_stats['mean'], 18, 23)
        }
    
    def _calculate_daily_patterns(self, df: pd.DataFrame, unit_factor: float) -> Dict[str, Any]:
        """Calculate daily patterns (weekday vs weekend)"""
        daily_stats = df.groupby('day_type')['demand'].agg(['mean', 'max', 'min', 'std']).round(4)
        
        # Apply unit conversion
        for col in ['mean', 'max', 'min', 'std']:
            daily_stats[col] = daily_stats[col] * unit_factor
        
        result = {'summary': daily_stats.to_dict('index')}
        
        # Hourly patterns by day type
        if 'hour' in df.columns:
            weekday_pattern = df[df['day_type'] == 'Weekday'].groupby('hour')['demand'].mean() * unit_factor
            weekend_pattern = df[df['day_type'] == 'Weekend'].groupby('hour')['demand'].mean() * unit_factor
            
            result['hourly_patterns'] = {
                'weekday': weekday_pattern.round(4).to_dict(),
                'weekend': weekend_pattern.round(4).to_dict(),
                'weekend_to_weekday_ratio': float(weekend_pattern.mean() / weekday_pattern.mean()) if weekday_pattern.mean() > 0 else 0
            }
        
        return result
    
    def _calculate_seasonal_patterns(self, df: pd.DataFrame, unit_factor: float) -> Dict[str, Any]:
        """Calculate seasonal patterns"""
        seasonal_stats = df.groupby('season')['demand'].agg(['mean', 'max', 'min', 'sum', 'std']).round(4)
        
        # Apply unit conversion
        for col in ['mean', 'max', 'min', 'sum', 'std']:
            seasonal_stats[col] = seasonal_stats[col] * unit_factor
        
        # Calculate seasonal load factors
        seasonal_load_factors = {}
        for season in seasonal_stats.index:
            season_data = df[df['season'] == season]['demand'] * unit_factor
            if len(season_data) > 0 and season_data.max() > 0:
                seasonal_load_factors[season] = float((season_data.mean() / season_data.max()) * 100)
        
        return {
            'summary': seasonal_stats.to_dict('index'),
            'load_factors': seasonal_load_factors
        }
    
    def _calculate_monthly_patterns(self, df: pd.DataFrame, unit_factor: float) -> Dict[str, Any]:
        """Calculate monthly patterns"""
        monthly_stats = df.groupby('month')['demand'].agg(['mean', 'max', 'min', 'sum', 'std']).round(4)
        
        # Apply unit conversion
        for col in ['mean', 'max', 'min', 'sum', 'std']:
            monthly_stats[col] = monthly_stats[col] * unit_factor
        
        return {
            'summary': monthly_stats.to_dict('index'),
            'month_names': {i: datetime(2000, i, 1).strftime('%B') for i in monthly_stats.index}
        }
    
    def _calculate_annual_patterns(self, df: pd.DataFrame, unit_factor: float) -> Dict[str, Any]:
        """Calculate annual patterns"""
        annual_stats = df.groupby('financial_year')['demand'].agg(['mean', 'max', 'min', 'sum', 'std']).round(4)
        
        # Apply unit conversion
        for col in ['mean', 'max', 'min', 'sum', 'std']:
            annual_stats[col] = annual_stats[col] * unit_factor
        
        # Calculate growth rates
        years = sorted(annual_stats.index)
        growth_rates = {}
        if len(years) > 1:
            for i in range(1, len(years)):
                prev_year = years[i-1]
                curr_year = years[i]
                if annual_stats.loc[prev_year, 'sum'] > 0:
                    growth_rate = ((annual_stats.loc[curr_year, 'sum'] - annual_stats.loc[prev_year, 'sum']) / 
                                 annual_stats.loc[prev_year, 'sum']) * 100
                    growth_rates[f"{prev_year}_to_{curr_year}"] = round(float(growth_rate), 2)
        
        return {
            'summary': annual_stats.to_dict('index'),
            'growth_rates': growth_rates
        }
    
    def _calculate_load_duration(self, demand_values: pd.Series) -> Dict[str, Any]:
        """Calculate load duration curve analysis"""
        sorted_demands = np.sort(demand_values.values)[::-1]  # Descending order
        total_hours = len(sorted_demands)
        
        percentiles = [1, 5, 10, 25, 50, 75, 90, 95, 99]
        duration_percentiles = {}
        
        for p in percentiles:
            idx = int((p / 100) * total_hours)
            if idx < total_hours:
                duration_percentiles[f'p{p}'] = round(float(sorted_demands[idx]), 4)
        
        return {
            'percentiles': duration_percentiles,
            'base_load': round(float(np.percentile(sorted_demands, 10)), 4),  # Bottom 10%
            'intermediate_load': round(float(np.percentile(sorted_demands, 50)), 4),  # Median
            'peak_load_hours': int(total_hours * 0.1),  # Top 10% hours
            'capacity_factor': round(float(demand_values.mean() / demand_values.max()), 6) if demand_values.max() > 0 else 0,
            'sorted_demands': sorted_demands.tolist()[:min(8760, len(sorted_demands))]  # Limit for performance
        }
    
    def _calculate_variability(self, demand_values: pd.Series) -> Dict[str, Any]:
        """Calculate variability analysis"""
        if len(demand_values) < 2:
            return {}
        
        # Calculate differences for ramp rate analysis
        demand_diff = demand_values.diff().dropna()
        
        return {
            'range': round(float(demand_values.max() - demand_values.min()), 4),
            'interquartile_range': round(float(demand_values.quantile(0.75) - demand_values.quantile(0.25)), 4),
            'coefficient_of_variation': round(float(demand_values.std() / demand_values.mean()), 6) if demand_values.mean() > 0 else 0,
            'ramp_rate_mean': round(float(demand_diff.abs().mean()), 4),
            'ramp_rate_max': round(float(demand_diff.abs().max()), 4),
            'ramp_rate_std': round(float(demand_diff.abs().std()), 4),
            'ramp_rate_95th': round(float(demand_diff.abs().quantile(0.95)), 4)
        }
    
    def _find_peak_in_range(self, hourly_data: pd.Series, start_hour: int, end_hour: int) -> Dict[str, Any]:
        """Find peak within a specific hour range"""
        try:
            available_hours = set(hourly_data.index)
            range_hours = set(range(start_hour, end_hour + 1))
            valid_hours = available_hours.intersection(range_hours)
            
            if not valid_hours:
                return {'hour': None, 'value': None}
            
            range_data = hourly_data[hourly_data.index.isin(valid_hours)]
            
            if range_data.empty:
                return {'hour': None, 'value': None}
            
            peak_hour = range_data.idxmax()
            peak_value = range_data.max()
            
            return {
                'hour': int(peak_hour),
                'value': round(float(peak_value), 4)
            }
        except Exception as e:
            logger.warning(f"Error finding peak in range {start_hour}-{end_hour}: {e}")
            return {'hour': None, 'value': None}
    
    def _infer_frequency(self, timestamps: pd.Series) -> str:
        """Infer the frequency of timestamp data"""
        if len(timestamps) < 2:
            return "unknown"
        
        diff = timestamps.diff().dropna()
        if diff.empty:
            return "unknown"
        
        # Get the most common time difference
        mode_diff = diff.mode()
        if mode_diff.empty:
            return "unknown"
        
        mode_seconds = mode_diff.iloc[0].total_seconds()
        
        frequency_map = {
            3600: "hourly",
            1800: "30min", 
            900: "15min",
            86400: "daily",
            604800: "weekly"
        }
        
        return frequency_map.get(mode_seconds, f"{int(mode_seconds)}s")
    
    # ... Rest of the methods (generate_analysis_data, compare_profiles, etc.) remain the same
    
    def generate_analysis_data(self, df: pd.DataFrame, analysis_type: str, unit: str = 'kW') -> Dict[str, Any]:
        """Generate specific analysis data for visualization"""
        try:
            # Apply unit conversion
            unit_factor = self.unit_factors.get(unit, 1)
            if unit_factor != 1:
                df = df.copy()
                df['demand'] = df['demand'] * unit_factor
            
            analysis_generators = {
                'overview': self._generate_overview_analysis,
                'peak_analysis': self._generate_peak_analysis,
                'weekday_weekend': self._generate_weekday_weekend_analysis,
                'seasonal': self._generate_seasonal_analysis,
                'monthly': self._generate_monthly_analysis,
                'duration_curve': self._generate_duration_curve_analysis,
                'heatmap': self._generate_heatmap_analysis
            }
            
            generator = analysis_generators.get(analysis_type)
            if not generator:
                return {'error': f'Unknown analysis type: {analysis_type}'}
            
            return generator(df, unit)
                
        except Exception as e:
            logger.error(f"Error generating {analysis_type} analysis: {e}")
            return {'error': str(e)}
    
    def _generate_overview_analysis(self, df: pd.DataFrame, unit: str) -> Dict[str, Any]:
        """Generate overview analysis with time series data"""
        if df.empty or 'demand' not in df.columns:
            return {'error': 'No data available for overview analysis'}
        
        # Sample data if too large for performance
        sample_size = min(8760, len(df))  # Max one year of hourly data
        if len(df) > sample_size:
            # Smart sampling - take every nth point to maintain pattern
            step = len(df) // sample_size
            sample_df = df.iloc[::step].copy()
        else:
            sample_df = df.copy()
        
        sample_df = sample_df.sort_values('ds' if 'ds' in sample_df.columns else sample_df.index)
        
        # Prepare data for visualization
        data = {
            'timestamps': sample_df['ds'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist() if 'ds' in sample_df.columns else list(range(len(sample_df))),
            'demand': sample_df['demand'].round(4).tolist()
        }
        
        # Find peak and minimum points
        peak_idx = sample_df['demand'].idxmax()
        min_idx = sample_df['demand'].idxmin()
        
        data['peak_point'] = {
            'timestamp': sample_df.loc[peak_idx, 'ds'].strftime('%Y-%m-%d %H:%M:%S') if 'ds' in sample_df.columns else peak_idx,
            'demand': round(float(sample_df.loc[peak_idx, 'demand']), 4),
            'index': list(sample_df.index).index(peak_idx)
        }
        
        data['min_point'] = {
            'timestamp': sample_df.loc[min_idx, 'ds'].strftime('%Y-%m-%d %H:%M:%S') if 'ds' in sample_df.columns else min_idx,
            'demand': round(float(sample_df.loc[min_idx, 'demand']), 4),
            'index': list(sample_df.index).index(min_idx)
        }
        
        return {
            'chart_type': 'line',
            'title': f'Load Profile Overview ({unit})',
            'data': data,
            'unit': unit,
            'sample_info': {
                'total_records': len(df),
                'displayed_records': len(sample_df),
                'sampling_ratio': len(sample_df) / len(df)
            }
        }
    

    
    def get_profile_fiscal_years(self, profile_id: str) -> List[int]:
        """Get available fiscal years for a specific profile"""
        try:
            df = self.load_profile_data(profile_id)
            
            if 'financial_year' in df.columns:
                fiscal_years = sorted(df['financial_year'].dropna().unique().astype(int).tolist())
            else:
                fiscal_years = []
            
            return fiscal_years
            
        except Exception as e:
            logger.error(f"Error getting fiscal years for {profile_id}: {e}")
            return []