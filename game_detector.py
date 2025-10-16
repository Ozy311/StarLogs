# Author: Ozy
"""
Game installation detector for Star Citizen.
Scans for installed game versions (LIVE, PTU, TECHPREVIEW, EPTU) across all drives.
"""

import os
import json
import string
from pathlib import Path
from typing import List, Dict, Optional


class GameDetector:
    """Detects Star Citizen game installations and available versions."""
    
    DEFAULT_INSTALL_PATH = r"C:\Program Files\Roberts Space Industries\StarCitizen"
    KNOWN_VERSIONS = ["LIVE", "PTU", "TECHPREVIEW", "EPTU"]
    RSI_FOLDER_NAME = "Roberts Space Industries"
    
    def __init__(self, custom_path: Optional[str] = None):
        """Initialize detector with optional custom installation path."""
        self.install_path = Path(custom_path) if custom_path else None
    
    def scan_all_drives(self) -> List[Path]:
        """
        Scan all fixed drives for Roberts Space Industries folder.
        
        Returns:
            List of paths where RSI folder was found
        """
        rsi_locations = []
        
        # Get all available drive letters
        if os.name == 'nt':  # Windows
            drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
        else:  # Linux/Mac (fallback)
            drives = ["/"]
        
        for drive in drives:
            # Check common install locations
            possible_paths = [
                Path(drive) / self.RSI_FOLDER_NAME,
                Path(drive) / "Program Files" / self.RSI_FOLDER_NAME,
                Path(drive) / "Program Files (x86)" / self.RSI_FOLDER_NAME,
            ]
            
            for path in possible_paths:
                if path.exists() and (path / "StarCitizen").exists():
                    rsi_locations.append(path / "StarCitizen")
        
        return rsi_locations
    
    def get_version_metadata(self, version_path: Path) -> Optional[Dict[str, str]]:
        """
        Read version metadata from build_manifest.id file.
        
        Args:
            version_path: Path to version folder (e.g., .../LIVE)
            
        Returns:
            Dict with branch, version, build, etc. or None if file missing
        """
        manifest_file = version_path / "build_manifest.id"
        
        if not manifest_file.exists():
            return None
        
        try:
            with open(manifest_file, 'r') as f:
                data = json.load(f)
                manifest_data = data.get('Data', {})
                return {
                    'branch': manifest_data.get('Branch', 'unknown'),
                    'version': manifest_data.get('Version', 'unknown'),
                    'build': manifest_data.get('RequestedP4ChangeNum', 'unknown'),
                    'build_date': manifest_data.get('BuildDateStamp', 'unknown'),
                    'tag': manifest_data.get('Tag', 'unknown')
                }
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not read build_manifest.id: {e}")
            return None
    
    def find_installations(self) -> List[Dict[str, str]]:
        """
        Find all available Star Citizen installations across all drives.
        
        Returns:
            List of dicts with keys: 'version', 'path', 'log_path', 'branch', 
                                     'version_string', 'build', etc.
        """
        installations = []
        
        # If custom path provided, check only that location
        if self.install_path:
            locations = [self.install_path]
        else:
            # Scan all drives
            locations = self.scan_all_drives()
        
        for base_path in locations:
            if not base_path.exists():
                continue
                
            for version in self.KNOWN_VERSIONS:
                version_path = base_path / version
                log_path = version_path / "Game.log"
                
                if version_path.exists():
                    # Get version metadata
                    metadata = self.get_version_metadata(version_path)
                    
                    installation = {
                        'version': version,
                        'path': str(version_path),
                        'log_path': str(log_path) if log_path.exists() else None,
                        'has_log': log_path.exists()
                    }
                    
                    # Add metadata if available
                    if metadata:
                        installation.update({
                            'branch': metadata['branch'],
                            'version_string': metadata['version'],
                            'build': metadata['build'],
                            'build_date': metadata['build_date'],
                            'tag': metadata['tag'],
                            # Format display string like launcher: "LIVE 4.3.157.21647"
                            'display_name': f"{version} {metadata['version']}"
                        })
                    else:
                        # Fallback to just version name
                        installation['display_name'] = version
                    
                    installations.append(installation)
        
        return installations
    
    def get_log_path(self, version: str) -> Optional[str]:
        """Get the Game.log path for a specific version."""
        installations = self.find_installations()
        for install in installations:
            if install['version'] == version:
                return install.get('log_path')
        return None
    
    def get_logbackups_path(self, version: str) -> Optional[str]:
        """Get the LogBackups folder path for a specific version."""
        installations = self.find_installations()
        for install in installations:
            if install['version'] == version:
                version_path = Path(install['path'])
                logbackups = version_path / "LogBackups"
                return str(logbackups) if logbackups.exists() else None
        return None
    
    def detect_running_game(self) -> Optional[Dict[str, str]]:
        """
        Detect which version is currently running by checking for newest log.
        
        Returns:
            Dict with installation info or None if no active game found.
        """
        installations = self.find_installations()
        if not installations:
            return None
        
        # Find the most recently modified log file
        newest = None
        newest_time = 0
        
        for install in installations:
            if not install.get('has_log'):
                continue
            log_path = Path(install['log_path'])
            if log_path.exists():
                mtime = log_path.stat().st_mtime
                if mtime > newest_time:
                    newest_time = mtime
                    newest = install
        
        return newest
    
    def validate_custom_path(self, custom_path: str) -> Optional[Dict[str, str]]:
        """
        Validate a custom Star Citizen installation path.
        
        Args:
            custom_path: User-provided path to validate
            
        Returns:
            Dict with installation info if valid, None otherwise
        """
        path = Path(custom_path).resolve()
        
        # Check if path exists
        if not path.exists():
            return None
        
        # Try to detect version by checking for known version folders
        # or by checking if current folder contains version files
        version_detected = None
        version_path = None
        
        # Case 1: Path ends with version name (e.g., D:\StarCitizen\LIVE)
        if path.name in self.KNOWN_VERSIONS:
            version_detected = path.name
            version_path = path
        
        # Case 2: Path contains StarCitizen and one of the version folders
        elif (path / "StarCitizen").exists():
            for version in self.KNOWN_VERSIONS:
                test_path = path / "StarCitizen" / version
                if test_path.exists():
                    version_detected = version
                    version_path = test_path
                    break
        
        # Case 3: Check if any version folder exists in this path
        else:
            for version in self.KNOWN_VERSIONS:
                test_path = path / version
                if test_path.exists():
                    version_detected = version
                    version_path = test_path
                    break
        
        # If no version detected, check if path itself looks like SC install
        if not version_detected:
            # Check for typical SC files/folders
            indicators = ['Data.p4k', 'Bin64', 'Data', 'USER']
            found_indicators = sum(1 for ind in indicators if (path / ind).exists())
            
            if found_indicators >= 2:
                # Likely a SC folder but unknown version
                version_detected = "CUSTOM"
                version_path = path
        
        if not version_path:
            return None
        
        # Build installation dict
        log_path = version_path / "Game.log"
        metadata = self.get_version_metadata(version_path)
        
        installation = {
            'version': version_detected,
            'path': str(version_path),
            'log_path': str(log_path) if log_path.exists() else None,
            'has_log': log_path.exists(),
            'auto_detected': False
        }
        
        if metadata:
            installation.update({
                'branch': metadata['branch'],
                'version_string': metadata['version'],
                'build': metadata['build'],
                'build_date': metadata['build_date'],
                'tag': metadata['tag'],
                'display_name': f"{version_detected} {metadata['version']}"
            })
        else:
            installation['display_name'] = version_detected
        
        return installation

