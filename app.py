"""
Databricks Streamlit Data App for Predictive Maintenance

Main application entry point with sidebar navigation for:
- KPI Overview page
- Data Exploration page  
- Chat Interface page
"""

import streamlit as st
from components.kpi_page import render_kpi_page, DEFAULT_CATALOG, DEFAULT_SCHEMA
from components.explore_page import render_explore_page
from components.chat_page import render_chat_page
from components.db import list_unity_catalog_tables


# Page configuration
st.set_page_config(
    page_title="Predictive Maintenance Data App",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)


def main():
    """Main application entry point."""
    
    # Sidebar navigation
    st.sidebar.title("🔧 Data App")
    st.sidebar.markdown("---")
    
    # Display user identity
    st.sidebar.markdown("**User:** Authenticated via Databricks Apps")
    st.sidebar.markdown("---")
    
    # Navigation menu
    page = st.sidebar.radio(
        "Navigation",
        ["📊 KPI Overview", "🔍 Explore Data", "💬 Chat Interface"],
        label_visibility="collapsed"
    )
    
    # Dataset selector (shared across pages)
    st.sidebar.markdown("### Dataset Selection")
    
    try:
        # List available tables
        tables = list_unity_catalog_tables(DEFAULT_CATALOG, DEFAULT_SCHEMA)
        
        if not tables:
            st.sidebar.warning(f"No tables found in {DEFAULT_CATALOG}.{DEFAULT_SCHEMA}")
            st.error("No datasets available. Please check your Unity Catalog configuration.")
            return
        
        # Initialize session state for selected table
        if 'selected_table' not in st.session_state:
            st.session_state.selected_table = tables[0]
        
        # Dataset selector dropdown
        selected_table = st.sidebar.selectbox(
            "Choose a dataset:",
            options=tables,
            index=tables.index(st.session_state.selected_table) if st.session_state.selected_table in tables else 0,
            key="global_dataset_selector"
        )
        
        # Update session state
        st.session_state.selected_table = selected_table
        
        st.sidebar.markdown("---")
        
        # Render selected page
        if page == "📊 KPI Overview":
            render_kpi_page()
        elif page == "🔍 Explore Data":
            render_explore_page(DEFAULT_CATALOG, DEFAULT_SCHEMA, selected_table)
        elif page == "💬 Chat Interface":
            render_chat_page(DEFAULT_CATALOG, DEFAULT_SCHEMA, selected_table)
    
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        st.exception(e)
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.caption("Powered by Databricks Apps")


if __name__ == "__main__":
    main()
