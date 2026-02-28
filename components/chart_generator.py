"""
Chart generation module for data visualization.

Provides functions for:
- Creating time trend visualizations (when time column exists)
- Creating category breakdown visualizations (when categorical columns exist)
- Creating distribution/histogram visualizations (when numeric columns exist)
- Fallback logic and explanations for missing columns
- Data point limiting for rendering performance
"""

from typing import Optional, List, Dict, Any, Tuple
import pandas as pd
import streamlit as st
from components.db import execute_query
from components.schema_introspector import SchemaInfo, get_primary_time_column


# Performance limits for chart rendering
MAX_TIME_SERIES_POINTS = 1000
MAX_CATEGORY_VALUES = 20
MAX_HISTOGRAM_BINS = 50


class Chart:
    """Container for a chart with data, type, and optional explanation."""
    
    def __init__(
        self,
        chart_type: str,
        data: pd.DataFrame,
        title: str,
        x_column: Optional[str] = None,
        y_column: Optional[str] = None,
        explanation: Optional[str] = None
    ):
        self.chart_type = chart_type  # 'line', 'bar', 'area', 'histogram'
        self.data = data
        self.title = title
        self.x_column = x_column
        self.y_column = y_column
        self.explanation = explanation
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            'chart_type': self.chart_type,
            'data': self.data.to_dict(),
            'title': self.title,
            'x_column': self.x_column,
            'y_column': self.y_column,
            'explanation': self.explanation
        }


def create_time_trend_chart(
    catalog: str,
    schema: str,
    table: str,
    schema_info: SchemaInfo
) -> Chart:
    """
    Create a time trend visualization when time column exists.
    
    Shows count of records over time, aggregated by date/time period.
    Limits data points to MAX_TIME_SERIES_POINTS for performance.
    
    Args:
        catalog: Unity Catalog name
        schema: Schema name
        table: Table name
        schema_info: SchemaInfo object with detected columns
        
    Returns:
        Chart object with time trend data or fallback explanation
        
    Raises:
        Exception: If query execution fails
    """
    time_col = get_primary_time_column(schema_info)
    
    if not time_col:
        # Fallback: No time column available
        return Chart(
            chart_type='line',
            data=pd.DataFrame(),
            title='Time Trend',
            explanation='No time column detected in dataset. Cannot create time trend visualization.'
        )
    
    # Query to get time series data with aggregation
    # Use DATE() to group by day for better performance
    query = f"""
        SELECT 
            DATE({time_col}) as date,
            COUNT(*) as count
        FROM {catalog}.{schema}.{table}
        WHERE {time_col} IS NOT NULL
        GROUP BY DATE({time_col})
        ORDER BY date
        LIMIT {MAX_TIME_SERIES_POINTS}
    """
    
    try:
        df = execute_query(query)
        
        if df.empty:
            return Chart(
                chart_type='line',
                data=pd.DataFrame(),
                title='Time Trend',
                explanation=f"Time column '{time_col}' contains no valid data"
            )
        
        return Chart(
            chart_type='line',
            data=df,
            title=f'Records Over Time ({time_col})',
            x_column='date',
            y_column='count'
        )
    except Exception as e:
        raise Exception(f"Failed to create time trend chart: {str(e)}")


def create_category_breakdown_chart(
    catalog: str,
    schema: str,
    table: str,
    schema_info: SchemaInfo
) -> Chart:
    """
    Create a category breakdown visualization when categorical columns exist.
    
    Shows distribution of top categories in the first categorical column.
    Limits to MAX_CATEGORY_VALUES for performance.
    
    Args:
        catalog: Unity Catalog name
        schema: Schema name
        table: Table name
        schema_info: SchemaInfo object with detected columns
        
    Returns:
        Chart object with category breakdown data or fallback explanation
        
    Raises:
        Exception: If query execution fails
    """
    if not schema_info.categorical_columns:
        # Fallback: No categorical columns available
        return Chart(
            chart_type='bar',
            data=pd.DataFrame(),
            title='Category Breakdown',
            explanation='No categorical columns detected in dataset. Cannot create category breakdown visualization.'
        )
    
    # Use first categorical column
    cat_col = schema_info.categorical_columns[0]
    
    # Query to get category distribution
    query = f"""
        SELECT 
            {cat_col} as category,
            COUNT(*) as count
        FROM {catalog}.{schema}.{table}
        WHERE {cat_col} IS NOT NULL
        GROUP BY {cat_col}
        ORDER BY count DESC
        LIMIT {MAX_CATEGORY_VALUES}
    """
    
    try:
        df = execute_query(query)
        
        if df.empty:
            return Chart(
                chart_type='bar',
                data=pd.DataFrame(),
                title='Category Breakdown',
                explanation=f"Categorical column '{cat_col}' contains no valid data"
            )
        
        return Chart(
            chart_type='bar',
            data=df,
            title=f'Top Categories ({cat_col})',
            x_column='category',
            y_column='count'
        )
    except Exception as e:
        raise Exception(f"Failed to create category breakdown chart: {str(e)}")


def create_distribution_chart(
    catalog: str,
    schema: str,
    table: str,
    schema_info: SchemaInfo
) -> Chart:
    """
    Create a distribution/histogram visualization when numeric columns exist.
    
    Shows distribution of values in the first numeric column.
    Samples data if needed for performance.
    
    Args:
        catalog: Unity Catalog name
        schema: Schema name
        table: Table name
        schema_info: SchemaInfo object with detected columns
        
    Returns:
        Chart object with distribution data or fallback explanation
        
    Raises:
        Exception: If query execution fails
    """
    if not schema_info.numeric_columns:
        # Fallback: No numeric columns available
        return Chart(
            chart_type='histogram',
            data=pd.DataFrame(),
            title='Numeric Distribution',
            explanation='No numeric columns detected in dataset. Cannot create distribution visualization.'
        )
    
    # Use first numeric column
    num_col = schema_info.numeric_columns[0]
    
    # Query to get numeric values (sample for performance)
    query = f"""
        SELECT {num_col} as value
        FROM {catalog}.{schema}.{table}
        WHERE {num_col} IS NOT NULL
        ORDER BY RAND()
        LIMIT {MAX_TIME_SERIES_POINTS}
    """
    
    try:
        df = execute_query(query)
        
        if df.empty:
            return Chart(
                chart_type='histogram',
                data=pd.DataFrame(),
                title='Numeric Distribution',
                explanation=f"Numeric column '{num_col}' contains no valid data"
            )
        
        # Create histogram bins
        hist_data, bin_edges = pd.cut(df['value'], bins=min(MAX_HISTOGRAM_BINS, 30), retbins=True, duplicates='drop')
        hist_counts = hist_data.value_counts().sort_index()
        
        # Create dataframe for histogram
        hist_df = pd.DataFrame({
            'bin': [f"{interval.left:.2f}-{interval.right:.2f}" for interval in hist_counts.index],
            'count': hist_counts.values
        })
        
        return Chart(
            chart_type='bar',
            data=hist_df,
            title=f'Distribution of {num_col}',
            x_column='bin',
            y_column='count'
        )
    except Exception as e:
        raise Exception(f"Failed to create distribution chart: {str(e)}")


def generate_all_charts(
    catalog: str,
    schema: str,
    table: str,
    schema_info: SchemaInfo
) -> List[Chart]:
    """
    Generate all available chart types for the dataset.
    
    Creates:
    1. Time trend visualization (when time column exists)
    2. Category breakdown visualization (when categorical columns exist)
    3. Distribution visualization (when numeric columns exist)
    
    Each chart includes fallback logic and explanations when required columns are missing.
    
    Args:
        catalog: Unity Catalog name
        schema: Schema name
        table: Table name
        schema_info: SchemaInfo object with detected columns
        
    Returns:
        List of Chart objects (at least 3 charts, some may have explanations for missing data)
        
    Raises:
        Exception: If chart generation fails
    """
    charts = []
    
    # 1. Time trend chart
    charts.append(create_time_trend_chart(catalog, schema, table, schema_info))
    
    # 2. Category breakdown chart
    charts.append(create_category_breakdown_chart(catalog, schema, table, schema_info))
    
    # 3. Distribution chart
    charts.append(create_distribution_chart(catalog, schema, table, schema_info))
    
    return charts


def render_chart(chart: Chart):
    """
    Render a chart using Streamlit chart components.
    
    Args:
        chart: Chart object to render
    """
    st.subheader(chart.title)
    
    if chart.explanation:
        st.info(chart.explanation)
        return
    
    if chart.data.empty:
        st.warning("No data available for this chart")
        return
    
    # Render based on chart type
    if chart.chart_type == 'line':
        st.line_chart(chart.data, x=chart.x_column, y=chart.y_column)
    elif chart.chart_type == 'bar':
        st.bar_chart(chart.data, x=chart.x_column, y=chart.y_column)
    elif chart.chart_type == 'area':
        st.area_chart(chart.data, x=chart.x_column, y=chart.y_column)
    elif chart.chart_type == 'histogram':
        st.bar_chart(chart.data, x=chart.x_column, y=chart.y_column)
    else:
        st.warning(f"Unknown chart type: {chart.chart_type}")
