"""
Logging configuration for the Gemini-O1 application.

This module provides structured logging with request ID tracking, 
colored console output, and file output with rotation.
"""

import logging
import logging.handlers
import os
import uuid
import json
import time
from datetime import datetime
from typing import Dict, Optional, Any, Union

# Try to import colorlog if available
try:
    import colorlog
    HAS_COLORLOG = True
except ImportError:
    HAS_COLORLOG = False

class StructuredLogFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def __init__(self, include_request_id: bool = True):
        """
        Initialize the formatter.
        
        Args:
            include_request_id: Whether to include request ID in logs
        """
        super().__init__()
        self.include_request_id = include_request_id
        
    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record as a JSON string.
        
        Args:
            record: The log record to format
            
        Returns:
            JSON-formatted log message
        """
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add request ID if available and enabled
        if self.include_request_id and hasattr(record, 'request_id'):
            log_data["request_id"] = record.request_id
            
        # Add exception info if available
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
            
        # Add custom fields if available
        if hasattr(record, 'data') and isinstance(record.data, dict):
            log_data.update(record.data)
            
        return json.dumps(log_data)

class LoggingConfig:
    """Configure logging for the application."""
    
    DEFAULT_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    REQUEST_FORMAT = '%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s: %(message)s'
    COLOR_FORMAT = '%(log_color)s%(asctime)s [%(levelname)s] %(name)s:%(reset)s %(message)s'
    COLOR_REQUEST_FORMAT = '%(log_color)s%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s:%(reset)s %(message)s'
    
    def __init__(self):
        """Initialize logging configuration."""
        self.request_id = None
        self.loggers = {}
        self.structured_logging = False
        
    def setup_logging(
        self,
        level: Optional[int] = None,
        log_file: Optional[str] = None,
        enable_console: bool = True,
        enable_request_tracking: Optional[bool] = None,
        enable_structured_logging: bool = False,
        max_log_size_mb: int = 10,
        backup_count: int = 5
    ) -> None:
        """
        Set up logging for the application.
        
        Args:
            level: Log level to use (defaults to config value)
            log_file: Path to log file (defaults to config value)
            enable_console: Whether to log to console
            enable_request_tracking: Whether to track request IDs (defaults to config value)
            enable_structured_logging: Whether to use JSON structured logging
            max_log_size_mb: Maximum log file size in MB before rotation
            backup_count: Number of backup logs to keep
        """
        # Get config values
        from .config import config
        
        # Use config values if not explicitly provided
        if level is None:
            level = config.get_log_level()
            
        if log_file is None:
            log_file = config.get("LOG_FILE", "app.log")
            
        if enable_request_tracking is None:
            enable_request_tracking = config.get("ENABLE_REQUEST_TRACKING", True)
            
        self.structured_logging = enable_structured_logging
        
        # Choose the appropriate format
        if enable_request_tracking:
            log_format = self.REQUEST_FORMAT
            color_format = self.COLOR_REQUEST_FORMAT
        else:
            log_format = self.DEFAULT_FORMAT
            color_format = self.COLOR_FORMAT
            
        # Create a directory for logs if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Set up handlers
        handlers = []
        
        # File handler with rotation
        if enable_structured_logging:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_log_size_mb * 1024 * 1024,
                backupCount=backup_count
            )
            file_handler.setFormatter(StructuredLogFormatter(enable_request_tracking))
        else:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_log_size_mb * 1024 * 1024,
                backupCount=backup_count
            )
            file_handler.setFormatter(logging.Formatter(log_format))
            
        handlers.append(file_handler)
        
        # Console handler
        if enable_console:
            if HAS_COLORLOG:
                console_handler = colorlog.StreamHandler()
                console_handler.setFormatter(colorlog.ColoredFormatter(
                    color_format,
                    log_colors={
                        'DEBUG': 'cyan',
                        'INFO': 'green',
                        'WARNING': 'yellow',
                        'ERROR': 'red',
                        'CRITICAL': 'red,bg_white',
                    }
                ))
            else:
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(logging.Formatter(log_format))
                
            handlers.append(console_handler)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        
        # Remove existing handlers to avoid duplication
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            
        # Add our handlers
        for handler in handlers:
            root_logger.addHandler(handler)
            
        # Create a new request ID if tracking is enabled
        if enable_request_tracking:
            self.request_id = str(uuid.uuid4())
            
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger with the given name.
        
        Args:
            name: The logger name
            
        Returns:
            The configured logger
        """
        if name in self.loggers:
            return self.loggers[name]
            
        logger = logging.getLogger(name)
        
        # Add context filter for request ID if tracking is enabled
        if self.request_id:
            logger.addFilter(RequestContextFilter(self.request_id))
            
        self.loggers[name] = logger
        return logger
        
    def set_request_id(self, request_id: Optional[str] = None) -> None:
        """
        Set the request ID for the current context.
        
        Args:
            request_id: The request ID to use, or None to generate a new one
        """
        self.request_id = request_id or str(uuid.uuid4())
        
        # Update existing loggers
        for logger in self.loggers.values():
            # Remove existing RequestContextFilters
            for filter in logger.filters[:]:
                if isinstance(filter, RequestContextFilter):
                    logger.removeFilter(filter)
            
            # Add new RequestContextFilter
            logger.addFilter(RequestContextFilter(self.request_id))
            
    def log_with_data(self, logger: logging.Logger, level: int, msg: str, data: Dict[str, Any]) -> None:
        """
        Log a message with additional data fields.
        
        Args:
            logger: The logger to use
            level: The log level
            msg: The log message
            data: Additional data to include in the log
        """
        # Create a log record with the extra data
        record = logging.LogRecord(
            name=logger.name,
            level=level,
            pathname="",
            lineno=0,
            msg=msg,
            args=(),
            exc_info=None
        )
        record.data = data
        
        # Log the record
        logger.handle(record)


class RequestContextFilter(logging.Filter):
    """Filter that adds request ID to log records."""
    
    def __init__(self, request_id: str):
        """
        Initialize the filter with a request ID.
        
        Args:
            request_id: The request ID to add to log records
        """
        super().__init__()
        self.request_id = request_id
        
    def filter(self, record):
        """Add request_id field to the log record."""
        record.request_id = self.request_id
        return True


class PerformanceTracker:
    """Utility to track and log performance metrics."""
    
    def __init__(self, logger: logging.Logger, operation_name: str):
        """
        Initialize the performance tracker.
        
        Args:
            logger: The logger to use
            operation_name: Name of the operation being tracked
        """
        self.logger = logger
        self.operation_name = operation_name
        self.start_time = None
        self.checkpoints = {}
        
    def start(self) -> None:
        """Start timing the operation."""
        self.start_time = time.time()
        
    def checkpoint(self, name: str) -> float:
        """
        Record a checkpoint in the operation.
        
        Args:
            name: Name of the checkpoint
            
        Returns:
            Time since the start in seconds
        """
        if not self.start_time:
            self.start()
            
        current_time = time.time()
        elapsed = current_time - self.start_time
        self.checkpoints[name] = elapsed
        return elapsed
        
    def stop(self, log_level: int = logging.DEBUG) -> Dict[str, float]:
        """
        Stop timing and log the results.
        
        Args:
            log_level: Log level to use
            
        Returns:
            Dictionary with timing information
        """
        if not self.start_time:
            return {}
            
        total_time = time.time() - self.start_time
        
        timing_data = {
            "operation": self.operation_name,
            "total_seconds": round(total_time, 4)
        }
        
        if self.checkpoints:
            timing_data["checkpoints"] = {k: round(v, 4) for k, v in self.checkpoints.items()}
            
        self.logger.log(
            log_level, 
            f"Performance: {self.operation_name} completed in {total_time:.4f}s", 
            extra={"data": timing_data}
        )
        
        return timing_data


# Global logging configuration instance
logging_config = LoggingConfig()