# infolomba_scraper.py

from ..core.base_scraper import BaseScraper
from typing import Dict, List, Any, Optional
import time
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from datetime import datetime, date
import re

class InfoLombaScraper(BaseScraper):
    """
    Scraper for InfoLomba competition data.
    
    Scrapes competition data from infolomba.id and returns data
    matching the lomba database table schema.
    """

    BASE_URL: str = "https://www.infolomba.id/"
    LOAD_MORE_CLICKS: int = 15
    EVENT_LIST_CONTAINER_SELECTOR: str = 'div.event-list'
    EVENT_LINK_SELECTOR: str = 'h4.event-title a'

    def __init__(self, db_client, headless: bool = True, timeout: int = 30):
        super().__init__(db_client, headless, timeout)

    def scrape(self) -> List[Dict[str, Any]]:
        """
        Main scraping method.
        
        Returns:
            List[Dict[str, Any]]: List of competition data matching lomba table schema
        """
        self.logger.info(f"Starting scrape for {self.__class__.__name__}")

        with self as scraper:
            page = scraper.get_page(self.BASE_URL)
            
            # Wait for the main content to load
            time.sleep(3)

            # Click the 'Load more' button multiple times to get more events
            for i in range(self.LOAD_MORE_CLICKS):
                try:
                    load_more_button = page.find_element(By.CSS_SELECTOR, '#btnLoadMore')
                    if load_more_button.is_displayed():
                        self.logger.info(f"Clicking 'Load more events' button {i + 1}/{self.LOAD_MORE_CLICKS}")
                        page.execute_script("arguments[0].click();", load_more_button)
                        time.sleep(2)
                    else:
                        self.logger.info("'Load more events' button not visible, stopping.")
                        break
                except NoSuchElementException:
                    self.logger.info("'Load more events' button not found, stopping.")
                    break
                except Exception as e:
                    self.logger.warning(f"Failed to click 'Load more events' button: {e}")
                    break

            # Get the page content and parse with BeautifulSoup
            html_content = page.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            event_list_container = soup.select_one(self.EVENT_LIST_CONTAINER_SELECTOR)
            
            if not event_list_container:
                self.logger.warning("Event list container not found")
                return []
                
            event_links = event_list_container.select(self.EVENT_LINK_SELECTOR)
            self.logger.info(f"Found {len(event_links)} events.")
            
            scraped_events = []

            for link_element in event_links:
                try:
                    event_div = link_element.find_parent('h4').parent

                    # Extract raw text details from the main page
                    date_element = event_div.find('div', class_='tanggal')
                    price_element = event_div.find('div', class_='biaya')
                    
                    date_text = date_element.text.strip() if date_element else 'Tidak ada tanggal'
                    price_text = price_element.text.strip() if price_element else 'Gratis'

                    # Deep scrape details from individual event page
                    detail_url = urljoin(self.BASE_URL, link_element['href'])
                    detail_data = self._deep_scrape(detail_url)

                    if detail_data:
                        event_dict = {
                            'date_text': date_text,
                            'price_text': price_text,
                            'source_url': detail_url,
                            **detail_data
                        }
                        scraped_events.append(event_dict)
                        self.logger.info(f"Successfully scraped: {detail_data['title']}")
                    else:
                        self.logger.warning(f"Failed to scrape details for: {detail_url}")
                        
                except Exception as e:
                    self.logger.error(f"Error processing event link: {e}")
                    continue

            # Filter events to only include those with registration still open
            current_date = date.today()
            filtered_events = []
            
            for event in scraped_events:
                if self._is_registration_open(event['date_text'], current_date):
                    filtered_events.append(event)
                else:
                    self.logger.info(f"Filtered out expired event: {event.get('title', 'Unknown')} - Date: {event['date_text']}")
            
            self.logger.info(f"After filtering expired events: {len(filtered_events)}/{len(scraped_events)} events remain")
            
            # Final deduplication check (just to be extra safe)
            final_events = self._final_deduplication(filtered_events)

            return final_events

    def _final_deduplication(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Final deduplication check to ensure no duplicate registration URLs.
        """
        seen_registration_urls = set()
        deduplicated_events = []
        duplicates_removed = 0
        
        for event in events:
            registration_url = event.get('registration_url')
            if registration_url and registration_url in seen_registration_urls:
                duplicates_removed += 1
                self.logger.warning(f"Final dedup: Removing duplicate registration URL: {registration_url}")
                continue
            
            if registration_url:
                seen_registration_urls.add(registration_url)
            deduplicated_events.append(event)
        
        if duplicates_removed > 0:
            self.logger.info(f"Final deduplication removed {duplicates_removed} duplicate events")
        
        return deduplicated_events
    
    def _deep_scrape(self, detail_url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape detailed information from a single event page.
        
        Args:
            detail_url: URL of the event detail page
            
        Returns:
            Dictionary with event details or None if scraping fails
        """
        try:
            # Use requests for static page fetching
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(detail_url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            detail_container = soup.select_one('div.event-details-container')
            if not detail_container:
                self.logger.warning(f"Main detail container not found at {detail_url}")
                return None

            # Extract required fields
            title_element = detail_container.select_one('h4.event-title')
            description_element = detail_container.select_one('div.event-description-container')
            organizer_element = detail_container.select_one('div.penyelenggara div span:last-of-type')
            poster_link_element = detail_container.select_one('a.image-link')
            registration_element = detail_container.select_one('a.btn.btn-primary[target="_blank"]')
            participant_element = detail_container.select_one('div.target')
            location_element = detail_container.select_one('div.lokasi')

            # Validate and extract data
            title = title_element.text.strip() if title_element else None
            description = description_element.get_text(separator='\n', strip=True) if description_element else None
            organizer = organizer_element.text.strip() if organizer_element else None
            poster_url = urljoin(self.BASE_URL, poster_link_element['href']) if poster_link_element and poster_link_element.get('href') else None
            registration_url = registration_element['href'] if registration_element and registration_element.get('href') else None
            participant = participant_element.text.strip().replace('\n', ' ').strip() if participant_element else None
            location = location_element.text.strip().replace('\n', ' ').strip() if location_element else None

            # Check all required fields are present and non-empty
            if not all([title, description, organizer, poster_url, registration_url, participant, location]):
                missing_fields = []
                if not title: missing_fields.append('title')
                if not description: missing_fields.append('description')
                if not organizer: missing_fields.append('organizer')
                if not poster_url: missing_fields.append('poster_url')
                if not registration_url: missing_fields.append('registration_url')
                if not participant: missing_fields.append('participant')
                if not location: missing_fields.append('location')
                
                self.logger.warning(f"Skipping {detail_url} - missing fields: {', '.join(missing_fields)}")
                return None

            return {
                'title': title,
                'description': description,
                'organizer': organizer,
                'poster_url': poster_url,
                'registration_url': registration_url,
                'participant': participant,
                'location': location
            }

        except Exception as e:
            self.logger.error(f"Failed to parse details from {detail_url}: {e}")
            return None

    def _is_registration_open(self, date_text: str, current_date: date) -> bool:
        """
        Check if event registration is still open based on date text.
        
        Args:
            date_text: Raw date text from the event page
            current_date: Current date to compare against
            
        Returns:
            bool: True if registration is still open, False otherwise
        """
        try:
            # Common date patterns found in infolomba.id
            # Examples: "15 Desember 2024", "31 Jan 2025", "Deadline: 20 Maret 2025"
            
            # Indonesian month mapping
            indonesian_months = {
                'januari': 1, 'jan': 1,
                'februari': 2, 'feb': 2,
                'maret': 3, 'mar': 3,
                'april': 4, 'apr': 4,
                'mei': 5,
                'juni': 6, 'jun': 6,
                'juli': 7, 'jul': 7,
                'agustus': 8, 'agu': 8,
                'september': 9, 'sep': 9,
                'oktober': 10, 'okt': 10,
                'november': 11, 'nov': 11,
                'desember': 12, 'des': 12
            }
            
            # Clean and normalize the date text
            date_text_clean = date_text.lower().strip()
            
            # Remove common prefixes
            date_text_clean = re.sub(r'^(deadline|batas|tutup|sampai|hingga)\s*:?\s*', '', date_text_clean)
            
            # Pattern for date format: DD Month YYYY
            date_pattern = r'(\d{1,2})\s+(\w+)\s+(\d{4})'
            match = re.search(date_pattern, date_text_clean)
            
            if match:
                day = int(match.group(1))
                month_name = match.group(2).lower()
                year = int(match.group(3))
                
                # Get month number from Indonesian month name
                month = indonesian_months.get(month_name)
                if month:
                    event_date = date(year, month, day)
                    is_open = event_date >= current_date
                    
                    self.logger.debug(f"Parsed date: {event_date} (from '{date_text}'), Current: {current_date}, Open: {is_open}")
                    return is_open
            
            # If no date pattern matches, assume it's open (to be safe)
            self.logger.warning(f"Could not parse date: '{date_text}' - assuming registration is open")
            return True
            
        except Exception as e:
            self.logger.error(f"Error parsing date '{date_text}': {e} - assuming registration is open")
            return True
