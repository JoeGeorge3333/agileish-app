"""
Unit tests for KPI engine module.

Tests:
- Row count computation
- Date range computation with and without time columns
- Data missingness computation
- Failure rate computation with and without label columns
- Unique asset count computation with and without ID columns
- Fallback logic for missing columns
"""

import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from components.kpi_engine import (
    KPI,
    compute_row_count,
    compute_date_range,
    compute_data_missingness,
    compute_failure_rate,
    compute_unique_asset_count,
    compute_all_kpis
)
from components.schema_introspector import SchemaInfo


@pytest.fixture
def mock_schema_info():
    """Create a mock SchemaInfo with typical columns."""
    schema = SchemaInfo()
    schema.all_columns = ['id', 'timestamp', 'sensor_value', 'failure', 'category']
    schema.time_columns = ['timestamp']
    schema.id_columns = ['id']
    schema.label_columns = ['failure']
    schema.categorical_columns = ['category']
    schema.numeric_columns = ['sensor_value']
    schema.column_types = {
        'id': 'int',
        'timestamp': 'timestamp',
        'sensor_value': 'double',
        'failure': 'int',
        'category': 'string'
    }
    return schema


@pytest.fixture
def mock_schema_info_minimal():
    """Create a minimal SchemaInfo with no special columns."""
    schema = SchemaInfo()
    schema.all_columns = ['col1', 'col2']
    schema.time_columns = []
    schema.id_columns = []
    schema.label_columns = []
    schema.categorical_columns = ['col1']
    schema.numeric_columns = ['col2']
    schema.column_types = {
        'col1': 'string',
        'col2': 'double'
    }
    return schema


class TestKPI:
    """Test KPI container class."""
    
    def test_kpi_creation(self):
        kpi = KPI(label="Test KPI", value="100", explanation="Test explanation")
        assert kpi.label == "Test KPI"
        assert kpi.value == "100"
        assert kpi.explanation == "Test explanation"
    
    def test_kpi_to_dict(self):
        kpi = KPI(label="Test KPI", value="100", explanation="Test explanation")
        result = kpi.to_dict()
        assert result == {
            'label': "Test KPI",
            'value': "100",
            'explanation': "Test explanation"
        }
    
    def test_kpi_without_explanation(self):
        kpi = KPI(label="Test KPI", value="100")
        assert kpi.explanation is None


class TestComputeRowCount:
    """Test row count KPI computation."""
    
    @patch('components.kpi_engine.execute_query')
    def test_compute_row_count_success(self, mock_execute):
        mock_execute.return_value = pd.DataFrame({'row_count': [1000]})
        
        kpi = compute_row_count('catalog', 'schema', 'table')
        
        assert kpi.label == "Total Rows"
        assert kpi.value == "1,000"
        assert kpi.explanation is None
        mock_execute.assert_called_once()
    
    @patch('components.kpi_engine.execute_query')
    def test_compute_row_count_zero(self, mock_execute):
        mock_execute.return_value = pd.DataFrame({'row_count': [0]})
        
        kpi = compute_row_count('catalog', 'schema', 'table')
        
        assert kpi.label == "Total Rows"
        assert kpi.value == "0"
    
    @patch('components.kpi_engine.execute_query')
    def test_compute_row_count_failure(self, mock_execute):
        mock_execute.side_effect = Exception("Query failed")
        
        with pytest.raises(Exception, match="Failed to compute row count"):
            compute_row_count('catalog', 'schema', 'table')


class TestComputeDateRange:
    """Test date range KPI computation."""
    
    @patch('components.kpi_engine.execute_query')
    def test_compute_date_range_success(self, mock_execute, mock_schema_info):
        mock_execute.return_value = pd.DataFrame({
            'min_date': ['2023-01-01'],
            'max_date': ['2023-12-31']
        })
        
        kpi = compute_date_range('catalog', 'schema', 'table', mock_schema_info)
        
        assert kpi.label == "Date Range"
        assert kpi.value == "2023-01-01 to 2023-12-31"
        assert kpi.explanation is None
    
    @patch('components.kpi_engine.execute_query')
    def test_compute_date_range_no_time_column(self, mock_execute, mock_schema_info_minimal):
        kpi = compute_date_range('catalog', 'schema', 'table', mock_schema_info_minimal)
        
        assert kpi.label == "Date Range"
        assert kpi.value == "N/A"
        assert "No time column detected" in kpi.explanation
        mock_execute.assert_not_called()
    
    @patch('components.kpi_engine.execute_query')
    def test_compute_date_range_null_dates(self, mock_execute, mock_schema_info):
        mock_execute.return_value = pd.DataFrame({
            'min_date': [None],
            'max_date': [None]
        })
        
        kpi = compute_date_range('catalog', 'schema', 'table', mock_schema_info)
        
        assert kpi.label == "Date Range"
        assert kpi.value == "No data"
        assert "contains no valid dates" in kpi.explanation


class TestComputeDataMissingness:
    """Test data missingness KPI computation."""
    
    @patch('components.kpi_engine.execute_query')
    def test_compute_data_missingness_success(self, mock_execute, mock_schema_info):
        # 100 rows, 10 total nulls across all columns
        mock_execute.return_value = pd.DataFrame({
            'row_count': [100],
            'total_nulls': [10]
        })
        
        kpi = compute_data_missingness('catalog', 'schema', 'table', mock_schema_info)
        
        assert kpi.label == "Data Missingness"
        # 10 nulls / (100 rows * 5 columns) = 2%
        assert kpi.value == "2.00%"
        assert kpi.explanation is None
    
    @patch('components.kpi_engine.execute_query')
    def test_compute_data_missingness_zero(self, mock_execute, mock_schema_info):
        mock_execute.return_value = pd.DataFrame({
            'row_count': [100],
            'total_nulls': [0]
        })
        
        kpi = compute_data_missingness('catalog', 'schema', 'table', mock_schema_info)
        
        assert kpi.label == "Data Missingness"
        assert kpi.value == "0.00%"
    
    @patch('components.kpi_engine.execute_query')
    def test_compute_data_missingness_empty_dataset(self, mock_execute, mock_schema_info):
        mock_execute.return_value = pd.DataFrame({
            'row_count': [0],
            'total_nulls': [0]
        })
        
        kpi = compute_data_missingness('catalog', 'schema', 'table', mock_schema_info)
        
        assert kpi.label == "Data Missingness"
        assert kpi.value == "0%"
        assert "Dataset is empty" in kpi.explanation
    
    def test_compute_data_missingness_no_columns(self):
        schema = SchemaInfo()
        schema.all_columns = []
        
        kpi = compute_data_missingness('catalog', 'schema', 'table', schema)
        
        assert kpi.label == "Data Missingness"
        assert kpi.value == "N/A"
        assert "No columns detected" in kpi.explanation


class TestComputeFailureRate:
    """Test failure rate KPI computation."""
    
    @patch('components.kpi_engine.execute_query')
    def test_compute_failure_rate_success(self, mock_execute, mock_schema_info):
        mock_execute.return_value = pd.DataFrame({
            'failure': [0, 1],
            'count': [80, 20]
        })
        
        kpi = compute_failure_rate('catalog', 'schema', 'table', mock_schema_info)
        
        assert kpi.label == "Failure Rate"
        assert kpi.value == "20.00%"
        assert kpi.explanation is None
    
    @patch('components.kpi_engine.execute_query')
    def test_compute_failure_rate_no_label_column(self, mock_execute, mock_schema_info_minimal):
        kpi = compute_failure_rate('catalog', 'schema', 'table', mock_schema_info_minimal)
        
        assert kpi.label == "Label Distribution"
        assert kpi.value == "N/A"
        assert "No label column detected" in kpi.explanation
        assert "col1" in kpi.explanation  # Suggests fallback column
        mock_execute.assert_not_called()
    
    @patch('components.kpi_engine.execute_query')
    def test_compute_failure_rate_distribution_fallback(self, mock_execute, mock_schema_info):
        # No failure indicator found, show distribution
        mock_execute.return_value = pd.DataFrame({
            'failure': ['normal', 'warning'],
            'count': [70, 30]
        })
        
        kpi = compute_failure_rate('catalog', 'schema', 'table', mock_schema_info)
        
        assert kpi.label == "Label Distribution"
        assert "normal: 70.0%" in kpi.value
        assert "Most common label" in kpi.explanation
    
    @patch('components.kpi_engine.execute_query')
    def test_compute_failure_rate_empty_data(self, mock_execute, mock_schema_info):
        mock_execute.return_value = pd.DataFrame()
        
        kpi = compute_failure_rate('catalog', 'schema', 'table', mock_schema_info)
        
        assert kpi.label == "Failure Rate"
        assert kpi.value == "No data"
        assert "contains no data" in kpi.explanation


class TestComputeUniqueAssetCount:
    """Test unique asset count KPI computation."""
    
    @patch('components.kpi_engine.execute_query')
    def test_compute_unique_asset_count_success(self, mock_execute, mock_schema_info):
        mock_execute.return_value = pd.DataFrame({'unique_count': [50]})
        
        kpi = compute_unique_asset_count('catalog', 'schema', 'table', mock_schema_info)
        
        assert kpi.label == "Unique Assets"
        assert kpi.value == "50"
        assert kpi.explanation is None
    
    @patch('components.kpi_engine.execute_query')
    def test_compute_unique_asset_count_no_id_column(self, mock_execute, mock_schema_info_minimal):
        # Fallback to categorical column
        mock_execute.return_value = pd.DataFrame({'unique_count': [25]})
        
        kpi = compute_unique_asset_count('catalog', 'schema', 'table', mock_schema_info_minimal)
        
        assert kpi.label == "Unique Values"
        assert kpi.value == "25"
        assert "No ID column detected" in kpi.explanation
        assert "col1" in kpi.explanation
    
    def test_compute_unique_asset_count_no_columns(self):
        schema = SchemaInfo()
        schema.all_columns = []
        schema.id_columns = []
        schema.categorical_columns = []
        
        kpi = compute_unique_asset_count('catalog', 'schema', 'table', schema)
        
        assert kpi.label == "Unique Assets"
        assert kpi.value == "N/A"
        assert "No ID or categorical columns detected" in kpi.explanation


class TestComputeAllKPIs:
    """Test computing all KPIs together."""
    
    @patch('components.kpi_engine.compute_row_count')
    @patch('components.kpi_engine.compute_date_range')
    @patch('components.kpi_engine.compute_data_missingness')
    @patch('components.kpi_engine.compute_failure_rate')
    @patch('components.kpi_engine.compute_unique_asset_count')
    def test_compute_all_kpis(
        self,
        mock_unique,
        mock_failure,
        mock_missingness,
        mock_date,
        mock_row,
        mock_schema_info
    ):
        # Mock all KPI functions
        mock_row.return_value = KPI("Total Rows", "1,000")
        mock_date.return_value = KPI("Date Range", "2023-01-01 to 2023-12-31")
        mock_missingness.return_value = KPI("Data Missingness", "2.00%")
        mock_failure.return_value = KPI("Failure Rate", "20.00%")
        mock_unique.return_value = KPI("Unique Assets", "50")
        
        kpis = compute_all_kpis('catalog', 'schema', 'table', mock_schema_info)
        
        assert len(kpis) == 5
        assert kpis[0].label == "Total Rows"
        assert kpis[1].label == "Date Range"
        assert kpis[2].label == "Data Missingness"
        assert kpis[3].label == "Failure Rate"
        assert kpis[4].label == "Unique Assets"
        
        # Verify all functions were called
        mock_row.assert_called_once()
        mock_date.assert_called_once()
        mock_missingness.assert_called_once()
        mock_failure.assert_called_once()
        mock_unique.assert_called_once()
