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

    # --- Magang Methods ---
    def insert_magang_rows(self, rows: List[dict], clean_first: bool = False) -> int:
        if clean_first:
            self.clean_magang_table_with_function()
        return self._insert_rows('magang', rows)

    def clean_magang_table_with_function(self) -> bool:
        return self._clean_table_with_function('clean_magang_simple', 'magang')

    def get_magang_count(self) -> Optional[int]:
        return self._get_table_count('magang')

    # --- Generic Helper Methods ---
    def _deduplicate_rows(self, rows: List[dict], unique_key: str) -> List[dict]:
        """
        Remove duplicate rows based on a unique key.
        Keeps the first occurrence of each unique key.
        """
        seen = set()
        deduplicated = []
        duplicates_count = 0
        
        for row in rows:
            key_value = row.get(unique_key)
            if key_value and key_value not in seen:
                seen.add(key_value)
                deduplicated.append(row)
            else:
                duplicates_count += 1
                logger.debug(f"Removing duplicate {unique_key}: {key_value}")
        
        if duplicates_count > 0:
            logger.info(f"Removed {duplicates_count} duplicate rows based on {unique_key}")
        
        return deduplicated
    
    def _insert_rows(self, table_name: str, rows: List[dict]) -> int:
        """Generic method to insert rows into a table in batches."""
        if not rows:
            logger.warning(f"No rows provided for insertion into '{table_name}'")
            return 0

        # Deduplicate rows based on table-specific unique keys
        if table_name == 'lomba':
            rows = self._deduplicate_rows(rows, 'registration_url')
            conflict_column = 'registration_url'
        elif table_name == 'beasiswa':
            rows = self._deduplicate_rows(rows, 'source_url')
            conflict_column = 'source_url'
        elif table_name == 'magang':
            rows = self._deduplicate_rows(rows, 'detail_page_url')
            conflict_column = 'detail_page_url'
        else:
            conflict_column = None

        total_inserted = 0
        for i in range(0, len(rows), self.batch_size):
            batch = rows[i:i + self.batch_size]
            if table_name == 'lomba':
                records = [
                    {
                        'title': item.get('title'),
                        'description': item.get('description'),
                        'organizer': item.get('organizer'),
                        'poster_url': item.get('poster_url'),
                        'registration_url': item.get('registration_url'),
                        'source_url': item.get('source_url'),
                        'date_text': item.get('date_text'),
                        'price_text': item.get('price_text'),
                        'participant': item.get('participant'),
                        'location': item.get('location'),
                    }
                    for item in batch
                ]
            elif table_name == 'beasiswa':
                records = [
                    {
                        'title': item.get('title'),
                        'education_level': item.get('education_level'),
                        'location': item.get('location'),
                        'deadline_date': item.get('deadline_date'),
                        'source_url': item.get('source_url'),
                        'image_url': item.get('image_url'),
                        'booklet_url': item.get('booklet_url'),
                        'description': item.get('description'),
                        'organizer': item.get('organizer'),
                    }
                    for item in batch
                ]
            elif table_name == 'magang':
                records = [
                    {
                        'company': item.get('company'),
                        'detail_page_url': item.get('detail_page_url'),
                        'company_page_url': item.get('company_page_url'),
                        'location': item.get('location'),
                        'description': item.get('description'),
                        'intern_position': item.get('intern_position'),
                        'responsibilities': item.get('responsibilities'),
                        'criteria': item.get('criteria'),
                        'learning_outcome': item.get('learning_outcome'),
                        'company_location': item.get('company_location'),
                        'field': item.get('field'),
                        'logo_image_url': item.get('logo_image_url'),
                    }
                    for item in batch
                ]    
            try:
                response = self.client.table(table_name).upsert(records, on_conflict='registration_url').execute()
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
