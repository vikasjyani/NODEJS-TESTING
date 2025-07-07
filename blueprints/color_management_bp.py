"""
Color Management API Blueprint
Provides endpoints for managing application-wide color schemes
"""

import logging
from flask import Blueprint, request, jsonify, current_app
from utils.color_manager import color_manager
from utils.common_decorators import api_route, validate_json_request, handle_exceptions
from utils.response_utils import success_json, error_json, validation_error_json

logger = logging.getLogger(__name__)

# Create blueprint
color_management_bp = Blueprint('color_management', __name__)

@color_management_bp.route('/api/colors/all', methods=['GET'])
@api_route(cache_ttl=300)
def get_all_colors():
    """Get all color configurations"""
    try:
        colors = color_manager.get_all_colors()
        return success_json("Colors retrieved successfully", colors)
    except Exception as e:
        logger.error(f"Error getting all colors: {e}")
        return error_json(f"Failed to get colors: {str(e)}")

@color_management_bp.route('/api/colors/category/<category>', methods=['GET'])
@api_route(cache_ttl=300)
def get_category_colors(category: str):
    """Get colors for a specific category"""
    try:
        if not category:
            return validation_error_json("Category parameter is required")
        
        colors = color_manager.get_category_colors(category)
        if not colors:
            return error_json(f"Category '{category}' not found", status_code=404)
        
        return success_json(f"Colors retrieved for category '{category}'", {
            'category': category,
            'colors': colors
        })
    except Exception as e:
        logger.error(f"Error getting colors for category {category}: {e}")
        return error_json(f"Failed to get category colors: {str(e)}")

@color_management_bp.route('/api/colors/sectors', methods=['GET'])
@api_route(cache_ttl=300)
def get_sector_colors():
    """Get all sector colors"""
    try:
        sectors = request.args.getlist('sectors')
        if sectors:
            colors = color_manager.get_sector_colors(sectors)
        else:
            colors = color_manager.get_category_colors('sectors')
        
        return success_json("Sector colors retrieved successfully", {
            'sectors': sectors if sectors else list(colors.keys()),
            'colors': colors
        })
    except Exception as e:
        logger.error(f"Error getting sector colors: {e}")
        return error_json(f"Failed to get sector colors: {str(e)}")

@color_management_bp.route('/api/colors/models', methods=['GET'])
@api_route(cache_ttl=300)
def get_model_colors():
    """Get all model colors"""
    try:
        models = request.args.getlist('models')
        if models:
            colors = color_manager.get_model_colors(models)
        else:
            colors = color_manager.get_category_colors('models')
        
        return success_json("Model colors retrieved successfully", {
            'models': models if models else list(colors.keys()),
            'colors': colors
        })
    except Exception as e:
        logger.error(f"Error getting model colors: {e}")
        return error_json(f"Failed to get model colors: {str(e)}")

@color_management_bp.route('/api/colors/carriers', methods=['GET'])
@api_route(cache_ttl=300)
def get_carrier_colors():
    """Get all carrier colors"""
    try:
        carriers = request.args.getlist('carriers')
        if carriers:
            colors = color_manager.get_carrier_colors(carriers)
        else:
            colors = color_manager.get_category_colors('carriers')
        
        return success_json("Carrier colors retrieved successfully", {
            'carriers': carriers if carriers else list(colors.keys()),
            'colors': colors
        })
    except Exception as e:
        logger.error(f"Error getting carrier colors: {e}")
        return error_json(f"Failed to get carrier colors: {str(e)}")

@color_management_bp.route('/api/colors/chart/<int:count>', methods=['GET'])
@api_route(cache_ttl=300)
def get_chart_colors(count: int):
    """Get chart colors for specified count"""
    try:
        if count <= 0 or count > 50:
            return validation_error_json("Count must be between 1 and 50")
        
        colors = color_manager.get_chart_colors(count)
        return success_json(f"Generated {len(colors)} chart colors", {
            'count': count,
            'colors': colors
        })
    except Exception as e:
        logger.error(f"Error getting chart colors for count {count}: {e}")
        return error_json(f"Failed to get chart colors: {str(e)}")

@color_management_bp.route('/api/colors/set', methods=['POST'])
@api_route(required_json_fields=['category', 'item', 'color'])
def set_color():
    """Set color for specific category and item"""
    try:
        data = request.get_json()
        category = data['category']
        item = data['item']
        color = data['color']
        
        # Validate color format (basic hex validation)
        if not color.startswith('#') or len(color) != 7:
            return validation_error_json("Color must be a valid hex color (e.g., #FF0000)")
        
        success = color_manager.set_color(category, item, color)
        if success:
            return success_json(f"Color set for {category}.{item}", {
                'category': category,
                'item': item,
                'color': color
            })
        else:
            return error_json("Failed to save color")
            
    except Exception as e:
        logger.error(f"Error setting color: {e}")
        return error_json(f"Failed to set color: {str(e)}")

@color_management_bp.route('/api/colors/set-multiple', methods=['POST'])
@api_route(required_json_fields=['category', 'colors'])
def set_multiple_colors():
    """Set multiple colors for a category"""
    try:
        data = request.get_json()
        category = data['category']
        colors = data['colors']
        
        if not isinstance(colors, dict):
            return validation_error_json("Colors must be a dictionary")
        
        # Validate all colors
        for item, color in colors.items():
            if not color.startswith('#') or len(color) != 7:
                return validation_error_json(f"Invalid color format for {item}: {color}")
        
        success = color_manager.set_colors(category, colors)
        if success:
            return success_json(f"Set {len(colors)} colors for category '{category}'", {
                'category': category,
                'colors': colors,
                'count': len(colors)
            })
        else:
            return error_json("Failed to save colors")
            
    except Exception as e:
        logger.error(f"Error setting multiple colors: {e}")
        return error_json(f"Failed to set colors: {str(e)}")

@color_management_bp.route('/api/colors/reset', methods=['POST'])
@api_route()
def reset_colors():
    """Reset colors to defaults"""
    try:
        data = request.get_json() or {}
        category = data.get('category')
        
        success = color_manager.reset_to_defaults(category)
        if success:
            message = f"Reset colors for category '{category}'" if category else "Reset all colors to defaults"
            return success_json(message, {
                'category': category,
                'reset_all': category is None
            })
        else:
            return error_json("Failed to reset colors")
            
    except Exception as e:
        logger.error(f"Error resetting colors: {e}")
        return error_json(f"Failed to reset colors: {str(e)}")

@color_management_bp.route('/api/colors/export/js', methods=['GET'])
@api_route(cache_ttl=600)
def export_colors_for_js():
    """Export colors as JavaScript object"""
    try:
        js_export = color_manager.export_colors_for_js()
        
        response = current_app.response_class(
            js_export,
            mimetype='application/javascript'
        )
        response.headers['Cache-Control'] = 'public, max-age=600'
        return response
        
    except Exception as e:
        logger.error(f"Error exporting colors for JS: {e}")
        return error_json(f"Failed to export colors: {str(e)}")

@color_management_bp.route('/api/colors/palette', methods=['POST'])
@api_route(required_json_fields=['category', 'items'])
def get_color_palette():
    """Get color palette for multiple items in a category"""
    try:
        data = request.get_json()
        category = data['category']
        items = data['items']
        
        if not isinstance(items, list):
            return validation_error_json("Items must be a list")
        
        palette = color_manager.get_color_palette(category, items)
        return success_json(f"Generated palette for {len(items)} items in '{category}'", {
            'category': category,
            'items': items,
            'palette': palette
        })
        
    except Exception as e:
        logger.error(f"Error getting color palette: {e}")
        return error_json(f"Failed to get color palette: {str(e)}")

@color_management_bp.route('/api/colors/gradient/<gradient_name>', methods=['GET'])
@api_route(cache_ttl=300)
def get_gradient(gradient_name: str):
    """Get gradient colors"""
    try:
        gradient = color_manager.get_gradient(gradient_name)
        return success_json(f"Gradient '{gradient_name}' retrieved", {
            'gradient_name': gradient_name,
            'colors': gradient
        })
    except Exception as e:
        logger.error(f"Error getting gradient {gradient_name}: {e}")
        return error_json(f"Failed to get gradient: {str(e)}")

@color_management_bp.route('/api/colors/theme/<theme_name>', methods=['GET'])
@api_route(cache_ttl=300)
def get_theme_colors(theme_name: str = 'light'):
    """Get theme colors"""
    try:
        theme_colors = color_manager.get_theme_colors(theme_name)
        return success_json(f"Theme '{theme_name}' colors retrieved", {
            'theme': theme_name,
            'colors': theme_colors
        })
    except Exception as e:
        logger.error(f"Error getting theme {theme_name}: {e}")
        return error_json(f"Failed to get theme colors: {str(e)}")

@color_management_bp.route('/api/colors/validate', methods=['POST'])
@api_route(required_json_fields=['color'])
def validate_color():
    """Validate color format"""
    try:
        data = request.get_json()
        color = data['color']
        
        # Basic hex color validation
        is_valid = (
            isinstance(color, str) and
            color.startswith('#') and
            len(color) == 7 and
            all(c in '0123456789ABCDEFabcdef' for c in color[1:])
        )
        
        result = {
            'color': color,
            'valid': is_valid,
            'format': 'hex' if is_valid else 'invalid'
        }
        
        if is_valid:
            # Add additional color information
            hex_color = color.lstrip('#')
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            
            result.update({
                'rgb': f"rgb({r}, {g}, {b})",
                'rgba_50': f"rgba({r}, {g}, {b}, 0.5)",
                'brightness': (r * 299 + g * 587 + b * 114) / 1000,
                'is_light': (r * 299 + g * 587 + b * 114) / 1000 > 127
            })
        
        return success_json(
            f"Color {color} is {'valid' if is_valid else 'invalid'}",
            result
        )
        
    except Exception as e:
        logger.error(f"Error validating color: {e}")
        return error_json(f"Failed to validate color: {str(e)}")

@color_management_bp.route('/api/colors/stats', methods=['GET'])
@api_route(cache_ttl=300)
def get_color_stats():
    """Get color configuration statistics"""
    try:
        all_colors = color_manager.get_all_colors()
        
        stats = {
            'total_categories': len(all_colors),
            'categories': {},
            'total_colors': 0
        }
        
        for category, colors in all_colors.items():
            if isinstance(colors, dict):
                count = len(colors)
                stats['categories'][category] = {
                    'count': count,
                    'items': list(colors.keys())
                }
                stats['total_colors'] += count
            else:
                stats['categories'][category] = {
                    'count': 1 if colors else 0,
                    'type': type(colors).__name__
                }
        
        return success_json("Color statistics retrieved", stats)
        
    except Exception as e:
        logger.error(f"Error getting color stats: {e}")
        return error_json(f"Failed to get color statistics: {str(e)}")

def register_color_management_bp(app):
    """Register the color management blueprint with the Flask app"""
    try:
        # Initialize color manager with app
        color_manager.init_app(app)
        
        # Register blueprint
        app.register_blueprint(color_management_bp)
        logger.info("Color Management Blueprint registered successfully")
    except Exception as e:
        logger.error(f"Failed to register Color Management Blueprint: {e}")
        raise