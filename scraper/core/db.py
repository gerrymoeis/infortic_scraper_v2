import os
import time
import logging
from typing import List, Optional
from supabase import create_client, Client
from retrying import retry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SupabaseDBClient:
    """
    Supabase database client with retry/backoff logic and bulk insert capabilities.
    
    This client provides methods for upserting data to Supabase tables with
    automatic retry logic and error handling.
    """
    
    def __init__(self, batch_size: int = 1000):
        """
        Initialize the Supabase client.
        
        Args:
            batch_size: Maximum number of rows to process in a single batch
        """
        url = os.getenv('SUPABASE_URL')
        anon_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not url or not anon_key:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables")
        
        try:
            self.client: Client = create_client(url, anon_key)
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {str(e)}")
            logger.error(f"This might be a version compatibility issue. Try updating dependencies.")
            raise ValueError(f"Failed to initialize Supabase client: {str(e)}")
        self.batch_size = batch_size
        logger.info(f"Supabase client initialized with batch size: {batch_size}")
    
    def _exponential_backoff(self, attempt: int) -> int:
        """
        Calculate exponential backoff delay.
        
        Args:
            attempt: The current attempt number (0-indexed)
            
        Returns:
            Delay in milliseconds
        """
        base_delay = 1000  # 1 second
        return min(base_delay * (2 ** attempt), 30000)  # Max 30 seconds
    
    @retry(
        stop_max_attempt_number=3,
        wait_func=lambda attempt, delay: max(1000, min(30000, 1000 * (2 ** attempt)))
    )
    def _insert_batch(self, rows: List[dict]) -> int:
        """
        Insert a batch of rows to the lomba table.
        
        Args:
            rows: List of dictionaries representing lomba records
            
        Returns:
            Number of rows processed
            
        Raises:
            Exception: If the insert operation fails after all retries
        """
        try:
            logger.info(f"Attempting to insert {len(rows)} rows to lomba table")
            
            # Perform the insert operation
            response = self.client.table('lomba').insert(rows).execute()
            
            # Check for errors in the response
            if hasattr(response, 'error') and response.error:
                raise Exception(f"Supabase error: {response.error}")
            
            # Count successful operations
            processed_count = len(response.data) if hasattr(response, 'data') and response.data else len(rows)
            logger.info(f"Successfully inserted {processed_count} rows")
            
            return processed_count
            
        except Exception as e:
            logger.error(f"Failed to insert batch: {str(e)}")
            raise
    
    @retry(
        stop_max_attempt_number=3,
        wait_func=lambda attempt, delay: max(1000, min(30000, 1000 * (2 ** attempt)))
    )
    def _upsert_batch(self, rows: List[dict]) -> int:
        """
        Upsert a batch of rows to the lomba table.
        
        Args:
            rows: List of dictionaries representing lomba records
            
        Returns:
            Number of rows processed
            
        Raises:
            Exception: If the upsert operation fails after all retries
        """
        try:
            logger.info(f"Attempting to upsert {len(rows)} rows to lomba table")
            
            # Perform the upsert operation
            response = self.client.table('lomba').upsert(
                rows, 
                on_conflict='source_url',
                ignore_duplicates=True
            ).execute()
            
            # Check for errors in the response
            if hasattr(response, 'error') and response.error:
                raise Exception(f"Supabase error: {response.error}")
            
            # Count successful operations
            processed_count = len(response.data) if hasattr(response, 'data') and response.data else len(rows)
            logger.info(f"Successfully upserted {processed_count} rows")
            
            return processed_count
            
        except Exception as e:
            logger.error(f"Failed to upsert batch: {str(e)}")
            raise
    
    def clean_lomba_table(self) -> bool:
        """
        Clean all existing data from the lomba table using Supabase client.
        
        Returns:
            True if successful, False otherwise
            
        Raises:
            Exception: If cleaning fails and should stop scraper execution
        """
        try:
            logger.info("Cleaning existing data from lomba table using Supabase client")
            
            # Use a validated delete call - delete all records where id is not null
            # This is a safer approach than using a fake UUID
            response = self.client.table('lomba').delete().not_.is_('id', 'null').execute()
            
            # Log detailed response information
            logger.info(f"Delete response status_code: {getattr(response, 'status_code', 'N/A')}")
            logger.info(f"Delete response data: {getattr(response, 'data', 'N/A')}")
            
            # Check for errors in the response
            if hasattr(response, 'error') and response.error:
                logger.error(f"Delete response error: {response.error}")
                raise Exception(f"Supabase delete error: {response.error}")
            
            # Verify the operation was successful
            if hasattr(response, 'status_code') and response.status_code >= 400:
                logger.error(f"Delete operation failed with status code: {response.status_code}")
                raise Exception(f"Delete operation failed with status code: {response.status_code}")
            
            logger.info("Successfully cleaned lomba table using Supabase client")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clean lomba table: {str(e)}")
            # Re-raise the exception to stop scraper execution with stale data
            raise Exception(f"Critical error during table cleaning: {str(e)}. Scraper cannot continue with stale data.")
    
    def clean_lomba_table_with_function(self) -> bool:
        """
        Clean all existing data from the lomba table using PostgreSQL function.
        
        This method calls the clean_lomba_table() PostgreSQL function that was
        created via migration. This is more efficient for large datasets.
        
        Returns:
            True if successful, False otherwise
            
        Raises:
            Exception: If cleaning fails and should stop scraper execution
        """
        try:
            logger.info("Cleaning existing data from lomba table using PostgreSQL function")
            
            # Call the PostgreSQL cleaning function (using simple version that works)
            response = self.client.rpc('clean_lomba_simple').execute()
            
            # Log detailed response information
            logger.info(f"Function response status_code: {getattr(response, 'status_code', 'N/A')}")
            logger.info(f"Function response data: {getattr(response, 'data', 'N/A')}")
            
            # Check for errors in the response
            if hasattr(response, 'error') and response.error:
                logger.error(f"Function response error: {response.error}")
                raise Exception(f"PostgreSQL function error: {response.error}")
            
            # Verify the operation was successful
            if hasattr(response, 'status_code') and response.status_code >= 400:
                logger.error(f"Function call failed with status code: {response.status_code}")
                raise Exception(f"Function call failed with status code: {response.status_code}")
            
            logger.info("Successfully cleaned lomba table using PostgreSQL function")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clean lomba table with function: {str(e)}")
            # Re-raise the exception to stop scraper execution with stale data
            raise Exception(f"Critical error during table cleaning with function: {str(e)}. Scraper cannot continue with stale data.")
    
    def get_lomba_count(self) -> int:
        """
        Get the current count of rows in the lomba table.
        
        Returns:
            Number of rows in the lomba table
            
        Raises:
            Exception: If count query fails
        """
        try:
            logger.info("Getting lomba table row count")
            
            response = self.client.table('lomba').select('*', count='exact').execute()
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"Count query error: {response.error}")
                raise Exception(f"Count query error: {response.error}")
            
            count = response.count if hasattr(response, 'count') else 0
            logger.info(f"Lomba table contains {count} rows")
            
            return count
            
        except Exception as e:
            logger.error(f"Failed to get lomba count: {str(e)}")
            raise
    

    def insert_lomba_rows(self, rows: List[dict], clean_first: bool = True) -> int:
        """
        Insert lomba rows with cleaning and deduplication.
        
        This method:
        1. Optionally cleans existing data
        2. Deduplicates the input rows
        3. Inserts rows in batches using simple insert operations
        
        Args:
            rows: List of dictionaries representing lomba records
            clean_first: Whether to clean the table before insertion
        
        Returns:
            Total number of rows processed
            
        Raises:
            ValueError: If rows list is empty or invalid
            Exception: If the operation fails after all retries
        """
        if not rows:
            logger.warning("No rows provided for insertion")
            return 0
        
        if not isinstance(rows, list):
            raise ValueError("Rows must be a list of dictionaries")
        
        # Validate that all rows are dictionaries
        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                raise ValueError(f"Row {i} is not a dictionary")
        
        # Clean the table if requested
        if clean_first:
            try:
                self.clean_lomba_table()
            except Exception as e:
                logger.error(f"Table cleaning failed: {str(e)}")
                # Re-raise the exception to prevent scraper from continuing with stale data
                raise Exception(f"Cannot proceed with data insertion due to cleaning failure: {str(e)}")
        
        total_processed = 0
        total_rows = len(rows)
        
        logger.info(f"Starting bulk insert operation for {total_rows} rows")
        
        try:
            # Process rows in batches
            for i in range(0, total_rows, self.batch_size):
                batch = rows[i:i + self.batch_size]
                batch_num = (i // self.batch_size) + 1
                total_batches = (total_rows + self.batch_size - 1) // self.batch_size
                
                logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} rows)")
                
                # Process the batch with retry logic
                processed = self._insert_batch(batch)
                total_processed += processed
                
                # Small delay between batches to avoid overwhelming the server
                if i + self.batch_size < total_rows:
                    time.sleep(0.1)
            
            logger.info(f"Bulk insert completed successfully. Total rows processed: {total_processed}")
            return total_processed
            
        except Exception as e:
            logger.error(f"Bulk insert operation failed: {str(e)}")
            logger.info(f"Rows processed before failure: {total_processed}")
            raise
    
    def test_connection(self) -> bool:
        """
        Test the connection to Supabase.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Simple query to test connection
            response = self.client.table('lomba').select('*').limit(1).execute()
            logger.info("Supabase connection test successful")
            return True
        except Exception as e:
            logger.error(f"Supabase connection test failed: {str(e)}")
            return False
