# Author: Ozy
"""
Log file monitor for Star Citizen Game.log.
Watches for file changes and streams new content.
"""

import time
from pathlib import Path
from typing import Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
import threading


class LogFileHandler(FileSystemEventHandler):
    """Handles file system events for the Game.log file."""
    
    def __init__(self, log_path: str, callback: Callable[[str], None]):
        """
        Initialize handler.
        
        Args:
            log_path: Path to the log file to monitor
            callback: Function to call with new log lines
        """
        super().__init__()
        self.log_path = Path(log_path)
        self.callback = callback
        self.last_position = 0
        self._lock = threading.Lock()
        
        # Get initial file size
        if self.log_path.exists():
            self.last_position = self.log_path.stat().st_size
    
    def on_modified(self, event):
        """Called when the log file is modified."""
        if not isinstance(event, FileModifiedEvent):
            return
        
        if Path(event.src_path) == self.log_path:
            self._read_new_lines()
    
    def _read_new_lines(self):
        """Read new lines from the log file."""
        with self._lock:
            try:
                if not self.log_path.exists():
                    return
                
                current_size = self.log_path.stat().st_size
                
                # Handle log rotation (file got smaller)
                if current_size < self.last_position:
                    self.last_position = 0
                
                if current_size > self.last_position:
                    with open(self.log_path, 'r', encoding='utf-8', errors='ignore') as f:
                        f.seek(self.last_position)
                        new_lines = f.read()
                        self.last_position = f.tell()
                        
                        # Process each line
                        for line in new_lines.splitlines():
                            if line.strip():
                                self.callback(line)
            except Exception as e:
                print(f"Error reading log file: {e}")


class LogMonitor:
    """Monitors a Star Citizen log file for changes."""
    
    def __init__(self, log_path: str, line_callback: Callable[[str], None]):
        """
        Initialize log monitor.
        
        Args:
            log_path: Path to the Game.log file
            line_callback: Function to call with each new log line
        """
        self.log_path = Path(log_path)
        self.line_callback = line_callback
        self.observer = None
        self.handler = None
        self._running = False
    
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
            with open(self.log_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if line.strip():
                        self.line_callback(line.rstrip('\n'))
                        line_count += 1
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
            with open(self.log_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Read all lines and get the last N
                lines = f.readlines()
                tail_lines = lines[-num_lines:] if len(lines) > num_lines else lines
                
                for line in tail_lines:
                    if line.strip():
                        self.line_callback(line.rstrip('\n'))
        except Exception as e:
            print(f"Error tailing log file: {e}")
    
    def start(self, tail_lines: int = 100, replay_all: bool = True) -> bool:
        """
        Start monitoring the log file.
        
        Args:
            tail_lines: Number of existing lines to read on start (if replay_all=False)
            replay_all: If True, replay entire log from beginning (default)
            
        Returns:
            True if started successfully, False otherwise
        """
        if self._running:
            return True
        
        if not self.log_path.exists():
            print(f"Error: Log file not found: {self.log_path}")
            return False
        
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
        
        # Set up file watcher
        self.handler = LogFileHandler(str(self.log_path), self.line_callback)
        self.observer = Observer()
        self.observer.schedule(
            self.handler,
            str(self.log_path.parent),
            recursive=False
        )
        
        self.observer.start()
        self._running = True
        return True
    
    def stop(self) -> None:
        """Stop monitoring the log file."""
        if self._running and self.observer:
            self.observer.stop()
            self.observer.join(timeout=2.0)
            self._running = False
    
    def is_running(self) -> bool:
        """Check if monitor is currently running."""
        return self._running
    
    def trigger_reprocess(self) -> int:
        """Trigger a reprocess of the entire log file."""
        line_count = self.replay_entire_log()
        # Send separator signal after reprocess
        self.line_callback("__REPLAY_COMPLETE__")
        return line_count

