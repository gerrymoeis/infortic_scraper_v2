# file: tests/test_infolomba_scraper.py
import unittest
from bs4 import BeautifulSoup
from scraper.lomba.infolomba_scraper import InfoLombaScraper

class TestInfoLombaScraper(unittest.TestCase):
    
    def test_selectors_on_static_html(self):
        with open('tests/fixtures/infolomba_sample.html', 'r', encoding='utf-8') as file:
            soup = BeautifulSoup(file, 'html.parser')
        
        event_list_container = soup.select_one(InfoLombaScraper.EVENT_LIST_CONTAINER_SELECTOR)
        event_links = event_list_container.select(InfoLombaScraper.EVENT_LINK_SELECTOR)
        
        self.assertIsNotNone(event_list_container, "Event list container should not be None")
        self.assertEqual(len(event_links), 3, "Should find exactly 3 event links")

if __name__ == '__main__':
    unittest.main()
