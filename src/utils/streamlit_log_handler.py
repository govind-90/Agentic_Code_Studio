"""Custom log handler for real-time Streamlit display."""

import logging
import threading
from collections import deque
from datetime import datetime
from typing import Optional


class StreamlitLogHandler(logging.Handler):
    """
    Thread-safe log handler that captures logs for Streamlit display.
    
    Stores logs in a deque with automatic size management.
    """
    
    def __init__(self, max_logs: int = 200):
        """
        Initialize the handler.
        
        Args:
            max_logs: Maximum number of logs to keep in memory
        """
        super().__init__()
        self.logs = deque(maxlen=max_logs)
        self.lock = threading.Lock()
        self._enabled = True
    
    def emit(self, record: logging.LogRecord):
        """
        Emit a log record.
        
        Args:
            record: Log record to emit
        """
        if not self._enabled:
            return
            
        try:
            log_entry = {
                'timestamp': datetime.fromtimestamp(record.created),
                'level': record.levelname,
                'message': self.format(record),
                'name': record.name,
                'raw': record
            }
            
            with self.lock:
                self.logs.append(log_entry)
                
        except Exception:
            self.handleError(record)
    
    def get_logs(self, n: Optional[int] = None) -> list:
        """
        Get the last n logs.
        
        Args:
            n: Number of logs to retrieve (None = all)
            
        Returns:
            List of log entries
        """
        with self.lock:
            if n is None:
                return list(self.logs)
            return list(self.logs)[-n:]
    
    def get_formatted_logs(self, n: Optional[int] = None) -> str:
        """
        Get formatted log messages as a single string.
        
        Args:
            n: Number of logs to retrieve (None = all)
            
        Returns:
            Formatted log string
        """
        logs = self.get_logs(n)
        return "\n".join(log['message'] for log in logs)
    
    def clear_logs(self):
        """Clear all stored logs."""
        with self.lock:
            self.logs.clear()
    
    def enable(self):
        """Enable log capture."""
        self._enabled = True
    
    def disable(self):
        """Disable log capture."""
        self._enabled = False
    
    def get_log_count(self) -> int:
        """Get the current number of stored logs."""
        with self.lock:
            return len(self.logs)


# Global instance for sharing across modules
streamlit_log_handler: Optional[StreamlitLogHandler] = None


def get_streamlit_log_handler() -> StreamlitLogHandler:
    """
    Get or create the global Streamlit log handler.
    
    Returns:
        StreamlitLogHandler instance
    """
    global streamlit_log_handler
    
    if streamlit_log_handler is None:
        streamlit_log_handler = StreamlitLogHandler()
        
        # Set formatter
        formatter = logging.Formatter(
            "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
            datefmt="%H:%M:%S"
        )
        streamlit_log_handler.setFormatter(formatter)
    
    return streamlit_log_handler


def attach_to_logger(logger: logging.Logger):
    """
    Attach the Streamlit log handler to a logger.
    
    Args:
        logger: Logger to attach to
    """
    handler = get_streamlit_log_handler()
    
    # Check if already attached
    if handler not in logger.handlers:
        logger.addHandler(handler)
