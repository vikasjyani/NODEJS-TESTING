# blueprints/pypsa_bp.py (OPTIMIZED - Fixed)
"""
Optimized PyPSA Blueprint - High-performance power system modeling
error handling, memory management, and standardized response patterns
Fixed to work without service layer dependency
"""
from flask import Blueprint, flash, redirect, url_for, render_template, request, jsonify, current_app, send_file, g
import os
import pandas as pd
import numpy as np
import json
import threading
import uuid
import tempfile
import asyncio
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional, Callable, Tuple
import psutil
import gc
import weakref
from functools import lru_cache, wraps
import logging
import time

# Optimization utilities
from utils.response_utils import success_json, error_json, validation_error_json
from utils.common_decorators import require_project, handle_exceptions, api_route, track_performance
from utils.constants import ERROR_MESSAGES, SUCCESS_MESSAGES

# PyPSA imports
import pypsa
import utils.pypsa_analysis_utils as pau
from utils.pypsa_runner import run_pypsa_model_core
from utils.helpers import extract_tables_by_markers, validate_file_path, get_file_info
from werkzeug.utils import secure_filename

# Initialize blueprint
pypsa_bp = Blueprint('pypsa', __name__, 
                     template_folder='../templates', 
                     static_folder='../static',
                     url_prefix='/pypsa')

logger = logging.getLogger(__name__)

# ========== Memory Management ==========

def memory_efficient_operation(func):
    """Decorator for memory-efficient operations"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        initial_memory = psutil.Process().memory_info().rss
        
        try:
            result = func(*args, **kwargs)
            return result
        except MemoryError as e:
            logger.error(f"Memory error in {func.__name__}: {e}")
            gc.collect()
            raise
        finally:
            final_memory = psutil.Process().memory_info().rss
            memory_delta = (final_memory - initial_memory) / (1024 * 1024)
            if memory_delta > 100:  # Log if more than 100MB used
                logger.warning(f"{func.__name__} used {memory_delta:.1f}MB memory")
    
    return wrapper

def cached_with_ttl(ttl_seconds=300):
    """caching with TTL"""
    def decorator(func):
        cache = {}
        timestamps = {}
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = str(args) + str(sorted(kwargs.items()))
            current_time = time.time()
            
            if (key in cache and 
                key in timestamps and 
                current_time - timestamps[key] < ttl_seconds):
                return cache[key]
            
            result = func(*args, **kwargs)
            cache[key] = result
            timestamps[key] = current_time
            
            # Cleanup old entries
            if len(cache) > 100:
                old_keys = [k for k, t in timestamps.items() 
                          if current_time - t > ttl_seconds]
                for k in old_keys:
                    cache.pop(k, None)
                    timestamps.pop(k, None)
            
            return result
        
        wrapper.cache_clear = lambda: cache.clear() or timestamps.clear()
        return wrapper
    
    return decorator

# ========== Network Management ==========

@dataclass
class NetworkCacheEntry:
    """Optimized cache entry for PyPSA networks"""
    network: pypsa.Network
    file_path: str
    file_mtime: float
    last_accessed: float
    memory_usage_mb: float
    access_count: int = 0

class NetworkManager:
    """
    High-performance network manager with intelligent caching and memory management
    """
    
    def __init__(self, max_cached_networks: int = 3, memory_threshold_mb: int = 1500):
        self.max_cached_networks = max_cached_networks
        self.memory_threshold_mb = memory_threshold_mb
        self.network_cache: Dict[str, NetworkCacheEntry] = {}
        self.cache_lock = threading.RLock()
        
        # Thread pools optimized for PyPSA operations
        self.io_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="pypsa-io")
        
        # Background cleanup
        self._start_cache_cleanup()
        
        logger.info(f"NetworkManager initialized: max_networks={max_cached_networks}, memory_threshold={memory_threshold_mb}MB")
    
    def _start_cache_cleanup(self):
        """Start optimized background cache cleanup"""
        def cleanup_worker():
            while True:
                try:
                    time.sleep(180)  # Every 3 minutes
                    self._cleanup_cache()
                except Exception as e:
                    logger.error(f"Cache cleanup error: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
    
    @memory_efficient_operation
    def load_network(self, file_path: str) -> pypsa.Network:
        """Load network with caching and memory management"""
        abs_path = os.path.abspath(file_path)
        
        with self.cache_lock:
            # Check cache first
            if abs_path in self.network_cache:
                entry = self.network_cache[abs_path]
                current_mtime = os.path.getmtime(abs_path)
                
                if entry.file_mtime == current_mtime:
                    # Update access stats
                    entry.last_accessed = time.time()
                    entry.access_count += 1
                    logger.debug(f"Cache hit for network: {abs_path}")
                    return entry.network
                else:
                    # File modified, remove from cache
                    logger.debug(f"Network file modified, removing from cache: {abs_path}")
                    del self.network_cache[abs_path]
            
            # Memory check before loading
            memory_status = self._check_memory_status()
            if memory_status['critical']:
                self._emergency_cleanup()
                
                # Recheck after cleanup
                if self._check_memory_status()['critical']:
                    raise MemoryError("Insufficient memory to load PyPSA network")
            
            # Load network with monitoring
            logger.info(f"Loading PyPSA network: {abs_path}")
            initial_memory = psutil.Process().memory_info().rss
            
            try:
                network = pypsa.Network(abs_path)
                
                final_memory = psutil.Process().memory_info().rss
                memory_usage_mb = (final_memory - initial_memory) / (1024 * 1024)
                
                # Cache if space available
                if len(self.network_cache) < self.max_cached_networks:
                    entry = NetworkCacheEntry(
                        network=network,
                        file_path=abs_path,
                        file_mtime=os.path.getmtime(abs_path),
                        last_accessed=time.time(),
                        memory_usage_mb=memory_usage_mb,
                        access_count=1
                    )
                    self.network_cache[abs_path] = entry
                    logger.info(f"Cached network: {abs_path} ({memory_usage_mb:.1f}MB)")
                else:
                    logger.info(f"Network cache full, not caching: {abs_path}")
                
                return network
                
            except Exception as e:
                logger.error(f"Error loading network {abs_path}: {e}")
                raise
    
    def _check_memory_status(self) -> Dict[str, Any]:
        """Check current memory status"""
        memory = psutil.virtual_memory()
        process_memory = psutil.Process().memory_info().rss / (1024 * 1024)
        
        return {
            'system_percent': memory.percent,
            'process_mb': process_memory,
            'critical': memory.percent > 85 or process_memory > 2000,
            'warning': memory.percent > 70 or process_memory > 1500
        }
    
    def _cleanup_cache(self):
        """Intelligent cache cleanup using LRU and access patterns"""
        with self.cache_lock:
            if not self.network_cache:
                return
            
            current_time = time.time()
            total_memory_mb = sum(entry.memory_usage_mb for entry in self.network_cache.values())
            
            if total_memory_mb > self.memory_threshold_mb:
                logger.info(f"Cache cleanup triggered: {total_memory_mb:.1f}MB > {self.memory_threshold_mb}MB")
                
                # Sort by combined score (recency + access frequency)
                def cache_score(entry):
                    recency_score = current_time - entry.last_accessed
                    frequency_score = 1000 / max(entry.access_count, 1)  # Lower is better
                    return recency_score + frequency_score
                
                sorted_entries = sorted(
                    self.network_cache.items(),
                    key=lambda x: cache_score(x[1]),
                    reverse=True  # Highest score (least valuable) first
                )
                
                # Remove least valuable entries
                for file_path, entry in sorted_entries:
                    del self.network_cache[file_path]
                    total_memory_mb -= entry.memory_usage_mb
                    logger.info(f"Removed cached network: {file_path}")
                    
                    if total_memory_mb <= self.memory_threshold_mb * 0.7:  # 30% buffer
                        break
                
                gc.collect()
    
    def _emergency_cleanup(self):
        """Emergency cleanup when memory is critical"""
        with self.cache_lock:
            logger.warning("Emergency cache cleanup - clearing all cached networks")
            self.network_cache.clear()
            gc.collect()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get detailed cache statistics"""
        with self.cache_lock:
            if not self.network_cache:
                return {
                    'cached_networks': 0,
                    'total_memory_mb': 0,
                    'average_memory_mb': 0,
                    'cache_hit_efficiency': 0
                }
            
            total_memory = sum(entry.memory_usage_mb for entry in self.network_cache.values())
            total_accesses = sum(entry.access_count for entry in self.network_cache.values())
            
            return {
                'cached_networks': len(self.network_cache),
                'total_memory_mb': round(total_memory, 2),
                'average_memory_mb': round(total_memory / len(self.network_cache), 2),
                'cache_paths': list(self.network_cache.keys()),
                'total_accesses': total_accesses,
                'memory_threshold_mb': self.memory_threshold_mb
            }

# Global network manager
network_manager = NetworkManager()

# ========== Data Extraction ==========

class OptimizedDataExtractor:
    """
    High-performance data extraction with intelligent caching and parallel processing
    """
    
    def __init__(self):
        self.extraction_cache = {}
        self.cache_timestamps = {}
        self.cache_ttl = 600  # 10 minutes for data
        self.max_cache_size = 50
    
    @cached_with_ttl(ttl_seconds=600)
    def extract_data_with_cache(self, network_path: str, extraction_func: str, 
                               snapshots_filter: Optional[pd.Index] = None,
                               **kwargs) -> Dict[str, Any]:
        """Extract data with caching and validation"""
        
        # Validate extraction function
        if not hasattr(pau, extraction_func):
            raise ValueError(f"Unknown extraction function: {extraction_func}")
        
        # Load network
        network = network_manager.load_network(network_path)
        
        # Get extraction function
        extraction_function = getattr(pau, extraction_func)
        
        # Prepare arguments with validation
        func_args = {'n': network}
        if snapshots_filter is not None:
            func_args['snapshots_slice'] = snapshots_filter
        
        # Add and validate kwargs
        import inspect
        sig = inspect.signature(extraction_function)
        valid_args = {k: v for k, v in {**func_args, **kwargs}.items() 
                     if k in sig.parameters}
        
        logger.info(f"Extracting data using {extraction_func} with {len(valid_args)} parameters")
        
        try:
            result = extraction_function(**valid_args)
            
            # Validate result
            if result is None:
                raise ValueError(f"Extraction function {extraction_func} returned None")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in data extraction {extraction_func}: {e}")
            raise

# Global data extractor
data_extractor = OptimizedDataExtractor()

# ========== Route Handlers ==========

@pypsa_bp.route('/modeling')
@require_project
@track_performance(threshold_ms=2000)
@handle_exceptions('pypsa')
def pypsa_modeling_route():
    """PyPSA modeling interface"""
    logger.info("Loading PyPSA modeling page")
    
    try:
        # Get cached page data
        page_data = get_cached_modeling_page_data()
        
        if 'error' in page_data:
            flash(f'Error loading PyPSA modeling: {page_data["error"]}', 'danger')
            return redirect(url_for('core.home'))
        
        return render_template('pypsa_modeling.html', **page_data)
        
    except Exception as e:
        logger.exception(f"Error in PyPSA modeling route: {e}")
        flash(f'Error loading PyPSA modeling: {str(e)}', 'danger')
        return redirect(url_for('core.home'))

@pypsa_bp.route('/results')
@require_project
@track_performance(threshold_ms=1500)
@handle_exceptions('pypsa')
def pypsa_results_route():
    """PyPSA results interface"""
    logger.info("Loading PyPSA results page")
    
    try:
        # Get basic page data
        page_data = get_basic_results_page_data()
        
        if 'error' in page_data:
            flash(f'Error loading results: {page_data["error"]}', 'danger')
            return redirect(url_for('core.home'))
        
        return render_template('pypsa_results.html', **page_data)
        
    except Exception as e:
        logger.exception(f"Error in PyPSA results route: {e}")
        flash(f'Error loading PyPSA results: {str(e)}', 'danger')
        return redirect(url_for('core.home'))

@pypsa_bp.route('/api/network_info/<path:network_rel_path>')
@api_route(cache_ttl=600)
def get_network_info_api(network_rel_path):
    """network info endpoint with comprehensive validation"""
    try:
        # Validate and get full path
        full_path = validate_and_get_network_path(network_rel_path)
        
        # Load network
        network = network_manager.load_network(full_path)
        
        # Extract comprehensive info
        info = extract_network_info(network, network_rel_path)
        
        return success_json("Network information retrieved successfully", info)
        
    except ValueError as e:
        return validation_error_json(str(e))
    except FileNotFoundError:
        return error_json(f'Network file not found: {network_rel_path}', status_code=404)
    except Exception as e:
        logger.exception(f"Error getting network info: {e}")
        return error_json(f"Failed to get network info: {str(e)}")

@pypsa_bp.route('/api/dispatch_data/<path:network_rel_path>')
@api_route(cache_ttl=300)
@memory_efficient_operation
def get_dispatch_data_api(network_rel_path):
    """dispatch data endpoint with optimized processing"""
    return get_pypsa_data(network_rel_path, 'dispatch_data_payload_former')

@pypsa_bp.route('/api/capacity_data/<path:network_rel_path>')
@api_route(cache_ttl=300)
@memory_efficient_operation
def get_capacity_data_api(network_rel_path):
    """capacity data endpoint"""
    return get_pypsa_data(network_rel_path, 'capacity_data_payload_former')

@pypsa_bp.route('/api/transmission_data/<path:network_rel_path>')
@api_route(cache_ttl=300)
@memory_efficient_operation
def get_transmission_data_api(network_rel_path):
    """transmission data endpoint"""
    return get_pypsa_data(network_rel_path, 'transmission_data_payload_former')

@pypsa_bp.route('/api/compare_networks', methods=['POST'])
@api_route(required_json_fields=['file_paths'])
@memory_efficient_operation
def compare_networks_api():
    """network comparison with parallel processing and validation"""
    try:
        data = request.get_json()
        file_paths = data.get('file_paths', [])
        comparison_type = data.get('comparison_type', 'capacity')
        
        # validation
        if not isinstance(file_paths, list):
            return validation_error_json("file_paths must be a list")
        
        if len(file_paths) < 2:
            return validation_error_json('At least 2 networks required for comparison')
        
        if len(file_paths) > 8:  # Reduced limit for stability
            return validation_error_json('Maximum 8 networks can be compared')
        
        # Validate all paths first
        validated_paths = []
        for file_path in file_paths:
            try:
                full_path = validate_and_get_network_path(file_path)
                validated_paths.append(full_path)
            except Exception as e:
                return validation_error_json(f"Invalid path '{file_path}': {str(e)}")
        
        # Load networks in parallel with error handling
        networks = load_networks_parallel(validated_paths)
        
        if len(networks) < 2:
            return error_json("Failed to load sufficient networks for comparison")
        
        # Perform comparison
        comparison_result = pau.compare_networks_results(
            networks, 
            comparison_type=comparison_type,
            **data.get('comparison_params', {})
        )
        
        # Add metadata
        comparison_result['metadata'] = {
            'networks_compared': len(networks),
            'comparison_type': comparison_type,
            'successful_loads': len(networks),
            'failed_loads': len(file_paths) - len(networks),
            'timestamp': time.time()
        }
        
        return success_json("Network comparison completed successfully", comparison_result)
        
    except Exception as e:
        logger.exception(f"Error comparing networks: {e}")
        return error_json(f"Network comparison failed: {str(e)}")

@pypsa_bp.route('/api/available_networks')
@api_route(cache_ttl=180)
def get_available_networks_api():
    """Get available PyPSA networks with metadata"""
    try:
        pypsa_folder = get_pypsa_results_folder()
        if not pypsa_folder or not os.path.exists(pypsa_folder):
            return success_json("No PyPSA results folder found", {'networks': []})
        
        networks = []
        
        # Scan for network files
        for root, dirs, files in os.walk(pypsa_folder):
            for file in files:
                if file.endswith('.nc'):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, pypsa_folder)
                    
                    try:
                        file_info = get_file_info(file_path)
                        networks.append({
                            'name': file,
                            'relative_path': rel_path,
                            'full_path': file_path,
                            'size_mb': file_info.get('size_mb', 0),
                            'modified': file_info.get('modified', ''),
                            'directory': os.path.dirname(rel_path)
                        })
                    except Exception as e:
                        logger.warning(f"Error processing network file {file_path}: {e}")
        
        # Sort by modification time (newest first)
        networks.sort(key=lambda x: x.get('modified', ''), reverse=True)
        
        return success_json(
            "Available networks retrieved successfully",
            {
                'networks': networks,
                'total_count': len(networks),
                'cache_stats': network_manager.get_cache_stats()
            }
        )
        
    except Exception as e:
        logger.exception(f"Error getting available networks: {e}")
        return error_json(f"Failed to get available networks: {str(e)}")

@pypsa_bp.route('/api/system_status')
@api_route(cache_ttl=60)
def get_system_status_api():
    """Get PyPSA system status and performance metrics"""
    try:
        # Memory status
        memory_status = network_manager._check_memory_status()
        
        # Cache statistics
        cache_stats = network_manager.get_cache_stats()
        
        # System metrics
        system_metrics = {
            'cpu_percent': psutil.cpu_percent(interval=0.1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage_percent': psutil.disk_usage('/').percent,
            'active_threads': threading.active_count()
        }
        
        # Determine overall health
        health_status = 'healthy'
        if memory_status['critical'] or system_metrics['memory_percent'] > 90:
            health_status = 'critical'
        elif memory_status['warning'] or system_metrics['memory_percent'] > 80:
            health_status = 'warning'
        
        return success_json(
            "System status retrieved successfully",
            {
                'health_status': health_status,
                'memory_status': memory_status,
                'cache_stats': cache_stats,
                'system_metrics': system_metrics,
                'pypsa_folder_available': get_pypsa_results_folder() is not None,
                'timestamp': time.time()
            }
        )
        
    except Exception as e:
        logger.exception(f"Error getting system status: {e}")
        return error_json(f"Failed to get system status: {str(e)}")

# ========== Helper Functions ==========

def validate_and_get_network_path(network_rel_path: str) -> str:
    """Validate network path and return full path with security"""
    if not network_rel_path or '..' in network_rel_path:
        raise ValueError("Invalid network path format")
    
    pypsa_folder = get_pypsa_results_folder()
    if not pypsa_folder:
        raise ValueError("PyPSA results folder not configured")
    
    full_path = os.path.normpath(os.path.join(pypsa_folder, network_rel_path))
    
    # security check
    if not full_path.startswith(os.path.normpath(pypsa_folder)):
        raise ValueError("Path outside allowed directory")
    
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"Network file not found: {network_rel_path}")
    
    # Additional validation for .nc files
    if not full_path.endswith('.nc'):
        raise ValueError("Invalid network file format - must be .nc file")
    
    return full_path

def get_pypsa_results_folder() -> Optional[str]:
    """Get PyPSA results folder with validation"""
    try:
        project_path = current_app.config.get('CURRENT_PROJECT_PATH')
        if not project_path:
            return None
        
        pypsa_folder = os.path.join(project_path, 'results', 'Pypsa_results')
        return pypsa_folder if os.path.exists(pypsa_folder) else None
        
    except Exception as e:
        logger.error(f"Error getting PyPSA results folder: {e}")
        return None

def load_networks_parallel(file_paths: List[str]) -> Dict[str, pypsa.Network]:
    """Load multiple networks in parallel with error handling"""
    networks = {}
    
    def load_single_network_safe(file_path: str) -> Tuple[str, Optional[pypsa.Network], Optional[str]]:
        try:
            network = network_manager.load_network(file_path)
            return file_path, network, None
        except Exception as e:
            logger.error(f"Error loading network {file_path}: {e}")
            return file_path, None, str(e)
    
    # Use thread pool with limited workers
    max_workers = min(3, len(file_paths))  # Limit concurrent loads
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(load_single_network_safe, path) for path in file_paths]
        
        for future in as_completed(futures):
            file_path, network, error = future.result()
            
            if network is not None:
                # Use filename as key for networks dict
                network_name = os.path.basename(file_path)
                networks[network_name] = network
            else:
                logger.warning(f"Failed to load network {file_path}: {error}")
    
    return networks

def get_pypsa_data(network_rel_path: str, extraction_func: str, **kwargs):
    """data extraction with comprehensive error handling"""
    try:
        # Validate path
        full_path = validate_and_get_network_path(network_rel_path)
        
        # Parse request parameters
        filters = {
            'period': request.args.get('period'),
            'start_date': request.args.get('start_date'),
            'end_date': request.args.get('end_date'),
            'resolution': request.args.get('resolution', '1H'),
        }
        
        # Get filtered snapshots
        network = network_manager.load_network(full_path)
        snapshots = get_filtered_snapshots(network, filters)
        
        # Extract data with caching
        result = data_extractor.extract_data_with_cache(
            full_path, extraction_func, snapshots, 
            **filters, **kwargs
        )
        
        # Get color palette if available
        colors = {}
        if hasattr(pau, 'get_color_palette'):
            try:
                colors = pau.get_color_palette(network)
            except Exception as e:
                logger.warning(f"Failed to get color palette: {e}")
        
        # Serialize result efficiently
        serialized_result = serialize_pypsa_data(result)
        
        # Create response
        response_key = extraction_func.replace('_payload_former', '').replace('_data', '') + '_data'
        
        response_data = {
            response_key: serialized_result,
            'colors': colors,
            'metadata': {
                'network_path': network_rel_path,
                'extraction_func': extraction_func,
                'snapshots_count': len(snapshots) if snapshots is not None else 0,
                'filters_applied': {k: v for k, v in filters.items() if v},
                'extraction_time': time.time()
            }
        }
        
        return success_json("Data extracted successfully", response_data)
        
    except ValueError as e:
        return validation_error_json(str(e))
    except FileNotFoundError as e:
        return error_json(str(e), status_code=404)
    except Exception as e:
        logger.exception(f"Error in data extraction: {e}")
        return error_json(f"Data extraction failed: {str(e)}")

def get_filtered_snapshots(network: pypsa.Network, filters: Dict) -> Optional[pd.Index]:
    """Get filtered snapshots with validation"""
    try:
        snapshots = network.snapshots
        
        if filters.get('start_date') or filters.get('end_date'):
            start_date = pd.to_datetime(filters.get('start_date')) if filters.get('start_date') else snapshots.min()
            end_date = pd.to_datetime(filters.get('end_date')) if filters.get('end_date') else snapshots.max()
            
            # Validate date range
            if start_date > end_date:
                raise ValueError("Start date must be before end date")
            
            mask = (snapshots >= start_date) & (snapshots <= end_date)
            snapshots = snapshots[mask]
        
        return snapshots if len(snapshots) > 0 else None
        
    except Exception as e:
        logger.warning(f"Error filtering snapshots: {e}")
        return network.snapshots

def serialize_pypsa_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """data serialization with memory optimization"""
    def serialize_item_safe(item):
        try:
            if isinstance(item, pd.DataFrame):
                # Memory-efficient DataFrame serialization
                if len(item) > 5000:  # Large DataFrame
                    # Sample for performance
                    sample_size = 2500
                    sampled_df = item.head(sample_size).copy()
                    logger.info(f"Large DataFrame ({len(item)} rows) sampled to {sample_size} for response")
                    return handle_nan_values_safe(sampled_df.to_dict(orient='records'))
                else:
                    return handle_nan_values_safe(item.to_dict(orient='records'))
            elif isinstance(item, pd.Series):
                return handle_nan_values_safe(item.to_dict())
            elif isinstance(item, np.ndarray):
                return handle_nan_values_safe(item.tolist())
            else:
                return handle_nan_values_safe(item)
        except Exception as e:
            logger.warning(f"Error serializing item: {e}")
            return {'error': f'Serialization failed: {str(e)}'}
    
    return {k: serialize_item_safe(v) for k, v in data.items()}

def handle_nan_values_safe(obj):
    """Safely handle NaN values in data structures"""
    try:
        if isinstance(obj, dict):
            return {k: handle_nan_values_safe(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [handle_nan_values_safe(item) for item in obj]
        elif pd.isna(obj):
            return None
        elif isinstance(obj, (np.integer, np.floating)):
            if np.isnan(obj) or np.isinf(obj):
                return None
            return float(obj) if isinstance(obj, np.floating) else int(obj)
        else:
            return obj
    except Exception:
        return None

def extract_network_info(network: pypsa.Network, network_rel_path: str) -> Dict[str, Any]:
    """Extract comprehensive network information with error handling"""
    try:
        info = {
            'network_path': network_rel_path,
            'basic_info': {
                'name': os.path.basename(network_rel_path),
                'snapshots_count': len(network.snapshots),
                'snapshot_range': {
                    'start': network.snapshots.min().isoformat() if len(network.snapshots) > 0 else None,
                    'end': network.snapshots.max().isoformat() if len(network.snapshots) > 0 else None
                }
            },
            'components': {},
            'summary_statistics': {}
        }
        
        # Component information
        for component in network.iterate_components():
            try:
                df = component.df
                info['components'][component.name] = {
                    'count': len(df),
                    'columns': df.columns.tolist() if hasattr(df, 'columns') else []
                }
            except Exception as e:
                logger.warning(f"Error processing component {component.name}: {e}")
                info['components'][component.name] = {'error': str(e)}
        
        # Summary statistics
        try:
            if hasattr(network, 'generators') and len(network.generators) > 0:
                info['summary_statistics']['total_generator_capacity'] = float(
                    network.generators['p_nom'].sum()
                )
            
            if hasattr(network, 'loads') and len(network.loads) > 0:
                info['summary_statistics']['total_load'] = float(
                    network.loads_t.p_set.sum().sum()
                ) if hasattr(network, 'loads_t') and not network.loads_t.p_set.empty else 0
                
        except Exception as e:
            logger.warning(f"Error calculating summary statistics: {e}")
            info['summary_statistics']['error'] = str(e)
        
        return info
        
    except Exception as e:
        logger.error(f"Error extracting network info: {e}")
        return {'error': str(e), 'network_path': network_rel_path}

@cached_with_ttl(ttl_seconds=300)
def get_cached_modeling_page_data() -> Dict[str, Any]:
    """Get cached modeling page data with validation"""
    try:
        project_path = current_app.config.get('CURRENT_PROJECT_PATH')
        if not project_path:
            return {'error': 'No project selected'}
        
        input_excel_path = Path(project_path) / "inputs" / "pypsa_input_template.xlsx"
        
        return {
            'current_project': current_app.config.get('CURRENT_PROJECT'),
            'input_file_exists': input_excel_path.exists(),
            'input_file_info': {
                'path': str(input_excel_path),
                'exists': input_excel_path.exists(),
                'size_mb': input_excel_path.stat().st_size / (1024*1024) if input_excel_path.exists() else 0
            },
            'optimization_engines': ['glpk', 'cbc', 'highs'],
            'solver_status': check_solver_availability(),
            'cache_stats': network_manager.get_cache_stats(),
            'system_status': network_manager._check_memory_status()
        }
    except Exception as e:
        logger.error(f"Error getting modeling page data: {e}")
        return {'error': str(e)}

def get_basic_results_page_data() -> Dict[str, Any]:
    """Get basic results page data with error handling"""
    try:
        pypsa_folder = get_pypsa_results_folder()
        scenarios = []
        
        if pypsa_folder and os.path.exists(pypsa_folder):
            # directory scanning
            for item in os.listdir(pypsa_folder):
                item_path = os.path.join(pypsa_folder, item)
                if os.path.isdir(item_path):
                    try:
                        # Count network files
                        nc_files = [f for f in os.listdir(item_path) if f.endswith('.nc')]
                        scenarios.append({
                            'name': item,
                            'path': item_path,
                            'file_count': len(nc_files),
                            'files': nc_files
                        })
                    except Exception as e:
                        logger.warning(f"Error processing scenario directory {item}: {e}")
        
        return {
            'scenarios': scenarios,
            'current_project': current_app.config.get('CURRENT_PROJECT', 'N/A'),
            'pypsa_folder': pypsa_folder,
            'cache_stats': network_manager.get_cache_stats(),
            'memory_stats': network_manager._check_memory_status()
        }
    except Exception as e:
        logger.error(f"Error getting basic results data: {e}")
        return {'error': str(e)}

def check_solver_availability() -> Dict[str, bool]:
    """Check availability of optimization solvers with detection"""
    solvers = {}
    
    solver_commands = {
        'glpk': ['glpsol', '--version'],
        'cbc': ['cbc', '-version'],
        'highs': ['highs', '--version']
    }
    
    for solver, command in solver_commands.items():
        try:
            import subprocess
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            solvers[solver] = result.returncode == 0
        except Exception:
            solvers[solver] = False
    
    return solvers

# ========== Blueprint Cleanup ==========

@pypsa_bp.teardown_request
def cleanup_pypsa_resources(exception):
    """cleanup of PyPSA resources after request"""
    if exception:
        logger.error(f"PyPSA request ended with exception: {exception}")
    
    # Periodic cache cleanup with smart timing
    if hasattr(g, 'request_count'):
        g.request_count += 1
        # More frequent cleanup for memory-intensive operations
        if g.request_count % 10 == 0:  
            network_manager._cleanup_cache()
    else:
        g.request_count = 1
    
    # Force garbage collection for large operations
    if hasattr(g, 'pypsa_large_operation'):
        gc.collect()

# Register shutdown handler
import atexit

def cleanup_on_shutdown():
    """Clean up resources on application shutdown"""
    try:
        network_manager.io_executor.shutdown(wait=True)
        logger.info("PyPSA blueprint cleanup completed")
    except Exception as e:
        logger.error(f"Error during PyPSA cleanup: {e}")

atexit.register(cleanup_on_shutdown)

# ========== Blueprint Registration ==========

def register_pypsa_bp(app):
    """Register the PyPSA blueprint"""
    try:
        app.register_blueprint(pypsa_bp)
        logger.info("PyPSA blueprint registered successfully")
    except Exception as e:
        logger.error(f"Failed to register PyPSA blueprint: {e}")
        raise