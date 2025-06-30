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
    """
    
    def __init__(self, batch_size: int = 1000):
        url = os.getenv('SUPABASE_URL')
        service_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if not url or not service_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment variables")
        
        try:
            self.client: Client = create_client(url, service_key)
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise
        self.batch_size = batch_size
        logger.info(f"Supabase client initialized with batch size: {batch_size}")

    def test_connection(self) -> bool:
        """
        Test the connection to Supabase.
        """
        try:
            self.client.table('lomba').select('id').limit(1).execute()
            logger.info("Supabase connection test successful")
            return True
        except Exception as e:
            logger.error(f"Supabase connection test failed: {e}")
            return False

    # --- Lomba Methods ---
    def insert_lomba_rows(self, rows: List[dict], clean_first: bool = False) -> int:
        if clean_first:
            self.clean_lomba_table_with_function()
        return self._insert_rows('lomba', rows)

    def clean_lomba_table_with_function(self) -> bool:
        return self._clean_table_with_function('clean_lomba_simple', 'lomba')

    def get_lomba_count(self) -> Optional[int]:
        return self._get_table_count('lomba')

    # --- Beasiswa Methods ---
    def insert_beasiswa_rows(self, rows: List[dict], clean_first: bool = False) -> int:
        if clean_first:
            self.clean_beasiswa_table_with_function()
        return self._insert_rows('beasiswa', rows)

    def clean_beasiswa_table_with_function(self) -> bool:
        return self._clean_table_with_function('clean_beasiswa_simple', 'beasiswa')

    def get_beasiswa_count(self) -> Optional[int]:
        return self._get_table_count('beasiswa')

    # --- Generic Helper Methods ---
    def _insert_rows(self, table_name: str, rows: List[dict]) -> int:
        """Generic method to insert rows into a table in batches."""
        if not rows:
            logger.warning(f"No rows provided for insertion into '{table_name}'")
            return 0

        total_inserted = 0
        for i in range(0, len(rows), self.batch_size):
            batch = rows[i:i + self.batch_size]
            try:
                response = self.client.table(table_name).insert(batch).execute()
                if hasattr(response, 'error') and response.error:
                    raise Exception(f"Supabase error: {response.error}")
                total_inserted += len(response.data)
            except Exception as e:
                logger.error(f"Failed to insert batch into '{table_name}': {e}")
        return total_inserted

    def _clean_table_with_function(self, function_name: str, table_name: str) -> bool:
        """Generic method to clean a table using a PostgreSQL function."""
        try:
            logger.info(f"Cleaning existing data from '{table_name}' table using '{function_name}'")
            response = self.client.rpc(function_name, {}).execute()
            if hasattr(response, 'error') and response.error:
                raise Exception(f"PostgreSQL function error: {response.error}")
            logger.info(f"Successfully cleaned '{table_name}' table")
            return True
        except Exception as e:
            logger.error(f"Failed to clean '{table_name}' table: {e}")
            raise

    def _get_table_count(self, table_name: str) -> Optional[int]:
        """Generic method to get the row count of a table."""
        try:
            response = self.client.table(table_name).select('id', count='exact').execute()
            if hasattr(response, 'error') and response.error:
                raise Exception(f"Count query error: {response.error}")
            return response.count
        except Exception as e:
            logger.error(f"Failed to get count for '{table_name}': {e}")
            return None
