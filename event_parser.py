# Author: Ozy
"""
Event parser for Star Citizen game logs.
Extracts and structures events like disconnects, kills, etc.
"""

import re
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum


class EventType(Enum):
    """Types of events we can parse from logs."""
    DISCONNECT = "disconnect"
    KILL = "kill"  # Player killed someone (PvP or PvE)
    DEATH = "death"  # Player was killed
    PVE_KILL = "pve_kill"  # Player killed NPC (vehicle)
    PVP_KILL = "pvp_kill"  # Player killed player (vehicle)
    FPS_PVE_KILL = "fps_pve_kill"  # Player killed NPC (on foot)
    FPS_PVP_KILL = "fps_pvp_kill"  # Player killed player (on foot)
    FPS_DEATH = "fps_death"  # Player was killed (on foot)
    ACTOR_STALL = "actor_stall"  # Game disconnect/crash/stall
    UNKNOWN = "unknown"


class LogEvent:
    """Represents a parsed log event."""
    
    def __init__(self, event_type: EventType, timestamp: Optional[datetime], 
                 raw_line: str, details: Optional[Dict[str, Any]] = None):
        self.type = event_type
        self.timestamp = timestamp
        self.raw_line = raw_line
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for JSON serialization."""
        return {
            'type': self.type.value,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'raw_line': self.raw_line,
            'details': self.details
        }


class EventParser:
    """Parses Star Citizen log events."""
    
    # Timestamp pattern: <2025-10-15T07:31:19.238Z>
    TIMESTAMP_PATTERN = re.compile(r'<(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)>')
    
    # Disconnect patterns
    DISCONNECT_PATTERN = re.compile(r'^\s*[Dd]isconnect\s*$', re.IGNORECASE)
    DISCONNECT_WITH_TIMESTAMP = re.compile(r'<.*?>\s*[Dd]isconnect\s*$', re.IGNORECASE)
    
    # Actor Stall pattern (primary disconnect/crash indicator)
    # Matches: <Actor stall> Actor stall detected, Player: Name, Type: downstream, Length: 3.746040
    ACTOR_STALL_PATTERN = re.compile(
        r'<Actor stall>.*?Actor stall detected,\s*Player:\s*(\w+),\s*Type:\s*(\w+),\s*Length:\s*(\d+(?:\.\d+)?)',
        re.IGNORECASE
    )
    
    # Kill pattern: <Actor Death> CActor::Kill: 'victim' [id] killed by 'killer' [id]
    # Captures: victim, victim_id, zone, killer, killer_id, weapon, weapon_class, damage_type, direction_x, direction_y, direction_z
    KILL_PATTERN = re.compile(
        r"<Actor Death> CActor::Kill: '([^']+)' \[(\d+)\] in zone '([^']+)' killed by '([^']+)' \[(\d+)\] using '([^']+)' \[Class ([^\]]+)\] with damage type '([^']+)' from direction x: ([-\d.]+), y: ([-\d.]+), z: ([-\d.]+)",
        re.IGNORECASE
    )
    
    # NPC name indicators
    NPC_INDICATORS = [
        'PU_Pilots',
        'PU_',
        'AI_CRIM',
        'AI_',
        '_NPC_',
        'Criminal-Pilot',
        'Security-',
        'Pirate-',
        '-Pilot_Light_',
        '-Pilot_Medium_',
        '-Pilot_Heavy_'
    ]
    
    def __init__(self):
        """Initialize the event parser."""
        pass
    
    def extract_timestamp(self, line: str) -> Optional[datetime]:
        """Extract timestamp from log line."""
        match = self.TIMESTAMP_PATTERN.search(line)
        if match:
            try:
                return datetime.fromisoformat(match.group(1).replace('Z', '+00:00'))
            except ValueError:
                return None
        return None
    
    def parse_line(self, line: str) -> Optional[LogEvent]:
        """
        Parse a single log line and return an event if recognized.
        
        Args:
            line: Raw log line
            
        Returns:
            LogEvent if line contains a recognized event, None otherwise
        """
        timestamp = self.extract_timestamp(line)
        
        # Check for Actor Stall (primary disconnect indicator)
        actor_stall_match = self.ACTOR_STALL_PATTERN.search(line)
        if actor_stall_match:
            player = actor_stall_match.group(1)
            stall_type = actor_stall_match.group(2)
            stall_length = actor_stall_match.group(3)
            return LogEvent(
                event_type=EventType.ACTOR_STALL,
                timestamp=timestamp,
                raw_line=line.strip(),
                details={
                    'type': 'actor_stall',
                    'player': player,
                    'stall_type': stall_type,
                    'length': stall_length
                }
            )
        
        # Check for kill events (more specific, check first)
        kill_match = self.KILL_PATTERN.search(line)
        if kill_match:
            return self._parse_kill_event(line, timestamp, kill_match)
        
        # Check for disconnect events (legacy pattern)
        if self.DISCONNECT_PATTERN.search(line) or self.DISCONNECT_WITH_TIMESTAMP.search(line):
            return LogEvent(
                event_type=EventType.DISCONNECT,
                timestamp=timestamp,
                raw_line=line.strip()
            )
        
        return None
    
    def _is_npc(self, entity_name: str) -> bool:
        """Check if entity name belongs to an NPC."""
        return any(indicator in entity_name for indicator in self.NPC_INDICATORS)
    
    def _extract_ship_from_zone(self, zone: str) -> Optional[str]:
        """
        Extract ship/location name from zone string.
        
        Examples:
            'ORIG_890Jump_6166775878721' -> '890 Jump'
            'AEGS_Gladius_1234567' -> 'Gladius'
            'Crusader_4567890' -> 'Crusader'
        
        Args:
            zone: Zone string from kill event
            
        Returns:
            Extracted ship/location name or None
        """
        if not zone:
            return None
        
        # Common ship/location patterns
        ship_patterns = [
            # Manufacturer_ShipName_ID format
            r'(?:ORIG|AEGS|ANVL|CRUS|MISC|RSI|DRAK|ARGO|ESPR)_([A-Za-z0-9]+)_\d+',
            # ShipName_ID format
            r'([A-Za-z][A-Za-z0-9]+)_\d{10,}',
            # Location names
            r'(Crusader|Hurston|microTech|ArcCorp|Pyro)',
        ]
        
        for pattern in ship_patterns:
            match = re.search(pattern, zone, re.IGNORECASE)
            if match:
                ship_name = match.group(1)
                # Format the name (add spaces before capitals, handle numbers)
                formatted = re.sub(r'(\d+)([A-Z])', r'\1 \2', ship_name)  # Add space between number and capital
                formatted = re.sub(r'([a-z])([A-Z])', r'\1 \2', formatted)  # Add space between lowercase and capital
                return formatted
        
        # If no pattern matches, try to extract something readable
        parts = zone.split('_')
        if len(parts) >= 2:
            # Return the second part if it looks like a name (not just numbers)
            potential = parts[1] if len(parts) > 1 else parts[0]
            if potential and not potential.isdigit():
                return potential
        
        return None
    
    def _parse_kill_event(self, line: str, timestamp: Optional[datetime], 
                          match: re.Match) -> LogEvent:
        """
        Parse kill event details from regex match.
        
        Args:
            line: Raw log line
            timestamp: Extracted timestamp
            match: Regex match object
            
        Returns:
            LogEvent with kill details
        """
        victim_name = match.group(1)
        victim_id = match.group(2)
        zone = match.group(3)
        killer_name = match.group(4)
        killer_id = match.group(5)
        weapon = match.group(6)
        weapon_class = match.group(7)
        damage_type = match.group(8)
        direction_x = match.group(9)
        direction_y = match.group(10)
        direction_z = match.group(11)
        
        # Extract ship/location info from zone
        # Zones often contain ship names like "ORIG_890Jump_6166775878721"
        ship_info = self._extract_ship_from_zone(zone)
        
        # Determine kill type
        is_npc_victim = self._is_npc(victim_name)
        is_npc_killer = self._is_npc(killer_name)
        is_fps_kill = damage_type.lower() == 'bullet'  # FPS combat uses 'Bullet' damage type
        
        # Classify the event (FPS vs Vehicle combat)
        if is_fps_kill:
            # FPS combat (on foot)
            if is_npc_killer and not is_npc_victim:
                event_type = EventType.FPS_DEATH  # Player killed by NPC on foot
            elif not is_npc_killer and is_npc_victim:
                event_type = EventType.FPS_PVE_KILL  # Player killed NPC on foot
            elif not is_npc_killer and not is_npc_victim:
                event_type = EventType.FPS_PVP_KILL  # Player killed player on foot
            else:
                event_type = EventType.KILL  # NPC killed NPC (generic)
        else:
            # Vehicle combat
            if is_npc_killer and not is_npc_victim:
                event_type = EventType.DEATH  # Player killed by NPC (vehicle)
            elif not is_npc_killer and is_npc_victim:
                event_type = EventType.PVE_KILL  # Player killed NPC (vehicle)
            elif not is_npc_killer and not is_npc_victim:
                event_type = EventType.PVP_KILL  # Player killed player (vehicle)
            else:
                event_type = EventType.KILL  # NPC killed NPC (generic)
        
        details = {
            'victim': victim_name,
            'victim_id': victim_id,
            'killer': killer_name,
            'killer_id': killer_id,
            'weapon': weapon,
            'weapon_class': weapon_class,
            'damage_type': damage_type,
            'zone': zone,
            'ship': ship_info,
            'direction': {
                'x': float(direction_x),
                'y': float(direction_y),
                'z': float(direction_z)
            },
            'is_pvp': not is_npc_victim and not is_npc_killer,
            'is_pve': not is_npc_killer and is_npc_victim,
            'is_death': is_npc_killer and not is_npc_victim,
            'is_fps': is_fps_kill
        }
        
        return LogEvent(
            event_type=event_type,
            timestamp=timestamp,
            raw_line=line.strip(),
            details=details
        )
    
    def extract_system_info(self, log_lines: List[str]) -> Dict[str, Any]:
        """
        Extract system information from log file header (first ~200 lines).
        
        Args:
            log_lines: List of log lines (typically first 200 lines)
            
        Returns:
            Dict with system information (CPU, GPU, RAM, OS, etc.)
        """
        system_info = {
            'cpu': None,
            'cpu_cores': None,
            'os': None,
            'ram_total': None,
            'ram_available': None,
            'gpu': None,
            'gpu_vram': None,
            'display_mode': None,
            'performance_cpu': None,
            'performance_gpu': None,
            'file_version': None,
            'changelist': None,
            'branch': None,
            'build_date': None,
            'hostname': None
        }
        
        # Patterns for extracting system info
        patterns = {
            'cpu': re.compile(r'Host CPU:\s*(.+)'),
            'cpu_cores': re.compile(r'Logical CPU Count:\s*(\d+)'),
            'os': re.compile(r'(Windows \d+.*?)\s+\(build'),
            'ram_total': re.compile(r'(\d+)MB physical memory installed'),
            'ram_available': re.compile(r'(\d+)MB available'),
            'gpu': re.compile(r'D3D Adapter: Description:\s*(.+)'),
            'gpu_vram': re.compile(r'DedicatedVidMem\s*=\s*(\d+)'),
            'display_mode': re.compile(r'Current display mode is\s*(.+)'),
            'performance_cpu': re.compile(r'Performance Index:\s*([\d.]+)\s*\(CPU\)'),
            'performance_gpu': re.compile(r'Performance Index:.*?\(GPU\),\s*([\d.]+)\s*\(GPU\)'),
            'file_version': re.compile(r'FileVersion:\s*([\d.]+)'),
            'changelist': re.compile(r'Changelist:\s*(\d+)'),
            'branch': re.compile(r'Branch:\s*(.+)'),
            'build_date': re.compile(r'Built on\s*(.+)'),
            'hostname': re.compile(r'network hostname:\s*(.+)')
        }
        
        # Search through log lines
        for line in log_lines:
            for key, pattern in patterns.items():
                if system_info[key] is None:  # Only capture first match
                    match = pattern.search(line)
                    if match:
                        system_info[key] = match.group(1).strip()
        
        # Convert numeric fields
        try:
            if system_info['cpu_cores']:
                system_info['cpu_cores'] = int(system_info['cpu_cores'])
            if system_info['ram_total']:
                system_info['ram_total'] = int(system_info['ram_total'])
            if system_info['ram_available']:
                system_info['ram_available'] = int(system_info['ram_available'])
            if system_info['gpu_vram']:
                system_info['gpu_vram'] = int(system_info['gpu_vram'])
            if system_info['performance_cpu']:
                system_info['performance_cpu'] = float(system_info['performance_cpu'])
            if system_info['performance_gpu']:
                system_info['performance_gpu'] = float(system_info['performance_gpu'])
        except (ValueError, TypeError):
            pass
        
        return system_info

