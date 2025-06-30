#!/usr/bin/env python3
"""
Simple test script to verify Supabase client initialization.
This helps identify version compatibility issues before running the full scraper.
"""

import os
import sys
from dotenv import load_dotenv

def test_supabase_client():
    """Test Supabase client initialization."""
    print("Testing Supabase client initialization...")
    
    # Load environment variables
    load_dotenv()
    
    # Check if environment variables are set
    url = os.getenv('SUPABASE_URL')
    anon_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not url or not anon_key:
        print("❌ SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables")
        return False
    
    try:
        # Try to import and initialize Supabase client
        from supabase import create_client, Client
        print(f"✅ Supabase module imported successfully")
        
        # Create client
        client: Client = create_client(url, anon_key)
        print(f"✅ Supabase client created successfully")
        
        # Test a simple query
        response = client.table('lomba').select('*').limit(1).execute()
        print(f"✅ Test query executed successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Supabase client initialization failed: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        return False

def check_package_versions():
    """Check versions of key packages."""
    packages = ['supabase', 'httpx', 'httpcore', 'gotrue', 'postgrest-py']
    
    print("\nChecking package versions...")
    for package in packages:
        try:
            module = __import__(package.replace('-', '_'))
            version = getattr(module, '__version__', 'Unknown')
            print(f"  {package}: {version}")
        except ImportError:
            print(f"  {package}: Not installed")
        except Exception as e:
            print(f"  {package}: Error - {e}")

if __name__ == "__main__":
    print("Supabase Client Compatibility Test")
    print("=" * 40)
    
    check_package_versions()
    
    success = test_supabase_client()
    
    if success:
        print("\n✅ All tests passed! Supabase client is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Tests failed! Check the error messages above.")
        sys.exit(1)
