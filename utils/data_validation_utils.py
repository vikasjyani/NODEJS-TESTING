# utils/data_validation_utils.py
#Data Validation Utilities

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
import logging
import os
from pathlib import Path
from scipy import stats
import warnings

warnings.filterwarnings('ignore', category=FutureWarning)
logger = logging.getLogger(__name__)

class DataValidationEngine:
    """
   Data Validation Engine
    
    Provides comprehensive validation for load profile generation including:
    - Input file structure validation
    - Data quality assessment
    - Temporal consistency checks
    - Statistical validation
    - Base year completeness verification
    """
    
    def __init__(self, project_path: str, fiscal_year_start_month: int = 4):
        self.project_path = Path(project_path)
        self.fy_start_month = fiscal_year_start_month
        
        # Validation thresholds
        self.validation_thresholds = {
            'min_data_quality_score': 0.7,
            'min_completeness_score': 0.95,
            'max_outlier_percentage': 5.0,
            'min_temporal_consistency': 0.90,
            'max_gap_hours': 6,
            'min_base_year_hours': 8000  # Minimum hours for base year
        }
    
    def validate_input_file(self, file_path: str) -> Dict[str, Any]:
        """Comprehensive input file validation"""
        logger.info(f"Validating input file: {file_path}")
        
        validation_result = {
            'file_path': file_path,
            'validation_timestamp': datetime.now().isoformat(),
            'is_valid': False,
            'overall_score': 0.0,
            'validation_details': {}
        }
        
        try:
            # Check file existence and accessibility
            if not os.path.exists(file_path):
                validation_result['validation_details']['file_error'] = 'File does not exist'
                return validation_result
            
            # Validate file format
            if not file_path.lower().endswith('.xlsx'):
                validation_result['validation_details']['format_error'] = 'File must be Excel (.xlsx) format'
                return validation_result
            
            # Load and validate Excel structure
            excel_validation = self._validate_excel_structure(file_path)
            validation_result['validation_details']['excel_structure'] = excel_validation
            
            if not excel_validation['has_required_sheets']:
                return validation_result
            
            # Load and validate data content
            df = pd.read_excel(file_path, sheet_name='Past_Hourly_Demand')
            data_validation = self._validate_data_content(df)
            validation_result['validation_details']['data_content'] = data_validation
            
            # Temporal validation
            temporal_validation = self._validate_temporal_structure(df)
            validation_result['validation_details']['temporal_structure'] = temporal_validation
            
            # Statistical validation
            statistical_validation = self._validate_statistical_properties(df)
            validation_result['validation_details']['statistical_properties'] = statistical_validation
            
            # Calculate overall validation score
            scores = [
                excel_validation.get('structure_score', 0),
                data_validation.get('content_score', 0),
                temporal_validation.get('temporal_score', 0),
                statistical_validation.get('statistical_score', 0)
            ]
            
            validation_result['overall_score'] = sum(scores) / len(scores)
            validation_result['is_valid'] = validation_result['overall_score'] >= self.validation_thresholds['min_data_quality_score']
            
            # Generate recommendations
            validation_result['recommendations'] = self._generate_validation_recommendations(
                validation_result['validation_details']
            )
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            validation_result['validation_details']['error'] = str(e)
        
        return validation_result
    
    def _validate_excel_structure(self, file_path: str) -> Dict[str, Any]:
        """Validate Excel file structure"""
        try:
            # Get sheet names
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names
            
            # Required sheets
            required_sheets = ['Past_Hourly_Demand']
            optional_sheets = ['Total Demand', 'Settings', 'Metadata']
            
            has_required = all(sheet in sheet_names for sheet in required_sheets)
            has_optional = [sheet for sheet in optional_sheets if sheet in sheet_names]
            
            # Check Past_Hourly_Demand sheet structure
            demand_sheet_validation = {}
            if 'Past_Hourly_Demand' in sheet_names:
                df = pd.read_excel(file_path, sheet_name='Past_Hourly_Demand', nrows=5)
                demand_sheet_validation = self._validate_demand_sheet_structure(df)
            
            # Check Total Demand sheet if present
            total_demand_validation = {}
            if 'Total Demand' in sheet_names:
                try:
                    total_df = pd.read_excel(file_path, sheet_name='Total Demand')
                    total_demand_validation = self._validate_total_demand_sheet(total_df)
                except:
                    total_demand_validation = {'valid': False, 'error': 'Cannot read Total Demand sheet'}
            
            structure_score = 1.0 if has_required else 0.0
            if has_required and demand_sheet_validation.get('valid', False):
                structure_score = min(1.0, structure_score + 0.2 * len(has_optional))
            
            return {
                'sheet_names': sheet_names,
                'has_required_sheets': has_required,
                'optional_sheets_present': has_optional,
                'demand_sheet_validation': demand_sheet_validation,
                'total_demand_validation': total_demand_validation,
                'structure_score': structure_score,
                'valid': has_required and demand_sheet_validation.get('valid', False)
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'structure_score': 0.0
            }
    
    def _validate_demand_sheet_structure(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate Past_Hourly_Demand sheet structure"""
        required_columns = ['datetime', 'demand']
        alternative_columns = {
            'datetime': ['timestamp', 'date_time', 'date', 'time'],
            'demand': ['load', 'power', 'kw', 'consumption', 'energy']
        }
        
        # Find datetime column
        datetime_col = None
        for col in df.columns:
            col_lower = str(col).lower().replace(' ', '_').replace('-', '_')
            if 'datetime' in col_lower or any(alt in col_lower for alt in alternative_columns['datetime']):
                datetime_col = col
                break
        
        # Find demand column
        demand_col = None
        for col in df.columns:
            col_lower = str(col).lower().replace(' ', '_').replace('-', '_')
            if 'demand' in col_lower or any(alt in col_lower for alt in alternative_columns['demand']):
                demand_col = col
                break
        
        validation = {
            'datetime_column': datetime_col,
            'demand_column': demand_col,
            'total_columns': len(df.columns),
            'valid': datetime_col is not None and demand_col is not None
        }
        
        # Test data conversion if columns found
        if validation['valid']:
            try:
                # Test datetime conversion
                test_datetime = pd.to_datetime(df[datetime_col].iloc[0])
                validation['datetime_convertible'] = True
                
                # Test demand conversion
                test_demand = pd.to_numeric(df[demand_col].iloc[0])
                validation['demand_numeric'] = True
                
            except Exception as e:
                validation['conversion_error'] = str(e)
                validation['valid'] = False
        
        return validation
    
    def _validate_total_demand_sheet(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate Total Demand sheet structure"""
        # Find year and total columns
        year_col = None
        total_col = None
        
        for col in df.columns:
            col_lower = str(col).lower().replace(' ', '_')
            if 'year' in col_lower or 'fy' in col_lower:
                year_col = col
            elif 'total' in col_lower or 'demand' in col_lower or 'energy' in col_lower:
                total_col = col
        
        validation = {
            'year_column': year_col,
            'total_column': total_col,
            'valid': year_col is not None and total_col is not None,
            'record_count': len(df)
        }
        
        if validation['valid']:
            try:
                # Extract valid year-total pairs
                valid_pairs = 0
                for _, row in df.iterrows():
                    try:
                        year = int(row[year_col])
                        total = float(row[total_col])
                        if 2000 <= year <= 2100 and total > 0:
                            valid_pairs += 1
                    except:
                        pass
                
                validation['valid_pairs'] = valid_pairs
                validation['data_quality'] = valid_pairs / len(df) if len(df) > 0 else 0
                
            except Exception as e:
                validation['error'] = str(e)
                validation['valid'] = False
        
        return validation
    
    def _validate_data_content(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate data content quality"""
        # Find and standardize columns
        datetime_col = self._find_datetime_column(df)
        demand_col = self._find_demand_column(df)
        
        if not datetime_col or not demand_col:
            return {'content_score': 0.0, 'valid': False, 'error': 'Required columns not found'}
        
        # Standardize column names
        df_work = df.rename(columns={datetime_col: 'datetime', demand_col: 'demand'}).copy()
        
        try:
            # Convert data types
            df_work['datetime'] = pd.to_datetime(df_work['datetime'])
            df_work['demand'] = pd.to_numeric(df_work['demand'], errors='coerce')
            
            # Content validation metrics
            total_records = len(df_work)
            
            # Missing data analysis
            missing_datetime = df_work['datetime'].isna().sum()
            missing_demand = df_work['demand'].isna().sum()
            
            # Invalid data analysis
            negative_demand = (df_work['demand'] < 0).sum()
            zero_demand = (df_work['demand'] == 0).sum()
            
            # Duplicate timestamps
            duplicate_timestamps = df_work['datetime'].duplicated().sum()
            
            # Outlier detection
            outliers = self._detect_outliers(df_work['demand'])
            
            # Calculate content score
            completeness_score = 1.0 - ((missing_datetime + missing_demand) / (total_records * 2))
            validity_score = 1.0 - ((negative_demand + duplicate_timestamps) / total_records)
            outlier_score = 1.0 - min(1.0, outliers['percentage'] / 10.0)  # Penalize >10% outliers
            
            content_score = (completeness_score + validity_score + outlier_score) / 3
            
            return {
                'content_score': content_score,
                'valid': content_score >= 0.7,
                'total_records': total_records,
                'missing_data': {
                    'datetime': missing_datetime,
                    'demand': missing_demand,
                    'percentage': (missing_datetime + missing_demand) / (total_records * 2) * 100
                },
                'data_quality': {
                    'negative_demand': negative_demand,
                    'zero_demand': zero_demand,
                    'duplicate_timestamps': duplicate_timestamps
                },
                'outliers': outliers,
                'scores': {
                    'completeness': completeness_score,
                    'validity': validity_score,
                    'outlier': outlier_score
                }
            }
            
        except Exception as e:
            return {
                'content_score': 0.0,
                'valid': False,
                'error': str(e)
            }
    
    def _validate_temporal_structure(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate temporal structure and consistency"""
        datetime_col = self._find_datetime_column(df)
        
        if not datetime_col:
            return {'temporal_score': 0.0, 'valid': False, 'error': 'No datetime column found'}
        
        try:
            df_work = df.copy()
            df_work['datetime'] = pd.to_datetime(df_work[datetime_col])
            df_work = df_work.sort_values('datetime').reset_index(drop=True)
            
            # Temporal analysis
            date_range = {
                'start': df_work['datetime'].min(),
                'end': df_work['datetime'].max(),
                'span_days': (df_work['datetime'].max() - df_work['datetime'].min()).days
            }
            
            # Expected vs actual frequency analysis
            time_diffs = df_work['datetime'].diff().dropna()
            
            # Most common time difference (should be 1 hour)
            mode_diff = time_diffs.mode().iloc[0] if not time_diffs.empty else pd.Timedelta(hours=1)
            
            # Check for regular hourly intervals
            expected_diff = pd.Timedelta(hours=1)
            regular_intervals = (time_diffs == expected_diff).sum()
            irregular_intervals = len(time_diffs) - regular_intervals
            
            # Gap analysis
            large_gaps = time_diffs[time_diffs > pd.Timedelta(hours=self.validation_thresholds['max_gap_hours'])]
            
            # Temporal consistency score
            consistency_score = regular_intervals / len(time_diffs) if len(time_diffs) > 0 else 0
            gap_penalty = min(1.0, len(large_gaps) / len(time_diffs) * 10) if len(time_diffs) > 0 else 0
            temporal_score = max(0.0, consistency_score - gap_penalty)
            
            # Fiscal year analysis
            fiscal_years = self._analyze_fiscal_years(df_work, self.fy_start_month)
            
            return {
                'temporal_score': temporal_score,
                'valid': temporal_score >= self.validation_thresholds['min_temporal_consistency'],
                'date_range': {
                    'start': date_range['start'].isoformat(),
                    'end': date_range['end'].isoformat(),
                    'span_days': date_range['span_days']
                },
                'frequency_analysis': {
                    'expected_frequency': str(expected_diff),
                    'detected_frequency': str(mode_diff),
                    'regular_intervals': regular_intervals,
                    'irregular_intervals': irregular_intervals,
                    'consistency_percentage': consistency_score * 100
                },
                'gaps': {
                    'large_gaps_count': len(large_gaps),
                    'largest_gap_hours': float(large_gaps.max().total_seconds() / 3600) if not large_gaps.empty else 0,
                    'gap_locations': [gap.isoformat() for gap in df_work.loc[large_gaps.index, 'datetime']] if not large_gaps.empty else []
                },
                'fiscal_years': fiscal_years
            }
            
        except Exception as e:
            return {
                'temporal_score': 0.0,
                'valid': False,
                'error': str(e)
            }
    
    def _validate_statistical_properties(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate statistical properties of the data"""
        demand_col = self._find_demand_column(df)
        
        if not demand_col:
            return {'statistical_score': 0.0, 'valid': False, 'error': 'No demand column found'}
        
        try:
            demand_series = pd.to_numeric(df[demand_col], errors='coerce').dropna()
            
            if demand_series.empty:
                return {'statistical_score': 0.0, 'valid': False, 'error': 'No valid demand data'}
            
            # Basic statistics
            stats_summary = {
                'count': len(demand_series),
                'mean': float(demand_series.mean()),
                'median': float(demand_series.median()),
                'std': float(demand_series.std()),
                'min': float(demand_series.min()),
                'max': float(demand_series.max()),
                'range': float(demand_series.max() - demand_series.min())
            }
            
            # Distribution characteristics
            stats_summary.update({
                'skewness': float(demand_series.skew()),
                'kurtosis': float(demand_series.kurtosis()),
                'coefficient_of_variation': float(demand_series.std() / demand_series.mean() * 100) if demand_series.mean() > 0 else 0
            })
            
            # Load factor calculation
            load_factor = (demand_series.mean() / demand_series.max()) * 100 if demand_series.max() > 0 else 0
            stats_summary['load_factor_percent'] = float(load_factor)
            
            # Realism checks
            realism_checks = {
                'reasonable_load_factor': 10 <= load_factor <= 95,
                'reasonable_cv': 5 <= stats_summary['coefficient_of_variation'] <= 100,
                'no_extreme_outliers': abs(stats_summary['skewness']) <= 3,
                'positive_values_only': stats_summary['min'] >= 0
            }
            
            # Statistical score calculation
            realism_score = sum(realism_checks.values()) / len(realism_checks)
            
            # Distribution normality test (for information)
            normality_test = {}
            try:
                if len(demand_series) <= 5000:  # Shapiro-Wilk for smaller samples
                    shapiro_stat, shapiro_p = stats.shapiro(demand_series.sample(min(len(demand_series), 5000)))
                    normality_test['shapiro_wilk'] = {
                        'statistic': float(shapiro_stat),
                        'p_value': float(shapiro_p),
                        'is_normal': shapiro_p > 0.05
                    }
                
                # Kolmogorov-Smirnov test
                ks_stat, ks_p = stats.kstest(demand_series, 'norm', args=(demand_series.mean(), demand_series.std()))
                normality_test['kolmogorov_smirnov'] = {
                    'statistic': float(ks_stat),
                    'p_value': float(ks_p),
                    'is_normal': ks_p > 0.05
                }
            except Exception as e:
                normality_test['error'] = str(e)
            
            return {
                'statistical_score': realism_score,
                'valid': realism_score >= 0.7,
                'statistics': stats_summary,
                'realism_checks': realism_checks,
                'normality_tests': normality_test
            }
            
        except Exception as e:
            return {
                'statistical_score': 0.0,
                'valid': False,
                'error': str(e)
            }
    
    def validate_base_year_data(self, df: pd.DataFrame, base_year: int) -> Dict[str, Any]:
        """Validate base year data completeness and quality"""
        try:
            # Add fiscal year column
            df_work = df.copy()
            df_work['fiscal_year'] = df_work['datetime'].apply(
                lambda x: self._get_fiscal_year(x, self.fy_start_month)
            )
            
            # Filter for base year
            base_data = df_work[df_work['fiscal_year'] == base_year]
            
            if base_data.empty:
                return {
                    'valid': False,
                    'error': f'No data found for fiscal year {base_year}',
                    'completeness_score': 0.0
                }
            
            # Expected hours in fiscal year (handle leap years)
            is_leap_year = self._is_leap_year_affecting_fy(base_year, self.fy_start_month)
            expected_hours = 8784 if is_leap_year else 8760
            actual_hours = len(base_data)
            
            completeness_percentage = actual_hours / expected_hours * 100
            
            # Gap analysis
            base_data_sorted = base_data.sort_values('datetime')
            time_diffs = base_data_sorted['datetime'].diff()
            gaps = time_diffs[time_diffs > pd.Timedelta(hours=1)]
            
            # Quality metrics
            demand_stats = {
                'mean': float(base_data['demand'].mean()),
                'std': float(base_data['demand'].std()),
                'min': float(base_data['demand'].min()),
                'max': float(base_data['demand'].max()),
                'load_factor': float((base_data['demand'].mean() / base_data['demand'].max()) * 100) if base_data['demand'].max() > 0 else 0
            }
            
            # Overall validation
            completeness_score = min(1.0, actual_hours / self.validation_thresholds['min_base_year_hours'])
            quality_score = 1.0 if len(gaps) <= 10 else max(0.0, 1.0 - len(gaps) / 100)
            
            overall_score = (completeness_score + quality_score) / 2
            
            return {
                'valid': overall_score >= 0.8,
                'base_year': base_year,
                'completeness_score': completeness_score,
                'quality_score': quality_score,
                'overall_score': overall_score,
                'hours': {
                    'expected': expected_hours,
                    'actual': actual_hours,
                    'completeness_percentage': completeness_percentage
                },
                'gaps': {
                    'count': len(gaps),
                    'largest_gap_hours': float(gaps.max().total_seconds() / 3600) if not gaps.empty else 0
                },
                'demand_statistics': demand_stats,
                'date_range': {
                    'start': base_data['datetime'].min().isoformat(),
                    'end': base_data['datetime'].max().isoformat()
                }
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'completeness_score': 0.0
            }
    
    # Helper methods
    def _find_datetime_column(self, df: pd.DataFrame) -> Optional[str]:
        """Find datetime column with intelligent matching"""
        datetime_keywords = ['datetime', 'timestamp', 'date_time', 'date', 'time']
        for col in df.columns:
            col_lower = str(col).lower().replace(' ', '_').replace('-', '_')
            if any(keyword in col_lower for keyword in datetime_keywords):
                return col
        return None
    
    def _find_demand_column(self, df: pd.DataFrame) -> Optional[str]:
        """Find demand column with intelligent matching"""
        demand_keywords = ['demand', 'load', 'power', 'kw', 'consumption', 'energy']
        for col in df.columns:
            col_lower = str(col).lower().replace(' ', '_').replace('-', '_')
            if any(keyword in col_lower for keyword in demand_keywords):
                return col
        return None
    
    def _detect_outliers(self, series: pd.Series) -> Dict[str, float]:
        """Detect outliers using IQR method"""
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
    
    def _get_fiscal_year(self, date_obj: datetime, fy_start_month: int) -> int:
        """Convert datetime to fiscal year"""
        if date_obj.month >= fy_start_month:
            return date_obj.year + 1
        else:
            return date_obj.year
    
    def _is_leap_year_affecting_fy(self, fiscal_year: int, fy_start_month: int) -> bool:
        """Check if leap year affects this fiscal year"""
        if fy_start_month <= 2:
            calendar_year = fiscal_year - 1
        else:
            calendar_year = fiscal_year
        
        return (calendar_year % 4 == 0 and 
                (calendar_year % 100 != 0 or calendar_year % 400 == 0))
    
    def _analyze_fiscal_years(self, df: pd.DataFrame, fy_start_month: int) -> Dict[str, Any]:
        """Analyze fiscal years present in data"""
        df['fiscal_year'] = df['datetime'].apply(
            lambda x: self._get_fiscal_year(x, fy_start_month)
        )
        
        fiscal_year_stats = df.groupby('fiscal_year').agg({
            'datetime': ['count', 'min', 'max']
        }).round(2)
        
        fiscal_year_stats.columns = ['hours', 'start_date', 'end_date']
        
        return {
            'fiscal_years_detected': sorted(df['fiscal_year'].unique().tolist()),
            'fiscal_year_stats': fiscal_year_stats.to_dict('index'),
            'most_complete_year': int(fiscal_year_stats['hours'].idxmax()) if not fiscal_year_stats.empty else None
        }
    
    def _generate_validation_recommendations(self, validation_details: Dict[str, Any]) -> List[str]:
        """Generate validation recommendations"""
        recommendations = []
        
        # Excel structure recommendations
        excel_validation = validation_details.get('excel_structure', {})
        if not excel_validation.get('valid', False):
            recommendations.append("Excel file structure issues detected. Ensure 'Past_Hourly_Demand' sheet exists with datetime and demand columns.")
        
        # Data content recommendations
        data_validation = validation_details.get('data_content', {})
        if data_validation.get('missing_data', {}).get('percentage', 0) > 5:
            recommendations.append("High percentage of missing data detected. Consider data cleaning before generation.")
        
        if data_validation.get('outliers', {}).get('percentage', 0) > 10:
            recommendations.append("High percentage of outliers detected. Review data for errors or unusual patterns.")
        
        # Temporal recommendations
        temporal_validation = validation_details.get('temporal_structure', {})
        if temporal_validation.get('gaps', {}).get('large_gaps_count', 0) > 5:
            recommendations.append("Multiple large gaps in time series detected. Consider interpolation or data completion.")
        
        # Statistical recommendations
        statistical_validation = validation_details.get('statistical_properties', {})
        realism_checks = statistical_validation.get('realism_checks', {})
        
        if not realism_checks.get('reasonable_load_factor', True):
            recommendations.append("Load factor appears unrealistic. Verify demand values and units.")
        
        if not realism_checks.get('positive_values_only', True):
            recommendations.append("Negative demand values detected. Review and correct data issues.")
        
        if not recommendations:
            recommendations.append("Data validation passed. File is ready for load profile generation.")
        
        return recommendations