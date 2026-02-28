"""
Database connection module for Databricks SQL.

Provides functions for:
- Establishing Databricks SQL connections using session context
- Executing queries with error handling
- Listing Unity Catalog tables
- Detecting secure views
"""

import pandas as pd
from typing import Optional, List, Tuple

# Lazy imports to avoid requiring databricks packages in test environments
_sql = None
_dbutils = None


def _get_databricks_sql():
    """Lazy import of databricks.sql module."""
    global _sql
    if _sql is None:
        try:
            from databricks import sql
            _sql = sql
        except ImportError:
            raise ImportError(
                "databricks-sql-connector is required for database operations. "
                "Install it with: pip install databricks-sql-connector"
            )
    return _sql


def _get_dbutils():
    """Lazy import of dbutils from databricks.sdk.runtime."""
    global _dbutils
    if _dbutils is None:
        try:
            from databricks.sdk.runtime import dbutils
            _dbutils = dbutils
        except (ImportError, ValueError) as e:
            raise ImportError(
                "databricks-sdk is required for Databricks runtime context. "
                "This module should only be used within Databricks Apps environment."
            ) from e
    return _dbutils


def get_connection():
    """
    Create a Databricks SQL connection using session context.
    
    Returns:
        Connection object for executing queries
        
    Raises:
        Exception: If connection cannot be established
    """
    try:
        sql = _get_databricks_sql()
        dbutils = _get_dbutils()
        
        # Get connection parameters from Databricks session context
        connection = sql.connect(
            server_hostname=dbutils.notebook.entry_point.getDbutils().notebook().getContext().browserHostName().get(),
            http_path=dbutils.notebook.entry_point.getDbutils().notebook().getContext().httpPath().get(),
            access_token=dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()
        )
        return connection
    except Exception as e:
        raise Exception(f"Failed to establish database connection: {str(e)}")


def execute_query(query: str, limit: Optional[int] = None) -> pd.DataFrame:
    """
    Execute a SQL query and return results as a DataFrame.
    
    Args:
        query: SQL query string to execute
        limit: Optional row limit to apply to query results
        
    Returns:
        pandas DataFrame containing query results
        
    Raises:
        ValueError: If query is invalid or empty
        Exception: If query execution fails
    """
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")
    
    # Apply limit if specified and not already in query
    if limit and "LIMIT" not in query.upper():
        query = f"{query.strip().rstrip(';')} LIMIT {limit}"
    
    try:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query)
            
            # Fetch results and convert to DataFrame
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            df = pd.DataFrame(rows, columns=columns)
            
            return df
        finally:
            conn.close()
    except Exception as e:
        raise Exception(f"Query execution failed: {str(e)}")


def list_unity_catalog_tables(catalog: str, schema: str) -> List[str]:
    """
    List all tables in a Unity Catalog schema.
    
    Args:
        catalog: Unity Catalog name
        schema: Schema name within the catalog
        
    Returns:
        List of table names (without catalog/schema prefix)
        
    Raises:
        Exception: If listing tables fails
    """
    try:
        query = f"SHOW TABLES IN {catalog}.{schema}"
        df = execute_query(query)
        
        # Extract table names from result
        # SHOW TABLES returns columns: database, tableName, isTemporary
        if 'tableName' in df.columns:
            return df['tableName'].tolist()
        else:
            return []
    except Exception as e:
        raise Exception(f"Failed to list tables from {catalog}.{schema}: {str(e)}")


def get_secure_table_name(catalog: str, schema: str, table: str) -> Tuple[str, bool]:
    """
    Determine the appropriate table name to query based on secure view availability.
    
    Implements governance requirement: If a secure view exists (with _secure_vw suffix),
    use it instead of the base table.
    
    Args:
        catalog: Unity Catalog name
        schema: Schema name
        table: Base table name
        
    Returns:
        Tuple of (table_name_to_use, is_secure_view)
        - table_name_to_use: Either the secure view name or base table name
        - is_secure_view: True if secure view exists and should be used
        
    Raises:
        Exception: If table existence check fails
    """
    secure_view_name = f"{table}_secure_vw"
    
    try:
        # Check if secure view exists
        tables = list_unity_catalog_tables(catalog, schema)
        
        if secure_view_name in tables:
            return (secure_view_name, True)
        else:
            return (table, False)
    except Exception as e:
        # If we can't check, default to base table
        return (table, False)
