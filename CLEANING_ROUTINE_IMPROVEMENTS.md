# Cleaning Routine Improvements

## Overview

The cleaning routine in the database client (`scraper/core/db.py`) has been improved to provide robust error handling and prevent the scraper from continuing with stale data.

## Changes Made

### 1. Validated Delete Query
- **Before**: Used a faulty query with a fake UUID: `.neq('id', '00000000-0000-0000-0000-000000000000')`
- **After**: Uses a validated delete call: `.not_.is_('id', 'null')`
- **Reason**: The new approach is safer and more reliable for deleting all records

### 2. Comprehensive Logging
The cleaning routine now logs detailed response information:
- `response.status_code`
- `response.data`
- `response.error`

This provides better visibility into what's happening during the cleaning process.

### 3. Robust Error Handling with Early Exit
- **Before**: Returned `False` on errors, allowing scraper to continue
- **After**: Raises exceptions to stop execution immediately
- **Behavior**: When cleaning fails, the scraper cannot continue with stale data

#### Error Scenarios Handled:
1. **Supabase API Errors**: When `response.error` is not None
2. **HTTP Status Errors**: When `response.status_code >= 400`
3. **Network/Connection Errors**: Any exception during the delete operation

### 4. Updated Exception Propagation
The `insert_lomba_rows` method now properly handles cleaning failures:
- Catches exceptions from `clean_lomba_table()`
- Re-raises with clear error messaging
- Prevents data insertion when cleaning fails

## Method Signatures

### `clean_lomba_table()`
```python
def clean_lomba_table(self) -> bool:
    """
    Clean all existing data from the lomba table.
    
    Returns:
        True if successful, False otherwise
        
    Raises:
        Exception: If cleaning fails and should stop scraper execution
    """
```

### `insert_lomba_rows()`
```python
def insert_lomba_rows(self, rows: List[dict], clean_first: bool = True) -> int:
    """
    Insert lomba rows with cleaning and deduplication.
    
    Args:
        rows: List of dictionaries representing lomba records
        clean_first: Whether to clean the table before insertion
    
    Returns:
        Total number of rows processed
        
    Raises:
        ValueError: If rows list is empty or invalid
        Exception: If the operation fails after all retries
    """
```

## Testing

New comprehensive tests have been added in `tests/test_db_client.py` to verify:
- Successful table cleaning with proper logging
- Error handling for Supabase API errors
- Error handling for HTTP status errors
- Error handling for network exceptions
- Proper exception propagation in insertion workflow
- Functionality when cleaning is skipped (`clean_first=False`)

## Usage

The cleaning routine changes are backward compatible. Existing code will work the same way, but with improved error handling:

```python
# This will now raise exceptions if cleaning fails
db_client = SupabaseDBClient()
rows_processed = db_client.insert_lomba_rows(scraped_data)

# To skip cleaning (if needed)
rows_processed = db_client.insert_lomba_rows(scraped_data, clean_first=False)
```

## Benefits

1. **Data Integrity**: Prevents scraper from continuing with stale data
2. **Better Debugging**: Detailed logging helps identify issues quickly
3. **Fail Fast**: Early detection and stopping of problematic workflows
4. **Reliable Operations**: Validated delete queries are more robust
5. **Clear Error Messages**: Descriptive exceptions help with troubleshooting
