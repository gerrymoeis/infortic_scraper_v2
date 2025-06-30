# file: tests/test_infolomba_integration.py
import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import sys

# Add the parent directory to sys.path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scraper.lomba.infolomba_scraper import InfoLombaScraper
from scraper.core.db import SupabaseDBClient

class TestInfoLombaIntegration(unittest.TestCase):

    @patch('scraper.core.db.create_client')
    @patch.dict(os.environ, {'SUPABASE_URL': 'test_url', 'SUPABASE_ANON_KEY': 'test_key'})
    def test_scraper_with_mocked_supabase(self, mock_create_client):
        """Test scraper integration with mocked Supabase client"""
        # Mock the Supabase client
        mock_supabase_client = MagicMock()
        mock_create_client.return_value = mock_supabase_client
        
        # Create a mock response for the delete operation (cleaning)
        mock_delete_response = MagicMock()
        mock_delete_response.status_code = 200
        mock_delete_response.data = []
        mock_delete_response.error = None
        
        # Create a mock response for the insert operation
        mock_insert_response = MagicMock()
        mock_insert_response.data = [{'id': 1}, {'id': 2}, {'id': 3}]  # Simulate 3 inserted records
        mock_insert_response.error = None
        
        # Mock the delete operation chain for cleaning
        mock_supabase_client.table.return_value.delete.return_value.not_.is_.return_value.execute.return_value = mock_delete_response
        
        # Mock the insert operation
        mock_supabase_client.table.return_value.insert.return_value.execute.return_value = mock_insert_response
        
        # Initialize the DB client
        db_client = SupabaseDBClient(batch_size=100)
        
        # Create sample data that the scraper would return
        sample_scraped_data = [
            {
                'title': 'Test Competition 1',
                'description': 'Test description 1',
                'organizer': 'Test Organizer 1',
                'poster_url': 'https://example.com/poster1.jpg',
                'registration_url': 'https://example.com/register1',
                'participant': 'Mahasiswa',
                'location': 'Jakarta',
                'date_text': '31 Desember 2024',
                'price_text': 'Gratis',
                'source_url': 'https://infolomba.id/event/test-1'
            },
            {
                'title': 'Test Competition 2',
                'description': 'Test description 2',
                'organizer': 'Test Organizer 2',
                'poster_url': 'https://example.com/poster2.jpg',
                'registration_url': 'https://example.com/register2',
                'participant': 'Umum',
                'location': 'Bandung',
                'date_text': '15 Januari 2025',
                'price_text': 'Rp 50.000',
                'source_url': 'https://infolomba.id/event/test-2'
            },
            {
                'title': 'Test Competition 3',
                'description': 'Test description 3',
                'organizer': 'Test Organizer 3',
                'poster_url': 'https://example.com/poster3.jpg',
                'registration_url': 'https://example.com/register3',
                'participant': 'SMA/SMK',
                'location': 'Surabaya',
                'date_text': '20 Februari 2025',
                'price_text': 'Rp 25.000',
                'source_url': 'https://infolomba.id/event/test-3'
            }
        ]
        
        # Test the database insertion
        result = db_client.insert_lomba_rows(sample_scraped_data)
        
        # Assertions
        self.assertEqual(len(sample_scraped_data), 3, "Should have 3 scraped data items")
        self.assertEqual(result, 3, "Should return 3 as the number of processed rows")
        
        # Verify that both delete (cleaning) and insert operations were called
        mock_supabase_client.table.assert_called_with('lomba')
        
        # Verify delete operation was called for cleaning
        mock_supabase_client.table.return_value.delete.assert_called()
        mock_supabase_client.table.return_value.delete.return_value.not_.is_.assert_called_with('id', 'null')
        
        # Verify insert operation was called
        mock_supabase_client.table.return_value.insert.assert_called_with(sample_scraped_data)

    def test_scraper_data_structure(self):
        """Test that scraped data has the expected structure"""
        # Sample data structure that should be returned by the scraper
        expected_keys = {
            'title', 'description', 'organizer', 'poster_url', 
            'registration_url', 'participant', 'location', 
            'date_text', 'price_text', 'source_url'
        }
        
        sample_data = {
            'title': 'Test Competition',
            'description': 'Test description',
            'organizer': 'Test Organizer',
            'poster_url': 'https://example.com/poster.jpg',
            'registration_url': 'https://example.com/register',
            'participant': 'Mahasiswa',
            'location': 'Jakarta',
            'date_text': '31 Desember 2024',
            'price_text': 'Gratis',
            'source_url': 'https://infolomba.id/event/test'
        }
        
        # Check that all expected keys are present
        self.assertEqual(set(sample_data.keys()), expected_keys)
        
        # Check that all values are strings and not empty
        for key, value in sample_data.items():
            self.assertIsInstance(value, str, f"{key} should be a string")
            self.assertTrue(len(value) > 0, f"{key} should not be empty")

if __name__ == '__main__':
    unittest.main()
