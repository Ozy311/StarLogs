# Author: Ozy
"""
Offline log analyzer for Star Citizen logs.
Processes log files without live monitoring and generates static reports.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from event_parser import EventParser, LogEvent


class OfflineAnalyzer:
    """Analyzes Star Citizen log files offline."""
    
    def __init__(self, log_file_path: str):
        """
        Initialize offline analyzer.
        
        Args:
            log_file_path: Path to the Game.log file to analyze
        """
        self.log_file_path = Path(log_file_path)
        if not self.log_file_path.exists():
            raise FileNotFoundError(f"Log file not found: {log_file_path}")
        
        self.event_parser = EventParser()
        self.events = []
        self.system_info = {}
        self.stats = {
            'total_lines': 0,
            'pve_kills': 0,
            'pvp_kills': 0,
            'deaths': 0,
            'disconnects': 0,
            'actor_stalls': 0
        }
    
    def parse_all_events(self) -> List[Dict[str, Any]]:
        """
        Parse entire log file and extract all events.
        
        Returns:
            List of event dictionaries
        """
        print(f"[INFO] Analyzing log file: {self.log_file_path}")
        self.events = []
        header_lines = []
        
        try:
            with open(self.log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for idx, line in enumerate(f):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Collect first 200 lines for system info
                    if idx < 200:
                        header_lines.append(line)
                    
                    # Parse for events
                    event = self.event_parser.parse_line(line)
                    if event:
                        self.events.append(event.to_dict())
                        
                        # Update stats
                        if event.type.value == 'pve_kill':
                            self.stats['pve_kills'] += 1
                        elif event.type.value == 'pvp_kill':
                            self.stats['pvp_kills'] += 1
                        elif event.type.value == 'death':
                            self.stats['deaths'] += 1
                        elif event.type.value == 'disconnect':
                            self.stats['disconnects'] += 1
                        elif event.type.value == 'actor_stall':
                            self.stats['actor_stalls'] += 1
                    
                    self.stats['total_lines'] += 1
        
        except Exception as e:
            print(f"[ERROR] Failed to parse log file: {e}")
            raise
        
        # Extract system info from header
        self.system_info = self.event_parser.extract_system_info(header_lines)
        
        print(f"[INFO] Processed {self.stats['total_lines']} lines")
        print(f"[INFO] Found {len(self.events)} events:")
        print(f"  - {self.stats['pve_kills']} PvE Kills")
        print(f"  - {self.stats['pvp_kills']} PvP Kills")
        print(f"  - {self.stats['deaths']} Deaths")
        print(f"  - {self.stats['actor_stalls']} Actor Stalls")
        print(f"  - {self.stats['disconnects']} Disconnects")
        
        return self.events
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get analysis statistics."""
        return self.stats.copy()
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get extracted system information."""
        return self.system_info.copy()
    
    def get_log_filename(self) -> str:
        """Get the log file name."""
        return self.log_file_path.name
    
    def get_log_size(self) -> int:
        """Get the log file size in bytes."""
        return self.log_file_path.stat().st_size


def parse_logbackup_filename(filename: str) -> Optional[Dict[str, Any]]:
    """
    Parse LogBackup filename to extract metadata.
    
    Format: Game Build(10188864) 12 Sep 25 (21 13 25).log
    
    Args:
        filename: LogBackup filename
        
    Returns:
        Dict with build, date, time or None if parsing fails
    """
    # Pattern: Game Build(changelist) DD Mon YY (HH MM SS).log
    pattern = r'Game Build\((\d+)\)\s+(\d{2})\s+(\w+)\s+(\d{2})\s+\((\d{2})\s+(\d{2})\s+(\d{2})\)\.log'
    match = re.search(pattern, filename)
    
    if match:
        changelist = match.group(1)
        day = match.group(2)
        month = match.group(3)
        year = f"20{match.group(4)}"  # Convert YY to YYYY
        hour = match.group(5)
        minute = match.group(6)
        second = match.group(7)
        
        # Create datetime object
        try:
            month_map = {
                'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
            }
            month_num = month_map.get(month, 1)
            dt = datetime(int(year), month_num, int(day), int(hour), int(minute), int(second))
            
            return {
                'build': changelist,
                'date': dt.strftime('%Y-%m-%d'),
                'time': dt.strftime('%H:%M:%S'),
                'datetime': dt.isoformat(),
                'display_date': dt.strftime('%b %d, %Y %I:%M %p')
            }
        except ValueError:
            pass
    
    return None


def list_logbackups(logbackups_path: str) -> List[Dict[str, Any]]:
    """
    List all LogBackup files in a directory.
    
    Args:
        logbackups_path: Path to LogBackups folder
        
    Returns:
        List of dicts with file information
    """
    logbackups_dir = Path(logbackups_path)
    if not logbackups_dir.exists():
        return []
    
    files = []
    for filepath in logbackups_dir.glob("*.log"):
        metadata = parse_logbackup_filename(filepath.name)
        
        file_info = {
            'filename': filepath.name,
            'path': str(filepath),
            'size_bytes': filepath.stat().st_size,
            'size_mb': round(filepath.stat().st_size / (1024 * 1024), 2)
        }
        
        if metadata:
            file_info.update(metadata)
        
        files.append(file_info)
    
    # Sort by date (newest first)
    files.sort(key=lambda x: x.get('datetime', ''), reverse=True)
    
    return files

