"""
Explore page component for data filtering and preview.

Provides functionality for:
- Dynamic filter generation based on column types
- Date range filters for time columns
- Selectbox filters for categorical columns (top N categories)
- Range slider filters for numeric columns
- Filtered data preview with pagination
- Download button for filtered results
- LIMIT clauses to restrict result sizes
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Any
from components.db import execute_query, get_secure_table_name
from components.schema_introspector import introspect_schema, SchemaInfo
from components.guardrails import validate_query


# Configuration constants
TOP_N_CATEGORIES = 10  # Number of top categories to show in selectbox filters
PREVIEW_LIMIT = 100  # Default number of rows to show in preview
MAX_DOWNLOAD_LIMIT = 10000  # Maximum rows for download


def render_explore_page(catalog: str, schema: str, table: str):
    """
    Render the explore page with dynamic filters and data preview.
    
    Implements Requirements 5.1-5.6 and 10.1:
    - Dynamic filters based on column types
    - Date range filters for time columns
    - Selectbox filters for categorical columns
    - Range slider filters for numeric columns
    - Filtered data preview
    - Download option for filtered data
    - LIMIT clauses for result size restriction
    
    Args:
        catalog: Unity Catalog name
        schema: Schema name
        table: Table name
    """
    st.title("🔍 Explore Data")
    
    # Get secure table name
    table_to_query, is_secure = get_secure_table_name(catalog, schema, table)
    full_table_name = f"{catalog}.{schema}.{table_to_query}"
    
    # Display table info
    st.write(f"**Dataset:** {full_table_name}")
    if is_secure:
        st.info("🔒 Using secure view with governance policies applied")
    
    # Introspect schema
    try:
        schema_info = introspect_schema(catalog, schema, table_to_query)
    except Exception as e:
        st.error(f"Failed to introspect schema: {str(e)}")
        return
    
    # Initialize session state for filters
    if 'explore_filters' not in st.session_state:
        st.session_state.explore_filters = {}
    
    # Render filters section
    st.subheader("Filters")
    
    filters = _render_filters(catalog, schema, table_to_query, schema_info)
    
    # Build and execute query
    st.subheader("Data Preview")
    
    try:
        # Build WHERE clause from filters
        where_clause = _build_where_clause(filters, schema_info)
        
        # Build query
        query = f"SELECT * FROM {full_table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"
        
        # Validate query with guardrails
        allowed_tables = [full_table_name, table_to_query]
        validated_query, limit_added = validate_query(
            query,
            allowed_tables,
            apply_limit=True,
            default_limit=PREVIEW_LIMIT
        )
        
        # Execute query
        with st.spinner("Loading data..."):
            df = execute_query(validated_query)
        
        # Display results
        if df.empty:
            st.info("No data matches the selected filters.")
        else:
            st.write(f"Showing {len(df)} rows")
            st.dataframe(df, use_container_width=True)
            
            # Download button
            _render_download_button(
                catalog, schema, table_to_query, full_table_name,
                where_clause, len(df)
            )
    
    except Exception as e:
        st.error(f"Failed to load data: {str(e)}")


def _render_filters(
    catalog: str,
    schema: str,
    table: str,
    schema_info: SchemaInfo
) -> Dict[str, Any]:
    """
    Render dynamic filters based on column types.
    
    Implements Requirements 5.1-5.4:
    - Dynamic filter generation
    - Date range filters
    - Selectbox filters for categorical columns
    - Range slider filters for numeric columns
    
    Args:
        catalog: Unity Catalog name
        schema: Schema name
        table: Table name
        schema_info: Schema introspection results
        
    Returns:
        Dictionary of filter values keyed by column name
    """
    filters = {}
    
    # Create filter columns for layout
    col1, col2 = st.columns(2)
    
    with col1:
        # Date range filters (Requirement 5.2)
        if schema_info.time_columns:
            st.write("**Date Filters**")
            for time_col in schema_info.time_columns[:2]:  # Limit to first 2 time columns
                date_filter = _render_date_range_filter(
                    catalog, schema, table, time_col
                )
                if date_filter:
                    filters[time_col] = date_filter
        
        # Categorical filters (Requirement 5.3)
        if schema_info.categorical_columns:
            st.write("**Categorical Filters**")
            # Filter out ID columns from categorical filters
            categorical_non_id = [
                col for col in schema_info.categorical_columns
                if col not in schema_info.id_columns
            ]
            for cat_col in categorical_non_id[:3]:  # Limit to first 3 categorical columns
                cat_filter = _render_categorical_filter(
                    catalog, schema, table, cat_col
                )
                if cat_filter:
                    filters[cat_col] = cat_filter
    
    with col2:
        # Numeric range filters (Requirement 5.4)
        if schema_info.numeric_columns:
            st.write("**Numeric Filters**")
            # Filter out ID columns from numeric filters
            numeric_non_id = [
                col for col in schema_info.numeric_columns
                if col not in schema_info.id_columns
            ]
            for num_col in numeric_non_id[:3]:  # Limit to first 3 numeric columns
                num_filter = _render_numeric_range_filter(
                    catalog, schema, table, num_col
                )
                if num_filter:
                    filters[num_col] = num_filter
    
    return filters


def _render_date_range_filter(
    catalog: str,
    schema: str,
    table: str,
    column: str
) -> Optional[Tuple[Any, Any]]:
    """
    Render date range filter for a time column.
    
    Implements Requirement 5.2: Date range filter when time column exists.
    
    Args:
        catalog: Unity Catalog name
        schema: Schema name
        table: Table name
        column: Time column name
        
    Returns:
        Tuple of (start_date, end_date) if filter is active, None otherwise
    """
    try:
        # Get min and max dates from the column
        full_table_name = f"{catalog}.{schema}.{table}"
        query = f"""
            SELECT 
                MIN({column}) as min_date,
                MAX({column}) as max_date
            FROM {full_table_name}
        """
        
        # Validate and execute query
        allowed_tables = [full_table_name, table]
        validated_query, _ = validate_query(query, allowed_tables, apply_limit=False)
        df = execute_query(validated_query)
        
        if df.empty or df['min_date'].isna().all():
            return None
        
        min_date = pd.to_datetime(df['min_date'].iloc[0])
        max_date = pd.to_datetime(df['max_date'].iloc[0])
        
        # Convert to date objects for date_input widget
        min_date_obj = min_date.date() if hasattr(min_date, 'date') else min_date
        max_date_obj = max_date.date() if hasattr(max_date, 'date') else max_date
        
        # Render date range input
        date_range = st.date_input(
            f"{column}",
            value=(min_date_obj, max_date_obj),
            min_value=min_date_obj,
            max_value=max_date_obj,
            key=f"date_filter_{column}"
        )
        
        # Return filter if user changed the range
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start, end = date_range
            if start != min_date_obj or end != max_date_obj:
                return (start, end)
        
        return None
        
    except Exception as e:
        st.warning(f"Could not load date range for {column}: {str(e)}")
        return None


def _render_categorical_filter(
    catalog: str,
    schema: str,
    table: str,
    column: str
) -> Optional[List[str]]:
    """
    Render selectbox filter for a categorical column showing top N categories.
    
    Implements Requirement 5.3: Selectbox filters for categorical columns.
    
    Args:
        catalog: Unity Catalog name
        schema: Schema name
        table: Table name
        column: Categorical column name
        
    Returns:
        List of selected categories if filter is active, None otherwise
    """
    try:
        # Get top N categories by frequency
        full_table_name = f"{catalog}.{schema}.{table}"
        query = f"""
            SELECT {column}, COUNT(*) as count
            FROM {full_table_name}
            WHERE {column} IS NOT NULL
            GROUP BY {column}
            ORDER BY count DESC
            LIMIT {TOP_N_CATEGORIES}
        """
        
        # Validate and execute query
        allowed_tables = [full_table_name, table]
        validated_query, _ = validate_query(query, allowed_tables, apply_limit=False)
        df = execute_query(validated_query)
        
        if df.empty:
            return None
        
        categories = df[column].tolist()
        
        # Render multiselect
        selected = st.multiselect(
            f"{column}",
            options=categories,
            key=f"cat_filter_{column}",
            help=f"Top {len(categories)} categories by frequency"
        )
        
        return selected if selected else None
        
    except Exception as e:
        st.warning(f"Could not load categories for {column}: {str(e)}")
        return None


def _render_numeric_range_filter(
    catalog: str,
    schema: str,
    table: str,
    column: str
) -> Optional[Tuple[float, float]]:
    """
    Render range slider filter for a numeric column.
    
    Implements Requirement 5.4: Range slider filters for numeric columns.
    
    Args:
        catalog: Unity Catalog name
        schema: Schema name
        table: Table name
        column: Numeric column name
        
    Returns:
        Tuple of (min_value, max_value) if filter is active, None otherwise
    """
    try:
        # Get min and max values from the column
        full_table_name = f"{catalog}.{schema}.{table}"
        query = f"""
            SELECT 
                MIN({column}) as min_val,
                MAX({column}) as max_val
            FROM {full_table_name}
            WHERE {column} IS NOT NULL
        """
        
        # Validate and execute query
        allowed_tables = [full_table_name, table]
        validated_query, _ = validate_query(query, allowed_tables, apply_limit=False)
        df = execute_query(validated_query)
        
        if df.empty or df['min_val'].isna().all():
            return None
        
        min_val = float(df['min_val'].iloc[0])
        max_val = float(df['max_val'].iloc[0])
        
        # Skip if min and max are the same
        if min_val == max_val:
            return None
        
        # Render slider
        range_val = st.slider(
            f"{column}",
            min_value=min_val,
            max_value=max_val,
            value=(min_val, max_val),
            key=f"num_filter_{column}"
        )
        
        # Return filter if user changed the range
        if range_val[0] != min_val or range_val[1] != max_val:
            return range_val
        
        return None
        
    except Exception as e:
        st.warning(f"Could not load range for {column}: {str(e)}")
        return None


def _build_where_clause(filters: Dict[str, Any], schema_info: SchemaInfo) -> str:
    """
    Build SQL WHERE clause from filter values.
    
    Args:
        filters: Dictionary of filter values keyed by column name
        schema_info: Schema introspection results
        
    Returns:
        SQL WHERE clause string (without "WHERE" keyword), or empty string if no filters
    """
    conditions = []
    
    for column, filter_value in filters.items():
        if filter_value is None:
            continue
        
        # Date range filter
        if column in schema_info.time_columns:
            if isinstance(filter_value, tuple) and len(filter_value) == 2:
                start, end = filter_value
                conditions.append(f"{column} >= '{start}'")
                conditions.append(f"{column} <= '{end}'")
        
        # Categorical filter
        elif column in schema_info.categorical_columns:
            if isinstance(filter_value, list) and filter_value:
                # Escape single quotes in values
                escaped_values = [val.replace("'", "''") for val in filter_value]
                values_str = "', '".join(escaped_values)
                conditions.append(f"{column} IN ('{values_str}')")
        
        # Numeric range filter
        elif column in schema_info.numeric_columns:
            if isinstance(filter_value, tuple) and len(filter_value) == 2:
                min_val, max_val = filter_value
                conditions.append(f"{column} >= {min_val}")
                conditions.append(f"{column} <= {max_val}")
    
    return " AND ".join(conditions)


def _render_download_button(
    catalog: str,
    schema: str,
    table: str,
    full_table_name: str,
    where_clause: str,
    preview_row_count: int
):
    """
    Render download button for filtered results.
    
    Implements Requirement 5.6: Download option for filtered data results.
    Implements Requirement 10.1: LIMIT clauses to restrict result sizes.
    
    Args:
        catalog: Unity Catalog name
        schema: Schema name
        table: Table name
        full_table_name: Full table name with catalog and schema
        where_clause: SQL WHERE clause (without "WHERE" keyword)
        preview_row_count: Number of rows in preview
    """
    st.subheader("Download Data")
    
    # Show download options
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.write(f"Download filtered results (up to {MAX_DOWNLOAD_LIMIT:,} rows)")
        
        if preview_row_count >= PREVIEW_LIMIT:
            st.info(
                f"Preview shows {PREVIEW_LIMIT} rows. "
                f"Download will include up to {MAX_DOWNLOAD_LIMIT:,} rows."
            )
    
    with col2:
        if st.button("📥 Download CSV", use_container_width=True):
            try:
                # Build download query
                query = f"SELECT * FROM {full_table_name}"
                if where_clause:
                    query += f" WHERE {where_clause}"
                
                # Validate query with download limit
                allowed_tables = [full_table_name, table]
                validated_query, _ = validate_query(
                    query,
                    allowed_tables,
                    apply_limit=True,
                    default_limit=MAX_DOWNLOAD_LIMIT
                )
                
                # Execute query
                with st.spinner("Preparing download..."):
                    df = execute_query(validated_query)
                
                # Convert to CSV
                csv = df.to_csv(index=False)
                
                # Offer download
                st.download_button(
                    label="💾 Save File",
                    data=csv,
                    file_name=f"{table}_filtered.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                
                st.success(f"✅ Prepared {len(df):,} rows for download")
                
            except Exception as e:
                st.error(f"Download failed: {str(e)}")
