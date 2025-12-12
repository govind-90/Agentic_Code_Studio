"""Custom log handler for real-time Streamlit display."""

import logging
import threading
from collections import deque
from datetime import datetime
from typing import Optional, List


class StreamlitLogHandler(logging.Handler):
    """
    Thread-safe log handler that captures logs for Streamlit display.
    Non-blocking and optimized for UI performance.
    """
    
    def __init__(self, max_logs: int = 200):
        """
        Initialize the handler.
        
        Args:
            max_logs: Maximum number of logs to keep in memory
        """
        super().__init__()
        self.logs = deque(maxlen=max_logs)
        self.lock = threading.RLock()  # Reentrant lock for safety
        self._enabled = True
    
    def emit(self, record: logging.LogRecord):
        """
        Emit a log record (non-blocking).
        
        Args:
            record: Log record to emit
        """
        if not self._enabled:
            return
            
        try:
            # Format message immediately
            message = self.format(record)
            
            # Quick lock to append
            with self.lock:
                self.logs.append({
                    'timestamp': datetime.fromtimestamp(record.created),
                    'level': record.levelname,
                    'message': message,
                    'name': record.name
                })
                
        except Exception:
            # Don't call handleError to avoid recursion
            pass
    
    def get_logs(self, n: Optional[int] = None) -> List[dict]:
        """
        Get the last n logs (non-blocking).
        
        Args:
            n: Number of logs to retrieve (None = all)
            
        Returns:
            List of log entries
        """
        try:
            with self.lock:
                if n is None:
                    return list(self.logs)
                return list(self.logs)[-n:] if len(self.logs) > 0 else []
        except Exception:
            return []
    
    def get_formatted_logs(self, n: Optional[int] = None) -> str:
        """
        Get formatted log messages as a single string (non-blocking).
        
        Args:
            n: Number of logs to retrieve (None = all)
            
        Returns:
            Formatted log string
        """
        try:
            logs = self.get_logs(n)
            if not logs:
                return ""
            return "\n".join(log['message'] for log in logs)
        except Exception:
            return ""
    
    def clear_logs(self):
        """Clear all stored logs."""
        try:
            with self.lock:
                self.logs.clear()
        except Exception:
            pass
    
    def get_log_count(self) -> int:
        """Get the current number of stored logs."""
        try:
            with self.lock:
                return len(self.logs)
        except Exception:
            return 0


# Global instance
_handler: Optional[StreamlitLogHandler] = None
_handler_lock = threading.Lock()


def get_streamlit_log_handler() -> StreamlitLogHandler:
    """
    Get or create the global Streamlit log handler (thread-safe singleton).
    
    Returns:
        StreamlitLogHandler instance
    """
    global _handler
    
    with _handler_lock:
        if _handler is None:
            _handler = StreamlitLogHandler()
            
            # Set formatter
            formatter = logging.Formatter(
                "%(asctime)s | %(name)-20s | %(levelname)-8s | %(message)s",
                datefmt="%H:%M:%S"
            )
            _handler.setFormatter(formatter)
        
        return _handler


def attach_to_logger(logger: logging.Logger) -> bool:
    """
    Attach the Streamlit log handler to a logger.
    
    Args:
        logger: Logger to attach to
        
    Returns:
        True if attached, False if already attached
    """
    try:
        handler = get_streamlit_log_handler()
        
        # Check if already attached
        if handler not in logger.handlers:
            logger.addHandler(handler)
            return True
        return False
    except Exception:
        return False
