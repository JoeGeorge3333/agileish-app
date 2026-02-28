"""
KPI page component for displaying dataset KPIs.

Provides:
- Dataset selector dropdown
- Computed KPIs displayed in metric cards
- Explanations for fallback KPIs
- Graceful handling of missing columns
"""

import streamlit as st
from typing import Optional
from components.db import list_unity_catalog_tables, get_secure_table_name
from components.schema_introspector import introspect_schema
from components.kpi_engine import compute_all_kpis
from components.chart_generator import generate_all_charts, render_chart


# Default catalog and schema for predictive maintenance datasets
DEFAULT_CATALOG = "dataknobs_predictive_maintenance_and_asset_management"
DEFAULT_SCHEMA = "datasets"


def render_kpi_page():
    """
    Render the KPI Overview page.
    
    Displays:
    - Dataset selector dropdown
    - Computed KPIs in metric cards
    - Explanations for fallback KPIs when columns are missing
    
    Handles missing columns gracefully with fallback behavior.
    """
    st.title("📊 KPI Overview")
    st.markdown("Select a dataset to view key performance indicators and data quality metrics.")
    
    # Dataset selector
    st.subheader("Select Dataset")
    
    try:
        # List available tables
        tables = list_unity_catalog_tables(DEFAULT_CATALOG, DEFAULT_SCHEMA)
        
        if not tables:
            st.warning(f"No tables found in {DEFAULT_CATALOG}.{DEFAULT_SCHEMA}")
            return
        
        # Initialize session state for selected table
        if 'selected_table' not in st.session_state:
            st.session_state.selected_table = tables[0]
        
        # Dataset selector dropdown
        selected_table = st.selectbox(
            "Choose a dataset:",
            options=tables,
            index=tables.index(st.session_state.selected_table) if st.session_state.selected_table in tables else 0,
            key="dataset_selector"
        )
        
        # Update session state
        st.session_state.selected_table = selected_table
        
        # Get secure table name (use secure view if available)
        table_to_query, is_secure = get_secure_table_name(DEFAULT_CATALOG, DEFAULT_SCHEMA, selected_table)
        
        if is_secure:
            st.info(f"🔒 Using secure view: {table_to_query}")
        
        # Introspect schema
        with st.spinner("Analyzing dataset schema..."):
            schema_info = introspect_schema(DEFAULT_CATALOG, DEFAULT_SCHEMA, table_to_query)
        
        # Display schema summary
        with st.expander("📋 Schema Summary", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Columns", len(schema_info.all_columns))
                st.metric("Time Columns", len(schema_info.time_columns))
            
            with col2:
                st.metric("ID Columns", len(schema_info.id_columns))
                st.metric("Label Columns", len(schema_info.label_columns))
            
            with col3:
                st.metric("Numeric Columns", len(schema_info.numeric_columns))
                st.metric("Categorical Columns", len(schema_info.categorical_columns))
        
        # Compute KPIs
        st.subheader("Key Performance Indicators")
        
        with st.spinner("Computing KPIs..."):
            kpis = compute_all_kpis(DEFAULT_CATALOG, DEFAULT_SCHEMA, table_to_query, schema_info)
        
        # Display KPIs in metric cards
        # Use columns to display KPIs in a grid layout
        num_kpis = len(kpis)
        cols_per_row = 3
        
        for i in range(0, num_kpis, cols_per_row):
            cols = st.columns(cols_per_row)
            
            for j in range(cols_per_row):
                idx = i + j
                if idx < num_kpis:
                    kpi = kpis[idx]
                    
                    with cols[j]:
                        # Display metric card
                        st.metric(label=kpi.label, value=kpi.value)
                        
                        # Display explanation if present (for fallback KPIs)
                        if kpi.explanation:
                            st.caption(f"ℹ️ {kpi.explanation}")
        
        # Success message
        st.success(f"✅ Computed {len(kpis)} KPIs for {selected_table}")
        
        # Generate and display visualizations
        st.subheader("Data Visualizations")
        
        with st.spinner("Generating visualizations..."):
            charts = generate_all_charts(DEFAULT_CATALOG, DEFAULT_SCHEMA, table_to_query, schema_info)
        
        # Display all generated charts
        for chart in charts:
            render_chart(chart)
            st.divider()  # Add visual separator between charts
        
    except Exception as e:
        st.error(f"❌ Error loading KPI page: {str(e)}")
        st.exception(e)


if __name__ == "__main__":
    # For standalone testing
    render_kpi_page()
