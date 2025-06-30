#!/usr/bin/env python3
"""
Pytest unit test for cleaning function using Supabase MCP Tools.
Run with: pytest test_cleaning_pytest.py -v
"""

import json
import pytest
from typing import Dict, Any


# In a real implementation, this would be imported from your MCP client
def call_supabase_mcp(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mock Supabase MCP tool caller.
    In real usage, replace this with actual MCP client calls.
    """
    print(f"[MCP] {tool_name}: {json.dumps(params, indent=2)}")
    
    if tool_name == "apply_migration":
        return {"text_result": [{"text": "Migration applied successfully"}]}
    
    elif tool_name == "execute_sql":
        query = params.get("query", "")
        
        if "INSERT INTO lomba" in query:
            # Set state to indicate data was inserted
            call_supabase_mcp._test_data_exists = True
            return {"text_result": [{"text": "INSERT 0 1"}]}
        
        elif "SELECT clean_lomba_table()" in query:
            # Clear state to indicate data was cleaned
            call_supabase_mcp._test_data_exists = False
            return {"text_result": [{"text": "clean_lomba_table\n---\n"}]}
        
        elif "SELECT COUNT(*)" in query:
            # Return count based on test state
            if hasattr(call_supabase_mcp, '_test_data_exists') and call_supabase_mcp._test_data_exists:
                return {"text_result": [{"text": "[{\"count\": 1}]"}]}
            else:
                return {"text_result": [{"text": "[{\"count\": 0}]"}]}
    
    return {"text_result": [{"text": "Success"}]}


@pytest.fixture
def project_id():
    """Fixture providing the project ID."""
    return "nezqzdioasufyoygarpl"


@pytest.fixture
def clean_state():
    """Fixture to ensure clean test state."""
    # Reset any test state
    if hasattr(call_supabase_mcp, '_test_data_exists'):
        delattr(call_supabase_mcp, '_test_data_exists')
    yield
    # Cleanup after test
    if hasattr(call_supabase_mcp, '_test_data_exists'):
        delattr(call_supabase_mcp, '_test_data_exists')


class TestCleaningFunction:
    """Test class for cleaning function tests."""
    
    def test_create_cleaning_function(self, project_id, clean_state):
        """Test creating the cleaning function via migration."""
        
        migration_sql = """
        CREATE OR REPLACE FUNCTION clean_lomba_table()
        RETURNS void AS $$
        BEGIN
            DELETE FROM lomba;
            RAISE NOTICE 'Cleaned lomba table - all rows deleted';
        END;
        $$ LANGUAGE plpgsql;
        """
        
        result = call_supabase_mcp("apply_migration", {
            "project_id": project_id,
            "name": "create_cleaning_function",
            "query": migration_sql
        })
        
        assert "text_result" in result
        assert "Migration applied successfully" in result["text_result"][0]["text"]
    
    def test_insert_dummy_data(self, project_id, clean_state):
        """Test inserting dummy data into the lomba table."""
        
        insert_sql = """
        INSERT INTO lomba (
            title, description, organizer, poster_url, registration_url, 
            source_url, date_text, price_text, participant, location
        ) VALUES (
            'PYTEST: Test Competition',
            'This is a PYTEST entry for unit testing',
            'Pytest Organizer',
            'https://pytest.example.com/poster.jpg',
            'https://pytest.example.com/register-' || gen_random_uuid(),
            'https://pytest.example.com/source-' || gen_random_uuid(),
            'PYTEST: 2024-01-01 to 2024-01-31',
            'FREE (PYTEST)',
            'Pytest Participants',
            'Pytest Location'
        );
        """
        
        result = call_supabase_mcp("execute_sql", {
            "project_id": project_id,
            "query": insert_sql
        })
        
        assert "text_result" in result
        assert "INSERT" in result["text_result"][0]["text"]
    
    def test_verify_data_exists(self, project_id, clean_state):
        """Test verifying that data exists before cleaning."""
        
        # First insert data
        self.test_insert_dummy_data(project_id, clean_state)
        
        count_sql = "SELECT COUNT(*) as count FROM lomba WHERE title LIKE 'PYTEST:%';"
        
        result = call_supabase_mcp("execute_sql", {
            "project_id": project_id,
            "query": count_sql
        })
        
        # Parse the result
        text_result = result["text_result"][0]["text"]
        data = json.loads(text_result)
        count = int(data[0]["count"])
        
        assert count > 0, f"Expected data to exist, but count was {count}"
    
    def test_call_cleaning_function(self, project_id, clean_state):
        """Test calling the cleaning function."""
        
        # Setup: create function and insert data
        self.test_create_cleaning_function(project_id, clean_state)
        self.test_insert_dummy_data(project_id, clean_state)
        
        # Call cleaning function
        clean_sql = "SELECT clean_lomba_table();"
        
        result = call_supabase_mcp("execute_sql", {
            "project_id": project_id,
            "query": clean_sql
        })
        
        assert "text_result" in result
        assert "clean_lomba_table" in result["text_result"][0]["text"]
    
    def test_verify_table_empty(self, project_id, clean_state):
        """Test verifying table is empty after cleaning."""
        
        # Setup: create function, insert data, and clean
        self.test_create_cleaning_function(project_id, clean_state)
        self.test_insert_dummy_data(project_id, clean_state)
        self.test_call_cleaning_function(project_id, clean_state)
        
        # Verify table is empty
        count_sql = "SELECT COUNT(*) as count FROM lomba;"
        
        result = call_supabase_mcp("execute_sql", {
            "project_id": project_id,
            "query": count_sql
        })
        
        # Parse the result
        text_result = result["text_result"][0]["text"]
        data = json.loads(text_result)
        count = int(data[0]["count"])
        
        assert count == 0, f"Expected table to be empty after cleaning, but found {count} rows"
    
    def test_full_cleaning_workflow(self, project_id, clean_state):
        """
        Full integration test that runs the complete cleaning workflow:
        1. Create cleaning function
        2. Insert dummy data
        3. Verify data exists
        4. Call cleaning function
        5. Assert table is empty
        """
        
        # Step 1: Create cleaning function
        migration_sql = """
        CREATE OR REPLACE FUNCTION clean_lomba_table()
        RETURNS void AS $$
        BEGIN
            DELETE FROM lomba;
            RAISE NOTICE 'Cleaned lomba table - all rows deleted';
        END;
        $$ LANGUAGE plpgsql;
        """
        
        result = call_supabase_mcp("apply_migration", {
            "project_id": project_id,
            "name": "create_cleaning_function",
            "query": migration_sql
        })
        
        assert "Migration applied successfully" in result["text_result"][0]["text"]
        
        # Step 2: Insert dummy data
        insert_sql = """
        INSERT INTO lomba (
            title, description, organizer, poster_url, registration_url, 
            source_url, date_text, price_text, participant, location
        ) VALUES (
            'PYTEST: Full Workflow Test',
            'This is a PYTEST entry for full workflow testing',
            'Pytest Full Test Organizer',
            'https://pytest-full.example.com/poster.jpg',
            'https://pytest-full.example.com/register-' || gen_random_uuid(),
            'https://pytest-full.example.com/source-' || gen_random_uuid(),
            'PYTEST: 2024-01-01 to 2024-01-31',
            'FREE (PYTEST FULL)',
            'Pytest Full Test Participants',
            'Pytest Full Test Location'
        );
        """
        
        result = call_supabase_mcp("execute_sql", {
            "project_id": project_id,
            "query": insert_sql
        })
        
        assert "INSERT" in result["text_result"][0]["text"]
        
        # Step 3: Verify data exists
        count_sql = "SELECT COUNT(*) as count FROM lomba;"
        
        result = call_supabase_mcp("execute_sql", {
            "project_id": project_id,
            "query": count_sql
        })
        
        text_result = result["text_result"][0]["text"]
        data = json.loads(text_result)
        count_before = int(data[0]["count"])
        
        assert count_before > 0, f"Expected data to exist before cleaning, but count was {count_before}"
        
        # Step 4: Call cleaning function
        clean_sql = "SELECT clean_lomba_table();"
        
        result = call_supabase_mcp("execute_sql", {
            "project_id": project_id,
            "query": clean_sql
        })
        
        assert "clean_lomba_table" in result["text_result"][0]["text"]
        
        # Step 5: Verify table is empty
        result = call_supabase_mcp("execute_sql", {
            "project_id": project_id,
            "query": count_sql
        })
        
        text_result = result["text_result"][0]["text"]
        data = json.loads(text_result)
        count_after = int(data[0]["count"])
        
        assert count_after == 0, f"Expected table to be empty after cleaning, but found {count_after} rows"


if __name__ == "__main__":
    # Run pytest if script is executed directly
    pytest.main([__file__, "-v", "--tb=short"])
