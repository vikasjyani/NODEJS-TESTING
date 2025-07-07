
# models/load_profile_generator.py

"""
Load Profile Generator with Base Profile Scaling and Optimized STL methods
Handles financial year calculations and constraint applications
Now includes dynamic calculation of monthly peaks and load factors when not in template
"""
import pandas as pd
import numpy as np
import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import holidays

# Optional: STL decomposition (install statsmodels if using STL method)
try:
    from statsmodels.tsa.seasonal import STL
    STL_AVAILABLE = True
except ImportError:
    STL_AVAILABLE = False
    logging.warning("STL not available. Install statsmodels for STL decomposition: pip install statsmodels")

from utils.helpers import ensure_directory, get_file_info
from utils.constants import UNIT_FACTORS, VALIDATION_RULES
from utils.response_utils import success_response, error_response

logger = logging.getLogger(__name__)

class LoadProfileGenerator:
    """
    Load Profile Generator supporting multiple methods and constraints
    """
    
    def __init__(self, project_path):
        self.project_path = Path(project_path)
        self.inputs_path = self.project_path / 'inputs'
        self.results_path = self.project_path / 'results' / 'load_profiles'
        self.config_path = self.project_path / 'config'
        
        ensure_directory(str(self.results_path))
        ensure_directory(str(self.config_path))
        
        # Initialize holidays for Kerala (can be configured)
        self.holidays_data = self._initialize_holidays()
        
        logger.info(f"LoadProfileGenerator initialized for project: {project_path}")
    
    def _initialize_holidays(self, years_range=(2017, 2040), region='IN', subdiv='KL'):
        """Initialize holiday data for the specified region"""
        try:
            years = range(years_range[0], years_range[1])
            holiday_calendar = holidays.country_holidays(region, subdiv=subdiv, years=years)
            
            holidays_df = pd.DataFrame(
                [(date, name) for date, name in holiday_calendar.items()],
                columns=['Date', 'Holiday']
            )
            holidays_df['Date'] = pd.to_datetime(holidays_df['Date'])
            
            logger.info(f"Loaded {len(holidays_df)} holidays for {region}-{subdiv}")
            return holidays_df
            
        except Exception as e:
            logger.warning(f"Could not load holidays: {e}")
            return pd.DataFrame(columns=['Date', 'Holiday'])

    def load_template_data(self, template_file=None):
        """
        Load data from the load curve template Excel file
        
        Returns:
            dict: Contains historical_demand, total_demand, monthly_peaks, monthly_load_factors
        """
        if not template_file:
            template_file = self.inputs_path / 'load_curve_template.xlsx'
        
        if not os.path.exists(template_file):
            raise FileNotFoundError(f"Template file not found: {template_file}")
        
        try:
            # Load required sheets
            historical_demand = pd.read_excel(template_file, sheet_name='Past_Hourly_Demand')
            
            # Try alternative sheet name for Total Demand
            try:
                total_demand = pd.read_excel(template_file, sheet_name='Total_Demand')
            except Exception:
                logger.info("Could not find 'Total_Demand' sheet, trying 'Total Demand' instead.")
                total_demand = pd.read_excel(template_file, sheet_name='Total Demand')
            
            # Optional sheets
            monthly_peaks = None
            monthly_load_factors = None
            
            try:
                monthly_peaks = pd.read_excel(template_file, sheet_name='Monthly_Peak_Demand')
                logger.info("Monthly_Peak_Demand sheet loaded from template")
            except:
                logger.info("Monthly_Peak_Demand sheet not found, will calculate dynamically")
            
            try:
                monthly_load_factors = pd.read_excel(template_file, sheet_name='Monthly_Load_Factors')
                logger.info("Monthly_Load_Factors sheet loaded from template")
            except:
                logger.info("Monthly_Load_Factors sheet not found, will calculate dynamically")
            
            # Process historical demand
            historical_demand = self._process_historical_demand(historical_demand)
            
            # Process total demand to financial years
            total_demand = self._process_total_demand(total_demand)
            
            # Calculate dynamic constraints if not available in template
            calculated_monthly_peaks = None
            calculated_load_factors = None
            
            if monthly_peaks is None:
                calculated_monthly_peaks = self._calculate_monthly_peaks(historical_demand)
                logger.info("Calculated monthly peaks from historical data")
            
            if monthly_load_factors is None:
                calculated_load_factors = self._calculate_monthly_load_factors(historical_demand)
                logger.info("Calculated monthly load factors from historical data")
            
            logger.info(f"Template data loaded successfully from {template_file}")
            
            return {
                'historical_demand': historical_demand,
                'total_demand': total_demand,
                'monthly_peaks': monthly_peaks,
                'monthly_load_factors': monthly_load_factors,
                'calculated_monthly_peaks': calculated_monthly_peaks,
                'calculated_load_factors': calculated_load_factors,
                'template_info': get_file_info(str(template_file))
            }
            
        except Exception as e:
            logger.error(f"Error loading template data: {e}")
            raise ValueError(f"Failed to load template data: {str(e)}")

    def _calculate_monthly_peaks(self, historical_data):
        """
        Calculate monthly peak fractions from historical data
        
        Args:
            historical_data (pd.DataFrame): Historical demand data with time features
            
        Returns:
            pd.DataFrame: Monthly peaks by financial year
        """
        try:
            if historical_data.empty:
                return None
            
            # Calculate monthly totals and peaks for each financial year
            monthly_stats = []
            
            for fy in historical_data['financial_year'].unique():
                fy_data = historical_data[historical_data['financial_year'] == fy]
                
                if len(fy_data) < 8000:  # Skip incomplete years
                    continue
                
                # Calculate annual total
                annual_total = fy_data['demand'].sum()
                
                if annual_total <= 0:
                    continue
                
                # Calculate monthly shares and peaks
                monthly_row = {'Financial_Year': fy}
                
                for month in range(1, 13):
                    month_data = fy_data[fy_data['financial_month'] == month]
                    
                    if not month_data.empty:
                        monthly_total = month_data['demand'].sum()
                        monthly_peak = month_data['demand'].max()
                        
                        # Calculate monthly share
                        monthly_share = monthly_total / annual_total if annual_total > 0 else 0
                        
                        # Store monthly share (this will be used for future scaling)
                        month_names = ['Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep',
                                     'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar']
                        month_col = month_names[month - 1]
                        monthly_row[month_col] = monthly_share
                
                monthly_stats.append(monthly_row)
            
            if not monthly_stats:
                return None
            
            # Create DataFrame and average across years
            monthly_peaks_df = pd.DataFrame(monthly_stats)
            
            # Calculate average monthly shares across all years
            month_cols = ['Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep',
                         'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar']
            
            avg_shares = {}
            for col in month_cols:
                if col in monthly_peaks_df.columns:
                    avg_shares[col] = monthly_peaks_df[col].mean()
            
            # Create final dataframe with average values
            final_peaks = pd.DataFrame([avg_shares])
            final_peaks['Financial_Year'] = 'Average'
            
            logger.info(f"Calculated monthly peaks for {len(monthly_stats)} years")
            return final_peaks
            
        except Exception as e:
            logger.error(f"Error calculating monthly peaks: {e}")
            return None

    def _calculate_monthly_load_factors(self, historical_data):
        """
        Calculate monthly load factors from historical data
        
        Args:
            historical_data (pd.DataFrame): Historical demand data with time features
            
        Returns:
            pd.DataFrame: Monthly load factors by financial year
        """
        try:
            if historical_data.empty:
                return None
            
            monthly_lf_stats = []
            
            for fy in historical_data['financial_year'].unique():
                fy_data = historical_data[historical_data['financial_year'] == fy]
                
                if len(fy_data) < 8000:  # Skip incomplete years
                    continue
                
                monthly_row = {'Financial_Year': fy}
                
                for month in range(1, 13):
                    month_data = fy_data[fy_data['financial_month'] == month]
                    
                    if not month_data.empty:
                        avg_demand = month_data['demand'].mean()
                        max_demand = month_data['demand'].max()
                        
                        # Calculate load factor
                        load_factor = avg_demand / max_demand if max_demand > 0 else 0
                        
                        month_names = ['Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep',
                                     'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar']
                        month_col = month_names[month - 1]
                        monthly_row[month_col] = load_factor
                
                monthly_lf_stats.append(monthly_row)
            
            if not monthly_lf_stats:
                return None
            
            # Create DataFrame and average across years
            monthly_lf_df = pd.DataFrame(monthly_lf_stats)
            
            # Calculate average load factors across all years
            month_cols = ['Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep',
                         'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar']
            
            avg_lf = {}
            for col in month_cols:
                if col in monthly_lf_df.columns:
                    avg_lf[col] = monthly_lf_df[col].mean()
            
            # Create final dataframe with average values
            final_lf = pd.DataFrame([avg_lf])
            final_lf['Financial_Year'] = 'Average'
            
            logger.info(f"Calculated monthly load factors for {len(monthly_lf_stats)} years")
            return final_lf
            
        except Exception as e:
            logger.error(f"Error calculating monthly load factors: {e}")
            return None

    def _process_historical_demand(self, df):
        """Process historical demand data with datetime and feature engineering"""
        try:
            # Create datetime column
            if 'date' in df.columns and 'time' in df.columns:
                df['ds'] = pd.to_datetime(df['date'].astype(str) + ' ' + df['time'].astype(str))
            elif 'datetime' in df.columns:
                df['ds'] = pd.to_datetime(df['datetime'])
            else:
                raise ValueError("Historical demand must have 'date'+'time' or 'datetime' columns")
            
            # Handle demand column
            demand_col = 'demand'
            if demand_col not in df.columns:
                # Try common alternatives
                alt_cols = ['Demand', 'load', 'Load', 'power', 'Power']
                for col in alt_cols:
                    if col in df.columns:
                        demand_col = col
                        break
                else:
                    raise ValueError("Could not find demand column in historical data")
            
            # Clean data
            df = df[['ds', demand_col]].rename(columns={demand_col: 'demand'})
            df = df.dropna()
            
            # Handle duplicates by taking mean
            if df['ds'].duplicated().sum() > 0:
                logger.warning(f"Found {df['ds'].duplicated().sum()} duplicate timestamps, taking mean")
                df = df.groupby('ds', as_index=False)['demand'].mean()
            
            # Sort by datetime
            df = df.sort_values('ds').reset_index(drop=True)
            
            # Add features
            df = self._add_time_features(df)
            
            logger.info(f"Processed {len(df)} historical demand records")
            return df
            
        except Exception as e:
            logger.error(f"Error processing historical demand: {e}")
            raise
    
    def _process_total_demand(self, df):
        """Process total demand data ensuring financial year format"""
        try:
            # Check if we have Financial_Year column
            if 'Financial_Year' not in df.columns:
                if 'Year' in df.columns:
                    # Convert calendar year to financial year (assuming April start)
                    df['Financial_Year'] = df['Year'] + 1
                    logger.info("Converted calendar years to financial years")
                else:
                    raise ValueError("Total demand must have 'Financial_Year' or 'Year' column")
            
            # Check for demand column
            demand_col = None
            for col in ['Total_Demand', 'Total demand', 'Demand', 'Total_On_Grid_Demand']:
                if col in df.columns:
                    demand_col = col
                    break
            
            if not demand_col:
                raise ValueError("Could not find total demand column")
            
            # Clean and standardize
            result = df[['Financial_Year', demand_col]].copy()
            result = result.rename(columns={demand_col: 'Total_Demand'})
            result = result.dropna()
            result = result.sort_values('Financial_Year').reset_index(drop=True)
            
            logger.info(f"Processed total demand for {len(result)} financial years")
            return result
            
        except Exception as e:
            logger.error(f"Error processing total demand: {e}")
            raise
    
    def _add_time_features(self, df):
        """Add comprehensive time-based features"""
        df = df.copy()
        
        # Basic time features
        df['hour'] = df['ds'].dt.hour
        df['dayofweek'] = df['ds'].dt.dayofweek
        df['month'] = df['ds'].dt.month
        df['year'] = df['ds'].dt.year
        df['day'] = df['ds'].dt.day
        
        # Financial year (April to March)
        df['financial_year'] = np.where(df['month'] >= 4, df['year'] + 1, df['year'])
        
        # Financial month (April = 1, May = 2, ..., March = 12)
        df['financial_month'] = np.where(df['month'] >= 4, df['month'] - 3, df['month'] + 9)
        
        # Weekend flag
        df['is_weekend'] = df['dayofweek'].isin([5, 6]).astype(int)
        
        # Holiday flag
        if not self.holidays_data.empty:
            df['is_holiday'] = df['ds'].dt.date.isin(self.holidays_data['Date'].dt.date).astype(int)
        else:
            df['is_holiday'] = 0
        
        # Special day flag (weekend or holiday)
        df['is_special_day'] = (df['is_weekend'] | df['is_holiday']).astype(int)
        
        return df
    
    def load_scenario_data(self, scenario_path):
        """
        Load demand scenario data from CSV file
        
        Args:
            scenario_path (str): Path to scenario CSV file
            
        Returns:
            pd.DataFrame: Processed scenario data with financial years
        """
        try:
            scenario_df = pd.read_csv(scenario_path)
            
            # Find year and demand columns
            year_col = None
            demand_col = None
            
            for col in ['Year', 'Financial_Year', 'year']:
                if col in scenario_df.columns:
                    year_col = col
                    break
            
            for col in ['Total_On_Grid_Demand', 'Total', 'Total_Demand', 'Demand']:
                if col in scenario_df.columns:
                    demand_col = col
                    break
            
            if not year_col or not demand_col:
                raise ValueError("Scenario file must have year and demand columns")
            
            # Process data
            result = scenario_df[[year_col, demand_col]].copy()
            result = result.rename(columns={year_col: 'Year', demand_col: 'Total_Demand'})
            
            # Convert to financial year if needed
            if year_col != 'Financial_Year':
                result['Financial_Year'] = result['Year'] + 1
            else:
                result['Financial_Year'] = result['Year']
            
            result = result[['Financial_Year', 'Total_Demand']].dropna()
            result = result.sort_values('Financial_Year').reset_index(drop=True)
            
            logger.info(f"Loaded scenario data for {len(result)} financial years")
            return result
            
        except Exception as e:
            logger.error(f"Error loading scenario data: {e}")
            raise
    
    def get_available_base_years(self, historical_data):
        """Get available financial years from historical data for base year selection"""
        if historical_data.empty:
            return []
        
        # Get complete financial years only
        year_counts = historical_data.groupby('financial_year').size()
        
        # A complete financial year should have close to 8760 hours (365*24) or 8784 (366*24)
        complete_years = year_counts[year_counts >= 8000].index.tolist()
        
        return sorted(complete_years)
    
    def extract_base_profiles(self, historical_data, base_year):
        """
        Extract load profiles from a specific base year
        
        Args:
            historical_data (pd.DataFrame): Historical demand data
            base_year (int): Financial year to use as base
            
        Returns:
            pd.DataFrame: Load profiles by financial_month, is_special_day, hour
        """
        try:
            # Filter data for base year
            base_data = historical_data[historical_data['financial_year'] == base_year].copy()
            
            if base_data.empty:
                raise ValueError(f"No data available for base year {base_year}")
            
            # Calculate daily totals
            daily_totals = base_data.groupby(['financial_year', 'financial_month', 'day'])['demand'].sum().reset_index()
            daily_totals.rename(columns={'demand': 'daily_total'}, inplace=True)
            
            # Merge daily totals back
            base_data = base_data.merge(daily_totals, on=['financial_year', 'financial_month', 'day'])
            
            # Calculate hourly fractions
            base_data['fraction'] = base_data['demand'] / base_data['daily_total']
            base_data['fraction'] = base_data['fraction'].fillna(0)
            
            # Extract profiles by financial_month, special day flag, and hour
            profiles = base_data.groupby(['financial_month', 'is_special_day', 'hour'])['fraction'].mean().reset_index()
            
            # Validate profiles
            profiles['fraction'] = profiles['fraction'].clip(lower=0, upper=1)
            
            logger.info(f"Extracted {len(profiles)} load profile patterns from base year {base_year}")
            return profiles
            
        except Exception as e:
            logger.error(f"Error extracting base profiles: {e}")
            raise
    
    def generate_base_profile_forecast(self, historical_data, demand_scenarios, base_year, 
                                     start_fy, end_fy, frequency='hourly', constraints=None):
        """
        Generate load profile forecast using base year scaling method
        
        Args:
            historical_data (pd.DataFrame): Historical demand data
            demand_scenarios (pd.DataFrame): Future demand scenarios
            base_year (int): Base financial year for profile extraction
            start_fy (int): Start financial year for forecast
            end_fy (int): End financial year for forecast
            frequency (str): Output frequency ('hourly', '15min', etc.)
            constraints (dict): Optional constraints
            
        Returns:
            dict: Forecast results and metadata
        """
        try:
            # Extract base profiles
            profiles = self.extract_base_profiles(historical_data, base_year)
            
            # Generate future dates
            future_dates = self._generate_future_dates(start_fy, end_fy, frequency)
            
            # Create forecast dataframe
            forecast_df = pd.DataFrame({'ds': future_dates})
            forecast_df = self._add_time_features(forecast_df)
            
            # Apply base profiles
            forecast_df = self._apply_base_profiles(forecast_df, profiles, demand_scenarios)
            
            # Apply constraints if provided
            if constraints:
                forecast_df = self._apply_constraints(forecast_df, constraints, demand_scenarios, historical_data)
            
            # Final processing
            forecast_df['demand'] = forecast_df['demand'].clip(lower=0)
            forecast_df['demand'] = forecast_df['demand'].round(2)
            
            # Validation
            validation_results = self._validate_forecast(forecast_df, demand_scenarios, constraints)
            
            # Prepare results
            results = {
                'method': 'base_profile_scaling',
                'base_year': base_year,
                'start_fy': start_fy,
                'end_fy': end_fy,
                'frequency': frequency,
                'forecast': forecast_df[['ds', 'demand', 'financial_year', 'financial_month', 'hour']],
                'validation': validation_results,
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'total_hours': len(forecast_df),
                    'method_config': {
                        'base_year': base_year,
                        'profiles_count': len(profiles)
                    }
                }
            }
            
            logger.info(f"Generated base profile forecast: {len(forecast_df)} records")
            return success_response("Base profile forecast generated successfully", results)
            
        except Exception as e:
            logger.error(f"Error generating base profile forecast: {e}")
            return error_response(f"Failed to generate forecast: {str(e)}")

    # OPTIMIZED STL SECTION - Enhanced with Load Factor Improvement
    def generate_stl_forecast(self, historical_data, demand_scenarios, start_fy, end_fy, 
                            frequency='hourly', stl_params=None, constraints=None, lf_improvement=None):
        """
        Generate load profile forecast using STL decomposition method with enhanced load factor improvement
        
        Args:
            historical_data (pd.DataFrame): Historical demand data
            demand_scenarios (pd.DataFrame): Future demand scenarios
            start_fy (int): Start financial year for forecast
            end_fy (int): End financial year for forecast
            frequency (str): Output frequency
            stl_params (dict): STL parameters
            constraints (dict): Optional constraints
            lf_improvement (dict): Load factor improvement parameters
                - enabled (bool): Whether to apply load factor improvement
                - target_year (int): Target financial year to achieve improvement
                - improvement_percent (float): Percentage improvement in load factor
            
        Returns:
            dict: Forecast results and metadata
        """
        if not STL_AVAILABLE:
            return error_response("STL decomposition not available. Install statsmodels package.")
        
        try:
            # Validate inputs
            validation_result = self._validate_stl_inputs(historical_data, demand_scenarios, start_fy, end_fy, lf_improvement)
            if not validation_result['valid']:
                return error_response(f"STL validation failed: {'; '.join(validation_result['errors'])}")
            
            # Set optimized STL parameters
            stl_params = self._optimize_stl_parameters(historical_data, stl_params)
            
            # Perform enhanced STL decomposition
            stl_result = self._perform_enhanced_stl_decomposition(historical_data, stl_params)
            
            # Generate future dates
            future_dates = self._generate_future_dates(start_fy, end_fy, frequency)
            
            # Create forecast using optimized STL components
            forecast_df = self._create_optimized_stl_forecast(future_dates, stl_result, demand_scenarios, historical_data)
            
            # Apply constraints if provided
            if constraints:
                forecast_df = self._apply_constraints(forecast_df, constraints, demand_scenarios, historical_data)
            
            # Apply enhanced load factor improvement if requested
            if lf_improvement and lf_improvement.get('enabled', False):
                forecast_df = self._apply_enhanced_load_factor_improvement(
                    forecast_df, 
                    lf_improvement.get('target_year'), 
                    lf_improvement.get('improvement_percent'),
                    start_fy,
                    historical_data
                )
            
            # Final processing and validation
            forecast_df = self._finalize_stl_forecast(forecast_df)
            
            # Comprehensive validation
            validation_results = self._validate_stl_forecast(forecast_df, demand_scenarios, constraints, historical_data)
            
            # Prepare optimized results
            results = {
                'method': 'stl_decomposition',
                'start_fy': start_fy,
                'end_fy': end_fy,
                'frequency': frequency,
                'forecast': forecast_df[['ds', 'demand', 'financial_year', 'financial_month', 'hour']],
                'validation': validation_results,
                'stl_components': {
                    'trend_growth_rate': stl_result.get('trend_growth_rate', 0),
                    'seasonal_strength': stl_result.get('seasonal_strength', 0),
                    'noise_level': stl_result.get('noise_level', 0),
                    'decomposition_quality': stl_result.get('quality_score', 0)
                },
                'load_factor_improvement': lf_improvement if lf_improvement and lf_improvement.get('enabled') else None,
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'total_hours': len(forecast_df),
                    'method_config': stl_params,
                    'realistic_profile_score': validation_results.get('realism_score', 0)
                }
            }
            
            logger.info(f"Generated optimized STL forecast: {len(forecast_df)} records with quality score: {stl_result.get('quality_score', 0):.3f}")
            return success_response("STL forecast generated successfully", results)
            
        except Exception as e:
            logger.error(f"Error generating STL forecast: {e}")
            return error_response(f"Failed to generate STL forecast: {str(e)}")

    def _validate_stl_inputs(self, historical_data, demand_scenarios, start_fy, end_fy, lf_improvement):
        """Comprehensive validation of STL inputs"""
        errors = []
        
        # Historical data validation
        if historical_data.empty:
            errors.append("Historical data is empty")
        elif len(historical_data) < 24 * 365 * 2:  # Minimum 2 years
            errors.append("Need at least 2 years of hourly data for reliable STL decomposition")
        
        # Demand scenarios validation
        if demand_scenarios.empty:
            errors.append("Demand scenarios data is empty")
        
        # Year validation
        if start_fy >= end_fy:
            errors.append("Start year must be before end year")
        if end_fy - start_fy > 30:
            errors.append("Forecast period exceeds 30 years - may affect accuracy")
        
        # Load factor improvement validation
        if lf_improvement and lf_improvement.get('enabled'):
            target_year = lf_improvement.get('target_year')
            improvement_percent = lf_improvement.get('improvement_percent')
            
            if not target_year or target_year < start_fy:
                errors.append("Target year must be >= start year")
            if not improvement_percent or improvement_percent <= 0 or improvement_percent > 50:
                errors.append("Improvement percent must be between 0 and 50")
        
        return {'valid': len(errors) == 0, 'errors': errors}

    def _optimize_stl_parameters(self, historical_data, stl_params):
        """Optimize STL parameters based on data characteristics"""
        if not stl_params:
            stl_params = {}
        
        # Analyze data frequency and length
        data_length = len(historical_data)
        
        # Optimize period parameter
        if 'period' not in stl_params:
            if data_length >= 24 * 365 * 3:  # 3+ years
                stl_params['period'] = 24 * 365  # Annual seasonality
            else:
                stl_params['period'] = min(24 * 365, data_length // 4)  # Adaptive period
        
        # Optimize seasonal parameter
        if 'seasonal' not in stl_params:
            stl_params['seasonal'] = max(7, min(21, stl_params['period'] // 365))  # Adaptive seasonal
        
        # Optimize trend parameter - must be odd integer > period
        if 'trend' not in stl_params:
            period = stl_params['period']
            # Calculate trend as odd integer greater than period
            candidate_trend = int(1.5 * period)
            # Ensure it's odd and greater than period
            if candidate_trend <= period:
                candidate_trend = period + 1
            if candidate_trend % 2 == 0:  # Make it odd
                candidate_trend += 1
            stl_params['trend'] = candidate_trend
        else:
            # Validate existing trend parameter
            trend = stl_params['trend']
            period = stl_params['period']
            if isinstance(trend, float):
                trend = int(trend)
            if trend <= period:
                trend = period + 1
            if trend % 2 == 0:  # Make it odd
                trend += 1
            stl_params['trend'] = trend
        
        # Always use robust mode for real-world data
        stl_params['robust'] = stl_params.get('robust', True)
        
        logger.info(f"Optimized STL parameters: {stl_params}")
        return stl_params

    def _perform_enhanced_stl_decomposition(self, historical_data, stl_params):
        """Enhanced STL decomposition with quality assessment"""
        try:
            # Prepare data
            data = historical_data.sort_values('ds').copy()
            demand_series = data.set_index('ds')['demand']
            
            # Create complete time index
            full_index = pd.date_range(
                start=demand_series.index.min(), 
                end=demand_series.index.max(), 
                freq='h'
            )
            
            # Reindex and interpolate missing values
            demand_series = demand_series.reindex(full_index)
            missing_count = demand_series.isna().sum()
            
            if missing_count > 0:
                logger.info(f"Interpolating {missing_count} missing values")
                demand_series = demand_series.interpolate(method='linear', limit_direction='both')
            
            # Apply smoothing for noisy data
            if demand_series.std() / demand_series.mean() > 0.5:  # High variability
                demand_series = demand_series.rolling(window=3, center=True).mean().fillna(demand_series)
            
            # Perform STL decomposition
            stl = STL(
                demand_series, 
                period=int(stl_params['period']),
                seasonal=int(stl_params['seasonal']),
                trend=int(stl_params['trend']) if stl_params.get('trend') else None,
                robust=stl_params.get('robust', True)
            )
            
            result = stl.fit()
            
            # Calculate enhanced metrics
            trend_values = result.trend.dropna()
            seasonal_values = result.seasonal
            residual_values = result.resid.dropna()
            
            # Trend analysis
            if len(trend_values) >= 2:
                x = np.arange(len(trend_values))
                trend_slope = np.polyfit(x, trend_values, 1)[0]
                trend_growth_rate = trend_slope * 24 * 365  # Annual growth
            else:
                trend_growth_rate = 0
            
            # Seasonal strength
            seasonal_var = seasonal_values.var()
            residual_var = residual_values.var()
            total_var = seasonal_var + residual_var
            seasonal_strength = seasonal_var / total_var if total_var > 0 else 0
            
            # Noise level assessment
            noise_level = residual_var / demand_series.var() if demand_series.var() > 0 else 0
            
            # Quality score (0-1, higher is better)
            quality_score = max(0, min(1, seasonal_strength - noise_level))
            
            # Enhanced seasonal pattern extraction
            seasonal_pattern = self._extract_enhanced_seasonal_pattern(seasonal_values, stl_params['period'])
            
            return {
                'trend': result.trend,
                'seasonal': result.seasonal,
                'resid': result.resid,
                'trend_growth_rate': trend_growth_rate,
                'seasonal_strength': seasonal_strength,
                'noise_level': noise_level,
                'quality_score': quality_score,
                'original_index': demand_series.index,
                'seasonal_pattern': seasonal_pattern,
                'baseline_stats': {
                    'mean': float(demand_series.mean()),
                    'std': float(demand_series.std()),
                    'peak': float(demand_series.max()),
                    'load_factor': float(demand_series.mean() / demand_series.max()) if demand_series.max() > 0 else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error in enhanced STL decomposition: {e}")
            raise

    def _extract_enhanced_seasonal_pattern(self, seasonal_values, period):
        """Extract and enhance seasonal patterns"""
        try:
            # Reshape seasonal values into pattern matrix
            pattern_length = int(period)
            n_patterns = len(seasonal_values) // pattern_length
            
            if n_patterns > 0:
                # Reshape and average patterns
                patterns = seasonal_values[:n_patterns * pattern_length].values.reshape(n_patterns, pattern_length)
                avg_pattern = np.mean(patterns, axis=0)
                
                # Smooth pattern to remove noise
                try:
                    from scipy.ndimage import gaussian_filter1d
                    smoothed_pattern = gaussian_filter1d(avg_pattern, sigma=1.0)
                except ImportError:
                    # Fallback to simple moving average
                    smoothed_pattern = pd.Series(avg_pattern).rolling(window=3, center=True).mean().fillna(avg_pattern).values
                
                return smoothed_pattern
            else:
                return seasonal_values.values[:pattern_length]
                
        except Exception as e:
            logger.warning(f"Failed to extract enhanced seasonal pattern: {e}")
            return seasonal_values.values[:min(len(seasonal_values), int(period))]

    def _create_optimized_stl_forecast(self, future_dates, stl_result, demand_scenarios, historical_data):
        """Create optimized forecast using STL components"""
        try:
            forecast_df = pd.DataFrame({'ds': future_dates})
            forecast_df = self._add_time_features(forecast_df)
            
            # Enhanced trend projection
            last_trend = stl_result['trend'].dropna().iloc[-1]
            trend_growth = stl_result['trend_growth_rate']
            baseline_mean = stl_result['baseline_stats']['mean']
            
            # Project trend with dampening for long forecasts
            hours_from_last = (forecast_df['ds'] - stl_result['original_index'][-1]).dt.total_seconds() / 3600
            years_from_last = hours_from_last / (24 * 365)
            
            # Apply dampening factor for long-term projections
            dampening_factor = np.exp(-0.1 * np.maximum(0, years_from_last - 5))  # Dampen after 5 years
            forecast_df['trend'] = last_trend + (trend_growth * years_from_last * dampening_factor)
            
            # Enhanced seasonal component
            seasonal_pattern = stl_result['seasonal_pattern']
            pattern_length = len(seasonal_pattern)
            
            # Create extended seasonal pattern
            forecast_length = len(forecast_df)
            seasonal_cycles = (forecast_length // pattern_length) + 1
            extended_seasonal = np.tile(seasonal_pattern, seasonal_cycles)[:forecast_length]
            
            # Add realistic variability to seasonal component
            seasonal_noise = np.random.normal(0, stl_result['baseline_stats']['std'] * 0.05, forecast_length)
            forecast_df['seasonal'] = extended_seasonal + seasonal_noise
            
            # Combine components with realistic constraints
            forecast_df['demand'] = forecast_df['trend'] + forecast_df['seasonal']
            
            # Apply realistic bounds
            historical_min = historical_data['demand'].quantile(0.01)
            historical_max = historical_data['demand'].quantile(0.99)
            
            # Expand bounds gradually for future years
            max_expansion = 1.5  # Maximum 50% expansion
            expansion_factor = 1 + (years_from_last * 0.1).clip(0, max_expansion - 1)
            
            lower_bound = historical_min * 0.8  # Allow some decrease
            upper_bound = historical_max * expansion_factor
            
            forecast_df['demand'] = forecast_df['demand'].clip(lower=lower_bound, upper=upper_bound)
            
            # Scale to match demand scenarios
            if not demand_scenarios.empty:
                forecast_df = self._scale_to_annual_targets(forecast_df, demand_scenarios)
            
            # Ensure realistic load patterns
            forecast_df = self._ensure_realistic_patterns(forecast_df, stl_result['baseline_stats'])
            
            return forecast_df
            
        except Exception as e:
            logger.error(f"Error creating optimized STL forecast: {e}")
            raise

    def _apply_enhanced_load_factor_improvement(self, forecast_df, target_year, improvement_percent, start_fy, historical_data):
        """Enhanced load factor improvement with realistic constraints"""
        try:
            if not target_year or not improvement_percent:
                return forecast_df
            
            # Ensure target year is within forecast range
            max_fy = forecast_df['financial_year'].max()
            target_year = min(target_year, max_fy)
            
            if target_year < start_fy:
                logger.warning(f"Target year {target_year} is before start year {start_fy}. No improvement applied.")
                return forecast_df
            
            modified_df = forecast_df.copy()
            
            # Calculate baseline load factor from historical data
            baseline_lf = self._calculate_baseline_load_factor(historical_data)
            
            # Calculate improvement for each year with smooth progression
            for fy in modified_df['financial_year'].unique():
                if fy < start_fy:
                    continue
                    
                # Calculate improvement progression
                if fy >= target_year:
                    year_improvement = improvement_percent
                else:
                    # Smooth S-curve progression instead of linear
                    progress = (fy - start_fy) / (target_year - start_fy) if target_year > start_fy else 1
                    # S-curve: slow start, rapid middle, slow end
                    s_curve_progress = 3 * progress**2 - 2 * progress**3
                    year_improvement = improvement_percent * s_curve_progress
                
                # Apply improvement to year data
                year_mask = modified_df['financial_year'] == fy
                year_data = modified_df.loc[year_mask, 'demand'].copy()
                
                if len(year_data) == 0:
                    continue
                
                # Calculate current load factor
                current_avg = year_data.mean()
                current_peak = year_data.max()
                current_lf = current_avg / current_peak if current_peak > 0 else 0
                
                # Calculate target load factor with realistic limits
                target_lf = current_lf * (1 + year_improvement / 100)
                target_lf = min(target_lf, 0.95)  # Cap at 95% for realism
                target_lf = max(target_lf, current_lf)  # Ensure no decrease
                
                if target_lf > current_lf:
                    # Apply sophisticated load factor improvement
                    improved_demand = self._apply_sophisticated_load_factor_improvement(
                        year_data.values, 
                        current_lf, 
                        target_lf,
                        baseline_lf
                    )
                    
                    # Update the forecast
                    modified_df.loc[year_mask, 'demand'] = improved_demand
                    
                    # Log improvement
                    new_avg = improved_demand.mean()
                    new_peak = improved_demand.max()
                    new_lf = new_avg / new_peak if new_peak > 0 else 0
                    
                    logger.info(f"FY{fy}: Load factor improved from {current_lf:.3f} to {new_lf:.3f} "
                               f"(target: {target_lf:.3f}, improvement: {year_improvement:.1f}%)")
            
            return modified_df
            
        except Exception as e:
            logger.error(f"Error applying enhanced load factor improvement: {e}")
            return forecast_df

    def _apply_sophisticated_load_factor_improvement(self, demand_array, current_lf, target_lf, baseline_lf):
        """Apply sophisticated load factor improvement maintaining realistic patterns"""
        try:
            demand = demand_array.copy()
            original_energy = demand.sum()
            
            # Calculate statistics
            avg_demand = demand.mean()
            peak_demand = demand.max()
            min_demand = demand.min()
            
            # Calculate new average based on target load factor
            target_avg = target_lf * peak_demand
            
            # Strategy: Peak shaving + Valley filling + Pattern preservation
            
            # 1. Identify peak hours (top 10%)
            peak_threshold = np.percentile(demand, 90)
            peak_mask = demand >= peak_threshold
            
            # 2. Identify valley hours (bottom 20%)
            valley_threshold = np.percentile(demand, 20)
            valley_mask = demand <= valley_threshold
            
            # 3. Calculate energy to redistribute
            peak_reduction_factor = 0.7  # Reduce peaks by 30%
            valley_fill_factor = 1.3     # Increase valleys by 30%
            
            # 4. Apply gradual peak shaving
            peak_reduction = (demand[peak_mask] - peak_threshold) * (1 - peak_reduction_factor)
            demand[peak_mask] -= peak_reduction
            
            # 5. Apply gradual valley filling
            valley_increase = (valley_threshold - demand[valley_mask]) * (valley_fill_factor - 1)
            demand[valley_mask] += valley_increase
            
            # 6. Smooth transitions to avoid abrupt changes
            demand = self._apply_smoothing_filter(demand, window_size=3)
            
            # 7. Scale to maintain total energy
            current_energy = demand.sum()
            if current_energy > 0:
                energy_scale_factor = original_energy / current_energy
                demand *= energy_scale_factor
            
            # 8. Final adjustment to target average
            current_new_avg = demand.mean()
            if current_new_avg > 0 and abs(current_new_avg - target_avg) > target_avg * 0.05:
                final_scale_factor = target_avg / current_new_avg
                demand *= final_scale_factor
            
            # 9. Ensure realistic bounds
            demand = np.clip(demand, min_demand * 0.8, peak_demand * 1.1)
            
            return demand
            
        except Exception as e:
            logger.error(f"Error in sophisticated load factor improvement: {e}")
            return demand_array

    def _apply_smoothing_filter(self, data, window_size=3):
        """Apply smoothing filter to data"""
        try:
            # Try scipy first
            from scipy.ndimage import uniform_filter1d
            return uniform_filter1d(data, size=window_size, mode='nearest')
        except ImportError:
            # Fallback to simple moving average
            return pd.Series(data).rolling(window=window_size, center=True).mean().fillna(data).values

    def _calculate_baseline_load_factor(self, historical_data):
        """Calculate baseline load factor from historical data"""
        try:
            if historical_data.empty or 'demand' not in historical_data.columns:
                return 0.6  # Default assumption
            
            avg_demand = historical_data['demand'].mean()
            peak_demand = historical_data['demand'].max()
            
            return avg_demand / peak_demand if peak_demand > 0 else 0.6
            
        except Exception as e:
            logger.warning(f"Error calculating baseline load factor: {e}")
            return 0.6

    def _ensure_realistic_patterns(self, forecast_df, baseline_stats):
        """Ensure forecast maintains realistic load patterns"""
        try:
            # Check for unrealistic values
            demand_mean = baseline_stats['mean']
            demand_std = baseline_stats['std']
            
            # Define realistic bounds (3-sigma rule)
            lower_bound = max(0, demand_mean - 3 * demand_std)
            upper_bound = demand_mean + 4 * demand_std  # Allow slightly higher peaks
            
            # Apply bounds
            forecast_df['demand'] = forecast_df['demand'].clip(lower=lower_bound, upper=upper_bound)
            
            # Ensure daily patterns make sense (if hourly data)
            if 'hour' in forecast_df.columns:
                forecast_df = self._adjust_daily_patterns(forecast_df, baseline_stats)
            
            return forecast_df
            
        except Exception as e:
            logger.warning(f"Error ensuring realistic patterns: {e}")
            return forecast_df

    def _adjust_daily_patterns(self, forecast_df, baseline_stats):
        """Adjust daily patterns to be realistic"""
        try:
            # Typical daily pattern adjustments
            hour_factors = {
                0: 0.7, 1: 0.6, 2: 0.6, 3: 0.6, 4: 0.6, 5: 0.7,  # Night hours
                6: 0.8, 7: 0.9, 8: 1.0, 9: 1.1, 10: 1.1, 11: 1.1,  # Morning
                12: 1.0, 13: 1.0, 14: 1.0, 15: 1.0, 16: 1.0, 17: 1.0,  # Afternoon
                18: 1.2, 19: 1.3, 20: 1.2, 21: 1.1, 22: 1.0, 23: 0.8   # Evening
            }
            
            # Apply gentle adjustments to maintain realistic daily patterns
            for hour, factor in hour_factors.items():
                hour_mask = forecast_df['hour'] == hour
                if hour_mask.sum() > 0:
                    adjustment_factor = 0.9 + 0.2 * factor  # Gentle adjustment (0.9 to 1.1)
                    forecast_df.loc[hour_mask, 'demand'] *= adjustment_factor
            
            return forecast_df
            
        except Exception as e:
            logger.warning(f"Error adjusting daily patterns: {e}")
            return forecast_df

    def _finalize_stl_forecast(self, forecast_df):
        """Final processing and cleanup of STL forecast"""
        try:
            # Remove intermediate columns
            columns_to_keep = ['ds', 'demand', 'financial_year', 'financial_month', 'hour', 
                              'dayofweek', 'month', 'year', 'day', 'is_weekend', 
                              'is_holiday', 'is_special_day']
            
            columns_to_keep = [col for col in columns_to_keep if col in forecast_df.columns]
            forecast_df = forecast_df[columns_to_keep].copy()
            
            # Final processing
            forecast_df['demand'] = forecast_df['demand'].clip(lower=0)
            forecast_df['demand'] = forecast_df['demand'].round(4)
            
            # Sort by timestamp
            forecast_df = forecast_df.sort_values('ds').reset_index(drop=True)
            
            return forecast_df
            
        except Exception as e:
            logger.error(f"Error finalizing STL forecast: {e}")
            return forecast_df

    def _validate_stl_forecast(self, forecast_df, demand_scenarios, constraints, historical_data):
        """Comprehensive validation of STL forecast"""
        validation = {
            'annual_totals': {},
            'realism_checks': {},
            'pattern_validation': {},
            'general_stats': {},
            'realism_score': 0
        }
        
        try:
            # Annual totals validation
            annual_totals = forecast_df.groupby('financial_year')['demand'].sum()
            
            for _, scenario_row in demand_scenarios.iterrows():
                fy = scenario_row['Financial_Year']
                target = scenario_row['Total_Demand']
                
                if fy in annual_totals.index:
                    actual = annual_totals[fy]
                    diff_percent = abs(target - actual) / target * 100 if target > 0 else 0
                    validation['annual_totals'][f'FY{fy}'] = {
                        'target': target,
                        'actual': actual,
                        'difference_percent': diff_percent
                    }
            
            # Realism checks
            historical_stats = {
                'mean': historical_data['demand'].mean(),
                'std': historical_data['demand'].std(),
                'max': historical_data['demand'].max(),
                'min': historical_data['demand'].min()
            }
            
            forecast_stats = {
                'mean': forecast_df['demand'].mean(),
                'std': forecast_df['demand'].std(),
                'max': forecast_df['demand'].max(),
                'min': forecast_df['demand'].min()
            }
            
            validation['realism_checks'] = {
                'mean_ratio': forecast_stats['mean'] / historical_stats['mean'] if historical_stats['mean'] > 0 else 1,
                'std_ratio': forecast_stats['std'] / historical_stats['std'] if historical_stats['std'] > 0 else 1,
                'max_ratio': forecast_stats['max'] / historical_stats['max'] if historical_stats['max'] > 0 else 1,
                'min_ratio': forecast_stats['min'] / historical_stats['min'] if historical_stats['min'] > 0 else 1
            }
            
            # Calculate realism score (0-1, higher is better)
            realism_factors = []
            
            # Mean should be within reasonable range
            mean_ratio = validation['realism_checks']['mean_ratio']
            realism_factors.append(max(0, 1 - abs(mean_ratio - 1)))
            
            # Standard deviation should be similar
            std_ratio = validation['realism_checks']['std_ratio']
            realism_factors.append(max(0, 1 - abs(std_ratio - 1) * 0.5))
            
            # Check for negative values
            negative_count = (forecast_df['demand'] < 0).sum()
            realism_factors.append(1 - (negative_count / len(forecast_df)))
            
            validation['realism_score'] = np.mean(realism_factors)
            
            # General statistics
            validation['general_stats'] = {
                'total_hours': len(forecast_df),
                'peak_demand': forecast_df['demand'].max(),
                'min_demand': forecast_df['demand'].min(),
                'avg_demand': forecast_df['demand'].mean(),
                'overall_load_factor': forecast_df['demand'].mean() / forecast_df['demand'].max() if forecast_df['demand'].max() > 0 else 0,
                'negative_values': int(negative_count),
                'zero_values': int((forecast_df['demand'] == 0).sum())
            }
            
        except Exception as e:
            logger.error(f"Error in STL forecast validation: {e}")
            validation['error'] = str(e)
        
        return validation

    # END OF OPTIMIZED STL SECTION

    def _apply_base_profiles(self, forecast_df, profiles, demand_scenarios):
        """Apply base year profiles to forecast with annual scaling"""
        try:
            # Merge profiles
            forecast_df = forecast_df.merge(
                profiles, 
                on=['financial_month', 'is_special_day', 'hour'], 
                how='left'
            )
            
            # Fill missing fractions with average
            avg_fraction = profiles['fraction'].mean()
            forecast_df['fraction'] = forecast_df['fraction'].fillna(avg_fraction)
            
            # Initialize demand with profiles
            forecast_df['demand'] = forecast_df['fraction'] * avg_fraction * 1000  # Base scaling
            
            # Scale to annual targets
            if not demand_scenarios.empty:
                forecast_df = self._scale_to_annual_targets(forecast_df, demand_scenarios)
            
            return forecast_df
            
        except Exception as e:
            logger.error(f"Error applying base profiles: {e}")
            raise
    
    def _scale_to_annual_targets(self, forecast_df, demand_scenarios):
        """Scale forecast to match annual demand targets"""
        try:
            for _, scenario_row in demand_scenarios.iterrows():
                fy = scenario_row['Financial_Year']
                target_annual = scenario_row['Total_Demand']
                
                # Filter forecast for this financial year
                fy_mask = forecast_df['financial_year'] == fy
                
                if fy_mask.sum() == 0:
                    continue
                
                # Calculate current annual total
                current_annual = forecast_df.loc[fy_mask, 'demand'].sum()
                
                if current_annual > 0:
                    # Scale to target
                    scale_factor = target_annual / current_annual
                    forecast_df.loc[fy_mask, 'demand'] *= scale_factor
            
            return forecast_df
            
        except Exception as e:
            logger.error(f"Error scaling to annual targets: {e}")
            raise
    
    def _generate_future_dates(self, start_fy, end_fy, frequency='hourly'):
        """Generate future datetime range for financial years"""
        try:
            # Convert financial years to calendar dates
            start_date = f"{start_fy-1}-04-01"  # April 1st of previous calendar year
            end_date = f"{end_fy}-03-31 23:00"  # March 31st 23:00 of end calendar year
            
            # Set frequency
            freq_map = {
                'hourly': 'H',
                '15min': '15T',
                '30min': '30T',
                'daily': 'D'
            }
            
            freq = freq_map.get(frequency, 'H')
            
            # Generate date range
            dates = pd.date_range(start=start_date, end=end_date, freq=freq)
            
            logger.info(f"Generated {len(dates)} timestamps from FY{start_fy} to FY{end_fy}")
            return dates
            
        except Exception as e:
            logger.error(f"Error generating future dates: {e}")
            raise
    
    def _apply_constraints(self, forecast_df, constraints, demand_scenarios, historical_data):
        """Apply constraints including calculated ones"""
        try:
            modified_df = forecast_df.copy()
            
            # Determine which constraints to use
            monthly_peaks_data = constraints.get('monthly_peaks')
            monthly_lf_data = constraints.get('monthly_load_factors')
            calculated_peaks = constraints.get('calculated_monthly_peaks')
            calculated_lf = constraints.get('calculated_load_factors')
            
            # Use calculated constraints if template constraints are not available
            if monthly_peaks_data is None and calculated_peaks is not None:
                monthly_peaks_data = calculated_peaks
                logger.info("Using calculated monthly peaks for constraints")
            
            if monthly_lf_data is None and calculated_lf is not None:
                monthly_lf_data = calculated_lf
                logger.info("Using calculated load factors for constraints")
            
            # Apply monthly share constraints (dynamic monthly peaks)
            if calculated_peaks is not None:
                modified_df = self._apply_monthly_share_constraints(
                    modified_df, calculated_peaks, demand_scenarios
                )
            
            # Apply load factor constraints
            if monthly_lf_data is not None:
                modified_df = self._apply_load_factor_constraints(
                    modified_df, monthly_lf_data
                )
            
            # Re-scale to annual targets after constraint application
            if not demand_scenarios.empty:
                modified_df = self._scale_to_annual_targets(modified_df, demand_scenarios)
            
            return modified_df
            
        except Exception as e:
            logger.error(f"Error applying constraints: {e}")
            return forecast_df  # Return original if constraints fail
    
    def _apply_monthly_share_constraints(self, forecast_df, monthly_shares_data, demand_scenarios):
        """Apply monthly share constraints based on calculated historical patterns"""
        try:
            # Month name to number mapping for financial year
            month_map = {
                'Apr': 1, 'May': 2, 'Jun': 3, 'Jul': 4, 'Aug': 5, 'Sep': 6,
                'Oct': 7, 'Nov': 8, 'Dec': 9, 'Jan': 10, 'Feb': 11, 'Mar': 12
            }
            
            # Get monthly shares
            if monthly_shares_data.empty:
                return forecast_df
            
            shares_row = monthly_shares_data.iloc[0]  # Use first (average) row
            
            # Apply constraints for each financial year and month
            for _, scenario_row in demand_scenarios.iterrows():
                fy = scenario_row['Financial_Year']
                annual_target = scenario_row['Total_Demand']
                
                for month_name, financial_month in month_map.items():
                    if month_name not in shares_row:
                        continue
                    
                    monthly_share = shares_row[month_name]
                    if pd.isna(monthly_share) or monthly_share <= 0:
                        continue
                    
                    # Calculate target monthly total
                    target_monthly_total = annual_target * monthly_share
                    
                    # Filter forecast for this month and year
                    mask = (forecast_df['financial_year'] == fy) & (forecast_df['financial_month'] == financial_month)
                    
                    if mask.sum() == 0:
                        continue
                    
                    # Current monthly total
                    current_monthly_total = forecast_df.loc[mask, 'demand'].sum()
                    
                    if current_monthly_total > 0:
                        # Scale to target monthly total
                        scale_factor = target_monthly_total / current_monthly_total
                        forecast_df.loc[mask, 'demand'] *= scale_factor
            
            return forecast_df
            
        except Exception as e:
            logger.error(f"Error applying monthly share constraints: {e}")
            return forecast_df
    
    def _apply_load_factor_constraints(self, forecast_df, load_factors_data):
        """Apply monthly load factor constraints"""
        try:
            # Month name to number mapping
            month_map = {
                'Apr': 1, 'May': 2, 'Jun': 3, 'Jul': 4, 'Aug': 5, 'Sep': 6,
                'Oct': 7, 'Nov': 8, 'Dec': 9, 'Jan': 10, 'Feb': 11, 'Mar': 12
            }
            
            if load_factors_data.empty:
                return forecast_df
            
            lf_row = load_factors_data.iloc[0]  # Use first (average) row
            
            # Apply load factor constraints for each financial year
            for fy in forecast_df['financial_year'].unique():
                for month_name, financial_month in month_map.items():
                    if month_name not in lf_row:
                        continue
                    
                    target_lf = lf_row[month_name]
                    if pd.isna(target_lf) or target_lf <= 0 or target_lf > 1:
                        continue
                    
                    # Filter data for this month and year
                    mask = (forecast_df['financial_year'] == fy) & (forecast_df['financial_month'] == financial_month)
                    
                    if mask.sum() == 0:
                        continue
                    
                    month_data = forecast_df.loc[mask, 'demand']
                    if month_data.empty:
                        continue
                    
                    # Calculate current load factor
                    current_avg = month_data.mean()
                    current_peak = month_data.max()
                    
                    if current_peak <= 0:
                        continue
                    
                    current_lf = current_avg / current_peak
                    
                    # Adjust if needed (only if significantly different)
                    if abs(current_lf - target_lf) > 0.05:  # 5% tolerance
                        # Calculate required average to achieve target load factor
                        target_avg = target_lf * current_peak
                        
                        # Scale demands to achieve target average
                        if current_avg > 0:
                            scale_factor = target_avg / current_avg
                            forecast_df.loc[mask, 'demand'] *= scale_factor
            
            return forecast_df
            
        except Exception as e:
            logger.error(f"Error applying load factor constraints: {e}")
            return forecast_df
    
    def _validate_forecast(self, forecast_df, demand_scenarios, constraints=None):
        """Validate forecast against targets and constraints"""
        validation = {
            'annual_totals': {},
            'monthly_validation': {},
            'general_stats': {}
        }
        
        try:
            # Annual totals validation
            annual_totals = forecast_df.groupby('financial_year')['demand'].sum()
            
            for _, scenario_row in demand_scenarios.iterrows():
                fy = scenario_row['Financial_Year']
                target = scenario_row['Total_Demand']
                
                if fy in annual_totals.index:
                    actual = annual_totals[fy]
                    diff_percent = abs(target - actual) / target * 100 if target > 0 else 0
                    validation['annual_totals'][f'FY{fy}'] = {
                        'target': target,
                        'actual': actual,
                        'difference_percent': diff_percent
                    }
            
            # Monthly validation
            monthly_stats = forecast_df.groupby(['financial_year', 'financial_month']).agg({
                'demand': ['sum', 'max', 'mean']
            }).round(2)
            
            # General statistics
            validation['general_stats'] = {
                'total_hours': len(forecast_df),
                'peak_demand': forecast_df['demand'].max(),
                'min_demand': forecast_df['demand'].min(),
                'avg_demand': forecast_df['demand'].mean(),
                'overall_load_factor': forecast_df['demand'].mean() / forecast_df['demand'].max() if forecast_df['demand'].max() > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error in forecast validation: {e}")
            validation['error'] = str(e)
        
        return validation
        
    def save_forecast(self, forecast_results, profile_id=None):
        """
        Save forecast results to CSV file with format
        Output columns: datetime, Demand (kW), Date, Time, Fiscal_Year, Year
        """
        try:
            if not profile_id:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                method = forecast_results.get('method', 'unknown')
                profile_id = f"{method}_{timestamp}"
            
            # Get forecast data
            forecast_df = forecast_results['forecast'].copy()
            
            # Ensure we have the required columns
            if 'ds' not in forecast_df.columns or 'demand' not in forecast_df.columns:
                raise ValueError("Forecast data must contain 'ds' and 'demand' columns")
            
            # Create output dataframe with required format
            output_df = pd.DataFrame()
            
            # Convert demand to kW (assuming input is in kW, but ensure consistency)
            # If demand is in MW, multiply by 1000; if in GW, multiply by 1,000,000
            demand_values = forecast_df['demand'].copy()
            
            # Create output columns in the specified order
            output_df['datetime'] = pd.to_datetime(forecast_df['ds'])
            output_df['Demand (kW)'] = demand_values.round(2)
            
            # Extract date and time components
            output_df['Date'] = output_df['datetime'].dt.date
            output_df['Time'] = output_df['datetime'].dt.time
            
            # Add financial year and calendar year
            if 'financial_year' in forecast_df.columns:
                output_df['Fiscal_Year'] = forecast_df['financial_year']
            else:
                # Calculate financial year from datetime (April to March)
                output_df['Fiscal_Year'] = np.where(
                    output_df['datetime'].dt.month >= 4,
                    output_df['datetime'].dt.year + 1,
                    output_df['datetime'].dt.year
                )
            
            output_df['Year'] = output_df['datetime'].dt.year
            
            # Add hour column for reference (useful for analysis)
            if 'hour' in forecast_df.columns:
                output_df['Hour'] = forecast_df['hour']
            else:
                output_df['Hour'] = output_df['datetime'].dt.hour
            
            # Sort by datetime to ensure chronological order
            output_df = output_df.sort_values('datetime').reset_index(drop=True)
            
            # Save to CSV with the specified column order
            csv_path = self.results_path / f"{profile_id}.csv"
            output_df.to_csv(csv_path, index=False)
            
            # Create summary statistics for metadata
            summary_stats = {
                'total_records': len(output_df),
                'date_range': {
                    'start': output_df['datetime'].min().isoformat(),
                    'end': output_df['datetime'].max().isoformat()
                },
                'demand_stats_kW': {
                    'min': float(output_df['Demand (kW)'].min()),
                    'max': float(output_df['Demand (kW)'].max()),
                    'mean': float(output_df['Demand (kW)'].mean()),
                    'std': float(output_df['Demand (kW)'].std())
                },
                'fiscal_years': {
                    'start': int(output_df['Fiscal_Year'].min()),
                    'end': int(output_df['Fiscal_Year'].max()),
                    'count': len(output_df['Fiscal_Year'].unique())
                },
                'load_factor': float(output_df['Demand (kW)'].mean() / output_df['Demand (kW)'].max()) if output_df['Demand (kW)'].max() > 0 else 0
            }
            
            # Save metadata
            metadata = {
                'profile_id': profile_id,
                'method': forecast_results.get('method'),
                'generated_at': forecast_results.get('metadata', {}).get('generated_at'),
                'start_fy': int(output_df['Fiscal_Year'].min()),
                'end_fy': int(output_df['Fiscal_Year'].max()),
                'output_format': {
                    'columns': list(output_df.columns),
                    'demand_unit': 'kW',
                    'timestamp_format': 'datetime',
                    'total_hours': len(output_df)
                },
                'summary_statistics': summary_stats,
                'validation': forecast_results.get('validation'),
                'file_info': get_file_info(str(csv_path))
            }
            
            metadata_path = self.config_path / f"{profile_id}_metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
            
            logger.info(f"Saved forecast to {csv_path} with {len(output_df)} records")
            logger.info(f"Output format: {list(output_df.columns)}")
            logger.info(f"Demand range: {summary_stats['demand_stats_kW']['min']:.1f} - {summary_stats['demand_stats_kW']['max']:.1f} kW")
            
            return {
                'profile_id': profile_id,
                'csv_path': str(csv_path),
                'metadata_path': str(metadata_path),
                'file_size': metadata['file_info']['size_mb'],
                'summary_stats': summary_stats
            }
            
        except Exception as e:
            logger.error(f"Error saving forecast: {e}")
            raise

    def get_saved_profiles(self):
        """Get list of saved load profiles"""
        try:
            profiles = []
            
            if not self.results_path.exists():
                return profiles
            
            for csv_file in self.results_path.glob("*.csv"):
                profile_id = csv_file.stem
                metadata_file = self.config_path / f"{profile_id}_metadata.json"
                
                profile_info = {
                    'profile_id': profile_id,
                    'csv_path': str(csv_file),
                    'file_info': get_file_info(str(csv_file))
                }
                
                # Load metadata if available
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        profile_info.update(metadata)
                    except (json.JSONDecodeError, Exception) as e:
                        logger.warning(f"Could not load or parse metadata for {profile_id}: {e}")
                        profile_info['error'] = 'Invalid metadata'
                
                profiles.append(profile_info)
            
            # Sort by creation time (newest first)
            profiles.sort(key=lambda x: x.get('generated_at', ''), reverse=True)
            
            return profiles
            
        except Exception as e:
            logger.error(f"Error getting saved profiles: {e}")
            return []

    def get_profile_data(self, profile_id):
        """Get profile data with proper column handling"""
        try:
            # Find profile file
            csv_path = self.results_path / f"{profile_id}.csv"
            
            if not csv_path.exists():
                raise FileNotFoundError(f"Profile not found: {profile_id}")
            
            # Load profile data
            profile_df = pd.read_csv(csv_path)
            
            # Load metadata if available
            metadata_path = self.config_path / f"{profile_id}_metadata.json"
            metadata = {}
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
            
            # Determine demand column (handle both old and new formats)
            demand_col = None
            if 'Demand (kW)' in profile_df.columns:
                demand_col = 'Demand (kW)'
            elif 'demand' in profile_df.columns:
                demand_col = 'demand'
            else:
                # Look for any column with 'demand' in the name
                demand_cols = [col for col in profile_df.columns if 'demand' in col.lower()]
                if demand_cols:
                    demand_col = demand_cols[0]
            
            if not demand_col:
                raise ValueError(f"No demand column found in profile {profile_id}")
            
            # Prepare response data
            profile_data = {
                'profile_id': profile_id,
                'file_info': get_file_info(str(csv_path)),
                'data_summary': {
                    'total_records': len(profile_df),
                    'columns': list(profile_df.columns),
                    'demand_column': demand_col
                },
                'metadata': metadata
            }
            
            # Add date range if datetime column exists
            datetime_col = None
            if 'datetime' in profile_df.columns:
                datetime_col = 'datetime'
            elif 'ds' in profile_df.columns:
                datetime_col = 'ds'
            
            if datetime_col:
                profile_data['data_summary']['date_range'] = {
                    'start': profile_df[datetime_col].min(),
                    'end': profile_df[datetime_col].max()
                }
            
            # Add demand statistics
            if demand_col:
                profile_data['data_summary']['demand_stats'] = {
                    'min': float(profile_df[demand_col].min()),
                    'max': float(profile_df[demand_col].max()),
                    'mean': float(profile_df[demand_col].mean()),
                    'std': float(profile_df[demand_col].std())
                }
            
            # Optional: Include sample data (first 100 records)
            sample_size = min(100, len(profile_df))
            profile_data['sample_data'] = profile_df.head(sample_size).to_dict('records')
            
            return profile_data
            
        except Exception as e:
            logger.error(f"Error getting profile data for {profile_id}: {e}")
            raise