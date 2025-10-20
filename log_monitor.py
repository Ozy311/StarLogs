# Author: Ozy
"""
Log file monitor for Star Citizen Game.log.
Aggressive polling-based monitoring for real-time performance.
Watchdog is unreliable on Windows for rapidly-changing files - pure polling is faster and more reliable.
"""

import time
import os
import sys
from pathlib import Path
from typing import Callable, Optional
from datetime import datetime
import threading
import traceback


# Global debug flag (set by main app)
_DEBUG_ENABLED = False

def set_debug_logging(enabled: bool):
    """Enable or disable debug logging at runtime."""
    global _DEBUG_ENABLED
    _DEBUG_ENABLED = enabled

# Debug logging helper
def _debug_log(msg: str):
    """Write debug messages to starlogs_debug.log for troubleshooting (only if debug enabled)."""
    if not _DEBUG_ENABLED:
        return
    
    try:
        debug_log = Path(__file__).parent / "starlogs_debug.log"
        with open(debug_log, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            f.write(f"[{timestamp}] [LogMonitor] {msg}\n")
            f.flush()
    except Exception as e:
        # Fail silently - don't break monitoring if debug logging fails
        pass


class LogFilePoller:
    """Aggressively polls log file for changes (more reliable than watchdog on Windows)."""
    
    def __init__(self, log_path: str, callback: Callable[[str], None], parent_monitor):
        """
        Initialize poller.
        
        Args:
            log_path: Path to the log file to monitor
            callback: Function to call with new log lines
            parent_monitor: Reference to parent LogMonitor for diagnostics
        """
        self.log_path = Path(log_path)
        self.callback = callback
        self.parent_monitor = parent_monitor
        self.last_position = 0
        self._lock = threading.Lock()
        
        # Get initial file size
        if self.log_path.exists():
            self.last_position = self.log_path.stat().st_size
    
    def check_for_changes(self):
        """Check for file changes and read new lines."""
        with self._lock:
            try:
                _debug_log(f"Polling check started for {self.log_path}")
                
                if not self.log_path.exists():
                    _debug_log(f"Log file does not exist: {self.log_path}")
                    return
                
                current_size = self.log_path.stat().st_size
                _debug_log(f"File size: {current_size}, last position: {self.last_position}")
                
                # Handle log rotation (file got smaller)
                if current_size < self.last_position:
                    _debug_log(f"Log rotation detected - resetting position")
                    self.last_position = 0
                
                if current_size > self.last_position:
                    bytes_read = current_size - self.last_position
                    _debug_log(f"New data available: {bytes_read} bytes")
                    
                    # Use Windows file sharing flags to prevent locking game's log writes
                    # This prevents game stuttering/hanging when we read the log
                    if sys.platform == 'win32':
                        try:
                            # Try using win32file for proper sharing control
                            import win32file
                            import pywintypes
                            
                            _debug_log("Opening file with win32file (FILE_SHARE_WRITE enabled)")
                            # Open with FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE
                            # This allows the game to write while we read (critical!)
                            handle = win32file.CreateFile(
                                str(self.log_path),
                                win32file.GENERIC_READ,
                                win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE | win32file.FILE_SHARE_DELETE,
                                None,
                                win32file.OPEN_EXISTING,
                                0,
                                None
                            )
                            # Convert handle to file descriptor
                            import msvcrt
                            fd = msvcrt.open_osfhandle(handle.Detach(), os.O_RDONLY)
                            f = os.fdopen(fd, 'r', encoding='utf-8', errors='ignore', buffering=8192)
                            _debug_log("File opened successfully with win32file")
                        except ImportError as ie:
                            # Fallback if pywin32 not available - os.open should work but less explicit
                            _debug_log(f"win32file not available ({ie}), using os.open fallback")
                            import msvcrt
                            fd = os.open(str(self.log_path), os.O_RDONLY | os.O_BINARY, 0)
                            f = os.fdopen(fd, 'r', encoding='utf-8', errors='ignore', buffering=8192)
                            _debug_log("File opened with os.open fallback")
                        except Exception as win_err:
                            _debug_log(f"ERROR opening with win32file: {win_err}")
                            _debug_log(f"Traceback: {traceback.format_exc()}")
                            raise
                    else:
                        # Non-Windows fallback (Linux/Mac don't have same locking issues)
                        _debug_log("Opening file with standard open() (non-Windows)")
                        f = open(self.log_path, 'r', encoding='utf-8', errors='ignore', buffering=8192)
                    
                    try:
                        f.seek(self.last_position)
                        new_lines = f.read()
                        self.last_position = f.tell()
                        _debug_log(f"Read {len(new_lines)} characters from file")
                        
                        # Process each line
                        line_count = 0
                        for line in new_lines.splitlines():
                            if line.strip():
                                self.callback(line)
                                line_count += 1
                        
                        _debug_log(f"Processed {line_count} lines")
                        
                        # Update parent monitor stats
                        if line_count > 0:
                            self.parent_monitor.lines_read += line_count
                            self.parent_monitor.bytes_read += bytes_read
                            self.parent_monitor.check_count += 1
                    finally:
                        f.close()
                        _debug_log("File closed successfully")
                else:
                    _debug_log("No new data - skipping read")
                        
            except Exception as e:
                error_msg = f"ERROR in check_for_changes: {type(e).__name__}: {e}"
                error_trace = traceback.format_exc()
                _debug_log(error_msg)
                _debug_log(f"Full traceback:\n{error_trace}")
                print(f"[ERROR] Reading log file: {e}")
                print(f"[ERROR] See starlogs_debug.log for full details")
                traceback.print_exc()


class LogMonitor:
    """Monitors a Star Citizen log file with aggressive polling (no watchdog)."""
    
    def __init__(self, log_path: str, line_callback: Callable[[str], None], poll_interval: float = 1.0):
        """
        Initialize log monitor.
        
        Args:
            log_path: Path to the Game.log file
            line_callback: Function to call with each new log line
            poll_interval: Time in seconds between polling checks (default: 1.0)
        """
        self.log_path = Path(log_path)
        self.line_callback = line_callback
        self.poll_interval = poll_interval
        self.poller = None
        self._running = False
        self._polling_thread = None
        
        # Diagnostics
        self.check_count = 0
        self.lines_read = 0
        self.bytes_read = 0
        self.start_time = None
        
        _debug_log(f"LogMonitor initialized with poll_interval={poll_interval}s")
    
    def replay_entire_log(self) -> int:
        """
        Read and replay the ENTIRE log file from the beginning.
        This gathers all data since game boot.
        
        Returns:
            Number of lines processed
        """
        if not self.log_path.exists():
            return 0
        
        line_count = 0
        try:
            # Use Windows file sharing to prevent blocking game
            if sys.platform == 'win32':
                try:
                    import win32file
                    import msvcrt
                    # Open with FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE
                    handle = win32file.CreateFile(
                        str(self.log_path),
                        win32file.GENERIC_READ,
                        win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE | win32file.FILE_SHARE_DELETE,
                        None,
                        win32file.OPEN_EXISTING,
                        0,
                        None
                    )
                    fd = msvcrt.open_osfhandle(handle.Detach(), os.O_RDONLY)
                    f = os.fdopen(fd, 'r', encoding='utf-8', errors='ignore', buffering=65536)
                except ImportError:
                    import msvcrt
                    fd = os.open(str(self.log_path), os.O_RDONLY | os.O_BINARY, 0)
                    f = os.fdopen(fd, 'r', encoding='utf-8', errors='ignore', buffering=65536)
            else:
                f = open(self.log_path, 'r', encoding='utf-8', errors='ignore', buffering=65536)
            
            try:
                for line in f:
                    if line.strip():
                        self.line_callback(line.rstrip('\n'))
                        line_count += 1
            finally:
                f.close()
        except Exception as e:
            print(f"Error replaying log file: {e}")
        
        return line_count
    
    def tail_existing_content(self, num_lines: int = 100) -> None:
        """
        Read the last N lines from the existing log file.
        
        Args:
            num_lines: Number of lines to read from the end
        """
        if not self.log_path.exists():
            return
        
        try:
            # Use Windows file sharing to prevent blocking game
            if sys.platform == 'win32':
                try:
                    import win32file
                    import msvcrt
                    # Open with FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE
                    handle = win32file.CreateFile(
                        str(self.log_path),
                        win32file.GENERIC_READ,
                        win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE | win32file.FILE_SHARE_DELETE,
                        None,
                        win32file.OPEN_EXISTING,
                        0,
                        None
                    )
                    fd = msvcrt.open_osfhandle(handle.Detach(), os.O_RDONLY)
                    f = os.fdopen(fd, 'r', encoding='utf-8', errors='ignore', buffering=65536)
                except ImportError:
                    import msvcrt
                    fd = os.open(str(self.log_path), os.O_RDONLY | os.O_BINARY, 0)
                    f = os.fdopen(fd, 'r', encoding='utf-8', errors='ignore', buffering=65536)
            else:
                f = open(self.log_path, 'r', encoding='utf-8', errors='ignore', buffering=65536)
            
            try:
                # Read all lines and get the last N
                lines = f.readlines()
                tail_lines = lines[-num_lines:] if len(lines) > num_lines else lines
                
                for line in tail_lines:
                    if line.strip():
                        self.line_callback(line.rstrip('\n'))
            finally:
                f.close()
        except Exception as e:
            print(f"Error tailing log file: {e}")
    
    def start(self, tail_lines: int = 100, replay_all: bool = True) -> bool:
        """
        Start monitoring the log file with aggressive polling.
        
        Args:
            tail_lines: Number of existing lines to read on start (if replay_all=False)
            replay_all: If True, replay entire log from beginning (default)
            
        Returns:
            True if started successfully, False otherwise
        """
        if self._running:
            return True
        
        if not self.log_path.exists():
            print(f"[ERROR] Log file not found: {self.log_path}")
            return False
        
        self.start_time = time.time()
        
        # Read existing content - either entire file or just tail
        if replay_all:
            print(f"[INFO] Replaying entire log file from game boot...")
            line_count = self.replay_entire_log()
            print(f"[INFO] Processed {line_count} existing log lines")
            # Signal end of replay
            self.line_callback("__REPLAY_COMPLETE__")
        elif tail_lines > 0:
            self.tail_existing_content(tail_lines)
            self.line_callback("__REPLAY_COMPLETE__")
        
        # Set up poller
        self.poller = LogFilePoller(str(self.log_path), self.line_callback, self)
        self._running = True
        
        # Start polling thread
        self._polling_thread = threading.Thread(target=self._polling_worker, daemon=True)
        self._polling_thread.start()
        
        print(f"[OK] Log monitor started (polling mode)")
        print(f"[OK] Monitoring: {self.log_path}")
        print(f"[OK] Poll interval: {self.poll_interval}s")
        _debug_log(f"Log monitor started with {self.poll_interval}s poll interval")
        
        return True
    
    def _polling_worker(self):
        """Background polling thread that checks for file changes at configured interval."""
        _debug_log(f"Polling thread started (checking every {self.poll_interval}s)")
        print(f"[INFO] Polling thread started (checking every {self.poll_interval}s)")
        
        while self._running:
            try:
                _debug_log(f"--- Poll cycle starting (interval={self.poll_interval}s) ---")
                if self.poller:
                    self.poller.check_for_changes()
                else:
                    _debug_log("WARNING: Poller is None!")
                _debug_log(f"--- Poll cycle complete, sleeping {self.poll_interval}s ---")
                time.sleep(self.poll_interval)
            except Exception as e:
                error_msg = f"ERROR in polling worker: {type(e).__name__}: {e}"
                error_trace = traceback.format_exc()
                _debug_log(error_msg)
                _debug_log(f"Full traceback:\n{error_trace}")
                print(f"[ERROR] Polling worker: {e}")
                print(f"[ERROR] See starlogs_debug.log for full details")
                time.sleep(self.poll_interval)  # Back off on error
        
        _debug_log("Polling thread exiting")
    
    def stop(self) -> None:
        """Stop monitoring the log file."""
        if self._running:
            self._running = False
            if self._polling_thread:
                self._polling_thread.join(timeout=1.0)
    
    def is_running(self) -> bool:
        """Check if monitor is currently running."""
        return self._running
    
    def get_diagnostics(self) -> dict:
        """
        Get monitoring diagnostics for troubleshooting.
        
        Returns:
            Dict with monitoring stats
        """
        runtime = time.time() - self.start_time if self.start_time else 0
        return {
            'running': self._running,
            'log_path': str(self.log_path),
            'log_exists': self.log_path.exists(),
            'runtime_seconds': round(runtime, 1),
            'poll_checks': self.check_count,
            'checks_per_second': round(self.check_count / runtime, 2) if runtime > 0 else 0,
            'lines_read': self.lines_read,
            'bytes_read': self.bytes_read,
            'current_position': self.poller.last_position if self.poller else 0,
            'file_size': self.log_path.stat().st_size if self.log_path.exists() else 0
        }
    
    def trigger_reprocess(self) -> int:
        """Trigger a reprocess of the entire log file."""
        line_count = self.replay_entire_log()
        # Send separator signal after reprocess
        self.line_callback("__REPLAY_COMPLETE__")
        return line_count

