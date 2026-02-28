"""
Unit tests for schema introspection module.

Tests column type detection, naming pattern matching, and caching behavior.
"""

import pytest
import pandas as pd
from unittest.mock import patch

from components.schema_introspector import (
    introspect_schema,
    SchemaInfo,
    get_primary_time_column,
    get_primary_id_column,
    get_primary_label_column,
    clear_schema_cache,
    ID_COLUMN_PATTERNS,
    LABEL_COLUMN_PATTERNS
)


@pytest.fixture
def mock_streamlit_session():
    """Mock streamlit session state."""
    with patch('components.schema_introspector.st') as mock_st:
        mock_st.session_state = {}
        yield mock_st


@pytest.fixture
def sample_schema_df():
    """Sample schema DataFrame from DESCRIBE command."""
    return pd.DataFrame({
        'col_name': [
            'timestamp',
            'asset_id',
            'machine_id',
            'failure',
            'temperature',
            'pressure',
            'status',
            'unit_count'
        ],
        'data_type': [
            'timestamp',
            'bigint',
            'string',
            'int',
            'double',
            'float',
            'string',
            'int'
        ]
    })


def test_schema_info_to_dict():
    """Test SchemaInfo serialization to dictionary."""
    schema = SchemaInfo()
    schema.time_columns = ['timestamp']
    schema.id_columns = ['asset_id']
    schema.label_columns = ['failure']
    schema.categorical_columns = ['status']
    schema.numeric_columns = ['temperature']
    schema.all_columns = ['timestamp', 'asset_id', 'failure', 'status', 'temperature']
    schema.column_types = {'timestamp': 'timestamp', 'asset_id': 'bigint'}
    
    result = schema.to_dict()
    
    assert result['time_columns'] == ['timestamp']
    assert result['id_columns'] == ['asset_id']
    assert result['label_columns'] == ['failure']
    assert result['categorical_columns'] == ['status']
    assert result['numeric_columns'] == ['temperature']
    assert len(result['all_columns']) == 5


def test_schema_info_from_dict():
    """Test SchemaInfo deserialization from dictionary."""
    data = {
        'time_columns': ['timestamp'],
        'id_columns': ['asset_id'],
        'label_columns': ['failure'],
        'categorical_columns': ['status'],
        'numeric_columns': ['temperature'],
        'all_columns': ['timestamp', 'asset_id'],
        'column_types': {'timestamp': 'timestamp'}
    }
    
    schema = SchemaInfo.from_dict(data)
    
    assert schema.time_columns == ['timestamp']
    assert schema.id_columns == ['asset_id']
    assert schema.label_columns == ['failure']
    assert schema.categorical_columns == ['status']
    assert schema.numeric_columns == ['temperature']


@patch('components.schema_introspector.execute_query')
def test_introspect_schema_detects_time_columns(mock_execute, mock_streamlit_session, sample_schema_df):
    """Test that time columns are detected based on data types."""
    mock_execute.return_value = sample_schema_df
    
    result = introspect_schema('catalog', 'schema', 'table', use_cache=False)
    
    assert 'timestamp' in result.time_columns
    assert len(result.time_columns) == 1


@patch('components.schema_introspector.execute_query')
def test_introspect_schema_detects_id_columns(mock_execute, mock_streamlit_session, sample_schema_df):
    """Test that ID columns are detected based on naming patterns."""
    mock_execute.return_value = sample_schema_df
    
    result = introspect_schema('catalog', 'schema', 'table', use_cache=False)
    
    assert 'asset_id' in result.id_columns
    assert 'machine_id' in result.id_columns
    assert len(result.id_columns) == 2


@patch('components.schema_introspector.execute_query')
def test_introspect_schema_detects_label_columns(mock_execute, mock_streamlit_session, sample_schema_df):
    """Test that label columns are detected based on naming patterns."""
    mock_execute.return_value = sample_schema_df
    
    result = introspect_schema('catalog', 'schema', 'table', use_cache=False)
    
    assert 'failure' in result.label_columns
    assert len(result.label_columns) == 1


@patch('components.schema_introspector.execute_query')
def test_introspect_schema_detects_numeric_columns(mock_execute, mock_streamlit_session, sample_schema_df):
    """Test that numeric columns are classified correctly."""
    mock_execute.return_value = sample_schema_df
    
    result = introspect_schema('catalog', 'schema', 'table', use_cache=False)
    
    # Should detect temperature (double), pressure (float), failure (int), unit_count (int), asset_id (bigint)
    assert 'temperature' in result.numeric_columns
    assert 'pressure' in result.numeric_columns
    assert 'failure' in result.numeric_columns
    assert 'unit_count' in result.numeric_columns
    assert 'asset_id' in result.numeric_columns


@patch('components.schema_introspector.execute_query')
def test_introspect_schema_detects_categorical_columns(mock_execute, mock_streamlit_session, sample_schema_df):
    """Test that categorical columns are classified correctly."""
    mock_execute.return_value = sample_schema_df
    
    result = introspect_schema('catalog', 'schema', 'table', use_cache=False)
    
    assert 'status' in result.categorical_columns
    assert 'machine_id' in result.categorical_columns


@patch('components.schema_introspector.execute_query')
def test_introspect_schema_caches_results(mock_execute, mock_streamlit_session, sample_schema_df):
    """Test that schema introspection results are cached in session state."""
    mock_execute.return_value = sample_schema_df
    
    # First call should execute query
    result1 = introspect_schema('catalog', 'schema', 'table', use_cache=True)
    assert mock_execute.call_count == 1
    
    # Second call should use cache
    result2 = introspect_schema('catalog', 'schema', 'table', use_cache=True)
    assert mock_execute.call_count == 1  # Should not call again
    
    # Results should be the same
    assert result1.time_columns == result2.time_columns
    assert result1.id_columns == result2.id_columns


@patch('components.schema_introspector.execute_query')
def test_introspect_schema_bypasses_cache_when_disabled(mock_execute, mock_streamlit_session, sample_schema_df):
    """Test that cache can be bypassed with use_cache=False."""
    mock_execute.return_value = sample_schema_df
    
    # First call
    introspect_schema('catalog', 'schema', 'table', use_cache=False)
    assert mock_execute.call_count == 1
    
    # Second call with use_cache=False should execute query again
    introspect_schema('catalog', 'schema', 'table', use_cache=False)
    assert mock_execute.call_count == 2


@patch('components.schema_introspector.execute_query')
def test_introspect_schema_handles_metadata_rows(mock_execute, mock_streamlit_session):
    """Test that metadata rows (starting with #) are skipped."""
    df = pd.DataFrame({
        'col_name': ['timestamp', '# Partition Information', '', 'asset_id'],
        'data_type': ['timestamp', '', '', 'bigint']
    })
    mock_execute.return_value = df
    
    result = introspect_schema('catalog', 'schema', 'table', use_cache=False)
    
    # Should only include actual columns, not metadata rows
    assert len(result.all_columns) == 2
    assert 'timestamp' in result.all_columns
    assert 'asset_id' in result.all_columns


@patch('components.schema_introspector.execute_query')
def test_introspect_schema_raises_on_error(mock_execute, mock_streamlit_session):
    """Test that schema introspection raises exception on query failure."""
    mock_execute.side_effect = Exception("Database error")
    
    with pytest.raises(Exception) as exc_info:
        introspect_schema('catalog', 'schema', 'table', use_cache=False)
    
    assert "Schema introspection failed" in str(exc_info.value)


def test_get_primary_time_column():
    """Test getting primary time column from schema info."""
    schema = SchemaInfo()
    schema.time_columns = ['timestamp', 'created_at']
    
    result = get_primary_time_column(schema)
    
    assert result == 'timestamp'


def test_get_primary_time_column_returns_none_when_empty():
    """Test that None is returned when no time columns exist."""
    schema = SchemaInfo()
    schema.time_columns = []
    
    result = get_primary_time_column(schema)
    
    assert result is None


def test_get_primary_id_column():
    """Test getting primary ID column from schema info."""
    schema = SchemaInfo()
    schema.id_columns = ['asset_id', 'machine_id']
    
    result = get_primary_id_column(schema)
    
    assert result == 'asset_id'


def test_get_primary_id_column_returns_none_when_empty():
    """Test that None is returned when no ID columns exist."""
    schema = SchemaInfo()
    schema.id_columns = []
    
    result = get_primary_id_column(schema)
    
    assert result is None


def test_get_primary_label_column():
    """Test getting primary label column from schema info."""
    schema = SchemaInfo()
    schema.label_columns = ['failure', 'target']
    
    result = get_primary_label_column(schema)
    
    assert result == 'failure'


def test_get_primary_label_column_returns_none_when_empty():
    """Test that None is returned when no label columns exist."""
    schema = SchemaInfo()
    schema.label_columns = []
    
    result = get_primary_label_column(schema)
    
    assert result is None


def test_clear_schema_cache_specific(mock_streamlit_session):
    """Test clearing specific schema cache entry."""
    # Add cache entries
    mock_streamlit_session.session_state['schema_info_cat1_sch1_tbl1'] = {}
    mock_streamlit_session.session_state['schema_info_cat2_sch2_tbl2'] = {}
    
    clear_schema_cache('cat1', 'sch1', 'tbl1')
    
    assert 'schema_info_cat1_sch1_tbl1' not in mock_streamlit_session.session_state
    assert 'schema_info_cat2_sch2_tbl2' in mock_streamlit_session.session_state


def test_clear_schema_cache_all(mock_streamlit_session):
    """Test clearing all schema cache entries."""
    # Add cache entries
    mock_streamlit_session.session_state['schema_info_cat1_sch1_tbl1'] = {}
    mock_streamlit_session.session_state['schema_info_cat2_sch2_tbl2'] = {}
    mock_streamlit_session.session_state['other_key'] = {}
    
    clear_schema_cache()
    
    assert 'schema_info_cat1_sch1_tbl1' not in mock_streamlit_session.session_state
    assert 'schema_info_cat2_sch2_tbl2' not in mock_streamlit_session.session_state
    assert 'other_key' in mock_streamlit_session.session_state


@patch('components.schema_introspector.execute_query')
def test_introspect_schema_detects_all_id_patterns(mock_execute, mock_streamlit_session):
    """Test that all ID naming patterns are detected."""
    df = pd.DataFrame({
        'col_name': ['asset_id', 'machine_id', 'unit', 'engine_id', 'other_col'],
        'data_type': ['bigint', 'bigint', 'int', 'string', 'string']
    })
    mock_execute.return_value = df
    
    result = introspect_schema('catalog', 'schema', 'table', use_cache=False)
    
    assert 'asset_id' in result.id_columns
    assert 'machine_id' in result.id_columns
    assert 'unit' in result.id_columns
    assert 'engine_id' in result.id_columns
    assert 'other_col' not in result.id_columns


@patch('components.schema_introspector.execute_query')
def test_introspect_schema_detects_all_label_patterns(mock_execute, mock_streamlit_session):
    """Test that all label naming patterns are detected."""
    df = pd.DataFrame({
        'col_name': ['failure', 'fault', 'target', 'y', 'label', 'other_col'],
        'data_type': ['int', 'int', 'int', 'int', 'int', 'int']
    })
    mock_execute.return_value = df
    
    result = introspect_schema('catalog', 'schema', 'table', use_cache=False)
    
    assert 'failure' in result.label_columns
    assert 'fault' in result.label_columns
    assert 'target' in result.label_columns
    assert 'y' in result.label_columns
    assert 'label' in result.label_columns
    assert 'other_col' not in result.label_columns


@patch('components.schema_introspector.execute_query')
def test_introspect_schema_case_insensitive_pattern_matching(mock_execute, mock_streamlit_session):
    """Test that pattern matching is case-insensitive."""
    df = pd.DataFrame({
        'col_name': ['Asset_ID', 'MACHINE_ID', 'Failure', 'TARGET'],
        'data_type': ['bigint', 'bigint', 'int', 'int']
    })
    mock_execute.return_value = df
    
    result = introspect_schema('catalog', 'schema', 'table', use_cache=False)
    
    assert 'Asset_ID' in result.id_columns
    assert 'MACHINE_ID' in result.id_columns
    assert 'Failure' in result.label_columns
    assert 'TARGET' in result.label_columns
