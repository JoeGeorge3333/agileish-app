"""
KPI computation engine for dataset analysis.

Provides functions for:
- Computing row count KPI
- Computing date range KPI (when time column exists)
- Computing data missingness KPI
- Computing failure rate KPI (when label column exists)
- Computing unique asset count KPI (when ID column exists)
- Fallback logic when expected columns are missing
- Optimized aggregate queries to minimize data transfer
"""

from typing import Dict, Any, Optional, List
from components.db import execute_query
from components.schema_introspector import SchemaInfo, get_primary_time_column, get_primary_id_column, get_primary_label_column


class KPI:
    """Container for a single KPI with value, label, and optional explanation."""
    
    def __init__(self, label: str, value: Any, explanation: Optional[str] = None):
        self.label = label
        self.value = value
        self.explanation = explanation
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            'label': self.label,
            'value': self.value,
            'explanation': self.explanation
        }


def compute_row_count(catalog: str, schema: str, table: str) -> KPI:
    """
    Compute row count KPI for the dataset.
    
    Args:
        catalog: Unity Catalog name
        schema: Schema name
        table: Table name
        
    Returns:
        KPI object with row count
        
    Raises:
        Exception: If query execution fails
    """
    query = f"SELECT COUNT(*) as row_count FROM {catalog}.{schema}.{table}"
    
    try:
        df = execute_query(query)
        row_count = int(df['row_count'].iloc[0])
        return KPI(label="Total Rows", value=f"{row_count:,}")
    except Exception as e:
        raise Exception(f"Failed to compute row count: {str(e)}")


def compute_date_range(catalog: str, schema: str, table: str, schema_info: SchemaInfo) -> KPI:
    """
    Compute date range KPI (min and max dates) when time column exists.
    
    Args:
        catalog: Unity Catalog name
        schema: Schema name
        table: Table name
        schema_info: SchemaInfo object with detected columns
        
    Returns:
        KPI object with date range or fallback explanation
        
    Raises:
        Exception: If query execution fails
    """
    time_col = get_primary_time_column(schema_info)
    
    if not time_col:
        # Fallback: No time column available
        return KPI(
            label="Date Range",
            value="N/A",
            explanation="No time column detected in dataset"
        )
    
    query = f"""
        SELECT 
            MIN({time_col}) as min_date,
            MAX({time_col}) as max_date
        FROM {catalog}.{schema}.{table}
    """
    
    try:
        df = execute_query(query)
        min_date = df['min_date'].iloc[0]
        max_date = df['max_date'].iloc[0]
        
        if min_date is None or max_date is None:
            return KPI(
                label="Date Range",
                value="No data",
                explanation=f"Time column '{time_col}' contains no valid dates"
            )
        
        # Format dates as strings
        value = f"{min_date} to {max_date}"
        return KPI(label="Date Range", value=value)
    except Exception as e:
        raise Exception(f"Failed to compute date range: {str(e)}")


def compute_data_missingness(catalog: str, schema: str, table: str, schema_info: SchemaInfo) -> KPI:
    """
    Compute data missingness percentage across all columns.
    
    Args:
        catalog: Unity Catalog name
        schema: Schema name
        table: Table name
        schema_info: SchemaInfo object with detected columns
        
    Returns:
        KPI object with missingness percentage
        
    Raises:
        Exception: If query execution fails
    """
    if not schema_info.all_columns:
        return KPI(
            label="Data Missingness",
            value="N/A",
            explanation="No columns detected in dataset"
        )
    
    # Build query to count nulls across all columns
    null_counts = [f"SUM(CASE WHEN {col} IS NULL THEN 1 ELSE 0 END)" for col in schema_info.all_columns]
    null_sum_expr = " + ".join(null_counts)
    
    total_cells = len(schema_info.all_columns)
    
    query = f"""
        SELECT 
            COUNT(*) as row_count,
            ({null_sum_expr}) as total_nulls
        FROM {catalog}.{schema}.{table}
    """
    
    try:
        df = execute_query(query)
        row_count = int(df['row_count'].iloc[0])
        total_nulls = int(df['total_nulls'].iloc[0])
        
        if row_count == 0:
            return KPI(
                label="Data Missingness",
                value="0%",
                explanation="Dataset is empty"
            )
        
        total_cells_count = row_count * total_cells
        missingness_pct = (total_nulls / total_cells_count) * 100
        
        return KPI(label="Data Missingness", value=f"{missingness_pct:.2f}%")
    except Exception as e:
        raise Exception(f"Failed to compute data missingness: {str(e)}")


def compute_failure_rate(catalog: str, schema: str, table: str, schema_info: SchemaInfo) -> KPI:
    """
    Compute failure rate or label distribution when label column exists.
    
    Args:
        catalog: Unity Catalog name
        schema: Schema name
        table: Table name
        schema_info: SchemaInfo object with detected columns
        
    Returns:
        KPI object with failure rate or fallback explanation
        
    Raises:
        Exception: If query execution fails
    """
    label_col = get_primary_label_column(schema_info)
    
    if not label_col:
        # Fallback: Compute categorical column distribution if available
        if schema_info.categorical_columns:
            fallback_col = schema_info.categorical_columns[0]
            return KPI(
                label="Label Distribution",
                value="N/A",
                explanation=f"No label column detected. Consider using '{fallback_col}' for categorical analysis"
            )
        else:
            return KPI(
                label="Failure Rate",
                value="N/A",
                explanation="No label or categorical columns detected in dataset"
            )
    
    query = f"""
        SELECT 
            {label_col},
            COUNT(*) as count
        FROM {catalog}.{schema}.{table}
        GROUP BY {label_col}
        ORDER BY count DESC
    """
    
    try:
        df = execute_query(query)
        
        if df.empty:
            return KPI(
                label="Failure Rate",
                value="No data",
                explanation=f"Label column '{label_col}' contains no data"
            )
        
        total_count = df['count'].sum()
        
        # Try to detect failure/positive class
        # Look for values like 1, True, 'failure', 'fault', 'yes'
        failure_indicators = [1, '1', True, 'true', 'True', 'failure', 'Failure', 'fault', 'Fault', 'yes', 'Yes']
        
        failure_count = 0
        for indicator in failure_indicators:
            if indicator in df[label_col].values:
                failure_count = int(df[df[label_col] == indicator]['count'].iloc[0])
                break
        
        if failure_count > 0:
            failure_rate = (failure_count / total_count) * 100
            return KPI(label="Failure Rate", value=f"{failure_rate:.2f}%")
        else:
            # Show distribution instead
            top_label = df.iloc[0][label_col]
            top_count = int(df.iloc[0]['count'])
            top_pct = (top_count / total_count) * 100
            
            return KPI(
                label="Label Distribution",
                value=f"{top_label}: {top_pct:.1f}%",
                explanation=f"Most common label in '{label_col}' column"
            )
    except Exception as e:
        raise Exception(f"Failed to compute failure rate: {str(e)}")


def compute_unique_asset_count(catalog: str, schema: str, table: str, schema_info: SchemaInfo) -> KPI:
    """
    Compute count of unique assets or entities when ID column exists.
    
    Args:
        catalog: Unity Catalog name
        schema: Schema name
        table: Table name
        schema_info: SchemaInfo object with detected columns
        
    Returns:
        KPI object with unique asset count or fallback explanation
        
    Raises:
        Exception: If query execution fails
    """
    id_col = get_primary_id_column(schema_info)
    
    if not id_col:
        # Fallback: Count distinct values in first categorical column
        if schema_info.categorical_columns:
            fallback_col = schema_info.categorical_columns[0]
            query = f"""
                SELECT COUNT(DISTINCT {fallback_col}) as unique_count
                FROM {catalog}.{schema}.{table}
            """
            
            try:
                df = execute_query(query)
                unique_count = int(df['unique_count'].iloc[0])
                return KPI(
                    label="Unique Values",
                    value=f"{unique_count:,}",
                    explanation=f"No ID column detected. Showing unique count for '{fallback_col}'"
                )
            except Exception as e:
                raise Exception(f"Failed to compute fallback unique count: {str(e)}")
        else:
            return KPI(
                label="Unique Assets",
                value="N/A",
                explanation="No ID or categorical columns detected in dataset"
            )
    
    query = f"""
        SELECT COUNT(DISTINCT {id_col}) as unique_count
        FROM {catalog}.{schema}.{table}
    """
    
    try:
        df = execute_query(query)
        unique_count = int(df['unique_count'].iloc[0])
        return KPI(label="Unique Assets", value=f"{unique_count:,}")
    except Exception as e:
        raise Exception(f"Failed to compute unique asset count: {str(e)}")


def compute_all_kpis(catalog: str, schema: str, table: str, schema_info: SchemaInfo) -> List[KPI]:
    """
    Compute all KPIs for the dataset.
    
    Computes:
    1. Row count (always)
    2. Date range (when time column exists, with fallback)
    3. Data missingness (always)
    4. Failure rate (when label column exists, with fallback)
    5. Unique asset count (when ID column exists, with fallback)
    
    Args:
        catalog: Unity Catalog name
        schema: Schema name
        table: Table name
        schema_info: SchemaInfo object with detected columns
        
    Returns:
        List of KPI objects
        
    Raises:
        Exception: If any KPI computation fails
    """
    kpis = []
    
    # 1. Row count (always available)
    kpis.append(compute_row_count(catalog, schema, table))
    
    # 2. Date range (conditional on time column)
    kpis.append(compute_date_range(catalog, schema, table, schema_info))
    
    # 3. Data missingness (always available)
    kpis.append(compute_data_missingness(catalog, schema, table, schema_info))
    
    # 4. Failure rate (conditional on label column)
    kpis.append(compute_failure_rate(catalog, schema, table, schema_info))
    
    # 5. Unique asset count (conditional on ID column)
    kpis.append(compute_unique_asset_count(catalog, schema, table, schema_info))
    
    return kpis
