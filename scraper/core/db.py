"""
Database client interface for handling database operations such as insertions.
Provides a standardized way to interact with the database.
"""

from typing import List, Optional
from abc import ABC, abstractmethod
import psycopg2
import psycopg2.extras
from psycopg2 import sql
import os

from .logger import Logger


class DBClient:
    """
    Database client for handling PostgreSQL database operations.
    
    Provides methods for inserting data into a database.
    Handles connection management and error handling.
    """
    
    def __init__(self, connection_string: Optional[str] = None):
        self.logger = Logger()
        self.connection_string = connection_string or self._get_connection_string()
        self._connection: Optional[psycopg2.connection] = None
        
    def _get_connection_string(self) -> str:
        """
        Get database connection string from environment variables.
        
        Returns:
            PostgreSQL connection string
        """
        host = os.getenv('DB_HOST', 'localhost')
        port = os.getenv('DB_PORT', '5432')
        database = os.getenv('DB_NAME', 'infortic')
        user = os.getenv('DB_USER', 'postgres')
        password = os.getenv('DB_PASSWORD', '')
        
        return f"host={host} port={port} dbname={database} user={user} password={password}"
        
    def connect(self):
        """
        Establish a database connection.
        
        Returns:
            psycopg2 connection object
        """
        try:
            if self._connection is None or self._connection.closed:
                self._connection = psycopg2.connect(self.connection_string)
                self.logger.info("Database connection established")
            return self._connection
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {str(e)}")
            raise
      
    def close(self):
        """
        Close the database connection.
        """
        if self._connection and not self._connection.closed:
            self._connection.close()
            self.logger.info("Database connection closed")
      
    def insert_many(self, data: List[dict], table_name: str):
        """
        Insert multiple records into a database table.
        
        Args:
            data: List of dictionaries representing records to insert
            table_name: Name of the database table
        
        Raises:
            Exception: If the insertion fails
        """
        try:
            self.logger.info(f"Preparing to insert data into {table_name}")
            conn = self.connect()
            cur = conn.cursor()
            
            # Create a list of column names and their corresponding data values
            columns = data[0].keys()
            
            # Construct the insert statement dynamically based on columns
            query = sql.SQL("INSERT INTO {table} ({fields}) VALUES %s").format(
                table=sql.Identifier(table_name),
                fields=sql.SQL(', ').join(map(sql.Identifier, columns))
            )
            
            # Transform data into a tuple of tuples (suitable for psycopg2.extras.execute_values)
            values = [tuple(item[col] for col in columns) for item in data]
            
            # Use execute_values() to perform bulk insert
            psycopg2.extras.execute_values(cur, query, values)
            conn.commit()
            self.logger.info(f"Inserted {len(data)} records into {table_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to insert data into {table_name}: {str(e)}")
            raise
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()
                self.logger.info("Database connection closed.")

