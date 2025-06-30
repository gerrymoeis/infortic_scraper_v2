# scraper/beasiswa/luarkampus_scraper.py

import os
import re
from typing import Optional
from datetime import datetime, date
from urllib.parse import urlparse, parse_qs, unquote
from typing import Any, Dict, List

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from playwright.sync_api import Page, sync_playwright, TimeoutError as PlaywrightTimeoutError, Browser

from ..core.base_scraper import BaseScraper

load_dotenv()

class LuarKampusBeasiswaScraper(BaseScraper):
    """
    Scraper for Beasiswa (Scholarship) data from luarkampus.id.
    This scraper logs into the site, scrapes detail pages for comprehensive data,
    and uses Yandex Image Search to find scholarship images.
    """
    BASE_URL = "https://luarkampus.id"
    LOGIN_URL = f"{BASE_URL}/login/email"
    BEASISWA_URL = f"{BASE_URL}/beasiswa"

    def __init__(self, db_client, headless: bool = True, timeout: int = 30):
        super().__init__(db_client, headless, timeout)
        self.logger.info("LuarKampusBeasiswaScraper initialized for authenticated scraping.")
        self.luar_kampus_gmail = os.getenv("LUAR_KAMPUS_GMAIL")
        self.luar_kampus_password = os.getenv("LUAR_KAMPUS_PASSWORD")
        if not self.luar_kampus_gmail or not self.luar_kampus_password:
            raise ValueError("LUAR_KAMPUS_GMAIL and LUAR_KAMPUS_PASSWORD must be set in .env file")

    def _login(self, page: Page):
        """Logs into luarkampus.id using credentials from .env file."""
        self.logger.info(f"Navigating to login page: {self.LOGIN_URL}")
        page.goto(self.LOGIN_URL, wait_until='domcontentloaded', timeout=60000)
        
        try:
            self.logger.info("Waiting for login form to be visible...")
            email_input_selector = 'input[name="email"]'
            page.wait_for_selector(email_input_selector, state='visible', timeout=30000)
            
            self.logger.info("Filling login credentials.")
            page.fill(email_input_selector, self.luar_kampus_gmail)
            page.fill('input[name="password"]', self.luar_kampus_password)
            
            self.logger.info("Submitting login form.")
            page.click('button[type="submit"]')
            
            self.logger.info("Waiting for login request to complete...")
            page.wait_for_load_state('networkidle', timeout=30000)
            self.logger.info("Login form submitted. Assuming login is successful.")
        except PlaywrightTimeoutError as e:
            screenshot_path = "login_failure_screenshot.png"
            page.screenshot(path=screenshot_path)
            self.logger.error(f"Timeout during login. A screenshot has been saved to '{screenshot_path}'. This might be due to a CAPTCHA.")
            raise e

    def scrape(self) -> List[Dict[str, Any]]:
        """Main scraping method orchestrating login, list scraping, and detail scraping."""
        self.logger.info(f"Starting scrape for {self.__class__.__name__}")
        scraped_data = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            page = browser.new_page()
            
            try:
                self._login(page)

                self.logger.info(f"Navigating to initial scholarship list: {self.BEASISWA_URL}")
                page.goto(self.BEASISWA_URL, timeout=60000)

                # Determine the total number of pages
                self.logger.info("Determining the total number of pages...")
                page_buttons = page.query_selector_all('nav[role="navigation"] button[wire\\:click*="gotoPage"]')
                page_numbers = [int(btn.inner_text()) for btn in page_buttons if btn.inner_text().strip().isdigit()]
                total_pages = max(page_numbers) if page_numbers else 1
                self.logger.info(f"Found {total_pages} pages to scrape.")

                for page_number in range(1, total_pages + 1):
                    if page_number > 1:
                        self.logger.info(f"Navigating to page {page_number}...")
                        page.goto(f"{self.BEASISWA_URL}?page={page_number}", wait_until='domcontentloaded', timeout=60000)
                    self.logger.info(f"Scraping page {page_number}...")
                    page.wait_for_selector('div.drawer-content', timeout=60000)
                    soup = BeautifulSoup(page.content(), 'html.parser')
                    
                    scholarship_cards = soup.select('div.drawer-content a[href^="https://luarkampus.id/beasiswa/"]')
                    scholarships_to_scrape = [card.get('href') for card in scholarship_cards if card.get('href') and card.get('href').split('/')[-1].isdigit()]
                    self.logger.info(f"Found {len(scholarships_to_scrape)} scholarships on page {page_number}.")

                    for detail_url in scholarships_to_scrape:
                        try:
                            self.logger.info(f"Scraping detail page: {detail_url}")
                            page.goto(detail_url, timeout=60000)
                            page.wait_for_load_state('domcontentloaded')
                            detail_soup = BeautifulSoup(page.content(), 'html.parser')

                            title_element = detail_soup.select_one('h1.text-2xl.font-bold')
                            title = title_element.text.strip() if title_element else 'No title found'

                            # Extract deadline
                            deadline_element = detail_soup.select_one('span:-soup-contains(\"Penutupan Pendaftaran\") + div span.ml-2')
                            deadline_str = deadline_element.text.strip() if deadline_element else None
                            
                            if not deadline_str:
                                self.logger.warning(f"Skipping scholarship '{title}' due to missing deadline information.")
                                continue

                            deadline_date = self._parse_indonesian_date(deadline_str)
                            if not deadline_date:
                                self.logger.error(f"Could not parse deadline '{deadline_str}' for '{title}'.")
                                continue

                            # Use current date from a fixed variable for consistent comparison
                            current_date = datetime.now().date()
                            if deadline_date <= current_date:
                                self.logger.info(f"Skipping expired scholarship '{title}' with deadline {deadline_date}.")
                                continue

                            # Extract organizer
                            organizer_tag = detail_soup.find('span', string=re.compile(r'Pemberi Beasiswa'))
                            organizer = organizer_tag.find_next_sibling('div').find('span', class_='ml-2').get_text(strip=True).strip() if organizer_tag else None

                            # Extract requirements to be used as description
                            requirements_section = detail_soup.find('div', id='requirements')
                            description = ''
                            if requirements_section:
                                prose_divs = requirements_section.find_all('div', class_='min-w-full prose')
                                description = '\n'.join(str(div) for div in prose_divs).strip()

                            # Extract booklet/registration URL
                            booklet_section = detail_soup.find(lambda tag: tag.name == 'div' and 'Booklet' in tag.get_text(strip=True) and 'font-bold' in tag.get('class', []))
                            registration_link = None
                            if booklet_section:
                                link_tag = booklet_section.find_next_sibling('div').find('a')
                                if link_tag and link_tag.has_attr('href'):
                                    registration_link = link_tag['href']
                            if not registration_link:
                                self.logger.warning(f"Skipping scholarship '{title}' due to missing registration/booklet URL.")
                                continue

                            # Extract education level
                            education_level_tag = detail_soup.find('span', string=re.compile(r'Jenjang Pendidikan'))
                            education_level = education_level_tag.find_next_sibling('div').find('span', class_='ml-2').get_text(strip=True) if education_level_tag else None

                            # Extract location (from applicable schools/universities)
                            location_tag = detail_soup.find('span', string=re.compile(r'Kampus/Sekolah yang Bisa Mendaftar'))
                            location = location_tag.find_next_sibling('div').find('span', class_='ml-2').get_text(strip=True) if location_tag else None

                            # Scrape image URL from Yandex
                            image_url = self._get_image_url_from_yandex(browser, f"{title}")

                            # Initialize dictionary to hold scholarship data
                            scholarship_data = {
                                'title': title,
                                'image_url': image_url,
                                'deadline_date': deadline_date.isoformat(),
                                'organizer': organizer,
                                'description': description,
                                'booklet_url': registration_link,
                                'source_url': detail_url,
                                'education_level': education_level,
                                'location': location
                            }
                            scraped_data.append(scholarship_data)
                            self.logger.info(f"Successfully scraped: {title}")

                        except Exception as e:
                            self.logger.error(f"Error scraping detail page {detail_url}: {e}")
                            continue

                self.logger.info("Finished scraping all pages.")
            
            except Exception as e:
                self.logger.critical(f"A critical error occurred during the scraping process: {e}", exc_info=True)

            finally:
                self.logger.info("Closing browser.")
                browser.close()

        self.logger.info(f"Scraping finished. Total scholarships scraped: {len(scraped_data)}")
        return scraped_data



    def _get_image_url_from_yandex(self, browser: Browser, query: str) -> Optional[str]:
        """
        Searches for an image on Yandex and returns the URL of the first result.
        Handles errors gracefully by returning None on failure.
        """
        page = None
        try:
            self.logger.info(f"Searching Yandex Images for: {query}")
            page = browser.new_page()
            page.goto("https://yandex.com/images/", timeout=60000)

            # Type the search query
            page.fill('input[name="text"]', query)
            
            # Click the search button
            page.click('button[type="submit"]')
            
            # Wait for search results to load
            first_image_link_selector = 'div.SerpItem a.Link.ImagesContentImage-Cover'
            page.wait_for_selector(first_image_link_selector, timeout=15000)

            # Get the href from the first search result link
            href = page.get_attribute(first_image_link_selector, 'href')
            image_url = None
            if href:
                # Parse the URL and extract the 'img_url' parameter
                parsed_url = urlparse(href)
                query_params = parse_qs(parsed_url.query)
                if 'img_url' in query_params:
                    # URL-decode the image URL
                    image_url = unquote(query_params['img_url'][0])

            if image_url:
                self.logger.info(f"Successfully found image URL on Yandex: {image_url}")
            else:
                self.logger.warning(f"Could not extract original image_url for '{query}'.")
            
            return image_url
        except PlaywrightTimeoutError:
            self.logger.warning(f"Timeout occurred during Yandex image search for '{query}'. No image will be used.")
            return None
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during Yandex image search for '{query}': {e}")
            return None
        finally:
            if page:
                page.close()

    def _parse_indonesian_date(self, date_str: str) -> Optional[date]:
        """
        Parses a date string with Indonesian month abbreviations.
        Example: '01 Agt 2025' -> date(2025, 8, 1)
        """
        month_map = {
            'Jan': 'Jan', 'Feb': 'Feb', 'Mar': 'Mar', 'Apr': 'Apr', 'Mei': 'May',
            'Jun': 'Jun', 'Jul': 'Jul', 'Agt': 'Aug', 'Sep': 'Sep', 'Okt': 'Oct',
            'Nov': 'Nov', 'Des': 'Dec'
        }
        
        for indo_month, eng_month in month_map.items():
            if indo_month in date_str:
                date_str = date_str.replace(indo_month, eng_month)
                break
        
        try:
            return datetime.strptime(date_str, '%d %b %Y').date()
        except ValueError:
            return None
