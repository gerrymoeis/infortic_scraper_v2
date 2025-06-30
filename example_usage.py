#!/usr/bin/env python3
"""
Example usage of the SupabaseDBClient for inserting lomba data.

This script demonstrates how to use the new Supabase integration
to insert/update lomba records with retry logic and bulk processing.
"""

import os
from dotenv import load_dotenv
from scraper.core.db import SupabaseDBClient

# Load environment variables
load_dotenv()

def main():
    """
    Example usage of the SupabaseDBClient.
    """
    
    # Initialize the client with custom batch size
    db_client = SupabaseDBClient(batch_size=500)
    
    # Test connection
    if not db_client.test_connection():
        print("Failed to connect to Supabase. Please check your credentials.")
        return
    
    # Example lomba data
    sample_lomba_data = [
        {
            "title": "Lomba Coding Nasional 2024",
            "url": "https://example.com/lomba1",
            "description": "Lomba coding untuk mahasiswa se-Indonesia",
            "deadline": "2024-12-31",
            "organizer": "Universitas Indonesia",
            "category": "programming",
            "prize": "Rp 10,000,000",
            "status": "open"
        },
        {
            "title": "Hackathon Teknologi Finansial",
            "url": "https://example.com/lomba2", 
            "description": "Kompetisi pengembangan aplikasi fintech",
            "deadline": "2024-11-30",
            "organizer": "Bank Indonesia",
            "category": "hackathon",
            "prize": "Rp 25,000,000",
            "status": "open"
        },
        {
            "title": "Lomba Desain UI/UX",
            "url": "https://example.com/lomba3",
            "description": "Kompetisi desain antarmuka pengguna",
            "deadline": "2024-12-15",
            "organizer": "Google Developer Group",
            "category": "design",
            "prize": "Rp 5,000,000",
            "status": "open"
        }
    ]
    
    try:
        # Insert the data
        print(f"Inserting {len(sample_lomba_data)} lomba records...")
        processed_count = db_client.insert_lomba_rows(sample_lomba_data)
        print(f"Successfully processed {processed_count} records")
        
        # Test with duplicate data (should update existing records)
        print("\nTesting upsert with duplicate URLs...")
        duplicate_data = [
            {
                "title": "Lomba Coding Nasional 2024 - Updated",
                "url": "https://example.com/lomba1",  # Same URL as first record
                "description": "Updated description for coding competition",
                "deadline": "2024-12-31",
                "organizer": "Universitas Indonesia",
                "category": "programming",
                "prize": "Rp 15,000,000",  # Updated prize
                "status": "open"
            }
        ]
        
        processed_count = db_client.insert_lomba_rows(duplicate_data)
        print(f"Successfully processed {processed_count} records (should be update)")
        
    except Exception as e:
        print(f"Error occurred: {e}")

if __name__ == "__main__":
    main()
