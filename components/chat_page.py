"""
Chat page component for conversational data queries.

Provides:
- Streamlit chat UI (st.chat_message, st.chat_input)
- Natural language to SQL conversion via QueryRouter
- Query validation via Guardrails
- Query execution and result display
- Automatic chart generation for chartable results
- Example questions to guide users
"""

import streamlit as st
import pandas as pd
from typing import Optional, Tuple
from components.db import execute_query, get_secure_table_name
from components.schema_introspector import introspect_schema
from components.query_router import create_query_router, QueryIntent
from components.guardrails import validate_query, GuardrailViolation


# Example questions to guide users
EXAMPLE_QUESTIONS = [
    "How many records are in the dataset?",
    "What is the average sensor value?",
    "Show me trends over time",
    "What are the top categories?",
    "What is the failure rate?"
]


def render_chat_page(catalog: str, schema: str, table: str):
    """
    Render the chat interface page.
    
    Implements Requirements 6.1-6.9:
    - Streamlit chat UI
    - Message history
    - Natural language to SQL conversion
    - Query validation via guardrails
    - Result display as dataframe
    - Narrative answers
    - Automatic chart generation
    - Example questions
    - User-friendly error messages
    
    Args:
        catalog: Unity Catalog name
        schema: Schema name
        table: Table name
    """
    st.title("💬 Chat with Your Data")
    st.markdown("Ask questions about your data in natural language.")
    
    # Get secure table name
    table_to_query, is_secure = get_secure_table_name(catalog, schema, table)
    full_table_name = f"{catalog}.{schema}.{table_to_query}"
    
    # Display table info
    st.write(f"**Dataset:** {full_table_name}")
    if is_secure:
        st.info("🔒 Using secure view with governance policies applied")
    
    # Introspect schema for query router
    try:
        schema_info = introspect_schema(catalog, schema, table_to_query)
    except Exception as e:
        st.error(f"Failed to introspect schema: {str(e)}")
        return
    
    # Initialize chat history in session state
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    # Display example questions
    with st.expander("💡 Example Questions", expanded=False):
        st.markdown("Try asking questions like:")
        for i, question in enumerate(EXAMPLE_QUESTIONS, 1):
            st.markdown(f"{i}. {question}")
    
    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Display dataframe if present
            if "dataframe" in message and message["dataframe"] is not None:
                st.dataframe(message["dataframe"], use_container_width=True)
            
            # Display chart if present
            if "chart" in message and message["chart"] is not None:
                _render_chart(message["chart"])
    
    # Chat input
    user_question = st.chat_input("Ask a question about your data...")
    
    if user_question:
        # Add user message to history
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_question
        })
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(user_question)
        
        # Process question and generate response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = _process_question(
                    user_question,
                    catalog,
                    schema,
                    table_to_query,
                    full_table_name,
                    schema_info
                )
            
            # Display response
            st.markdown(response["content"])
            
            # Display dataframe if present
            if response.get("dataframe") is not None:
                st.dataframe(response["dataframe"], use_container_width=True)
            
            # Display chart if present
            if response.get("chart") is not None:
                _render_chart(response["chart"])
            
            # Add assistant response to history
            st.session_state.chat_history.append(response)
    
    # Clear chat button
    if st.button("🗑️ Clear Chat History"):
        st.session_state.chat_history = []
        st.rerun()


def _process_question(
    question: str,
    catalog: str,
    schema: str,
    table: str,
    full_table_name: str,
    schema_info
) -> dict:
    """
    Process user question and generate response.
    
    Args:
        question: User's natural language question
        catalog: Unity Catalog name
        schema: Schema name
        table: Table name
        full_table_name: Full table name with catalog and schema
        schema_info: SchemaInfo object
        
    Returns:
        Dictionary with response content, dataframe, and chart
    """
    try:
        # Create query router
        router = create_query_router(catalog, schema, table, schema_info)
        
        # Convert natural language to SQL
        try:
            sql_query, intent = router.route_query(question)
        except ValueError as e:
            return {
                "role": "assistant",
                "content": f"❌ {str(e)}",
                "dataframe": None,
                "chart": None
            }
        
        # Validate query with guardrails
        try:
            allowed_tables = [full_table_name, table]
            validated_query, limit_added = validate_query(
                sql_query,
                allowed_tables,
                apply_limit=True,
                default_limit=100
            )
        except GuardrailViolation as e:
            return {
                "role": "assistant",
                "content": f"❌ Query validation failed: {str(e)}",
                "dataframe": None,
                "chart": None
            }
        
        # Execute query
        try:
            df = execute_query(validated_query)
        except Exception as e:
            return {
                "role": "assistant",
                "content": f"❌ Query execution failed: {str(e)}",
                "dataframe": None,
                "chart": None
            }
        
        # Generate narrative answer
        narrative = _generate_narrative(df, intent)
        
        # Generate chart if data is chartable
        chart = _generate_chart_if_chartable(df, intent)
        
        return {
            "role": "assistant",
            "content": narrative,
            "dataframe": df,
            "chart": chart
        }
    
    except Exception as e:
        return {
            "role": "assistant",
            "content": f"❌ An error occurred: {str(e)}",
            "dataframe": None,
            "chart": None
        }


def _generate_narrative(df: pd.DataFrame, intent: str) -> str:
    """
    Generate narrative answer from query results.
    
    Args:
        df: Query results dataframe
        intent: Query intent type
        
    Returns:
        Narrative answer string
    """
    if df.empty:
        return "No results found for your query."
    
    # Generate intent-specific narrative
    if intent == QueryIntent.COUNT:
        count = df.iloc[0, 0]
        return f"✅ Found **{count:,}** records in the dataset."
    
    elif intent == QueryIntent.SUMMARY_STATS:
        # Extract statistics from first row
        stats = df.iloc[0].to_dict()
        narrative_parts = ["✅ Here are the summary statistics:"]
        for key, value in stats.items():
            if pd.notna(value):
                if isinstance(value, (int, float)):
                    narrative_parts.append(f"- **{key}**: {value:,.2f}")
                else:
                    narrative_parts.append(f"- **{key}**: {value}")
        return "\n".join(narrative_parts)
    
    elif intent == QueryIntent.FAILURE_RATE:
        if 'failure_rate_percent' in df.columns:
            rate = df.iloc[0]['failure_rate_percent']
            total = df.iloc[0]['total_records']
            failures = df.iloc[0]['failure_count']
            return f"✅ The failure rate is **{rate}%** ({failures:,} failures out of {total:,} total records)."
        return "✅ Here are the failure rate statistics:"
    
    elif intent == QueryIntent.TREND_ANALYSIS:
        return f"✅ Found **{len(df)}** data points showing trends over time."
    
    elif intent == QueryIntent.TOP_CATEGORIES:
        top_category = df.iloc[0, 0]
        top_count = df.iloc[0, 1]
        return f"✅ Found **{len(df)}** categories. The top category is **{top_category}** with {top_count:,} records."
    
    else:
        return f"✅ Query returned **{len(df)}** rows."


def _generate_chart_if_chartable(df: pd.DataFrame, intent: str) -> Optional[dict]:
    """
    Generate chart if results are chartable.
    
    Chartable results are:
    - 2-column dataframes (x, y)
    - Time series data (date/time column + numeric column)
    - Category aggregates (category column + count column)
    
    Args:
        df: Query results dataframe
        intent: Query intent type
        
    Returns:
        Chart configuration dict or None
    """
    if df.empty or len(df.columns) < 2:
        return None
    
    # Check if data is chartable based on intent
    if intent in [QueryIntent.TREND_ANALYSIS, QueryIntent.TOP_CATEGORIES]:
        # These intents typically return chartable data
        if len(df.columns) == 2:
            return {
                "type": "line" if intent == QueryIntent.TREND_ANALYSIS else "bar",
                "x": df.columns[0],
                "y": df.columns[1],
                "data": df
            }
    
    return None


def _render_chart(chart: dict):
    """
    Render chart using Streamlit chart components.
    
    Args:
        chart: Chart configuration dictionary
    """
    if chart["type"] == "line":
        st.line_chart(chart["data"], x=chart["x"], y=chart["y"])
    elif chart["type"] == "bar":
        st.bar_chart(chart["data"], x=chart["x"], y=chart["y"])
    elif chart["type"] == "area":
        st.area_chart(chart["data"], x=chart["x"], y=chart["y"])


if __name__ == "__main__":
    # For standalone testing
    render_chat_page("test_catalog", "test_schema", "test_table")
