"""
Unit tests for chart_generator module.

Tests:
- Time trend chart creation with and without time columns
- Category breakdown chart creation with and without categorical columns
- Distribution chart creation with and without numeric columns
- Fallback logic and explanations
- Data point limiting for performance
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch
from components.chart_generator import (
    Chart,
    create_time_trend_chart,
    create_category_breakdown_chart,
    create_distribution_chart,
    generate_all_charts,
    MAX_TIME_SERIES_POINTS,
    MAX_CATEGORY_VALUES
)
from components.schema_introspector import SchemaInfo


@pytest.fixture
def schema_info_full():
    """Schema info with all column types."""
    schema = SchemaInfo()
    schema.time_columns = ['timestamp']
    schema.categorical_columns = ['category', 'status']
    schema.numeric_columns = ['value', 'score']
    schema.all_columns = ['timestamp', 'category', 'status', 'value', 'score']
    return schema


@pytest.fixture
def schema_info_no_time():
    """Schema info without time columns."""
    schema = SchemaInfo()
    schema.time_columns = []
    schema.categorical_columns = ['category']
    schema.numeric_columns = ['value']
    schema.all_columns = ['category', 'value']
    return schema


@pytest.fixture
def schema_info_no_categorical():
    """Schema info without categorical columns."""
    schema = SchemaInfo()
    schema.time_columns = ['timestamp']
    schema.categorical_columns = []
    schema.numeric_columns = ['value']
    schema.all_columns = ['timestamp', 'value']
    return schema


@pytest.fixture
def schema_info_no_numeric():
    """Schema info without numeric columns."""
    schema = SchemaInfo()
    schema.time_columns = ['timestamp']
    schema.categorical_columns = ['category']
    schema.numeric_columns = []
    schema.all_columns = ['timestamp', 'category']
    return schema


class TestChart:
    """Tests for Chart class."""
    
    def test_chart_creation(self):
        """Test Chart object creation."""
        data = pd.DataFrame({'x': [1, 2, 3], 'y': [4, 5, 6]})
        chart = Chart(
            chart_type='line',
            data=data,
            title='Test Chart',
            x_column='x',
            y_column='y'
        )
        
        assert chart.chart_type == 'line'
        assert chart.title == 'Test Chart'
        assert chart.x_column == 'x'
        assert chart.y_column == 'y'
        assert chart.explanation is None
        assert len(chart.data) == 3
    
    def test_chart_with_explanation(self):
        """Test Chart with explanation for fallback."""
        chart = Chart(
            chart_type='line',
            data=pd.DataFrame(),
            title='Test Chart',
            explanation='No data available'
        )
        
        assert chart.explanation == 'No data available'
        assert chart.data.empty


class TestCreateTimeTrendChart:
    """Tests for create_time_trend_chart function."""
    
    @patch('components.chart_generator.execute_query')
    def test_time_trend_with_time_column(self, mock_execute, schema_info_full):
        """Test time trend chart creation when time column exists."""
        # Mock query result
        mock_df = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10),
            'count': [100, 120, 110, 130, 125, 140, 135, 150, 145, 160]
        })
        mock_execute.return_value = mock_df
        
        chart = create_time_trend_chart('catalog', 'schema', 'table', schema_info_full)
        
        assert chart.chart_type == 'line'
        assert 'timestamp' in chart.title
        assert chart.x_column == 'date'
        assert chart.y_column == 'count'
        assert len(chart.data) == 10
        assert chart.explanation is None
    
    def test_time_trend_without_time_column(self, schema_info_no_time):
        """Test time trend chart fallback when no time column exists."""
        chart = create_time_trend_chart('catalog', 'schema', 'table', schema_info_no_time)
        
        assert chart.chart_type == 'line'
        assert chart.title == 'Time Trend'
        assert chart.data.empty
        assert chart.explanation is not None
        assert 'No time column detected' in chart.explanation
    
    @patch('components.chart_generator.execute_query')
    def test_time_trend_with_empty_data(self, mock_execute, schema_info_full):
        """Test time trend chart when query returns empty data."""
        mock_execute.return_value = pd.DataFrame()
        
        chart = create_time_trend_chart('catalog', 'schema', 'table', schema_info_full)
        
        assert chart.data.empty
        assert chart.explanation is not None
        assert 'no valid data' in chart.explanation
    
    @patch('components.chart_generator.execute_query')
    def test_time_trend_respects_limit(self, mock_execute, schema_info_full):
        """Test that time trend query includes performance limit."""
        mock_execute.return_value = pd.DataFrame({'date': [], 'count': []})
        
        create_time_trend_chart('catalog', 'schema', 'table', schema_info_full)
        
        # Verify query includes LIMIT clause
        call_args = mock_execute.call_args[0][0]
        assert f'LIMIT {MAX_TIME_SERIES_POINTS}' in call_args


class TestCreateCategoryBreakdownChart:
    """Tests for create_category_breakdown_chart function."""
    
    @patch('components.chart_generator.execute_query')
    def test_category_breakdown_with_categorical_column(self, mock_execute, schema_info_full):
        """Test category breakdown chart when categorical column exists."""
        # Mock query result
        mock_df = pd.DataFrame({
            'category': ['A', 'B', 'C', 'D', 'E'],
            'count': [100, 80, 60, 40, 20]
        })
        mock_execute.return_value = mock_df
        
        chart = create_category_breakdown_chart('catalog', 'schema', 'table', schema_info_full)
        
        assert chart.chart_type == 'bar'
        assert 'category' in chart.title
        assert chart.x_column == 'category'
        assert chart.y_column == 'count'
        assert len(chart.data) == 5
        assert chart.explanation is None
    
    def test_category_breakdown_without_categorical_column(self, schema_info_no_categorical):
        """Test category breakdown fallback when no categorical column exists."""
        chart = create_category_breakdown_chart('catalog', 'schema', 'table', schema_info_no_categorical)
        
        assert chart.chart_type == 'bar'
        assert chart.title == 'Category Breakdown'
        assert chart.data.empty
        assert chart.explanation is not None
        assert 'No categorical columns detected' in chart.explanation
    
    @patch('components.chart_generator.execute_query')
    def test_category_breakdown_with_empty_data(self, mock_execute, schema_info_full):
        """Test category breakdown when query returns empty data."""
        mock_execute.return_value = pd.DataFrame()
        
        chart = create_category_breakdown_chart('catalog', 'schema', 'table', schema_info_full)
        
        assert chart.data.empty
        assert chart.explanation is not None
        assert 'no valid data' in chart.explanation
    
    @patch('components.chart_generator.execute_query')
    def test_category_breakdown_respects_limit(self, mock_execute, schema_info_full):
        """Test that category breakdown query includes performance limit."""
        mock_execute.return_value = pd.DataFrame({'category': [], 'count': []})
        
        create_category_breakdown_chart('catalog', 'schema', 'table', schema_info_full)
        
        # Verify query includes LIMIT clause
        call_args = mock_execute.call_args[0][0]
        assert f'LIMIT {MAX_CATEGORY_VALUES}' in call_args


class TestCreateDistributionChart:
    """Tests for create_distribution_chart function."""
    
    @patch('components.chart_generator.execute_query')
    def test_distribution_with_numeric_column(self, mock_execute, schema_info_full):
        """Test distribution chart when numeric column exists."""
        # Mock query result with numeric values
        mock_df = pd.DataFrame({
            'value': [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        })
        mock_execute.return_value = mock_df
        
        chart = create_distribution_chart('catalog', 'schema', 'table', schema_info_full)
        
        assert chart.chart_type == 'bar'
        assert 'value' in chart.title
        assert chart.x_column == 'bin'
        assert chart.y_column == 'count'
        assert not chart.data.empty
        assert chart.explanation is None
    
    def test_distribution_without_numeric_column(self, schema_info_no_numeric):
        """Test distribution fallback when no numeric column exists."""
        chart = create_distribution_chart('catalog', 'schema', 'table', schema_info_no_numeric)
        
        assert chart.chart_type == 'histogram'
        assert chart.title == 'Numeric Distribution'
        assert chart.data.empty
        assert chart.explanation is not None
        assert 'No numeric columns detected' in chart.explanation
    
    @patch('components.chart_generator.execute_query')
    def test_distribution_with_empty_data(self, mock_execute, schema_info_full):
        """Test distribution when query returns empty data."""
        mock_execute.return_value = pd.DataFrame()
        
        chart = create_distribution_chart('catalog', 'schema', 'table', schema_info_full)
        
        assert chart.data.empty
        assert chart.explanation is not None
        assert 'no valid data' in chart.explanation
    
    @patch('components.chart_generator.execute_query')
    def test_distribution_respects_limit(self, mock_execute, schema_info_full):
        """Test that distribution query includes performance limit."""
        mock_execute.return_value = pd.DataFrame({'value': []})
        
        create_distribution_chart('catalog', 'schema', 'table', schema_info_full)
        
        # Verify query includes LIMIT clause
        call_args = mock_execute.call_args[0][0]
        assert f'LIMIT {MAX_TIME_SERIES_POINTS}' in call_args


class TestGenerateAllCharts:
    """Tests for generate_all_charts function."""
    
    @patch('components.chart_generator.create_distribution_chart')
    @patch('components.chart_generator.create_category_breakdown_chart')
    @patch('components.chart_generator.create_time_trend_chart')
    def test_generate_all_charts(self, mock_time, mock_category, mock_distribution, schema_info_full):
        """Test that all chart types are generated."""
        # Mock chart returns
        mock_time.return_value = Chart('line', pd.DataFrame(), 'Time')
        mock_category.return_value = Chart('bar', pd.DataFrame(), 'Category')
        mock_distribution.return_value = Chart('bar', pd.DataFrame(), 'Distribution')
        
        charts = generate_all_charts('catalog', 'schema', 'table', schema_info_full)
        
        assert len(charts) == 3
        mock_time.assert_called_once()
        mock_category.assert_called_once()
        mock_distribution.assert_called_once()
    
    @patch('components.chart_generator.create_distribution_chart')
    @patch('components.chart_generator.create_category_breakdown_chart')
    @patch('components.chart_generator.create_time_trend_chart')
    def test_generate_all_charts_with_fallbacks(self, mock_time, mock_category, mock_distribution, schema_info_no_time):
        """Test that charts are generated even with missing columns (fallbacks)."""
        # Mock chart returns with explanations
        mock_time.return_value = Chart('line', pd.DataFrame(), 'Time', explanation='No time column')
        mock_category.return_value = Chart('bar', pd.DataFrame(), 'Category')
        mock_distribution.return_value = Chart('bar', pd.DataFrame(), 'Distribution')
        
        charts = generate_all_charts('catalog', 'schema', 'table', schema_info_no_time)
        
        assert len(charts) == 3
        # Verify all chart functions were called despite missing columns
        assert mock_time.called
        assert mock_category.called
        assert mock_distribution.called
