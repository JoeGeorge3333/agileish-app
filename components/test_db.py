"""
Unit tests for database connection module.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from components.db import (
    get_connection,
    execute_query,
    list_unity_catalog_tables,
    get_secure_table_name
)


class TestDatabaseConnection:
    """Tests for database connection functionality."""
    
    @patch('components.db._get_databricks_sql')
    @patch('components.db._get_dbutils')
    def test_get_connection_success(self, mock_get_dbutils, mock_get_sql):
        """Test successful database connection."""
        # Setup mocks for sql module
        mock_sql = Mock()
        mock_connection = Mock()
        mock_sql.connect.return_value = mock_connection
        mock_get_sql.return_value = mock_sql
        
        # Setup mocks for dbutils
        mock_dbutils = Mock()
        mock_context = Mock()
        mock_context.browserHostName().get.return_value = "test-host"
        mock_context.httpPath().get.return_value = "/sql/test"
        mock_context.apiToken().get.return_value = "test-token"
        mock_dbutils.notebook.entry_point.getDbutils().notebook().getContext.return_value = mock_context
        mock_get_dbutils.return_value = mock_dbutils
        
        # Execute
        result = get_connection()
        
        # Verify
        assert result == mock_connection
        mock_sql.connect.assert_called_once()
    
    @patch('components.db._get_databricks_sql')
    @patch('components.db._get_dbutils')
    def test_get_connection_failure(self, mock_get_dbutils, mock_get_sql):
        """Test connection failure handling."""
        mock_sql = Mock()
        mock_sql.connect.side_effect = Exception("Connection failed")
        mock_get_sql.return_value = mock_sql
        
        mock_dbutils = Mock()
        mock_get_dbutils.return_value = mock_dbutils
        
        with pytest.raises(Exception) as exc_info:
            get_connection()
        
        assert "Failed to establish database connection" in str(exc_info.value)


class TestQueryExecution:
    """Tests for query execution functionality."""
    
    @patch('components.db.get_connection')
    def test_execute_query_success(self, mock_get_connection):
        """Test successful query execution."""
        # Setup mocks
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.description = [('col1',), ('col2',)]
        mock_cursor.fetchall.return_value = [('val1', 'val2'), ('val3', 'val4')]
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn
        
        # Execute
        result = execute_query("SELECT * FROM test_table")
        
        # Verify
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert list(result.columns) == ['col1', 'col2']
        mock_conn.close.assert_called_once()
    
    @patch('components.db.get_connection')
    def test_execute_query_with_limit(self, mock_get_connection):
        """Test query execution with limit applied."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.description = [('col1',)]
        mock_cursor.fetchall.return_value = [('val1',)]
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn
        
        # Execute
        execute_query("SELECT * FROM test_table", limit=10)
        
        # Verify limit was added
        call_args = mock_cursor.execute.call_args[0][0]
        assert "LIMIT 10" in call_args
    
    def test_execute_query_empty_query(self):
        """Test that empty query raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            execute_query("")
        
        assert "Query cannot be empty" in str(exc_info.value)
    
    @patch('components.db.get_connection')
    def test_execute_query_failure(self, mock_get_connection):
        """Test query execution failure handling."""
        mock_conn = Mock()
        mock_conn.cursor.side_effect = Exception("Query failed")
        mock_get_connection.return_value = mock_conn
        
        with pytest.raises(Exception) as exc_info:
            execute_query("SELECT * FROM test_table")
        
        assert "Query execution failed" in str(exc_info.value)


class TestUnityTableListing:
    """Tests for Unity Catalog table listing."""
    
    @patch('components.db.execute_query')
    def test_list_unity_catalog_tables_success(self, mock_execute_query):
        """Test successful table listing."""
        mock_df = pd.DataFrame({
            'database': ['test_schema', 'test_schema'],
            'tableName': ['table1', 'table2'],
            'isTemporary': [False, False]
        })
        mock_execute_query.return_value = mock_df
        
        result = list_unity_catalog_tables('test_catalog', 'test_schema')
        
        assert result == ['table1', 'table2']
        mock_execute_query.assert_called_once_with('SHOW TABLES IN test_catalog.test_schema')
    
    @patch('components.db.execute_query')
    def test_list_unity_catalog_tables_empty(self, mock_execute_query):
        """Test table listing with no results."""
        mock_df = pd.DataFrame()
        mock_execute_query.return_value = mock_df
        
        result = list_unity_catalog_tables('test_catalog', 'test_schema')
        
        assert result == []


class TestSecureViewDetection:
    """Tests for secure view detection functionality."""
    
    @patch('components.db.list_unity_catalog_tables')
    def test_get_secure_table_name_with_secure_view(self, mock_list_tables):
        """Test that secure view is returned when it exists."""
        mock_list_tables.return_value = ['base_table', 'base_table_secure_vw', 'other_table']
        
        table_name, is_secure = get_secure_table_name('catalog', 'schema', 'base_table')
        
        assert table_name == 'base_table_secure_vw'
        assert is_secure is True
    
    @patch('components.db.list_unity_catalog_tables')
    def test_get_secure_table_name_without_secure_view(self, mock_list_tables):
        """Test that base table is returned when secure view doesn't exist."""
        mock_list_tables.return_value = ['base_table', 'other_table']
        
        table_name, is_secure = get_secure_table_name('catalog', 'schema', 'base_table')
        
        assert table_name == 'base_table'
        assert is_secure is False
    
    @patch('components.db.list_unity_catalog_tables')
    def test_get_secure_table_name_error_handling(self, mock_list_tables):
        """Test that base table is returned on error."""
        mock_list_tables.side_effect = Exception("Listing failed")
        
        table_name, is_secure = get_secure_table_name('catalog', 'schema', 'base_table')
        
        assert table_name == 'base_table'
        assert is_secure is False
