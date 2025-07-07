# utils/load_profile_engine.py
#Load Profile Generation Engine - Main Orchestrator

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
import logging
from dataclasses import dataclass, asdict
import json
import os
from abc import ABC, abstractmethod
import warnings
from pathlib import Path

warnings.filterwarnings('ignore', category=FutureWarning)
logger = logging.getLogger(__name__)

# =====================================================================
#CONFIGURATION CLASSES
# =====================================================================

@dataclass
class LoadProfileConfig:
    """ configuration for load profile generation"""
    # Core methodology
    methodology: str = 'base_year_scaling'  # 'base_year_scaling', 'stl_decomposition', 'statistical_pattern'
    
    # Time configuration
    base_year: int = 2023
    start_year: int = 2025
    end_year: int = 2035
    fiscal_year_start_month: int = 4
    
    # Data source
    scenario_name: Optional[str] = None
    use_excel_totals: bool = True
    custom_totals: Optional[Dict[int, float]] = None
    
    # Shape preservation (critical requirement)
    preserve_exact_shape: bool = True
    preserve_hourly_patterns: bool = True
    preserve_daily_patterns: bool = True
    preserve_weekly_patterns: bool = True
    preserve_seasonal_ratios: bool = True
    preserve_load_factors: bool = True
    
    # Load shifting configuration
    enable_load_shifting: bool = False
    load_shift_rules: Optional[List[Dict]] = None
    gradual_shift_implementation: bool = True
    shift_implementation_years: int = 5
    peak_shifting_hours: Optional[Dict[int, int]] = None  # {from_hour: to_hour}
    load_shift_percentage: float = 10.0  # Percentage of load to shift
    
    # Quality controls
    energy_conservation_tolerance: float = 0.001  # 0.1%
    apply_realistic_noise: bool = True
    noise_level: float = 0.02  # 2%
    apply_light_smoothing: bool = True
    
    # Output configuration
    output_frequency: str = 'hourly'
    output_unit: str = 'kW'
    include_metadata: bool = True
    
    # Advanced options
    handle_leap_years: bool = True
    interpolate_missing_data: bool = True
    validate_data_quality: bool = True

@dataclass
class LoadShiftRule:
    """ load shifting rule configuration"""
    from_hour: int
    to_hour: int
    shift_percentage: float = 10.0
    days_of_week: Optional[List[int]] = None  # [0-6] Monday=0
    months: Optional[List[int]] = None  # [1-12]
    start_year: Optional[int] = None
    ramp_up_years: int = 3
    shift_type: str = 'linear'  # 'linear', 'exponential', 'step'

# =====================================================================
# DATA FLOW AGENTS (Enhanced)
# =====================================================================

class DataFlowAgent:
    """ agent for data ingestion, validation, and preparation"""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.inputs_folder = self.project_path / 'inputs'
        self.results_folder = self.project_path / 'results'
        self.cache = {}
        
        # Ensure directories exist
        self.inputs_folder.mkdir(parents=True, exist_ok=True)
        self.results_folder.mkdir(parents=True, exist_ok=True)
    

    def load_target_totals(self, config: LoadProfileConfig) -> Dict[int, float]:
        """Load target annual totals with comprehensive validation"""
        logger.info("Loading target annual totals")
        
        if config.custom_totals:
            return self._validate_custom_totals(config.custom_totals, config)
        elif config.scenario_name:
            return self._load_scenario_totals(config.scenario_name, config)
        else:
            return self._load_excel_totals(config)
    
    def prepare_base_year_data(self, df: pd.DataFrame, config: LoadProfileConfig) -> pd.DataFrame:
        """Prepare base year data withprocessing"""
        logger.info(f"Preparing base year data for FY {config.base_year}")
        
        # Add comprehensive time features
        df = self._add_comprehensive_time_features(df, config.fiscal_year_start_month)
        
        # Filter for base year
        base_data = df[df['fiscal_year'] == config.base_year].copy()
        
        if base_data.empty:
            raise ValueError(f"No data found for fiscal year {config.base_year}")
        
        # Sort and clean
        base_data = base_data.sort_values('datetime').reset_index(drop=True)
        
        # Handle missing values with pattern-aware interpolation
        if config.interpolate_missing_data:
            base_data = self._intelligent_interpolation(base_data)
        
        # Validate completeness
        self._validate_base_year_completeness(base_data, config)
        
        logger.info(f"Prepared {len(base_data)} records for base year {config.base_year}")
        return base_data


    def _find_specific_column(self, df: pd.DataFrame, keywords: List[str], exclude: List[str] = None) -> Optional[str]:
        """Helper to find a column matching specific keywords, optionally excluding others."""
        for col in df.columns:
            col_lower_norm = str(col).lower().replace(' ', '_').replace('-', '_')
            if exclude and any(ex_kw in col_lower_norm for ex_kw in exclude):
                continue
            if any(keyword in col_lower_norm for keyword in keywords):
                return col
        return None


    def _comprehensive_data_validation(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        validation_report = {
            'original_records': len(df),
            'issues_found': [],
            'fixes_applied': [],
            'data_quality_score': 0.0,
            'completeness_score': 0.0,
            'consistency_score': 0.0
        }

        datetime_col_found = False
        datetime_col_name_in_df = 'datetime'

        # Find datetime column - SIMPLIFIED AND FIXED
        datetime_col = None
        for col in df.columns:
            col_lower = str(col).lower().replace(' ', '_').replace('-', '_')
            if any(keyword in col_lower for keyword in ['datetime', 'timestamp', 'date_time']):
                datetime_col = col
                break
        
        # If no single datetime column, look for separate date and time columns
        if not datetime_col:
            date_col = None
            time_col = None
            
            for col in df.columns:
                col_lower = str(col).lower().replace(' ', '_').replace('-', '_')
                if 'date' in col_lower and not any(ex in col_lower for ex in ['datetime', 'timestamp']):
                    date_col = col
                elif 'time' in col_lower and not any(ex in col_lower for ex in ['datetime', 'timestamp']):
                    time_col = col
            
            if date_col and time_col:
                try:
                    df[datetime_col_name_in_df] = pd.to_datetime(
                        df[date_col].astype(str) + ' ' + df[time_col].astype(str)
                    )
                    validation_report['fixes_applied'].append(f"Combined '{date_col}' and '{time_col}' into 'datetime'")
                    datetime_col_found = True
                except Exception as e:
                    validation_report['issues_found'].append(f"Could not combine date/time columns: {e}")
            elif date_col:
                df = df.rename(columns={date_col: datetime_col_name_in_df})
                datetime_col_found = True
        else:
            df = df.rename(columns={datetime_col: datetime_col_name_in_df})
            datetime_col_found = True

        if not datetime_col_found:
            raise ValueError("No suitable datetime column found. Expected 'datetime' or separate 'date'/'time' columns.")

        # Find demand column - FIXED
        demand_col = None
        for col in df.columns:
            col_lower = str(col).lower().replace(' ', '_').replace('-', '_')
            if any(keyword in col_lower for keyword in ['demand', 'load', 'power', 'kw', 'consumption']):
                if col != datetime_col_name_in_df:  # Don't rename datetime column
                    demand_col = col
                    break

        if not demand_col:
            raise ValueError("No demand column found. Expected columns: demand, load, power, kw, consumption")

        df = df.rename(columns={demand_col: 'demand'})

        # Data type conversion with validation
        try:
            df[datetime_col_name_in_df] = pd.to_datetime(df[datetime_col_name_in_df])
            df['demand'] = pd.to_numeric(df['demand'])
        except Exception as e:s
            validation_report['issues_found'].append(f"Data type conversion failed: {e}")

        # Remove invalid rows
        initial_count = len(df)

        # Remove rows with invalid datetime
        invalid_datetime = df[datetime_col_name_in_df].isna()
        if invalid_datetime.any():
            df = df[~invalid_datetime]
            validation_report['issues_found'].append(f"Removed {invalid_datetime.sum()} rows with invalid datetime")

        # Handle negative demands
        negative_demands = df['demand'] < 0
        if negative_demands.any():
            df.loc[negative_demands, 'demand'] = 0
            validation_report['fixes_applied'].append(f"Set {negative_demands.sum()} negative demands to zero")

        # Remove rows with NaN demands
        nan_demands = df['demand'].isna()
        if nan_demands.any():
            df = df[~nan_demands]
            validation_report['issues_found'].append(f"Removed {nan_demands.sum()} rows with NaN demands")

        # Check for duplicated timestamps
        duplicated_times = df[datetime_col_name_in_df].duplicated()
        if duplicated_times.any():
            df = df[~duplicated_times]
            validation_report['fixes_applied'].append(f"Removed {duplicated_times.sum()} duplicate timestamps")

        # Validate temporal consistency
        df = df.sort_values(datetime_col_name_in_df).reset_index(drop=True)
        time_diffs = df[datetime_col_name_in_df].diff()
        expected_freq = pd.Timedelta(hours=1)
        irregular_intervals = (time_diffs != expected_freq) & (time_diffs.notna())

        if irregular_intervals.any():
            validation_report['issues_found'].append(f"Found {irregular_intervals.sum()} irregular time intervals")

        # Calculate quality scores
        validation_report['completeness_score'] = len(df) / initial_count if initial_count > 0 else 0
        validation_report['consistency_score'] = 1.0 - (irregular_intervals.sum() / len(df)) if len(df) > 0 else 0

        # Detect outliers
        outliers = self._detect_statistical_outliers(df['demand'])
        validation_report['outliers_detected'] = outliers['count']
        validation_report['outlier_percentage'] = outliers['percentage']

        # Overall quality score
        validation_report['data_quality_score'] = (
            validation_report['completeness_score'] * 0.4 +
            validation_report['consistency_score'] * 0.4 +
            (1.0 - min(0.1, outliers['percentage'] / 100)) * 0.2
        )
        validation_report['final_records'] = len(df)

        return df, validation_report

    def _add_comprehensive_time_features(self, df: pd.DataFrame, fy_start_month: int) -> pd.DataFrame:
        """Add comprehensive time features for analysis"""
        # Basic time components
        df['year'] = df['datetime'].dt.year
        df['month'] = df['datetime'].dt.month
        df['day'] = df['datetime'].dt.day
        df['hour'] = df['datetime'].dt.hour
        df['minute'] = df['datetime'].dt.minute
        
        # Day-based features
        df['day_of_week'] = df['datetime'].dt.dayofweek  # Monday=0
        df['day_of_year'] = df['datetime'].dt.dayofyear
        df['week_of_year'] = df['datetime'].dt.isocalendar().week
        df['is_weekend'] = df['day_of_week'].isin([5, 6])  # Saturday, Sunday
        
        # Fiscal year calculation
        df['fiscal_year'] = df['datetime'].apply(lambda x: self._get_fiscal_year(x, fy_start_month))
        df['fiscal_month'] = df.apply(lambda row: self._get_fiscal_month(row['month'], fy_start_month), axis=1)
        df['fiscal_quarter'] = ((df['fiscal_month'] - 1) // 3) + 1
        
        # Seasonal features
        df['season'] = df['month'].apply(self._get_season)
        df['is_summer'] = df['season'] == 'Summer'
        df['is_winter'] = df['season'] == 'Winter'
        
        # Time of day categories
        df['time_of_day'] = df['hour'].apply(self._get_time_category)
        df['is_peak_hour'] = df['hour'].isin([17, 18, 19, 20, 21])  # Evening peak
        df['is_off_peak'] = df['hour'].isin([23, 0, 1, 2, 3, 4, 5])  # Night hours
        
        # Holiday indicators (basic implementation)
        df['is_holiday'] = False  # Would need holiday calendar for accuracy
        df['is_business_day'] = ~(df['is_weekend'] | df['is_holiday'])
        
        return df
    
    def _intelligent_interpolation(self, df: pd.DataFrame) -> pd.DataFrame:
        """Intelligent interpolation for missing demand values"""
        missing_count = df['demand'].isna().sum()
        
        if missing_count == 0:
            return df
        
        logger.info(f"Interpolating {missing_count} missing demand values")
        
        df = df.copy()
        
        # Multi-stage interpolation approach
        # Stage 1: Linear interpolation for small gaps (≤6 hours)
        df['demand'] = df['demand'].interpolate(method='linear', limit=6)
        
        # Stage 2: Seasonal pattern interpolation for larger gaps
        remaining_missing = df['demand'].isna().sum()
        if remaining_missing > 0:
            df = self._seasonal_pattern_interpolation(df)
        
        # Stage 3: Forward/backward fill for extreme cases
        df['demand'] = df['demand'].fillna(method='ffill').fillna(method='bfill')
        
        # Final fallback: median value
        if df['demand'].isna().any():
            df['demand'] = df['demand'].fillna(df['demand'].median())
        
        return df
    
    def _seasonal_pattern_interpolation(self, df: pd.DataFrame) -> pd.DataFrame:
        """Interpolate using seasonal patterns"""
        # Calculate patterns for interpolation
        hourly_patterns = df.groupby('hour')['demand'].median()
        daily_patterns = df.groupby(['day_of_week', 'hour'])['demand'].median()
        monthly_patterns = df.groupby(['month', 'hour'])['demand'].median()
        
        # Fill missing values using best available pattern
        for idx in df[df['demand'].isna()].index:
            row = df.loc[idx]
            hour = row['hour']
            day_of_week = row['day_of_week']
            month = row['month']
            
            # Try most specific pattern first
            if (month, hour) in monthly_patterns.index:
                df.loc[idx, 'demand'] = monthly_patterns[(month, hour)]
            elif (day_of_week, hour) in daily_patterns.index:
                df.loc[idx, 'demand'] = daily_patterns[(day_of_week, hour)]
            elif hour in hourly_patterns.index:
                df.loc[idx, 'demand'] = hourly_patterns[hour]
        
        return df
    
    def _validate_base_year_completeness(self, df: pd.DataFrame, config: LoadProfileConfig):
        """Validate base year data completeness"""
        # Check for expected number of hours in fiscal year
        start_date = datetime(config.base_year - 1, config.fiscal_year_start_month, 1)
        
        # Determine if leap year affects this fiscal year
        is_leap_year = config.base_year % 4 == 0 and (config.base_year % 100 != 0 or config.base_year % 400 == 0)
        if is_leap_year and config.fiscal_year_start_month <= 2:
            expected_hours = 8784
        else:
            expected_hours = 8760
        
        actual_hours = len(df)
        completeness = actual_hours / expected_hours
        
        if completeness < 0.95:  # Less than 95% complete
            logger.warning(f"Base year data only {completeness:.1%} complete ({actual_hours}/{expected_hours} hours)")
        
        # Check for large gaps
        time_diffs = df['datetime'].diff()
        large_gaps = time_diffs[time_diffs > pd.Timedelta(hours=6)]
        
        if not large_gaps.empty:
            logger.warning(f"Found {len(large_gaps)} large gaps (>6 hours) in base year data")
    
    def _detect_statistical_outliers(self, series: pd.Series) -> Dict[str, float]:
        """Detect statistical outliers using IQR method"""
        Q1 = series.quantile(0.25)
        Q3 = series.quantile(0.75)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        outliers = ((series < lower_bound) | (series > upper_bound))
        
        return {
            'count': int(outliers.sum()),
            'percentage': float(outliers.mean() * 100),
            'lower_bound': float(lower_bound),
            'upper_bound': float(upper_bound)
        }
    
    def _load_scenario_totals(self, scenario_name: str, config: LoadProfileConfig) -> Dict[int, float]:
        """Load totals from demand projection scenario"""
        scenario_path = self.results_folder / 'demand_projection' / scenario_name / 'consolidated_results.csv'
        
        if not scenario_path.exists():
            raise FileNotFoundError(f"Scenario file not found: {scenario_path}")
        
        df = pd.read_csv(scenario_path)
        
        # Intelligent column detection
        year_col = self._find_year_column(df)
        total_col = self._find_total_column(df)
        
        if not year_col or not total_col:
            raise ValueError("Cannot identify year or total columns in scenario data")
        
        totals = {}
        for _, row in df.iterrows():
            try:
                year = int(row[year_col])
                total = float(row[total_col])
                if config.start_year <= year <= config.end_year:
                    totals[year] = total
            except (ValueError, TypeError):
                continue
        
        if not totals:
            raise ValueError(f"No valid data found for years {config.start_year}-{config.end_year}")
        
        return totals
    
    def _load_excel_totals(self, config: LoadProfileConfig) -> Dict[int, float]:
        """Load totals from Excel Total Demand sheet"""
        excel_path = self.inputs_folder / 'load_curve_template.xlsx'
        
        try:
            df = pd.read_excel(excel_path, sheet_name='Total Demand')
            
            year_col = self._find_year_column(df)
            total_col = self._find_total_column(df)
            
            if not year_col or not total_col:
                raise ValueError("Cannot identify year or total columns in Excel")
            
            totals = {}
            for _, row in df.iterrows():
                try:
                    year = int(row[year_col])
                    total = float(row[total_col])
                    if config.start_year <= year <= config.end_year:
                        totals[year] = total
                except (ValueError, TypeError):
                    continue
            
            return totals
            
        except Exception as e:
            logger.error(f"Error loading Excel totals: {e}")
            raise

# Add helper functions

    def _find_datetime_column(self, df: pd.DataFrame) -> Optional[Tuple[str, Optional[str]]]:
        """Find datetime-related columns intelligently (supports separate date and time columns)."""
        datetime_keywords = ['datetime', 'timestamp', 'date_time']
        date_keywords = ['date']
        time_keywords = ['time']
        
        # Normalize column names
        normalized_columns = {col: str(col).lower().replace(' ', '').replace('-', '_') for col in df.columns}
        
        # Search for datetime-like column
        for col, norm_col in normalized_columns.items():
            if any(keyword in norm_col for keyword in datetime_keywords):
                return (col, None)
        
        # Otherwise, look for separate date and time columns
        date_col = time_col = None
        for col, norm_col in normalized_columns.items():
            if not date_col and any(keyword == norm_col or norm_col.endswith('_' + keyword) for keyword in date_keywords):
                date_col = col
            elif not time_col and any(keyword == norm_col or norm_col.endswith('_' + keyword) for keyword in time_keywords):
                time_col = col

        if date_col:
            return (date_col, time_col)  # time_col may still be None

        return None

    def _find_demand_column(self, df: pd.DataFrame) -> Optional[str]:
        """Find demand column with intelligent matching"""
        demand_keywords = ['demand', 'load', 'power', 'kw', 'consumption', 'energy']
        for col in df.columns:
            col_lower = str(col).lower().replace(' ', '_').replace('-', '_')
            if any(keyword in col_lower for keyword in demand_keywords):
                return col
        return None

    def _find_year_column(self, df: pd.DataFrame) -> Optional[str]:
        """Find year column with intelligent matching"""
        year_keywords = ['year', 'fy', 'fiscal_year', 'financial_year']
        for col in df.columns:
            col_lower = str(col).lower().replace(' ', '_').replace('-', '_')
            if any(keyword in col_lower for keyword in year_keywords):
                return col
        return None

    def _find_total_column(self, df: pd.DataFrame) -> Optional[str]:
        """Find total column with intelligent matching"""
        total_keywords = ['total', 'demand', 'energy', 'consumption', 'kwh', 'mwh', 'gwh']
        for col in df.columns:
            col_lower = str(col).lower().replace(' ', '_').replace('-', '_')
            if any(keyword in col_lower for keyword in total_keywords):
                return col
        return None

    def _get_fiscal_year(self, date_obj: datetime, fy_start_month: int) -> int:
        """Convert datetime to fiscal year"""
        if date_obj.month >= fy_start_month:
            return date_obj.year + 1
        else:
            return date_obj.year

    def _get_fiscal_month(self, calendar_month: int, fy_start_month: int) -> int:
        """Convert calendar month to fiscal month"""
        fiscal_month = calendar_month - fy_start_month + 1
        if fiscal_month <= 0:
            fiscal_month += 12
        return fiscal_month

    def _get_season(self, month: int) -> str:
        """Get season from month"""
        if month in [12, 1, 2]:
            return 'Winter'
        elif month in [3, 4, 5]:
            return 'Spring'
        elif month in [6, 7, 8]:
            return 'Summer'
        else:
            return 'Autumn'

    def _get_time_category(self, hour: int) -> str:
        """Categorize hour into time periods"""
        if 6 <= hour < 12:
            return 'Morning'
        elif 12 <= hour < 18:
            return 'Afternoon'
        elif 18 <= hour < 22:
            return 'Evening'
        else:
            return 'Night'

    def _validate_custom_totals(self, totals: Dict[int, float], config: LoadProfileConfig) -> Dict[int, float]:
        """Validate custom totals"""
        validated_totals = {}
        
        for year, total in totals.items():
            if config.start_year <= year <= config.end_year:
                if total > 0:
                    validated_totals[year] = total
                else:
                    logger.warning(f"Invalid total for year {year}: {total}")
        
        if not validated_totals:
            raise ValueError("No valid totals found in custom totals")
        
        return validated_totals
    def load_and_validate_historical_data(self, file_path: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Load and comprehensively validate historical load data"""
        logger.info(f"Loading historical data from {file_path}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Input file not found: {file_path}")
        
        try:
            # Read Excel file with Past_Hourly_Demand sheet
            df = pd.read_excel(file_path, sheet_name='Past_Hourly_Demand')
            
            # Validate and clean data
            df, validation_report = self._comprehensive_data_validation(df)
                            # Extract available base years
            cols = self._find_datetime_column(df)
            if cols:
                date_col, time_col = cols
                if time_col:
                    df['datetime'] = pd.to_datetime(df[date_col].astype(str) + ' ' + df[time_col].astype(str))
                else:
                    df['datetime'] = pd.to_datetime(df[date_col])
            # Cache the validated data
            self.cache['historical_data'] = df
            self.cache['validation_report'] = validation_report
            
            logger.info(f"Successfully loaded and validated {len(df)} hourly records")
            return df, validation_report
            
        except Exception as e:
            logger.error(f"Error loading historical data: {e}")
            raise
    
# =====================================================================
# METHODOLOGY AGENT (Enhanced)
# =====================================================================

class MethodologyAgent:
    """ agent for methodology selection and execution"""
    
    def __init__(self):
        self.methodologies = {}
        self.current_methodology = None
        self.execution_cache = {}
    
    def register_methodology(self, name: str, methodology_class):
        """Register a methodology class"""
        self.methodologies[name] = methodology_class
        logger.info(f"Registered methodology: {name}")
    
    def get_methodology_instance(self, name: str, fy_start_month: int):
        """Get methodology instance"""
        if name not in self.methodologies:
            raise ValueError(f"Unknown methodology: {name}")
        
        # Create instance with fiscal year configuration
        return self.methodologies[name](fiscal_year_start_month=fy_start_month)
    
    def execute_methodology(self, 
                          methodology_name: str,
                          base_data: pd.DataFrame,
                          target_totals: Dict[int, float],
                          config: LoadProfileConfig) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Execute methodology witherror handling and validation"""
        logger.info(f"Executing {methodology_name} methodology")
        
        try:
            # Get methodology instance
            methodology = self.get_methodology_instance(methodology_name, config.fiscal_year_start_month)
            
            # Extract patterns from base data
            logger.info("Extracting patterns from base year data")
            patterns = methodology.extract_patterns(base_data, config)
            
            # Validate pattern extraction
            self._validate_patterns(patterns, base_data, config)
            
            # Generate future profile
            logger.info("Generating future load profile")
            profile_df = methodology.generate_future_profile(patterns, target_totals, config)
            
            # Validate generated profile
            self._validate_generated_profile(profile_df, target_totals, config)
            
            # Apply load shifting if enabled
            if config.enable_load_shifting:
                profile_df = self._apply_load_shifting(profile_df, config)
            
            # Final formatting and validation
            profile_df = self._ensure_standard_output_format(profile_df)
            
            return profile_df, patterns
            
        except Exception as e:
            logger.error(f"Methodology execution failed: {e}")
            raise
    
    def _validate_patterns(self, patterns: Dict[str, Any], base_data: pd.DataFrame, config: LoadProfileConfig):
        """Validate extracted patterns"""
        required_keys = ['methodology', 'base_year']
        
        for key in required_keys:
            if key not in patterns:
                raise ValueError(f"Missing required pattern key: {key}")
        
        if patterns['base_year'] != config.base_year:
            raise ValueError(f"Pattern base year mismatch: {patterns['base_year']} != {config.base_year}")
    
    def _validate_generated_profile(self, profile_df: pd.DataFrame, target_totals: Dict[int, float], config: LoadProfileConfig):
        """Validate generated profile"""
        required_columns = ['datetime', 'Demand', 'Date', 'Time', 'Fiscal_Year', 'Year']
        
        for col in required_columns:
            if col not in profile_df.columns:
                raise ValueError(f"Missing required column: {col}")
        
        # Validate data types
        if not pd.api.types.is_datetime64_any_dtype(profile_df['datetime']):
            raise ValueError("datetime column must be datetime type")
        
        if not pd.api.types.is_numeric_dtype(profile_df['Demand']):
            raise ValueError("Demand column must be numeric")
        
        # Validate energy conservation
        for year, target_total in target_totals.items():
            year_data = profile_df[profile_df['Fiscal_Year'] == year]
            if not year_data.empty:
                actual_total = year_data['Demand'].sum()
                error_percent = abs(actual_total - target_total) / target_total * 100
                
                if error_percent > config.energy_conservation_tolerance * 100:
                    logger.warning(f"Energy conservation error for year {year}: {error_percent:.3f}%")
    
    def _apply_load_shifting(self, profile_df: pd.DataFrame, config: LoadProfileConfig) -> pd.DataFrame:
        """Applyload shifting with gradual implementation"""
        if not config.enable_load_shifting or not config.peak_shifting_hours:
            return profile_df
        
        logger.info("Applyingload shifting")
        
        df = profile_df.copy()
        
        for year in range(config.start_year, config.end_year + 1):
            year_mask = df['Fiscal_Year'] == year
            
            # Calculate implementation progress
            years_since_start = year - config.start_year
            if config.gradual_shift_implementation:
                implementation_factor = min(1.0, years_since_start / config.shift_implementation_years)
            else:
                implementation_factor = 1.0
            
            # Apply load shifting rules
            for from_hour, to_hour in config.peak_shifting_hours.items():
                self._apply_hourly_shift(df, year_mask, from_hour, to_hour, 
                                       config.load_shift_percentage, implementation_factor)
        
        # Ensure no negative values
        df['Demand'] = df['Demand'].clip(lower=0)
        
        # Reapply energy conservation after shifting
        for year, target_total in self._get_target_totals_from_df(df).items():
            year_mask = df['Fiscal_Year'] == year
            year_data = df[year_mask]
            
            if not year_data.empty:
                current_total = year_data['Demand'].sum()
                if abs(current_total - target_total) / target_total > config.energy_conservation_tolerance:
                    scale_factor = target_total / current_total
                    df.loc[year_mask, 'Demand'] *= scale_factor
        
        return df
    
    def _apply_hourly_shift(self, df: pd.DataFrame, year_mask: pd.Series, 
                          from_hour: int, to_hour: int, shift_percentage: float, 
                          implementation_factor: float):
        """Apply hourly load shift"""
        from_hour_mask = year_mask & (df['Hour'] == from_hour)
        to_hour_mask = year_mask & (df['Hour'] == to_hour)
        
        if from_hour_mask.any() and to_hour_mask.any():
            # Calculate amount to shift
            from_hour_demand = df.loc[from_hour_mask, 'Demand']
            shift_amount = from_hour_demand * (shift_percentage / 100) * implementation_factor
            
            # Apply the shift
            df.loc[from_hour_mask, 'Demand'] -= shift_amount
            
            # Distribute to target hour(s)
            total_shift = shift_amount.sum()
            to_hour_count = to_hour_mask.sum()
            if to_hour_count > 0:
                df.loc[to_hour_mask, 'Demand'] += total_shift / to_hour_count
    
    def _get_target_totals_from_df(self, df: pd.DataFrame) -> Dict[int, float]:
        """Extract target totals from existing dataframe"""
        return df.groupby('Fiscal_Year')['Demand'].sum().to_dict()
    
    def _ensure_standard_output_format(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure standard output format with all required columns"""
        df = df.copy()
        
        # Ensure datetime is properly formatted
        df['datetime'] = pd.to_datetime(df['datetime'])
        
        # Add missing columns if needed
        if 'Date' not in df.columns:
            df['Date'] = df['datetime'].dt.date.astype(str)
        if 'Time' not in df.columns:
            df['Time'] = df['datetime'].dt.time.astype(str)
        if 'Year' not in df.columns:
            df['Year'] = df['datetime'].dt.year
        if 'Hour' not in df.columns:
            df['Hour'] = df['datetime'].dt.hour
        if 'Month' not in df.columns:
            df['Month'] = df['datetime'].dt.month
        
        # Ensure column order
        column_order = ['datetime', 'Demand', 'Date', 'Time', 'Fiscal_Year', 'Year', 'Month', 'Hour']
        other_columns = [col for col in df.columns if col not in column_order]
        final_columns = column_order + other_columns
        
        return df[final_columns]
    
    def get_available_methodologies(self) -> Dict[str, Dict[str, str]]:
        """Get information about available methodologies"""
        methodology_info = {}
        
        for name, methodology_class in self.methodologies.items():
            try:
                # Create temporary instance to get info
                temp_instance = methodology_class(fiscal_year_start_month=4)
                methodology_info[name] = temp_instance.get_methodology_info()
            except Exception as e:
                logger.warning(f"Could not get info for methodology {name}: {e}")
                methodology_info[name] = {
                    'name': name,
                    'description': 'Information unavailable',
                    'error': str(e)
                }
        
        return methodology_info

# =====================================================================
# ANALYSIS AGENT (Enhanced)
# =====================================================================

class AnalysisAgent:
    """ agent for comprehensive analysis and quality assessment"""
    
    def __init__(self):
        self.analysis_cache = {}
    
    def comprehensive_profile_analysis(self, 
                                     profile_df: pd.DataFrame,
                                     base_data: pd.DataFrame,
                                     config: LoadProfileConfig,
                                     patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive analysis of generated profile"""
        logger.info("Performing comprehensive profile analysis")
        
        analysis = {
            'analysis_timestamp': datetime.now().isoformat(),
            'profile_metadata': self._extract_profile_metadata(profile_df),
            'statistical_analysis': self._detailed_statistical_analysis(profile_df),
            'temporal_analysis': self._temporal_pattern_analysis(profile_df),
            'quality_assessment': self._quality_assessment(profile_df, config),
            'base_comparison': self._compare_with_base(profile_df, base_data, config),
            'energy_conservation_check': self._validate_energy_conservation_detailed(profile_df, config),
            'pattern_preservation_analysis': self._analyze_pattern_preservation(profile_df, base_data, patterns, config),
            'load_shifting_analysis': self._analyze_load_shifting_effects(profile_df, config) if config.enable_load_shifting else None,
            'yearly_evolution': self._analyze_yearly_evolution(profile_df),
            'recommendations': self._generate_detailed_recommendations(profile_df, config, patterns)
        }
        
        return analysis
    
    def _extract_profile_metadata(self, profile_df: pd.DataFrame) -> Dict[str, Any]:
        """Extract comprehensive profile metadata"""
        demand = profile_df['Demand']
        
        return {
            'total_hours': len(profile_df),
            'date_range': {
                'start': profile_df['datetime'].min().isoformat(),
                'end': profile_df['datetime'].max().isoformat(),
                'span_days': (profile_df['datetime'].max() - profile_df['datetime'].min()).days
            },
            'fiscal_years_covered': sorted(profile_df['Fiscal_Year'].unique().tolist()),
            'demand_statistics': {
                'peak_demand_kw': float(demand.max()),
                'min_demand_kw': float(demand.min()),
                'avg_demand_kw': float(demand.mean()),
                'median_demand_kw': float(demand.median()),
                'std_demand_kw': float(demand.std()),
                'total_energy_kwh': float(demand.sum()),
                'load_factor_percent': float((demand.mean() / demand.max()) * 100) if demand.max() > 0 else 0,
                'capacity_factor_percent': float((demand.mean() / demand.max()) * 100) if demand.max() > 0 else 0
            },
            'peak_characteristics': {
                'peak_datetime': profile_df.loc[demand.idxmax(), 'datetime'].isoformat(),
                'peak_fiscal_year': int(profile_df.loc[demand.idxmax(), 'Fiscal_Year']),
                'peak_month': int(profile_df.loc[demand.idxmax(), 'Month']),
                'peak_hour': int(profile_df.loc[demand.idxmax(), 'Hour']),
                'peak_to_min_ratio': float(demand.max() / demand.min()) if demand.min() > 0 else float('inf'),
                'peak_to_avg_ratio': float(demand.max() / demand.mean()) if demand.mean() > 0 else float('inf')
            }
        }
    
    def _detailed_statistical_analysis(self, profile_df: pd.DataFrame) -> Dict[str, Any]:
        """Detailed statistical analysis"""
        demand = profile_df['Demand']
        
        # Distribution analysis
        percentiles = [1, 5, 10, 25, 50, 75, 90, 95, 99]
        percentile_values = {f'p{p}': float(np.percentile(demand, p)) for p in percentiles}
        
        # Variability analysis
        variability = {
            'coefficient_of_variation': float(demand.std() / demand.mean() * 100) if demand.mean() > 0 else 0,
            'skewness': float(demand.skew()),
            'kurtosis': float(demand.kurtosis()),
            'interquartile_range': float(demand.quantile(0.75) - demand.quantile(0.25))
        }
        
        # Autocorrelation analysis
        autocorr = {
            'lag_1h': float(demand.autocorr(lag=1)) if len(demand) > 1 else 0,
            'lag_24h': float(demand.autocorr(lag=24)) if len(demand) > 24 else 0,
            'lag_168h': float(demand.autocorr(lag=168)) if len(demand) > 168 else 0
        }
        
        return {
            'percentiles': percentile_values,
            'variability': variability,
            'autocorrelation': autocorr,
            'outlier_analysis': self._analyze_outliers(demand)
        }
    
    def _temporal_pattern_analysis(self, profile_df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze temporal patterns"""
        return {
            'hourly_patterns': self._analyze_hourly_patterns(profile_df),
            'daily_patterns': self._analyze_daily_patterns(profile_df),
            'weekly_patterns': self._analyze_weekly_patterns(profile_df),
            'monthly_patterns': self._analyze_monthly_patterns(profile_df),
            'seasonal_patterns': self._analyze_seasonal_patterns(profile_df)
        }
    
    def _analyze_hourly_patterns(self, profile_df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze hourly patterns"""
        hourly_stats = profile_df.groupby('Hour')['Demand'].agg(['mean', 'std', 'min', 'max']).round(2)
        
        return {
            'statistics': hourly_stats.to_dict('index'),
            'peak_hour': int(hourly_stats['mean'].idxmax()),
            'min_hour': int(hourly_stats['mean'].idxmin()),
            'peak_to_trough_ratio': float(hourly_stats['mean'].max() / hourly_stats['mean'].min()) if hourly_stats['mean'].min() > 0 else float('inf'),
            'hourly_variability': float(hourly_stats['mean'].std())
        }
    
    def _analyze_daily_patterns(self, profile_df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze daily patterns"""
        profile_df['day_name'] = profile_df['datetime'].dt.day_name()
        daily_stats = profile_df.groupby('day_name')['Demand'].agg(['mean', 'std']).round(2)
        
        weekday_avg = profile_df[~profile_df['datetime'].dt.dayofweek.isin([5, 6])]['Demand'].mean()
        weekend_avg = profile_df[profile_df['datetime'].dt.dayofweek.isin([5, 6])]['Demand'].mean()
        
        return {
            'statistics': daily_stats.to_dict('index'),
            'weekday_avg': float(weekday_avg),
            'weekend_avg': float(weekend_avg),
            'weekday_weekend_ratio': float(weekday_avg / weekend_avg) if weekend_avg > 0 else float('inf')
        }
    
    def _compare_with_base(self, profile_df: pd.DataFrame, base_data: pd.DataFrame, config: LoadProfileConfig) -> Dict[str, Any]:
        """ comparison with base year data"""
        # Get first year of generated profile for comparison
        first_year = profile_df['Fiscal_Year'].min()
        first_year_data = profile_df[profile_df['Fiscal_Year'] == first_year]
        
        if first_year_data.empty:
            return {'error': 'No data for comparison'}
        
        base_demand = base_data['demand']
        gen_demand = first_year_data['Demand']
        
        # Shape correlation (normalized patterns)
        base_hourly = base_data.groupby('hour')['demand'].mean()
        gen_hourly = first_year_data.groupby('Hour')['Demand'].mean()
        
        # Normalize for shape comparison
        base_norm = (base_hourly - base_hourly.min()) / (base_hourly.max() - base_hourly.min())
        gen_norm = (gen_hourly - gen_hourly.min()) / (gen_hourly.max() - gen_hourly.min())
        
        shape_correlation = float(np.corrcoef(base_norm.values, gen_norm.values)[0, 1])
        
        return {
            'shape_correlation': shape_correlation,
            'load_factor_comparison': {
                'base': float((base_demand.mean() / base_demand.max()) * 100),
                'generated': float((gen_demand.mean() / gen_demand.max()) * 100),
                'difference_pp': float((gen_demand.mean() / gen_demand.max()) * 100 - (base_demand.mean() / base_demand.max()) * 100)
            },
            'peak_timing_preservation': self._compare_peak_timing(base_data, first_year_data),
            'pattern_fidelity_score': self._calculate_pattern_fidelity(base_data, first_year_data)
        }
    
    # Additional helper methods continue...
    def _quality_assessment(self, profile_df: pd.DataFrame, config: LoadProfileConfig) -> Dict[str, Any]:
        """Comprehensive quality assessment"""
        demand = profile_df['Demand']
        
        return {
            'data_integrity': {
                'negative_values': int((demand < 0).sum()),
                'zero_values': int((demand == 0).sum()),
                'null_values': int(demand.isna().sum()),
                'infinite_values': int(np.isinf(demand).sum()),
                'integrity_score': self._calculate_integrity_score(demand)
            },
            'realism_assessment': {
                'load_factor_realism': self._assess_load_factor_realism(demand),
                'variability_realism': self._assess_variability_realism(demand),
                'pattern_realism': self._assess_pattern_realism(profile_df)
            },
            'temporal_consistency': self._assess_temporal_consistency(profile_df),
            'overall_quality_score': 0.0  # Will be calculated
        }
    
    def _calculate_integrity_score(self, demand: pd.Series) -> float:
        """Calculate data integrity score"""
        total_issues = (
            (demand < 0).sum() +
            (demand == 0).sum() +
            demand.isna().sum() +
            np.isinf(demand).sum()
        )
        return float(max(0.0, 1.0 - (total_issues / len(demand))))
    
    def _generate_detailed_recommendations(self, profile_df: pd.DataFrame, config: LoadProfileConfig, patterns: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate detailed recommendations"""
        recommendations = []
        demand = profile_df['Demand']
        
        # Load factor analysis
        load_factor = (demand.mean() / demand.max()) * 100
        if load_factor < 40:
            recommendations.append({
                'category': 'Load Management',
                'priority': 'High',
                'issue': f'Low load factor ({load_factor:.1f}%)',
                'recommendation': 'Consider demand management strategies to improve system utilization',
                'impact': 'Improved efficiency and cost reduction'
            })
        elif load_factor > 85:
            recommendations.append({
                'category': 'System Planning',
                'priority': 'Medium',
                'issue': f'High load factor ({load_factor:.1f}%)',
                'recommendation': 'Monitor capacity adequacy for peak demand growth',
                'impact': 'Ensure reliable supply during peak periods'
            })
        
        # Peak-to-minimum ratio analysis
        peak_to_min = demand.max() / demand.min() if demand.min() > 0 else float('inf')
        if peak_to_min > 10:
            recommendations.append({
                'category': 'Load Balancing',
                'priority': 'Medium',
                'issue': f'High peak-to-minimum ratio ({peak_to_min:.1f})',
                'recommendation': 'Implement load leveling strategies or demand response programs',
                'impact': 'Reduced infrastructure costs and improved efficiency'
            })
        
        # Energy conservation check
        yearly_totals = profile_df.groupby('Fiscal_Year')['Demand'].sum()
        if yearly_totals.std() / yearly_totals.mean() > 0.3:
            recommendations.append({
                'category': 'Data Quality',
                'priority': 'High',
                'issue': 'High variability in annual energy totals',
                'recommendation': 'Verify target energy values and methodology parameters',
                'impact': 'Improved forecast accuracy and planning reliability'
            })
        
        return recommendations