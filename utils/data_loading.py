"""
Enhanced data loading utilities for the KSEB Energy Futures Platform
"""
import pandas as pd
import numpy as np
import logging
import os
from datetime import datetime

from utils.helpers import extract_table, extract_tables_by_markers
from utils.constants import REQUIRED_SHEETS, VALIDATION_RULES, ERROR_MESSAGES

logger = logging.getLogger(__name__)

def validate_input_file(file_path):
    """
    Validate input demand Excel file structure and content
    
    Args:
        file_path (str): Path to the Excel file
        
    Returns:
        dict: Validation result with status and details
    """
    validation_result = {
        'valid': False,
        'errors': [],
        'warnings': [],
        'sheets_found': [],
        'required_sheets_missing': [],
        'file_info': {}
    }
    
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            validation_result['errors'].append(f"File not found: {file_path}")
            return validation_result
        
        # Get file info
        try:
            file_stat = os.stat(file_path)
            validation_result['file_info'] = {
                'size_bytes': file_stat.st_size,
                'size_mb': round(file_stat.st_size / (1024 * 1024), 2),
                'modified': datetime.fromtimestamp(file_stat.st_mtime).isoformat()
            }
        except Exception as file_error:
            validation_result['warnings'].append(f"Could not get file info: {file_error}")
        
        # Try to read Excel file
        try:
            excel_file = pd.ExcelFile(file_path)
            validation_result['sheets_found'] = excel_file.sheet_names
            logger.debug(f"Found sheets in {file_path}: {excel_file.sheet_names}")
        except Exception as excel_error:
            validation_result['errors'].append(f"Cannot read Excel file: {excel_error}")
            return validation_result
        
        # Check for required sheets
        required_main_sheet = REQUIRED_SHEETS['MAIN']  # 'main'
        if required_main_sheet not in excel_file.sheet_names:
            validation_result['required_sheets_missing'].append(required_main_sheet)
            validation_result['errors'].append(f"Required sheet '{required_main_sheet}' not found")
        
        # Validate main sheet structure if it exists
        if required_main_sheet in excel_file.sheet_names:
            try:
                main_sheet = pd.read_excel(file_path, sheet_name=required_main_sheet)
                main_validation = validate_main_sheet(main_sheet)
                validation_result['main_sheet_validation'] = main_validation
                
                if not main_validation['valid']:
                    validation_result['errors'].extend(main_validation['errors'])
                    validation_result['warnings'].extend(main_validation.get('warnings', []))
                
            except Exception as main_error:
                validation_result['errors'].append(f"Error validating main sheet: {main_error}")
        
        # Check for Economic Indicators sheet (optional)
        economic_sheet = REQUIRED_SHEETS['ECONOMIC_INDICATORS']  # 'Economic_Indicators'
        if economic_sheet in excel_file.sheet_names:
            try:
                economic_data = pd.read_excel(file_path, sheet_name=economic_sheet)
                economic_validation = validate_economic_indicators_sheet(economic_data)
                validation_result['economic_indicators_validation'] = economic_validation
                
                if not economic_validation['valid']:
                    validation_result['warnings'].extend(economic_validation.get('warnings', []))
                
            except Exception as econ_error:
                validation_result['warnings'].append(f"Error validating Economic Indicators sheet: {econ_error}")
        
        # Overall validation result
        validation_result['valid'] = len(validation_result['errors']) == 0
        
        # Close Excel file
        try:
            excel_file.close()
        except:
            pass
        
        logger.info(f"File validation {'passed' if validation_result['valid'] else 'failed'} for {file_path}")
        return validation_result
        
    except Exception as e:
        logger.exception(f"Error validating input file {file_path}: {e}")
        validation_result['errors'].append(f"Validation error: {str(e)}")
        return validation_result

def validate_main_sheet(main_sheet_df):
    """
    Validate the main sheet structure and content
    
    Args:
        main_sheet_df (pd.DataFrame): Main sheet data
        
    Returns:
        dict: Validation result
    """
    validation = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'settings_found': False,
        'sectors_found': False,
        'parameters_found': {}
    }
    
    try:
        # Look for settings table marked with "~"
        settings_markers = extract_tables_by_markers(main_sheet_df, "~")
        
        if 'Settings' not in settings_markers:
            validation['errors'].append("Settings table (marked with ~Settings) not found in main sheet")
        else:
            settings_df = settings_markers['Settings']
            validation['settings_found'] = True
            
            # Validate settings structure
            if 'Parameters' not in settings_df.columns or 'Inputs' not in settings_df.columns:
                validation['errors'].append("Settings table must have 'Parameters' and 'Inputs' columns")
            else:
                # Check for required parameters
                required_params = ['Start_Year', 'End_Year']
                parameters = settings_df['Parameters'].tolist()
                
                for param in required_params:
                    if param not in parameters:
                        validation['errors'].append(f"Required parameter '{param}' not found in Settings")
                    else:
                        # Get parameter value
                        param_row = settings_df[settings_df['Parameters'] == param]
                        if not param_row.empty:
                            param_value = param_row['Inputs'].iloc[0]
                            validation['parameters_found'][param] = param_value
                            
                            # Validate year parameters
                            if param.endswith('_Year'):
                                try:
                                    year_value = int(param_value)
                                    if year_value < VALIDATION_RULES['MIN_YEAR'] or year_value > VALIDATION_RULES['MAX_YEAR']:
                                        validation['warnings'].append(f"{param} value {year_value} is outside typical range")
                                except (ValueError, TypeError):
                                    validation['errors'].append(f"{param} must be a valid year (integer)")
        
        # Look for consumption sectors
        if 'Consumption_Sectors' in settings_markers:
            sectors_df = settings_markers['Consumption_Sectors']
            validation['sectors_found'] = True
            
            if 'Sector_Name' not in sectors_df.columns:
                validation['errors'].append("Consumption_Sectors table must have 'Sector_Name' column")
            else:
                sectors = sectors_df['Sector_Name'].dropna().tolist()
                if len(sectors) == 0:
                    validation['errors'].append("No sectors found in Consumption_Sectors table")
                else:
                    validation['sectors_list'] = sectors
                    logger.debug(f"Found {len(sectors)} sectors: {sectors}")
        else:
            validation['errors'].append("Consumption_Sectors table not found in main sheet")
        
        # Check for Econometric Parameters (optional)
        if 'Econometric_Parameters' in settings_markers:
            validation['econometric_parameters_found'] = True
            validation['warnings'].append("Econometric parameters configuration found")
        
        validation['valid'] = len(validation['errors']) == 0
        
    except Exception as e:
        logger.exception(f"Error validating main sheet: {e}")
        validation['errors'].append(f"Main sheet validation error: {str(e)}")
        validation['valid'] = False
    
    return validation

def validate_economic_indicators_sheet(economic_df):
    """
    Validate Economic Indicators sheet structure
    
    Args:
        economic_df (pd.DataFrame): Economic indicators data
        
    Returns:
        dict: Validation result
    """
    validation = {
        'valid': True,
        'warnings': [],
        'columns_found': [],
        'year_column_found': False,
        'data_rows': 0
    }
    
    try:
        validation['columns_found'] = economic_df.columns.tolist()
        validation['data_rows'] = len(economic_df)
        
        # Check for Year column
        if 'Year' in economic_df.columns:
            validation['year_column_found'] = True
            
            # Validate year data
            year_data = economic_df['Year'].dropna()
            if len(year_data) == 0:
                validation['warnings'].append("No valid year data found in Economic Indicators")
            else:
                try:
                    years = pd.to_numeric(year_data, errors='coerce').dropna()
                    if len(years) != len(year_data):
                        validation['warnings'].append("Some year values in Economic Indicators are not numeric")
                    
                    if len(years) > 0:
                        year_range = f"{int(years.min())}-{int(years.max())}"
                        validation['year_range'] = year_range
                        logger.debug(f"Economic indicators year range: {year_range}")
                        
                except Exception as year_error:
                    validation['warnings'].append(f"Error processing year data: {year_error}")
        else:
            validation['warnings'].append("No 'Year' column found in Economic Indicators - will use constant values")
        
        # Check for indicator columns
        indicator_columns = [col for col in economic_df.columns if col != 'Year']
        if len(indicator_columns) == 0:
            validation['warnings'].append("No economic indicator columns found")
        else:
            validation['indicator_columns'] = indicator_columns
            
            # Check for missing data
            for col in indicator_columns:
                missing_count = economic_df[col].isna().sum()
                if missing_count > 0:
                    validation['warnings'].append(f"Column '{col}' has {missing_count} missing values")
        
    except Exception as e:
        logger.exception(f"Error validating economic indicators: {e}")
        validation['warnings'].append(f"Economic indicators validation error: {str(e)}")
    
    return validation

def input_demand_data(demand_input_file_path):
    """
   input demand data processing with comprehensive error handling
    
    Args:
        demand_input_file_path (str): Path to the input Excel file
        
    Returns:
        tuple: (sectors, missing_sectors, param_dict, sector_data, aggregated_ele)
    """
    logger.info(f"Processing input demand file: {demand_input_file_path}")
    
    try:
        # First, validate the input file
        file_validation = validate_input_file(demand_input_file_path)
        if not file_validation['valid']:
            error_msg = "Input file validation failed: " + "; ".join(file_validation['errors'])
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Log warnings if any
        for warning in file_validation.get('warnings', []):
            logger.warning(f"Input file warning: {warning}")
        
        # Read main sheet
        main_settings = pd.read_excel(demand_input_file_path, sheet_name='main')
        main_settings_parameters = extract_tables_by_markers(main_settings, "~")
        
        # Extract settings
        if 'Settings' not in main_settings_parameters:
            raise ValueError("Settings table not found in main sheet")
        
        settings = main_settings_parameters.get('Settings')
        param_dict = dict(zip(settings['Parameters'], settings['Inputs']))
        
        # Process and validate year parameters
        try:
            start_year = int(param_dict.get('Start_Year', VALIDATION_RULES.get('MIN_YEAR', 2006)))
            end_year = int(param_dict.get('End_Year', 2037))
            
            # Validate year range
            if start_year >= end_year:
                logger.warning(f"Start year ({start_year}) >= End year ({end_year}), adjusting")
                if start_year == end_year:
                    end_year = start_year + 1
                else:
                    start_year, end_year = end_year, start_year
            
            param_dict['Start_Year'] = start_year
            param_dict['End_Year'] = end_year
            
            logger.info(f"Extracted parameters: Start_Year={start_year}, End_Year={end_year}")
            
        except (ValueError, TypeError) as year_error:
            logger.warning(f"Error processing year parameters: {year_error}")
            # Set defaults
            param_dict['Start_Year'] = 2006
            param_dict['End_Year'] = 2037
            logger.info("Using default years: Start_Year=2006, End_Year=2037")
        
        # Get econometric parameters setting
        econometric_parameters = param_dict.get('Econometric_Parameters', 'No')
        
        # Extract sectors
        if 'Consumption_Sectors' not in main_settings_parameters:
            raise ValueError("Consumption_Sectors table not found in main sheet")
        
        sectors_df = main_settings_parameters.get('Consumption_Sectors')
        if 'Sector_Name' not in sectors_df.columns:
            raise ValueError("Sector_Name column not found in Consumption_Sectors table")
        
        sectors = sectors_df['Sector_Name'].dropna().tolist()
        if not sectors:
            raise ValueError("No sectors found in Consumption_Sectors table")
        
        logger.info(f"Found {len(sectors)} sectors: {sectors}")
        
        # Initialize data structures
        sector_data = {}
        missing_sectors = []
        aggregated_ele = pd.DataFrame()
        
        # Load Economic Indicators if enabled
        economic_indicators = None
        if econometric_parameters == 'Yes':
            try:
                economic_indicators = pd.read_excel(demand_input_file_path, sheet_name='Economic_Indicators')
                logger.info(f"Loaded Economic Indicators with columns: {economic_indicators.columns.tolist()}")
                
                # Validate economic indicators
                econ_validation = validate_economic_indicators_sheet(economic_indicators)
                for warning in econ_validation.get('warnings', []):
                    logger.warning(f"Economic indicators: {warning}")
                    
            except Exception as econ_error:
                logger.warning(f"Failed to load Economic Indicators: {econ_error}")
                econometric_parameters = 'No'  # Disable if loading fails
        
        # Process each sector
        for sector in sectors:
            try:
                # Load sector data
                sector_data[sector] = pd.read_excel(demand_input_file_path, sheet_name=sector)
                logger.debug(f"Loaded sector {sector} with columns: {sector_data[sector].columns.tolist()}")
                
                # Validate sector data
                sector_validation = validate_sector_data(sector_data[sector], sector)
                if not sector_validation['valid']:
                    logger.warning(f"Sector {sector} validation issues: {sector_validation['warnings']}")
                
                # Process economic parameters if enabled
                if econometric_parameters == 'Yes' and economic_indicators is not None:
                    try:
                        # Get econometric parameters for this sector
                        econometric_params_sector = None
                        if 'Econometric_Parameters' in main_settings_parameters:
                            econ_params_df = main_settings_parameters['Econometric_Parameters']
                            if sector in econ_params_df.columns:
                                econometric_params_sector = econ_params_df[sector].dropna().tolist()
                                logger.debug(f"Economic parameters for {sector}: {econometric_params_sector}")
                        
                        if econometric_params_sector:
                            # Apply economic indicators to sector data
                            apply_economic_indicators_to_sector(
                                sector_data[sector], 
                                economic_indicators, 
                                econometric_params_sector,
                                sector
                            )
                    
                    except Exception as econ_apply_error:
                        logger.warning(f"Error applying economic parameters to {sector}: {econ_apply_error}")
                
                # Aggregate electricity data
                if 'Year' in sector_data[sector].columns and 'Electricity' in sector_data[sector].columns:
                    sector_electricity = sector_data[sector][['Year', 'Electricity']].copy()
                    
                    # Clean and validate electricity data
                    sector_electricity = clean_electricity_data(sector_electricity, sector)
                    
                    if aggregated_ele.empty:
                        aggregated_ele = sector_electricity.copy()
                        aggregated_ele.rename(columns={'Electricity': sector}, inplace=True)
                    else:
                        # Use outer join to include all years
                        aggregated_ele = pd.merge(
                            aggregated_ele,
                            sector_electricity.rename(columns={'Electricity': sector}),
                            on='Year',
                            how='outer'
                        )
                else:
                    logger.warning(f"Sector {sector} missing Year or Electricity columns")
                    missing_sectors.append(sector)
            
            except Exception as sector_error:
                logger.error(f"Error processing sector {sector}: {sector_error}")
                missing_sectors.append(sector)
        
        # Calculate total electricity demand
        if not aggregated_ele.empty and 'Year' in aggregated_ele.columns:
            try:
                # Fill NaN values with 0 for calculation
                calc_df = aggregated_ele.fillna(0)
                data_columns = [col for col in calc_df.columns if col != 'Year']
                
                if data_columns:
                    aggregated_ele['Total'] = calc_df[data_columns].sum(axis=1)
                    logger.info(f"Calculated Total column for aggregated data with {len(data_columns)} sectors")
            
            except Exception as total_error:
                logger.warning(f"Error calculating total electricity: {total_error}")
        
        # Final validation
        successful_sectors = [s for s in sectors if s not in missing_sectors]
        logger.info(f"Successfully processed {len(successful_sectors)} sectors, {len(missing_sectors)} failed")
        
        return sectors, missing_sectors, param_dict, sector_data, aggregated_ele
        
    except Exception as e:
        logger.exception(f"Error processing input file {demand_input_file_path}: {e}")
        # Return empty structures to prevent application crash
        return [], [], {}, {}, pd.DataFrame()

def validate_sector_data(sector_df, sector_name):
    """
    Validate individual sector data
    
    Args:
        sector_df (pd.DataFrame): Sector data
        sector_name (str): Name of the sector
        
    Returns:
        dict: Validation result
    """
    validation = {
        'valid': True,
        'warnings': [],
        'has_year': False,
        'has_electricity': False,
        'data_range': None,
        'missing_data_points': 0
    }
    
    try:
        # Check for required columns
        if 'Year' not in sector_df.columns:
            validation['warnings'].append(f"Sector {sector_name}: 'Year' column missing")
        else:
            validation['has_year'] = True
            
            # Validate year data
            year_data = sector_df['Year'].dropna()
            if len(year_data) > 0:
                try:
                    years = pd.to_numeric(year_data, errors='coerce').dropna()
                    if len(years) > 0:
                        validation['data_range'] = {
                            'start': int(years.min()),
                            'end': int(years.max()),
                            'count': len(years)
                        }
                except Exception as year_error:
                    validation['warnings'].append(f"Sector {sector_name}: Invalid year data - {year_error}")
        
        if 'Electricity' not in sector_df.columns:
            validation['warnings'].append(f"Sector {sector_name}: 'Electricity' column missing")
        else:
            validation['has_electricity'] = True
            
            # Check for missing electricity data
            electricity_data = sector_df['Electricity']
            missing_count = electricity_data.isna().sum()
            validation['missing_data_points'] = missing_count
            
            if missing_count > 0:
                validation['warnings'].append(f"Sector {sector_name}: {missing_count} missing electricity values")
            
            # Check for negative values
            if electricity_data.dtype in ['int64', 'float64']:
                negative_count = (electricity_data < 0).sum()
                if negative_count > 0:
                    validation['warnings'].append(f"Sector {sector_name}: {negative_count} negative electricity values")
        
        # Check data quality
        if len(sector_df) < VALIDATION_RULES['MIN_DATA_POINTS']:
            validation['warnings'].append(f"Sector {sector_name}: Only {len(sector_df)} data points (minimum recommended: {VALIDATION_RULES['MIN_DATA_POINTS']})")
        
        validation['valid'] = validation['has_year'] and validation['has_electricity']
        
    except Exception as e:
        logger.exception(f"Error validating sector {sector_name}: {e}")
        validation['warnings'].append(f"Validation error: {str(e)}")
        validation['valid'] = False
    
    return validation

def apply_economic_indicators_to_sector(sector_df, economic_indicators, indicator_list, sector_name):
    """
    Apply economic indicators to sector data
    
    Args:
        sector_df (pd.DataFrame): Sector data (modified in place)
        economic_indicators (pd.DataFrame): Economic indicators data
        indicator_list (list): List of indicators to apply
        sector_name (str): Name of the sector
    """
    try:
        logger.debug(f"Applying economic indicators to {sector_name}: {indicator_list}")
        
        # Check if Economic Indicators has a Year column for mapping
        if 'Year' in economic_indicators.columns:
            # Year-by-year mapping
            for indicator in indicator_list:
                if indicator in economic_indicators.columns:
                    # Create year-to-value mapping
                    year_to_value = dict(zip(economic_indicators['Year'], economic_indicators[indicator]))
                    
                    # Apply mapping to sector data
                    def map_indicator(year):
                        if pd.isna(year):
                            return None
                        try:
                            year_int = int(year)
                            return year_to_value.get(year_int)
                        except (ValueError, TypeError):
                            return None
                    
                    sector_df[indicator] = sector_df['Year'].map(map_indicator)
                    logger.debug(f"Mapped {indicator} values by year for {sector_name}")
                else:
                    logger.warning(f"Indicator {indicator} not found in Economic Indicators for {sector_name}")
        else:
            # No Year column - use constant values (first row or mean)
            logger.debug(f"Economic Indicators has no Year column, using constant values for {sector_name}")
            for indicator in indicator_list:
                if indicator in economic_indicators.columns and not economic_indicators[indicator].empty:
                    # Use first non-null value
                    indicator_values = economic_indicators[indicator].dropna()
                    if not indicator_values.empty:
                        constant_value = indicator_values.iloc[0]
                        sector_df[indicator] = constant_value
                        logger.debug(f"Applied constant value {constant_value} for {indicator} in {sector_name}")
                    else:
                        logger.warning(f"No valid values for indicator {indicator} in {sector_name}")
                else:
                    logger.warning(f"Indicator {indicator} not found or empty in Economic Indicators for {sector_name}")
    
    except Exception as e:
        logger.exception(f"Error applying economic indicators to {sector_name}: {e}")

def clean_electricity_data(electricity_df, sector_name):
    """
    Clean and validate electricity data
    
    Args:
        electricity_df (pd.DataFrame): DataFrame with Year and Electricity columns
        sector_name (str): Name of the sector
        
    Returns:
        pd.DataFrame: Cleaned electricity data
    """
    try:
        cleaned_df = electricity_df.copy()
        
        # Convert Year to numeric
        cleaned_df['Year'] = pd.to_numeric(cleaned_df['Year'], errors='coerce')
        
        # Convert Electricity to numeric
        cleaned_df['Electricity'] = pd.to_numeric(cleaned_df['Electricity'], errors='coerce')
        
        # Remove rows with invalid years
        before_count = len(cleaned_df)
        cleaned_df = cleaned_df.dropna(subset=['Year'])
        after_count = len(cleaned_df)
        
        if before_count != after_count:
            logger.warning(f"Sector {sector_name}: Removed {before_count - after_count} rows with invalid years")
        
        # Handle missing electricity values
        electricity_missing = cleaned_df['Electricity'].isna().sum()
        if electricity_missing > 0:
            logger.warning(f"Sector {sector_name}: {electricity_missing} missing electricity values")
            # Option 1: Fill with 0 (conservative)
            # cleaned_df['Electricity'] = cleaned_df['Electricity'].fillna(0)
            # Option 2: Forward fill or interpolate (more sophisticated)
            cleaned_df['Electricity'] = cleaned_df['Electricity'].interpolate(method='linear')
            cleaned_df['Electricity'] = cleaned_df['Electricity'].fillna(0)  # Fill any remaining NaN
        
        # Handle negative values
        negative_count = (cleaned_df['Electricity'] < 0).sum()
        if negative_count > 0:
            logger.warning(f"Sector {sector_name}: {negative_count} negative electricity values, setting to 0")
            cleaned_df.loc[cleaned_df['Electricity'] < 0, 'Electricity'] = 0
        
        # Sort by year
        cleaned_df = cleaned_df.sort_values('Year').reset_index(drop=True)
        
        # Remove duplicate years (keep last)
        duplicate_years = cleaned_df['Year'].duplicated().sum()
        if duplicate_years > 0:
            logger.warning(f"Sector {sector_name}: {duplicate_years} duplicate years, keeping last values")
            cleaned_df = cleaned_df.drop_duplicates(subset=['Year'], keep='last')
        
        return cleaned_df
        
    except Exception as e:
        logger.exception(f"Error cleaning electricity data for {sector_name}: {e}")
        return electricity_df  # Return original if cleaning fails