"""
Singleton logger implementation for centralized logging across all scrapers.
Provides structured logging with different levels and automatic log rotation.
"""

import logging
import logging.handlers
import os
from datetime import datetime
from typing import Optional
import threading


class Logger:
    """
    Singleton logger class that provides centralized logging functionality.
    
    Features:
    - Singleton pattern ensures one logger instance
    - Rotating file handler to manage log file sizes
    - Console and file logging
    - Structured log format with timestamps
    - Thread-safe implementation
    """
    
    _instance: Optional['Logger'] = None
    _lock = threading.Lock()
    _logger: Optional[logging.Logger] = None
    
    def __new__(cls):
        """Ensure only one instance of Logger exists (Singleton pattern)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(Logger, cls).__new__(cls)
                    cls._instance._initialize_logger()
        return cls._instance
    
    def _initialize_logger(self):
        """Initialize the logger with handlers and formatters."""
        if self._logger is not None:
            return
        
        # Create logger
        self._logger = logging.getLogger('infortic_scraper')
        self._logger.setLevel(logging.INFO)
        
        # Prevent duplicate handlers if logger already exists
        if self._logger.handlers:
            return
        
        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(os.getcwd(), 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        simple_formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # File handler with rotation (10MB max, keep 5 backup files)
        log_file = os.path.join(logs_dir, 'scraper.log')
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        
        # Add handlers to logger
        self._logger.addHandler(file_handler)
        self._logger.addHandler(console_handler)
        
        # Log initialization
        self._logger.info("Logger initialized successfully")
        self._logger.info(f"Log file location: {log_file}")
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        exc_info = kwargs.pop('exc_info', False)
        self._logger.debug(message, exc_info=exc_info, extra=kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        exc_info = kwargs.pop('exc_info', False)
        self._logger.info(message, exc_info=exc_info, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        exc_info = kwargs.pop('exc_info', False)
        self._logger.warning(message, exc_info=exc_info, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        exc_info = kwargs.pop('exc_info', True)
        self._logger.error(message, exc_info=exc_info, extra=kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        exc_info = kwargs.pop('exc_info', True)
        self._logger.critical(message, exc_info=exc_info, extra=kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log exception with traceback."""
        self._logger.exception(message, extra=kwargs)
    
    def log_scraper_start(self, scraper_name: str, url: str = None):
        """Log the start of a scraper operation."""
        msg = f"Starting scraper: {scraper_name}"
        if url:
            msg += f" | Target URL: {url}"
        self.info(msg)
    
    def log_scraper_end(self, scraper_name: str, items_count: int = 0, duration: float = 0):
        """Log the end of a scraper operation."""
        msg = f"Completed scraper: {scraper_name}"
        if items_count > 0:
            msg += f" | Items scraped: {items_count}"
        if duration > 0:
            msg += f" | Duration: {duration:.2f}s"
        self.info(msg)
    
    def log_scraper_error(self, scraper_name: str, error: Exception, url: str = None):
        """Log scraper-specific errors."""
        msg = f"Error in scraper: {scraper_name} | Error: {str(error)}"
        if url:
            msg += f" | URL: {url}"
        self.error(msg)
    
    def log_data_save(self, table_name: str, record_count: int):
        """Log successful data save operations."""
        self.info(f"Data saved to {table_name}: {record_count} records")
    
    def log_data_save_error(self, table_name: str, error: Exception):
        """Log data save errors."""
        self.error(f"Failed to save data to {table_name}: {str(error)}")
    
    def set_level(self, level: str):
        """
        Set logging level.
        
        Args:
            level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        """
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        if level.upper() in level_map:
            self._logger.setLevel(level_map[level.upper()])
            self.info(f"Logging level set to {level.upper()}")
        else:
            self.warning(f"Invalid logging level: {level}")
    
    def get_logger(self) -> logging.Logger:
        """Get the underlying logger instance for advanced usage."""
        return self._logger
