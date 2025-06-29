"""
Infortic Scraper Package

A scalable web scraping framework that provides:
- Base scraper class with context manager support
- Singleton logger for centralized logging  
- Database client for data persistence
- Standardized interfaces for easy extension

To add a new scraper, simply subclass BaseScraper and implement the scrape() method.
"""

from .core.base_scraper import BaseScraper
from .core.logger import Logger
from .core.db import DBClient

__version__ = "1.0.0"
__all__ = ["BaseScraper", "Logger", "DBClient"]
