# utils/load_profile_report_generator.py
"""
Enhanced Load Profile Report Generator
Adapted for the new project-based structure with comprehensive analytics
"""

import os
import io
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use 'Agg' backend for non-interactive plotting
import matplotlib.pyplot as plt
import seaborn as sns
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, 
                               TableStyle, Image as RLImage, PageBreak, KeepTogether)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from datetime import datetime, timedelta
import tempfile
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class LoadProfileReportGenerator:
    """
   report generator for load profile analysis
    """
    
    def __init__(self, project_path, profile_id):
        """
        Initialize the report generator
        
        Args:
            project_path (str): Path to the project directory
            profile_id (str): ID of the profile to analyze
        """
        self.project_path = Path(project_path)
        self.profile_id = profile_id
        self.data = None
        self.metadata = None
        self.statistics = None
        self.plots = {}
        
        # Initialize styles
        self.styles = getSampleStyleSheet()
        self.custom_styles = self._create_custom_styles()
        
        # Load profile data
        self._load_profile_data()
    
    def _create_custom_styles(self):
        """Create custom paragraph styles for the report"""
        styles = {
            'Title': ParagraphStyle(
                'Title',
                parent=self.styles['Title'],
                fontSize=24,
                alignment=1,  # Center
                spaceAfter=20,
                textColor=colors.HexColor('#2c3e50')
            ),
            'Heading1': ParagraphStyle(
                'Heading1',
                parent=self.styles['Heading1'],
                fontSize=18,
                spaceAfter=12,
                spaceBefore=20,
                textColor=colors.HexColor('#34495e')
            ),
            'Heading2': ParagraphStyle(
                'Heading2',
                parent=self.styles['Heading2'],
                fontSize=14,
                spaceAfter=8,
                spaceBefore=12,
                textColor=colors.HexColor('#34495e')
            ),
            'Normal': ParagraphStyle(
                'Normal',
                parent=self.styles['Normal'],
                fontSize=11,
                spaceAfter=6,
                leading=14
            ),
            'Caption': ParagraphStyle(
                'Caption',
                parent=self.styles['Normal'],
                fontSize=9,
                textColor=colors.HexColor('#7f8c8d'),
                alignment=1,  # Center
                spaceAfter=12
            )
        }
        return styles
    
    def _load_profile_data(self):
        """Load profile data and metadata"""
        try:
            # Load CSV data
            csv_path = self.project_path / 'results' / 'load_profiles' / f"{self.profile_id}.csv"
            if not csv_path.exists():
                raise FileNotFoundError(f"Profile {self.profile_id} not found")
            
            self.data = pd.read_csv(csv_path)
            
            # Standardize columns
            self.data = self._standardize_columns(self.data)
            
            # Load metadata if available
            metadata_path = self.project_path / 'config' / f"{self.profile_id}_metadata.json"
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    self.metadata = json.load(f)
            else:
                self.metadata = {}
            
            # Calculate comprehensive statistics
            self.statistics = self._calculate_comprehensive_statistics()
            
        except Exception as e:
            logger.error(f"Failed to load profile data: {e}")
            raise
    
    def _standardize_columns(self, df):
        """Standardize column names and ensure required columns exist"""
        # Column mapping
        column_mapping = {
            'Demand (kW)': 'demand',
            'Load': 'demand',
            'load': 'demand',
            'datetime': 'ds',
            'timestamp': 'ds',
            'Date': 'date_str',
            'Time': 'time_str'
        }
        
        df = df.rename(columns=column_mapping)
        
        # Ensure datetime column
        if 'ds' not in df.columns:
            if 'date_str' in df.columns and 'time_str' in df.columns:
                df['ds'] = pd.to_datetime(df['date_str'] + ' ' + df['time_str'], 
                                         format='%d-%m-%Y %H:%M:%S', 
                                         dayfirst=True, errors='coerce')
            else:
                # Try to create from index or other columns
                df['ds'] = pd.to_datetime(df.index)
        
        # Ensure datetime is properly formatted
        if 'ds' in df.columns:
            df['ds'] = pd.to_datetime(df['ds'])
            df['date'] = df['ds'].dt.date
            df['time'] = df['ds'].dt.time
            df['hour'] = df['ds'].dt.hour
            df['day_of_week'] = df['ds'].dt.dayofweek
            df['month'] = df['ds'].dt.month
            df['year'] = df['ds'].dt.year
            
            # Calculate financial year (April to March)
            df['financial_year'] = df['ds'].apply(
                lambda x: x.year + 1 if x.month >= 4 else x.year
            )
            
            # Add season
            season_map = {
                12: 'Winter', 1: 'Winter', 2: 'Winter',
                3: 'Summer', 4: 'Summer', 5: 'Summer', 6: 'Summer',
                7: 'Monsoon', 8: 'Monsoon', 9: 'Monsoon', 10: 'Monsoon', 11: 'Monsoon'
            }
            df['season'] = df['month'].map(season_map)
            
            # Add day type
            df['is_weekend'] = df['day_of_week'].isin([5, 6])
            df['day_type'] = df['is_weekend'].map({True: 'Weekend', False: 'Weekday'})
        
        return df
    
    def _calculate_comprehensive_statistics(self):
        """Calculate comprehensive statistics for the profile"""
        if 'demand' not in self.data.columns:
            return {}
        
        demand = self.data['demand']
        stats = {}
        
        # Basic statistics
        stats['basic'] = {
            'total_records': len(self.data),
            'peak_load': float(demand.max()),
            'min_load': float(demand.min()),
            'average_load': float(demand.mean()),
            'std_dev': float(demand.std()),
            'load_factor': float((demand.mean() / demand.max()) * 100) if demand.max() > 0 else 0,
            'total_energy': float(demand.sum()),
            'cv': float(demand.std() / demand.mean()) if demand.mean() > 0 else 0
        }
        
        # Time-based statistics
        if 'ds' in self.data.columns:
            peak_idx = demand.idxmax()
            min_idx = demand.idxmin()
            stats['basic']['peak_datetime'] = self.data.loc[peak_idx, 'ds'].strftime('%d %b %Y %H:%M')
            stats['basic']['min_datetime'] = self.data.loc[min_idx, 'ds'].strftime('%d %b %Y %H:%M')
            
            # Date range
            stats['basic']['date_range'] = {
                'start': self.data['ds'].min().strftime('%d %b %Y'),
                'end': self.data['ds'].max().strftime('%d %b %Y'),
                'duration_days': (self.data['ds'].max() - self.data['ds'].min()).days
            }
        
        # Hourly patterns
        if 'hour' in self.data.columns:
            hourly_stats = self.data.groupby('hour')['demand'].agg(['mean', 'max', 'min', 'std'])
            stats['hourly'] = {
                'pattern': hourly_stats['mean'].to_dict(),
                'peak_hour': int(hourly_stats['mean'].idxmax()),
                'min_hour': int(hourly_stats['mean'].idxmin()),
                'peak_hour_avg': float(hourly_stats['mean'].max()),
                'min_hour_avg': float(hourly_stats['mean'].min())
            }
        
        # Daily patterns
        if 'day_type' in self.data.columns:
            daily_stats = self.data.groupby('day_type')['demand'].agg(['mean', 'max', 'min'])
            stats['daily'] = daily_stats.to_dict('index')
            
            # Weekday vs weekend comparison
            if 'hour' in self.data.columns:
                weekday_pattern = self.data[~self.data['is_weekend']].groupby('hour')['demand'].mean()
                weekend_pattern = self.data[self.data['is_weekend']].groupby('hour')['demand'].mean()
                stats['daily_patterns'] = {
                    'weekday': weekday_pattern.to_dict(),
                    'weekend': weekend_pattern.to_dict()
                }
        
        # Seasonal patterns
        if 'season' in self.data.columns:
            seasonal_stats = self.data.groupby('season')['demand'].agg(['mean', 'max', 'min', 'sum'])
            stats['seasonal'] = seasonal_stats.to_dict('index')
        
        # Monthly patterns
        if 'month' in self.data.columns:
            monthly_stats = self.data.groupby('month')['demand'].agg(['mean', 'max', 'min', 'std'])
            stats['monthly'] = monthly_stats.to_dict('index')
        
        # Load duration curve
        sorted_demands = np.sort(demand.values)[::-1]  # Sort in descending order
        stats['duration_curve'] = {
            'demands': sorted_demands.tolist(),
            'percentiles': {
                'p10': float(np.percentile(sorted_demands, 90)),  # Top 10%
                'p25': float(np.percentile(sorted_demands, 75)),  # Top 25%
                'p50': float(np.percentile(sorted_demands, 50)),  # Median
                'p75': float(np.percentile(sorted_demands, 25)),  # Bottom 25%
                'p90': float(np.percentile(sorted_demands, 10))   # Bottom 10%
            }
        }
        
        # Annual statistics by financial year
        if 'financial_year' in self.data.columns:
            annual_stats = self.data.groupby('financial_year')['demand'].agg(['mean', 'max', 'min', 'sum'])
            stats['annual'] = annual_stats.to_dict('index')
        
        return stats
    
    def generate_plots(self):
        """Generate all plots for the report"""
        plt.style.use('seaborn-v0_8')
        plt.rcParams['figure.figsize'] = (10, 6)
        plt.rcParams['font.size'] = 10
        
        # 1. Overview time series plot
        self._create_overview_plot()
        
        # 2. Load duration curve
        self._create_duration_curve_plot()
        
        # 3. Hourly patterns
        self._create_hourly_patterns_plot()
        
        # 4. Daily patterns (weekday vs weekend)
        self._create_daily_patterns_plot()
        
        # 5. Seasonal analysis
        self._create_seasonal_plot()
        
        # 6. Monthly patterns
        self._create_monthly_patterns_plot()
        
        # 7. Load factor analysis
        self._create_load_factor_plot()
        
        # 8. Heatmap (weekly pattern)
        self._create_heatmap_plot()
        
        # 9. Statistical distribution
        self._create_distribution_plot()
    
    def _create_overview_plot(self):
        """Create overview time series plot"""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        if 'ds' in self.data.columns and len(self.data) > 0:
            # Sample data if too large
            if len(self.data) > 8760:  # More than a year of hourly data
                sample_data = self.data.sample(n=8760, random_state=42).sort_values('ds')
            else:
                sample_data = self.data.sort_values('ds')
            
            ax.plot(sample_data['ds'], sample_data['demand'], 
                   linewidth=0.8, alpha=0.8, color='#3498db')
            ax.fill_between(sample_data['ds'], sample_data['demand'], 
                           alpha=0.3, color='#3498db')
            
            # Mark peak and minimum
            peak_idx = sample_data['demand'].idxmax()
            min_idx = sample_data['demand'].idxmin()
            
            ax.plot(sample_data.loc[peak_idx, 'ds'], sample_data.loc[peak_idx, 'demand'], 
                   'ro', markersize=8, label=f'Peak: {sample_data.loc[peak_idx, "demand"]:.1f}')
            ax.plot(sample_data.loc[min_idx, 'ds'], sample_data.loc[min_idx, 'demand'], 
                   'go', markersize=8, label=f'Min: {sample_data.loc[min_idx, "demand"]:.1f}')
        
        ax.set_xlabel('Date/Time')
        ax.set_ylabel('Demand (kW)')
        ax.set_title('Load Profile Overview', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Format x-axis
        fig.autofmt_xdate()
        
        plt.tight_layout()
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='PNG', dpi=300, bbox_inches='tight')
        plt.close()
        buffer.seek(0)
        self.plots['overview'] = buffer
    
    def _create_duration_curve_plot(self):
        """Create load duration curve"""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        sorted_demands = np.sort(self.data['demand'].values)[::-1]
        hours = np.arange(1, len(sorted_demands) + 1)
        
        ax.plot(hours, sorted_demands, linewidth=2, color='#e74c3c')
        ax.fill_between(hours, sorted_demands, alpha=0.3, color='#e74c3c')
        
        # Add percentile lines
        percentiles = self.statistics['duration_curve']['percentiles']
        for pct, value in percentiles.items():
            ax.axhline(y=value, color='gray', linestyle='--', alpha=0.7, 
                      label=f'{pct.upper()}: {value:.1f} kW')
        
        ax.set_xlabel('Hours (Ranked by Demand)')
        ax.set_ylabel('Demand (kW)')
        ax.set_title('Load Duration Curve', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        plt.tight_layout()
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='PNG', dpi=300, bbox_inches='tight')
        plt.close()
        buffer.seek(0)
        self.plots['duration_curve'] = buffer
    
    def _create_hourly_patterns_plot(self):
        """Create hourly load patterns"""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        if 'hourly' in self.statistics:
            hours = list(range(24))
            hourly_avg = [self.statistics['hourly']['pattern'].get(h, 0) for h in hours]
            
            bars = ax.bar(hours, hourly_avg, color='#9b59b6', alpha=0.8, edgecolor='darkviolet')
            
            # Highlight peak hour
            peak_hour = self.statistics['hourly']['peak_hour']
            bars[peak_hour].set_color('#e74c3c')
            
            ax.set_xlabel('Hour of Day')
            ax.set_ylabel('Average Demand (kW)')
            ax.set_title('Average Hourly Load Pattern', fontsize=14, fontweight='bold')
            ax.set_xticks(hours)
            ax.set_xticklabels([f'{h:02d}:00' for h in hours], rotation=45)
            ax.grid(True, alpha=0.3, axis='y')
            
            # Add peak hour annotation
            ax.annotate(f'Peak Hour\n{peak_hour}:00\n{self.statistics["hourly"]["peak_hour_avg"]:.1f} kW',
                       xy=(peak_hour, self.statistics['hourly']['peak_hour_avg']),
                       xytext=(peak_hour + 2, self.statistics['hourly']['peak_hour_avg'] * 1.1),
                       arrowprops=dict(arrowstyle='->', color='red', lw=1.5),
                       fontsize=9, ha='center')
        
        plt.tight_layout()
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='PNG', dpi=300, bbox_inches='tight')
        plt.close()
        buffer.seek(0)
        self.plots['hourly_patterns'] = buffer
    
    def _create_daily_patterns_plot(self):
        """Create weekday vs weekend patterns"""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        if 'daily_patterns' in self.statistics:
            hours = list(range(24))
            weekday_pattern = [self.statistics['daily_patterns']['weekday'].get(h, 0) for h in hours]
            weekend_pattern = [self.statistics['daily_patterns']['weekend'].get(h, 0) for h in hours]
            
            ax.plot(hours, weekday_pattern, 'b-', linewidth=2, label='Weekdays', marker='o', markersize=4)
            ax.plot(hours, weekend_pattern, 'r--', linewidth=2, label='Weekends', marker='s', markersize=4)
            
            ax.fill_between(hours, weekday_pattern, alpha=0.3, color='blue')
            ax.fill_between(hours, weekend_pattern, alpha=0.3, color='red')
        
        ax.set_xlabel('Hour of Day')
        ax.set_ylabel('Average Demand (kW)')
        ax.set_title('Weekday vs Weekend Load Patterns', fontsize=14, fontweight='bold')
        ax.set_xticks(hours)
        ax.set_xticklabels([f'{h:02d}:00' for h in hours], rotation=45)
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        plt.tight_layout()
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='PNG', dpi=300, bbox_inches='tight')
        plt.close()
        buffer.seek(0)
        self.plots['daily_patterns'] = buffer
    
    def _create_seasonal_plot(self):
        """Create seasonal analysis plot"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        if 'seasonal' in self.statistics:
            seasons = list(self.statistics['seasonal'].keys())
            means = [self.statistics['seasonal'][s]['mean'] for s in seasons]
            maxes = [self.statistics['seasonal'][s]['max'] for s in seasons]
            mins = [self.statistics['seasonal'][s]['min'] for s in seasons]
            totals = [self.statistics['seasonal'][s]['sum'] for s in seasons]
            
            # Bar chart for averages
            colors = ['#e74c3c', '#f39c12', '#27ae60'][:len(seasons)]
            bars = ax1.bar(seasons, means, color=colors, alpha=0.8)
            
            # Add value labels on bars
            for bar, mean in zip(bars, means):
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                        f'{mean:.1f}', ha='center', va='bottom', fontweight='bold')
            
            ax1.set_ylabel('Average Demand (kW)')
            ax1.set_title('Average Seasonal Demand', fontweight='bold')
            ax1.grid(True, alpha=0.3, axis='y')
            
            # Line chart for min/max
            x_pos = range(len(seasons))
            ax2.plot(x_pos, maxes, 'r-o', linewidth=2, markersize=8, label='Maximum')
            ax2.plot(x_pos, means, 'b-s', linewidth=2, markersize=8, label='Average')
            ax2.plot(x_pos, mins, 'g-^', linewidth=2, markersize=8, label='Minimum')
            
            ax2.set_xticks(x_pos)
            ax2.set_xticklabels(seasons)
            ax2.set_ylabel('Demand (kW)')
            ax2.set_title('Seasonal Demand Variations', fontweight='bold')
            ax2.grid(True, alpha=0.3)
            ax2.legend()
        
        plt.tight_layout()
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='PNG', dpi=300, bbox_inches='tight')
        plt.close()
        buffer.seek(0)
        self.plots['seasonal'] = buffer
    
    def _create_monthly_patterns_plot(self):
        """Create monthly patterns plot"""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        if 'monthly' in self.statistics:
            months = sorted(self.statistics['monthly'].keys())
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            month_labels = [month_names[m-1] for m in months]
            
            means = [self.statistics['monthly'][m]['mean'] for m in months]
            maxes = [self.statistics['monthly'][m]['max'] for m in months]
            mins = [self.statistics['monthly'][m]['min'] for m in months]
            
            # Create gradient colors
            colors = plt.cm.viridis(np.linspace(0, 1, len(months)))
            
            bars = ax.bar(month_labels, means, color=colors, alpha=0.8, edgecolor='black', linewidth=0.5)
            
            # Add error bars for min/max
            errors = [[mean - min_val for mean, min_val in zip(means, mins)],
                     [max_val - mean for mean, max_val in zip(means, maxes)]]
            ax.errorbar(month_labels, means, yerr=errors, fmt='none', 
                       ecolor='black', capsize=5, capthick=2)
            
            # Add trend line
            ax.plot(month_labels, means, 'r-', linewidth=2, alpha=0.7, label='Trend')
        
        ax.set_xlabel('Month')
        ax.set_ylabel('Demand (kW)')
        ax.set_title('Monthly Load Patterns with Min/Max Range', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y')
        ax.legend()
        
        plt.tight_layout()
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='PNG', dpi=300, bbox_inches='tight')
        plt.close()
        buffer.seek(0)
        self.plots['monthly_patterns'] = buffer
    
    def _create_load_factor_plot(self):
        """Create load factor analysis plot"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Load factor gauge (simplified as bar chart)
        load_factor = self.statistics['basic']['load_factor']
        categories = ['Current\nLoad Factor', 'Excellent\n(>80%)', 'Good\n(60-80%)', 'Poor\n(<60%)']
        values = [load_factor, 90, 70, 40]
        colors_lf = ['#3498db', '#27ae60', '#f39c12', '#e74c3c']
        
        bars = ax1.bar(categories, values, color=colors_lf, alpha=0.8)
        bars[0].set_color('#2980b9')  # Highlight current load factor
        
        ax1.set_ylabel('Load Factor (%)')
        ax1.set_title('Load Factor Analysis', fontweight='bold')
        ax1.set_ylim(0, 100)
        ax1.grid(True, alpha=0.3, axis='y')
        
        # Add percentage labels
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{value:.1f}%', ha='center', va='bottom', fontweight='bold')
        
        # Load factor by time period (if annual data available)
        if 'annual' in self.statistics and len(self.statistics['annual']) > 1:
            years = sorted(self.statistics['annual'].keys())
            annual_lf = []
            for year in years:
                annual_stats = self.statistics['annual'][year]
                lf = (annual_stats['mean'] / annual_stats['max']) * 100 if annual_stats['max'] > 0 else 0
                annual_lf.append(lf)
            
            ax2.plot(years, annual_lf, 'b-o', linewidth=2, markersize=8)
            ax2.set_xlabel('Financial Year')
            ax2.set_ylabel('Load Factor (%)')
            ax2.set_title('Load Factor Trend', fontweight='bold')
            ax2.grid(True, alpha=0.3)
            ax2.set_ylim(0, 100)
        else:
            # Show distribution instead
            if len(self.data) > 0:
                hourly_lf = (self.data.groupby('hour')['demand'].mean() / 
                           self.statistics['basic']['peak_load'] * 100)
                ax2.bar(range(24), hourly_lf, color='lightblue', alpha=0.8)
                ax2.set_xlabel('Hour of Day')
                ax2.set_ylabel('Load Factor (%)')
                ax2.set_title('Hourly Load Factor Distribution', fontweight='bold')
                ax2.set_xticks(range(0, 24, 2))
                ax2.grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='PNG', dpi=300, bbox_inches='tight')
        plt.close()
        buffer.seek(0)
        self.plots['load_factor'] = buffer
    
    def _create_heatmap_plot(self):
        """Create weekly load pattern heatmap"""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        if 'hour' in self.data.columns and 'day_of_week' in self.data.columns:
            # Create pivot table for heatmap
            heatmap_data = self.data.groupby(['day_of_week', 'hour'])['demand'].mean().unstack()
            
            # Handle missing values
            heatmap_data = heatmap_data.fillna(0)
            
            # Create heatmap
            sns.heatmap(heatmap_data, annot=True, fmt='.0f', cmap='YlOrRd', 
                       cbar_kws={'label': 'Average Demand (kW)'}, 
                       linewidths=0.5, linecolor='white')
            
            ax.set_xlabel('Hour of Day')
            ax.set_ylabel('Day of Week')
            ax.set_title('Weekly Load Pattern Heatmap', fontsize=14, fontweight='bold')
            
            # Customize labels
            day_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            ax.set_yticklabels(day_labels, rotation=0)
            
            hour_labels = [f'{h:02d}:00' for h in range(0, 24, 2)]
            ax.set_xticks(range(0, 24, 2))
            ax.set_xticklabels(hour_labels, rotation=45)
        
        plt.tight_layout()
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='PNG', dpi=300, bbox_inches='tight')
        plt.close()
        buffer.seek(0)
        self.plots['heatmap'] = buffer
    
    def _create_distribution_plot(self):
        """Create demand distribution analysis"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        
        demand = self.data['demand']
        
        # Histogram
        ax1.hist(demand, bins=50, alpha=0.7, color='skyblue', edgecolor='black')
        ax1.axvline(demand.mean(), color='red', linestyle='--', linewidth=2, label=f'Mean: {demand.mean():.1f}')
        ax1.axvline(demand.median(), color='green', linestyle='--', linewidth=2, label=f'Median: {demand.median():.1f}')
        ax1.set_xlabel('Demand (kW)')
        ax1.set_ylabel('Frequency')
        ax1.set_title('Demand Distribution', fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Box plot
        ax2.boxplot(demand, vert=True, patch_artist=True, 
                   boxprops=dict(facecolor='lightblue', alpha=0.7))
        ax2.set_ylabel('Demand (kW)')
        ax2.set_title('Demand Box Plot', fontweight='bold')
        ax2.grid(True, alpha=0.3)
        
        # Q-Q plot (simplified)
        from scipy import stats
        stats.probplot(demand, dist="norm", plot=ax3)
        ax3.set_title('Q-Q Plot (Normal Distribution)', fontweight='bold')
        ax3.grid(True, alpha=0.3)
        
        # Cumulative distribution
        sorted_demand = np.sort(demand)
        cumulative = np.arange(1, len(sorted_demand) + 1) / len(sorted_demand)
        ax4.plot(sorted_demand, cumulative * 100, linewidth=2, color='purple')
        ax4.set_xlabel('Demand (kW)')
        ax4.set_ylabel('Cumulative Probability (%)')
        ax4.set_title('Cumulative Distribution Function', fontweight='bold')
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='PNG', dpi=300, bbox_inches='tight')
        plt.close()
        buffer.seek(0)
        self.plots['distribution'] = buffer
    
    def generate_pdf_report(self, output_path):
        """Generate comprehensive PDF report"""
        try:
            # Generate all plots first
            self.generate_plots()
            
            # Create PDF document
            doc = SimpleDocTemplate(output_path, pagesize=letter, 
                                  topMargin=1*inch, bottomMargin=1*inch,
                                  leftMargin=0.75*inch, rightMargin=0.75*inch)
            elements = []
            
            # Title page
            elements.extend(self._create_title_page())
            elements.append(PageBreak())
            
            # Executive summary
            elements.extend(self._create_executive_summary())
            elements.append(PageBreak())
            
            # Overview analysis
            elements.extend(self._create_overview_section())
            elements.append(PageBreak())
            
            # Detailed analysis sections
            elements.extend(self._create_detailed_analysis())
            
            # Build PDF
            doc.build(elements)
            
            logger.info(f"PDF report generated successfully: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to generate PDF report: {e}")
            raise
    
    def _create_title_page(self):
        """Create title page elements"""
        elements = []
        
        # Main title
        title = Paragraph(f"Load Profile Analysis Report", self.custom_styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 0.5*inch))
        
        # Profile information
        profile_info = f"""
        <para fontSize="14" spaceAfter="12">
        <b>Profile ID:</b> {self.profile_id}<br/>
        <b>Analysis Date:</b> {datetime.now().strftime('%d %B %Y')}<br/>
        <b>Report Generated:</b> {datetime.now().strftime('%d %B %Y at %H:%M')}
        </para>
        """
        elements.append(Paragraph(profile_info, self.custom_styles['Normal']))
        elements.append(Spacer(1, 0.5*inch))
        
        # Key metrics table
        if self.statistics and 'basic' in self.statistics:
            stats = self.statistics['basic']
            metrics_data = [
                ['Metric', 'Value', 'Unit'],
                ['Total Records', f"{stats['total_records']:,}", 'records'],
                ['Peak Load', f"{stats['peak_load']:.2f}", 'kW'],
                ['Average Load', f"{stats['average_load']:.2f}", 'kW'],
                ['Minimum Load', f"{stats['min_load']:.2f}", 'kW'],
                ['Load Factor', f"{stats['load_factor']:.1f}", '%'],
                ['Total Energy', f"{stats['total_energy']:,.0f}", 'kWh'],
                ['Analysis Period', f"{stats.get('date_range', {}).get('duration_days', 'N/A')}", 'days']
            ]
            
            metrics_table = Table(metrics_data, colWidths=[2.5*inch, 1.5*inch, 1*inch])
            metrics_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
            ]))
            
            elements.append(metrics_table)
        
        return elements
    
    def _create_executive_summary(self):
        """Create executive summary section"""
        elements = []
        
        elements.append(Paragraph("Executive Summary", self.custom_styles['Heading1']))
        
        if self.statistics and 'basic' in self.statistics:
            stats = self.statistics['basic']
            
            # Generate insights
            insights = []
            
            # Load factor analysis
            lf = stats['load_factor']
            if lf > 80:
                lf_assessment = "excellent, indicating highly efficient utilization"
            elif lf > 60:
                lf_assessment = "good, showing effective demand management"
            elif lf > 40:
                lf_assessment = "moderate, with room for optimization"
            else:
                lf_assessment = "poor, suggesting significant optimization opportunities"
            
            insights.append(f"The load factor of {lf:.1f}% is {lf_assessment}.")
            
            # Peak analysis
            peak_ratio = stats['peak_load'] / stats['average_load']
            if peak_ratio > 3:
                insights.append(f"The peak-to-average ratio of {peak_ratio:.1f} indicates highly variable demand patterns.")
            elif peak_ratio > 2:
                insights.append(f"The peak-to-average ratio of {peak_ratio:.1f} shows moderate demand variability.")
            else:
                insights.append(f"The peak-to-average ratio of {peak_ratio:.1f} indicates relatively stable demand patterns.")
            
            # Seasonal insights
            if 'seasonal' in self.statistics:
                seasonal_data = self.statistics['seasonal']
                seasons = list(seasonal_data.keys())
                season_loads = [seasonal_data[s]['mean'] for s in seasons]
                max_season = seasons[season_loads.index(max(season_loads))]
                min_season = seasons[season_loads.index(min(season_loads))]
                insights.append(f"Seasonal analysis shows peak consumption during {max_season} and lowest during {min_season}.")
            
            # Time period insights
            if 'date_range' in stats:
                duration = stats['date_range'].get('duration_days', 0)
                if duration > 365:
                    insights.append(f"Analysis covers {duration} days of data, providing comprehensive long-term insights.")
                elif duration > 30:
                    insights.append(f"Analysis covers {duration} days of data, providing good medium-term insights.")
                else:
                    insights.append(f"Analysis covers {duration} days of data, providing short-term insights.")
            
            # Create summary paragraph
            summary_text = " ".join(insights)
            elements.append(Paragraph(summary_text, self.custom_styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))
            
            # Key recommendations
            elements.append(Paragraph("Key Recommendations:", self.custom_styles['Heading2']))
            
            recommendations = []
            if lf < 60:
                recommendations.append("Consider demand-side management strategies to improve load factor")
            if peak_ratio > 2.5:
                recommendations.append("Implement load shifting or peak shaving measures")
            if 'hourly' in self.statistics:
                peak_hour = self.statistics['hourly']['peak_hour']
                recommendations.append(f"Focus demand management efforts around {peak_hour}:00 when peak demand typically occurs")
            
            for i, rec in enumerate(recommendations, 1):
                elements.append(Paragraph(f"{i}. {rec}", self.custom_styles['Normal']))
        
        return elements
    
    def _create_overview_section(self):
        """Create overview section with main plots"""
        elements = []
        
        elements.append(Paragraph("Load Profile Overview", self.custom_styles['Heading1']))
        
        # Overview plot
        if 'overview' in self.plots:
            elements.append(RLImage(self.plots['overview'], width=7*inch, height=4.2*inch))
            elements.append(Paragraph("Figure 1: Complete load profile time series showing demand patterns over the analysis period.", 
                                    self.custom_styles['Caption']))
            elements.append(Spacer(1, 0.2*inch))
        
        # Load duration curve
        if 'duration_curve' in self.plots:
            elements.append(RLImage(self.plots['duration_curve'], width=7*inch, height=4.2*inch))
            elements.append(Paragraph("Figure 2: Load duration curve showing the distribution of demand levels and system utilization efficiency.", 
                                    self.custom_styles['Caption']))
        
        return elements
    
    def _create_detailed_analysis(self):
        """Create detailed analysis sections"""
        elements = []
        
        # Temporal patterns section
        elements.append(PageBreak())
        elements.append(Paragraph("Temporal Load Patterns", self.custom_styles['Heading1']))
        
        # Hourly patterns
        if 'hourly_patterns' in self.plots:
            elements.append(RLImage(self.plots['hourly_patterns'], width=7*inch, height=4.2*inch))
            elements.append(Paragraph("Figure 3: Average hourly load pattern showing typical daily demand variations.", 
                                    self.custom_styles['Caption']))
            elements.append(Spacer(1, 0.2*inch))
        
        # Daily patterns
        if 'daily_patterns' in self.plots:
            elements.append(RLImage(self.plots['daily_patterns'], width=7*inch, height=4.2*inch))
            elements.append(Paragraph("Figure 4: Comparison of weekday versus weekend load patterns.", 
                                    self.custom_styles['Caption']))
            elements.append(Spacer(1, 0.2*inch))
        
        # Seasonal analysis section
        elements.append(PageBreak())
        elements.append(Paragraph("Seasonal and Monthly Analysis", self.custom_styles['Heading1']))
        
        if 'seasonal' in self.plots:
            elements.append(RLImage(self.plots['seasonal'], width=7*inch, height=4.2*inch))
            elements.append(Paragraph("Figure 5: Seasonal load analysis showing variations across different seasons.", 
                                    self.custom_styles['Caption']))
            elements.append(Spacer(1, 0.2*inch))
        
        if 'monthly_patterns' in self.plots:
            elements.append(RLImage(self.plots['monthly_patterns'], width=7*inch, height=4.2*inch))
            elements.append(Paragraph("Figure 6: Monthly load patterns with minimum and maximum ranges.", 
                                    self.custom_styles['Caption']))
            elements.append(Spacer(1, 0.2*inch))
        
        # Load factor analysis section
        elements.append(PageBreak())
        elements.append(Paragraph("Load Factor and Efficiency Analysis", self.custom_styles['Heading1']))
        
        if 'load_factor' in self.plots:
            elements.append(RLImage(self.plots['load_factor'], width=7*inch, height=4.2*inch))
            elements.append(Paragraph("Figure 7: Load factor analysis and efficiency benchmarking.", 
                                    self.custom_styles['Caption']))
            elements.append(Spacer(1, 0.2*inch))
        
        # Advanced analysis section
        elements.append(PageBreak())
        elements.append(Paragraph("Advanced Pattern Analysis", self.custom_styles['Heading1']))
        
        if 'heatmap' in self.plots:
            elements.append(RLImage(self.plots['heatmap'], width=7*inch, height=5.6*inch))
            elements.append(Paragraph("Figure 8: Weekly load pattern heatmap showing demand intensity across days and hours.", 
                                    self.custom_styles['Caption']))
            elements.append(Spacer(1, 0.2*inch))
        
        if 'distribution' in self.plots:
            elements.append(RLImage(self.plots['distribution'], width=7*inch, height=5.6*inch))
            elements.append(Paragraph("Figure 9: Statistical distribution analysis of demand values.", 
                                    self.custom_styles['Caption']))
        
        return elements