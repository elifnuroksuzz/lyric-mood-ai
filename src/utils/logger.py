"""
Advanced Logging System for LyricMood-AI Application

This module provides a comprehensive logging system with file rotation,
colored console output, and structured logging capabilities.
"""

import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import json

from ..core.constants import LoggingConstants, UIConstants
from ..core.config_manager import config


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to console output"""
    
    COLORS = UIConstants.COLORS
    
    LEVEL_COLORS = {
        'DEBUG': 'CYAN',
        'INFO': 'GREEN',
        'WARNING': 'YELLOW', 
        'ERROR': 'RED',
        'CRITICAL': 'MAGENTA'
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors if enabled"""
        formatted = super().format(record)
        
        if config.enable_color_output and record.levelname in self.LEVEL_COLORS:
            color = self.COLORS[self.LEVEL_COLORS[record.levelname]]
            reset = self.COLORS['END']
            formatted = f"{color}{formatted}{reset}"
        
        return formatted


class StructuredFormatter(logging.Formatter):
    """Formatter for structured JSON logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception information if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields from the record
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 
                          'pathname', 'filename', 'module', 'lineno', 'funcName',
                          'created', 'msecs', 'relativeCreated', 'thread', 
                          'threadName', 'processName', 'process', 'getMessage',
                          'exc_info', 'exc_text', 'stack_info']:
                log_data[key] = value
        
        return json.dumps(log_data, ensure_ascii=False)


class LyricMoodLogger:
    """Advanced logger class with multiple output handlers and configurations"""
    
    def __init__(self, name: str = "LyricMood-AI"):
        """
        Initialize the logger system.
        
        Args:
            name: Logger name
        """
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, config.log_level.upper()))
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self) -> None:
        """Setup all logging handlers"""
        # Console handler with colors
        self._setup_console_handler()
        
        # File handler with rotation
        if config.enable_detailed_logging:
            self._setup_file_handler()
            self._setup_error_file_handler()
    
    def _setup_console_handler(self) -> None:
        """Setup colored console output handler"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        formatter = ColoredFormatter(
            fmt=LoggingConstants.LOG_FORMAT,
            datefmt=LoggingConstants.DATE_FORMAT
        )
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(console_handler)
    
    def _setup_file_handler(self) -> None:
        """Setup rotating file handler for general logs"""
        # Ensure logs directory exists
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Create rotating file handler
        log_file = logs_dir / f"lyricmood_{datetime.now().strftime('%Y%m')}.log"
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=LoggingConstants.MAX_LOG_FILE_SIZE,
            backupCount=LoggingConstants.BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Use structured JSON formatter for files
        formatter = StructuredFormatter()
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
    
    def _setup_error_file_handler(self) -> None:
        """Setup separate handler for error logs only"""
        logs_dir = Path("logs")
        error_log_file = logs_dir / f"errors_{datetime.now().strftime('%Y%m')}.log"
        
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=LoggingConstants.MAX_LOG_FILE_SIZE,
            backupCount=LoggingConstants.BACKUP_COUNT,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        
        formatter = StructuredFormatter()
        error_handler.setFormatter(formatter)
        
        self.logger.addHandler(error_handler)
    
    def log_api_request(self, api_name: str, endpoint: str, method: str = "GET",
                       status_code: Optional[int] = None, 
                       response_time: Optional[float] = None,
                       **kwargs) -> None:
        """
        Log API request with structured data.
        
        Args:
            api_name: Name of the API (e.g., 'Genius', 'Groq')
            endpoint: API endpoint
            method: HTTP method
            status_code: Response status code
            response_time: Request duration in seconds
            **kwargs: Additional context data
        """
        self.logger.info(
            f"{api_name} API {method} {endpoint}",
            extra={
                'event_type': 'api_request',
                'api_name': api_name,
                'endpoint': endpoint,
                'method': method,
                'status_code': status_code,
                'response_time': response_time,
                **kwargs
            }
        )
    
    def log_analysis_start(self, song_name: str, artist_name: str,
                          lyrics_length: Optional[int] = None) -> None:
        """Log the start of emotion analysis"""
        self.logger.info(
            f"Starting emotion analysis for '{song_name}' by '{artist_name}'",
            extra={
                'event_type': 'analysis_start',
                'song_name': song_name,
                'artist_name': artist_name,
                'lyrics_length': lyrics_length
            }
        )
    
    def log_analysis_result(self, song_name: str, artist_name: str,
                           emotion_scores: Dict[str, float],
                           dominant_emotion: str,
                           confidence: float,
                           processing_time: Optional[float] = None) -> None:
        """Log emotion analysis results"""
        self.logger.info(
            f"Analysis completed for '{song_name}' - Dominant emotion: {dominant_emotion}",
            extra={
                'event_type': 'analysis_result',
                'song_name': song_name,
                'artist_name': artist_name,
                'emotion_scores': emotion_scores,
                'dominant_emotion': dominant_emotion,
                'confidence': confidence,
                'processing_time': processing_time
            }
        )
    
    def log_file_operation(self, operation: str, file_path: str,
                          success: bool = True, file_size: Optional[int] = None,
                          **kwargs) -> None:
        """Log file operations"""
        level = logging.INFO if success else logging.ERROR
        message = f"File {operation} {'successful' if success else 'failed'}: {file_path}"
        
        self.logger.log(
            level,
            message,
            extra={
                'event_type': 'file_operation',
                'operation': operation,
                'file_path': file_path,
                'success': success,
                'file_size': file_size,
                **kwargs
            }
        )
    
    def log_user_action(self, action: str, **kwargs) -> None:
        """Log user actions for analytics"""
        self.logger.info(
            f"User action: {action}",
            extra={
                'event_type': 'user_action',
                'action': action,
                **kwargs
            }
        )
    
    def log_performance_metric(self, metric_name: str, value: float,
                              unit: str = "seconds", **kwargs) -> None:
        """Log performance metrics"""
        self.logger.info(
            f"Performance metric - {metric_name}: {value} {unit}",
            extra={
                'event_type': 'performance_metric',
                'metric_name': metric_name,
                'value': value,
                'unit': unit,
                **kwargs
            }
        )
    
    def log_cache_operation(self, operation: str, cache_key: str,
                           hit: Optional[bool] = None, **kwargs) -> None:
        """Log cache operations"""
        message = f"Cache {operation}: {cache_key}"
        if hit is not None:
            message += f" ({'HIT' if hit else 'MISS'})"
        
        self.logger.debug(
            message,
            extra={
                'event_type': 'cache_operation',
                'operation': operation,
                'cache_key': cache_key,
                'hit': hit,
                **kwargs
            }
        )
    
    # Convenience methods for different log levels
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message"""
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message"""
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message"""
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, exc_info: bool = False, **kwargs) -> None:
        """Log error message"""
        self.logger.error(message, exc_info=exc_info, extra=kwargs)
    
    def critical(self, message: str, exc_info: bool = False, **kwargs) -> None:
        """Log critical message"""
        self.logger.critical(message, exc_info=exc_info, extra=kwargs)
    
    def exception(self, message: str, **kwargs) -> None:
        """Log exception with traceback"""
        self.logger.exception(message, extra=kwargs)


class PerformanceTimer:
    """Context manager for measuring and logging performance"""
    
    def __init__(self, logger: LyricMoodLogger, operation_name: str, **context):
        """
        Initialize performance timer.
        
        Args:
            logger: Logger instance
            operation_name: Name of the operation being timed
            **context: Additional context to log
        """
        self.logger = logger
        self.operation_name = operation_name
        self.context = context
        self.start_time = None
    
    def __enter__(self):
        """Start timing"""
        import time
        self.start_time = time.time()
        self.logger.debug(f"Starting operation: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing and log results"""
        import time
        if self.start_time:
            duration = time.time() - self.start_time
            
            if exc_type is None:
                self.logger.log_performance_metric(
                    self.operation_name,
                    duration,
                    "seconds",
                    **self.context
                )
            else:
                self.logger.error(
                    f"Operation failed: {self.operation_name}",
                    extra={
                        'operation': self.operation_name,
                        'duration': duration,
                        'exception_type': exc_type.__name__ if exc_type else None,
                        **self.context
                    }
                )


# Global logger instance
logger = LyricMoodLogger()


# Convenience functions for quick logging
def log_info(message: str, **kwargs) -> None:
    """Quick info logging"""
    logger.info(message, **kwargs)


def log_error(message: str, exc_info: bool = False, **kwargs) -> None:
    """Quick error logging"""
    logger.error(message, exc_info=exc_info, **kwargs)


def log_debug(message: str, **kwargs) -> None:
    """Quick debug logging"""
    logger.debug(message, **kwargs)


def performance_timer(operation_name: str, **context):
    """Create a performance timer context manager"""
    return PerformanceTimer(logger, operation_name, **context)