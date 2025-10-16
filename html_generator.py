# Author: Ozy
"""
Static HTML report generator for Star Citizen log analysis.
Creates self-contained HTML files with embedded CSS/JS.
"""

import json
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path


class StaticHTMLGenerator:
    """Generates static HTML reports from log analysis."""
    
    def __init__(self, events: List[Dict[str, Any]], system_info: Dict[str, Any], 
                 stats: Dict[str, Any], filename: str):
        """
        Initialize HTML generator.
        
        Args:
            events: List of parsed events
            system_info: System information dictionary
            stats: Statistics dictionary
            filename: Original log filename
        """
        self.events = events
        self.system_info = system_info
        self.stats = stats
        self.filename = filename
        self.generated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def generate_html(self, format_type: str = 'full') -> str:
        """
        Generate static HTML report.
        
        Args:
            format_type: 'full' for complete UI, 'simple' for basic report
            
        Returns:
            Complete HTML string
        """
        if format_type == 'simple':
            return self._generate_simple_html()
        else:
            return self._generate_full_html()
    
    def _generate_simple_html(self) -> str:
        """Generate simple text-based HTML report."""
        
        # Calculate uptime
        uptime_str = ''
        if self.events and len(self.events) >= 2:
            first_time = datetime.fromisoformat(self.events[0]['timestamp'].replace('Z', '+00:00'))
            last_time = datetime.fromisoformat(self.events[-1]['timestamp'].replace('Z', '+00:00'))
            uptime_ms = (last_time - first_time).total_seconds() * 1000
            uptime_hours = int(uptime_ms / (1000 * 60 * 60))
            uptime_minutes = int((uptime_ms % (1000 * 60 * 60)) / (1000 * 60))
            uptime_str = f'{uptime_hours}h {uptime_minutes}m'
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StarLogs Report - {self.filename}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #021C31;
            color: #e0e0e0;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .header {{
            background: #173A51;
            color: #e0e0e0;
            padding: 30px;
            border-radius: 8px;
            border: 2px solid #54ADF7;
            margin-bottom: 20px;
        }}
        .header h1 {{
            color: #54ADF7;
            margin-bottom: 10px;
            font-size: 2rem;
        }}
        .header .tagline {{
            color: #F5AC1A;
            font-weight: bold;
            font-size: 1.2rem;
        }}
        .header-info {{
            margin-top: 15px;
            color: #a0a0a0;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: #173A51;
            padding: 20px;
            border-radius: 8px;
            border: 2px solid #54ADF7;
            text-align: center;
        }}
        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 8px;
        }}
        .stat-value.pve {{ color: #00ff88; }}
        .stat-value.pvp {{ color: #ff4444; }}
        .stat-value.death {{ color: #ff8800; }}
        .stat-value.stall {{ color: #ff4444; }}
        .stat-value.disconnect {{ color: #F5AC1A; }}
        .stat-value.default {{ color: #54ADF7; }}
        .stat-label {{
            color: #a0a0a0;
            text-transform: uppercase;
            font-size: 0.85rem;
            letter-spacing: 1px;
        }}
        .system-info {{
            background: #173A51;
            padding: 20px;
            border-radius: 8px;
            border: 2px solid #54ADF7;
            margin: 20px 0;
        }}
        .system-info h2 {{
            color: #54ADF7;
            margin-bottom: 15px;
            font-size: 1.5rem;
        }}
        .system-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 10px;
        }}
        .system-item {{
            color: #a0a0a0;
            padding: 8px 0;
            font-size: 0.95rem;
        }}
        .system-item strong {{
            color: #54ADF7;
            margin-right: 8px;
        }}
        .event-list {{
            background: #173A51;
            padding: 20px;
            border-radius: 8px;
            border: 2px solid #54ADF7;
            margin: 20px 0;
        }}
        .event-list h2 {{
            color: #54ADF7;
            margin-bottom: 15px;
            font-size: 1.5rem;
        }}
        .event-item {{
            padding: 12px;
            margin-bottom: 8px;
            background: #0a2940;
            border-radius: 4px;
            border-left: 4px solid #54ADF7;
            display: flex;
            gap: 15px;
            align-items: baseline;
        }}
        .event-item.pve-kill {{ border-left-color: #00ff88; }}
        .event-item.pvp-kill {{ border-left-color: #ff4444; }}
        .event-item.death {{ border-left-color: #ff8800; }}
        .event-item.actor-stall {{ border-left-color: #ff4444; }}
        .event-item.disconnect {{ border-left-color: #F5AC1A; }}
        .event-type {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
            text-transform: uppercase;
        }}
        .event-type.pve-kill {{ background: #00ff88; color: #021C31; }}
        .event-type.pvp-kill {{ background: #ff4444; color: white; }}
        .event-type.death {{ background: #ff8800; color: white; }}
        .event-type.actor-stall {{ background: #ff4444; color: white; }}
        .event-type.disconnect {{ background: #F5AC1A; color: #021C31; }}
        .event-timestamp {{
            color: #a0a0a0;
            font-size: 0.85rem;
            min-width: 120px;
        }}
        .event-details {{
            color: #e0e0e0;
            flex: 1;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding: 20px;
            color: #a0a0a0;
            font-size: 0.9rem;
        }}
        .footer .cube {{
            color: #F5AC1A;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 StarLogs Static Report</h1>
            <p class="tagline">FOR THE CUBE!</p>
            <div class="header-info">
                <p><strong>Log File:</strong> {self.filename}</p>
                <p><strong>Generated:</strong> {self.generated_at}</p>
                {f'<p><strong>Session Time:</strong> {uptime_str}</p>' if uptime_str else ''}
            </div>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value pve">{self.stats.get('pve_kills', 0)}</div>
                <div class="stat-label">PvE Kills</div>
            </div>
            <div class="stat-card">
                <div class="stat-value pvp">{self.stats.get('pvp_kills', 0)}</div>
                <div class="stat-label">PvP Kills</div>
            </div>
            <div class="stat-card">
                <div class="stat-value death">{self.stats.get('deaths', 0)}</div>
                <div class="stat-label">Deaths</div>
            </div>
            <div class="stat-card">
                <div class="stat-value stall">{self.stats.get('actor_stalls', 0)}</div>
                <div class="stat-label">Actor Stalls</div>
            </div>
            <div class="stat-card">
                <div class="stat-value disconnect">{self.stats.get('disconnects', 0)}</div>
                <div class="stat-label">Disconnects</div>
            </div>
            <div class="stat-card">
                <div class="stat-value default">{self.stats.get('total_lines', 0)}</div>
                <div class="stat-label">Total Lines</div>
            </div>
        </div>
        
        {self._generate_system_info_html()}
        
        <div class="event-list">
            <h2>📜 Event Timeline ({len(self.events)} events)</h2>
            {self._generate_event_list_html()}
        </div>
        
        <div class="footer">
            <p>Generated by <span class="cube">StarLogs</span> | FOR THE CUBE! 🟨</p>
        </div>
    </div>
</body>
</html>"""
        return html
    
    def _generate_system_info_html(self) -> str:
        """Generate HTML for system information section."""
        if not self.system_info:
            return ''
        
        # Only show if we have useful system data
        if not any([self.system_info.get('cpu'), self.system_info.get('gpu'), self.system_info.get('os')]):
            return ''
        
        html = '<div class="system-info"><h2>💻 System Information</h2><div class="system-grid">'
        
        if self.system_info.get('os'):
            html += f'<div class="system-item"><strong>OS:</strong> {self.system_info["os"]}</div>'
        if self.system_info.get('cpu'):
            cores = f' ({self.system_info["cpu_cores"]} cores)' if self.system_info.get('cpu_cores') else ''
            html += f'<div class="system-item"><strong>CPU:</strong> {self.system_info["cpu"]}{cores}</div>'
        if self.system_info.get('ram_total'):
            ram_gb = round(self.system_info["ram_total"] / 1024)
            html += f'<div class="system-item"><strong>RAM:</strong> {ram_gb}GB</div>'
        if self.system_info.get('gpu'):
            html += f'<div class="system-item"><strong>GPU:</strong> {self.system_info["gpu"]}</div>'
        if self.system_info.get('gpu_vram'):
            vram_gb = round(self.system_info["gpu_vram"] / 1024)
            html += f'<div class="system-item"><strong>VRAM:</strong> {vram_gb}GB</div>'
        if self.system_info.get('display_mode'):
            html += f'<div class="system-item"><strong>Display:</strong> {self.system_info["display_mode"]}</div>'
        if self.system_info.get('performance_cpu') and self.system_info.get('performance_gpu'):
            html += f'<div class="system-item"><strong>Performance Index:</strong> {self.system_info["performance_cpu"]} (CPU), {self.system_info["performance_gpu"]} (GPU)</div>'
        if self.system_info.get('branch'):
            html += f'<div class="system-item"><strong>Branch:</strong> {self.system_info["branch"]}</div>'
        if self.system_info.get('changelist'):
            html += f'<div class="system-item"><strong>Build:</strong> {self.system_info["changelist"]}</div>'
        
        html += '</div></div>'
        return html
    
    def _format_direction(self, direction: dict) -> str:
        """Format direction vector into human-readable text."""
        if not direction:
            return ""
        
        x = direction.get('x', 0)
        y = direction.get('y', 0)
        z = direction.get('z', 0)
        
        distance = (x * x + y * y + z * z) ** 0.5
        if distance < 0.01:
            return ""
        
        # Calculate primary direction
        abs_x = abs(x)
        abs_y = abs(y)
        abs_z = abs(z)
        
        if abs_x > abs_y and abs_x > abs_z:
            return "from Right" if x > 0 else "from Left"
        elif abs_y > abs_x and abs_y > abs_z:
            return "from Above" if y > 0 else "from Below"
        elif abs_z > 0:
            return "from Front" if z > 0 else "from Behind"
        
        return ""
    
    def _generate_event_list_html(self) -> str:
        """Generate HTML for event list."""
        if not self.events:
            return '<p style="color: #a0a0a0; text-align: center; padding: 20px;">No events found in this log file.</p>'
        
        html_parts = []
        for event in self.events:
            event_type = event.get('type', 'unknown')
            timestamp = event.get('timestamp', 'N/A')
            details = event.get('details', {})
            
            # Format event based on type with enhanced details
            event_text = ""
            extra_details = []
            
            if event_type in ['pve_kill', 'pvp_kill']:
                killer = details.get('killer', 'Unknown')
                victim = details.get('victim', 'Unknown')
                weapon = details.get('weapon', 'Unknown')
                event_text = f"{killer} killed {victim}"
                
                # Add weapon details
                weapon_class = details.get('weapon_class', '')
                if weapon and weapon != 'unknown':
                    weapon_text = weapon
                    if weapon_class and weapon_class != 'unknown':
                        weapon_text += f" ({weapon_class})"
                    extra_details.append(f"🎯 {weapon_text}")
                
                # Add damage type
                damage_type = details.get('damage_type')
                if damage_type:
                    extra_details.append(f"💥 {damage_type}")
                
                # Add ship/location
                ship = details.get('ship')
                if ship:
                    extra_details.append(f"📍 {ship}")
                
                # Add direction
                direction = details.get('direction')
                if direction:
                    dir_text = self._format_direction(direction)
                    if dir_text:
                        extra_details.append(f"🧭 {dir_text}")
                
            elif event_type == 'death':
                killer = details.get('killer', 'Unknown')
                victim = details.get('victim', 'Unknown')
                event_text = f"{victim} was killed by {killer}"
                
                damage_type = details.get('damage_type')
                if damage_type:
                    extra_details.append(f"💥 {damage_type}")
                
                ship = details.get('ship')
                if ship:
                    extra_details.append(f"📍 {ship}")
                    
            elif event_type == 'actor_stall':
                player = details.get('player')
                stall_type = details.get('stall_type')
                length = details.get('length')
                if player and stall_type and length:
                    event_text = f"Actor Stall: {player} ({stall_type}, {length}s)"
                else:
                    event_text = "Game disconnect/crash (Actor Stall)"
            elif event_type == 'disconnect':
                event_text = "Network disconnect"
            else:
                event_text = str(details)
            
            # Combine main text with extra details
            if extra_details:
                event_text += f"<br><span style=\"font-size: 0.85em; color: #a0a0a0;\">{' • '.join(extra_details)}</span>"
            
            html_parts.append(f'''
            <div class="event-item {event_type.replace('_', '-')}">
                <span class="event-timestamp">{timestamp}</span>
                <span class="event-type {event_type.replace('_', '-')}">{event_type.upper().replace('_', ' ')}</span>
                <span class="event-details">{event_text}</span>
            </div>
            ''')
        
        return ''.join(html_parts)
    
    def _generate_full_html(self) -> str:
        """Generate full interactive HTML report (future enhancement)."""
        # For now, return simple version
        # TODO: Embed full CSS/JS from static files
        return self._generate_simple_html()
    
    def save(self, output_path: str, format_type: str = 'full') -> None:
        """
        Save HTML report to file.
        
        Args:
            output_path: Output file path
            format_type: 'full' or 'simple'
        """
        html = self.generate_html(format_type)
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"[INFO] HTML report saved to: {output_file}")
        print(f"[INFO] Report size: {len(html)} bytes")

