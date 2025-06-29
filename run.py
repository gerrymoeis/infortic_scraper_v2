#!/usr/bin/env python3
"""
Main runner script for the Infortic scraper architecture.
Demonstrates how to use the scalable scraper system.
"""

import os
import sys
import time
from dotenv import load_dotenv

# Add the scraper directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper.core.logger import Logger
from scraper.lomba.infolomba_scraper import InfoLombaScraper


def main():
    """
    Main function to run scrapers.
    """
    # Load environment variables
    load_dotenv()
    
    # Initialize logger
    logger = Logger()
    logger.info("=== Starting Infortic Scraper System ===")
    
    try:
        # Example: Run InfoLomba scraper
        run_infolomba_scraper()
        
        logger.info("=== Scraping completed successfully ===")
        
    except Exception as e:
        logger.error(f"Scraping failed: {str(e)}")
        sys.exit(1)


def run_infolomba_scraper():
    """
    Run the InfoLomba scraper.
    """
    logger = Logger()
    logger.info("Starting InfoLomba scraper...")
    
    start_time = time.time()
    
    try:
        # Create and run scraper
        scraper = InfoLombaScraper(headless=True, timeout=30)
        results = scraper.scrape()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Log results
        competitions_count = len(results.get('competitions', []))
        logger.log_scraper_end("InfoLombaScraper", competitions_count, duration)
        
        return results
        
    except Exception as e:
        logger.log_scraper_error("InfoLombaScraper", e)
        raise


def run_all_scrapers():
    """
    Run all available scrapers.
    Add new scrapers here as they are implemented.
    """
    logger = Logger()
    logger.info("Running all scrapers...")
    
    scrapers = [
        ("InfoLomba", run_infolomba_scraper),
        # Add more scrapers here:
        # ("AnotherScraper", run_another_scraper),
    ]
    
    results = {}
    
    for scraper_name, scraper_func in scrapers:
        try:
            logger.info(f"Running {scraper_name} scraper...")
            results[scraper_name] = scraper_func()
        except Exception as e:
            logger.error(f"Failed to run {scraper_name}: {str(e)}")
            results[scraper_name] = None
    
    return results


def setup_environment():
    """
    Setup and validate the environment.
    """
    logger = Logger()
    
    # Check required environment variables
    required_vars = ['DB_HOST', 'DB_NAME', 'DB_USER']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.info("Please check your .env file configuration")
        return False
    
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    logger.info("Environment setup completed successfully")
    return True


if __name__ == "__main__":
    # Setup environment first
    if not setup_environment():
        sys.exit(1)
    
    # Handle command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "all":
            run_all_scrapers()
        elif command == "infolomba":
            run_infolomba_scraper()
        elif command == "help":
            print("Usage: python run.py [command]")
            print("Commands:")
            print("  all      - Run all scrapers")
            print("  infolomba - Run InfoLomba scraper only")
            print("  help     - Show this help message")
        else:
            print(f"Unknown command: {command}")
            print("Use 'python run.py help' for available commands")
    else:
        # Default: run main function
        main()
