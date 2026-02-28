"""
Schema introspection module for detecting column types and purposes.

Provides functions for:
- Analyzing table schemas to detect column types
- Identifying time, ID, label, categorical, and numeric columns
- Caching introspection results in session state
"""

import re
import pandas as pd
import streamlit as st
from typing import Optional, List, Dict
from components.db import execute_query


# ID column patterns - refined to avoid false positives
# Matches: id, asset_id, machine_id, engine_id, unit (standalone), device_id, etc.
# Excludes: unit_count, identifier, identity, uuid, guid, hash-like fields
ID_COLUMN_PATTERNS = [
    r'^id$',              # Exact match: "id"
    r'^.+_id$',           # Suffix: anything ending with "_id" (asset_id, machine_id)
    r'^.+_sk$',           # Suffix: anything ending with "_sk" (surrogate key)
    r'^unit$',            # Exact match: "unit" (standalone)
    r'^engine$',          # Exact match: "engine" (standalone)
    r'^asset$',           # Exact match: "asset" (standalone)
    r'^machine$',         # Exact match: "machine" (standalone)
    r'^device$',          # Exact match: "device" (standalone)
]

# Patterns to EXCLUDE from ID detection (false positives)
ID_EXCLUDE_PATTERNS = [
    r'identifier',        # Contains "identifier"
    r'identity',          # Contains "identity"
    r'uuid',              # Contains "uuid"
    r'guid',              # Contains "guid"
    r'hash',              # Contains "hash"
    r'_count$',           # Ends with "_count" (e.g., unit_count)
    r'_total$',           # Ends with "_total"
    r'_sum$',             # Ends with "_sum"
]

# Label column patterns
LABEL_COLUMN_PATTERNS = [
    r'^failure$',
    r'^fault$',
    r'^target$',
    r'^y$',
    r'^label$',
]


class SchemaInfo:
    """Container for schema introspection results."""
    
    def __init__(self):
        self.time_columns: List[str] = []
        self.id_columns: List[str] = []
        self.label_columns: List[str] = []
        self.categorical_columns: List[str] = []
        self.numeric_columns: List[str] = []
        self.all_columns: List[str] = []
        self.column_types: Dict[str, str] = {}
    
    def to_dict(self) -> dict:
        """Serialize to dictionary for caching."""
        return {
            'time_columns': self.time_columns,
            'id_columns': self.id_columns,
            'label_columns': self.label_columns,
            'categorical_columns': self.categorical_columns,
            'numeric_columns': self.numeric_columns,
            'all_columns': self.all_columns,
            'column_types': self.column_types,
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'SchemaInfo':
        """Deserialize from dictionary."""
        schema = SchemaInfo()
        schema.time_columns = data.get('time_columns', [])
        schema.id_columns = data.get('id_columns', [])
        schema.label_columns = data.get('label_columns', [])
        schema.categorical_columns = data.get('categorical_columns', [])
        schema.numeric_columns = data.get('numeric_columns', [])
        schema.all_columns = data.get('all_columns', [])
        schema.column_types = data.get('column_types', {})
        return schema


def _is_id_column(col_name: str) -> bool:
    """
    Determine if a column name matches ID patterns.
    
    Uses refined heuristics to detect true identifiers while excluding
    false positives like unit_count, identifier, uuid, etc.
    
    Args:
        col_name: Column name to check (case-insensitive)
        
    Returns:
        True if column matches ID patterns and doesn't match exclude patterns
    """
    col_lower = col_name.lower()
    
    # First check exclude patterns - if any match, it's NOT an ID column
    for exclude_pattern in ID_EXCLUDE_PATTERNS:
        if re.search(exclude_pattern, col_lower):
            return False
    
    # Then check include patterns - if any match, it IS an ID column
    for pattern in ID_COLUMN_PATTERNS:
        if re.match(pattern, col_lower):
            return True
    
    return False


def _is_label_column(col_name: str) -> bool:
    """
    Determine if a column name matches label patterns.
    
    Args:
        col_name: Column name to check (case-insensitive)
        
    Returns:
        True if column matches label patterns
    """
    col_lower = col_name.lower()
    
    for pattern in LABEL_COLUMN_PATTERNS:
        if re.match(pattern, col_lower):
            return True
    
    return False


def _is_time_column(data_type: str) -> bool:
    """
    Determine if a data type represents a time/date column.
    
    Args:
        data_type: Column data type from schema
        
    Returns:
        True if data type is temporal
    """
    time_types = ['timestamp', 'date', 'datetime', 'time']
    return any(t in data_type.lower() for t in time_types)


def _is_numeric_type(data_type: str) -> bool:
    """
    Determine if a data type is numeric.
    
    Args:
        data_type: Column data type from schema
        
    Returns:
        True if data type is numeric
    """
    numeric_types = ['int', 'bigint', 'smallint', 'tinyint', 'float', 'double', 'decimal', 'numeric']
    return any(t in data_type.lower() for t in numeric_types)


def introspect_schema(
    catalog: str,
    schema: str,
    table: str,
    use_cache: bool = True
) -> SchemaInfo:
    """
    Analyze table schema and detect column types and purposes.
    
    Detects:
    - Time columns (based on data types)
    - ID columns (based on naming patterns)
    - Label columns (based on naming patterns)
    - Categorical columns (string types)
    - Numeric columns (numeric types)
    
    Args:
        catalog: Unity Catalog name
        schema: Schema name
        table: Table name
        use_cache: Whether to use cached results from session state
        
    Returns:
        SchemaInfo object with detected column classifications
        
    Raises:
        Exception: If schema introspection fails
    """
    cache_key = f"schema_info_{catalog}_{schema}_{table}"
    
    # Check cache if enabled
    if use_cache and cache_key in st.session_state:
        return SchemaInfo.from_dict(st.session_state[cache_key])
    
    try:
        # Get schema information using DESCRIBE
        query = f"DESCRIBE {catalog}.{schema}.{table}"
        df = execute_query(query)
        
        # Filter out metadata rows (starting with # or empty)
        df = df[
            (df['col_name'].notna()) &
            (~df['col_name'].str.startswith('#')) &
            (df['col_name'].str.strip() != '')
        ]
        
        schema_info = SchemaInfo()
        
        # Analyze each column
        for _, row in df.iterrows():
            col_name = row['col_name']
            data_type = row['data_type']
            
            schema_info.all_columns.append(col_name)
            schema_info.column_types[col_name] = data_type
            
            # Detect time columns
            if _is_time_column(data_type):
                schema_info.time_columns.append(col_name)
            
            # Detect ID columns
            if _is_id_column(col_name):
                schema_info.id_columns.append(col_name)
            
            # Detect label columns
            if _is_label_column(col_name):
                schema_info.label_columns.append(col_name)
            
            # Detect numeric columns
            if _is_numeric_type(data_type):
                schema_info.numeric_columns.append(col_name)
            
            # Detect categorical columns (string types that aren't IDs)
            if 'string' in data_type.lower() or 'varchar' in data_type.lower():
                schema_info.categorical_columns.append(col_name)
        
        # Cache results if enabled
        if use_cache:
            st.session_state[cache_key] = schema_info.to_dict()
        
        return schema_info
        
    except Exception as e:
        raise Exception(f"Schema introspection failed for {catalog}.{schema}.{table}: {str(e)}")


def get_primary_time_column(schema_info: SchemaInfo) -> Optional[str]:
    """
    Get the primary time column from schema info.
    
    Args:
        schema_info: SchemaInfo object
        
    Returns:
        First time column name, or None if no time columns exist
    """
    return schema_info.time_columns[0] if schema_info.time_columns else None


def get_primary_id_column(schema_info: SchemaInfo) -> Optional[str]:
    """
    Get the primary ID column from schema info.
    
    Args:
        schema_info: SchemaInfo object
        
    Returns:
        First ID column name, or None if no ID columns exist
    """
    return schema_info.id_columns[0] if schema_info.id_columns else None


def get_primary_label_column(schema_info: SchemaInfo) -> Optional[str]:
    """
    Get the primary label column from schema info.
    
    Args:
        schema_info: SchemaInfo object
        
    Returns:
        First label column name, or None if no label columns exist
    """
    return schema_info.label_columns[0] if schema_info.label_columns else None


def clear_schema_cache(catalog: Optional[str] = None, schema: Optional[str] = None, table: Optional[str] = None):
    """
    Clear schema cache from session state.
    
    Args:
        catalog: Optional catalog name to clear specific entry
        schema: Optional schema name to clear specific entry
        table: Optional table name to clear specific entry
        
    If all parameters are None, clears all schema cache entries.
    """
    if catalog and schema and table:
        # Clear specific entry
        cache_key = f"schema_info_{catalog}_{schema}_{table}"
        if cache_key in st.session_state:
            del st.session_state[cache_key]
    else:
        # Clear all schema cache entries
        keys_to_delete = [k for k in st.session_state.keys() if k.startswith('schema_info_')]
        for key in keys_to_delete:
            del st.session_state[key]
