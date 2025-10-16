# Author: Ozy
"""
Configuration manager for StarLogger.
Handles saving and loading user preferences.
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any


class ConfigManager:
    """Manages application configuration and user preferences."""
    
    DEFAULT_CONFIG = {
        'installations': {},
        'active_version': None,
        'web_port': 3111,
        'auto_detect': True,
        'custom_installations': [],
        'debug_mode': False
    }
    
    def __init__(self, config_file: str = "starlogs_config.json"):
        """Initialize config manager with config file path."""
        # Store config in same directory as executable/script
        if getattr(sys, 'frozen', False):
            # Running as compiled exe - save in exe directory
            app_dir = Path(os.path.dirname(sys.executable))
        else:
            # Running as script - use script directory
            app_dir = Path(__file__).parent
        
        self.config_path = app_dir / config_file
        print(f"[Config] Config path: {self.config_path}")
        print(f"[Config] App directory writable: {os.access(app_dir, os.W_OK)}")
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file, create default if missing."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    loaded = json.load(f)
                    # Merge with defaults to handle new keys
                    config = self.DEFAULT_CONFIG.copy()
                    config.update(loaded)
                    return config
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load config: {e}")
                return self.DEFAULT_CONFIG.copy()
        return self.DEFAULT_CONFIG.copy()
    
    def save_config(self) -> bool:
        """Save current configuration to file."""
        try:
            # Clean up legacy fields before saving
            config_to_save = self.config.copy()
            config_to_save.pop('last_version', None)
            config_to_save.pop('log_path', None)
            
            print(f"[Config] Attempting to save config to: {self.config_path}")
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_to_save, f, indent=2)
            print(f"[Config] Config saved successfully")
            return True
        except IOError as e:
            print(f"[Config] ERROR saving config: {e}")
            print(f"[Config]   Path: {self.config_path}")
            print(f"[Config]   Exists: {self.config_path.exists()}")
            print(f"[Config]   Parent writable: {os.access(self.config_path.parent, os.W_OK)}")
            return False
        except Exception as e:
            print(f"[Config] ERROR: Unexpected error saving config: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value and save."""
        self.config[key] = value
        self.save_config()
    
    def update(self, updates: Dict[str, Any]) -> None:
        """Update multiple configuration values and save."""
        self.config.update(updates)
        self.save_config()
    
    def store_installations(self, installations: list) -> None:
        """
        Store detected installations in config.
        
        Args:
            installations: List of installation dicts from GameDetector
        """
        installations_dict = {}
        for install in installations:
            version = install['version']
            installations_dict[version] = {
                'path': install['path'],
                'branch': install.get('branch', 'unknown'),
                'version': install.get('version_string', 'unknown'),
                'build': install.get('build', 'unknown'),
                'auto_detected': True
            }
        
        self.config['installations'] = installations_dict
        self.save_config()
    
    def get_active_installation(self) -> Optional[Dict[str, Any]]:
        """Get the currently active installation info."""
        active_version = self.config.get('active_version')
        if active_version and active_version in self.config.get('installations', {}):
            return self.config['installations'][active_version]
        return None
    
    def set_active_version(self, version: str) -> bool:
        """
        Set the active version.
        
        Args:
            version: Version name (e.g., "LIVE", "PTU")
            
        Returns:
            True if successful, False if version not found
        """
        if version in self.config.get('installations', {}):
            self.config['active_version'] = version
            # Clean up legacy fields
            self.config.pop('last_version', None)
            self.config.pop('log_path', None)
            self.save_config()
            return True
        return False
    
    def get_log_path(self, version: str = None) -> Optional[str]:
        """
        Get the Game.log path for a specific version or the active version.
        
        Args:
            version: Version name (e.g., "LIVE", "PTU"). If None, uses active_version.
            
        Returns:
            Full path to Game.log, or None if not found
        """
        if version is None:
            version = self.config.get('active_version')
        
        if version and version in self.config.get('installations', {}):
            install_path = self.config['installations'][version]['path']
            return str(Path(install_path) / 'Game.log')
        return None
    
    def add_custom_installation(self, version: str, path: str, metadata: Dict[str, Any]) -> bool:
        """
        Add a custom installation to the config.
        
        Args:
            version: Version name (e.g., "LIVE", "PTU", "EPTU")
            path: Installation path
            metadata: Version metadata dict
            
        Returns:
            True if added successfully
        """
        if 'installations' not in self.config:
            self.config['installations'] = {}
        
        self.config['installations'][version] = {
            'path': path,
            'branch': metadata.get('branch', 'unknown'),
            'version': metadata.get('version', 'unknown'),
            'build': metadata.get('build', 'unknown'),
            'auto_detected': False  # Mark as custom
        }
        
        return self.save_config()
    
    def remove_custom_installation(self, version: str) -> bool:
        """
        Remove a custom installation from the config.
        Only removes if it's marked as custom (auto_detected=False).
        
        Args:
            version: Version name to remove
            
        Returns:
            True if removed, False if not found or is auto-detected
        """
        installations = self.config.get('installations', {})
        
        if version not in installations:
            return False
        
        # Don't allow removing auto-detected installations
        if installations[version].get('auto_detected', True):
            return False
        
        # Remove the installation
        del installations[version]
        
        # If this was the active version, clear active_version
        if self.config.get('active_version') == version:
            self.config['active_version'] = None
        
        return self.save_config()


# Import sys for executable path detection
import sys

