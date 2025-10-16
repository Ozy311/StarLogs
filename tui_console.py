# Author: Ozy
"""
TUI Console for StarLogger with split-screen display.
Inspired by btop - separate panels for web server logs and game logs.
"""

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.table import Table
from collections import deque
import threading
import time
import sys
import msvcrt  # For Windows keyboard input


class TUIConsole:
    """Split-screen TUI console for StarLogger."""
    
    def __init__(self, max_lines: int = 50, version: str = "Unknown", log_path: str = "", game_status: dict = None, config_manager=None):
        """
        Initialize TUI console.
        
        Args:
            max_lines: Maximum lines to keep in each log buffer
            version: Game version display name (e.g., "LIVE 4.3.157.21647")
            log_path: Path to the current log file
            game_status: Dict with keys 'running', 'pid', 'memory_mb'
            config_manager: ConfigManager instance for accessing settings
        """
        self.console = Console()
        self.max_lines = max_lines
        self.config_manager = config_manager
        
        # Game environment info
        self.version = version
        self.log_path = log_path
        self.game_status = game_status or {'running': False, 'pid': None, 'memory_mb': None}
        
        # Separate buffers for each log type
        self.web_logs = deque(maxlen=max_lines)
        self.game_logs = deque(maxlen=max_lines)
        
        # Statistics
        self.stats = {
            'total_lines': 0,
            'disconnects': 0,
            'kills': 0,
            'web_requests': 0
        }
        
        # View mode: 'split', 'game', 'web', 'options', 'about'
        self.view_mode = 'split'
        self.previous_view_mode = 'split'  # Track previous mode for modal return
        
        # Options modal state
        self.options_selected_index = 0  # Which option is selected
        self.options_editing = False  # Whether we're editing a value
        self.options_items = ['port', 'auto_detect', 'debug_mode']  # Available options
        self.port_input_buffer = ""  # Buffer for port text input
        
        # Lock for thread safety
        self.lock = threading.Lock()
        
        # Live display
        self.live = None
        self.running = False
        
        # Callback for version switching
        self.on_version_change = None
        self.pending_callback = None  # Callback to run after TUI exits
    
    def add_game_log(self, line: str):
        """Add a game log line."""
        with self.lock:
            self.game_logs.append(line)
            self.stats['total_lines'] += 1
            if 'disconnect' in line.lower():
                self.stats['disconnects'] += 1
    
    def add_web_log(self, line: str):
        """Add a web server log line."""
        with self.lock:
            self.web_logs.append(line)
            self.stats['web_requests'] += 1
    
    def create_layout(self) -> Layout:
        """Create the TUI layout based on view mode."""
        layout = Layout()
        
        if self.view_mode in ['options', 'about']:
            # Modal view (full screen with header/footer)
            layout.split_column(
                Layout(name="header", size=5),
                Layout(name="body", ratio=1),
                Layout(name="footer", size=3)
            )
        elif self.view_mode == 'split':
            # Split screen mode
            layout.split_column(
                Layout(name="header", size=5),
                Layout(name="main"),
                Layout(name="footer", size=3)
            )
            
            layout["main"].split_row(
                Layout(name="game", ratio=1),
                Layout(name="web", ratio=1)
            )
        elif self.view_mode == 'game':
            # Full screen game logs
            layout.split_column(
                Layout(name="header", size=5),
                Layout(name="game"),
                Layout(name="footer", size=3)
            )
        elif self.view_mode == 'web':
            # Full screen web logs
            layout.split_column(
                Layout(name="header", size=5),
                Layout(name="web"),
                Layout(name="footer", size=3)
            )
        
        return layout
    
    def generate_header(self) -> Panel:
        """Generate header panel with stats and version info."""
        table = Table.grid(expand=True)
        table.add_column(justify="left")
        table.add_column(justify="center")
        table.add_column(justify="right")
        
        with self.lock:
            # First row: App name and version
            table.add_row(
                "[bold cyan]StarLogs[/bold cyan] [dim]by Ozy311[/dim] [yellow]FOR THE CUBE![/yellow]",
                f"[bold green]{self.version}[/bold green]",
                f"[bold]Mode:[/bold] {self.view_mode.upper()}  [dim]|[/dim]  Lines: {self.stats['total_lines']}"
            )
            # Second row: Log path and game status
            short_path = self.log_path if len(self.log_path) < 80 else "..." + self.log_path[-77:]
            
            # Game status display
            if self.game_status['running']:
                game_status_text = f"[bold green]Game: Running[/bold green] [dim](PID: {self.game_status['pid']})[/dim]"
            else:
                game_status_text = "[bold yellow]Game: Not Running[/bold yellow]"
            
            table.add_row(
                f"[dim]Path:[/dim] {short_path}",
                game_status_text,
                f"Web: {self.stats['web_requests']}  [dim]|[/dim]  Stalls: {self.stats['disconnects']}"
            )
        
        return Panel(
            table,
            style="bold white on blue",
            border_style="blue"
        )
    
    def generate_game_panel(self) -> Panel:
        """Generate game log panel."""
        with self.lock:
            text = Text("\n".join(list(self.game_logs)))
        
        return Panel(
            text,
            title="[bold cyan]Game Logs[/bold cyan]",
            border_style="cyan",
            subtitle=f"[dim]{len(self.game_logs)}/{self.max_lines} lines[/dim]"
        )
    
    def generate_web_panel(self) -> Panel:
        """Generate web server log panel."""
        with self.lock:
            text = Text("\n".join(list(self.web_logs)))
        
        return Panel(
            text,
            title="[bold yellow]Web Server Logs[/bold yellow]",
            border_style="yellow",
            subtitle=f"[dim]{len(self.web_logs)}/{self.max_lines} lines[/dim]"
        )
    
    def generate_footer(self) -> Panel:
        """Generate footer with controls."""
        if self.view_mode in ['options', 'about']:
            # Modal footer
            text = Text.from_markup(
                "[bold yellow]Modal View:[/bold yellow] Press [cyan]ESC[/cyan] or [cyan]Q[/cyan] to return"
            )
        else:
            # Normal footer
            port = self.config_manager.get('web_port', 8080) if self.config_manager else 8080
            text = Text.from_markup(
                "[bold green]Ready:[/bold green] [cyan]1[/cyan]=Split [cyan]2[/cyan]=Game [cyan]3[/cyan]=Web  "
                "[cyan]O[/cyan]=Options [cyan]A[/cyan]=About [cyan]V[/cyan]=Change Env [cyan]C[/cyan]=Clear [cyan]Q[/cyan]=Quit   "
                f"[dim]|[/dim] [yellow]Web: http://localhost:{port}[/yellow]"
            )
        return Panel(text, style="dim")
    
    def render(self) -> Layout:
        """Render the current layout."""
        layout = self.create_layout()
        
        # Update panels
        layout["header"].update(self.generate_header())
        layout["footer"].update(self.generate_footer())
        
        # Check which panels exist in current view mode
        if self.view_mode == 'options':
            try:
                layout["body"].update(self.render_options_modal())
            except KeyError:
                pass
        elif self.view_mode == 'about':
            try:
                layout["body"].update(self.render_about_modal())
            except KeyError:
                pass
        else:
            try:
                layout["game"].update(self.generate_game_panel())
            except KeyError:
                pass  # Game panel doesn't exist in this view
            
            try:
                layout["web"].update(self.generate_web_panel())
            except KeyError:
                pass  # Web panel doesn't exist in this view
        
        return layout
    
    def set_view_mode(self, mode: str):
        """Change the view mode."""
        with self.lock:
            # Save previous mode if entering modal
            if mode in ['options', 'about'] and self.view_mode not in ['options', 'about']:
                self.previous_view_mode = self.view_mode
            self.view_mode = mode
    
    def return_from_modal(self):
        """Return from modal view to previous mode."""
        with self.lock:
            self.view_mode = self.previous_view_mode
    
    def handle_options_input(self, key):
        """Handle keyboard input for options modal."""
        if not self.config_manager:
            return
        
        selected_item = self.options_items[self.options_selected_index]
        
        # Handle port editing mode
        if self.options_editing and selected_item == 'port':
            if key == b'\r':  # Enter - save the port
                if self.port_input_buffer:
                    try:
                        new_port = int(self.port_input_buffer)
                        if 1024 <= new_port <= 65535:
                            self.config_manager.set('web_port', new_port)
                            self.options_editing = False
                            self.port_input_buffer = ""
                        else:
                            # Invalid range - clear buffer to show error
                            self.port_input_buffer = "ERR"
                    except ValueError:
                        self.port_input_buffer = "ERR"
                else:
                    # Cancel if buffer is empty
                    self.options_editing = False
                    self.port_input_buffer = ""
            
            elif key == b'\x1b':  # ESC - cancel editing
                self.options_editing = False
                self.port_input_buffer = ""
            
            elif key == b'\x08' or key == b'\x7f':  # Backspace
                if self.port_input_buffer:
                    self.port_input_buffer = self.port_input_buffer[:-1]
            
            elif key.isdigit():  # Number input
                digit = key.decode()
                # Only allow up to 5 digits (65535 max)
                if len(self.port_input_buffer) < 5:
                    self.port_input_buffer += digit
            
            return  # Don't process other keys in edit mode
        
        # Arrow keys for navigation (only when not editing)
        if key == b'H':  # Up arrow
            if not self.options_editing:
                self.options_selected_index = (self.options_selected_index - 1) % len(self.options_items)
        
        elif key == b'P':  # Down arrow
            if not self.options_editing:
                self.options_selected_index = (self.options_selected_index + 1) % len(self.options_items)
        
        # Enter or Space to toggle/edit
        elif key in (b'\r', b' '):
            if selected_item == 'port':
                # Start editing port
                self.options_editing = True
                self.port_input_buffer = ""  # Start fresh
            
            elif selected_item in ['auto_detect', 'debug_mode']:
                # Toggle boolean option
                current = self.config_manager.get(selected_item, True)
                self.config_manager.set(selected_item, not current)
    
    def clear_logs(self):
        """Clear all log buffers."""
        with self.lock:
            self.game_logs.clear()
            self.web_logs.clear()
    
    def update_version_info(self, version: str, log_path: str):
        """Update version and log path displayed in header."""
        with self.lock:
            self.version = version
            self.log_path = log_path
    
    def update_game_status(self, game_status: dict):
        """Update the game process status."""
        with self.lock:
            self.game_status = game_status
    
    def render_options_modal(self) -> Panel:
        """Render interactive options modal panel."""
        import version
        app_version = getattr(version, 'VERSION', getattr(version, '__version__', '1.0.0'))
        
        # Get current settings
        port = self.config_manager.get('web_port', 8080) if self.config_manager else 8080
        debug = self.config_manager.get('debug_mode', False) if self.config_manager else False
        auto_detect = self.config_manager.get('auto_detect', True) if self.config_manager else True
        
        # Create table for options
        table = Table.grid(padding=(0, 2))
        table.add_column(style="cyan", justify="right", width=30)
        table.add_column(style="white", width=40)
        
        # Determine which item is selected
        selected_item = self.options_items[self.options_selected_index]
        editing_indicator = " [yellow]✎[/yellow]" if self.options_editing else ""
        
        # Port option
        if selected_item == 'port':
            if self.options_editing and self.port_input_buffer:
                # Show current input buffer with cursor
                port_display = f"[black on yellow] {self.port_input_buffer}█ [/black on yellow]"
            else:
                port_display = f"[black on yellow] {port} [/black on yellow]{editing_indicator}"
        else:
            port_display = f"[yellow]{port}[/yellow]"
        table.add_row("Web Server Port:", port_display)
        
        # Auto-detect option
        auto_status = "[green]Enabled[/green]" if auto_detect else "[red]Disabled[/red]"
        if selected_item == 'auto_detect':
            auto_status = f"[black on yellow] {auto_status} [/black on yellow]{editing_indicator}"
        table.add_row("Auto-Detect Installations:", auto_status)
        
        # Debug mode option
        debug_status = "[green]Enabled[/green]" if debug else "[dim]Disabled[/dim]"
        if selected_item == 'debug_mode':
            debug_status = f"[black on yellow] {debug_status} [/black on yellow]{editing_indicator}"
        table.add_row("Debug Mode:", debug_status)
        
        table.add_row("", "")
        if self.options_editing and selected_item == 'port':
            table.add_row("", "[dim yellow]Type new port (1024-65535), Backspace to delete[/dim yellow]")
            table.add_row("", "[dim yellow]Enter: Save  ESC: Cancel[/dim yellow]")
        else:
            table.add_row("", "[dim]↑/↓: Navigate  Enter/Space: Edit/Toggle[/dim]")
            table.add_row("", "[dim]ESC/Q: Save & Exit[/dim]")
        table.add_row("", "")
        table.add_row("[dim]Note:", "[dim yellow]Changes require restarting StarLogs[/dim yellow]")
        
        return Panel(
            table,
            title=f"[bold cyan]⚙ Options[/bold cyan]",
            subtitle=f"[dim]StarLogs v{app_version}[/dim]",
            border_style="cyan",
            padding=(2, 4)
        )
    
    def render_about_modal(self) -> Panel:
        """Render about modal panel."""
        import version
        app_version = getattr(version, 'VERSION', getattr(version, '__version__', '1.0.0'))
        
        # Create content
        content = Text()
        content.append("StarLogs\n", style="bold cyan")
        content.append(f"Version {app_version}\n\n", style="yellow")
        content.append("FOR THE CUBE!\n\n", style="bold yellow")
        content.append("Author: ", style="bold")
        content.append("Ozy311\n", style="cyan")
        content.append("Organization: ", style="bold")
        content.append("CUBE Org\n\n", style="cyan")
        content.append("Star Citizen Log Parser and Event Tracker\n\n", style="dim")
        
        content.append("Features:\n", style="bold green")
        features = [
            "• Real-time log monitoring and event parsing",
            "• PvE and PvP kill tracking",
            "• Death and disconnect logging",
            "• Actor stall detection (crashes)",
            "• Multi-version support (LIVE, PTU, EPTU)",
            "• Web dashboard with SSE updates",
            "• Offline log analysis and HTML export",
            "• System info extraction from logs"
        ]
        for feature in features:
            content.append(f"{feature}\n", style="white")
        
        return Panel(
            content,
            title="[bold cyan]ℹ About StarLogs[/bold cyan]",
            border_style="cyan",
            padding=(2, 4)
        )
    
    def _handle_input(self):
        """Handle keyboard input in a separate thread."""
        # Try to get debug log path for logging
        try:
            from pathlib import Path
            debug_log = Path(__file__).parent / "starlogs_debug.log"
            
            def _log(msg):
                try:
                    from datetime import datetime
                    with open(debug_log, 'a', encoding='utf-8') as f:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                        f.write(f"[{timestamp}] [TUI] {msg}\n")
                        f.flush()
                except:
                    pass
        except:
            def _log(msg):
                pass
        
        _log("TUI input handler started")
        
        while self.running:
            if msvcrt.kbhit():
                key = msvcrt.getch()
                _log(f"Key pressed: {key}")
                
                # Handle special keys (arrow keys on Windows)
                if key in (b'\xe0', b'\x00'):
                    # Arrow key prefix, get next byte
                    if msvcrt.kbhit():
                        key = msvcrt.getch()
                        _log(f"Special key code: {key}")
                
                # Handle key presses
                if key == b'1':
                    self.set_view_mode('split')
                elif key == b'2':
                    self.set_view_mode('game')
                elif key == b'3':
                    self.set_view_mode('web')
                elif key in (b'o', b'O'):
                    _log("O key detected - opening options")
                    self.options_selected_index = 0  # Reset selection
                    self.options_editing = False
                    self.port_input_buffer = ""  # Clear input buffer
                    self.set_view_mode('options')
                elif key in (b'a', b'A'):
                    _log("A key detected - opening about")
                    self.set_view_mode('about')
                elif key == b'\x1b':  # ESC key
                    _log("ESC key detected")
                    if self.view_mode in ['options', 'about']:
                        _log("Returning from modal view")
                        if self.options_editing and self.options_items[self.options_selected_index] == 'port':
                            # Cancel port editing only
                            self.options_editing = False
                            self.port_input_buffer = ""
                        else:
                            # Exit modal
                            self.options_editing = False
                            self.port_input_buffer = ""
                            self.return_from_modal()
                # Options modal navigation
                elif self.view_mode == 'options':
                    self.handle_options_input(key)
                elif key in (b'v', b'V'):
                    _log("V key detected - triggering version change")
                    # Trigger version change
                    if self.on_version_change:
                        _log(f"on_version_change callback exists: {self.on_version_change}")
                        _log("Setting self.running = False to exit TUI")
                        self.running = False  # Stop TUI - this will exit the Live context
                        _log("Breaking out of input handler loop")
                        # Store callback to call AFTER TUI exits
                        self.pending_callback = self.on_version_change
                        break
                    else:
                        _log("ERROR: on_version_change callback is None!")
                elif key in (b'c', b'C'):
                    self.clear_logs()
                elif key in (b'q', b'Q'):
                    if self.view_mode in ['options', 'about']:
                        _log("Q key in modal - returning to previous view")
                        self.return_from_modal()
                    else:
                        self.running = False
                        break
            
            time.sleep(0.1)
        
        _log("TUI input handler exiting")
    
    def start(self):
        """Start the TUI display."""
        self.running = True
        self.pending_callback = None
        
        # Start keyboard input handler in background thread
        input_thread = threading.Thread(target=self._handle_input, daemon=True)
        input_thread.start()
        
        with Live(
            self.render(),
            console=self.console,
            refresh_per_second=4,
            screen=True
        ) as live:
            self.live = live
            
            while self.running:
                live.update(self.render())
                time.sleep(0.25)
        
        # TUI has exited - now call pending callback if set
        if self.pending_callback:
            time.sleep(0.5)  # Give terminal a moment to settle
            self.pending_callback()
    
    def stop(self):
        """Stop the TUI display."""
        self.running = False

