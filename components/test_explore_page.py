"""
Unit tests for explore page component.

Tests:
- Filter rendering and generation
- WHERE clause building
- Date range filter logic
- Categorical filter logic
- Numeric range filter logic
- Download functionality
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date
import pandas as pd
from components.explore_page import (
    _build_where_clause,
    _render_date_range_filter,
    _render_categorical_filter,
    _render_numeric_range_filter,
)
from components.schema_introspector import SchemaInfo


class TestBuildWhereClause:
    """Test WHERE clause building from filters."""
    
    def test_empty_filters(self):
        """Test that empty filters produce empty WHERE clause."""
        schema_info = SchemaInfo()
        filters = {}
        
        result = _build_where_clause(filters, schema_info)
        
        assert result == ""
    
    def test_date_range_filter(self):
        """Test date range filter produces correct SQL."""
        schema_info = SchemaInfo()
        schema_info.time_columns = ['event_date']
        
        filters = {
            'event_date': (date(2024, 1, 1), date(2024, 12, 31))
        }
        
        result = _build_where_clause(filters, schema_info)
        
        assert "event_date >= '2024-01-01'" in result
        assert "event_date <= '2024-12-31'" in result
        assert " AND " in result
    
    def test_categorical_filter(self):
        """Test categorical filter produces correct SQL."""
        schema_info = SchemaInfo()
        schema_info.categorical_columns = ['status']
        
        filters = {
            'status': ['active', 'pending']
        }
        
        result = _build_where_clause(filters, schema_info)
        
        assert "status IN ('active', 'pending')" in result
    
    def test_categorical_filter_with_quotes(self):
        """Test categorical filter escapes single quotes."""
        schema_info = SchemaInfo()
        schema_info.categorical_columns = ['name']
        
        filters = {
            'name': ["O'Brien", "D'Angelo"]
        }
        
        result = _build_where_clause(filters, schema_info)
        
        assert "name IN ('O''Brien', 'D''Angelo')" in result
    
    def test_numeric_range_filter(self):
        """Test numeric range filter produces correct SQL."""
        schema_info = SchemaInfo()
        schema_info.numeric_columns = ['temperature']
        
        filters = {
            'temperature': (20.0, 80.0)
        }
        
        result = _build_where_clause(filters, schema_info)
        
        assert "temperature >= 20.0" in result
        assert "temperature <= 80.0" in result
        assert " AND " in result
    
    def test_multiple_filters(self):
        """Test multiple filters are combined with AND."""
        schema_info = SchemaInfo()
        schema_info.time_columns = ['event_date']
        schema_info.categorical_columns = ['status']
        schema_info.numeric_columns = ['temperature']
        
        filters = {
            'event_date': (date(2024, 1, 1), date(2024, 12, 31)),
            'status': ['active'],
            'temperature': (20.0, 80.0)
        }
        
        result = _build_where_clause(filters, schema_info)
        
        # Should contain all conditions
        assert "event_date >= '2024-01-01'" in result
        assert "event_date <= '2024-12-31'" in result
        assert "status IN ('active')" in result
        assert "temperature >= 20.0" in result
        assert "temperature <= 80.0" in result
        
        # Should have multiple AND operators
        assert result.count(" AND ") >= 4
    
    def test_none_filter_values_ignored(self):
        """Test that None filter values are ignored."""
        schema_info = SchemaInfo()
        schema_info.categorical_columns = ['status']
        schema_info.numeric_columns = ['temperature']
        
        filters = {
            'status': None,
            'temperature': None
        }
        
        result = _build_where_clause(filters, schema_info)
        
        assert result == ""
    
    def test_empty_list_filter_ignored(self):
        """Test that empty list filters are ignored."""
        schema_info = SchemaInfo()
        schema_info.categorical_columns = ['status']
        
        filters = {
            'status': []
        }
        
        result = _build_where_clause(filters, schema_info)
        
        assert result == ""


class TestDateRangeFilter:
    """Test date range filter rendering."""
    
    @patch('components.explore_page.execute_query')
    @patch('components.explore_page.validate_query')
    @patch('streamlit.date_input')
    def test_date_range_filter_returns_none_when_unchanged(
        self, mock_date_input, mock_validate, mock_execute
    ):
        """Test that date filter returns None when user doesn't change range."""
        # Mock query results
        mock_validate.return_value = ("SELECT ...", False)
        mock_execute.return_value = pd.DataFrame({
            'min_date': [pd.Timestamp('2024-01-01')],
            'max_date': [pd.Timestamp('2024-12-31')]
        })
        
        # Mock user selecting the same range (no change)
        mock_date_input.return_value = (date(2024, 1, 1), date(2024, 12, 31))
        
        result = _render_date_range_filter('catalog', 'schema', 'table', 'event_date')
        
        assert result is None
    
    @patch('components.explore_page.execute_query')
    @patch('components.explore_page.validate_query')
    @patch('streamlit.date_input')
    def test_date_range_filter_returns_tuple_when_changed(
        self, mock_date_input, mock_validate, mock_execute
    ):
        """Test that date filter returns tuple when user changes range."""
        # Mock query results
        mock_validate.return_value = ("SELECT ...", False)
        mock_execute.return_value = pd.DataFrame({
            'min_date': [pd.Timestamp('2024-01-01')],
            'max_date': [pd.Timestamp('2024-12-31')]
        })
        
        # Mock user selecting a different range
        mock_date_input.return_value = (date(2024, 3, 1), date(2024, 9, 30))
        
        result = _render_date_range_filter('catalog', 'schema', 'table', 'event_date')
        
        assert result == (date(2024, 3, 1), date(2024, 9, 30))
    
    @patch('components.explore_page.execute_query')
    @patch('components.explore_page.validate_query')
    @patch('streamlit.warning')
    def test_date_range_filter_handles_empty_data(
        self, mock_warning, mock_validate, mock_execute
    ):
        """Test that date filter handles empty data gracefully."""
        # Mock empty query results
        mock_validate.return_value = ("SELECT ...", False)
        mock_execute.return_value = pd.DataFrame({
            'min_date': [pd.NaT],
            'max_date': [pd.NaT]
        })
        
        result = _render_date_range_filter('catalog', 'schema', 'table', 'event_date')
        
        assert result is None


class TestCategoricalFilter:
    """Test categorical filter rendering."""
    
    @patch('components.explore_page.execute_query')
    @patch('components.explore_page.validate_query')
    @patch('streamlit.multiselect')
    def test_categorical_filter_returns_none_when_empty(
        self, mock_multiselect, mock_validate, mock_execute
    ):
        """Test that categorical filter returns None when no selection."""
        # Mock query results
        mock_validate.return_value = ("SELECT ...", False)
        mock_execute.return_value = pd.DataFrame({
            'status': ['active', 'pending', 'completed'],
            'count': [100, 50, 30]
        })
        
        # Mock user selecting nothing
        mock_multiselect.return_value = []
        
        result = _render_categorical_filter('catalog', 'schema', 'table', 'status')
        
        assert result is None
    
    @patch('components.explore_page.execute_query')
    @patch('components.explore_page.validate_query')
    @patch('streamlit.multiselect')
    def test_categorical_filter_returns_list_when_selected(
        self, mock_multiselect, mock_validate, mock_execute
    ):
        """Test that categorical filter returns list when items selected."""
        # Mock query results
        mock_validate.return_value = ("SELECT ...", False)
        mock_execute.return_value = pd.DataFrame({
            'status': ['active', 'pending', 'completed'],
            'count': [100, 50, 30]
        })
        
        # Mock user selecting items
        mock_multiselect.return_value = ['active', 'pending']
        
        result = _render_categorical_filter('catalog', 'schema', 'table', 'status')
        
        assert result == ['active', 'pending']
    
    @patch('components.explore_page.execute_query')
    @patch('components.explore_page.validate_query')
    @patch('streamlit.warning')
    def test_categorical_filter_handles_empty_data(
        self, mock_warning, mock_validate, mock_execute
    ):
        """Test that categorical filter handles empty data gracefully."""
        # Mock empty query results
        mock_validate.return_value = ("SELECT ...", False)
        mock_execute.return_value = pd.DataFrame()
        
        result = _render_categorical_filter('catalog', 'schema', 'table', 'status')
        
        assert result is None


class TestNumericRangeFilter:
    """Test numeric range filter rendering."""
    
    @patch('components.explore_page.execute_query')
    @patch('components.explore_page.validate_query')
    @patch('streamlit.slider')
    def test_numeric_filter_returns_none_when_unchanged(
        self, mock_slider, mock_validate, mock_execute
    ):
        """Test that numeric filter returns None when user doesn't change range."""
        # Mock query results
        mock_validate.return_value = ("SELECT ...", False)
        mock_execute.return_value = pd.DataFrame({
            'min_val': [0.0],
            'max_val': [100.0]
        })
        
        # Mock user selecting the same range (no change)
        mock_slider.return_value = (0.0, 100.0)
        
        result = _render_numeric_range_filter('catalog', 'schema', 'table', 'temperature')
        
        assert result is None
    
    @patch('components.explore_page.execute_query')
    @patch('components.explore_page.validate_query')
    @patch('streamlit.slider')
    def test_numeric_filter_returns_tuple_when_changed(
        self, mock_slider, mock_validate, mock_execute
    ):
        """Test that numeric filter returns tuple when user changes range."""
        # Mock query results
        mock_validate.return_value = ("SELECT ...", False)
        mock_execute.return_value = pd.DataFrame({
            'min_val': [0.0],
            'max_val': [100.0]
        })
        
        # Mock user selecting a different range
        mock_slider.return_value = (20.0, 80.0)
        
        result = _render_numeric_range_filter('catalog', 'schema', 'table', 'temperature')
        
        assert result == (20.0, 80.0)
    
    @patch('components.explore_page.execute_query')
    @patch('components.explore_page.validate_query')
    def test_numeric_filter_handles_same_min_max(
        self, mock_validate, mock_execute
    ):
        """Test that numeric filter returns None when min equals max."""
        # Mock query results with same min and max
        mock_validate.return_value = ("SELECT ...", False)
        mock_execute.return_value = pd.DataFrame({
            'min_val': [50.0],
            'max_val': [50.0]
        })
        
        result = _render_numeric_range_filter('catalog', 'schema', 'table', 'temperature')
        
        assert result is None
    
    @patch('components.explore_page.execute_query')
    @patch('components.explore_page.validate_query')
    @patch('streamlit.warning')
    def test_numeric_filter_handles_empty_data(
        self, mock_warning, mock_validate, mock_execute
    ):
        """Test that numeric filter handles empty data gracefully."""
        # Mock empty query results
        mock_validate.return_value = ("SELECT ...", False)
        mock_execute.return_value = pd.DataFrame({
            'min_val': [pd.NA],
            'max_val': [pd.NA]
        })
        
        result = _render_numeric_range_filter('catalog', 'schema', 'table', 'temperature')
        
        assert result is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
