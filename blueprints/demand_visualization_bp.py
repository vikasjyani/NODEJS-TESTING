# blueprints/demand_visualization_bp.py
"""
Enhanced Demand Visualization Blueprint
Clean API endpoints with proper filtering and comparison functionality
"""
import os
import logging
from flask import Blueprint, request, jsonify, render_template, send_file, current_app
from datetime import datetime

from services.demand_visualization_service import DemandVisualizationService
from utils.common_decorators import require_project

logger = logging.getLogger(__name__)

demand_visualization_bp = Blueprint(
    'demand_visualization',
    __name__,
    template_folder='../templates',
    static_folder='../static'
)

def get_service():
    """Get demand visualization service instance"""
    project_path = current_app.config.get('CURRENT_PROJECT_PATH')
    if not project_path:
        raise ValueError("No project selected")
    return DemandVisualizationService(project_path)

# ===== MAIN PAGE ROUTE =====
@demand_visualization_bp.route('/')
@require_project
def demand_visualization_route():
    """Main demand visualization page"""
    try:
        service = get_service()
        scenarios = service.get_available_scenarios()
        
        context = {
            'page_title': 'Demand Visualization & Analysis',
            'scenarios': [
                {
                    'name': s.name,
                    'sectors_count': s.sectors_count,
                    'year_range': s.year_range,
                    'file_count': s.file_count,
                    'last_modified': s.last_modified
                }
                for s in scenarios
            ],
            'has_scenarios': len(scenarios) > 0,
            'current_project': current_app.config.get('CURRENT_PROJECT')
        }
        
        return render_template('demand_visualization.html', **context)
        
    except Exception as e:
        logger.exception(f"Error loading demand visualization page: {e}")
        return render_template('errors/500.html', error=str(e)), 500

# ===== API ENDPOINTS =====

@demand_visualization_bp.route('/api/scenarios')
def api_get_scenarios():
    """Get available scenarios"""
    try:
        service = get_service()
        scenarios = service.get_available_scenarios()
        
        scenarios_data = [
            {
                'name': s.name,
                'sectors_count': s.sectors_count,
                'year_range': s.year_range,
                'file_count': s.file_count,
                'has_data': s.has_data,
                'last_modified': s.last_modified
            }
            for s in scenarios
        ]
        
        return jsonify({
            'success': True,
            'scenarios': scenarios_data,
            'total_count': len(scenarios_data)
        })
        
    except Exception as e:
        logger.exception(f"Error getting scenarios: {e}")
        return jsonify({'error': str(e)}), 500

@demand_visualization_bp.route('/api/scenario/<scenario_name>')
def api_get_scenario_data(scenario_name):
    """Get scenario data with filters"""
    try:
        service = get_service()
        
        # Get filter parameters
        filters = {
            'unit': request.args.get('unit', 'TWh'),
            'start_year': request.args.get('start_year', type=int),
            'end_year': request.args.get('end_year', type=int),
            'sectors': request.args.getlist('sectors') if request.args.getlist('sectors') else []
        }
        
        # Remove None values
        filters = {k: v for k, v in filters.items() if v is not None and v != []}
        
        data = service.get_scenario_data(scenario_name, filters)
        
        if 'error' in data:
            return jsonify({'error': data['error']}), 404
        
        return jsonify({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        logger.exception(f"Error getting scenario data: {e}")
        return jsonify({'error': str(e)}), 500

@demand_visualization_bp.route('/api/comparison')
def api_get_comparison():
    """Get comparison data between two scenarios"""
    try:
        scenario1 = request.args.get('scenario1')
        scenario2 = request.args.get('scenario2')
        
        if not scenario1 or not scenario2:
            return jsonify({'error': 'Both scenario1 and scenario2 parameters required'}), 400
        
        service = get_service()
        
        # Get filter parameters
        filters = {
            'unit': request.args.get('unit', 'TWh'),
            'start_year': request.args.get('start_year', type=int),
            'end_year': request.args.get('end_year', type=int),
            'sectors': request.args.getlist('sectors') if request.args.getlist('sectors') else []
        }
        
        # Remove None values
        filters = {k: v for k, v in filters.items() if v is not None and v != []}
        
        comparison_data = service.get_comparison_data(scenario1, scenario2, filters)
        
        if 'error' in comparison_data:
            return jsonify({'error': comparison_data['error']}), 404
        
        return jsonify({
            'success': True,
            'comparison': comparison_data
        })
        
    except Exception as e:
        logger.exception(f"Error getting comparison data: {e}")
        return jsonify({'error': str(e)}), 500

@demand_visualization_bp.route('/api/model-selection/<scenario_name>', methods=['GET', 'POST'])
def api_model_selection(scenario_name):
    """Get or save model selection configuration"""
    try:
        service = get_service()
        
        if request.method == 'GET':
            config = service.get_model_selection(scenario_name)
            return jsonify({
                'success': True,
                'config': config
            })
        
        elif request.method == 'POST':
            if not request.is_json:
                return jsonify({'error': 'JSON data required'}), 400
            
            data = request.get_json()
            model_selection = data.get('model_selection', {})
            
            if not model_selection:
                return jsonify({'error': 'Model selection data required'}), 400
            
            result = service.save_model_selection(scenario_name, model_selection)
            
            if 'error' in result:
                return jsonify({'error': result['error']}), 500
            
            return jsonify({
                'success': True,
                'message': result['message']
            })
            
    except Exception as e:
        logger.exception(f"Error with model selection: {e}")
        return jsonify({'error': str(e)}), 500

@demand_visualization_bp.route('/api/td-losses/<scenario_name>', methods=['GET', 'POST'])
def api_td_losses(scenario_name):
    """Get or save T&D losses configuration"""
    try:
        service = get_service()
        
        if request.method == 'GET':
            config = service.get_td_losses(scenario_name)
            return jsonify({
                'success': True,
                'config': config
            })
        
        elif request.method == 'POST':
            if not request.is_json:
                return jsonify({'error': 'JSON data required'}), 400
            
            data = request.get_json()
            td_losses = data.get('td_losses', [])
            
            if not td_losses:
                return jsonify({'error': 'T&D losses data required'}), 400
            
            result = service.save_td_losses(scenario_name, td_losses)
            
            if 'error' in result:
                return jsonify({'error': result['error']}), 500
            
            return jsonify({
                'success': True,
                'message': result['message']
            })
            
    except Exception as e:
        logger.exception(f"Error with T&D losses: {e}")
        return jsonify({'error': str(e)}), 500

@demand_visualization_bp.route('/api/consolidated/<scenario_name>', methods=['POST'])
def api_generate_consolidated(scenario_name):
    """Generate consolidated results"""
    try:
        if not request.is_json:
            return jsonify({'error': 'JSON data required'}), 400
        
        data = request.get_json()
        model_selection = data.get('model_selection', {})
        td_losses = data.get('td_losses', [])
        filters = data.get('filters', {})
        
        if not model_selection:
            return jsonify({'error': 'Model selection required'}), 400
        
        if not td_losses:
            return jsonify({'error': 'T&D losses configuration required'}), 400
        
        service = get_service()
        result = service.generate_consolidated_results(scenario_name, model_selection, td_losses, filters)
        
        if 'error' in result:
            return jsonify({'error': result['error']}), 500
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.exception(f"Error generating consolidated results: {e}")
        return jsonify({'error': str(e)}), 500

@demand_visualization_bp.route('/api/analysis/<scenario_name>')
def api_get_analysis(scenario_name):
    """Get analysis summary"""
    try:
        service = get_service()
        
        # Get filter parameters
        filters = {
            'unit': request.args.get('unit', 'TWh'),
            'start_year': request.args.get('start_year', type=int),
            'end_year': request.args.get('end_year', type=int),
            'sectors': request.args.getlist('sectors') if request.args.getlist('sectors') else []
        }
        
        # Remove None values
        filters = {k: v for k, v in filters.items() if v is not None and v != []}
        
        analysis = service.get_analysis_summary(scenario_name, filters)
        
        if 'error' in analysis:
            return jsonify({'error': analysis['error']}), 404
        
        return jsonify({
            'success': True,
            'analysis': analysis
        })
        
    except Exception as e:
        logger.exception(f"Error getting analysis: {e}")
        return jsonify({'error': str(e)}), 500

@demand_visualization_bp.route('/api/export/<scenario_name>')
def api_export_data(scenario_name):
    """Export data to CSV"""
    try:
        service = get_service()
        
        data_type = request.args.get('type', 'consolidated')  # 'consolidated' or 'scenario'
        
        # Get filter parameters for scenario export
        filters = None
        if data_type == 'scenario':
            filters = {
                'unit': request.args.get('unit', 'TWh'),
                'start_year': request.args.get('start_year', type=int),
                'end_year': request.args.get('end_year', type=int),
                'sectors': request.args.getlist('sectors') if request.args.getlist('sectors') else []
            }
            # Remove None values
            filters = {k: v for k, v in filters.items() if v is not None and v != []}
        
        file_path = service.export_data(scenario_name, data_type, filters)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'Export file not found'}), 404
        
        # Generate download filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        download_name = f"{scenario_name}_{data_type}_{timestamp}.csv"
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=download_name,
            mimetype='text/csv'
        )
        
    except Exception as e:
        logger.exception(f"Error exporting data: {e}")
        return jsonify({'error': str(e)}), 500

@demand_visualization_bp.route('/api/validate/<scenario_name>')
def api_validate_scenario(scenario_name):
    """Validate scenario data and configuration"""
    try:
        service = get_service()
        
        # Check if scenario exists and has data
        scenarios = service.get_available_scenarios()
        scenario_info = next((s for s in scenarios if s.name == scenario_name), None)
        
        if not scenario_info:
            return jsonify({
                'valid': False,
                'error': f"Scenario '{scenario_name}' not found"
            })
        
        # Check configurations
        model_config = service.get_model_selection(scenario_name)
        td_losses_config = service.get_td_losses(scenario_name)
        
        # Get basic scenario data to validate structure
        scenario_data = service.get_scenario_data(scenario_name, {'unit': 'TWh'})
        
        validation_result = {
            'valid': True,
            'scenario_info': {
                'name': scenario_info.name,
                'sectors_count': scenario_info.sectors_count,
                'year_range': scenario_info.year_range,
                'has_data': scenario_info.has_data
            },
            'configurations': {
                'has_model_selection': bool(model_config.get('model_selection')),
                'has_td_losses': bool(td_losses_config.get('td_losses')),
                'model_selection_count': len(model_config.get('model_selection', {})),
                'td_losses_count': len(td_losses_config.get('td_losses', []))
            },
            'data_validation': {
                'has_sector_data': 'error' not in scenario_data,
                'sectors_with_data': len(scenario_data.get('sectors', {})) if 'error' not in scenario_data else 0,
                'available_models': scenario_data.get('available_models', []) if 'error' not in scenario_data else []
            }
        }
        
        return jsonify({
            'success': True,
            'validation': validation_result
        })
        
    except Exception as e:
        logger.exception(f"Error validating scenario: {e}")
        return jsonify({'error': str(e)}), 500

# ===== CHART DATA API ENDPOINTS =====

@demand_visualization_bp.route('/api/chart/sector/<scenario_name>/<sector_name>', methods=['GET'])
def get_sector_chart_data(scenario_name, sector_name):
    """Get chart data for a specific sector"""
    try:
        service = get_service()
        
        # Get filters from query parameters
        filters = {
            'unit': request.args.get('unit', 'TWh'),
            'start_year': request.args.get('start_year', type=int),
            'end_year': request.args.get('end_year', type=int),
            'sectors': request.args.getlist('sectors') or None
        }
        
        chart_type = request.args.get('chart_type', 'line')
        
        chart_data = service.generate_sector_chart_data(
            scenario_name=scenario_name,
            sector_name=sector_name,
            chart_type=chart_type,
            filters=filters
        )
        
        return jsonify(chart_data)
    except Exception as e:
        logger.exception(f"Error getting sector chart data: {e}")
        return jsonify({'error': str(e)}), 500

@demand_visualization_bp.route('/api/chart/sector-comparison/<scenario_name>', methods=['POST'])
def get_sector_comparison_chart_data(scenario_name):
    """Get chart data for comparing multiple sectors"""
    try:
        service = get_service()
        data = request.get_json() or {}
        
        sectors = data.get('sectors', [])
        selected_models = data.get('selected_models', {})
        chart_type = data.get('chart_type', 'line')
        filters = data.get('filters', {})
        
        if not sectors:
            return jsonify({'error': 'No sectors specified for comparison'}), 400
        
        chart_data = service.generate_sector_comparison_chart_data(
            scenario_name=scenario_name,
            sectors=sectors,
            selected_models=selected_models,
            chart_type=chart_type,
            filters=filters
        )
        
        return jsonify(chart_data)
    except Exception as e:
        logger.exception(f"Error getting sector comparison chart data: {e}")
        return jsonify({'error': str(e)}), 500

@demand_visualization_bp.route('/api/chart/model-comparison/<scenario_name>/<sector_name>', methods=['POST'])
def get_model_comparison_chart_data(scenario_name, sector_name):
    """Get chart data for comparing different models"""
    try:
        service = get_service()
        data = request.get_json() or {}
        
        models = data.get('models')
        filters = data.get('filters', {})
        
        chart_data = service.generate_model_comparison_chart_data(
            scenario_name=scenario_name,
            sector_name=sector_name,
            models=models,
            filters=filters
        )
        
        return jsonify(chart_data)
    except Exception as e:
        logger.exception(f"Error getting model comparison chart data: {e}")
        return jsonify({'error': str(e)}), 500

@demand_visualization_bp.route('/api/chart/consolidated/<scenario_name>', methods=['GET'])
def get_consolidated_chart_data(scenario_name):
    """Get chart data for consolidated results"""
    try:
        service = get_service()
        
        chart_type = request.args.get('chart_type', 'stacked_bar')
        filters = {
            'unit': request.args.get('unit', 'TWh')
        }
        
        chart_data = service.generate_consolidated_chart_data(
            scenario_name=scenario_name,
            chart_type=chart_type,
            filters=filters
        )
        
        return jsonify(chart_data)
    except Exception as e:
        logger.exception(f"Error getting consolidated chart data: {e}")
        return jsonify({'error': str(e)}), 500

@demand_visualization_bp.route('/api/chart/td-losses/<scenario_name>', methods=['GET'])
def get_td_losses_chart_data(scenario_name):
    """Get chart data for T&D losses visualization"""
    try:
        service = get_service()
        
        chart_data = service.generate_td_losses_chart_data(
            scenario_name=scenario_name
        )
        
        return jsonify(chart_data)
    except Exception as e:
        logger.exception(f"Error getting T&D losses chart data: {e}")
        return jsonify({'error': str(e)}), 500

# ===== ERROR HANDLERS =====
@demand_visualization_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@demand_visualization_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

def register_demand_visualization_bp(app):
    """Register the demand visualization blueprint"""
    try:
        app.register_blueprint(demand_visualization_bp, url_prefix='/demand_visualization')
        logger.info("Demand Visualization Blueprint registered successfully")
    except Exception as e:
        logger.error(f"Failed to register Demand Visualization Blueprint: {e}")
        raise