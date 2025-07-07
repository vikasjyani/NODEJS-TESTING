# utils/helpers.py
"""
Helper utilities for the KSEB Energy Futures Platform
"""
import os
import shutil
import pandas as pd
import numpy as np
import json
import logging
from pathlib import Path
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app

from .constants import (
    PROJECT_STRUCTURE, TEMPLATE_FILES, ERROR_MESSAGES, 
    VALIDATION_RULES, DEFAULT_PATHS
)

logger = logging.getLogger(__name__)

def slugify(text):
    """
    Convert text to a safe slug for use in IDs and URLs.
    """
    import re
    from unicodedata import normalize
    
    # Convert to lowercase and normalize unicode
    text = str(text).lower().strip()
    text = normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    
    # Replace spaces and special characters with hyphens
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    
    return text

def safe_filename(filename):
    """Create a safe filename using werkzeug's secure_filename"""
    if not filename:
        return None
    return secure_filename(filename)

def ensure_directory(path):
    """Ensure directory exists, create if it doesn't"""
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {path}: {e}")
        return False

def create_project_structure(project_path, template_folder=None):
    """
    Create the standard project folder structure
    
    Args:
        project_path (str): The path where the project structure will be created
        template_folder (str, optional): Path to template folder. 
                                        If None, uses default from config
    
    Returns:
        dict: Result with success status and details
    """
    try:
        logger.info(f"Creating project structure at: {project_path}")
        
        # Create main project folder if it doesn't exist
        if not ensure_directory(project_path):
            return {
                'success': False,
                'message': f'Failed to create project directory: {project_path}'
            }
        
        # Create folder structure based on PROJECT_STRUCTURE
        created_folders = []
        for folder_name, subfolders in PROJECT_STRUCTURE.items():
            folder_path = os.path.join(project_path, folder_name)
            if ensure_directory(folder_path):
                created_folders.append(folder_name)
                
                # Create subfolders if they exist
                if isinstance(subfolders, dict):
                    for subfolder_name in subfolders.keys():
                        subfolder_path = os.path.join(folder_path, subfolder_name)
                        if ensure_directory(subfolder_path):
                            created_folders.append(f"{folder_name}/{subfolder_name}")
        
        # Copy template files to inputs folder if template folder is provided
        copied_templates = []
        if template_folder and os.path.exists(template_folder):
            inputs_folder = os.path.join(project_path, 'inputs')
            
            for template_name, dest_name in TEMPLATE_FILES.items():
                source_path = os.path.join(template_folder, template_name)
                
                if os.path.exists(source_path):
                    dest_path = os.path.join(inputs_folder, dest_name)
                    try:
                        shutil.copy2(source_path, dest_path)
                        copied_templates.append(dest_name)
                        logger.debug(f"Copied template: {template_name} -> {dest_name}")
                    except Exception as e:
                        logger.warning(f"Failed to copy template {template_name}: {e}")
                else:
                    logger.warning(f"Template file not found: {source_path}")
        
        # Create project metadata
        metadata = {
            'name': os.path.basename(project_path),
            'created': datetime.now().isoformat(),
            'last_modified': datetime.now().isoformat(),
            'version': '1.0',
            'structure_created': created_folders,
            'templates_copied': copied_templates
        }
        
        metadata_path = os.path.join(project_path, 'config', 'project.json')
        try:
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to create project metadata: {e}")
        
        logger.info(f"Project structure created successfully at {project_path}")
        return {
            'success': True,
            'message': 'Project structure created successfully',
            'created_folders': created_folders,
            'copied_templates': copied_templates,
            'metadata_path': metadata_path
        }
    
    except Exception as e:
        logger.exception(f"Error creating project structure: {e}")
        return {
            'success': False,
            'message': f'Error creating project structure: {str(e)}',
            'error': str(e)
        }

def validate_project_structure(project_path):
    """
    Validate project structure and return detailed status
    
    Args:
        project_path (str): Path to the project directory
        
    Returns:
        dict: Validation result with detailed status
    """
    try:
        # Check if the path exists
        if not os.path.exists(project_path):
            return {
                'status': 'error',
                'message': ERROR_MESSAGES['FILE_NOT_FOUND'].replace('file', f'path "{project_path}"'),
                'valid': False
            }
        
        # Check if it's a directory
        if not os.path.isdir(project_path):
            return {
                'status': 'error',
                'message': f'The path "{project_path}" is not a directory',
                'valid': False
            }
        
        # Check for required folders
        missing_folders = []
        existing_folders = []
        
        for folder_name, subfolders in PROJECT_STRUCTURE.items():
            folder_path = os.path.join(project_path, folder_name)
            
            if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
                missing_folders.append(folder_name)
            else:
                existing_folders.append(folder_name)
                
                # Check subfolders if they exist in structure
                if isinstance(subfolders, dict):
                    for subfolder_name in subfolders.keys():
                        subfolder_path = os.path.join(folder_path, subfolder_name)
                        if not os.path.exists(subfolder_path) or not os.path.isdir(subfolder_path):
                            missing_folders.append(f"{folder_name}/{subfolder_name}")
                        else:
                            existing_folders.append(f"{folder_name}/{subfolder_name}")
        
        # Check for template files in inputs folder
        inputs_folder = os.path.join(project_path, 'inputs')
        missing_templates = []
        existing_templates = []
        
        if os.path.exists(inputs_folder):
            for template_name in TEMPLATE_FILES.values():
                template_path = os.path.join(inputs_folder, template_name)
                if not os.path.exists(template_path):
                    missing_templates.append(template_name)
                else:
                    existing_templates.append(template_name)
        
        # Determine validation result
        if missing_folders:
            if len(missing_folders) == len(PROJECT_STRUCTURE):
                status = 'error'
                message = 'Invalid project structure: Required folders are missing'
                valid = False
                can_fix = True
            else:
                status = 'warning'
                message = f'Project structure is incomplete: Missing folders: {", ".join(missing_folders)}'
                valid = True
                can_fix = True
        elif missing_templates:
            status = 'warning'
            message = f'Template files missing: {", ".join(missing_templates)}'
            valid = True
            can_fix = True
        else:
            status = 'success'
            message = 'Valid project structure detected'
            valid = True
            can_fix = False
        
        return {
            'status': status,
            'message': message,
            'valid': valid,
            'can_fix': can_fix if status != 'success' else False,
            'missing_folders': missing_folders,
            'existing_folders': existing_folders,
            'missing_templates': missing_templates,
            'existing_templates': existing_templates
        }
    
    except Exception as e:
        logger.exception(f"Error validating project structure: {e}")
        return {
            'status': 'error',
            'message': f'Error validating project structure: {str(e)}',
            'valid': False,
            'error': str(e)
        }

def copy_missing_templates(project_path, missing_templates, template_folder):
    """
    Copy missing template files to the project
    
    Args:
        project_path (str): Path to the project
        missing_templates (list): List of missing template files
        template_folder (str): Path to template folder
        
    Returns:
        dict: Result of copy operation
    """
    if not missing_templates:
        return {'success': True, 'copied': [], 'message': 'No templates to copy'}
    
    if not template_folder or not os.path.exists(template_folder):
        return {
            'success': False,
            'message': 'Template folder not found or not specified',
            'copied': []
        }
    
    inputs_folder = os.path.join(project_path, 'inputs')
    if not ensure_directory(inputs_folder):
        return {
            'success': False,
            'message': 'Failed to create inputs folder',
            'copied': []
        }
    
    copied_templates = []
    failed_templates = []
    
    # Reverse lookup for template files
    template_source_map = {v: k for k, v in TEMPLATE_FILES.items()}
    
    for template_name in missing_templates:
        source_name = template_source_map.get(template_name, template_name)
        source_path = os.path.join(template_folder, source_name)
        dest_path = os.path.join(inputs_folder, template_name)
        
        try:
            if os.path.exists(source_path):
                shutil.copy2(source_path, dest_path)
                copied_templates.append(template_name)
                logger.info(f"Copied template: {template_name}")
            else:
                failed_templates.append(template_name)
                logger.warning(f"Template source not found: {source_path}")
        except Exception as e:
            failed_templates.append(template_name)
            logger.error(f"Error copying template {template_name}: {e}")
    
    success = len(failed_templates) == 0
    message = f"Copied {len(copied_templates)} templates"
    if failed_templates:
        message += f", failed to copy {len(failed_templates)} templates"
    
    return {
        'success': success,
        'copied': copied_templates,
        'failed': failed_templates,
        'message': message
    }

def find_special_symbols(df, marker):
    """Find cells with special marker symbols in DataFrame"""
    markers = []
    try:
        for i, row in df.iterrows():
            for j, value in enumerate(row):
                if isinstance(value, str) and value.startswith(marker):
                    markers.append((i, j, value[len(marker):].strip()))
    except Exception as e:
        logger.error(f"Error finding special symbols: {e}")
    return markers

def extract_table(df, start_row, start_col):
    """Extract table from DataFrame starting at specified position"""
    try:
        end_row = start_row + 1
        while end_row < len(df) and pd.notnull(df.iloc[end_row, start_col]):
            end_row += 1

        end_col = start_col + 1
        while end_col < len(df.columns) and pd.notnull(df.iloc[start_row, end_col]):
            end_col += 1

        table = df.iloc[start_row:end_row, start_col:end_col].copy()
        table.columns = table.iloc[0]
        table = table[1:].reset_index(drop=True)

        return table
    except Exception as e:
        logger.error(f"Error extracting table: {e}")
        return pd.DataFrame()

def extract_tables_by_markers(df, marker):
    """Extract multiple tables from DataFrame using marker symbols"""
    markers = find_special_symbols(df, marker)
    tables = {}
    for marker_info in markers:
        try:
            start_row, start_col, table_name = marker_info
            tables[table_name] = extract_table(df, start_row + 1, start_col)
        except Exception as e:
            logger.error(f"Error extracting table {table_name}: {e}")
            tables[table_name] = pd.DataFrame()
    return tables

def interpolate_td_losses_for_range(range_start_year, range_end_year, points):
    """
    Interpolates T&D losses for a given range of years based on specified points.

    Args:
        range_start_year (int): The first year of the desired interpolation range.
        range_end_year (int): The last year of the desired interpolation range.
        points (list of dict): A list of dictionaries, each with 'year' and 'losses' keys.
                               Must be sorted by year. Example: [{'year': 2020, 'losses': 10.0}, ...]

    Returns:
        dict: A dictionary where keys are years (int) and values are interpolated loss percentages (float).
    """
    if not points:
        # If no points, return zero losses for all years
        return {year: 0.0 for year in range(range_start_year, range_end_year + 1)}

    try:
        # Ensure points are sorted by year
        sorted_points = sorted(points, key=lambda p: p['year'])
        
        # Create arrays for interpolation
        point_years = np.array([p['year'] for p in sorted_points])
        point_losses = np.array([p['losses'] for p in sorted_points])
        
        interpolated_losses = {}
        for year_to_interpolate in range(range_start_year, range_end_year + 1):
            # Handle years outside the provided points range (extrapolation as constant)
            if year_to_interpolate < sorted_points[0]['year']:
                interpolated_losses[year_to_interpolate] = sorted_points[0]['losses']
            elif year_to_interpolate > sorted_points[-1]['year']:
                interpolated_losses[year_to_interpolate] = sorted_points[-1]['losses']
            else:
                # np.interp performs linear interpolation
                interpolated_value = np.interp(year_to_interpolate, point_years, point_losses)
                interpolated_losses[year_to_interpolate] = round(float(interpolated_value), 4)

        return interpolated_losses
    
    except Exception as e:
        logger.error(f"Error interpolating T&D losses: {e}")
        # Return zero losses as fallback
        return {year: 0.0 for year in range(range_start_year, range_end_year + 1)}

def validate_file_path(file_path, base_path=None):
    """
    Validate that a file path is safe and within allowed directories
    
    Args:
        file_path (str): The file path to validate
        base_path (str, optional): Base directory to check against
        
    Returns:
        dict: Validation result
    """
    try:
        if not file_path:
            return {'valid': False, 'message': 'File path is empty'}
        
        # Check for path traversal attempts
        if '..' in file_path or file_path.startswith('/'):
            return {'valid': False, 'message': 'Invalid file path'}
        
        # If base path provided, ensure file is within it
        if base_path:
            abs_base = os.path.abspath(base_path)
            abs_file = os.path.abspath(os.path.join(base_path, file_path))
            
            if not abs_file.startswith(abs_base):
                return {'valid': False, 'message': 'File path outside allowed directory'}
        
        return {'valid': True, 'message': 'Valid file path'}
    
    except Exception as e:
        logger.error(f"Error validating file path: {e}")
        return {'valid': False, 'message': f'Error validating path: {str(e)}'}

def get_file_info(file_path):
    """
    Get comprehensive information about a file
    
    Args:
        file_path (str): Path to the file
        
    Returns:
        dict: File information
    """
    try:
        if not os.path.exists(file_path):
            return {
                'exists': False,
                'path': file_path,
                'message': 'File does not exist'
            }
        
        stat = os.stat(file_path)
        
        return {
            'exists': True,
            'path': file_path,
            'size_bytes': stat.st_size,
            'size_mb': round(stat.st_size / (1024 * 1024), 2),
            'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'is_file': os.path.isfile(file_path),
            'is_directory': os.path.isdir(file_path),
            'extension': os.path.splitext(file_path)[1].lower()
        }
    
    except Exception as e:
        logger.error(f"Error getting file info for {file_path}: {e}")
        return {
            'exists': False,
            'path': file_path,
            'error': str(e)
        }

def cleanup_old_files(directory, max_age_days=30, file_patterns=None):
    """
    Clean up old files in a directory
    
    Args:
        directory (str): Directory to clean
        max_age_days (int): Maximum age of files to keep
        file_patterns (list, optional): File patterns to match for cleanup
        
    Returns:
        dict: Cleanup result
    """
    try:
        if not os.path.exists(directory):
            return {'success': False, 'message': 'Directory does not exist'}
        
        import time
        cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
        
        cleaned_files = []
        failed_files = []
        
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            
            # Skip directories
            if not os.path.isfile(file_path):
                continue
            
            # Check file patterns if specified
            if file_patterns:
                if not any(filename.endswith(pattern) for pattern in file_patterns):
                    continue
            
            # Check file age
            try:
                file_age = os.path.getmtime(file_path)
                if file_age < cutoff_time:
                    os.remove(file_path)
                    cleaned_files.append(filename)
            except Exception as e:
                failed_files.append({'file': filename, 'error': str(e)})
        
        return {
            'success': True,
            'cleaned_files': cleaned_files,
            'failed_files': failed_files,
            'message': f'Cleaned {len(cleaned_files)} files'
        }
    
    except Exception as e:
        logger.exception(f"Error cleaning up files: {e}")
        return {
            'success': False,
            'message': f'Error during cleanup: {str(e)}',
            'error': str(e)
        }

def validate_data_types(data, schema):
    """
    Validate data against a schema
    
    Args:
        data (dict): Data to validate
        schema (dict): Schema with field types and requirements
        
    Returns:
        dict: Validation result
    """
    errors = []
    warnings = []
    
    try:
        for field, requirements in schema.items():
            if field not in data:
                if requirements.get('required', False):
                    errors.append(f"Required field '{field}' is missing")
                continue
            
            value = data[field]
            expected_type = requirements.get('type')
            
            if expected_type and not isinstance(value, expected_type):
                try:
                    # Try to convert
                    if expected_type == int:
                        data[field] = int(value)
                    elif expected_type == float:
                        data[field] = float(value)
                    elif expected_type == str:
                        data[field] = str(value)
                    else:
                        errors.append(f"Field '{field}' should be {expected_type.__name__}")
                except (ValueError, TypeError):
                    errors.append(f"Field '{field}' cannot be converted to {expected_type.__name__}")
            
            # Check constraints
            if 'min_value' in requirements and value < requirements['min_value']:
                errors.append(f"Field '{field}' value {value} is below minimum {requirements['min_value']}")
            
            if 'max_value' in requirements and value > requirements['max_value']:
                errors.append(f"Field '{field}' value {value} is above maximum {requirements['max_value']}")
            
            if 'choices' in requirements and value not in requirements['choices']:
                errors.append(f"Field '{field}' value '{value}' not in allowed choices: {requirements['choices']}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'data': data
        }
    
    except Exception as e:
        logger.exception(f"Error validating data: {e}")
        return {
            'valid': False,
            'errors': [f"Validation error: {str(e)}"],
            'warnings': warnings,
            'data': data
        }