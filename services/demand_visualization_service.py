# services/demand_visualization_service.py
"""Enhanced Demand Visualization Service
Clean, efficient service for demand analysis with working filters and comparisons
"""
import os
import json
import pandas as pd
import numpy as np
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

# Import plot utilities for consistent chart generation
from utils.plot_utils import (
    create_time_series_chart,
    create_sector_comparison_chart,
    create_model_comparison_chart,
    plot_utils
)

logger = logging.getLogger(__name__)

@dataclass
class ScenarioInfo:
    name: str
    path: str
    sectors_count: int
    year_range: Dict[str, int]
    has_data: bool
    file_count: int = 0
    last_modified: str = None

class DemandVisualizationService:
    """Enhanced Demand Visualization Service with improved filtering and comparison"""
    
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.results_path = os.path.join(project_path, 'results', 'demand_projection')
        self.unit_factors = {
            'kWh': 1,
            'MWh': 1000,
            'GWh': 1000000,
            'TWh': 1000000000
        }
        logger.info(f"Initialized DemandVisualizationService with path: {self.results_path}")
    
    def get_available_scenarios(self) -> List[ScenarioInfo]:
        """Get list of available scenarios with comprehensive metadata"""
        try:
            if not os.path.exists(self.results_path):
                logger.warning(f"Results path does not exist: {self.results_path}")
                return []
            
            scenarios = []
            for item in os.listdir(self.results_path):
                item_path = os.path.join(self.results_path, item)
                
                if not os.path.isdir(item_path):
                    continue
                
                try:
                    scenario_info = self._analyze_scenario_directory(item, item_path)
                    if scenario_info.has_data:
                        scenarios.append(scenario_info)
                except Exception as e:
                    logger.warning(f"Error analyzing scenario {item}: {e}")
                    continue
            
            # Sort by last modified (newest first)
            scenarios.sort(key=lambda x: x.last_modified or '', reverse=True)
            logger.info(f"Found {len(scenarios)} valid scenarios")
            return scenarios
            
        except Exception as e:
            logger.exception(f"Error getting available scenarios: {e}")
            return []
    
    def _analyze_scenario_directory(self, scenario_name: str, scenario_path: str) -> ScenarioInfo:
        """Analyze scenario directory and extract comprehensive metadata"""
        try:
            excel_files = [
                f for f in os.listdir(scenario_path)
                if f.endswith('.xlsx') and not f.startswith('_') and not f.startswith('~')
            ]
            
            year_range = {'min': 2025, 'max': 2037}  # Default range
            last_modified = None
            
            if excel_files:
                # Analyze first few files for year range
                for excel_file in excel_files[:3]:
                    file_path = os.path.join(scenario_path, excel_file)
                    try:
                        file_mtime = os.path.getmtime(file_path)
                        if last_modified is None or file_mtime > last_modified:
                            last_modified = file_mtime
                        
                        # Quick scan for years
                        df = pd.read_excel(file_path, nrows=50)
                        year_cols = [col for col in df.columns if 'year' in str(col).lower()]
                        
                        for year_col in year_cols:
                            years = pd.to_numeric(df[year_col], errors='coerce').dropna()
                            if not years.empty:
                                year_range['min'] = min(year_range['min'], int(years.min()))
                                year_range['max'] = max(year_range['max'], int(years.max()))
                                break
                        
                    except Exception as e:
                        logger.debug(f"Could not analyze file {excel_file}: {e}")
                        continue
            
            return ScenarioInfo(
                name=scenario_name,
                path=scenario_path,
                sectors_count=len(excel_files),
                year_range=year_range,
                has_data=len(excel_files) > 0,
                file_count=len(excel_files),
                last_modified=datetime.fromtimestamp(last_modified).isoformat() if last_modified else None
            )
            
        except Exception as e:
            logger.warning(f"Error analyzing scenario directory {scenario_name}: {e}")
            return ScenarioInfo(
                name=scenario_name,
                path=scenario_path,
                sectors_count=0,
                year_range={'min': 2025, 'max': 2037},
                has_data=False
            )
    
    def get_scenario_data(self, scenario_name: str, filters: Dict = None) -> Dict[str, Any]:
        """Get comprehensive scenario data with applied filters"""
        try:
            scenario_path = os.path.join(self.results_path, scenario_name)
            if not os.path.exists(scenario_path):
                return {'error': f"Scenario '{scenario_name}' not found"}
            
            # Default filters
            filters = filters or {}
            unit = filters.get('unit', 'TWh')
            start_year = filters.get('start_year')
            end_year = filters.get('end_year')
            selected_sectors = filters.get('sectors', [])
            
            excel_files = [
                f for f in os.listdir(scenario_path)
                if f.endswith('.xlsx') and not f.startswith('_') and not f.startswith('~')
            ]
            
            sectors_data = {}
            all_years = set()
            available_models = set()
            
            for excel_file in excel_files:
                sector_name = os.path.splitext(excel_file)[0]
                
                # Skip if sector filtering is applied and sector not in selection
                if selected_sectors and sector_name not in selected_sectors:
                    continue
                
                file_path = os.path.join(scenario_path, excel_file)
                sector_data = self._load_sector_data(file_path, sector_name, unit, start_year, end_year)
                
                if sector_data:
                    sectors_data[sector_name] = sector_data
                    all_years.update(sector_data['years'])
                    available_models.update(sector_data['models'])
            
            # Determine year range
            if all_years:
                year_range = {'min': min(all_years), 'max': max(all_years)}
            else:
                year_range = {'min': 2025, 'max': 2037}
            
            return {
                'scenario_name': scenario_name,
                'sectors': sectors_data,
                'sector_list': list(sectors_data.keys()),
                'year_range': year_range,
                'available_models': list(available_models),
                'unit': unit,
                'filters_applied': filters,
                'total_sectors': len(sectors_data),
                'has_data': len(sectors_data) > 0
            }
            
        except Exception as e:
            logger.exception(f"Error getting scenario data for {scenario_name}: {e}")
            return {'error': str(e)}
    
    def _load_sector_data(self, file_path: str, sector_name: str, unit: str, 
                         start_year: int = None, end_year: int = None) -> Dict[str, Any]:
        """Load and process sector data with filters"""
        try:
            # Determine sheet name
            with pd.ExcelFile(file_path) as xls:
                sheet_names = xls.sheet_names
                target_sheet = 'Results' if 'Results' in sheet_names else sheet_names[0]
            
            df = pd.read_excel(file_path, sheet_name=target_sheet)
            
            # Find year column
            year_column = None
            for col in df.columns:
                if 'year' in str(col).lower():
                    year_column = col
                    break
            
            if not year_column:
                logger.warning(f"No year column found in {file_path}")
                return None
            
            # Clean and validate years
            df[year_column] = pd.to_numeric(df[year_column], errors='coerce')
            df = df.dropna(subset=[year_column])
            df[year_column] = df[year_column].astype(int)
            
            # Apply year range filter
            if start_year and end_year:
                df = df[(df[year_column] >= start_year) & (df[year_column] <= end_year)]
            elif start_year:
                df = df[df[year_column] >= start_year]
            elif end_year:
                df = df[df[year_column] <= end_year]
            
            if df.empty:
                return None
            
            df = df.sort_values(year_column)
            years = df[year_column].tolist()
            
            # Extract model columns
            exclude_patterns = ['year', 'years', 'unnamed', 'index', 'id', 'date', 'time']
            model_columns = []
            
            for col in df.columns:
                if col == year_column:
                    continue
                
                col_str = str(col).lower().strip()
                if any(pattern in col_str for pattern in exclude_patterns):
                    continue
                
                if col_str.startswith('unnamed') or col_str == '' or col_str.isdigit():
                    continue
                
                # Check if column has numeric data
                try:
                    col_data = pd.to_numeric(df[col], errors='coerce')
                    if not col_data.isna().all():
                        model_columns.append(str(col))
                except:
                    continue
            
            # Convert data to specified unit
            unit_factor = self.unit_factors.get(unit, 1)
            models_data = {}
            
            for model in model_columns:
                model_values = []
                for value in df[model]:
                    try:
                        num_value = float(value) if pd.notnull(value) else 0
                        # Convert from kWh base to target unit
                        converted_value = num_value / unit_factor
                        model_values.append(round(converted_value, 3))
                    except:
                        model_values.append(0)
                
                models_data[model] = model_values
            
            return {
                'sector': sector_name,
                'years': years,
                'models': model_columns,
                **models_data
            }
            
        except Exception as e:
            logger.warning(f"Error loading sector data from {file_path}: {e}")
            return None
    
    def get_comparison_data(self, scenario1: str, scenario2: str, filters: Dict = None) -> Dict[str, Any]:
        """Get data for scenario comparison with proper filtering"""
        try:
            filters = filters or {}
            
            # Get data for both scenarios with same filters
            data1 = self.get_scenario_data(scenario1, filters)
            data2 = self.get_scenario_data(scenario2, filters)
            
            if 'error' in data1 or 'error' in data2:
                return {
                    'error': f"Error loading comparison data: {data1.get('error', '')} {data2.get('error', '')}"
                }
            
            # Find common sectors and years
            common_sectors = set(data1['sector_list']) & set(data2['sector_list'])
            
            comparison_data = {
                'scenario1': {
                    'name': scenario1,
                    'sectors': {s: data1['sectors'][s] for s in common_sectors if s in data1['sectors']},
                    'year_range': data1['year_range']
                },
                'scenario2': {
                    'name': scenario2,
                    'sectors': {s: data2['sectors'][s] for s in common_sectors if s in data2['sectors']},
                    'year_range': data2['year_range']
                },
                'common_sectors': list(common_sectors),
                'filters_applied': filters,
                'unit': filters.get('unit', 'TWh')
            }
            
            return comparison_data
            
        except Exception as e:
            logger.exception(f"Error exporting scenario data: {e}")
            return {'error': str(e)}
    
    # ===== CHART GENERATION METHODS USING PLOT_UTILS =====
    
    def generate_sector_chart_data(self, scenario_name: str, sector_name: str, 
                                 chart_type: str = "line", filters: Dict = None) -> Dict[str, Any]:
        """Generate chart data for a specific sector using plot_utils"""
        try:
            # Get scenario data
            scenario_data = self.get_scenario_data(scenario_name, filters or {})
            if 'error' in scenario_data:
                return scenario_data
            
            if sector_name not in scenario_data['sectors']:
                return {'error': f'Sector {sector_name} not found'}
            
            sector_data = scenario_data['sectors'][sector_name]
            
            # Create DataFrame for plot_utils
            df_data = {'Year': sector_data['years']}
            for model in sector_data['models']:
                df_data[model] = sector_data.get(model, [])
            
            df = pd.DataFrame(df_data)
            
            # Generate chart using plot_utils
            chart_data = create_time_series_chart(
                df=df,
                x_column='Year',
                y_columns=sector_data['models'],
                chart_type=chart_type,
                title=f"{sector_name} Demand Forecast ({filters.get('unit', 'TWh')})"
            )
            
            return {
                'success': True,
                'chart_data': chart_data,
                'sector': sector_name,
                'models': sector_data['models'],
                'unit': filters.get('unit', 'TWh')
            }
            
        except Exception as e:
            logger.exception(f"Error generating sector chart data: {e}")
            return {'error': str(e)}
    
    def generate_sector_comparison_chart_data(self, scenario_name: str, sectors: List[str], 
                                            selected_models: Dict[str, str] = None,
                                            chart_type: str = "line", filters: Dict = None) -> Dict[str, Any]:
        """Generate chart data for comparing multiple sectors using plot_utils"""
        try:
            # Get scenario data
            scenario_data = self.get_scenario_data(scenario_name, filters or {})
            if 'error' in scenario_data:
                return scenario_data
            
            # Prepare data for comparison
            years = None
            sector_values = {}
            
            for sector in sectors:
                if sector not in scenario_data['sectors']:
                    continue
                
                sector_data = scenario_data['sectors'][sector]
                if years is None:
                    years = sector_data['years']
                
                # Use selected model or first available model
                if selected_models and sector in selected_models:
                    model = selected_models[sector]
                else:
                    model = sector_data['models'][0] if sector_data['models'] else None
                
                if model and model in sector_data:
                    sector_values[sector] = sector_data[model]
            
            if not sector_values or years is None:
                return {'error': 'No valid sector data found for comparison'}
            
            # Create DataFrame
            df_data = {'Year': years}
            df_data.update(sector_values)
            df = pd.DataFrame(df_data)
            
            # Generate chart using plot_utils
            chart_data = create_sector_comparison_chart(
                df=df,
                sectors=list(sector_values.keys()),
                year_column='Year',
                chart_type=chart_type,
                title=f"Sector Comparison ({filters.get('unit', 'TWh')})"
            )
            
            return {
                'success': True,
                'chart_data': chart_data,
                'sectors': list(sector_values.keys()),
                'selected_models': selected_models,
                'unit': filters.get('unit', 'TWh')
            }
            
        except Exception as e:
            logger.exception(f"Error generating sector comparison chart: {e}")
            return {'error': str(e)}
    
    def generate_model_comparison_chart_data(self, scenario_name: str, sector_name: str, 
                                           models: List[str] = None, filters: Dict = None) -> Dict[str, Any]:
        """Generate chart data for comparing different models using plot_utils"""
        try:
            # Get scenario data
            scenario_data = self.get_scenario_data(scenario_name, filters or {})
            if 'error' in scenario_data:
                return scenario_data
            
            if sector_name not in scenario_data['sectors']:
                return {'error': f'Sector {sector_name} not found'}
            
            sector_data = scenario_data['sectors'][sector_name]
            
            # Use specified models or all available models
            if models is None:
                models = sector_data['models']
            else:
                # Filter to only available models
                models = [m for m in models if m in sector_data['models']]
            
            if not models:
                return {'error': 'No valid models found for comparison'}
            
            # Prepare data for model comparison
            results_dict = {}
            for model in models:
                if model in sector_data:
                    results_dict[model] = sector_data[model]
            
            # Generate chart using plot_utils
            chart_data = create_model_comparison_chart(
                results_dict=results_dict,
                years=sector_data['years'],
                models=models,
                title=f"{sector_name} - Model Comparison ({filters.get('unit', 'TWh')})"
            )
            
            return {
                'success': True,
                'chart_data': chart_data,
                'sector': sector_name,
                'models': models,
                'unit': filters.get('unit', 'TWh')
            }
            
        except Exception as e:
            logger.exception(f"Error generating model comparison chart: {e}")
            return {'error': str(e)}
    
    def generate_consolidated_chart_data(self, scenario_name: str, chart_type: str = "stacked_bar", 
                                       filters: Dict = None) -> Dict[str, Any]:
        """Generate chart data for consolidated results using plot_utils"""
        try:
            # Get consolidated data
            consolidated_data = self.get_consolidated_results(scenario_name)
            if 'error' in consolidated_data:
                return consolidated_data
            
            if not consolidated_data.get('data'):
                return {'error': 'No consolidated data available'}
            
            # Convert to DataFrame
            df = pd.DataFrame(consolidated_data['data'])
            
            # Get sector columns (exclude Year, totals, and loss columns)
            exclude_cols = ['Year', 'Total_Gross_Demand', 'TD_Losses', 'Total_Net_Demand', 'Loss_Percentage']
            sector_columns = [col for col in df.columns if col not in exclude_cols]
            
            if chart_type == "stacked_bar":
                # Use stacked bar chart for sector breakdown
                # Convert DataFrame to dictionary format for stacked bar chart
                data_dict = {}
                for col in sector_columns:
                    data_dict[col] = df[col].tolist()
                
                labels = df['Year'].tolist()
                chart_data = plot_utils.create_stacked_bar_chart_data(
                    data_dict=data_dict,
                    labels=labels,
                    title=f"Consolidated Demand by Sector ({filters.get('unit', 'TWh')})"
                )
            else:
                # Use time series chart for trends
                chart_data = create_time_series_chart(
                    df=df,
                    x_column='Year',
                    y_columns=['Total_Gross_Demand', 'Total_Net_Demand'],
                    chart_type=chart_type,
                    title=f"Total Demand Trends ({filters.get('unit', 'TWh')})"
                )
            
            return {
                'success': True,
                'chart_data': chart_data,
                'sectors': sector_columns,
                'unit': filters.get('unit', 'TWh'),
                'chart_type': chart_type
            }
            
        except Exception as e:
            logger.exception(f"Error generating consolidated chart data: {e}")
            return {'error': str(e)}
    
    def generate_td_losses_chart_data(self, scenario_name: str, filters: Dict = None) -> Dict[str, Any]:
        """Generate chart data for T&D losses visualization using plot_utils"""
        try:
            # Get T&D losses data
            td_data = self.get_td_losses(scenario_name)
            if 'error' in td_data:
                return td_data
            
            if not td_data.get('td_losses'):
                return {'error': 'No T&D losses data available'}
            
            # Generate chart using specialized T&D losses chart function
            from utils.plot_utils import create_td_losses_chart
            
            chart_data = create_td_losses_chart(
                td_losses_data=td_data['td_losses'],
                title="T&D Losses Configuration"
            )
            
            return {
                'success': True,
                'chart_data': chart_data,
                'td_losses': td_data['td_losses']
            }
            
        except Exception as e:
            logger.exception(f"Error generating T&D losses chart data: {e}")
            return {'error': str(e)}
    
    def save_model_selection(self, scenario_name: str, model_config: Dict[str, str]) -> Dict[str, Any]:
        """Save model selection configuration"""
        try:
            scenario_path = os.path.join(self.results_path, scenario_name)
            os.makedirs(scenario_path, exist_ok=True)
            
            config = {
                'scenario_name': scenario_name,
                'model_selection': model_config,
                'saved_at': datetime.now().isoformat(),
                'saved_by': 'demand_visualization_service'
            }
            
            config_path = os.path.join(scenario_path, 'model_selection.json')
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"Saved model selection for scenario {scenario_name}")
            return {'success': True, 'message': 'Model selection saved successfully'}
            
        except Exception as e:
            logger.exception(f"Error saving model selection: {e}")
            return {'error': str(e)}
    
    def get_model_selection(self, scenario_name: str) -> Dict[str, Any]:
        """Get saved model selection configuration"""
        try:
            config_path = os.path.join(self.results_path, scenario_name, 'model_selection.json')
            
            if not os.path.exists(config_path):
                return {'model_selection': {}, 'message': 'No saved configuration found'}
            
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            return {
                'model_selection': config.get('model_selection', {}),
                'saved_at': config.get('saved_at'),
                'success': True
            }
            
        except Exception as e:
            logger.exception(f"Error getting model selection: {e}")
            return {'error': str(e)}
    
    def save_td_losses(self, scenario_name: str, td_losses: List[Dict]) -> Dict[str, Any]:
        """Save T&D losses configuration"""
        try:
            # Validate and clean T&D losses data
            validated_losses = []
            for loss in td_losses:
                try:
                    year = int(loss.get('year', 0))
                    loss_pct = float(loss.get('loss_percentage', 0))
                    
                    if year > 0 and 0 <= loss_pct <= 100:
                        validated_losses.append({
                            'year': year,
                            'loss_percentage': round(loss_pct, 2)
                        })
                except:
                    continue
            
            # Sort by year
            validated_losses.sort(key=lambda x: x['year'])
            
            scenario_path = os.path.join(self.results_path, scenario_name)
            os.makedirs(scenario_path, exist_ok=True)
            
            config = {
                'scenario_name': scenario_name,
                'td_losses': validated_losses,
                'saved_at': datetime.now().isoformat()
            }
            
            config_path = os.path.join(scenario_path, 'td_losses.json')
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"Saved T&D losses configuration for scenario {scenario_name}")
            return {'success': True, 'message': 'T&D losses saved successfully'}
            
        except Exception as e:
            logger.exception(f"Error saving T&D losses: {e}")
            return {'error': str(e)}
    
    def get_td_losses(self, scenario_name: str) -> Dict[str, Any]:
        """Get saved T&D losses configuration"""
        try:
            config_path = os.path.join(self.results_path, scenario_name, 'td_losses.json')
            
            if not os.path.exists(config_path):
                return {'td_losses': [], 'message': 'No saved T&D losses found'}
            
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            return {
                'td_losses': config.get('td_losses', []),
                'saved_at': config.get('saved_at'),
                'success': True
            }
            
        except Exception as e:
            logger.exception(f"Error getting T&D losses: {e}")
            return {'error': str(e)}
    
    def generate_consolidated_results(self, scenario_name: str, model_selection: Dict[str, str], 
                                    td_losses: List[Dict], filters: Dict = None) -> Dict[str, Any]:
        """Generate consolidated results with T&D losses"""
        try:
            filters = filters or {}
            unit = filters.get('unit', 'TWh')
            start_year = filters.get('start_year', 2025)
            end_year = filters.get('end_year', 2037)
            
            # Get scenario data
            scenario_data = self.get_scenario_data(scenario_name, {
                'unit': 'kWh',  # Use base unit for calculations
                'start_year': start_year,
                'end_year': end_year
            })
            
            if 'error' in scenario_data:
                return scenario_data
            
            years = list(range(start_year, end_year + 1))
            consolidated_data = []
            
            # Interpolate T&D losses
            td_losses_interpolated = self._interpolate_td_losses(td_losses, years)
            
            for year in years:
                year_data = {'Year': year}
                total_gross_demand = 0
                
                # Sum demands from selected models
                for sector, selected_model in model_selection.items():
                    if sector in scenario_data['sectors']:
                        sector_data = scenario_data['sectors'][sector]
                        
                        demand_value = 0
                        if year in sector_data['years']:
                            year_index = sector_data['years'].index(year)
                            if selected_model in sector_data and year_index < len(sector_data[selected_model]):
                                demand_value = sector_data[selected_model][year_index]
                        
                        # Convert from kWh to target unit
                        unit_factor = self.unit_factors.get(unit, 1)
                        converted_demand = demand_value / unit_factor
                        
                        year_data[sector] = round(converted_demand, 3)
                        total_gross_demand += converted_demand
                
                # Calculate T&D losses
                loss_percentage = td_losses_interpolated.get(year, 0)
                loss_fraction = loss_percentage / 100
                
                if loss_fraction < 1:
                    on_grid_demand = total_gross_demand / (1 - loss_fraction)
                    td_loss_amount = on_grid_demand - total_gross_demand
                else:
                    on_grid_demand = total_gross_demand
                    td_loss_amount = 0
                
                year_data.update({
                    'Total_Gross_Demand': round(total_gross_demand, 3),
                    'TD_Losses': round(max(0, td_loss_amount), 3),
                    'Total_Net_Demand': round(max(0, on_grid_demand), 3),
                    'Loss_Percentage': round(loss_percentage, 2)
                })
                
                consolidated_data.append(year_data)
            
            # Save consolidated results
            self._save_consolidated_results(scenario_name, consolidated_data, {
                'model_selection': model_selection,
                'td_losses': td_losses,
                'filters': filters
            })
            
            return {
                'success': True,
                'consolidated_data': consolidated_data,
                'metadata': {
                    'scenario_name': scenario_name,
                    'unit': unit,
                    'year_range': {'start': start_year, 'end': end_year},
                    'total_years': len(years),
                    'total_sectors': len(model_selection)
                }
            }
            
        except Exception as e:
            logger.exception(f"Error generating consolidated results: {e}")
            return {'error': str(e)}
    
    def _interpolate_td_losses(self, td_losses: List[Dict], years: List[int]) -> Dict[int, float]:
        """Interpolate T&D losses for given years"""
        if not td_losses:
            return {year: 0 for year in years}
        
        # Sort by year
        sorted_losses = sorted(td_losses, key=lambda x: x['year'])
        interpolated = {}
        
        for year in years:
            if year <= sorted_losses[0]['year']:
                interpolated[year] = sorted_losses[0]['loss_percentage']
            elif year >= sorted_losses[-1]['year']:
                interpolated[year] = sorted_losses[-1]['loss_percentage']
            else:
                # Linear interpolation
                for i in range(len(sorted_losses) - 1):
                    if sorted_losses[i]['year'] <= year <= sorted_losses[i + 1]['year']:
                        x1, y1 = sorted_losses[i]['year'], sorted_losses[i]['loss_percentage']
                        x2, y2 = sorted_losses[i + 1]['year'], sorted_losses[i + 1]['loss_percentage']
                        
                        # Linear interpolation formula
                        slope = (y2 - y1) / (x2 - x1)
                        interpolated[year] = y1 + slope * (year - x1)
                        break
        
        return interpolated
    
    def _save_consolidated_results(self, scenario_name: str, consolidated_data: List[Dict], metadata: Dict):
        """Save consolidated results to files"""
        try:
            scenario_path = os.path.join(self.results_path, scenario_name)
            os.makedirs(scenario_path, exist_ok=True)
            
            # Save CSV
            df = pd.DataFrame(consolidated_data)
            csv_path = os.path.join(scenario_path, 'consolidated_results.csv')
            df.to_csv(csv_path, index=False)
            
            # Save metadata
            metadata_with_info = {
                **metadata,
                'generated_at': datetime.now().isoformat(),
                'csv_file': 'consolidated_results.csv',
                'total_records': len(consolidated_data)
            }
            
            metadata_path = os.path.join(scenario_path, 'consolidated_metadata.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata_with_info, f, indent=2)
            
            logger.info(f"Saved consolidated results for scenario {scenario_name}")
            
        except Exception as e:
            logger.warning(f"Error saving consolidated results: {e}")
    
    def export_data(self, scenario_name: str, data_type: str = 'consolidated', 
                   filters: Dict = None) -> str:
        """Export data to CSV file"""
        try:
            scenario_path = os.path.join(self.results_path, scenario_name)
            
            if data_type == 'consolidated':
                csv_path = os.path.join(scenario_path, 'consolidated_results.csv')
                if os.path.exists(csv_path):
                    return csv_path
                else:
                    raise FileNotFoundError("No consolidated results found. Please generate first.")
            
            elif data_type == 'scenario':
                # Export scenario data
                scenario_data = self.get_scenario_data(scenario_name, filters)
                if 'error' in scenario_data:
                    raise ValueError(scenario_data['error'])
                
                # Create export DataFrame
                export_data = []
                for sector, data in scenario_data['sectors'].items():
                    for i, year in enumerate(data['years']):
                        row = {'Sector': sector, 'Year': year}
                        for model in data['models']:
                            if model in data and i < len(data[model]):
                                row[model] = data[model][i]
                        export_data.append(row)
                
                df = pd.DataFrame(export_data)
                
                # Save export file
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{scenario_name}_export_{timestamp}.csv"
                csv_path = os.path.join(scenario_path, filename)
                df.to_csv(csv_path, index=False)
                
                return csv_path
            
            else:
                raise ValueError(f"Unknown data type: {data_type}")
                
        except Exception as e:
            logger.exception(f"Error exporting data: {e}")
            raise
    
    def get_analysis_summary(self, scenario_name: str, filters: Dict = None) -> Dict[str, Any]:
        """Get comprehensive analysis summary"""
        try:
            scenario_data = self.get_scenario_data(scenario_name, filters)
            if 'error' in scenario_data:
                return scenario_data
            
            summary = {
                'scenario_name': scenario_name,
                'total_sectors': len(scenario_data['sectors']),
                'year_range': scenario_data['year_range'],
                'available_models': scenario_data['available_models'],
                'unit': scenario_data['unit'],
                'sector_analysis': {},
                'overall_trends': {}
            }
            
            # Analyze each sector
            for sector, data in scenario_data['sectors'].items():
                sector_summary = {
                    'models_count': len(data['models']),
                    'years_count': len(data['years']),
                    'model_ranges': {}
                }
                
                # Calculate ranges for each model
                for model in data['models']:
                    if model in data:
                        values = [v for v in data[model] if v > 0]
                        if values:
                            sector_summary['model_ranges'][model] = {
                                'min': round(min(values), 3),
                                'max': round(max(values), 3),
                                'avg': round(sum(values) / len(values), 3)
                            }
                
                summary['sector_analysis'][sector] = sector_summary
            
            # Overall trends analysis
            all_values = []
            for sector_data in scenario_data['sectors'].values():
                for model in sector_data['models']:
                    if model in sector_data:
                        all_values.extend([v for v in sector_data[model] if v > 0])
            
            if all_values:
                summary['overall_trends'] = {
                    'total_data_points': len(all_values),
                    'overall_min': round(min(all_values), 3),
                    'overall_max': round(max(all_values), 3),
                    'overall_avg': round(sum(all_values) / len(all_values), 3)
                }
            
            return summary
            
        except Exception as e:
            logger.exception(f"Error getting analysis summary: {e}")
            return {'error': str(e)}