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
            'fps_pve_kills': 0,
            'fps_pvp_kills': 0,
            'fps_deaths': 0,
            'disconnects': 0,
            'actor_stalls': 0,
            'suicides': 0,
            'corpses': 0,
            'vehicle_destroy_soft': 0,
            'vehicle_destroy_full': 0,
            'vehicle_destroy_combat': 0,
            'vehicle_destroy_collision': 0,
            'vehicle_destroy_selfdestruct': 0,
            'vehicle_destroy_gamerules': 0
        }
        
        # Vehicle destruction tracking (for crew kill correlation)
        self.recent_vehicle_destructions = {}
    
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
                        # Handle vehicle destruction events
                        if event.type.value in ['vehicle_destroy_soft', 'vehicle_destroy_full']:
                            vehicle_id = event.details.get('vehicle_id')
                            if vehicle_id:
                                # Store in recent destructions for crew kill correlation
                                self.recent_vehicle_destructions[vehicle_id] = {
                                    'timestamp': event.timestamp,
                                    'event': event
                                }
                                
                                # Clean up old entries (>10 seconds)
                                from datetime import timedelta
                                cutoff_time = event.timestamp - timedelta(seconds=10) if event.timestamp else None
                                if cutoff_time:
                                    to_remove = [vid for vid, data in self.recent_vehicle_destructions.items() 
                                                if data['timestamp'] and data['timestamp'] < cutoff_time]
                                    for vid in to_remove:
                                        del self.recent_vehicle_destructions[vid]
                        
                        # Handle crew kills with VehicleDestruction damage type - correlate with vehicle destruction
                        if event.type.value in ['pve_kill', 'pvp_kill'] and event.details.get('damage_type') == 'VehicleDestruction':
                            # Extract vehicle_id from zone (victim was in the destroyed vehicle)
                            zone = event.details.get('zone', '')
                            vehicle_id_match = re.search(r'_(\d{13})$', zone)
                            if vehicle_id_match:
                                vehicle_id = vehicle_id_match.group(1)
                                
                                # Look up recent vehicle destruction
                                if vehicle_id in self.recent_vehicle_destructions:
                                    destruction_data = self.recent_vehicle_destructions[vehicle_id]
                                    destruction_event = destruction_data['event']
                                    
                                    # Check timestamp proximity (within 200ms)
                                    from datetime import timedelta
                                    time_diff = abs((event.timestamp - destruction_event.timestamp).total_seconds()) if event.timestamp and destruction_event.timestamp else 999
                                    
                                    if time_diff <= 0.2:  # 200ms window
                                        # Update crew count and names in the vehicle destruction event
                                        victim_name = event.details.get('victim', 'Unknown')
                                        destruction_event.details['crew_count'] += 1
                                        destruction_event.details['crew_names'].append(victim_name)
                        
                        self.events.append(event.to_dict())
                        
                        # Update stats
                        if event.type.value == 'pve_kill':
                            self.stats['pve_kills'] += 1
                        elif event.type.value == 'pvp_kill':
                            self.stats['pvp_kills'] += 1
                        elif event.type.value == 'death':
                            self.stats['deaths'] += 1
                        elif event.type.value == 'fps_pve_kill':
                            self.stats['fps_pve_kills'] += 1
                        elif event.type.value == 'fps_pvp_kill':
                            self.stats['fps_pvp_kills'] += 1
                        elif event.type.value == 'fps_death':
                            self.stats['fps_deaths'] += 1
                        elif event.type.value == 'disconnect':
                            self.stats['disconnects'] += 1
                        elif event.type.value == 'actor_stall':
                            self.stats['actor_stalls'] += 1
                        elif event.type.value == 'suicide':
                            self.stats['suicides'] += 1
                        elif event.type.value == 'corpse':
                            self.stats['corpses'] += 1
                        elif event.type.value == 'vehicle_destroy_soft':
                            self.stats['vehicle_destroy_soft'] += 1
                            damage_type = event.details.get('damage_type', '').lower()
                            if damage_type == 'combat':
                                self.stats['vehicle_destroy_combat'] += 1
                            elif damage_type == 'collision':
                                self.stats['vehicle_destroy_collision'] += 1
                            elif damage_type == 'selfdestruct':
                                self.stats['vehicle_destroy_selfdestruct'] += 1
                            elif damage_type == 'gamerules':
                                self.stats['vehicle_destroy_gamerules'] += 1
                        elif event.type.value == 'vehicle_destroy_full':
                            self.stats['vehicle_destroy_full'] += 1
                            damage_type = event.details.get('damage_type', '').lower()
                            if damage_type == 'combat':
                                self.stats['vehicle_destroy_combat'] += 1
                            elif damage_type == 'collision':
                                self.stats['vehicle_destroy_collision'] += 1
                            elif damage_type == 'selfdestruct':
                                self.stats['vehicle_destroy_selfdestruct'] += 1
                            elif damage_type == 'gamerules':
                                self.stats['vehicle_destroy_gamerules'] += 1
                    
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
        print(f"  - {self.stats['fps_pve_kills']} FPS PvE Kills")
        print(f"  - {self.stats['fps_pvp_kills']} FPS PvP Kills")
        print(f"  - {self.stats['fps_deaths']} FPS Deaths")
        print(f"  - {self.stats['vehicle_destroy_soft']} Soft Deaths (0→1)")
        print(f"  - {self.stats['vehicle_destroy_full']} Full Destructions (→2)")
        print(f"  - {self.stats['actor_stalls']} Actor Stalls")
        print(f"  - {self.stats['suicides']} Suicides")
        print(f"  - {self.stats['corpses']} Corpses")
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

