import asyncio
from playwright.async_api import async_playwright
import threading


class BaseWebScraper:
    def __init__(self, headless: bool = True, timeout: int = 30000):
        """
        Initialize the base scraper with Playwright.

        Args:
            headless: Whether to run the browser in headless mode
            timeout: Default timeout for web operations in milliseconds
        """
        self.headless = headless
        self.timeout = timeout
        self.browser = None
        self.lock = threading.Lock()
        self.playwright_context = None

    async def _start_browser(self):
        """Start the Playwright browser."""
        async with async_playwright() as p:
            browser_type = p.chromium
            self.browser = await browser_type.launch(headless=self.headless)
            self.browser_context = await self.browser.new_context()

    async def get_page(self, url: str):
        """
        Navigate to a page and get the page content.

        Args:
            url: URL to navigate to

        Returns:
            Page object

        Raises:
            Exception: If page load fails
        """
        async with self.lock:
            if not self.browser:
                await self._start_browser()

            page = await self.browser_context.new_page()
            await page.goto(url, timeout=self.timeout)
            return page

    async def save_debug_page(self, page, path: str):
        """
        Save the current state of the page for debugging purposes.

        Args:
            page: Page object
            path: File path to save the page content
        """
        await page.screenshot(path=path)

    async def close(self):
        """Close the Playwright browser and clean up resources."""
        async with self.lock:
            if self.browser:
                await self.browser.close()
                self.browser = None

"""
Base scraper interface that provides a standardized way to create scrapers.
All scrapers should inherit from this class and implement the required methods.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import asyncio
import aiohttp
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .logger import Logger
from .db import SupabaseDBClient


class BaseScraper(ABC):
    """
    Abstract base class for all scrapers.
    
    Provides context manager functionality and common scraping methods.
    Subclasses only need to implement the scrape() method.
    """
    
    def __init__(self, db_client: SupabaseDBClient, headless: bool = True, timeout: int = 30):
        """
        Initialize the base scraper.
        
        Args:
            db_client: An initialized SupabaseDBClient instance
            headless: Whether to run browser in headless mode
            timeout: Default timeout for web operations
        """
        self.headless = headless
        self.timeout = timeout
        self.driver: Optional[webdriver.Chrome] = None
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = Logger()
        self.db_client = db_client
        
    def __enter__(self):
        """Context manager entry - initialize browser driver."""
        self._setup_driver()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        self._cleanup()
        
    async def __aenter__(self):
        """Async context manager entry - initialize HTTP session."""
        await self._setup_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup resources."""
        await self._cleanup_async()
    
    def _setup_driver(self):
        """Setup Chrome WebDriver with optimal configurations."""
        try:
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument("--headless")
            
            # Performance optimizations
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-images")
            chrome_options.add_argument("--disable-javascript")  # Can be overridden if JS needed
            
            # User agent to avoid detection
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(self.timeout)
            
            self.logger.info(f"Chrome driver initialized for {self.__class__.__name__}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Chrome driver: {str(e)}")
            raise
    
    async def _setup_session(self):
        """Setup aiohttp session for static page fetching."""
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers
            )
            
            self.logger.info(f"HTTP session initialized for {self.__class__.__name__}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize HTTP session: {str(e)}")
            raise
    
    def _cleanup(self):
        """Cleanup browser driver."""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("Chrome driver closed")
            except Exception as e:
                self.logger.error(f"Error closing Chrome driver: {str(e)}")
    
    async def _cleanup_async(self):
        """Cleanup HTTP session."""
        if self.session:
            try:
                await self.session.close()
                self.logger.info("HTTP session closed")
            except Exception as e:
                self.logger.error(f"Error closing HTTP session: {str(e)}")
    
    def get_page(self, url: str, wait_for_element: Optional[str] = None, 
                 wait_timeout: Optional[int] = None) -> webdriver.Chrome:
        """
        Navigate to a page and optionally wait for specific element.
        
        Args:
            url: URL to navigate to
            wait_for_element: CSS selector to wait for (optional)
            wait_timeout: Custom timeout for waiting (optional)
            
        Returns:
            WebDriver instance for further operations
            
        Raises:
            Exception: If page load fails or element not found
        """
        if not self.driver:
            raise RuntimeError("Driver not initialized. Use within context manager.")
        
        try:
            self.logger.info(f"Navigating to: {url}")
            self.driver.get(url)
            
            if wait_for_element:
                timeout = wait_timeout or self.timeout
                wait = WebDriverWait(self.driver, timeout)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_element)))
                self.logger.info(f"Element found: {wait_for_element}")
            
            return self.driver
            
        except Exception as e:
            self.logger.error(f"Failed to load page {url}: {str(e)}")
            raise
    
    async def fetch_static_page(self, url: str) -> str:
        """
        Fetch static HTML content using HTTP request.
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content as string
            
        Raises:
            Exception: If request fails
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use within async context manager.")
        
        try:
            self.logger.info(f"Fetching static page: {url}")
            
            async with self.session.get(url) as response:
                response.raise_for_status()
                content = await response.text()
                
                self.logger.info(f"Successfully fetched {len(content)} characters from {url}")
                return content
                
        except Exception as e:
            self.logger.error(f"Failed to fetch static page {url}: {str(e)}")
            raise
    
    @abstractmethod
    def scrape(self) -> Dict[str, Any]:
        """
        Main scraping method that must be implemented by subclasses.
        
        Returns:
            Dictionary containing scraped data
        """
        pass
    
    def save_data(self, data: list, table_name: str):
        """
        Save scraped data to database.
        
        Args:
            data: List of dictionaries containing data to save
            table_name: Name of the database table
        """
        try:
            self.db.insert_many(data, table_name)
            self.logger.info(f"Saved {len(data)} records to {table_name}")
        except Exception as e:
            self.logger.error(f"Failed to save data to {table_name}: {str(e)}")
            raise
