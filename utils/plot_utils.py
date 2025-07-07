"""
Plotting Utilities for Energy Platform
Reusable plotting functions with consistent styling and color management
"""

import json
import logging
from typing import Dict, List, Optional, Union, Any
import pandas as pd
from utils.color_manager import color_manager

logger = logging.getLogger(__name__)

class PlotUtils:
    """
    Centralized plotting utilities for consistent chart creation across the application
    """
    
    def __init__(self):
        self.default_config = self._get_default_chart_config()
    
    def _get_default_chart_config(self) -> Dict:
        """Get enhanced default chart configuration with improved styling"""
        return {
            "responsive": True,
            "maintainAspectRatio": False,
            "interaction": {
                "intersect": False,
                "mode": "index"
            },
            "animation": {
                "duration": 750,
                "easing": "easeInOutQuart"
            },
            "plugins": {
                "legend": {
                    "position": "bottom",
                    "align": "center",
                    "labels": {
                        "usePointStyle": True,
                        "pointStyle": "circle",
                        "padding": 20,
                        "boxWidth": 12,
                        "boxHeight": 12,
                        "font": {
                            "size": 13,
                            "family": "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
                            "weight": "500"
                        },
                        "color": "#374151",
                        "generateLabels": "function(chart) { return Chart.defaults.plugins.legend.labels.generateLabels(chart).map(label => { label.fillStyle = label.strokeStyle; return label; }); }"
                    }
                },
                "tooltip": {
                    "enabled": True,
                    "backgroundColor": "rgba(17, 24, 39, 0.95)",
                    "titleColor": "#F9FAFB",
                    "bodyColor": "#F3F4F6",
                    "borderColor": "rgba(75, 85, 99, 0.3)",
                    "borderWidth": 1,
                    "cornerRadius": 12,
                    "displayColors": True,
                    "padding": 12,
                    "titleFont": {
                        "size": 14,
                        "family": "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
                        "weight": "600"
                    },
                    "bodyFont": {
                        "size": 13,
                        "family": "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
                        "weight": "400"
                    },
                    "footerFont": {
                        "size": 12,
                        "family": "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
                        "weight": "400"
                    },
                    "caretSize": 8,
                    "caretPadding": 10,
                    "multiKeyBackground": "rgba(17, 24, 39, 0.8)"
                }
            },
            "scales": {
                "x": {
                    "grid": {
                        "color": "rgba(229, 231, 235, 0.8)",
                        "drawBorder": False,
                        "lineWidth": 1
                    },
                    "border": {
                        "display": False
                    },
                    "ticks": {
                        "color": "#6B7280",
                        "padding": 8,
                        "font": {
                            "size": 12,
                            "family": "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
                            "weight": "500"
                        },
                        "maxRotation": 45,
                        "minRotation": 0
                    },
                    "title": {
                        "color": "#374151",
                        "font": {
                            "size": 13,
                            "family": "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
                            "weight": "600"
                        },
                        "padding": 16
                    }
                },
                "y": {
                    "grid": {
                        "color": "rgba(229, 231, 235, 0.8)",
                        "drawBorder": False,
                        "lineWidth": 1
                    },
                    "border": {
                        "display": False
                    },
                    "ticks": {
                        "color": "#6B7280",
                        "padding": 8,
                        "font": {
                            "size": 12,
                            "family": "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
                            "weight": "500"
                        },
                        "callback": "function(value) { return typeof value === 'number' ? value.toLocaleString() : value; }"
                    },
                    "title": {
                        "color": "#374151",
                        "font": {
                            "size": 13,
                            "family": "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
                            "weight": "600"
                        },
                        "padding": 16
                    }
                }
            },
            "elements": {
                "point": {
                    "radius": 5,
                    "hoverRadius": 8,
                    "borderWidth": 2,
                    "hoverBorderWidth": 3,
                    "backgroundColor": "#FFFFFF",
                    "borderColor": "inherit"
                },
                "line": {
                    "borderWidth": 3,
                    "tension": 0.2,
                    "borderCapStyle": "round",
                    "borderJoinStyle": "round"
                },
                "bar": {
                    "borderWidth": 0,
                    "borderRadius": 4,
                    "borderSkipped": False
                }
            },
            "layout": {
                "padding": {
                    "top": 20,
                    "right": 20,
                    "bottom": 20,
                    "left": 20
                }
            }
        }
    
    def create_time_series_chart_data(self, 
                                    df: pd.DataFrame, 
                                    x_column: str, 
                                    y_columns: Union[str, List[str]], 
                                    chart_type: str = "line",
                                    title: str = "",
                                    colors: Optional[Dict[str, str]] = None) -> Dict:
        """
        Create chart data for time series visualization
        
        Args:
            df: DataFrame with data
            x_column: Column name for x-axis (usually time/year)
            y_columns: Column name(s) for y-axis data
            chart_type: Type of chart (line, area, bar)
            title: Chart title
            colors: Custom colors for series
        
        Returns:
            Dictionary with Chart.js compatible data structure
        """
        try:
            if isinstance(y_columns, str):
                y_columns = [y_columns]
            
            # Prepare labels (x-axis values)
            labels = df[x_column].tolist()
            
            # Get colors for datasets
            if not colors:
                colors = color_manager.get_chart_colors(len(y_columns))
                color_dict = {col: colors[i] for i, col in enumerate(y_columns)}
            else:
                color_dict = colors
            
            # Create datasets
            datasets = []
            for i, column in enumerate(y_columns):
                if column not in df.columns:
                    logger.warning(f"Column '{column}' not found in DataFrame")
                    continue
                
                color = color_dict.get(column, color_manager.get_chart_colors(1)[0])
                
                dataset = {
                    "label": column.replace('_', ' ').title(),
                    "data": df[column].fillna(0).tolist(),
                    "borderColor": color,
                    "backgroundColor": self._add_transparency(color, 0.1),
                    "fill": chart_type == "area",
                    "tension": 0.2 if chart_type in ["line", "area"] else 0,
                    "pointBackgroundColor": "#FFFFFF",
                    "pointBorderColor": color,
                    "pointBorderWidth": 2,
                    "pointRadius": 4,
                    "pointHoverRadius": 6,
                    "pointHoverBackgroundColor": color,
                    "pointHoverBorderColor": "#FFFFFF",
                    "pointHoverBorderWidth": 2
                }
                
                # Chart type specific styling
                if chart_type == "area":
                    dataset["backgroundColor"] = self._add_transparency(color, 0.25)
                    dataset["borderWidth"] = 3
                    dataset["fill"] = "origin"
                    dataset["tension"] = 0.4  # Smoother curves for area charts
                elif chart_type == "bar":
                    dataset["backgroundColor"] = self._add_transparency(color, 0.8)
                    dataset["borderColor"] = self._darken_color(color, 0.1)
                    dataset["borderWidth"] = 1
                    dataset["borderRadius"] = 4
                    dataset["borderSkipped"] = False
                    # Remove point styling for bars
                    for key in list(dataset.keys()):
                        if key.startswith('point'):
                            del dataset[key]
                else:  # line chart
                    dataset["borderWidth"] = 3
                    dataset["backgroundColor"] = self._add_transparency(color, 0.05)
                
                datasets.append(dataset)
            
            # Create chart configuration
            config = self._create_chart_config(chart_type, title, labels, datasets)
            
            return {
                "type": chart_type,
                "data": {
                    "labels": labels,
                    "datasets": datasets
                },
                "options": config["options"],
                "title": title,
                "chart_id": f"chart_{hash(str(labels))}"
            }
            
        except Exception as e:
            logger.error(f"Error creating time series chart data: {e}")
            return self._create_error_chart_data(str(e))
    
    def create_sector_comparison_chart_data(self, 
                                          df: pd.DataFrame, 
                                          sectors: List[str], 
                                          year_column: str = "Year",
                                          chart_type: str = "line",
                                          title: str = "Sector Comparison") -> Dict:
        """
        Create chart data for sector comparison
        
        Args:
            df: DataFrame with sector data
            sectors: List of sector names (column names in df)
            year_column: Column name for years
            chart_type: Type of chart
            title: Chart title
        
        Returns:
            Chart data dictionary
        """
        try:
            # Get sector colors
            sector_colors = color_manager.get_sector_colors(sectors)
            
            return self.create_time_series_chart_data(
                df=df,
                x_column=year_column,
                y_columns=sectors,
                chart_type=chart_type,
                title=title,
                colors=sector_colors
            )
            
        except Exception as e:
            logger.error(f"Error creating sector comparison chart: {e}")
            return self._create_error_chart_data(str(e))
    
    def create_model_comparison_chart_data(self, 
                                         results_dict: Dict[str, List], 
                                         years: List[int],
                                         models: List[str],
                                         title: str = "Model Comparison") -> Dict:
        """
        Create chart data for model comparison
        
        Args:
            results_dict: Dictionary with model names as keys and results as values
            years: List of years for x-axis
            models: List of model names
            title: Chart title
        
        Returns:
            Chart data dictionary
        """
        try:
            # Get model colors
            model_colors = color_manager.get_model_colors(models)
            
            datasets = []
            for model in models:
                if model not in results_dict:
                    continue
                
                color = model_colors.get(model, color_manager.get_chart_colors(1)[0])
                
                dataset = {
                    "label": model,
                    "data": results_dict[model],
                    "borderColor": color,
                    "backgroundColor": self._add_transparency(color, 0.05),
                    "borderWidth": 3,
                    "tension": 0.2,
                    "pointRadius": 5,
                    "pointHoverRadius": 8,
                    "pointBackgroundColor": "#FFFFFF",
                    "pointBorderColor": color,
                    "pointBorderWidth": 2,
                    "pointHoverBackgroundColor": color,
                    "pointHoverBorderColor": "#FFFFFF",
                    "pointHoverBorderWidth": 3,
                    "fill": False
                }
                
                datasets.append(dataset)
            
            config = self._create_chart_config("line", title, years, datasets)
            
            return {
                "type": "line",
                "data": {
                    "labels": years,
                    "datasets": datasets
                },
                "options": config["options"],
                "title": title,
                "chart_id": f"model_comparison_{hash(str(years))}"
            }
            
        except Exception as e:
            logger.error(f"Error creating model comparison chart: {e}")
            return self._create_error_chart_data(str(e))
    
    def create_stacked_bar_chart_data(self, 
                                    df: pd.DataFrame, 
                                    x_column: str, 
                                    y_columns: List[str],
                                    title: str = "Stacked Bar Chart",
                                    colors: Optional[Dict[str, str]] = None) -> Dict:
        """
        Create stacked bar chart data
        
        Args:
            df: DataFrame with data
            x_column: Column for x-axis
            y_columns: Columns for stacking
            title: Chart title
            colors: Custom colors
        
        Returns:
            Chart data dictionary
        """
        try:
            labels = df[x_column].tolist()
            
            if not colors:
                colors = color_manager.get_chart_colors(len(y_columns))
                color_dict = {col: colors[i] for i, col in enumerate(y_columns)}
            else:
                color_dict = colors
            
            datasets = []
            for column in y_columns:
                if column not in df.columns:
                    continue
                
                color = color_dict.get(column, color_manager.get_chart_colors(1)[0])
                
                dataset = {
                    "label": column.replace('_', ' ').title(),
                    "data": df[column].fillna(0).tolist(),
                    "backgroundColor": self._add_transparency(color, 0.8),
                    "borderColor": self._darken_color(color, 0.1),
                    "borderWidth": 1,
                    "borderRadius": 6,
                    "borderSkipped": False,
                    "hoverBackgroundColor": self._add_transparency(color, 0.9),
                    "hoverBorderColor": self._darken_color(color, 0.2),
                    "hoverBorderWidth": 2
                }
                
                datasets.append(dataset)
            
            # Stacked bar configuration
            options = self.default_config.copy()
            options["scales"]["x"]["stacked"] = True
            options["scales"]["y"]["stacked"] = True
            options["scales"]["y"]["beginAtZero"] = True
            
            return {
                "type": "bar",
                "data": {
                    "labels": labels,
                    "datasets": datasets
                },
                "options": options,
                "title": title,
                "chart_id": f"stacked_bar_{hash(str(labels))}"
            }
            
        except Exception as e:
            logger.error(f"Error creating stacked bar chart: {e}")
            return self._create_error_chart_data(str(e))
    
    def create_pie_chart_data(self, 
                            data: Dict[str, float], 
                            title: str = "Pie Chart",
                            colors: Optional[List[str]] = None) -> Dict:
        """
        Create pie chart data
        
        Args:
            data: Dictionary with labels and values
            title: Chart title
            colors: Custom colors
        
        Returns:
            Chart data dictionary
        """
        try:
            labels = list(data.keys())
            values = list(data.values())
            
            if not colors:
                colors = color_manager.get_chart_colors(len(labels))
            
            dataset = {
                "data": values,
                "backgroundColor": colors[:len(labels)],
                "borderColor": "#FFFFFF",
                "borderWidth": 2
            }
            
            options = {
                "responsive": True,
                "maintainAspectRatio": False,
                "plugins": {
                    "legend": {
                        "position": "right",
                        "labels": {
                            "usePointStyle": True,
                            "padding": 15,
                            "font": {
                                "size": 12,
                                "family": "'Inter', sans-serif"
                            }
                        }
                    },
                    "tooltip": {
                        "callbacks": {
                            "label": "function(context) { return context.label + ': ' + context.parsed.toLocaleString(); }"
                        }
                    }
                }
            }
            
            return {
                "type": "pie",
                "data": {
                    "labels": labels,
                    "datasets": [dataset]
                },
                "options": options,
                "title": title,
                "chart_id": f"pie_{hash(str(labels))}"
            }
            
        except Exception as e:
            logger.error(f"Error creating pie chart: {e}")
            return self._create_error_chart_data(str(e))
    
    def create_correlation_heatmap_data(self, 
                                      correlation_matrix: pd.DataFrame,
                                      title: str = "Correlation Matrix") -> Dict:
        """
        Create correlation heatmap data (for use with Chart.js Matrix chart or similar)
        
        Args:
            correlation_matrix: Pandas DataFrame with correlation values
            title: Chart title
        
        Returns:
            Chart data dictionary
        """
        try:
            # Convert correlation matrix to format suitable for heatmap
            data = []
            variables = correlation_matrix.columns.tolist()
            
            for i, var1 in enumerate(variables):
                for j, var2 in enumerate(variables):
                    correlation = correlation_matrix.loc[var1, var2]
                    
                    # Color based on correlation strength
                    if correlation >= 0.7:
                        color = color_manager.get_color("status", "success")
                    elif correlation >= 0.4:
                        color = color_manager.get_color("charts", "primary")
                    elif correlation >= -0.4:
                        color = color_manager.get_color("status", "warning")
                    else:
                        color = color_manager.get_color("status", "error")
                    
                    data.append({
                        "x": j,
                        "y": i,
                        "v": round(correlation, 3),
                        "variable1": var1,
                        "variable2": var2,
                        "color": color
                    })
            
            return {
                "type": "heatmap",
                "data": data,
                "variables": variables,
                "title": title,
                "chart_id": f"heatmap_{hash(str(variables))}"
            }
            
        except Exception as e:
            logger.error(f"Error creating correlation heatmap: {e}")
            return self._create_error_chart_data(str(e))
    
    def _create_chart_config(self, chart_type: str, title: str, labels: List, datasets: List) -> Dict:
        """Create enhanced chart configuration based on type"""
        config = self.default_config.copy()
        
        # Add enhanced title if provided
        if title:
            config["plugins"]["title"] = {
                "display": True,
                "text": title,
                "font": {
                    "size": 18,
                    "weight": "700",
                    "family": "'Inter', -apple-system, BlinkMacSystemFont, sans-serif"
                },
                "padding": {
                    "top": 10,
                    "bottom": 25
                },
                "color": "#111827",
                "align": "center"
            }
        
        # Chart type specific configurations
        if chart_type in ["area", "line"]:
            config["scales"]["y"]["beginAtZero"] = True
            config["scales"]["y"]["grace"] = "5%"  # Add some padding at top
            
            if chart_type == "area":
                config["elements"]["line"]["fill"] = True
                config["interaction"]["intersect"] = False
                config["plugins"]["filler"] = {
                    "propagate": False
                }
        
        elif chart_type == "bar":
            config["scales"]["y"]["beginAtZero"] = True
            config["scales"]["y"]["grace"] = "5%"
            config["plugins"]["legend"]["display"] = len(datasets) > 1
            config["elements"]["bar"]["borderRadius"] = 6
            config["elements"]["bar"]["borderSkipped"] = False
            
            # Adjust bar thickness based on data points
            if len(labels) <= 5:
                config["scales"]["x"]["categoryPercentage"] = 0.6
                config["scales"]["x"]["barPercentage"] = 0.8
            elif len(labels) <= 10:
                config["scales"]["x"]["categoryPercentage"] = 0.7
                config["scales"]["x"]["barPercentage"] = 0.9
            else:
                config["scales"]["x"]["categoryPercentage"] = 0.8
                config["scales"]["x"]["barPercentage"] = 0.95
        
        # Enhanced tooltip formatting
        config["plugins"]["tooltip"]["callbacks"] = {
            "title": "function(context) { return context[0].label; }",
            "label": "function(context) { const label = context.dataset.label || ''; const value = typeof context.parsed.y === 'number' ? context.parsed.y.toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 2}) : context.parsed.y; return label + ': ' + value; }",
            "footer": "function(tooltipItems) { if (tooltipItems.length > 1) { const total = tooltipItems.reduce((sum, item) => sum + (item.parsed.y || 0), 0); return 'Total: ' + total.toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 2}); } return ''; }"
        }
        
        # Add hover effects
        config["onHover"] = "function(event, activeElements) { event.native.target.style.cursor = activeElements.length > 0 ? 'pointer' : 'default'; }"
        
        return {"options": config}
    
    def _add_transparency(self, hex_color: str, alpha: float) -> str:
        """Add transparency to hex color"""
        try:
            # Remove # if present
            hex_color = hex_color.lstrip('#')
            
            # Convert to RGB
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            
            return f"rgba({r}, {g}, {b}, {alpha})"
        except Exception:
            return f"rgba(59, 130, 246, {alpha})"  # Default blue with transparency
    
    def _darken_color(self, hex_color: str, factor: float) -> str:
        """Darken a hex color by a factor"""
        try:
            hex_color = hex_color.lstrip('#')
            
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            
            r = max(0, int(r * (1 - factor)))
            g = max(0, int(g * (1 - factor)))
            b = max(0, int(b * (1 - factor)))
            
            return f"#{r:02X}{g:02X}{b:02X}"
        except Exception:
            return "#1D4ED8"  # Default dark blue
    
    def _create_error_chart_data(self, error_message: str) -> Dict:
        """Create error chart data for display"""
        return {
            "type": "line",
            "data": {
                "labels": ["Error"],
                "datasets": [{
                    "label": "Error",
                    "data": [0],
                    "borderColor": "#EF4444",
                    "backgroundColor": "rgba(239, 68, 68, 0.1)"
                }]
            },
            "options": {
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"Chart Error: {error_message}"
                    }
                }
            }
         }
    
    def _add_transparency(self, color: str, alpha: float = 0.3) -> str:
        """Add transparency to a color"""
        try:
            # Handle hex colors
            if color.startswith('#'):
                hex_color = color.lstrip('#')
                if len(hex_color) == 6:
                    r = int(hex_color[0:2], 16)
                    g = int(hex_color[2:4], 16)
                    b = int(hex_color[4:6], 16)
                    return f"rgba({r}, {g}, {b}, {alpha})"
            
            # Handle rgba colors
            if color.startswith('rgba'):
                return color
            
            # Handle rgb colors
            if color.startswith('rgb'):
                rgb_values = color.replace('rgb(', '').replace(')', '').split(',')
                r, g, b = [int(x.strip()) for x in rgb_values]
                return f"rgba({r}, {g}, {b}, {alpha})"
            
            # Fallback
            return f"rgba(99, 102, 241, {alpha})"
            
        except Exception:
            return f"rgba(99, 102, 241, {alpha})"
    
    def create_td_losses_chart_data(self, 
                                   td_losses_data: List[Dict],
                                   title: str = "T&D Losses Configuration") -> Dict:
        """
        Create T&D losses chart data with configured points and interpolation
        
        Args:
            td_losses_data: List of T&D losses configuration data
            title: Chart title
        
        Returns:
            Chart data dictionary
        """
        try:
            if not td_losses_data:
                return self._create_error_chart_data("No T&D losses data available")
            
            # Sort data by year
            sorted_data = sorted(td_losses_data, key=lambda x: x.get('year', 0))
            
            # Extract configured points
            configured_years = [item['year'] for item in sorted_data]
            configured_losses = [item['loss_percentage'] for item in sorted_data]
            
            # Create interpolated data for smooth line (if more than one point)
            if len(configured_years) > 1:
                # Generate interpolated years
                min_year = min(configured_years)
                max_year = max(configured_years)
                interpolated_years = list(range(min_year, max_year + 1))
                
                # Linear interpolation
                interpolated_losses = []
                for year in interpolated_years:
                    if year in configured_years:
                        # Use configured value
                        idx = configured_years.index(year)
                        interpolated_losses.append(configured_losses[idx])
                    else:
                        # Interpolate between nearest points
                        lower_years = [y for y in configured_years if y < year]
                        upper_years = [y for y in configured_years if y > year]
                        
                        if lower_years and upper_years:
                            lower_year = max(lower_years)
                            upper_year = min(upper_years)
                            lower_idx = configured_years.index(lower_year)
                            upper_idx = configured_years.index(upper_year)
                            
                            # Linear interpolation formula
                            ratio = (year - lower_year) / (upper_year - lower_year)
                            interpolated_value = (configured_losses[lower_idx] + 
                                                ratio * (configured_losses[upper_idx] - configured_losses[lower_idx]))
                            interpolated_losses.append(round(interpolated_value, 2))
                        else:
                            interpolated_losses.append(0)
            else:
                interpolated_years = configured_years
                interpolated_losses = configured_losses
            
            # Create datasets
            datasets = []
            
            # Interpolated line dataset
            line_color = color_manager.get_color("status", "info")
            datasets.append({
                "label": "T&D Losses (%)",
                "data": interpolated_losses,
                "borderColor": line_color,
                "backgroundColor": self._add_transparency(line_color, 0.1),
                "borderWidth": 2,
                "fill": True,
                "tension": 0.4,
                "pointRadius": 0,
                "pointHoverRadius": 0
            })
            
            # Configured points dataset
            point_color = color_manager.get_color("status", "error")
            configured_data = [None] * len(interpolated_years)
            for i, year in enumerate(interpolated_years):
                if year in configured_years:
                    idx = configured_years.index(year)
                    configured_data[i] = configured_losses[idx]
            
            datasets.append({
                "label": "Configured Points",
                "data": configured_data,
                "borderColor": point_color,
                "backgroundColor": point_color,
                "borderWidth": 2,
                "pointRadius": 6,
                "pointHoverRadius": 8,
                "showLine": False,
                "fill": False
            })
            
            # Chart configuration
            options = self.default_config.copy()
            options["scales"]["y"]["beginAtZero"] = True
            options["scales"]["y"]["title"] = {
                "display": True,
                "text": "Loss Percentage (%)"
            }
            options["scales"]["x"]["title"] = {
                "display": True,
                "text": "Year"
            }
            
            return {
                "type": "line",
                "data": {
                    "labels": interpolated_years,
                    "datasets": datasets
                },
                "options": options,
                "title": title,
                "chart_id": f"td_losses_{hash(str(configured_years))}"
            }
            
        except Exception as e:
            logger.error(f"Error creating T&D losses chart: {e}")
            return self._create_error_chart_data(str(e))
    
    def get_responsive_chart_config(self, container_width: int = 800, container_height: int = 400) -> Dict:
        """Get enhanced responsive chart configuration based on container dimensions"""
        config = self.default_config.copy()
        
        # Mobile devices (< 480px)
        if container_width < 480:
            config["plugins"]["legend"]["position"] = "bottom"
            config["plugins"]["legend"]["labels"]["font"]["size"] = 10
            config["plugins"]["legend"]["labels"]["padding"] = 12
            config["plugins"]["legend"]["labels"]["boxWidth"] = 10
            config["plugins"]["title"]["font"]["size"] = 14
            config["plugins"]["title"]["padding"] = {"top": 8, "bottom": 15}
            config["scales"]["x"]["ticks"]["font"]["size"] = 9
            config["scales"]["x"]["ticks"]["maxRotation"] = 45
            config["scales"]["y"]["ticks"]["font"]["size"] = 9
            config["elements"]["point"]["radius"] = 3
            config["elements"]["point"]["hoverRadius"] = 5
            config["elements"]["line"]["borderWidth"] = 2
            config["layout"]["padding"] = {"top": 10, "right": 10, "bottom": 10, "left": 10}
            
        # Tablet devices (480px - 768px)
        elif container_width < 768:
            config["plugins"]["legend"]["labels"]["font"]["size"] = 11
            config["plugins"]["legend"]["labels"]["padding"] = 15
            config["plugins"]["title"]["font"]["size"] = 16
            config["plugins"]["title"]["padding"] = {"top": 10, "bottom": 20}
            config["scales"]["x"]["ticks"]["font"]["size"] = 10
            config["scales"]["x"]["ticks"]["maxRotation"] = 30
            config["scales"]["y"]["ticks"]["font"]["size"] = 10
            config["elements"]["point"]["radius"] = 4
            config["elements"]["point"]["hoverRadius"] = 6
            config["elements"]["line"]["borderWidth"] = 2.5
            config["layout"]["padding"] = {"top": 15, "right": 15, "bottom": 15, "left": 15}
            
        # Desktop devices (> 768px)
        else:
            config["plugins"]["legend"]["labels"]["font"]["size"] = 13
            config["plugins"]["legend"]["labels"]["padding"] = 20
            config["plugins"]["title"]["font"]["size"] = 18
            config["plugins"]["title"]["padding"] = {"top": 10, "bottom": 25}
            config["scales"]["x"]["ticks"]["font"]["size"] = 12
            config["scales"]["x"]["ticks"]["maxRotation"] = 0
            config["scales"]["y"]["ticks"]["font"]["size"] = 12
            config["elements"]["point"]["radius"] = 5
            config["elements"]["point"]["hoverRadius"] = 8
            config["elements"]["line"]["borderWidth"] = 3
            
        # Adjust for very tall or short containers
        if container_height < 300:
            config["plugins"]["legend"]["display"] = False
            config["plugins"]["title"]["font"]["size"] = max(12, config["plugins"]["title"]["font"]["size"] - 2)
            config["layout"]["padding"] = {"top": 5, "right": 10, "bottom": 5, "left": 10}
        elif container_height > 600:
            config["plugins"]["title"]["font"]["size"] = min(22, config["plugins"]["title"]["font"]["size"] + 2)
            config["layout"]["padding"] = {"top": 25, "right": 25, "bottom": 25, "left": 25}
            
        return config

# Global instance
plot_utils = PlotUtils()

# Direct utility functions
def create_time_series_chart(df: pd.DataFrame, 
                           x_column: str, 
                           y_columns: Union[str, List[str]], 
                           chart_type: str = "line",
                           title: str = "",
                           colors: Optional[Dict[str, str]] = None) -> Dict:
    """Direct function to create time series chart"""
    return plot_utils.create_time_series_chart_data(df, x_column, y_columns, chart_type, title, colors)

def create_sector_comparison_chart(df: pd.DataFrame, 
                                 sectors: List[str], 
                                 year_column: str = "Year",
                                 chart_type: str = "line",
                                 title: str = "Sector Comparison") -> Dict:
    """Direct function to create sector comparison chart"""
    return plot_utils.create_sector_comparison_chart_data(df, sectors, year_column, chart_type, title)

def create_model_comparison_chart(results_dict: Dict[str, List], 
                                years: List[int],
                                models: List[str],
                                title: str = "Model Comparison") -> Dict:
    """Direct function to create model comparison chart"""
    return plot_utils.create_model_comparison_chart_data(results_dict, years, models, title)

def create_td_losses_chart(td_losses_data: List[Dict], 
                          title: str = "T&D Losses Configuration") -> Dict:
    """Direct function to create T&D losses chart with configured points"""
    return plot_utils.create_td_losses_chart_data(td_losses_data, title)

def create_consolidated_chart(df: pd.DataFrame,
                            chart_type: str = "stacked_bar",
                            title: str = "Consolidated Analysis",
                            colors: Optional[Dict[str, str]] = None) -> Dict:
    """Direct function to create consolidated charts"""
    if chart_type == "stacked_bar":
        # Convert DataFrame to format expected by stacked bar chart
        data_dict = {}
        for col in df.columns:
            if col != 'Year' and col != 'year':
                data_dict[col] = df[col].tolist()
        
        year_col = 'Year' if 'Year' in df.columns else 'year'
        labels = df[year_col].tolist() if year_col in df.columns else list(range(len(df)))
        
        return plot_utils.create_stacked_bar_chart_data(data_dict, labels, title, colors)
    else:
        # For other chart types, use time series
        year_col = 'Year' if 'Year' in df.columns else 'year'
        value_cols = [col for col in df.columns if col not in [year_col, 'Year', 'year']]
        return plot_utils.create_time_series_chart_data(df, year_col, value_cols, chart_type, title, colors)