# Author: Ozy
"""
Monitor StarCitizen.exe process status.
"""

import psutil
from typing import Optional, Dict


class ProcessMonitor:
    """Monitor StarCitizen.exe process."""
    
    def __init__(self):
        self.process_name = "StarCitizen.exe"
    
    def get_game_status(self) -> Dict[str, any]:
        """
        Check if StarCitizen.exe is running.
        
        Returns:
            Dict with keys: 'running' (bool), 'pid' (int or None), 'memory_mb' (float or None)
        """
        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                if proc.info['name'] == self.process_name:
                    memory_mb = proc.info['memory_info'].rss / (1024 * 1024)  # Convert to MB
                    return {
                        'running': True,
                        'pid': proc.info['pid'],
                        'memory_mb': round(memory_mb, 1)
                    }
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        
        return {
            'running': False,
            'pid': None,
            'memory_mb': None
        }

