#!/usr/bin/env python3
"""
Simple runner script that wires scraper output to Supabase insertion.
Includes testing of the cleaning function implementation.
"""

import os
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


def test_cleaning_function():
    """
    Test the PostgreSQL cleaning function implementation.
    
    This function:
    1. Inserts test data
    2. Verifies data exists
    3. Calls cleaning function
    4. Verifies table is empty
    """
    logger.info("Starting cleaning function test...")
    
    try:
        # Load environment
        load_dotenv()
        logger.info("Environment variables loaded")
        
        # Initialize database client
        db_client = SupabaseDBClient()
        
        # Test connection first
        if not db_client.test_connection():
            raise Exception("Database connection test failed")
        
        logger.info("=== Step 1: Getting initial count ===")
        initial_count = db_client.get_lomba_count()
        logger.info(f"Initial lomba table count: {initial_count}")
        
        logger.info("=== Step 2: Inserting test data ===")
        import uuid
        unique_id = str(uuid.uuid4())
        test_data = [{
            'title': f'TEST: Cleaning Function Test {unique_id}',
            'description': f'This is a test entry for cleaning function verification {unique_id}',
            'organizer': 'Test Organizer',
            'poster_url': f'https://test.example.com/poster-{unique_id}.jpg',
            'registration_url': f'https://test.example.com/register-test-cleaning-{unique_id}',
            'source_url': f'https://test.example.com/source-test-cleaning-{unique_id}',
            'date_text': 'TEST: 2024-01-01 to 2024-01-31',
            'price_text': 'FREE (TEST)',
            'participant': 'Test Participants',
            'location': 'Test Location'
        }]
        
        # Insert without cleaning first
        inserted_count = db_client.insert_lomba_rows(test_data, clean_first=False)
        logger.info(f"Inserted {inserted_count} test rows")
        
        logger.info("=== Step 3: Verifying data exists ===")
        count_after_insert = db_client.get_lomba_count()
        logger.info(f"Count after insert: {count_after_insert}")
        
        if count_after_insert <= initial_count:
            raise Exception(f"Expected count to increase from {initial_count}, but got {count_after_insert}")
        
        logger.info("=== Step 4: Testing PostgreSQL cleaning function ===")
        success = db_client.clean_lomba_table_with_function()
        
        if not success:
            raise Exception("Cleaning function returned False")
        
        # Add a small delay to ensure the transaction is committed
        import time
        time.sleep(1)
        
        logger.info("=== Step 5: Verifying table is empty ===")
        # Create a fresh database client to avoid any connection caching issues
        fresh_db_client = SupabaseDBClient()
        final_count = fresh_db_client.get_lomba_count()
        logger.info(f"Final count after cleaning: {final_count}")
        
        if final_count != 0:
            raise Exception(f"Expected table to be empty (count=0), but found {final_count} rows")
        
        logger.info("🎉 Cleaning function test PASSED! All verifications successful.")
        return True
        
    except Exception as e:
        logger.error(f"❌ Cleaning function test FAILED: {str(e)}")
        return False


def run_scraper_with_cleaning():
    """
    Run the scraper with the PostgreSQL cleaning function.
    """
    logger.info("Starting scraper with PostgreSQL cleaning function...")
    
    try:
        # Load environment
        load_dotenv()
        logger.info("Environment variables loaded")
        
        # Initialize database client
        db_client = SupabaseDBClient()
        
        # Test connection
        if not db_client.test_connection():
            raise Exception("Database connection test failed")
        
        logger.info("=== Getting initial count ===")
        initial_count = db_client.get_lomba_count()
        logger.info(f"Initial lomba table count: {initial_count}")
        
        logger.info("=== Cleaning table with PostgreSQL function ===")
        success = db_client.clean_lomba_table_with_function()
        
        if not success:
            raise Exception("Table cleaning failed")
        
        logger.info("=== Verifying table is clean ===")
        clean_count = db_client.get_lomba_count()
        logger.info(f"Count after cleaning: {clean_count}")
        
        if clean_count != 0:
            logger.warning(f"Table not completely clean - still has {clean_count} rows")
        
        logger.info("=== Starting scraper ===")
        scraper = InfoLombaScraper(db_client=db_client, headless=True, timeout=30)
        logger.info("InfoLombaScraper instantiated")
        
        # Scrape data
        results = scraper.scrape()
        logger.info(f"Scraped {len(results)} items")
        
        # Insert without cleaning (since we already cleaned)
        if results:
            affected_rows = db_client.insert_lomba_rows(results, clean_first=False)
            logger.info(f"Successfully inserted {affected_rows} rows into database")
            
            # Final verification
            final_count = db_client.get_lomba_count()
            logger.info(f"Final table count: {final_count}")
            
            print(f"\n=== SCRAPER SUMMARY ===")
            print(f"Initial count: {initial_count}")
            print(f"After cleaning: {clean_count}")
            print(f"Scraped items: {len(results)}")
            print(f"Inserted rows: {affected_rows}")
            print(f"Final count: {final_count}")
            print(f"======================")
            
        else:
            logger.info("No items to insert into database")
            
    except Exception as e:
        logger.error(f"Error during scraper with cleaning: {str(e)}")
        raise

def run_beasiswa_scraper():
    """
    Runs the LuarKampus.id Beasiswa scraper and inserts the data into the database.
    """
    logger.info("Running Beasiswa scraper...")
    
    try:
        db_client = SupabaseDBClient()
        db_client.test_connection()

        logger.info("Starting Beasiswa scraper...")
        load_dotenv()
        logger.info("Environment variables loaded")
        
        scraper = LuarKampusBeasiswaScraper(db_client=db_client)
        results = scraper.scrape()
        logger.info(f"Scraped {len(results)} beasiswa items")
        
        if results:
            db_client.insert_beasiswa_rows(results)
        else:
            logger.info("No beasiswa items to insert into database")
            
    except Exception as e:
        logger.error(f"Error during beasiswa scraping: {e}", exc_info=True)
        sys.exit(1)

def main():
    """
    Main function to run scraper and insert data into Supabase.
    """
    # 1. Load environment
    load_dotenv()
    logger.info("Environment variables loaded")
    
    try:
        # 2. Instantiate InfolombaScraper (InfoLombaScraper)
        db_client = SupabaseDBClient()
        scraper = InfoLombaScraper(db_client=db_client, headless=True, timeout=30)
        logger.info("InfoLombaScraper instantiated")
        
        # 3. Call .scrape() and log count
        results = scraper.scrape()
        logger.info(f"Scraped {len(results)} items")
        
        # 4. On non-empty list, call db.insert_lomba_rows() and print affected rows
        if results:
            affected_rows = db_client.insert_lomba_rows(results)
            print(f"Affected rows: {affected_rows}")
            logger.info(f"Successfully inserted {affected_rows} rows into database")
        else:
            logger.info("No items to insert into database")
            
    except Exception as e:
        logger.error(f"Error during scraping and insertion: {str(e)}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='InfoLomba Scraper Runner')
    parser.add_argument('--test-cleaning', action='store_true', 
                       help='Test the PostgreSQL cleaning function')
    parser.add_argument('--run-with-cleaning', action='store_true',
                       help='Run scraper with PostgreSQL cleaning function')
    parser.add_argument('--scrape-beasiswa', action='store_true',
                        help='Run the Beasiswa scraper for luarkampus.id')
    
    args = parser.parse_args()
    
    if args.test_cleaning:
        logger.info("Running cleaning function test...")
        success = test_cleaning_function()
        sys.exit(0 if success else 1)
    elif args.run_with_cleaning:
        logger.info("Running scraper with cleaning...")
        run_scraper_with_cleaning()
    elif args.scrape_beasiswa:
        logger.info("Running Beasiswa scraper...")
        run_beasiswa_scraper()
    else:
        logger.info("Running standard scraper...")
        main()
