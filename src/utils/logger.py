"""Centralized logging configuration."""

import logging
import sys
from pathlib import Path
from typing import Optional

from src.config.settings import settings


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logger(
    name: str, log_file: Optional[str] = None, level: Optional[str] = None
) -> logging.Logger:
    """
    Set up a logger with console and file handlers.

    Args:
        name: Logger name (usually __name__)
        log_file: Optional specific log file path
        level: Optional log level override

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    log_level = getattr(logging, level or settings.log_level)
    logger.setLevel(log_level)

    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = ColoredFormatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler
    log_file_path = Path(log_file or settings.log_file)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
    file_handler.setLevel(log_level)
    file_formatter = logging.Formatter(
        "%(asctime)s | %(name)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger


# Create default loggers for each module
orchestrator_logger = setup_logger("orchestrator", "logs/orchestrator.log")
code_gen_logger = setup_logger("code_generator", "logs/code_generator.log")
build_logger = setup_logger("build_agent", "logs/build_agent.log")
test_logger = setup_logger("testing_agent", "logs/testing_agent.log")
ui_logger = setup_logger("ui", "logs/ui.log")


def attach_streamlit_handler():
    """Attach Streamlit log handler to all loggers for UI display."""
    try:
        from src.utils.streamlit_log_handler import attach_to_logger
        
        attach_to_logger(orchestrator_logger)
        attach_to_logger(code_gen_logger)
        attach_to_logger(build_logger)
        attach_to_logger(test_logger)
        attach_to_logger(ui_logger)
        
    except ImportError:
        pass  # Streamlit handler not available
