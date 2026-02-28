"""
Unit tests for KPI page component.

Tests:
- KPI page module structure and imports
- Helper functions and constants
"""

import pytest
from components.kpi_page import DEFAULT_CATALOG, DEFAULT_SCHEMA

def test_default_catalog_and_schema():
    """Test that default catalog and schema constants are defined."""
    assert DEFAULT_CATALOG == "dataknobs_predictive_maintenance_and_asset_management"
    assert DEFAULT_SCHEMA == "datasets"


def test_kpi_page_module_imports():
    """Test that kpi_page module imports successfully and has required functions."""
    from components import kpi_page
    
    # Verify render_kpi_page function exists
    assert hasattr(kpi_page, 'render_kpi_page')
    assert callable(kpi_page.render_kpi_page)
    
    # Verify constants exist
    assert hasattr(kpi_page, 'DEFAULT_CATALOG')
    assert hasattr(kpi_page, 'DEFAULT_SCHEMA')


def test_kpi_page_imports_required_modules():
    """Test that kpi_page imports all required dependencies."""
    from components import kpi_page
    
    # Verify streamlit is imported
    assert hasattr(kpi_page, 'st')
    
    # Verify database functions are imported
    assert hasattr(kpi_page, 'list_unity_catalog_tables')
    assert hasattr(kpi_page, 'get_secure_table_name')
    
    # Verify schema introspection is imported
    assert hasattr(kpi_page, 'introspect_schema')
    
    # Verify KPI engine is imported
    assert hasattr(kpi_page, 'compute_all_kpis')
    
    # Verify chart generator functions are imported
    assert hasattr(kpi_page, 'generate_all_charts')
    assert hasattr(kpi_page, 'render_chart')
