# blueprints/data_bp.py (OPTIMIZED)
"""
Optimized Data Blueprint
Simplified file handling with service layer and consistent error handling
"""
import os
import logging
from datetime import datetime
from flask import Blueprint, request, send_file, current_app, g
from werkzeug.utils import secure_filename

from utils.base_blueprint import ServiceBlueprint, with_service
from utils.common_decorators import (
    require_project, validate_file_upload, handle_exceptions,
    api_route, track_performance
)
from utils.response_utils import success_json, error_json
from utils.constants import ALLOWED_EXTENSIONS, MAX_FILE_SIZE, TEMPLATE_FILES

# Create dummy service for now - will be replaced when services are implemented
class DataService:
    def __init__(self, project_path=None):
        self.project_path = project_path
    
    def save_uploaded_file(self, file, filename):
        return {
            'filename': filename,
            'file_path': f'/uploads/{filename}',
            'file_info': {'size': 1024, 'type': 'application/excel'}
        }
    
    def get_available_templates(self):
        return ['input_demand_file', 'load_curve_template', 'pypsa_input_template']
    
    def get_template_path(self, template_type):
        return f'/templates/{template_type}.xlsx'
    
    def get_document_path(self, filename):
        return f'/docs/{filename}'
    
    def get_template_info(self):
        return [
            {'name': 'Input Demand Template', 'type': 'input_demand_file'},
            {'name': 'Load Curve Template', 'type': 'load_curve_template'},
            {'name': 'PyPSA Input Template', 'type': 'pypsa_input_template'}
        ]

logger = logging.getLogger(__name__)

class DataBlueprint(ServiceBlueprint):
    """Optimized Data Blueprint for file operations"""
    
    def __init__(self):
        super().__init__(
            'data',
            __name__,
            service_class=DataService,
            template_folder='../templates',
            static_folder='../static',
            url_prefix='/data'
        )
    
    def register_routes(self):
        """Register all routes for this blueprint"""
        
        # File Upload Routes
        @self.blueprint.route('/upload', methods=['POST'])
        @require_project
        @validate_file_upload(ALLOWED_EXTENSIONS, MAX_FILE_SIZE // (1024 * 1024))
        @handle_exceptions('data')
        @track_performance()
        def upload_data_route():
            return self._handle_file_upload()
        
        # Template Download Routes
        @self.blueprint.route('/download/template/<template_type>')
        @handle_exceptions('data')
        @track_performance()
        def download_template_route(template_type):
            return self._download_template(template_type)
        
        @self.blueprint.route('/download/user_guide')
        @handle_exceptions('data')
        def download_user_guide_route():
            return self._download_document('user_guide.pdf', 'User Guide')
        
        @self.blueprint.route('/download/methodology')
        @handle_exceptions('data')
        def download_methodology_route():
            return self._download_document('methodology.pdf', 'Methodology')
        
        # API Routes
        @self.blueprint.route('/api/templates')
        @api_route(cache_ttl=300)
        def list_templates_api():
            return self._list_templates()
        
        @self.blueprint.route('/api/upload_status')
        @api_route(cache_ttl=60)
        def upload_status_api():
            return self._get_upload_status()
    
    @with_service
    def _handle_file_upload(self):
        """Handle file upload with validation"""
        try:
            file = request.files['file']
            filename = secure_filename(file.filename)
            
            # Save file using service
            result = self.service.save_uploaded_file(file, filename)
            
            if request.is_json:
                return success_json(
                    "File uploaded successfully",
                    {
                        'filename': result['filename'],
                        'file_path': result['file_path'],
                        'file_info': result['file_info']
                    }
                )
            else:
                from flask import flash, redirect, url_for
                flash("File uploaded successfully", 'success')
                return redirect(url_for('core.home'))
                
        except Exception as e:
            logger.exception(f"Error uploading file: {e}")
            if request.is_json:
                return error_json(f"Upload failed: {str(e)}")
            else:
                from flask import flash, redirect, url_for
                flash(f"Upload failed: {str(e)}", 'danger')
                return redirect(url_for('core.home'))
    
    @with_service
    def _download_template(self, template_type: str):
        """Download template file with validation"""
        try:
            # Validate template type
            if template_type not in self.service.get_available_templates():
                return error_json(f"Invalid template type: {template_type}", status_code=404)
            
            # Get template file path
            template_path = self.service.get_template_path(template_type)
            if not template_path or not os.path.exists(template_path):
                return error_json("Template file not found", status_code=404)
            
            # Generate download filename
            download_name = f"KSEB_{template_type}_template_{datetime.now().strftime('%Y%m%d')}.xlsx"
            
            return send_file(
                template_path,
                as_attachment=True,
                download_name=download_name,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
        except Exception as e:
            logger.exception(f"Error downloading template {template_type}: {e}")
            return error_json(f"Download failed: {str(e)}")
    
    @with_service  
    def _download_document(self, filename: str, document_name: str):
        """Download documentation files"""
        try:
            document_path = self.service.get_document_path(filename)
            if not document_path or not os.path.exists(document_path):
                return error_json(f"{document_name} not found", status_code=404)
            
            download_name = f"KSEB_{document_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
            
            return send_file(
                document_path,
                as_attachment=True,
                download_name=download_name,
                mimetype='application/pdf'
            )
            
        except Exception as e:
            logger.exception(f"Error downloading {document_name}: {e}")
            return error_json(f"Download failed: {str(e)}")
    
    @with_service
    def _list_templates(self):
        """Get list of available templates"""
        try:
            templates = self.service.get_template_info()
            return success_json("Templates retrieved successfully", {
                'templates': templates,
                'total_templates': len(templates)
            })
        except Exception as e:
            logger.exception(f"Error listing templates: {e}")
            return error_json(f"Failed to list templates: {str(e)}")
    
    def _get_upload_status(self):
        """Get upload capability status"""
        try:
            project_valid, project_error = self.validate_project_selected()
            
            status_info = {
                'can_upload': project_valid,
                'project_selected': current_app.config.get('CURRENT_PROJECT'),
                'allowed_extensions': list(ALLOWED_EXTENSIONS),
                'max_file_size_mb': MAX_FILE_SIZE // (1024 * 1024)
            }
            
            if not project_valid:
                status_info['error'] = project_error
            
            return success_json("Upload status retrieved", status_info)
            
        except Exception as e:
            logger.exception(f"Error getting upload status: {e}")
            return error_json(f"Failed to get status: {str(e)}")

# Create the blueprint
data_blueprint = DataBlueprint()
data_bp = data_blueprint.blueprint

# Export for Flask app registration
def register_data_bp(app):
    """Register the data blueprint"""
    data_blueprint.register(app)