# services/data_service.py
"""
Data Service Layer
Handles file operations, template management, and document handling
"""
import os
import logging
from typing import Dict, List, Any, Optional
from werkzeug.datastructures import FileStorage

from utils.constants import TEMPLATE_FILES
from utils.helpers import ensure_directory, get_file_info

logger = logging.getLogger(__name__)

class DataService:
    """
    Service for data and file operations
    Handles uploads, templates, and document management
    """
    
    def __init__(self, project_path: str = None):
        self.project_path = project_path
        
        # Initialize paths from Flask config if not provided
        if not project_path:
            from flask import current_app
            self.project_path = current_app.config.get('CURRENT_PROJECT_PATH')
            self.template_folder = current_app.config.get('TEMPLATE_FOLDER', 'static/templates')
        else:
            self.template_folder = 'static/templates'
        
        # Template type mapping
        self.template_mapping = {
            'data_input': {
                'file': 'input_demand_file.xlsx',
                'description': 'Data input template for demand forecasting'
            },
            'load_curve': {
                'file': 'load_curve_template.xlsx', 
                'description': 'Load curve template for profile generation'
            },
            'pypsa_input': {
                'file': 'pypsa_input_template.xlsx',
                'description': 'PyPSA model input template'
            },
            'input_demand_file': {
                'file': 'input_demand_file.xlsx',
                'description': 'Main demand input file template'
            },
            'load_profile_excel': {
                'file': 'load_profile.xlsx',
                'description': 'Load profile Excel template'
            }
        }
    
    def save_uploaded_file(self, file: FileStorage, filename: str) -> Dict[str, Any]:
        """
        Save uploaded file to project inputs directory
        
        Args:
            file: Uploaded file object
            filename: Secure filename
            
        Returns:
            Dict with file information
        """
        try:
            if not self.project_path:
                raise ValueError("No project path configured")
            
            # Create inputs directory if needed
            inputs_dir = os.path.join(self.project_path, 'inputs')
            ensure_directory(inputs_dir)
            
            # Save file
            file_path = os.path.join(inputs_dir, filename)
            file.save(file_path)
            
            # Get file info
            file_info = get_file_info(file_path)
            
            logger.info(f"Saved uploaded file: {file_path}")
            
            return {
                'filename': filename,
                'file_path': file_path,
                'file_info': file_info,
                'success': True
            }
            
        except Exception as e:
            logger.exception(f"Error saving uploaded file {filename}: {e}")
            raise
    
    def get_available_templates(self) -> List[str]:
        """Get list of available template types"""
        return list(self.template_mapping.keys())
    
    def get_template_path(self, template_type: str) -> Optional[str]:
        """
        Get file path for a template type
        
        Args:
            template_type: Type of template to get
            
        Returns:
            File path or None if not found
        """
        try:
            if template_type not in self.template_mapping:
                return None
            
            template_info = self.template_mapping[template_type]
            template_filename = template_info['file']
            
            template_path = os.path.join(self.template_folder, template_filename)
            
            # Check if file exists
            if os.path.exists(template_path):
                return template_path
            
            logger.warning(f"Template file not found: {template_path}")
            return None
            
        except Exception as e:
            logger.exception(f"Error getting template path for {template_type}: {e}")
            return None
    
    def get_document_path(self, filename: str) -> Optional[str]:
        """
        Get path for documentation files
        
        Args:
            filename: Document filename
            
        Returns:
            File path or None if not found
        """
        try:
            document_path = os.path.join(self.template_folder, filename)
            
            if os.path.exists(document_path):
                return document_path
            
            logger.warning(f"Document file not found: {document_path}")
            return None
            
        except Exception as e:
            logger.exception(f"Error getting document path for {filename}: {e}")
            return None
    
    def get_template_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about all templates
        
        Returns:
            Dict with template information
        """
        try:
            templates_info = {}
            
            for template_type, template_config in self.template_mapping.items():
                template_filename = template_config['file']
                template_path = os.path.join(self.template_folder, template_filename)
                
                # Get file info
                file_info = get_file_info(template_path)
                
                templates_info[template_type] = {
                    'filename': template_filename,
                    'description': template_config['description'],
                    'available': file_info['exists'],
                    'size_mb': file_info.get('size_mb', 0),
                    'modified': file_info.get('modified'),
                    'path': template_path
                }
            
            return templates_info
            
        except Exception as e:
            logger.exception(f"Error getting template info: {e}")
            return {}
    
    def validate_template_availability(self) -> Dict[str, Any]:
        """
        Validate that all required templates are available
        
        Returns:
            Validation result with missing templates
        """
        try:
            missing_templates = []
            available_templates = []
            
            for template_type in self.template_mapping.keys():
                template_path = self.get_template_path(template_type)
                if template_path and os.path.exists(template_path):
                    available_templates.append(template_type)
                else:
                    missing_templates.append(template_type)
            
            return {
                'all_available': len(missing_templates) == 0,
                'available_templates': available_templates,
                'missing_templates': missing_templates,
                'total_templates': len(self.template_mapping),
                'available_count': len(available_templates)
            }
            
        except Exception as e:
            logger.exception(f"Error validating template availability: {e}")
            return {
                'all_available': False,
                'error': str(e)
            }
    
    def get_project_file_info(self, relative_path: str) -> Dict[str, Any]:
        """
        Get information about a file in the project
        
        Args:
            relative_path: Path relative to project root
            
        Returns:
            File information dict
        """
        try:
            if not self.project_path:
                raise ValueError("No project path configured")
            
            file_path = os.path.join(self.project_path, relative_path)
            
            # Security check - ensure path is within project
            abs_project = os.path.abspath(self.project_path)
            abs_file = os.path.abspath(file_path)
            
            if not abs_file.startswith(abs_project):
                raise ValueError("File path outside project directory")
            
            return get_file_info(file_path)
            
        except Exception as e:
            logger.exception(f"Error getting project file info for {relative_path}: {e}")
            return {'exists': False, 'error': str(e)}
    
    def list_project_files(self, subdirectory: str = '', 
                          extensions: List[str] = None) -> List[Dict[str, Any]]:
        """
        List files in project directory
        
        Args:
            subdirectory: Subdirectory within project
            extensions: Filter by file extensions
            
        Returns:
            List of file information dicts
        """
        try:
            if not self.project_path:
                return []
            
            search_dir = os.path.join(self.project_path, subdirectory)
            if not os.path.exists(search_dir):
                return []
            
            files = []
            for filename in os.listdir(search_dir):
                file_path = os.path.join(search_dir, filename)
                
                if not os.path.isfile(file_path):
                    continue
                
                # Filter by extensions if specified
                if extensions:
                    file_ext = os.path.splitext(filename)[1].lower()
                    if file_ext not in extensions:
                        continue
                
                file_info = get_file_info(file_path)
                file_info['relative_path'] = os.path.join(subdirectory, filename)
                files.append(file_info)
            
            # Sort by modification time (newest first)
            files.sort(key=lambda x: x.get('modified', 0), reverse=True)
            
            return files
            
        except Exception as e:
            logger.exception(f"Error listing project files in {subdirectory}: {e}")
            return []
    
    def get_upload_directory_info(self) -> Dict[str, Any]:
        """
        Get information about the project upload directory
        
        Returns:
            Directory information
        """
        try:
            if not self.project_path:
                return {'available': False, 'error': 'No project path'}
            
            inputs_dir = os.path.join(self.project_path, 'inputs')
            
            # Ensure directory exists
            if not os.path.exists(inputs_dir):
                ensure_directory(inputs_dir)
            
            # Get directory info
            files = self.list_project_files('inputs')
            
            return {
                'available': True,
                'path': inputs_dir,
                'file_count': len(files),
                'files': files,
                'total_size_mb': sum(f.get('size_mb', 0) for f in files)
            }
            
        except Exception as e:
            logger.exception(f"Error getting upload directory info: {e}")
            return {'available': False, 'error': str(e)}
    
    def cleanup_old_uploads(self, max_age_days: int = 30) -> Dict[str, Any]:
        """
        Clean up old uploaded files
        
        Args:
            max_age_days: Maximum age of files to keep
            
        Returns:
            Cleanup results
        """
        try:
            if not self.project_path:
                return {'success': False, 'error': 'No project path'}
            
            import time
            cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
            
            inputs_dir = os.path.join(self.project_path, 'inputs')
            if not os.path.exists(inputs_dir):
                return {'success': True, 'cleaned_files': []}
            
            cleaned_files = []
            failed_files = []
            
            for filename in os.listdir(inputs_dir):
                file_path = os.path.join(inputs_dir, filename)
                
                if not os.path.isfile(file_path):
                    continue
                
                try:
                    file_mtime = os.path.getmtime(file_path)
                    if file_mtime < cutoff_time:
                        os.remove(file_path)
                        cleaned_files.append(filename)
                        logger.info(f"Cleaned up old file: {filename}")
                except Exception as file_error:
                    failed_files.append({'file': filename, 'error': str(file_error)})
            
            return {
                'success': True,
                'cleaned_files': cleaned_files,
                'failed_files': failed_files,
                'total_cleaned': len(cleaned_files)
            }
            
        except Exception as e:
            logger.exception(f"Error during cleanup: {e}")
            return {'success': False, 'error': str(e)}