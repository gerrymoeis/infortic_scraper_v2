# scraper/beasiswa/luarkampus_scraper.py

from ..core.base_scraper import BaseScraper
from typing import Dict, List, Any, Optional
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from datetime import datetime
import re
import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class LuarKampusBeasiswaScraper(BaseScraper):
    """
    Scraper for Beasiswa (Scholarship) data from luarkampus.id.
    
    This scraper is designed to be lightweight and does not require a browser,
    as the target page content is static. It uses Playwright to find additional details like image and registration URLs.
    """

    BASE_URL: str = "https://luarkampus.id/beasiswa"

    def __init__(self, db_client, headless: bool = True, timeout: int = 30):
        super().__init__(db_client, headless, timeout)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.logger.info("LuarKampusBeasiswaScraper initialized.")

    def _parse_deadline(self, deadline_text: str) -> Optional[str]:
        """
        Parses a deadline string (e.g., 'Deadline: 01 Agt 2025') into an ISO 8601 date string.
        """
        indonesian_months = {
            'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'mei': '05', 'jun': '06',
            'jul': '07', 'agt': '08', 'sep': '09', 'okt': '10', 'nov': '11', 'des': '12'
        }
        try:
            clean_text = deadline_text.lower().replace('deadline:', '').strip()
            day, month_abbr, year = clean_text.split()
            month = indonesian_months.get(month_abbr)
            
            if month:
                dt = datetime(int(year), int(month), int(day))
                return dt.strftime('%Y-%m-%d')
            
            self.logger.warning(f"Could not map month abbreviation: '{month_abbr}'")
            return None
        except Exception as e:
            self.logger.error(f"Could not parse deadline: '{deadline_text}'. Error: {e}")
            return None

    def _get_urls_with_playwright(self, title: str) -> (Optional[str], Optional[str]):
        """
        Uses Playwright to perform Google searches for the image and registration URL,
        mimicking a manual search process.
        """
        image_url = None
        registration_url = None
        query = f'"{title}" registration link'

        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()

                # --- Registration Link Search ---
                self.logger.info(f"Searching for registration link: {query}")
                page.goto(f"https://www.google.com/search?q={query}", timeout=60000)
                # Wait for the first search result link to appear
                first_result_selector = 'div.g a[jsname="UWckNb"]'
                page.wait_for_selector(first_result_selector, timeout=15000)
                registration_url = page.locator(first_result_selector).first.get_attribute('href')
                self.logger.info(f"Found registration link: {registration_url}")

                # --- Image Search ---
                self.logger.info(f"Searching for image: {query}")
                # Navigate to Google Images tab
                page.get_by_role("link", name="Images").click()
                page.wait_for_load_state('networkidle')
                
                # Click the first image thumbnail
                first_image_selector = 'div.H8Rx8c'
                page.wait_for_selector(first_image_selector, timeout=15000)
                page.locator(first_image_selector).first.click()

                # Wait for the preview pane and get the high-res image src
                preview_image_selector = 'img.sFlh5c.pT0Scc.iPVvYb'
                page.wait_for_selector(preview_image_selector, timeout=15000)
                image_url = page.locator(preview_image_selector).get_attribute('src')
                self.logger.info(f"Found image address: {image_url}")
                
                browser.close()
            except PlaywrightTimeoutError as e:
                self.logger.error(f"Playwright timed out for query '{query}': {e}")
                if 'browser' in locals() and browser.is_connected():
                    browser.close()
            except Exception as e:
                self.logger.error(f"An error occurred with Playwright for query '{query}': {e}")
                if 'browser' in locals() and browser.is_connected():
                    browser.close()

        return image_url, registration_url

    def scrape(self) -> List[Dict[str, Any]]:
        """
        Main scraping method for luarkampus.id scholarships.
        """
        self.logger.info(f"Starting scrape for {self.__class__.__name__} at {self.BASE_URL}")
        
        all_scholarships = []
        
        try:
            response = self.session.get(self.BASE_URL, timeout=60)
            response.raise_for_status() 
            
            soup = BeautifulSoup(response.content, 'html.parser')

            scholarship_cards = soup.select(r'a.block[wire\:id]')
            self.logger.info(f"Found {len(scholarship_cards)} scholarship cards.")

            for card in scholarship_cards:
                try:
                    href = card.get('href', '')
                    if not href or not re.search(r'/beasiswa/\d+', href):
                        continue

                    source_url = urljoin(self.BASE_URL, href)
                    title_element = card.find('h2', class_='font-bold')
                    title = title_element.text.strip() if title_element else 'No Title Provided'

                    deadline_str = 'No Deadline Provided'
                    deadline_mobile = card.select_one('span.text-error')
                    if deadline_mobile:
                        deadline_str = deadline_mobile.text.replace('Deadline:', '').strip()
                    else:
                        deadline_label = card.find(lambda tag: tag.name == 'span' and 'Deadline:' in tag.text.strip())
                        if deadline_label:
                            deadline_value = deadline_label.find_next_sibling('span')
                            if deadline_value:
                                deadline_str = deadline_value.text.strip()

                    deadline_date = self._parse_deadline(deadline_str)
                    if not deadline_date or datetime.strptime(deadline_date, '%Y-%m-%d').date() <= datetime.now().date():
                        self.logger.info(f"Skipping expired scholarship: '{title}' (Deadline: {deadline_date or 'N/A'})")
                        continue

                    degree_elements = card.select('span.bg-success')
                    education_level = ', '.join(sorted([el.text.strip() for el in degree_elements])) or 'Not Specified'

                    location_element = card.select_one('span.text-sm.text-gray-600')
                    location = location_element.text.strip() if location_element else 'No Location Provided'

                    image_url, registration_url = self._get_urls_with_playwright(title)

                    # Enforce non-null URLs to maintain data quality
                    if not image_url or not registration_url:
                        self.logger.warning(f"Skipping '{title}' due to missing image or registration URL.")
                        continue
                    
                    scholarship_data = {
                        'title': title,
                        'education_level': education_level,
                        'location': location,
                        'deadline_date': deadline_date,
                        'source_url': source_url,
                        'image_url': image_url,
                        'registration_url': registration_url
                    }
                    
                    all_scholarships.append(scholarship_data)
                    self.logger.info(f"Scraped scholarship: {title}")

                except Exception:
                    self.logger.error("Error processing a scholarship card", exc_info=True)
                    continue

        except requests.RequestException as e:
            self.logger.error(f"Failed to retrieve the main page: {e}")
        except Exception:
            self.logger.error("An unexpected error occurred during scraping", exc_info=True)
        
        self.logger.info(f"Scraping finished. Total scholarships scraped: {len(all_scholarships)}")
        return all_scholarships
