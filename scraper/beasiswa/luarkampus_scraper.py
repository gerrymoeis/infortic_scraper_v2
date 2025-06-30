# scraper/beasiswa/luarkampus_scraper.py

from ..core.base_scraper import BaseScraper
from typing import Dict, List, Any, Optional
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from datetime import datetime
import re
import os
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class LuarKampusBeasiswaScraper(BaseScraper):
    """
    Scraper for Beasiswa (Scholarship) data from luarkampus.id.
    
    This scraper is designed to be lightweight and does not require a browser,
    as the target page content is static. It also uses Google Custom Search API
    to find additional details like image and registration URLs.
    """

    BASE_URL: str = "https://luarkampus.id/beasiswa"

    def __init__(self, db_client, headless: bool = True, timeout: int = 30):
        super().__init__(db_client, headless, timeout)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.logger.info("LuarKampusBeasiswaScraper initialized.")
        
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.google_cse_id = os.getenv("GOOGLE_CSE_ID")
        
        if not self.google_api_key or not self.google_cse_id:
            self.logger.warning("Google API Key or CSE ID not found in .env. Search functionality will be disabled.")
            self.search_service = None
        else:
            try:
                self.search_service = build("customsearch", "v1", developerKey=self.google_api_key)
                self.logger.info("Google Custom Search service initialized.")
            except Exception as e:
                self.logger.error(f"Failed to initialize Google Custom Search service: {e}")
                self.search_service = None

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

    def _get_google_search_results(self, title: str) -> (Optional[str], Optional[str]):
        """
        Uses Google Custom Search to find an image URL and a registration URL.
        """
        self.logger.info(f"Searching for image and registration URL for: {title}")
        
        # Search for a relevant image
        image_query = f'"{title}" logo OR icon'
        image_url = self._search_google(image_query, searchType='image')
        
        # Search for the official registration page
        registration_query = f'"{title}" pendaftaran OR registrasi site:.ac.id OR site:.edu OR site:.org'
        registration_url = self._search_google(registration_query)
        
        return image_url, registration_url

    def _search_google(self, query: str, **kwargs) -> Optional[str]:
        """
        Performs a Google search and returns the first result URL.
        """
        if not self.search_service:
            self.logger.warning("Google search skipped: service not initialized.")
            return None
        
        try:
            self.logger.info(f"Searching Google for: '{query}'")
            request_params = {
                'q': query,
                'cx': self.google_cse_id,
                'num': 1,
                **kwargs
            }
            
            result = self.search_service.cse().list(**request_params).execute()
            
            items = result.get('items')
            if items:
                url = items[0].get('link')
                self.logger.info(f"Found URL: {url}")
                return url
            else:
                self.logger.warning(f"No results found for query: '{query}'")
                return None
        except Exception as e:
            self.logger.error(f"An error occurred during Google search for '{query}': {e}")
            return None

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

            # The scholarship cards are <a> tags with a `wire:id` attribute,
            # which is specific to the Livewire framework used by the site.
            scholarship_cards = soup.select(r'a.block[wire\:id]')
            self.logger.info(f"Found {len(scholarship_cards)} scholarship cards.")

            for card in scholarship_cards:
                try:
                    # Verify it's a valid scholarship link before proceeding
                    href = card.get('href', '')
                    if not href or not re.search(r'/beasiswa/\d+', href):
                        continue

                    source_url = urljoin(self.BASE_URL, href)
                    
                    title_element = card.find('h2', class_='font-bold')
                    title = title_element.text.strip() if title_element else 'No Title Provided'

                    # Education levels are in green rounded spans
                    degree_elements = card.select('span.bg-success')
                    education_level = ', '.join(sorted([el.text.strip() for el in degree_elements])) or 'Not Specified'

                    # Location is in a gray span
                    location_element = card.select_one('span.text-sm.text-gray-600')
                    location = location_element.text.strip() if location_element else 'No Location Provided'

                    # Find deadline string from either mobile or desktop view for robustness
                    deadline_str = 'No Deadline Provided'
                    # Mobile view uses a span with class 'text-error'
                    deadline_mobile = card.select_one('span.text-error')
                    if deadline_mobile:
                        deadline_str = deadline_mobile.text.replace('Deadline:', '').strip()
                    else:
                        # Desktop view has a label and a value in separate spans
                        deadline_label = card.find(lambda tag: tag.name == 'span' and 'Deadline:' in tag.text.strip())
                        if deadline_label:
                            deadline_value = deadline_label.find_next_sibling('span')
                            if deadline_value:
                                deadline_str = deadline_value.text.strip()

                    deadline = self._parse_deadline(deadline_str)

                    # Fetch image and registration URL from Google Search
                    image_url, registration_url = self._get_google_search_results(title)
                    
                    scholarship_data = {
                        'title': title,
                        'education_level': education_level,
                        'location': location,
                        'deadline_date': deadline,
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
