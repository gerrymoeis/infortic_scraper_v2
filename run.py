#!/usr/bin/env python3
"""
Simple runner script that wires scraper output to Supabase insertion.
"""

import sys
import logging
import argparse
from dotenv import load_dotenv

from scraper.lomba.infolomba_scraper import InfoLombaScraper
from scraper.beasiswa.luarkampus_scraper import LuarKampusBeasiswaScraper
from scraper.core.db import SupabaseDBClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Map scraper names to their classes and DB functions
SCRAPER_CONFIG = {
    'lomba': {
        'class': InfoLombaScraper,
        'insert_method': 'insert_lomba_rows',
        'clean_method': 'clean_lomba_table_with_function',
        'count_method': 'get_lomba_count',
    },
    'beasiswa': {
        'class': LuarKampusBeasiswaScraper,
        'insert_method': 'insert_beasiswa_rows',
        'clean_method': 'clean_beasiswa_table_with_function',
        'count_method': 'get_beasiswa_count',
    }
}

def main():
    """Main function to parse arguments and run the scraper."""
    parser = argparse.ArgumentParser(description="Run a specified scraper and insert data into Supabase.")
    parser.add_argument('scraper_name', choices=SCRAPER_CONFIG.keys(), help="The name of the scraper to run.")
    parser.add_argument('--run-with-cleaning', action='store_true', help="Clean the table before inserting new data.")
    parser.add_argument('--start-page', type=int, default=1, help="The page number to start scraping from.")
    parser.add_argument('--max-pages', type=int, default=999, help="The maximum number of pages to scrape in this run.")
    parser.add_argument('--clean-only', action='store_true', help="Only run the cleaning process for the specified scraper.")

    args = parser.parse_args()

    if args.clean_only:
        clean_database(args.scraper_name)
    else:
        run_scraper(scraper_name=args.scraper_name, 
                    clean_first=args.run_with_cleaning, 
                    start_page=args.start_page, 
                    max_pages=args.max_pages)

def clean_database(scraper_name: str):
    """Runs only the cleaning process for a specified scraper's table."""
    if scraper_name not in SCRAPER_CONFIG:
        logger.error(f"Invalid scraper name: '{scraper_name}'. Valid options are: {list(SCRAPER_CONFIG.keys())}")
        sys.exit(1)

    logger.info(f"Starting database cleaning for '{scraper_name}' table.")
    try:
        load_dotenv()
        db_client = SupabaseDBClient()
        config = SCRAPER_CONFIG[scraper_name]
        clean_method = getattr(db_client, config['clean_method'])
        
        logger.info(f"Executing cleaning method: {config['clean_method']}")
        clean_method()
        logger.info(f"Successfully cleaned the '{scraper_name}' table.")

    except Exception as e:
        logger.critical(f"An error occurred during the database cleaning process: {e}", exc_info=True)
        sys.exit(1)

def main():
    """Main function to parse arguments and run the scraper."""
    parser = argparse.ArgumentParser(description="Run a specified scraper and insert data into Supabase.")
    parser.add_argument('scraper_name', choices=SCRAPER_CONFIG.keys(), help="The name of the scraper to run.")
    parser.add_argument('--run-with-cleaning', action='store_true', help="Clean the table before inserting new data.")
    parser.add_argument('--start-page', type=int, default=1, help="The page number to start scraping from.")
    parser.add_argument('--max-pages', type=int, default=999, help="The maximum number of pages to scrape in this run.")
    parser.add_argument('--clean-only', action='store_true', help="Only run the cleaning process for the specified scraper.")

    args = parser.parse_args()

    if args.clean_only:
        clean_database(args.scraper_name)
    else:
        run_scraper(scraper_name=args.scraper_name, 
                    clean_first=args.run_with_cleaning, 
                    start_page=args.start_page, 
                    max_pages=args.max_pages)

def clean_database(scraper_name: str):
    """Runs only the cleaning process for a specified scraper's table."""
    if scraper_name not in SCRAPER_CONFIG:
        logger.error(f"Invalid scraper name: '{scraper_name}'. Valid options are: {list(SCRAPER_CONFIG.keys())}")
        sys.exit(1)

    logger.info(f"Starting database cleaning for '{scraper_name}' table.")
    try:
        load_dotenv()
        db_client = SupabaseDBClient()
        config = SCRAPER_CONFIG[scraper_name]
        clean_method = getattr(db_client, config['clean_method'])
        
        logger.info(f"Executing cleaning method: {config['clean_method']}")
        clean_method()
        logger.info(f"Successfully cleaned the '{scraper_name}' table.")

    except Exception as e:
        logger.critical(f"An error occurred during the database cleaning process: {e}", exc_info=True)
        sys.exit(1)

def run_scraper(scraper_name: str, clean_first: bool, start_page: int, max_pages: int):
    """
    Runs a specified scraper and inserts the data into the database.

    Args:
        scraper_name: The name of the scraper to run ('lomba' or 'beasiswa').
        clean_first: If True, cleans the corresponding table before inserting data.
    """
    if scraper_name not in SCRAPER_CONFIG:
        logger.error(f"Invalid scraper name: '{scraper_name}'. Valid options are: {list(SCRAPER_CONFIG.keys())}")
        sys.exit(1)

    logger.info(f"Starting run for '{scraper_name}' scraper. Cleaning: {clean_first}")

    try:
        load_dotenv()
        db_client = SupabaseDBClient()

        if not db_client.test_connection():
            raise Exception("Database connection test failed.")

        config = SCRAPER_CONFIG[scraper_name]
        scraper_class = config['class']
        insert_method_name = config['insert_method']
        clean_method_name = config['clean_method']
        count_method_name = config['count_method']

        # Get methods from the db_client instance
        insert_method = getattr(db_client, insert_method_name)
        clean_method = getattr(db_client, clean_method_name)
        count_method = getattr(db_client, count_method_name)

        initial_count = count_method()
        logger.info(f"Initial count for '{scraper_name}' table: {initial_count}")

        clean_count = initial_count
        if clean_first:
            logger.info(f"Cleaning '{scraper_name}' table...")
            if not clean_method():
                raise Exception(f"Table cleaning failed for '{scraper_name}'")
            
            clean_count = count_method()
            logger.info(f"Count after cleaning: {clean_count}")
            if clean_count != 0:
                logger.warning(f"Table not completely clean - still has {clean_count} rows")

        logger.info(f"Instantiating '{scraper_class.__name__}'...")
        scraper = scraper_class(db_client=db_client, start_page=start_page, max_pages=max_pages)
        
        results = scraper.scrape()
        logger.info(f"Scraped {len(results)} items from '{scraper_name}'")

        if results:
            # Pass clean_first=False because we handled it already
            affected_rows = insert_method(results, clean_first=False)
            logger.info(f"Successfully inserted {affected_rows} rows into '{scraper_name}' database table.")
            
            final_count = count_method()
            logger.info(f"Final table count for '{scraper_name}': {final_count}")

            print("\n=== SCRAPER SUMMARY ===")
            print(f"Scraper: {scraper_name}")
            print(f"Initial count: {initial_count}")
            if clean_first:
                print(f"After cleaning: {clean_count}")
            print(f"Scraped items: {len(results)}")
            print(f"Inserted rows: {affected_rows}")
            print(f"Final count: {final_count}")
            print("======================")
        else:
            logger.info("No items to insert into database.")

    except Exception as e:
        logger.error(f"An error occurred during the '{scraper_name}' scraper run: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
