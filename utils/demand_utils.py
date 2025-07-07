# """
# Enhanced utility functions for demand projection and visualization modules
# """
# import os
# import json
# import time
# import pandas as pd
# import numpy as np
# import logging
# from datetime import datetime
# from flask import current_app

# from utils.constants import UNIT_FACTORS, VALIDATION_RULES, ERROR_MESSAGES
# from utils.response_utils import handle_exception_response

# logger = logging.getLogger(__name__)

# # ========== Data Handling Utilities ==========


# def handle_nan_values(obj):
#     """
#     Convert NaN and Infinity values to null for JSON serialization
#     """
#     if isinstance(obj, float):
#         if np.isnan(obj) or np.isinf(obj):
#             return None
#     elif isinstance(obj, np.number):
#         if np.isnan(obj) or np.isinf(obj):
#             return None
#         return float(obj)
#     elif isinstance(obj, dict):
#         return {k: handle_nan_values(v) for k, v in obj.items()}
#     elif isinstance(obj, list):
#         return [handle_nan_values(item) for item in obj]
#     elif isinstance(obj, np.ndarray):
#         return handle_nan_values(obj.tolist())
#     elif pd.isna(obj):
#         return None
#     return obj

# def safe_numeric_conversion(value, default=0):
#     """
#     Safely convert value to numeric, handling various edge cases INCLUDING infinity strings
#     """
#     try:
#         if pd.isna(value) or value is None:
#             return default
        
#         if isinstance(value, (int, float)):
#             if np.isnan(value) or np.isinf(value):
#                 return default
#             return float(value)
        
#         # Try to convert string to float
#         if isinstance(value, str):
#             cleaned_value = value.strip().replace(',', '').lower()
            
#             # Check for problematic string values that create infinity
#             if cleaned_value in ['', 'na', 'nan', 'null', 'inf', 'infinity', '-inf', '-infinity']:
#                 return default
                
#             try:
#                 result = float(cleaned_value)
#                 # Double-check the result isn't infinity
#                 if np.isinf(result) or np.isnan(result):
#                     return default
#                 return result
#             except (ValueError, OverflowError):
#                 return default
        
#         result = float(value)
#         if np.isinf(result) or np.isnan(result):
#             return default
#         return result
    
#     except (ValueError, TypeError, OverflowError):
#         logger.debug(f"Could not convert {value} to numeric, using default {default}")
#         return default

# def validate_year_range(start_year, end_year):
#     """
#     Validate and adjust year range
    
#     Args:
#         start_year: Start year
#         end_year: End year
        
#     Returns:
#         tuple: (validated_start_year, validated_end_year, warnings)
#     """
#     warnings = []
    
#     try:
#         start_year = int(safe_numeric_conversion(start_year, VALIDATION_RULES.get('MIN_YEAR', 2006)))
#         end_year = int(safe_numeric_conversion(end_year, 2037))
        
#         # Ensure start year is before end year
#         if start_year >= end_year:
#             warnings.append(f"Start year ({start_year}) >= End year ({end_year}), adjusting")
#             if start_year == end_year:
#                 end_year = start_year + 1
#             else:
#                 start_year, end_year = min(start_year, end_year), max(start_year, end_year)
        
#         # Check reasonable bounds
#         min_year = VALIDATION_RULES.get('MIN_YEAR', 1990)
#         max_year = VALIDATION_RULES.get('MAX_YEAR', 2100)
        
#         if start_year < min_year:
#             warnings.append(f"Start year {start_year} is below minimum {min_year}")
#             start_year = min_year
        
#         if end_year > max_year:
#             warnings.append(f"End year {end_year} is above maximum {max_year}")
#             end_year = max_year
        
#         return start_year, end_year, warnings
        
#     except Exception as e:
#         logger.warning(f"Error validating year range: {e}")
#         return 2006, 2037, [f"Year validation error: {str(e)}"]

# # ========== Project and Path Validation ==========

# def validate_project_path():
#     """
#    project path validation with detailed checking
    
#     Returns:
#         bool: True if valid project is selected
#     """
#     try:
#         project_path = current_app.config.get('CURRENT_PROJECT_PATH')
        
#         if not project_path:
#             logger.debug("No project path configured")
#             return False
        
#         if not os.path.exists(project_path):
#             logger.warning(f"Project path does not exist: {project_path}")
#             # Clear invalid project
#             current_app.config['CURRENT_PROJECT'] = None
#             current_app.config['CURRENT_PROJECT_PATH'] = None
#             return False
        
#         if not os.path.isdir(project_path):
#             logger.warning(f"Project path is not a directory: {project_path}")
#             return False
        
#         # Check for basic project structure
#         required_dirs = ['inputs', 'results']
#         for required_dir in required_dirs:
#             dir_path = os.path.join(project_path, required_dir)
#             if not os.path.exists(dir_path):
#                 logger.warning(f"Required directory missing: {dir_path}")
#                 return False
        
#         return True
        
#     except Exception as e:
#         logger.exception(f"Error validating project path: {e}")
#         return False

# def get_scenario_list(scenarios_path):
#     """
#     Get list of available forecast scenarios with validation
    
#     Args:
#         scenarios_path (str): Path to scenarios directory
        
#     Returns:
#         list: List of valid scenario names
#     """
#     try:
#         if not os.path.exists(scenarios_path):
#             logger.debug(f"Scenarios path does not exist: {scenarios_path}")
#             return []
        
#         scenarios = []
#         for item in os.listdir(scenarios_path):
#             item_path = os.path.join(scenarios_path, item)
            
#             if not os.path.isdir(item_path):
#                 continue
            
#             # Check if directory contains forecast files
#             try:
#                 scenario_files = os.listdir(item_path)
#                 has_forecast_files = any(
#                     f.endswith('.xlsx') and not f.startswith('_') 
#                     for f in scenario_files
#                 )
                
#                 if has_forecast_files:
#                     scenarios.append(item)
#                 else:
#                     logger.debug(f"Scenario directory {item} has no valid forecast files")
                    
#             except (OSError, PermissionError) as dir_error:
#                 logger.warning(f"Cannot access scenario directory {item}: {dir_error}")
        
#         scenarios.sort()
#         logger.debug(f"Found {len(scenarios)} valid scenarios")
#         return scenarios
        
#     except Exception as e:
#         logger.exception(f"Error getting scenario list from {scenarios_path}: {e}")
#         return []

# # ========== Data Loading and Processing ==========

# def get_forecast_data_for_sector(scenario_path, sector, from_year, to_year, unit='kWh'):
#     """
#    forecast data loading with comprehensive error handling
    
#     Args:
#         scenario_path (str): Path to scenario directory
#         sector (str): Sector name
#         from_year (int): Start year
#         to_year (int): End year
#         unit (str): Unit for data conversion
        
#     Returns:
#         pd.DataFrame or None: Forecast data or None if error
#     """
#     logger.debug(f"Loading forecast data for sector '{sector}' from {scenario_path}")
    
#     try:
#         # Validate inputs
#         if not scenario_path or not sector:
#             logger.warning("Invalid scenario path or sector name")
#             return None
        
#         from_year, to_year, year_warnings = validate_year_range(from_year, to_year)
#         for warning in year_warnings:
#             logger.debug(f"Year range validation: {warning}")
        
#         # Construct file path
#         file_path = os.path.join(scenario_path, f"{sector}.xlsx")
        
#         if not os.path.exists(file_path):
#             logger.debug(f"Sector file not found: {file_path}")
#             return None
        
#         # Try to read Results sheet
#         try:
#             df = pd.read_excel(file_path, sheet_name='Results')
#             logger.debug(f"Successfully read Results sheet from {file_path}")
#         except Exception as read_error:
#             logger.warning(f"Could not read Results sheet from {file_path}: {read_error}")
#             return None
        
#         # Validate DataFrame structure
#         if df.empty:
#             logger.warning(f"Empty Results sheet in {file_path}")
#             return None
        
#         if 'Year' not in df.columns:
#             logger.warning(f"'Year' column missing in {file_path}")
#             return None
        
#         # Clean and convert Year column
#         df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
#         df = df.dropna(subset=['Year'])
        
#         if df.empty:
#             logger.warning(f"No valid year data in {file_path}")
#             return None
        
#         # Filter by year range
#         df = df[(df['Year'] >= from_year) & (df['Year'] <= to_year)].copy()
        
#         if df.empty:
#             logger.debug(f"No data in year range {from_year}-{to_year} for {sector}")
#             return None
        
#         # Convert numeric columns and handle unit conversion
#         unit_factor = UNIT_FACTORS.get(unit, 1)
        
#         for col in df.columns:
#             if col != 'Year':
#                 try:
#                     # Convert to numeric
#                     df[col] = pd.to_numeric(df[col], errors='coerce')
                    
#                     # Apply unit conversion if not kWh
#                     if unit != 'kWh' and unit_factor != 1:
#                         df[col] = df[col] / unit_factor
                        
#                 except Exception as col_error:
#                     logger.debug(f"Could not process column {col} in {sector}: {col_error}")
        
#         # Sort by year
#         df = df.sort_values('Year').reset_index(drop=True)
        
#         logger.debug(f"Successfully loaded {len(df)} rows for {sector} ({from_year}-{to_year})")
#         return df
        
#     except Exception as e:
#         logger.exception(f"Error getting forecast data for sector {sector}: {e}")
#         return None

# # ========== T&D Losses Calculation ==========

# def interpolate_td_losses(td_losses_points, years):
#     """
#    T&D losses interpolation with validation
    
#     Args:
#         td_losses_points (list): List of dicts with 'year' and 'loss_percentage' keys
#         years (list): List of years to interpolate for
        
#     Returns:
#         dict: Year to loss percentage mapping
#     """
#     try:
#         if not td_losses_points:
#             logger.debug("No T&D losses points provided, returning zero losses")
#             return {year: 0.0 for year in years}
        
#         if not years:
#             logger.debug("No years provided for T&D losses interpolation")
#             return {}
        
#         # Validate and clean points
#         valid_points = []
#         for point in td_losses_points:
#             try:
#                 year = int(safe_numeric_conversion(point.get('year', 0)))
#                 loss_pct = safe_numeric_conversion(point.get('loss_percentage', 0))
                
#                 # Validate loss percentage is reasonable
#                 if loss_pct < 0:
#                     logger.warning(f"Negative loss percentage {loss_pct} for year {year}, setting to 0")
#                     loss_pct = 0
#                 elif loss_pct > 50:
#                     logger.warning(f"Very high loss percentage {loss_pct} for year {year}")
                
#                 valid_points.append({'year': year, 'loss_percentage': loss_pct})
                
#             except Exception as point_error:
#                 logger.warning(f"Invalid T&D loss point {point}: {point_error}")
        
#         if not valid_points:
#             logger.warning("No valid T&D losses points after validation")
#             return {year: 0.0 for year in years}
        
#         # Sort points by year
#         sorted_points = sorted(valid_points, key=lambda x: x['year'])
#         interpolated = {}
        
#         for year in years:
#             try:
#                 year = int(year)
                
#                 if year <= sorted_points[0]['year']:
#                     # Before first point - use first value
#                     interpolated[year] = sorted_points[0]['loss_percentage']
#                 elif year >= sorted_points[-1]['year']:
#                     # After last point - use last value
#                     interpolated[year] = sorted_points[-1]['loss_percentage']
#                 else:
#                     # Linear interpolation between points
#                     for i in range(len(sorted_points) - 1):
#                         if sorted_points[i]['year'] <= year <= sorted_points[i + 1]['year']:
#                             prev_point = sorted_points[i]
#                             next_point = sorted_points[i + 1]
                            
#                             # Linear interpolation formula
#                             year_diff = next_point['year'] - prev_point['year']
#                             if year_diff == 0:
#                                 interpolated[year] = prev_point['loss_percentage']
#                             else:
#                                 loss_diff = next_point['loss_percentage'] - prev_point['loss_percentage']
#                                 weight = (year - prev_point['year']) / year_diff
#                                 interpolated[year] = prev_point['loss_percentage'] + (weight * loss_diff)
#                             break
            
#             except Exception as year_error:
#                 logger.warning(f"Error interpolating T&D losses for year {year}: {year_error}")
#                 interpolated[year] = 0.0
        
#         logger.debug(f"Interpolated T&D losses for {len(interpolated)} years")
#         return interpolated
        
#     except Exception as e:
#         logger.exception(f"Error interpolating T&D losses: {e}")
#         return {year: 0.0 for year in years}

# # ========== Consolidated Demand Calculation ==========

# def calculate_consolidated_demand(scenario_path, sector_models, td_losses_data, year_range):
#     """
#    consolidated demand calculation with comprehensive error handling
    
#     Args:
#         scenario_path (str): Path to scenario directory
#         sector_models (dict): Mapping of sector to selected model
#         td_losses_data (list): T&D losses configuration
#         year_range (dict): Dict with 'from' and 'to' keys
        
#     Returns:
#         pd.DataFrame: Consolidated demand data
#     """
#     logger.info(f"Calculating consolidated demand for scenario at {scenario_path}")
    
#     try:
#         # Validate inputs
#         if not scenario_path or not os.path.exists(scenario_path):
#             raise ValueError(f"Invalid scenario path: {scenario_path}")
        
#         if not sector_models:
#             raise ValueError("No sector models provided")
        
#         if not year_range or 'from' not in year_range or 'to' not in year_range:
#             raise ValueError("Invalid year range specification")
        
#         from_year, to_year, year_warnings = validate_year_range(
#             year_range['from'], year_range['to']
#         )
        
#         for warning in year_warnings:
#             logger.warning(f"Year range validation: {warning}")
        
#         years = list(range(from_year, to_year + 1))
#         consolidated_data = {'Year': years}
        
#         # Load data for each sector using selected model
#         gross_demand_by_year = {year: 0.0 for year in years}
#         successful_sectors = []
#         failed_sectors = []
        
#         for sector, selected_model in sector_models.items():
#             logger.debug(f"Processing sector {sector} with model {selected_model}")
            
#             try:
#                 sector_df = get_forecast_data_for_sector(
#                     scenario_path, sector, from_year, to_year, 'kWh'
#                 )
                
#                 if sector_df is not None and selected_model in sector_df.columns:
#                     # Create mapping of year to demand
#                     year_to_demand = {}
#                     for _, row in sector_df.iterrows():
#                         year = int(row['Year'])
#                         demand = safe_numeric_conversion(row[selected_model], 0)
#                         year_to_demand[year] = demand
                    
#                     sector_demands = []
#                     for year in years:
#                         demand = year_to_demand.get(year, 0)
#                         sector_demands.append(demand)
#                         gross_demand_by_year[year] += demand
                    
#                     consolidated_data[sector] = sector_demands
#                     successful_sectors.append(sector)
#                     logger.debug(f"Successfully processed sector {sector}")
                    
#                 else:
#                     # No data available for this sector/model combination
#                     logger.warning(f"No data available for sector {sector} with model {selected_model}")
#                     consolidated_data[sector] = [0] * len(years)
#                     failed_sectors.append(sector)
                    
#             except Exception as sector_error:
#                 logger.error(f"Error processing sector {sector}: {sector_error}")
#                 consolidated_data[sector] = [0] * len(years)
#                 failed_sectors.append(sector)
        
#         # Log processing results
#         logger.info(f"Sector processing: {len(successful_sectors)} successful, {len(failed_sectors)} failed")
#         if failed_sectors:
#             logger.warning(f"Failed sectors: {failed_sectors}")
        
#         # Calculate T&D losses and total on-grid demand
#         try:
#             interpolated_losses = interpolate_td_losses(td_losses_data, years)
            
#             td_losses = []
#             total_on_grid = []
            
#             for year in years:
#                 gross_demand = gross_demand_by_year[year]
#                 loss_percentage = interpolated_losses.get(year, 0)
#                 loss_fraction = loss_percentage / 100
                
#                 # Calculate on-grid demand: gross_demand = on_grid_demand * (1 - loss_fraction)
#                 # Therefore: on_grid_demand = gross_demand / (1 - loss_fraction)
#                 if loss_fraction < 1 and loss_fraction >= 0:  # Avoid division by zero and negative losses
#                     on_grid_demand = gross_demand / (1 - loss_fraction)
#                     td_loss = on_grid_demand - gross_demand
#                 else:
#                     logger.warning(f"Invalid loss fraction {loss_fraction} for year {year}")
#                     on_grid_demand = gross_demand
#                     td_loss = 0
                
#                 td_losses.append(max(0, td_loss))  # Ensure non-negative
#                 total_on_grid.append(max(0, on_grid_demand))  # Ensure non-negative
            
#             consolidated_data['T&D_Losses'] = td_losses
#             consolidated_data['Total_On_Grid_Demand'] = total_on_grid
            
#         except Exception as td_error:
#             logger.exception(f"Error calculating T&D losses: {td_error}")
#             # Add zero losses as fallback
#             consolidated_data['T&D_Losses'] = [0] * len(years)
#             consolidated_data['Total_On_Grid_Demand'] = [gross_demand_by_year[year] for year in years]
        
#         # Create DataFrame
#         result_df = pd.DataFrame(consolidated_data)
        
#         # Validate result
#         if result_df.empty:
#             logger.error("Consolidated demand calculation resulted in empty DataFrame")
#             raise ValueError("Consolidated demand calculation failed")
        
#         # Apply final validation and cleaning
#         for col in result_df.columns:
#             if col != 'Year':
#                 result_df[col] = result_df[col].apply(lambda x: max(0, safe_numeric_conversion(x, 0)))
        
#         logger.info(f"Successfully calculated consolidated demand for {len(years)} years")
#         return result_df
        
#     except Exception as e:
#         logger.exception(f"Error calculating consolidated demand: {e}")
        
#         # Return safe fallback DataFrame
#         try:
#             from_year = year_range.get('from', 2025)
#             to_year = year_range.get('to', 2037)
#             years = list(range(from_year, to_year + 1))
            
#             fallback_data = {'Year': years}
#             for sector in sector_models.keys():
#                 fallback_data[sector] = [0] * len(years)
#             fallback_data['T&D_Losses'] = [0] * len(years)
#             fallback_data['Total_On_Grid_Demand'] = [0] * len(years)
            
#             return pd.DataFrame(fallback_data)
            
#         except Exception as fallback_error:
#             logger.exception(f"Error creating fallback DataFrame: {fallback_error}")
#             return pd.DataFrame()

# # ========== Workflow Management ==========

# def validate_workflow_completion(scenario_path):
#     """
#    workflow completion validation
    
#     Args:
#         scenario_path (str): Path to scenario directory
        
#     Returns:
#         dict: Detailed workflow status
#     """
#     checks = {
#         'has_forecast_data': False,
#         'has_model_config': False, 
#         'has_td_losses': False,
#         'has_consolidated': False,
#         'forecast_files_count': 0,
#         'config_files_found': [],
#         'last_modified': None
#     }
    
#     try:
#         if not os.path.exists(scenario_path):
#             logger.debug(f"Scenario path does not exist: {scenario_path}")
#             return checks
        
#         # Check for forecast data (Excel files)
#         try:
#             xlsx_files = [
#                 f for f in os.listdir(scenario_path) 
#                 if f.endswith('.xlsx') and not f.startswith('_')
#             ]
#             checks['has_forecast_data'] = len(xlsx_files) > 0
#             checks['forecast_files_count'] = len(xlsx_files)
            
#             if xlsx_files:
#                 logger.debug(f"Found {len(xlsx_files)} forecast files in {scenario_path}")
#         except (OSError, PermissionError) as dir_error:
#             logger.warning(f"Cannot access scenario directory {scenario_path}: {dir_error}")
        
#         # Check for configuration files
#         config_files = {
#             'model_config.json': 'has_model_config',
#             'td_losses.json': 'has_td_losses'
#         }
        
#         for config_file, check_key in config_files.items():
#             config_path = os.path.join(scenario_path, config_file)
#             if os.path.exists(config_path):
#                 checks[check_key] = True
#                 checks['config_files_found'].append(config_file)
                
#                 # Get last modified time
#                 try:
#                     mtime = os.path.getmtime(config_path)
#                     if checks['last_modified'] is None or mtime > checks['last_modified']:
#                         checks['last_modified'] = datetime.fromtimestamp(mtime).isoformat()
#                 except (OSError, OverflowError):
#                     pass
        
#         # Check for consolidated results
#         scenario_name = os.path.basename(scenario_path)
#         consolidated_patterns = [
#             f'consolidated_results_{scenario_name}.csv',
#             'consolidated_results.csv',
#             f'{scenario_name}_consolidated.csv'
#         ]
        
#         for pattern in consolidated_patterns:
#             consolidated_path = os.path.join(scenario_path, pattern)
#             if os.path.exists(consolidated_path):
#                 checks['has_consolidated'] = True
#                 checks['consolidated_file'] = pattern
#                 break
        
#         # Calculate completion percentage
#         total_steps = 4
#         completed_steps = sum([
#             checks['has_forecast_data'],
#             checks['has_model_config'],
#             checks['has_td_losses'],
#             checks['has_consolidated']
#         ])
#         checks['completion_percentage'] = (completed_steps / total_steps) * 100
        
#         logger.debug(f"Workflow completion for {scenario_path}: {checks['completion_percentage']:.1f}%")
        
#     except Exception as e:
#         logger.exception(f"Error validating workflow completion for {scenario_path}: {e}")
#         checks['error'] = str(e)
    
#     return checks

# # ========== Summary and Reporting ==========

# def create_summary(data_payload, sector_configs, forecast_dir, sectors_using_existing_data, 
#                   sectors_forecasted, sectors_with_errors, start_year, end_year):
#     """
#    summary creation with comprehensive reporting
    
#     Args:
#         data_payload (dict): Original forecast request payload
#         sector_configs (dict): Sector configurations used
#         forecast_dir (str): Directory where results are saved
#         sectors_using_existing_data (list): Sectors that used existing data
#         sectors_forecasted (list): Sectors that were forecasted
#         sectors_with_errors (list): Sectors that failed processing
#         start_year (int): Data start year
#         end_year (int): Data end year
        
#     Returns:
#         dict: Comprehensive summary
#     """
#     try:
#         scenario_name = data_payload.get('scenarioName', 'Unknown')
#         target_year = int(data_payload.get('targetYear', 2037))
#         exclude_covid = data_payload.get('excludeCovidYears', True)
#         detailed_config = data_payload.get('detailedConfiguration', {})
        
#         # Calculate processing statistics
#         total_sectors = len(sector_configs)
#         successful_sectors = len(sectors_forecasted) + len(sectors_using_existing_data)
#         success_rate = (successful_sectors / total_sectors) if total_sectors > 0 else 0
        
#         # Analyze model usage
#         model_usage = {}
#         advanced_configs = 0
        
#         for sector_name, config in sector_configs.items():
#             models = config.get('models', [])
#             for model in models:
#                 model_usage[model] = model_usage.get(model, 0) + 1
            
#             # Check for advanced configurations
#             if ('MLR' in models and len(config.get('independentVars', [])) > 3) or \
#                ('WAM' in models and config.get('windowSize', 10) != 10):
#                 advanced_configs += 1
        
#         most_common_model = max(model_usage.keys(), key=model_usage.get) if model_usage else None
        
#         summary = {
#             # Basic scenario information
#             'scenario_info': {
#                 'scenario_name': scenario_name,
#                 'target_year': target_year,
#                 'start_year': start_year,
#                 'end_year': end_year,
#                 'exclude_covid_years': exclude_covid,
#                 'created_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
#                 'created_timestamp_iso': datetime.now().isoformat(),
#                 'forecast_period_years': max(0, target_year - end_year),
#                 'data_period_years': end_year - start_year + 1
#             },
            
#             # Processing results
#             'processing_results': {
#                 'total_sectors': total_sectors,
#                 'successful_sectors': successful_sectors,
#                 'sectors_forecasted': len(sectors_forecasted),
#                 'sectors_using_existing_data': len(sectors_using_existing_data),
#                 'sectors_with_errors': len(sectors_with_errors),
#                 'success_rate': round(success_rate, 3),
#                 'processing_summary': {
#                     'forecasted': sectors_forecasted,
#                     'existing_data': sectors_using_existing_data,
#                     'failed': sectors_with_errors
#                 }
#             },
            
#             # Model usage statistics
#             'model_statistics': {
#                 'models_used': list(model_usage.keys()),
#                 'model_usage_counts': model_usage,
#                 'most_common_model': most_common_model,
#                 'advanced_configurations': advanced_configs,
#                 'total_model_instances': sum(model_usage.values())
#             },
            
#             # Configuration details
#             'configuration_summary': {
#                 'total_sectors_configured': total_sectors,
#                 'default_models_used': detailed_config.get('defaultModels', []),
#                 'configuration_complexity': 'Advanced' if advanced_configs > 0 else 'Standard'
#             },
            
#             # File and directory information
#             'file_info': {
#                 'results_directory': forecast_dir,
#                 'scenario_folder': os.path.basename(forecast_dir),
#                 'project_relative_path': f"results/demand_projection/{scenario_name}"
#             }
#         }
        
#         # Add detailed sector configurations
#         summary['sector_configurations'] = {}
#         for sector_name, config in sector_configs.items():
#             sector_status = 'forecasted' if sector_name in sectors_forecasted else \
#                            'existing_data' if sector_name in sectors_using_existing_data else 'failed'
            
#             summary['sector_configurations'][sector_name] = {
#                 'models_selected': config.get('models', []),
#                 'status': sector_status,
#                 'independent_variables': config.get('independentVars', []),
#                 'window_size': config.get('windowSize'),
#                 'configuration_complexity': 'Advanced' if len(config.get('independentVars', [])) > 3 else 'Standard'
#             }
        
#         # Add file listing if directory exists
#         if os.path.exists(forecast_dir):
#             try:
#                 generated_files = [f for f in os.listdir(forecast_dir) if f.endswith('.xlsx')]
#                 summary['file_info']['generated_files'] = generated_files
#                 summary['file_info']['file_count'] = len(generated_files)
#             except Exception as files_error:
#                 logger.warning(f"Could not list generated files: {files_error}")
#                 summary['file_info']['file_listing_error'] = str(files_error)
        
#         # Add quality metrics
#         summary['quality_metrics'] = {
#             'data_completeness': success_rate,
#             'forecast_coverage': len(sectors_forecasted) / total_sectors if total_sectors > 0 else 0,
#             'error_rate': len(sectors_with_errors) / total_sectors if total_sectors > 0 else 0,
#             'configuration_sophistication': advanced_configs / total_sectors if total_sectors > 0 else 0
#         }
        
#         logger.info(f"Summary created for scenario {scenario_name}: {success_rate:.1%} success rate")
#         return summary
        
#     except Exception as e:
#         logger.exception(f"Error creating summary: {e}")
#         # Return minimal summary on error
#         return {
#             'scenario_info': {
#                 'scenario_name': data_payload.get('scenarioName', 'Unknown'),
#                 'created_timestamp_iso': datetime.now().isoformat(),
#                 'error': str(e)
#             },
#             'processing_results': {
#                 'total_sectors': len(sector_configs),
#                 'sectors_with_errors': len(sectors_with_errors),
#                 'error_occurred': True
#             }
#         }


"""
FIXED utility functions for demand projection and visualization modules
"""
import os
import json
import time
import pandas as pd
import numpy as np
import logging
from datetime import datetime
from flask import current_app

from utils.constants import UNIT_FACTORS, VALIDATION_RULES, ERROR_MESSAGES
from utils.response_utils import handle_exception_response

logger = logging.getLogger(__name__)

# ========== Data Handling Utilities ==========

def handle_nan_values(obj):
    """
    FIXED: Convert NaN and Infinity values to null for JSON serialization
    """
    if isinstance(obj, pd.DataFrame):
        # Handle DataFrame specifically
        df_copy = obj.copy()
        # Replace NaN and inf values with None
        df_copy = df_copy.replace([np.nan, np.inf, -np.inf], None)
        return df_copy
    elif isinstance(obj, pd.Series):
        # Handle Series specifically
        return obj.replace([np.nan, np.inf, -np.inf], None)
    elif isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return obj
    elif isinstance(obj, np.number):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, dict):
        return {k: handle_nan_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [handle_nan_values(item) for item in obj]
    elif isinstance(obj, np.ndarray):
        return handle_nan_values(obj.tolist())
    elif pd.isna(obj):
        return None
    return obj

def safe_numeric_conversion(value, default=0):
    """
    FIXED: Safely convert value to numeric, handling various edge cases INCLUDING infinity strings
    """
    try:
        if pd.isna(value) or value is None:
            return default
        
        if isinstance(value, (int, float)):
            if np.isnan(value) or np.isinf(value):
                return default
            return float(value)
        
        # Try to convert string to float
        if isinstance(value, str):
            cleaned_value = value.strip().replace(',', '').lower()
            
            # Check for problematic string values that create infinity
            if cleaned_value in ['', 'na', 'nan', 'null', 'inf', 'infinity', '-inf', '-infinity']:
                return default
                
            try:
                result = float(cleaned_value)
                # Double-check the result isn't infinity
                if np.isinf(result) or np.isnan(result):
                    return default
                return result
            except (ValueError, OverflowError):
                return default
        
        result = float(value)
        if np.isinf(result) or np.isnan(result):
            return default
        return result
    
    except (ValueError, TypeError, OverflowError):
        logger.debug(f"Could not convert {value} to numeric, using default {default}")
        return default

def validate_year_range(start_year, end_year):
    """
    Validate and adjust year range
    """
    warnings = []
    
    try:
        start_year = int(safe_numeric_conversion(start_year, VALIDATION_RULES.get('MIN_YEAR', 2006)))
        end_year = int(safe_numeric_conversion(end_year, 2037))
        
        # Ensure start year is before end year
        if start_year >= end_year:
            warnings.append(f"Start year ({start_year}) >= End year ({end_year}), adjusting")
            if start_year == end_year:
                end_year = start_year + 1
            else:
                start_year, end_year = min(start_year, end_year), max(start_year, end_year)
        
        # Check reasonable bounds
        min_year = VALIDATION_RULES.get('MIN_YEAR', 1990)
        max_year = VALIDATION_RULES.get('MAX_YEAR', 2100)
        
        if start_year < min_year:
            warnings.append(f"Start year {start_year} is below minimum {min_year}")
            start_year = min_year
        
        if end_year > max_year:
            warnings.append(f"End year {end_year} is above maximum {max_year}")
            end_year = max_year
        
        return start_year, end_year, warnings
        
    except Exception as e:
        logger.warning(f"Error validating year range: {e}")
        return 2006, 2037, [f"Year validation error: {str(e)}"]

# ========== Project and Path Validation ==========

def validate_project_path():
    """
    FIXED: project path validation with detailed checking
    """
    try:
        project_path = current_app.config.get('CURRENT_PROJECT_PATH')
        
        if not project_path:
            logger.debug("No project path configured")
            return False
        
        if not os.path.exists(project_path):
            logger.warning(f"Project path does not exist: {project_path}")
            current_app.config['CURRENT_PROJECT'] = None
            current_app.config['CURRENT_PROJECT_PATH'] = None
            return False
        
        if not os.path.isdir(project_path):
            logger.warning(f"Project path is not a directory: {project_path}")
            return False
        
        # Check for basic project structure
        required_dirs = ['inputs', 'results']
        for required_dir in required_dirs:
            dir_path = os.path.join(project_path, required_dir)
            if not os.path.exists(dir_path):
                logger.warning(f"Required directory missing: {dir_path}")
                return False
        
        return True
        
    except Exception as e:
        logger.exception(f"Error validating project path: {e}")
        return False

def get_scenario_list(scenarios_path):
    """
    Get list of available forecast scenarios with validation
    """
    try:
        if not os.path.exists(scenarios_path):
            logger.debug(f"Scenarios path does not exist: {scenarios_path}")
            return []
        
        scenarios = []
        for item in os.listdir(scenarios_path):
            item_path = os.path.join(scenarios_path, item)
            
            if not os.path.isdir(item_path):
                continue
            
            # Check if directory contains forecast files
            try:
                scenario_files = os.listdir(item_path)
                has_forecast_files = any(
                    f.endswith('.xlsx') and not f.startswith('_') 
                    for f in scenario_files
                )
                
                if has_forecast_files:
                    scenarios.append(item)
                else:
                    logger.debug(f"Scenario directory {item} has no valid forecast files")
                    
            except (OSError, PermissionError) as dir_error:
                logger.warning(f"Cannot access scenario directory {item}: {dir_error}")
        
        scenarios.sort()
        logger.debug(f"Found {len(scenarios)} valid scenarios")
        return scenarios
        
    except Exception as e:
        logger.exception(f"Error getting scenario list from {scenarios_path}: {e}")
        return []

# ========== Data Loading and Processing ==========

def get_forecast_data_for_sector(scenario_path, sector, from_year, to_year, unit='kWh'):
    """
    FIXED: forecast data loading with comprehensive error handling and Results sheet reading
    """
    logger.debug(f"Loading forecast data for sector '{sector}' from {scenario_path}")
    
    try:
        # Validate inputs
        if not scenario_path or not sector:
            logger.warning("Invalid scenario path or sector name")
            return None
        
        from_year, to_year, year_warnings = validate_year_range(from_year, to_year)
        for warning in year_warnings:
            logger.debug(f"Year range validation: {warning}")
        
        # Construct file path
        file_path = os.path.join(scenario_path, f"{sector}.xlsx")
        
        if not os.path.exists(file_path):
            logger.debug(f"Sector file not found: {file_path}")
            return None
        
        # FIXED: Try to read Results sheet first, then fallback
        try:
            df = pd.read_excel(file_path, sheet_name='Results')
            logger.debug(f"Successfully read Results sheet from {file_path}")
        except Exception as read_error:
            logger.warning(f"Could not read Results sheet from {file_path}: {read_error}")
            try:
                # Try first sheet as fallback
                df = pd.read_excel(file_path, sheet_name=0)
                logger.debug(f"Used first sheet as fallback for {file_path}")
            except Exception as fallback_error:
                logger.error(f"Could not read any sheet from {file_path}: {fallback_error}")
                return None
        
        # Validate DataFrame structure
        if df.empty:
            logger.warning(f"Empty sheet in {file_path}")
            return None
        
        if 'Year' not in df.columns:
            logger.warning(f"'Year' column missing in {file_path}")
            return None
        
        # Clean and convert Year column
        df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
        df = df.dropna(subset=['Year'])
        
        if df.empty:
            logger.warning(f"No valid year data in {file_path}")
            return None
        
        # Filter by year range
        df = df[(df['Year'] >= from_year) & (df['Year'] <= to_year)].copy()
        
        if df.empty:
            logger.debug(f"No data in year range {from_year}-{to_year} for {sector}")
            return None
        
        # Convert numeric columns and handle unit conversion
        unit_factor = UNIT_FACTORS.get(unit, 1)
        
        for col in df.columns:
            if col != 'Year':
                try:
                    # Convert to numeric
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    # Apply unit conversion if not kWh
                    if unit != 'kWh' and unit_factor != 1:
                        df[col] = df[col] / unit_factor
                        
                except Exception as col_error:
                    logger.debug(f"Could not process column {col} in {sector}: {col_error}")
        
        # Sort by year
        df = df.sort_values('Year').reset_index(drop=True)
        
        logger.debug(f"Successfully loaded {len(df)} rows for {sector} ({from_year}-{to_year})")
        return df
        
    except Exception as e:
        logger.exception(f"Error getting forecast data for sector {sector}: {e}")
        return None

# ========== T&D Losses Calculation ==========

def interpolate_td_losses(td_losses_points, years):
    """
    FIXED: T&D losses interpolation with validation
    """
    try:
        if not td_losses_points:
            logger.debug("No T&D losses points provided, returning zero losses")
            return {year: 0.0 for year in years}
        
        if not years:
            logger.debug("No years provided for T&D losses interpolation")
            return {}
        
        # Validate and clean points
        valid_points = []
        for point in td_losses_points:
            try:
                year = int(safe_numeric_conversion(point.get('year', 0)))
                loss_pct = safe_numeric_conversion(point.get('loss_percentage', 0))
                
                # Validate loss percentage is reasonable
                if loss_pct < 0:
                    logger.warning(f"Negative loss percentage {loss_pct} for year {year}, setting to 0")
                    loss_pct = 0
                elif loss_pct > 50:
                    logger.warning(f"Very high loss percentage {loss_pct} for year {year}")
                
                valid_points.append({'year': year, 'loss_percentage': loss_pct})
                
            except Exception as point_error:
                logger.warning(f"Invalid T&D loss point {point}: {point_error}")
        
        if not valid_points:
            logger.warning("No valid T&D losses points after validation")
            return {year: 0.0 for year in years}
        
        # Sort points by year
        sorted_points = sorted(valid_points, key=lambda x: x['year'])
        interpolated = {}
        
        for year in years:
            try:
                year = int(year)
                
                if year <= sorted_points[0]['year']:
                    # Before first point - use first value
                    interpolated[year] = sorted_points[0]['loss_percentage']
                elif year >= sorted_points[-1]['year']:
                    # After last point - use last value
                    interpolated[year] = sorted_points[-1]['loss_percentage']
                else:
                    # Linear interpolation between points
                    for i in range(len(sorted_points) - 1):
                        if sorted_points[i]['year'] <= year <= sorted_points[i + 1]['year']:
                            prev_point = sorted_points[i]
                            next_point = sorted_points[i + 1]
                            
                            # Linear interpolation formula
                            year_diff = next_point['year'] - prev_point['year']
                            if year_diff == 0:
                                interpolated[year] = prev_point['loss_percentage']
                            else:
                                loss_diff = next_point['loss_percentage'] - prev_point['loss_percentage']
                                weight = (year - prev_point['year']) / year_diff
                                interpolated[year] = prev_point['loss_percentage'] + (weight * loss_diff)
                            break
            
            except Exception as year_error:
                logger.warning(f"Error interpolating T&D losses for year {year}: {year_error}")
                interpolated[year] = 0.0
        
        logger.debug(f"Interpolated T&D losses for {len(interpolated)} years")
        return interpolated
        
    except Exception as e:
        logger.exception(f"Error interpolating T&D losses: {e}")
        return {year: 0.0 for year in years}

# ========== Consolidated Demand Calculation ==========

def calculate_consolidated_demand(scenario_path, sector_models, td_losses_data, year_range):
    """
    FIXED: consolidated demand calculation with comprehensive error handling and Results sheet reading
    """
    logger.info(f"Calculating consolidated demand for scenario at {scenario_path}")
    
    try:
        # Validate inputs
        if not scenario_path or not os.path.exists(scenario_path):
            raise ValueError(f"Invalid scenario path: {scenario_path}")
        
        if not sector_models:
            raise ValueError("No sector models provided")
        
        if not year_range or 'from' not in year_range or 'to' not in year_range:
            raise ValueError("Invalid year range specification")
        
        from_year, to_year, year_warnings = validate_year_range(
            year_range['from'], year_range['to']
        )
        
        for warning in year_warnings:
            logger.warning(f"Year range validation: {warning}")
        
        years = list(range(from_year, to_year + 1))
        consolidated_data = {'Year': years}
        
        # Load data for each sector using selected model
        gross_demand_by_year = {year: 0.0 for year in years}
        successful_sectors = []
        failed_sectors = []
        
        for sector, selected_model in sector_models.items():
            logger.debug(f"Processing sector {sector} with model {selected_model}")
            
            try:
                # FIXED: Use get_forecast_data_for_sector which handles Results sheet
                sector_df = get_forecast_data_for_sector(
                    scenario_path, sector, from_year, to_year, 'kWh'
                )
                
                if sector_df is not None and selected_model in sector_df.columns:
                    # Create mapping of year to demand
                    year_to_demand = {}
                    for _, row in sector_df.iterrows():
                        year = int(row['Year'])
                        demand = safe_numeric_conversion(row[selected_model], 0)
                        year_to_demand[year] = demand
                    
                    sector_demands = []
                    for year in years:
                        demand = year_to_demand.get(year, 0)
                        sector_demands.append(demand)
                        gross_demand_by_year[year] += demand
                    
                    consolidated_data[sector] = sector_demands
                    successful_sectors.append(sector)
                    logger.debug(f"Successfully processed sector {sector}")
                    
                else:
                    # No data available for this sector/model combination
                    logger.warning(f"No data available for sector {sector} with model {selected_model}")
                    consolidated_data[sector] = [0] * len(years)
                    failed_sectors.append(sector)
                    
            except Exception as sector_error:
                logger.error(f"Error processing sector {sector}: {sector_error}")
                consolidated_data[sector] = [0] * len(years)
                failed_sectors.append(sector)
        
        # Log processing results
        logger.info(f"Sector processing: {len(successful_sectors)} successful, {len(failed_sectors)} failed")
        if failed_sectors:
            logger.warning(f"Failed sectors: {failed_sectors}")
        
        # Calculate T&D losses and total on-grid demand
        try:
            interpolated_losses = interpolate_td_losses(td_losses_data, years)
            
            td_losses = []
            total_on_grid = []
            
            for year in years:
                gross_demand = gross_demand_by_year[year]
                loss_percentage = interpolated_losses.get(year, 0)
                loss_fraction = loss_percentage / 100
                
                # Calculate on-grid demand: gross_demand = on_grid_demand * (1 - loss_fraction)
                # Therefore: on_grid_demand = gross_demand / (1 - loss_fraction)
                if loss_fraction < 1 and loss_fraction >= 0:  # Avoid division by zero and negative losses
                    on_grid_demand = gross_demand / (1 - loss_fraction)
                    td_loss = on_grid_demand - gross_demand
                else:
                    logger.warning(f"Invalid loss fraction {loss_fraction} for year {year}")
                    on_grid_demand = gross_demand
                    td_loss = 0
                
                td_losses.append(max(0, td_loss))  # Ensure non-negative
                total_on_grid.append(max(0, on_grid_demand))  # Ensure non-negative
            
            consolidated_data['T&D_Losses'] = td_losses
            consolidated_data['Total_On_Grid_Demand'] = total_on_grid
            
        except Exception as td_error:
            logger.exception(f"Error calculating T&D losses: {td_error}")
            # Add zero losses as fallback
            consolidated_data['T&D_Losses'] = [0] * len(years)
            consolidated_data['Total_On_Grid_Demand'] = [gross_demand_by_year[year] for year in years]
        
        # Create DataFrame
        result_df = pd.DataFrame(consolidated_data)
        
        # Validate result
        if result_df.empty:
            logger.error("Consolidated demand calculation resulted in empty DataFrame")
            raise ValueError("Consolidated demand calculation failed")
        
        # Apply final validation and cleaning
        for col in result_df.columns:
            if col != 'Year':
                result_df[col] = result_df[col].apply(lambda x: max(0, safe_numeric_conversion(x, 0)))
        
        logger.info(f"Successfully calculated consolidated demand for {len(years)} years")
        return result_df
        
    except Exception as e:
        logger.exception(f"Error calculating consolidated demand: {e}")
        
        # Return safe fallback DataFrame
        try:
            from_year = year_range.get('from', 2025)
            to_year = year_range.get('to', 2037)
            years = list(range(from_year, to_year + 1))
            
            fallback_data = {'Year': years}
            for sector in sector_models.keys():
                fallback_data[sector] = [0] * len(years)
            fallback_data['T&D_Losses'] = [0] * len(years)
            fallback_data['Total_On_Grid_Demand'] = [0] * len(years)
            
            return pd.DataFrame(fallback_data)
            
        except Exception as fallback_error:
            logger.exception(f"Error creating fallback DataFrame: {fallback_error}")
            return pd.DataFrame()

# ========== Workflow Management ==========

def validate_workflow_completion(scenario_path):
    """
    FIXED: workflow completion validation
    """
    checks = {
        'has_forecast_data': False,
        'has_model_config': False, 
        'has_td_losses': False,
        'has_consolidated': False,
        'forecast_files_count': 0,
        'config_files_found': [],
        'last_modified': None
    }
    
    try:
        if not os.path.exists(scenario_path):
            logger.debug(f"Scenario path does not exist: {scenario_path}")
            return checks
        
        # Check for forecast data (Excel files)
        try:
            xlsx_files = [
                f for f in os.listdir(scenario_path) 
                if f.endswith('.xlsx') and not f.startswith('_')
            ]
            checks['has_forecast_data'] = len(xlsx_files) > 0
            checks['forecast_files_count'] = len(xlsx_files)
            
            if xlsx_files:
                logger.debug(f"Found {len(xlsx_files)} forecast files in {scenario_path}")
        except (OSError, PermissionError) as dir_error:
            logger.warning(f"Cannot access scenario directory {scenario_path}: {dir_error}")
        
        # Check for configuration files
        config_files = {
            'model_config.json': 'has_model_config',
            'td_losses.json': 'has_td_losses'
        }
        
        for config_file, check_key in config_files.items():
            config_path = os.path.join(scenario_path, config_file)
            if os.path.exists(config_path):
                checks[check_key] = True
                checks['config_files_found'].append(config_file)
                
                # Get last modified time
                try:
                    mtime = os.path.getmtime(config_path)
                    if checks['last_modified'] is None or mtime > checks['last_modified']:
                        checks['last_modified'] = datetime.fromtimestamp(mtime).isoformat()
                except (OSError, OverflowError):
                    pass
        
        # Check for consolidated results
        scenario_name = os.path.basename(scenario_path)
        consolidated_patterns = [
            f'consolidated_results_{scenario_name}.csv',
            'consolidated_results.csv',
            f'{scenario_name}_consolidated.csv'
        ]
        
        for pattern in consolidated_patterns:
            consolidated_path = os.path.join(scenario_path, pattern)
            if os.path.exists(consolidated_path):
                checks['has_consolidated'] = True
                checks['consolidated_file'] = pattern
                break
        
        # Calculate completion percentage
        total_steps = 4
        completed_steps = sum([
            checks['has_forecast_data'],
            checks['has_model_config'],
            checks['has_td_losses'],
            checks['has_consolidated']
        ])
        checks['completion_percentage'] = (completed_steps / total_steps) * 100
        
        logger.debug(f"Workflow completion for {scenario_path}: {checks['completion_percentage']:.1f}%")
        
    except Exception as e:
        logger.exception(f"Error validating workflow completion for {scenario_path}: {e}")
        checks['error'] = str(e)
    
    return checks

# ========== Summary and Reporting ==========

def create_summary(data_payload, sector_configs, forecast_dir, sectors_using_existing_data, 
                  sectors_forecasted, sectors_with_errors, start_year, end_year):
    """
    FIXED: summary creation with comprehensive reporting
    """
    try:
        scenario_name = data_payload.get('scenarioName', 'Unknown')
        target_year = int(data_payload.get('targetYear', 2037))
        exclude_covid = data_payload.get('excludeCovidYears', True)
        detailed_config = data_payload.get('detailedConfiguration', {})
        
        # Calculate processing statistics
        total_sectors = len(sector_configs)
        successful_sectors = len(sectors_forecasted) + len(sectors_using_existing_data)
        success_rate = (successful_sectors / total_sectors) if total_sectors > 0 else 0
        
        # Analyze model usage
        model_usage = {}
        advanced_configs = 0
        
        for sector_name, config in sector_configs.items():
            models = config.get('models', [])
            for model in models:
                model_usage[model] = model_usage.get(model, 0) + 1
            
            # Check for advanced configurations
            if ('MLR' in models and len(config.get('independentVars', [])) > 3) or \
               ('WAM' in models and config.get('windowSize', 10) != 10):
                advanced_configs += 1
        
        most_common_model = max(model_usage.keys(), key=model_usage.get) if model_usage else None
        
        summary = {
            # Basic scenario information
            'scenario_info': {
                'scenario_name': scenario_name,
                'target_year': target_year,
                'start_year': start_year,
                'end_year': end_year,
                'exclude_covid_years': exclude_covid,
                'created_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'created_timestamp_iso': datetime.now().isoformat(),
                'forecast_period_years': max(0, target_year - end_year),
                'data_period_years': end_year - start_year + 1
            },
            
            # Processing results
            'processing_results': {
                'total_sectors': total_sectors,
                'successful_sectors': successful_sectors,
                'sectors_forecasted': len(sectors_forecasted),
                'sectors_using_existing_data': len(sectors_using_existing_data),
                'sectors_with_errors': len(sectors_with_errors),
                'success_rate': round(success_rate, 3),
                'processing_summary': {
                    'forecasted': sectors_forecasted,
                    'existing_data': sectors_using_existing_data,
                    'failed': sectors_with_errors
                }
            },
            
            # Model usage statistics
            'model_statistics': {
                'models_used': list(model_usage.keys()),
                'model_usage_counts': model_usage,
                'most_common_model': most_common_model,
                'advanced_configurations': advanced_configs,
                'total_model_instances': sum(model_usage.values())
            },
            
            # Configuration details
            'configuration_summary': {
                'total_sectors_configured': total_sectors,
                'default_models_used': detailed_config.get('defaultModels', []),
                'configuration_complexity': 'Advanced' if advanced_configs > 0 else 'Standard'
            },
            
            # File and directory information
            'file_info': {
                'results_directory': forecast_dir,
                'scenario_folder': os.path.basename(forecast_dir),
                'project_relative_path': f"results/demand_projection/{scenario_name}"
            }
        }
        
        # Add detailed sector configurations
        summary['sector_configurations'] = {}
        for sector_name, config in sector_configs.items():
            sector_status = 'forecasted' if sector_name in sectors_forecasted else \
                           'existing_data' if sector_name in sectors_using_existing_data else 'failed'
            
            summary['sector_configurations'][sector_name] = {
                'models_selected': config.get('models', []),
                'status': sector_status,
                'independent_variables': config.get('independentVars', []),
                'window_size': config.get('windowSize'),
                'configuration_complexity': 'Advanced' if len(config.get('independentVars', [])) > 3 else 'Standard'
            }
        
        # Add file listing if directory exists
        if os.path.exists(forecast_dir):
            try:
                generated_files = [f for f in os.listdir(forecast_dir) if f.endswith('.xlsx')]
                summary['file_info']['generated_files'] = generated_files
                summary['file_info']['file_count'] = len(generated_files)
            except Exception as files_error:
                logger.warning(f"Could not list generated files: {files_error}")
                summary['file_info']['file_listing_error'] = str(files_error)
        
        # Add quality metrics
        summary['quality_metrics'] = {
            'data_completeness': success_rate,
            'forecast_coverage': len(sectors_forecasted) / total_sectors if total_sectors > 0 else 0,
            'error_rate': len(sectors_with_errors) / total_sectors if total_sectors > 0 else 0,
            'configuration_sophistication': advanced_configs / total_sectors if total_sectors > 0 else 0
        }
        
        logger.info(f"Summary created for scenario {scenario_name}: {success_rate:.1%} success rate")
        return summary
        
    except Exception as e:
        logger.exception(f"Error creating summary: {e}")
        # Return minimal summary on error
        return {
            'scenario_info': {
                'scenario_name': data_payload.get('scenarioName', 'Unknown'),
                'created_timestamp_iso': datetime.now().isoformat(),
                'error': str(e)
            },
            'processing_results': {
                'total_sectors': len(sector_configs),
                'sectors_with_errors': len(sectors_with_errors),
                'error_occurred': True
            }
        }