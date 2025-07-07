"""
Color Management Utility for Energy Platform
Centralized color management system for consistent theming across the application
"""

import json
import os
import logging
from typing import Dict, List, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)

class ColorManager:
    """
    Centralized color management system for the entire application
    Supports sectors, models, carriers, and custom color schemes
    """
    
    def __init__(self, app=None):
        self.app = app
        self.config_file = None
        self.colors = {}
        self.default_colors = self._get_default_colors()
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app"""
        self.app = app
        static_folder = app.static_folder or 'static'
        self.config_file = os.path.join(static_folder, 'config', 'colors.json')
        
        # Ensure config directory exists
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
        # Load existing colors or create default
        self.load_colors()
        
        # Register template functions
        app.jinja_env.globals['get_color'] = self.get_color
        app.jinja_env.globals['get_color_palette'] = self.get_color_palette
        app.jinja_env.globals['get_all_colors'] = self.get_all_colors
    
    def _get_default_colors(self) -> Dict:
        """Define comprehensive default color schemes with enhanced visual appeal"""
        return {
            "sectors": {
                "residential": "#2563EB",      # Vibrant Blue
                "commercial": "#059669",       # Emerald Green
                "industrial": "#DC2626",       # Strong Red
                "transportation": "#7C3AED",   # Rich Purple
                "agriculture": "#16A34A",      # Forest Green
                "public": "#EA580C",           # Warm Orange
                "mining": "#92400E",           # Earth Brown
                "construction": "#0891B2",     # Steel Blue
                "services": "#BE185D",         # Magenta Pink
                "healthcare": "#0D9488",       # Medical Teal
                "education": "#7C2D12",        # Academic Brown
                "hospitality": "#B91C1C",      # Hospitality Red
                "retail": "#1D4ED8",           # Commerce Blue
                "finance": "#6B21A8",          # Finance Purple
                "technology": "#0F766E",       # Tech Teal
                "manufacturing": "#A16207",    # Industrial Amber
                "utilities": "#DC2626",        # Utility Red
                "government": "#1F2937",       # Official Gray
                "military": "#374151",         # Military Gray
                "other": "#6B7280"             # Neutral Gray
            },
            "models": {
                "MLR": "#2563EB",              # Primary Blue
                "SLR": "#059669",              # Success Green
                "WAM": "#F59E0B",              # Warning Amber
                "TimeSeries": "#8B5CF6",       # Time Violet
                "ARIMA": "#EF4444",            # Alert Red
                "Linear": "#06B6D4",           # Linear Cyan
                "Polynomial": "#84CC16",       # Growth Lime
                "Exponential": "#F97316",      # Energy Orange
                "Logarithmic": "#EC4899",      # Analysis Pink
                "Power": "#14B8A6",            # Power Teal
                "Neural": "#A855F7",           # AI Purple
                "RandomForest": "#22C55E",     # Forest Green
                "SVM": "#F43F5E",              # Vector Rose
                "XGBoost": "#0EA5E9",          # Boost Sky
                "LSTM": "#8B5CF6",             # Memory Violet
                "Ensemble": "#6366F1",         # Ensemble Indigo
                "Hybrid": "#8B5CF6",           # Hybrid Purple
                "Custom": "#6B7280"            # Custom Gray
            },
            "carriers": {
                "electricity": "#3B82F6",      # Blue
                "natural_gas": "#EF4444",      # Red
                "coal": "#1F2937",             # Gray
                "oil": "#92400E",              # Brown
                "biomass": "#16A34A",          # Green
                "solar": "#F59E0B",            # Amber
                "wind": "#06B6D4",             # Cyan
                "hydro": "#0891B2",            # Light Blue
                "nuclear": "#7C3AED",          # Purple
                "geothermal": "#DC2626",       # Red
                "waste": "#6B7280",            # Gray
                "hydrogen": "#8B5CF6",         # Violet
                "battery": "#10B981",          # Emerald
                "pumped_hydro": "#0D9488",     # Teal
                "compressed_air": "#84CC16",   # Lime
                "thermal": "#F97316",          # Orange
                "district_heating": "#EC4899", # Pink
                "district_cooling": "#14B8A6"  # Teal
            },
            "status": {
                "success": "#10B981",          # Emerald
                "warning": "#F59E0B",          # Amber
                "error": "#EF4444",            # Red
                "info": "#3B82F6",             # Blue
                "pending": "#6B7280",          # Gray
                "active": "#8B5CF6",           # Violet
                "inactive": "#9CA3AF",         # Light Gray
                "completed": "#059669",        # Dark Green
                "failed": "#DC2626",           # Dark Red
                "cancelled": "#F97316"         # Orange
            },
            "charts": {
                "primary": "#2563EB",          # Vibrant Blue
                "secondary": "#059669",        # Emerald Green
                "tertiary": "#DC2626",         # Strong Red
                "quaternary": "#7C3AED",       # Rich Purple
                "quinary": "#EA580C",          # Warm Orange
                "senary": "#0891B2",           # Steel Blue
                "septenary": "#BE185D",        # Magenta Pink
                "octonary": "#16A34A",         # Forest Green
                "nonary": "#F59E0B",           # Golden Amber
                "denary": "#8B5CF6",           # Violet
                "background": "#FFFFFF",       # Pure White
                "surface": "#F8FAFC",          # Light Surface
                "grid": "rgba(226, 232, 240, 0.8)",  # Subtle Grid
                "text": "#1E293B",             # Dark Text
                "axis": "#64748B",             # Axis Gray
                "hover": "rgba(241, 245, 249, 0.9)",  # Hover Overlay
                "border": "#E2E8F0",           # Border Gray
                "shadow": "rgba(0, 0, 0, 0.1)" # Subtle Shadow
            },
            "gradients": {
                "primary": ["#3B82F6", "#1E40AF", "#1D4ED8"],        # Blue gradient
                "secondary": ["#10B981", "#047857", "#059669"],       # Green gradient
                "tertiary": ["#EF4444", "#B91C1C", "#DC2626"],        # Red gradient
                "quaternary": ["#8B5CF6", "#6D28D9", "#7C3AED"],      # Purple gradient
                "success": ["#10B981", "#047857", "#059669"],         # Success gradient
                "warning": ["#F59E0B", "#B45309", "#D97706"],         # Warning gradient
                "error": ["#EF4444", "#B91C1C", "#DC2626"],           # Error gradient
                "info": ["#3B82F6", "#1E40AF", "#2563EB"],            # Info gradient
                "chart_area": ["rgba(59, 130, 246, 0.1)", "rgba(59, 130, 246, 0.3)"],  # Chart area gradient
                "chart_line": ["#2563EB", "#1D4ED8"],                 # Chart line gradient
                "heatmap_cool": ["#EFF6FF", "#DBEAFE", "#BFDBFE", "#93C5FD", "#60A5FA", "#3B82F6"],  # Cool heatmap
                "heatmap_warm": ["#FEF3C7", "#FDE68A", "#FCD34D", "#FBBF24", "#F59E0B", "#D97706"]   # Warm heatmap
            },
            "themes": {
                "light": {
                    "background": "#FFFFFF",
                    "surface": "#F8FAFC",
                    "primary": "#2563EB",
                    "secondary": "#64748B",
                    "text": "#1E293B",
                    "border": "#E2E8F0"
                },
                "dark": {
                    "background": "#0F172A",
                    "surface": "#1E293B",
                    "primary": "#3B82F6",
                    "secondary": "#94A3B8",
                    "text": "#F1F5F9",
                    "border": "#334155"
                }
            }
        }
    
    def load_colors(self):
        """Load colors from JSON file or create default"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    saved_colors = json.load(f)
                # Merge with defaults to ensure all categories exist
                self.colors = self._merge_colors(self.default_colors, saved_colors)
                logger.info(f"Colors loaded from {self.config_file}")
            else:
                self.colors = self.default_colors.copy()
                self.save_colors()
                logger.info("Default colors created and saved")
        except Exception as e:
            logger.error(f"Error loading colors: {e}")
            self.colors = self.default_colors.copy()
    
    def save_colors(self):
        """Save current colors to JSON file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.colors, f, indent=2)
            logger.info(f"Colors saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving colors: {e}")
            return False
    
    def _merge_colors(self, defaults: Dict, saved: Dict) -> Dict:
        """Merge saved colors with defaults to ensure completeness"""
        merged = defaults.copy()
        for category, colors in saved.items():
            if category in merged and isinstance(colors, dict):
                merged[category].update(colors)
            else:
                merged[category] = colors
        return merged
    
    def get_color(self, category: str, item: str, default: str = "#6B7280") -> str:
        """Get color for specific category and item"""
        try:
            return self.colors.get(category, {}).get(item, default)
        except Exception:
            return default
    
    def get_color_palette(self, category: str, items: List[str]) -> Dict[str, str]:
        """Get color palette for multiple items in a category"""
        palette = {}
        category_colors = self.colors.get(category, {})
        
        for item in items:
            if item in category_colors:
                palette[item] = category_colors[item]
            else:
                # Generate color if not exists
                palette[item] = self._generate_color_for_item(category, item)
                # Save the generated color
                if category not in self.colors:
                    self.colors[category] = {}
                self.colors[category][item] = palette[item]
        
        return palette
    
    def _generate_color_for_item(self, category: str, item: str) -> str:
        """Generate a consistent, visually appealing color for an item based on its name"""
        import hashlib
        
        # Use hash of item name to generate consistent color
        hash_object = hashlib.md5(f"{category}_{item}".encode())
        hex_dig = hash_object.hexdigest()
        
        # Convert to HSL for better color control
        hue = int(hex_dig[:3], 16) % 360  # 0-359 degrees
        
        # Use predefined saturation and lightness for better visual appeal
        saturation = 65 + (int(hex_dig[3:5], 16) % 25)  # 65-90%
        lightness = 45 + (int(hex_dig[5:7], 16) % 20)   # 45-65%
        
        # Convert HSL to RGB
        def hsl_to_rgb(h, s, l):
            h = h / 360
            s = s / 100
            l = l / 100
            
            def hue_to_rgb(p, q, t):
                if t < 0: t += 1
                if t > 1: t -= 1
                if t < 1/6: return p + (q - p) * 6 * t
                if t < 1/2: return q
                if t < 2/3: return p + (q - p) * (2/3 - t) * 6
                return p
            
            if s == 0:
                r = g = b = l  # achromatic
            else:
                q = l * (1 + s) if l < 0.5 else l + s - l * s
                p = 2 * l - q
                r = hue_to_rgb(p, q, h + 1/3)
                g = hue_to_rgb(p, q, h)
                b = hue_to_rgb(p, q, h - 1/3)
            
            return int(r * 255), int(g * 255), int(b * 255)
        
        r, g, b = hsl_to_rgb(hue, saturation, lightness)
        return f"#{r:02X}{g:02X}{b:02X}"
    
    def set_color(self, category: str, item: str, color: str) -> bool:
        """Set color for specific category and item"""
        try:
            if category not in self.colors:
                self.colors[category] = {}
            self.colors[category][item] = color
            return self.save_colors()
        except Exception as e:
            logger.error(f"Error setting color: {e}")
            return False
    
    def set_colors(self, category: str, color_dict: Dict[str, str]) -> bool:
        """Set multiple colors for a category"""
        try:
            if category not in self.colors:
                self.colors[category] = {}
            self.colors[category].update(color_dict)
            return self.save_colors()
        except Exception as e:
            logger.error(f"Error setting colors: {e}")
            return False
    
    def get_all_colors(self) -> Dict:
        """Get all colors"""
        return self.colors.copy()
    
    def get_category_colors(self, category: str) -> Dict[str, str]:
        """Get all colors for a specific category"""
        return self.colors.get(category, {}).copy()
    
    def reset_to_defaults(self, category: Optional[str] = None) -> bool:
        """Reset colors to defaults"""
        try:
            if category:
                if category in self.default_colors:
                    self.colors[category] = self.default_colors[category].copy()
            else:
                self.colors = self.default_colors.copy()
            return self.save_colors()
        except Exception as e:
            logger.error(f"Error resetting colors: {e}")
            return False
    
    def get_chart_colors(self, count: int, category: str = "charts") -> List[str]:
        """Get an enhanced list of colors for charts with better visual distribution"""
        base_colors = [
            self.get_color(category, "primary"),     # Blue
            self.get_color(category, "secondary"),   # Green
            self.get_color(category, "tertiary"),    # Red
            self.get_color(category, "quaternary"),  # Purple
            self.get_color(category, "quinary"),     # Orange
            self.get_color(category, "senary"),      # Steel Blue
            self.get_color(category, "septenary"),   # Magenta
            self.get_color(category, "octonary"),    # Forest Green
            self.get_color(category, "nonary"),      # Amber
            self.get_color(category, "denary")       # Violet
        ]
        
        # If we need more colors, generate them with better distribution
        if count > len(base_colors):
            additional_colors = self._generate_additional_colors(count - len(base_colors))
            base_colors.extend(additional_colors)
        
        return base_colors[:count]
    
    def _generate_additional_colors(self, count: int) -> List[str]:
        """Generate additional colors with good visual distribution"""
        # Enhanced color palette for additional colors
        extended_palette = [
            "#6366F1",  # Indigo
            "#14B8A6",  # Teal
            "#F43F5E",  # Rose
            "#84CC16",  # Lime
            "#F97316",  # Orange
            "#EC4899",  # Pink
            "#06B6D4",  # Cyan
            "#A855F7",  # Purple
            "#22C55E",  # Green
            "#EF4444",  # Red
            "#8B5CF6",  # Violet
            "#10B981",  # Emerald
            "#F59E0B",  # Amber
            "#3B82F6",  # Blue
            "#6B7280"   # Gray
        ]
        
        colors = []
        for i in range(count):
            if i < len(extended_palette):
                colors.append(extended_palette[i])
            else:
                # Generate color using improved algorithm
                colors.append(self._generate_color_for_item("chart", f"extended_{i}"))
        
        return colors
    
    def get_sector_colors(self, sectors: List[str]) -> Dict[str, str]:
        """Get colors specifically for sectors"""
        return self.get_color_palette("sectors", sectors)
    
    def get_model_colors(self, models: List[str]) -> Dict[str, str]:
        """Get colors specifically for models"""
        return self.get_color_palette("models", models)
    
    def get_carrier_colors(self, carriers: List[str]) -> Dict[str, str]:
        """Get colors specifically for carriers"""
        return self.get_color_palette("carriers", carriers)
    
    def export_colors_for_js(self) -> str:
        """Export colors as JavaScript object"""
        try:
            return f"window.AppColors = {json.dumps(self.colors, indent=2)};"
        except Exception as e:
            logger.error(f"Error exporting colors for JS: {e}")
            return "window.AppColors = {};"
    
    def get_gradient(self, gradient_name: str) -> List[str]:
        """Get gradient colors"""
        return self.colors.get("gradients", {}).get(gradient_name, ["#3B82F6", "#1D4ED8"])
    
    def get_theme_colors(self, theme: str = "light") -> Dict[str, str]:
        """Get theme colors"""
        return self.colors.get("themes", {}).get(theme, self.colors["themes"]["light"])

# Global instance
color_manager = ColorManager()

def init_color_manager(app):
    """Initialize color manager with Flask app"""
    color_manager.init_app(app)
    return color_manager

# Utility functions for direct use
def get_color(category: str, item: str, default: str = "#6B7280") -> str:
    """Direct function to get color"""
    return color_manager.get_color(category, item, default)

def get_sector_colors(sectors: List[str]) -> Dict[str, str]:
    """Direct function to get sector colors"""
    return color_manager.get_sector_colors(sectors)

def get_model_colors(models: List[str]) -> Dict[str, str]:
    """Direct function to get model colors"""
    return color_manager.get_model_colors(models)

def get_chart_colors(count: int) -> List[str]:
    """Direct function to get chart colors"""
    return color_manager.get_chart_colors(count)