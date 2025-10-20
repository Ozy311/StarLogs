# Author: Ozy
"""
Flask web server for StarLogs.
Serves dashboard and provides real-time log streaming via SSE.
"""

from flask import Flask, render_template, Response, jsonify, request
import json
import queue
import re
import threading
from typing import Optional, Dict, Any
from event_parser import EventParser, LogEvent
from version import VERSION_INFO, get_about_info


class WebServer:
    """Flask-based web server for StarLogs dashboard."""
    
    @staticmethod
    def check_port_available(port: int, host: str = '127.0.0.1') -> bool:
        """
        Check if a port is available for binding.
        
        Args:
            port: Port number to check
            host: Host address (default: 127.0.0.1)
            
        Returns:
            True if port is available, False if already in use
        """
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind((host, port))
            sock.close()
            return True
        except OSError:
            return False
    
    def __init__(self, port: int = 8080):
        """Initialize the web server."""
        self.port = port
        self.app = Flask(__name__)
        self.event_parser = EventParser()
        
        # Queues for SSE clients
        self.sse_queues = []
        self.sse_lock = threading.Lock()
        
        # Event history buffer (for clients connecting after replay)
        self.event_history = []
        self.event_history_lock = threading.Lock()
        self.max_history = 500  # Keep last 500 events
        
        # Raw log line buffer (for replay catchup)
        self.log_line_history = []
        self.log_line_history_lock = threading.Lock()
        self.max_log_lines = 1000  # Keep last 1000 raw log lines
        
        # Reprocess callback
        self.reprocess_callback = None
        
        # Statistics
        self.stats = {
            'total_lines': 0,
            'disconnects': 0,
            'kills': 0,
            'deaths': 0,
            'pve_kills': 0,
            'pvp_kills': 0,
            'fps_pve_kills': 0,
            'fps_pvp_kills': 0,
            'fps_deaths': 0,
            'actor_stalls': 0,
            'vehicle_destroy_soft': 0,
            'vehicle_destroy_full': 0,
            'vehicle_destroy_combat': 0,
            'vehicle_destroy_collision': 0,
            'vehicle_destroy_selfdestruct': 0,
            'vehicle_destroy_gamerules': 0,
            'session_start': None,
            'log_path': None
        }
        self.stats_lock = threading.Lock()
        
        # Vehicle destruction tracking (for crew kill correlation)
        # Maps vehicle_id -> {timestamp, event_data}
        self.recent_vehicle_destructions = {}
        self.vehicle_destruction_lock = threading.Lock()
        
        # Callbacks for version switching and installations
        self.get_installations_callback = None
        self.switch_version_callback = None
        self.get_logbackups_callback = None
        self.get_game_status_callback = None
        self.validate_path_callback = None
        self.remove_custom_path_callback = None
        self.get_config_callback = None
        self.update_config_callback = None
        self.get_diagnostics_callback = None
        
        # Setup routes
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes."""
        
        @self.app.route('/')
        def index():
            """Serve the main dashboard."""
            from version import __version__
            return render_template('index.html', version=__version__)
        
        @self.app.route('/events')
        def events():
            """SSE endpoint for real-time log streaming."""
            def event_stream():
                # Create a queue for this client - larger size to accommodate history
                client_queue = queue.Queue(maxsize=2000)
                
                with self.sse_lock:
                    self.sse_queues.append(client_queue)
                
                # Send event history FIRST so they show up right away
                event_history_count = 0
                with self.event_history_lock:
                    event_history_count = len(self.event_history)
                    for event_data in self.event_history:
                        try:
                            client_queue.put_nowait(event_data)
                        except queue.Full:
                            print(f"[WARNING] Client queue full when sending event history!")
                            break
                
                # Then send raw log line history
                log_history_count = 0
                with self.log_line_history_lock:
                    log_history_count = len(self.log_line_history)
                    for log_data in self.log_line_history:
                        try:
                            client_queue.put_nowait(log_data)
                        except queue.Full:
                            print(f"[WARNING] Client queue full when sending log history!")
                            break
                
                print(f"[DEBUG] New SSE client connected. Sent {event_history_count} events and {log_history_count} log lines from history")
                
                try:
                    while True:
                        # Get message from queue (blocking)
                        message = client_queue.get()
                        if message is None:
                            break
                        yield f"data: {json.dumps(message)}\n\n"
                except GeneratorExit:
                    pass
                finally:
                    with self.sse_lock:
                        if client_queue in self.sse_queues:
                            self.sse_queues.remove(client_queue)
            
            return Response(event_stream(), mimetype='text/event-stream')
        
        @self.app.route('/status')
        def status():
            """Get current server status and statistics."""
            with self.stats_lock:
                stats_data = dict(self.stats)
            
            # Add game process status
            if hasattr(self, 'get_game_status_callback') and self.get_game_status_callback:
                stats_data['game'] = self.get_game_status_callback()
            else:
                stats_data['game'] = {'running': False, 'pid': None, 'memory_mb': None}
            
            # Add log monitor diagnostics
            if hasattr(self, 'get_diagnostics_callback') and self.get_diagnostics_callback:
                stats_data['monitor'] = self.get_diagnostics_callback()
            
            return jsonify(stats_data)
        
        @self.app.route('/config', methods=['GET', 'POST'])
        def config():
            """Get or update configuration."""
            if request.method == 'GET':
                # Return current config
                return jsonify({'port': self.port})
            else:
                # Update config (placeholder for future features)
                return jsonify({'status': 'ok'})
        
        @self.app.route('/about')
        def about():
            """Get application about information."""
            return jsonify(get_about_info())
        
        @self.app.route('/reprocess', methods=['POST'])
        def reprocess():
            """Reprocess the entire game log file."""
            try:
                # Send clear message to all clients first
                clear_message = {'type': 'clear_all', 'message': 'Reprocessing log...'}
                self.broadcast_message(clear_message)
                
                # Clear all histories and stats
                with self.event_history_lock:
                    self.event_history.clear()
                with self.log_line_history_lock:
                    self.log_line_history.clear()
                with self.stats_lock:
                    self.stats['total_lines'] = 0
                    self.stats['disconnects'] = 0
                    self.stats['kills'] = 0
                    self.stats['deaths'] = 0
                    self.stats['pve_kills'] = 0
                    self.stats['pvp_kills'] = 0
                    self.stats['actor_stalls'] = 0
                    self.stats['suicides'] = 0
                    self.stats['vehicle_destroy_soft'] = 0
                    self.stats['vehicle_destroy_full'] = 0
                    self.stats['vehicle_destroy_combat'] = 0
                    self.stats['vehicle_destroy_collision'] = 0
                    self.stats['vehicle_destroy_selfdestruct'] = 0
                    self.stats['vehicle_destroy_gamerules'] = 0
                
                # Signal the main application to reprocess
                if hasattr(self, 'reprocess_callback') and self.reprocess_callback:
                    self.reprocess_callback()
                
                return jsonify({'status': 'success', 'message': 'Log reprocessing initiated'})
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/log_file', methods=['GET'])
        def get_log_file():
            """Get current log file path."""
            with self.stats_lock:
                log_file = self.stats.get('log_path')
            
            return jsonify({
                'log_file': log_file
            })
        
        @self.app.route('/api/versions', methods=['GET'])
        def get_versions():
            """Get list of available Star Citizen installations."""
            if hasattr(self, 'get_installations_callback') and self.get_installations_callback:
                installations = self.get_installations_callback()
                
                # Add is_active flag based on current log path (stored in stats)
                with self.stats_lock:
                    current_log = self.stats.get('log_path')
                
                for install in installations:
                    # Mark as active if this installation's log matches the current log
                    is_active = (install.get('log_path') == current_log)
                    install['is_active'] = is_active
                
                return jsonify({
                    'installations': installations,
                    'current_log_path': current_log  # Also return current log for fallback matching
                })
            return jsonify({'installations': [], 'current_log_path': None})
        
        @self.app.route('/api/switch_version', methods=['POST'])
        def switch_version():
            """Switch to a different Star Citizen version."""
            try:
                data = request.get_json()
                version = data.get('version')
                
                if not version:
                    return jsonify({'status': 'error', 'message': 'No version specified'}), 400
                
                # Send clear message to all clients
                clear_message = {'type': 'clear_all', 'message': f'Switching to {version}...'}
                self.broadcast_message(clear_message)
                
                # Clear histories
                with self.event_history_lock:
                    self.event_history.clear()
                with self.log_line_history_lock:
                    self.log_line_history.clear()
                with self.stats_lock:
                    self.stats['total_lines'] = 0
                    self.stats['disconnects'] = 0
                    self.stats['kills'] = 0
                    self.stats['deaths'] = 0
                    self.stats['pve_kills'] = 0
                    self.stats['pvp_kills'] = 0
                    self.stats['actor_stalls'] = 0
                    self.stats['suicides'] = 0
                    self.stats['corpses'] = 0
                    self.stats['vehicle_destroy_soft'] = 0
                    self.stats['vehicle_destroy_full'] = 0
                    self.stats['vehicle_destroy_combat'] = 0
                    self.stats['vehicle_destroy_collision'] = 0
                    self.stats['vehicle_destroy_selfdestruct'] = 0
                    self.stats['vehicle_destroy_gamerules'] = 0
                
                # Signal version switch to main application
                if hasattr(self, 'switch_version_callback') and self.switch_version_callback:
                    success = self.switch_version_callback(version)
                    if success:
                        return jsonify({'status': 'success', 'version': version})
                    else:
                        return jsonify({'status': 'error', 'message': f'Failed to switch to {version}'}), 500
                
                return jsonify({'status': 'error', 'message': 'Version switching not available'}), 500
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/logbackups/<version>', methods=['GET'])
        def list_logbackups(version):
            """List LogBackup files for a specific version."""
            try:
                if hasattr(self, 'get_logbackups_callback') and self.get_logbackups_callback:
                    logbackups = self.get_logbackups_callback(version)
                    return jsonify({'files': logbackups})
                return jsonify({'files': []})
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/validate_path', methods=['POST'])
        def validate_path():
            """Validate a custom installation path."""
            try:
                data = request.get_json()
                path = data.get('path', '').strip()
                
                if not path:
                    return jsonify({'valid': False, 'message': 'Path is required'}), 400
                
                if hasattr(self, 'validate_path_callback') and self.validate_path_callback:
                    result = self.validate_path_callback(path)
                    return jsonify(result)
                
                return jsonify({'valid': False, 'message': 'Validation not available'}), 500
            except Exception as e:
                return jsonify({'valid': False, 'message': str(e)}), 500
        
        @self.app.route('/api/remove_custom_path', methods=['POST'])
        def remove_custom_path():
            """Remove a custom installation path."""
            try:
                data = request.get_json()
                version = data.get('version', '').strip()
                
                if not version:
                    return jsonify({'status': 'error', 'message': 'Version is required'}), 400
                
                if hasattr(self, 'remove_custom_path_callback') and self.remove_custom_path_callback:
                    result = self.remove_custom_path_callback(version)
                    return jsonify(result)
                
                return jsonify({'status': 'error', 'message': 'Remove not available'}), 500
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/config', methods=['GET', 'POST'])
        def config_endpoint():
            """Get or update configuration settings."""
            if request.method == 'GET':
                # Return current config (safe subset)
                if hasattr(self, 'get_config_callback') and self.get_config_callback:
                    config = self.get_config_callback()
                    return jsonify(config)
                return jsonify({'web_port': self.port})
            
            elif request.method == 'POST':
                # Update config
                try:
                    data = request.get_json()
                    
                    if hasattr(self, 'update_config_callback') and self.update_config_callback:
                        result = self.update_config_callback(data)
                        return jsonify(result)
                    
                    return jsonify({'status': 'error', 'message': 'Config update not available'}), 500
                except Exception as e:
                    return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/analyze_log', methods=['POST'])
        def analyze_log():
            """Analyze a historical log file."""
            try:
                data = request.get_json()
                log_file = data.get('log_file')
                
                if not log_file:
                    return jsonify({'status': 'error', 'message': 'No log file specified'}), 400
                
                # Import offline analyzer
                from offline_analyzer import OfflineAnalyzer
                from pathlib import Path
                
                # Analyze the log
                analyzer = OfflineAnalyzer(log_file)
                analyzer.parse_all_events()
                
                # Get stats from analyzer
                stats = analyzer.get_statistics()
                
                # Events are already stored as dicts in analyzer.events
                event_list = analyzer.events
                
                return jsonify({
                    'status': 'success',
                    'stats': stats,
                    'events': event_list,
                    'system_info': analyzer.system_info
                })
                
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/api/export_log', methods=['POST'])
        def export_log():
            """Export a log file to HTML."""
            try:
                data = request.get_json()
                log_file = data.get('log_file')
                format_type = data.get('format', 'full')
                
                if not log_file:
                    return jsonify({'status': 'error', 'message': 'No log file specified'}), 400
                
                # Import offline analyzer and HTML generator
                from offline_analyzer import OfflineAnalyzer
                from html_generator import StaticHTMLGenerator
                from pathlib import Path
                import os
                
                # Analyze the log
                analyzer = OfflineAnalyzer(log_file)
                events = analyzer.parse_all_events()
                system_info = analyzer.system_info
                stats = analyzer.get_statistics()
                
                # Generate HTML
                filename = Path(log_file).name
                generator = StaticHTMLGenerator(
                    events=events,
                    system_info=system_info,
                    stats=stats,
                    filename=filename
                )
                html_content = generator.generate_html(format_type=format_type)
                
                # Return as downloadable file
                filename = Path(log_file).stem
                return Response(
                    html_content,
                    mimetype='text/html',
                    headers={
                        'Content-Disposition': f'attachment; filename=starlogs_{filename}.html'
                    }
                )
                
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500
    
    def broadcast_message(self, message: Dict[str, Any]) -> None:
        """
        Broadcast a message to all connected SSE clients.
        
        Args:
            message: Dictionary to send to clients
        """
        with self.sse_lock:
            # Remove full queues (slow clients)
            queues_to_remove = []
            for q in self.sse_queues:
                try:
                    q.put_nowait(message)
                except queue.Full:
                    queues_to_remove.append(q)
            
            for q in queues_to_remove:
                self.sse_queues.remove(q)
    
    def process_log_line(self, line: str) -> None:
        """
        Process a log line and broadcast to clients.
        
        Args:
            line: Raw log line
        """
        # Check for special separator message
        if line == "__REPLAY_COMPLETE__":
            separator_message = {
                'type': 'separator',
                'message': '═══ END OF REPLAY - LIVE LOGGING STARTS HERE ═══'
            }
            # Only add to history for raw log feed, not event summary
            # Event summary will get it once from the broadcast
            with self.log_line_history_lock:
                self.log_line_history.append(separator_message)
            self.broadcast_message(separator_message)
            with self.event_history_lock:
                event_count = len(self.event_history)
            with self.log_line_history_lock:
                log_count = len(self.log_line_history)
            print(f"[DEBUG] Replay complete! Event history: {event_count} events, Raw log history: {log_count} lines")
            return
        
        # Update statistics
        with self.stats_lock:
            self.stats['total_lines'] += 1
        
        # Parse for events
        try:
            event = self.event_parser.parse_line(line)
        except Exception as e:
            print(f"[ERROR] Failed to parse event from line: {e}")
            event = None
        
        if event:
            # Handle vehicle destruction events
            if event.type.value in ['vehicle_destroy_soft', 'vehicle_destroy_full']:
                vehicle_id = event.details.get('vehicle_id')
                if vehicle_id:
                    # Store in recent destructions for crew kill correlation
                    with self.vehicle_destruction_lock:
                        self.recent_vehicle_destructions[vehicle_id] = {
                            'timestamp': event.timestamp,
                            'event': event,
                            'event_message': None  # Will store the message after creating it
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
                # Zone format: 'ANVL_Paladin_6763231335005' contains the vehicle ID
                vehicle_id_match = re.search(r'_(\d{13})$', zone)
                if vehicle_id_match:
                    vehicle_id = vehicle_id_match.group(1)
                    
                    # Look up recent vehicle destruction
                    with self.vehicle_destruction_lock:
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
                                
                                # Update the stored event message if it exists
                                if destruction_data['event_message']:
                                    destruction_data['event_message']['event'] = destruction_event.to_dict()
            
            # Update event-specific stats
            with self.stats_lock:
                if event.type.value == 'disconnect':
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
                elif event.type.value in ['kill', 'pve_kill', 'pvp_kill', 'fps_pve_kill', 'fps_pvp_kill']:
                    self.stats['kills'] += 1
                    if event.type.value == 'pve_kill':
                        self.stats['pve_kills'] += 1
                    elif event.type.value == 'pvp_kill':
                        self.stats['pvp_kills'] += 1
                    elif event.type.value == 'fps_pve_kill':
                        self.stats['fps_pve_kills'] += 1
                    elif event.type.value == 'fps_pvp_kill':
                        self.stats['fps_pvp_kills'] += 1
                elif event.type.value in ['death', 'fps_death']:
                    self.stats['deaths'] += 1
                    if event.type.value == 'fps_death':
                        self.stats['fps_deaths'] += 1
            
            # Create event message
            event_message = {
                'type': 'event',
                'event': event.to_dict()
            }
            
            # Store event_message reference for vehicle destructions (for crew kill correlation)
            if event.type.value in ['vehicle_destroy_soft', 'vehicle_destroy_full']:
                vehicle_id = event.details.get('vehicle_id')
                if vehicle_id:
                    with self.vehicle_destruction_lock:
                        if vehicle_id in self.recent_vehicle_destructions:
                            self.recent_vehicle_destructions[vehicle_id]['event_message'] = event_message
            
            # Add to event history
            with self.event_history_lock:
                self.event_history.append(event_message)
                # Keep only last N events
                if len(self.event_history) > self.max_history:
                    self.event_history = self.event_history[-self.max_history:]
                current_event_count = len(self.event_history)
            
            # Debug: Print every 50th event to show progress
            if current_event_count % 50 == 0:
                print(f"[DEBUG] Event history now at {current_event_count} events (type: {event.type.value})")
            
            # Broadcast event to connected clients
            with self.sse_lock:
                client_count = len(self.sse_queues)
            self.broadcast_message(event_message)
            
            # Debug: Log first few events to verify they're being created correctly
            if current_event_count <= 5:
                print(f"[DEBUG] Event #{current_event_count}: type={event.type.value}, details={list(event.details.keys())}")
        
        # Create raw log line message
        log_line_message = {
            'type': 'log_line',
            'line': line,
            'has_event': event is not None
        }
        
        # Add to log line history
        with self.log_line_history_lock:
            self.log_line_history.append(log_line_message)
            # Keep only last N log lines
            if len(self.log_line_history) > self.max_log_lines:
                self.log_line_history = self.log_line_history[-self.max_log_lines:]
        
        # Broadcast raw log line to connected clients
        self.broadcast_message(log_line_message)
    
    def set_log_path(self, path: str) -> None:
        """Set the current log path in stats."""
        with self.stats_lock:
            self.stats['log_path'] = path
            if self.stats['session_start'] is None:
                from datetime import datetime
                self.stats['session_start'] = datetime.now().isoformat()
    
    def clear_data(self):
        """Clear all event history, log lines, and statistics."""
        with self.event_history_lock:
            self.event_history.clear()
        with self.log_line_history_lock:
            self.log_line_history.clear()
        with self.stats_lock:
            self.stats['total_lines'] = 0
            self.stats['disconnects'] = 0
            self.stats['kills'] = 0
            self.stats['deaths'] = 0
            self.stats['pve_kills'] = 0
            self.stats['pvp_kills'] = 0
            self.stats['actor_stalls'] = 0
            self.stats['suicides'] = 0
            self.stats['corpses'] = 0
            self.stats['vehicle_destroy_soft'] = 0
            self.stats['vehicle_destroy_full'] = 0
            self.stats['vehicle_destroy_combat'] = 0
            self.stats['vehicle_destroy_collision'] = 0
            self.stats['vehicle_destroy_selfdestruct'] = 0
            self.stats['vehicle_destroy_gamerules'] = 0
            # Keep log_path and session_start
    
    def run(self, threaded: bool = True) -> None:
        """
        Start the Flask server.
        
        Args:
            threaded: Whether to run in threaded mode
        """
        # Configure Flask's werkzeug logger
        import logging
        import os
        
        # Don't disable werkzeug - let it log to custom handlers (TUI, etc)
        # Just prevent it from printing to console by removing StreamHandlers
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.INFO)
        
        # Remove any console/stream handlers (but keep custom handlers like TUIHandler)
        handlers_to_remove = [h for h in log.handlers if isinstance(h, logging.StreamHandler)]
        for handler in handlers_to_remove:
            log.removeHandler(handler)
        
        # Same for Flask app logger
        app_log = logging.getLogger('flask.app')
        app_log.setLevel(logging.INFO)
        handlers_to_remove = [h for h in app_log.handlers if isinstance(h, logging.StreamHandler)]
        for handler in handlers_to_remove:
            app_log.removeHandler(handler)
        
        # Suppress the startup banner
        os.environ['FLASK_ENV'] = 'production'
        
        # Check if port is already in use before attempting to run
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('127.0.0.1', self.port))
            sock.close()
        except OSError as e:
            print(f"\n{'='*70}")
            print(f"❌ ERROR: Port {self.port} is already in use!")
            print(f"{'='*70}")
            print(f"\nAnother instance of StarLogs (or another application) is already")
            print(f"running on port {self.port}.")
            print(f"\nPlease either:")
            print(f"  1. Stop the other instance and try again")
            print(f"  2. Close this window (you're probably already viewing the dashboard)")
            print(f"\nTo find what's using port {self.port}:")
            print(f"  Windows: netstat -ano | findstr :{self.port}")
            print(f"{'='*70}\n")
            raise SystemExit(1) from e
        
        self.app.run(
            host='127.0.0.1',
            port=self.port,
            debug=False,
            threaded=threaded,
            use_reloader=False
        )
        
        # Restore environment
        if cli is not None:
            os.environ['FLASK_RUN_FROM_CLI'] = cli
        else:
            os.environ.pop('FLASK_RUN_FROM_CLI', None)

    def start_in_thread(self) -> threading.Thread:
        """
        Start the server in a background thread.
        
        Returns:
            The thread running the server
        """
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        return thread

