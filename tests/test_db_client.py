# file: tests/test_db_client.py
import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import sys

# Add the parent directory to sys.path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scraper.core.db import SupabaseDBClient


class TestSupabaseDBClient(unittest.TestCase):
    """Test suite for SupabaseDBClient cleaning functionality"""

    @patch('scraper.core.db.create_client')
    @patch.dict(os.environ, {'SUPABASE_URL': 'test_url', 'SUPABASE_ANON_KEY': 'test_key'})
    def setUp(self, mock_create_client):
        """Set up test fixtures"""
        self.mock_supabase_client = MagicMock()
        mock_create_client.return_value = self.mock_supabase_client
        self.db_client = SupabaseDBClient()

    def test_clean_lomba_table_success(self):
        """Test successful table cleaning with proper logging"""
        # Mock successful delete response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.data = [{'id': '1'}, {'id': '2'}]
        mock_response.error = None
        
        self.mock_supabase_client.table.return_value.delete.return_value.not_.is_.return_value.execute.return_value = mock_response
        
        # Call the method
        result = self.db_client.clean_lomba_table()
        
        # Verify the response
        self.assertTrue(result)
        
        # Verify the correct delete query was used
        self.mock_supabase_client.table.assert_called_with('lomba')
        self.mock_supabase_client.table.return_value.delete.return_value.not_.is_.assert_called_with('id', 'null')

    def test_clean_lomba_table_with_supabase_error(self):
        """Test table cleaning with Supabase error response"""
        # Mock error response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.data = None
        mock_response.error = "Database connection failed"
        
        self.mock_supabase_client.table.return_value.delete.return_value.not_.is_.return_value.execute.return_value = mock_response
        
        # Call the method and expect exception
        with self.assertRaises(Exception) as context:
            self.db_client.clean_lomba_table()
        
        # Verify error message contains expected information
        self.assertIn("Critical error during table cleaning", str(context.exception))
        self.assertIn("Scraper cannot continue with stale data", str(context.exception))

    def test_clean_lomba_table_with_http_error(self):
        """Test table cleaning with HTTP error status code"""
        # Mock HTTP error response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.data = None
        mock_response.error = None
        
        self.mock_supabase_client.table.return_value.delete.return_value.not_.is_.return_value.execute.return_value = mock_response
        
        # Call the method and expect exception
        with self.assertRaises(Exception) as context:
            self.db_client.clean_lomba_table()
        
        # Verify error message contains expected information
        self.assertIn("Delete operation failed with status code: 500", str(context.exception))

    def test_clean_lomba_table_with_network_exception(self):
        """Test table cleaning with network exception"""
        # Mock network exception
        self.mock_supabase_client.table.return_value.delete.return_value.not_.is_.return_value.execute.side_effect = Exception("Network error")
        
        # Call the method and expect exception
        with self.assertRaises(Exception) as context:
            self.db_client.clean_lomba_table()
        
        # Verify error message contains expected information
        self.assertIn("Critical error during table cleaning", str(context.exception))
        self.assertIn("Network error", str(context.exception))

    def test_insert_lomba_rows_with_cleaning_failure(self):
        """Test that insert_lomba_rows properly handles cleaning failures"""
        # Mock cleaning to fail
        self.mock_supabase_client.table.return_value.delete.return_value.not_.is_.return_value.execute.side_effect = Exception("Cleaning failed")
        
        sample_data = [
            {
                'title': 'Test Competition',
                'description': 'Test description',
                'organizer': 'Test Organizer',
                'poster_url': 'https://example.com/poster.jpg',
                'registration_url': 'https://example.com/register',
                'participant': 'Mahasiswa',
                'location': 'Jakarta'
            }
        ]
        
        # Call insert_lomba_rows with clean_first=True and expect exception
        with self.assertRaises(Exception) as context:
            self.db_client.insert_lomba_rows(sample_data, clean_first=True)
        
        # Verify error message indicates cleaning failure prevented insertion
        self.assertIn("Cannot proceed with data insertion due to cleaning failure", str(context.exception))

    def test_insert_lomba_rows_success_after_cleaning(self):
        """Test successful insertion after successful cleaning"""
        # Mock successful cleaning
        mock_clean_response = MagicMock()
        mock_clean_response.status_code = 200
        mock_clean_response.data = []
        mock_clean_response.error = None
        
        # Mock successful insertion
        mock_insert_response = MagicMock()
        mock_insert_response.data = [{'id': '1'}]
        mock_insert_response.error = None
        
        self.mock_supabase_client.table.return_value.delete.return_value.not_.is_.return_value.execute.return_value = mock_clean_response
        self.mock_supabase_client.table.return_value.insert.return_value.execute.return_value = mock_insert_response
        
        sample_data = [
            {
                'title': 'Test Competition',
                'description': 'Test description',
                'organizer': 'Test Organizer',
                'poster_url': 'https://example.com/poster.jpg',
                'registration_url': 'https://example.com/register',
                'participant': 'Mahasiswa',
                'location': 'Jakarta'
            }
        ]
        
        # Call insert_lomba_rows
        result = self.db_client.insert_lomba_rows(sample_data, clean_first=True)
        
        # Verify successful result
        self.assertEqual(result, 1)
        
        # Verify both cleaning and insertion were called
        self.mock_supabase_client.table.assert_any_call('lomba')
        
    def test_insert_lomba_rows_skip_cleaning(self):
        """Test insertion without cleaning when clean_first=False"""
        # Mock successful insertion
        mock_insert_response = MagicMock()
        mock_insert_response.data = [{'id': '1'}]
        mock_insert_response.error = None
        
        self.mock_supabase_client.table.return_value.insert.return_value.execute.return_value = mock_insert_response
        
        sample_data = [
            {
                'title': 'Test Competition',
                'description': 'Test description',
                'organizer': 'Test Organizer',
                'poster_url': 'https://example.com/poster.jpg',
                'registration_url': 'https://example.com/register',
                'participant': 'Mahasiswa',
                'location': 'Jakarta'
            }
        ]
        
        # Call insert_lomba_rows with clean_first=False
        result = self.db_client.insert_lomba_rows(sample_data, clean_first=False)
        
        # Verify successful result
        self.assertEqual(result, 1)
        
        # Verify delete was NOT called (no cleaning)
        self.mock_supabase_client.table.return_value.delete.assert_not_called()


if __name__ == '__main__':
    unittest.main()
