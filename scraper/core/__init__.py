"""
Core modules for the Infortic scraper framework.

Contains the base interfaces that all scrapers should use:
- BaseScraper: Abstract base class for all scrapers
- Logger: Singleton logger for centralized logging
- DBClient: Database client for data persistence
"""

from .base_scraper import BaseScraper
from .logger import Logger
from .db import DBClient

__all__ = ["BaseScraper", "Logger", "DBClient"]
