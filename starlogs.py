# Author: Ozy
"""
StarLogs - Star Citizen Log Parser
Main entry point for the application.
"""

# Ensure UTF-8 encoding for proper character handling
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

import sys
import signal
import time
import logging
import argparse
from datetime import datetime
from pathlib import Path
from game_detector import GameDetector
from config_manager import ConfigManager
from log_monitor import LogMonitor
from web_server import WebServer
from tui_console import TUIConsole
from process_monitor import ProcessMonitor
from offline_analyzer import OfflineAnalyzer, list_logbackups
from html_generator import StaticHTMLGenerator
import threading
import os

# Windows-specific imports for keyboard input
if os.name == 'nt':
    import msvcrt


class StarLogs:
    """Main application class for StarLogs."""
    
    def __init__(self, use_tui: bool = True):
        """
        Initialize StarLogger application.
        
        Args:
            use_tui: Whether to use TUI mode (default: True)
        """
        self.config_manager = ConfigManager()
        self.game_detector = GameDetector()
        self.process_monitor = ProcessMonitor()
        self.log_monitor = None
        self.web_server = None
        self.tui = None
        self.game_status = {'running': False, 'pid': None, 'memory_mb': None}  # Will be initialized after version selection
        self.use_tui = use_tui
        self.running = False
        self.installations = []  # Store detected installations
        self.active_version = None  # Currently active version
        self.current_log_path = None  # Current log file path
        
        # Debug logging
        self.debug_mode = self.config_manager.get('debug_mode', False)
        self.debug_log_path = Path(__file__).parent / "starlogs_debug.log"
        if self.debug_mode:
            self._debug_log("="*60)
            self._debug_log(f"StarLogs initialized at {datetime.now()}")
            self._debug_log(f"TUI mode: {use_tui}")
            self._debug_log("="*60)
    
    def _debug_log(self, message: str):
        """Write debug message to log file if debug mode is enabled."""
        if self.debug_mode:
            try:
                with open(self.debug_log_path, 'a', encoding='utf-8') as f:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    f.write(f"[{timestamp}] {message}\n")
                    f.flush()  # Force write immediately
            except Exception as e:
                # Don't let debug logging break the app
                print(f"Debug log error: {e}")
    
    def _setup_logging(self):
        """Setup logging to redirect Flask logs to TUI."""
        # Suppress werkzeug console output
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.INFO)
        log.handlers.clear()
        
        # Create custom handler that sends to TUI
        class TUIHandler(logging.Handler):
            def __init__(self, tui_console):
                super().__init__()
                self.tui = tui_console
            
            def emit(self, record):
                try:
                    msg = self.format(record)
                    self.tui.add_web_log(msg)
                except Exception:
                    pass
        
        handler = TUIHandler(self.tui)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s', datefmt='%H:%M:%S'))
        log.addHandler(handler)
    
    def print_banner(self):
        """Print application banner."""
        if not self.use_tui:
            print("\n" + "=" * 60)
            print("⭐ StarLogs - Star Citizen Log Parser")
            print("=" * 60)
            print()
    
    def select_game_version(self, skip_countdown: bool = False) -> str:
        """
        Prompt user to select a game version.
        Auto-selects if saved preference exists and TUI mode.
        
        Args:
            skip_countdown: If True, always prompt user (no auto-countdown)
        
        Returns:
            Path to the selected Game.log file
        """
        print("Detecting Star Citizen installations...")
        self.installations = self.game_detector.find_installations()
        
        if not self.installations:
            print("\n[WARNING] No Star Citizen installations found!")
            print("   Searched all drives for Roberts Space Industries folder")
            print("\nWould you like to enter a custom installation path? (y/n): ", end='', flush=True)
            
            try:
                response = input().strip().lower()
                if response not in ['y', 'yes']:
                    print("\nPlease ensure Star Citizen is installed and try again.")
                    sys.exit(1)
                
                # Prompt for custom path
                print("\nEnter the path to your Star Citizen installation.")
                print("You can provide either:")
                print("  1. The parent folder (e.g., D:\\StarCitizen\\StarCitizen)")
                print("  2. The version folder (e.g., D:\\StarCitizen\\StarCitizen\\LIVE)")
                print("\nExamples:")
                print("  D:\\StarCitizen\\StarCitizen")
                print("  E:\\Games\\StarCitizen")
                print("  C:\\Program Files\\Roberts Space Industries\\StarCitizen")
                print("\nPath: ", end='', flush=True)
                
                custom_path = input().strip().strip('"')  # Remove quotes if present
                
                if not custom_path:
                    print("\n[ERROR] No path provided.")
                    sys.exit(1)
                
                print(f"\nValidating path: {custom_path}")
                validated = self.game_detector.validate_custom_path(custom_path)
                
                if not validated:
                    print("\n[ERROR] Invalid Star Citizen installation path!")
                    print("   Could not find Game.log or typical Star Citizen files.")
                    print("   Please check the path and try again.")
                    sys.exit(1)
                
                print(f"[OK] Found {validated['display_name']}")
                self.installations = [validated]
                
            except (EOFError, KeyboardInterrupt):
                print("\n\nCancelled.")
                sys.exit(1)
        
        # Store installations in config
        self.config_manager.store_installations(self.installations)
        
        print(f"\n[OK] Found {len(self.installations)} installation(s):\n")
        
        for idx, install in enumerate(self.installations, 1):
            display = install.get('display_name', install['version'])
            print(f"  {idx}. {display}")
            print(f"     Path: {install['path']}")
        
        print()
        
        # Check if we have a saved preference
        active_version = self.config_manager.get('active_version')
        default_choice = None
        
        if active_version:
            for idx, install in enumerate(self.installations, 1):
                if install['version'] == active_version:
                    default_choice = idx
                    print(f"Last used: {install.get('display_name', active_version)} (option {idx})")
                    break
        
        # If using TUI and we have a saved preference, countdown to auto-select (unless skipped)
        if self.use_tui and default_choice and not skip_countdown:
            selected_install = self.installations[default_choice - 1]
            print(f"\n[AUTO] Starting {selected_install.get('display_name', active_version)} in 5 seconds...")
            print("Press any key to choose a different version...\n")
            
            # 5-second countdown with keyboard interrupt check
            interrupted = False
            for i in range(5, 0, -1):
                sys.stdout.write(f"\rAuto-starting in {i}... ")
                sys.stdout.flush()
                
                # Check for keyboard input (non-blocking)
                if self._check_keyboard_input():
                    interrupted = True
                    # Clear the input buffer
                    if os.name == 'nt':
                        while msvcrt.kbhit():
                            msvcrt.getch()
                    print("\n\n[INPUT] Countdown interrupted!\n")
                    break
                    
                time.sleep(1)
            
            # If not interrupted, auto-select
            if not interrupted:
                print("\n")
                selected = self.installations[default_choice - 1]
                self.active_version = selected['version']
                return selected['log_path']
            # Otherwise fall through to manual selection below
        
        # Get user selection (interactive mode)
        while True:
            try:
                if default_choice:
                    choice_str = input(f"Select version [1-{len(self.installations)}] (default: {default_choice}): ").strip()
                    if not choice_str:
                        choice_str = str(default_choice)
                else:
                    choice_str = input(f"Select version [1-{len(self.installations)}]: ").strip()
                
                choice = int(choice_str)
                if 1 <= choice <= len(self.installations):
                    selected = self.installations[choice - 1]
                    
                    # Save preference
                    self.active_version = selected['version']
                    self.config_manager.set_active_version(selected['version'])
                    
                    return selected['log_path']
                else:
                    print(f"Please enter a number between 1 and {len(self.installations)}")
            except ValueError:
                print("Please enter a valid number")
            except EOFError:
                # Handle background process - use default if available
                if default_choice:
                    print(f"\n[AUTO] Using default: {active_version}")
                    selected = self.installations[default_choice - 1]
                    self.active_version = selected['version']
                    return selected['log_path']
                else:
                    print("\n[ERROR] No saved preference and cannot prompt in background")
                    sys.exit(1)
    
    def _check_keyboard_input(self) -> bool:
        """
        Check if a key has been pressed (non-blocking).
        Windows-only (Star Citizen is Windows-only).
        
        Returns:
            True if key was pressed, False otherwise
        """
        if os.name == 'nt':  # Windows
            return msvcrt.kbhit()
        else:
            # Star Citizen is Windows-only, no need for Linux/Mac support yet
            return False
    
    def on_log_line(self, line: str):
        """
        Callback for new log lines.
        
        Args:
            line: New log line from the monitor
        """
        # Send to TUI or console
        if self.use_tui and self.tui:
            self.tui.add_game_log(line)
        else:
            print(f"[LOG] {line}")
        
        # Send to web server for processing and broadcasting
        if self.web_server:
            self.web_server.process_log_line(line)
    
    def get_installations_callback(self):
        """Callback for web server to get installations list."""
        return self.installations
    
    def get_game_status_callback(self):
        """Callback for web server to get game process status."""
        return self.game_status
    
    def update_game_status(self):
        """Update game process status (called periodically)."""
        self.game_status = self.process_monitor.get_game_status()
        if self.tui:
            self.tui.update_game_status(self.game_status)
    
    def switch_version_callback(self, version: str) -> bool:
        """
        Callback for web server to switch versions.
        
        Args:
            version: Version name to switch to (e.g., "LIVE", "PTU")
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Find the installation
            target_install = None
            for install in self.installations:
                if install['version'] == version:
                    target_install = install
                    break
            
            if not target_install:
                print(f"[ERROR] Version {version} not found")
                return False
            
            new_log_path = target_install.get('log_path')
            if not new_log_path:
                print(f"[ERROR] No log file found for {version}")
                return False
            
            # Stop current monitor
            if self.log_monitor:
                self.log_monitor.stop()
            
            # Update active version
            self.active_version = version
            self.config_manager.set_active_version(version)
            
            # Restart monitor with new path
            self.log_monitor = LogMonitor(new_log_path, self.on_log_line)
            if not self.log_monitor.start(replay_all=True):
                print(f"[ERROR] Failed to start monitor for {version}")
                return False
            
            if self.web_server:
                self.web_server.set_log_path(new_log_path)
            
            print(f"[INFO] Switched to {version}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to switch version: {e}")
            return False
    
    def get_logbackups_callback(self, version: str):
        """
        Callback for web server to list LogBackup files.
        
        Args:
            version: Version name (e.g., "LIVE", "PTU")
            
        Returns:
            List of LogBackup file information
        """
        try:
            logbackups_path = self.game_detector.get_logbackups_path(version)
            if logbackups_path:
                return list_logbackups(logbackups_path)
            return []
        except Exception as e:
            print(f"[ERROR] Failed to list LogBackups: {e}")
            return []
    
    def validate_path_callback(self, path: str) -> dict:
        """
        Callback for web server to validate a custom installation path.
        
        Args:
            path: Path to validate
            
        Returns:
            Dict with 'valid' (bool) and optional 'message' (str) and 'version' (str)
        """
        from pathlib import Path
        
        path_obj = Path(path)
        
        # Check if path exists
        if not path_obj.exists():
            return {'valid': False, 'message': 'Path does not exist'}
        
        # Check for build_manifest.id file
        manifest_file = path_obj / 'build_manifest.id'
        if not manifest_file.exists():
            return {'valid': False, 'message': 'Not a valid Star Citizen installation (missing build_manifest.id)'}
        
        # Try to extract version metadata
        metadata = self.game_detector.get_version_metadata(path_obj)
        if not metadata:
            return {'valid': False, 'message': 'Could not read version information'}
        
        # Valid! Extract version name from path (usually LIVE, PTU, EPTU, etc.)
        version_name = path_obj.name
        version_string = f"{metadata.get('branch', 'unknown')} {metadata.get('version', 'unknown')}"
        
        # Add to config as custom installation
        self.config_manager.add_custom_installation(
            version=version_name,
            path=str(path_obj),
            metadata=metadata
        )
        
        # Refresh installations list
        self.installations = self.game_detector.find_installations()
        
        return {
            'valid': True,
            'version': version_string,
            'message': f'Added {version_name} installation'
        }
    
    def remove_custom_path_callback(self, version: str) -> dict:
        """
        Callback for web server to remove a custom installation.
        
        Args:
            version: Version name to remove
            
        Returns:
            Dict with 'status' and optional 'message'
        """
        # Check if this is a custom installation
        result = self.config_manager.remove_custom_installation(version)
        
        if result:
            # Refresh installations list
            self.installations = self.game_detector.find_installations()
            return {'status': 'success', 'message': f'Removed {version}'}
        else:
            return {'status': 'error', 'message': f'Cannot remove {version} (not a custom installation)'}
    
    def get_config_callback(self) -> dict:
        """
        Callback for web server to get configuration.
        
        Returns:
            Dict with safe config values
        """
        return {
            'web_port': self.config_manager.get('web_port', 8080),
            'auto_detect': self.config_manager.get('auto_detect', True),
            'debug_mode': self.config_manager.get('debug_mode', False)
        }
    
    def update_config_callback(self, updates: dict) -> dict:
        """
        Callback for web server to update configuration.
        
        Args:
            updates: Dict of config keys to update
            
        Returns:
            Dict with 'status' and optional 'message'
        """
        try:
            # Only allow updating certain fields
            allowed_fields = ['web_port', 'auto_detect', 'debug_mode']
            
            for key, value in updates.items():
                if key in allowed_fields:
                    self.config_manager.set(key, value)
            
            return {'status': 'success', 'message': 'Configuration updated'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        if not self.use_tui:
            print("\n\nShutting down StarLogs...")
        
        self.running = False
        
        if self.tui:
            self.tui.stop()
        
        if self.log_monitor:
            self.log_monitor.stop()
        
        sys.exit(0)
    
    def handle_version_change(self):
        """Handle user-initiated version change from TUI."""
        error_log_path = Path(__file__).parent / "starlogs_error.log"
        
        self._debug_log("\n" + "="*60)
        self._debug_log("HANDLE_VERSION_CHANGE called")
        self._debug_log("="*60)
        
        try:
            # Log that we're starting
            self._debug_log("Step 1: Writing to error log")
            with open(error_log_path, 'a') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"Version change started at {datetime.now()}\n")
                f.write(f"{'='*60}\n")
            
            # Clear screen
            self._debug_log("Step 2: Clearing screen")
            import os
            os.system('cls' if os.name == 'nt' else 'clear')
            
            # Stop current monitoring
            self._debug_log(f"Step 3: Stopping log monitor (exists: {self.log_monitor is not None})")
            if self.log_monitor:
                self.log_monitor.stop()
                self._debug_log("  - Log monitor stopped")
            
            # Show version selection (skip auto-countdown for manual switch)
            self._debug_log("Step 4: Showing version selection banner")
            print("\n" + "=" * 60)
            print("⭐ StarLogs - Change Game Environment")
            print("=" * 60 + "\n")
            
            self._debug_log("Step 5: Calling select_game_version(skip_countdown=True)")
            log_path = self.select_game_version(skip_countdown=True)
            self._debug_log(f"  - Selected log_path: {log_path}")
            self._debug_log(f"  - Active version: {self.active_version}")
            self.current_log_path = log_path
            
            # Update TUI with new version info
            self._debug_log(f"Step 6: Updating TUI (exists: {self.tui is not None})")
            if self.tui:
                selected_install = next((i for i in self.installations if i['version'] == self.active_version), None)
                self._debug_log(f"  - Found installation: {selected_install is not None}")
                if selected_install:
                    display_name = selected_install.get('display_name', self.active_version)
                    self._debug_log(f"  - Display name: {display_name}")
                    self.tui.update_version_info(display_name, log_path)
                    self._debug_log("  - TUI updated")
            
            # Restart log monitor with new path
            self._debug_log(f"Step 7: Restarting services (web_server exists: {self.web_server is not None})")
            if self.web_server:
                self._debug_log("  - Clearing web server data")
                self.web_server.clear_data()
                self._debug_log("  - Setting new log path")
                self.web_server.set_log_path(log_path)
                self._debug_log("  - Web server updated")
            
            self._debug_log(f"Step 8: Creating new LogMonitor for {log_path}")
            self.log_monitor = LogMonitor(log_path, self.on_log_line)
            self._debug_log("  - LogMonitor created")
            
            self._debug_log("Step 9: Starting log monitor with replay_all=True")
            self.log_monitor.start(replay_all=True)
            self._debug_log("  - LogMonitor started")
            
            # Restart TUI
            self._debug_log(f"Step 10: Restarting TUI (exists: {self.tui is not None})")
            if self.tui:
                self._debug_log("  - Adding switched message to TUI")
                self.tui.add_game_log(f"\n[OK] Switched to: {log_path}")
                self._debug_log("  - Setting TUI running flag to True")
                self.tui.running = True  # Reset running flag
                self._debug_log("  - Calling TUI.start()")
                self.tui.start()
                self._debug_log("  - TUI.start() returned")
            
            self._debug_log("Step 11: handle_version_change completed successfully")
                
        except Exception as e:
            self._debug_log(f"EXCEPTION in handle_version_change: {type(e).__name__}: {str(e)}")
            import traceback
            self._debug_log("Full traceback:")
            for line in traceback.format_exc().split('\n'):
                self._debug_log(f"  {line}")
            
            # Write full error to log file
            with open(error_log_path, 'a') as f:
                f.write(f"\nERROR at {datetime.now()}:\n")
                f.write(f"{str(e)}\n\n")
                traceback.print_exception(type(e), e, e.__traceback__, file=f)
            
            # Show error on screen and wait
            print(f"\n[ERROR] Failed to switch version: {e}")
            print(f"\nFull error logged to: {error_log_path}")
            if self.debug_mode:
                print(f"Debug log: {self.debug_log_path}")
            print("\nError details:")
            traceback.print_exc()
            print("\n" + "="*60)
            print("Press Ctrl+C to exit (error logged for review)")
            print("="*60)
            
            # Keep it open so user can see
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                sys.exit(1)
    
    def run(self):
        """Main application run loop."""
        self.print_banner()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Select game version
        log_path = self.select_game_version()
        self.current_log_path = log_path
        
        # Initialize TUI with version info after selection
        if self.use_tui:
            selected_install = next((i for i in self.installations if i['version'] == self.active_version), None)
            if selected_install:
                # Get initial game status
                self.game_status = self.process_monitor.get_game_status()
                self.tui = TUIConsole(
                    version=selected_install.get('display_name', self.active_version),
                    log_path=log_path,
                    game_status=self.game_status,
                    config_manager=self.config_manager
                )
                # Set version change callback
                self.tui.on_version_change = self.handle_version_change
                # Setup logging to redirect to TUI
                self._setup_logging()
        
        if not self.use_tui:
            print(f"\n[OK] Selected: {log_path}\n")
        
        # Get web server port from config
        port = self.config_manager.get('web_port', 8080)
        
        # Initialize web server
        if not self.use_tui:
            print("Starting web server...")
        
        self.web_server = WebServer(port=port)
        self.web_server.set_log_path(log_path)
        
        # Set up callbacks
        def reprocess_callback():
            if self.log_monitor and self.log_monitor.is_running():
                line_count = self.log_monitor.trigger_reprocess()
                print(f"[INFO] Reprocessed {line_count} log lines")
        self.web_server.reprocess_callback = reprocess_callback
        self.web_server.get_installations_callback = self.get_installations_callback
        self.web_server.switch_version_callback = self.switch_version_callback
        self.web_server.get_logbackups_callback = self.get_logbackups_callback
        self.web_server.get_game_status_callback = self.get_game_status_callback
        self.web_server.validate_path_callback = self.validate_path_callback
        self.web_server.remove_custom_path_callback = self.remove_custom_path_callback
        self.web_server.get_config_callback = self.get_config_callback
        self.web_server.update_config_callback = self.update_config_callback
        
        # Start web server in background thread
        server_thread = self.web_server.start_in_thread()
        
        # Give the server a moment to start
        time.sleep(1.5)
        
        # Verify server is running
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            if result != 0:
                if not self.use_tui:
                    print("[WARNING] Web server may not have started properly")
        except Exception:
            pass
        
        if not self.use_tui:
            print(f"\n[OK] StarLogs listening on http://localhost:{port}")
            print(f"[OK] Attached to: {log_path}")
            print("\nPress Ctrl+C to stop\n")
            print("-" * 60)
            print("LIVE LOG FEED:")
            print("-" * 60 + "\n")
        
        # Initialize log monitor
        self.log_monitor = LogMonitor(log_path, self.on_log_line)
        
        # Start monitoring - replay entire log from game boot
        if not self.use_tui:
            print("[INFO] Replaying log file from game boot...")
        if not self.log_monitor.start(replay_all=True):
            if not self.use_tui:
                print("\n[ERROR] Failed to start log monitor")
            sys.exit(1)
        
        self.running = True
        
        # Start game process monitoring thread
        def monitor_game_process():
            while self.running:
                self.update_game_status()
                time.sleep(3)  # Check every 3 seconds
        
        game_monitor_thread = threading.Thread(target=monitor_game_process, daemon=True)
        game_monitor_thread.start()
        
        # Start TUI or simple loop
        if self.use_tui:
            # Add initial message
            self.tui.add_game_log(f"[OK] Connected to: {log_path}")
            self.tui.add_web_log(f"[OK] Web server started on http://localhost:{port}")
            
            # Start TUI in main thread
            try:
                self.tui.start()
            except KeyboardInterrupt:
                self.signal_handler(None, None)
        else:
            # Keep main thread alive
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.signal_handler(None, None)


def analyze_log(log_file: str, output: str = None, format_type: str = 'full'):
    """
    Analyze a log file offline and generate HTML report.
    
    Args:
        log_file: Path to the Game.log file
        output: Output HTML file path (defaults to logfile_report.html)
        format_type: Report format ('full' or 'simple')
    """
    print("\n" + "=" * 60)
    print("⭐ StarLogs - Offline Log Analysis")
    print("=" * 60 + "\n")
    
    # Default output filename
    if not output:
        log_path = Path(log_file)
        output = log_path.parent / f"{log_path.stem}_report.html"
    
    try:
        # Create analyzer
        analyzer = OfflineAnalyzer(log_file)
        
        # Parse all events
        events = analyzer.parse_all_events()
        stats = analyzer.get_statistics()
        system_info = analyzer.get_system_info()
        filename = analyzer.get_log_filename()
        
        # Generate HTML report
        generator = StaticHTMLGenerator(events, system_info, stats, filename)
        generator.save(output, format_type)
        
        print(f"\n[SUCCESS] Analysis complete!")
        print(f"[INFO] Report saved to: {output}")
        print(f"\n{'='*60}\n")
        
    except FileNotFoundError as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Entry point for the application."""
    parser = argparse.ArgumentParser(
        description='StarLogs - Star Citizen Log Parser',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Live monitoring (default)
  python starlogs.py
  
  # Offline analysis
  python starlogs.py analyze "G:\\StarCitizen\\LIVE\\Game.log"
  python starlogs.py analyze logfile.log --output report.html --format simple
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze a log file offline')
    analyze_parser.add_argument('logfile', help='Path to the Game.log file')
    analyze_parser.add_argument('--output', '-o', help='Output HTML file path')
    analyze_parser.add_argument('--format', '-f', choices=['full', 'simple'], 
                               default='full', help='Report format (default: full)')
    
    args = parser.parse_args()
    
    # Handle commands
    if args.command == 'analyze':
        analyze_log(args.logfile, args.output, args.format)
    else:
        # Default: live monitoring mode
        app = StarLogs()
        app.run()


if __name__ == '__main__':
    main()

