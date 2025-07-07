import os
import json
import time
from pathlib import Path
import logging
from functools import lru_cache
from flask import current_app

logger = logging.getLogger(__name__)

class FeatureManager:
    """
   Feature Manager with better error handling and caching
    """
    
    def __init__(self, app):
        self.app = app
        self.global_config_path = Path(app.root_path) / 'config' / 'features.json'
        self._ensure_global_config()
        self.cache_timeout = 300  # 5 minutes
        self.last_load_time = {}
        self.feature_cache = {}
        logger.info("FeatureManager initialized")
        
    def _ensure_global_config(self):
        """Ensure the global feature configuration file exists"""
        try:
            if not self.global_config_path.exists():
                logger.info(f"Creating default global feature configuration at {self.global_config_path}")
                os.makedirs(self.global_config_path.parent, exist_ok=True)
                default_config = {
                    "features": {
                        "demand-projection": {
                            "enabled": True, 
                            "description": "Electricity demand forecasting and projection analysis",
                            "category": "forecasting"
                        },
                        "demand-visualization": {
                            "enabled": True, 
                            "description": "Demand forecast results visualization and analysis",
                            "category": "visualization"
                        },
                        "load-curve": {
                            "enabled": True, 
                            "description": "Load curve generation and analysis",
                            "category": "load_management"
                        },
                        "load-profile-analysis": {
                            "enabled": True,
                            "description": "Load profile analysis and optimization",
                            "category": "load_management"
                        },
                        "pypsa-modeling": {
                            "enabled": True,
                            "description": "Power system modeling with PyPSA",
                            "category": "power_systems"
                        }
                    },
                    "feature_groups": {
                        "basic": ["demand-projection", "demand-visualization"],
                        "advanced": ["load-curve", "load-profile-analysis", "pypsa-modeling"],
                        "forecasting": ["demand-projection"],
                        "visualization": ["demand-visualization"],
                        "load_management": ["load-curve", "load-profile-analysis"],
                        "power_systems": ["pypsa-modeling"]
                    },
                    "metadata": {
                        "created": time.strftime('%Y-%m-%d %H:%M:%S'),
                        "version": "1.0"
                    }
                }
                
                with open(self.global_config_path, 'w') as f:
                    json.dump(default_config, f, indent=2)
                logger.info("Default feature configuration created")
        except Exception as e:
            logger.error(f"Error ensuring global config: {e}")
    
    def _load_global_features(self):
        """Load the global feature configuration with error handling"""
        try:
            if not self.global_config_path.exists():
                logger.warning("Global features config file does not exist, creating default")
                self._ensure_global_config()
            
            with open(self.global_config_path, 'r') as f:
                config = json.load(f)
                
            # Validate config structure
            if 'features' not in config:
                config['features'] = {}
            if 'feature_groups' not in config:
                config['feature_groups'] = {}
                
            return config
        except Exception as e:
            logger.error(f"Error loading global features: {e}")
            return {
                "features": {},
                "feature_groups": {},
                "error": str(e)
            }
    
    def _load_project_features(self, project_path):
        """Load project-specific feature configuration with validation"""
        if not project_path:
            return {"features": {}, "feature_groups": {}}
        
        try:
            project_config_path = Path(project_path) / 'config' / 'features.json'
            if not project_config_path.exists():
                logger.debug(f"No project-specific features config found at {project_config_path}")
                return {"features": {}, "feature_groups": {}}
            
            with open(project_config_path, 'r') as f:
                config = json.load(f)
            
            # Validate config structure
            if 'features' not in config:
                config['features'] = {}
            if 'feature_groups' not in config:
                config['feature_groups'] = {}
                
            logger.debug(f"Loaded project features from {project_config_path}")
            return config
            
        except Exception as e:
            logger.error(f"Error loading project features from {project_path}: {e}")
            return {"features": {}, "feature_groups": {}}
    
    def _needs_reload(self, cache_key):
        """Check if the feature configuration needs to be reloaded"""
        if cache_key not in self.feature_cache:
            return True
        
        last_load = self.last_load_time.get(cache_key, 0)
        return time.time() - last_load > self.cache_timeout
    
    def get_merged_features(self, project_path=None):
        """Get merged feature configuration withcaching and error handling"""
        cache_key = project_path or 'global'
        
        try:
            if self._needs_reload(cache_key):
                logger.debug(f"Loading feature configuration for {cache_key}")
                global_config = self._load_global_features()
                
                if project_path:
                    project_config = self._load_project_features(project_path)
                    
                    # Merge project-specific features into global features
                    merged_features = dict(global_config.get("features", {}))
                    for feature_id, feature_config in project_config.get("features", {}).items():
                        if feature_id in merged_features:
                            # Update existing feature with project-specific settings
                            merged_features[feature_id].update(feature_config)
                        else:
                            # Add new project-specific feature
                            merged_features[feature_id] = feature_config
                    
                    # Merge feature groups
                    merged_groups = dict(global_config.get("feature_groups", {}))
                    for group_id, features in project_config.get("feature_groups", {}).items():
                        merged_groups[group_id] = features
                    
                    config = {
                        "features": merged_features,
                        "feature_groups": merged_groups,
                        "metadata": {
                            "merged_from": ["global", "project"],
                            "project_path": project_path,
                            "loaded_at": time.strftime('%Y-%m-%d %H:%M:%S')
                        }
                    }
                else:
                    config = global_config
                    config["metadata"] = config.get("metadata", {})
                    config["metadata"]["loaded_at"] = time.strftime('%Y-%m-%d %H:%M:%S')
                
                self.feature_cache[cache_key] = config
                self.last_load_time[cache_key] = time.time()
                logger.debug(f"Feature configuration cached for {cache_key}")
            
            return self.feature_cache[cache_key]
            
        except Exception as e:
            logger.exception(f"Error getting merged features for {cache_key}: {e}")
            # Return safe default
            return {
                "features": {},
                "feature_groups": {},
                "error": str(e)
            }
    
    def is_feature_enabled(self, feature_id, project_path=None):
        """Check if a feature is enabled witherror handling"""
        try:
            features = self.get_merged_features(project_path)
            
            # Check for errors in loading
            if 'error' in features:
                logger.warning(f"Error in features config, defaulting feature {feature_id} to disabled")
                return False
            
            feature_config = features.get("features", {}).get(feature_id)
            
            if not feature_config:
                logger.debug(f"Feature {feature_id} not found in configuration")
                return False
            
            enabled = feature_config.get("enabled", False)
            logger.debug(f"Feature {feature_id} enabled status: {enabled}")
            return enabled
            
        except Exception as e:
            logger.exception(f"Error checking feature {feature_id}: {e}")
            return False
    
    def get_enabled_features(self, project_path=None):
        """Get a list of all enabled features with filtering options"""
        try:
            features = self.get_merged_features(project_path)
            
            if 'error' in features:
                logger.warning("Error in features config, returning empty list")
                return []
            
            enabled_features = [
                feature_id for feature_id, config in features.get("features", {}).items()
                if config.get("enabled", False)
            ]
            
            logger.debug(f"Found {len(enabled_features)} enabled features")
            return enabled_features
            
        except Exception as e:
            logger.exception(f"Error getting enabled features: {e}")
            return []
    
    def get_features_by_category(self, category, project_path=None):
        """Get features filtered by category"""
        try:
            features = self.get_merged_features(project_path)
            
            if 'error' in features:
                return []
            
            category_features = [
                feature_id for feature_id, config in features.get("features", {}).items()
                if config.get("category") == category and config.get("enabled", False)
            ]
            
            return category_features
            
        except Exception as e:
            logger.exception(f"Error getting features by category {category}: {e}")
            return []
    
    def set_feature_enabled(self, feature_id, enabled, project_path=None):
        """Enable or disable a feature witherror handling"""
        try:
            if not project_path:
                config_path = self.global_config_path
            else:
                config_path = Path(project_path) / 'config' / 'features.json'
                os.makedirs(config_path.parent, exist_ok=True)
            
            # Load existing config
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
            else:
                config = {"features": {}, "feature_groups": {}}
            
            # Update feature
            if feature_id not in config["features"]:
                config["features"][feature_id] = {}
            
            config["features"][feature_id]["enabled"] = enabled
            config["features"][feature_id]["last_modified"] = time.strftime('%Y-%m-%d %H:%M:%S')
            
            # Save config
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Clear cache
            cache_key = project_path or 'global'
            if cache_key in self.feature_cache:
                del self.feature_cache[cache_key]
                logger.debug(f"Cleared cache for {cache_key}")
            
            # Clear LRU cache if being used
            if hasattr(self.get_merged_features, 'cache_clear'):
                self.get_merged_features.cache_clear()
            
            logger.info(f"Feature {feature_id} set to {enabled} in {config_path}")
            return True
            
        except Exception as e:
            logger.exception(f"Error setting feature {feature_id} to {enabled}: {e}")
            return False
    
    def get_feature_info(self, feature_id, project_path=None):
        """Get detailed information about a specific feature"""
        try:
            features = self.get_merged_features(project_path)
            
            if 'error' in features:
                return None
            
            feature_config = features.get("features", {}).get(feature_id)
            if not feature_config:
                return None
            
            # Find which groups this feature belongs to
            feature_groups = []
            for group_id, group_features in features.get("feature_groups", {}).items():
                if feature_id in group_features:
                    feature_groups.append(group_id)
            
            return {
                "id": feature_id,
                "enabled": feature_config.get("enabled", False),
                "description": feature_config.get("description", ""),
                "category": feature_config.get("category", ""),
                "groups": feature_groups,
                "last_modified": feature_config.get("last_modified", ""),
                "metadata": feature_config.get("metadata", {})
            }
            
        except Exception as e:
            logger.exception(f"Error getting feature info for {feature_id}: {e}")
            return None
    
    def clear_cache(self, project_path=None):
        """Clear feature cache for specific project or all"""
        try:
            if project_path:
                cache_key = project_path
                if cache_key in self.feature_cache:
                    del self.feature_cache[cache_key]
                    del self.last_load_time[cache_key]
                    logger.info(f"Cleared cache for project: {project_path}")
            else:
                self.feature_cache.clear()
                self.last_load_time.clear()
                logger.info("Cleared all feature cache")
                
        except Exception as e:
            logger.exception(f"Error clearing cache: {e}")
    
    def validate_feature_config(self, config):
        """Validate feature configuration structure"""
        errors = []
        warnings = []
        
        try:
            if not isinstance(config, dict):
                errors.append("Config must be a dictionary")
                return {"valid": False, "errors": errors, "warnings": warnings}
            
            # Check required top-level keys
            if "features" not in config:
                errors.append("Missing 'features' section")
            elif not isinstance(config["features"], dict):
                errors.append("'features' must be a dictionary")
            
            if "feature_groups" not in config:
                warnings.append("Missing 'feature_groups' section")
            elif not isinstance(config["feature_groups"], dict):
                errors.append("'feature_groups' must be a dictionary")
            
            # Validate individual features
            if "features" in config and isinstance(config["features"], dict):
                for feature_id, feature_config in config["features"].items():
                    if not isinstance(feature_config, dict):
                        errors.append(f"Feature '{feature_id}' config must be a dictionary")
                        continue
                    
                    if "enabled" not in feature_config:
                        warnings.append(f"Feature '{feature_id}' missing 'enabled' property")
                    elif not isinstance(feature_config["enabled"], bool):
                        errors.append(f"Feature '{feature_id}' 'enabled' must be boolean")
            
            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings
            }
            
        except Exception as e:
            logger.exception(f"Error validating feature config: {e}")
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": warnings
            }