"""
Query router module for converting natural language to SQL queries.

Provides functions for:
- Template matching for intent detection
- SQL query generation from natural language
- Support for multiple query intents (count, summary, trend, top categories, failure rate)
- Modular interface for future LLM integration
"""

import re
from typing import Optional, Dict, Any, Tuple
from components.schema_introspector import SchemaInfo


class QueryIntent:
    """Enumeration of supported query intents."""
    COUNT = "count"
    SUMMARY_STATS = "summary_stats"
    TREND_ANALYSIS = "trend_analysis"
    TOP_CATEGORIES = "top_categories"
    FAILURE_RATE = "failure_rate"
    UNKNOWN = "unknown"


class QueryRouter:
    """
    Routes natural language questions to SQL queries using template matching.
    
    Implements Requirements 6.3, 6.4, 12.1, 12.2, 12.3, 12.4:
    - Template-based query generation (default method)
    - Support for multiple query intents
    - Modular interface for alternative implementations
    - No external LLM dependencies required
    """
    
    def __init__(self, catalog: str, schema: str, table: str, schema_info: SchemaInfo):
        """
        Initialize query router with table context.
        
        Args:
            catalog: Unity Catalog name
            schema: Schema name
            table: Table name (can be secure view)
            schema_info: SchemaInfo object with detected column types
        """
        self.catalog = catalog
        self.schema = schema
        self.table = table
        self.schema_info = schema_info
        self.full_table_name = f"{catalog}.{schema}.{table}"
    
    def route_query(self, question: str) -> Tuple[str, str]:
        """
        Convert natural language question to SQL query.
        
        This is the main entry point for query routing. It detects intent
        and generates appropriate SQL query.
        
        Args:
            question: Natural language question from user
            
        Returns:
            Tuple of (sql_query, intent)
            - sql_query: Generated SQL query string
            - intent: Detected intent type (from QueryIntent)
            
        Raises:
            ValueError: If question cannot be converted to SQL
        """
        # Detect intent
        intent = self._detect_intent(question)
        
        # Generate SQL based on intent
        if intent == QueryIntent.COUNT:
            return (self._generate_count_query(question), intent)
        elif intent == QueryIntent.SUMMARY_STATS:
            return (self._generate_summary_stats_query(question), intent)
        elif intent == QueryIntent.TREND_ANALYSIS:
            return (self._generate_trend_analysis_query(question), intent)
        elif intent == QueryIntent.TOP_CATEGORIES:
            return (self._generate_top_categories_query(question), intent)
        elif intent == QueryIntent.FAILURE_RATE:
            return (self._generate_failure_rate_query(question), intent)
        else:
            raise ValueError(
                "I couldn't understand your question. Please try asking about:\n"
                "- Counts (e.g., 'How many records?')\n"
                "- Summary statistics (e.g., 'What are the average values?')\n"
                "- Trends over time (e.g., 'Show me trends')\n"
                "- Top categories (e.g., 'What are the top categories?')\n"
                "- Failure rates (e.g., 'What is the failure rate?')"
            )
    
    def _detect_intent(self, question: str) -> str:
        """
        Detect query intent from natural language question.
        
        Uses pattern matching to identify user intent.
        
        Args:
            question: Natural language question
            
        Returns:
            Intent type (from QueryIntent)
        """
        question_lower = question.lower()
        
        # Count query patterns
        count_patterns = [
            r'\bhow many\b',
            r'\bcount\b',
            r'\bnumber of\b',
            r'\btotal (records|rows|entries)\b',
        ]
        if any(re.search(pattern, question_lower) for pattern in count_patterns):
            return QueryIntent.COUNT
        
        # Failure rate patterns
        failure_patterns = [
            r'\bfailure rate\b',
            r'\bfailure percentage\b',
            r'\bfailure ratio\b',
            r'\bhow many fail\b',
            r'\bpercent.*fail\b',
        ]
        if any(re.search(pattern, question_lower) for pattern in failure_patterns):
            return QueryIntent.FAILURE_RATE
        
        # Summary statistics patterns
        summary_patterns = [
            r'\baverage\b',
            r'\bmean\b',
            r'\bmedian\b',
            r'\bmin\b',
            r'\bmax\b',
            r'\bsum\b',
            r'\bstatistics\b',
            r'\bsummary\b',
            r'\bstats\b',
        ]
        if any(re.search(pattern, question_lower) for pattern in summary_patterns):
            return QueryIntent.SUMMARY_STATS
        
        # Trend analysis patterns
        trend_patterns = [
            r'\btrends?\b',
            r'\bover time\b',
            r'\btime series\b',
            r'\bhistorical\b',
            r'\bchanges?\b',
            r'\bprogression\b',
        ]
        if any(re.search(pattern, question_lower) for pattern in trend_patterns):
            return QueryIntent.TREND_ANALYSIS
        
        # Top categories patterns
        top_patterns = [
            r'\btop\b',
            r'\bmost (common|frequent)\b',
            r'\bhighest\b',
            r'\blargest\b',
            r'\bbest\b',
            r'\bworst\b',
            r'\bcategories\b',
            r'\bbreakdown\b',
        ]
        if any(re.search(pattern, question_lower) for pattern in top_patterns):
            return QueryIntent.TOP_CATEGORIES
        
        return QueryIntent.UNKNOWN
    
    def _generate_count_query(self, question: str) -> str:
        """
        Generate SQL query for count intent.
        
        Args:
            question: Natural language question
            
        Returns:
            SQL query string
        """
        return f"SELECT COUNT(*) as total_count FROM {self.full_table_name}"
    
    def _generate_summary_stats_query(self, question: str) -> str:
        """
        Generate SQL query for summary statistics intent.
        
        Args:
            question: Natural language question
            
        Returns:
            SQL query string
            
        Raises:
            ValueError: If no numeric columns available
        """
        if not self.schema_info.numeric_columns:
            raise ValueError(
                "Cannot generate summary statistics: No numeric columns found in the dataset."
            )
        
        # Use first numeric column for statistics
        numeric_col = self.schema_info.numeric_columns[0]
        
        query = f"""
SELECT 
    COUNT(*) as count,
    AVG({numeric_col}) as avg_{numeric_col},
    MIN({numeric_col}) as min_{numeric_col},
    MAX({numeric_col}) as max_{numeric_col}
FROM {self.full_table_name}
        """.strip()
        
        return query
    
    def _generate_trend_analysis_query(self, question: str) -> str:
        """
        Generate SQL query for trend analysis intent.
        
        Args:
            question: Natural language question
            
        Returns:
            SQL query string
            
        Raises:
            ValueError: If no time column available
        """
        if not self.schema_info.time_columns:
            raise ValueError(
                "Cannot generate trend analysis: No time column found in the dataset."
            )
        
        time_col = self.schema_info.time_columns[0]
        
        # If we have numeric columns, show trend of first numeric column
        if self.schema_info.numeric_columns:
            numeric_col = self.schema_info.numeric_columns[0]
            query = f"""
SELECT 
    DATE({time_col}) as date,
    COUNT(*) as record_count,
    AVG({numeric_col}) as avg_{numeric_col}
FROM {self.full_table_name}
GROUP BY DATE({time_col})
ORDER BY date
            """.strip()
        else:
            # Just show record count over time
            query = f"""
SELECT 
    DATE({time_col}) as date,
    COUNT(*) as record_count
FROM {self.full_table_name}
GROUP BY DATE({time_col})
ORDER BY date
            """.strip()
        
        return query
    
    def _generate_top_categories_query(self, question: str) -> str:
        """
        Generate SQL query for top categories intent.
        
        Args:
            question: Natural language question
            
        Returns:
            SQL query string
            
        Raises:
            ValueError: If no categorical columns available
        """
        if not self.schema_info.categorical_columns:
            raise ValueError(
                "Cannot generate top categories: No categorical columns found in the dataset."
            )
        
        # Use first categorical column
        cat_col = self.schema_info.categorical_columns[0]
        
        query = f"""
SELECT 
    {cat_col},
    COUNT(*) as count
FROM {self.full_table_name}
GROUP BY {cat_col}
ORDER BY count DESC
LIMIT 10
        """.strip()
        
        return query
    
    def _generate_failure_rate_query(self, question: str) -> str:
        """
        Generate SQL query for failure rate intent.
        
        Args:
            question: Natural language question
            
        Returns:
            SQL query string
            
        Raises:
            ValueError: If no label column available
        """
        if not self.schema_info.label_columns:
            raise ValueError(
                "Cannot calculate failure rate: No label column found in the dataset."
            )
        
        label_col = self.schema_info.label_columns[0]
        
        query = f"""
SELECT 
    COUNT(*) as total_records,
    SUM(CASE WHEN {label_col} = 1 THEN 1 ELSE 0 END) as failure_count,
    ROUND(100.0 * SUM(CASE WHEN {label_col} = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) as failure_rate_percent
FROM {self.full_table_name}
        """.strip()
        
        return query


class LLMQueryRouter(QueryRouter):
    """
    Alternative query router using LLM for query generation.
    
    This class provides the interface for future LLM integration.
    Implements Requirement 12.2: Modular interface for alternative implementations.
    Implements Requirement 12.4: Support for external LLM integration.
    
    Note: This is a placeholder for future LLM integration (e.g., Genie Conversation API).
    The actual LLM implementation would be added here.
    """
    
    def __init__(self, catalog: str, schema: str, table: str, schema_info: SchemaInfo, llm_config: Optional[Dict[str, Any]] = None):
        """
        Initialize LLM-based query router.
        
        Args:
            catalog: Unity Catalog name
            schema: Schema name
            table: Table name
            schema_info: SchemaInfo object
            llm_config: Optional configuration for LLM service
        """
        super().__init__(catalog, schema, table, schema_info)
        self.llm_config = llm_config or {}
    
    def route_query(self, question: str) -> Tuple[str, str]:
        """
        Convert natural language to SQL using LLM.
        
        This method would integrate with an external LLM service.
        For now, it falls back to template-based routing.
        
        Args:
            question: Natural language question
            
        Returns:
            Tuple of (sql_query, intent)
        """
        # TODO: Implement LLM integration here
        # For now, fall back to template-based routing
        return super().route_query(question)


def create_query_router(
    catalog: str,
    schema: str,
    table: str,
    schema_info: SchemaInfo,
    use_llm: bool = False,
    llm_config: Optional[Dict[str, Any]] = None
) -> QueryRouter:
    """
    Factory function to create appropriate query router.
    
    Implements Requirement 12.2: Interface for swapping implementations.
    
    Args:
        catalog: Unity Catalog name
        schema: Schema name
        table: Table name
        schema_info: SchemaInfo object
        use_llm: Whether to use LLM-based router (default: False)
        llm_config: Optional LLM configuration
        
    Returns:
        QueryRouter instance (template-based or LLM-based)
    """
    if use_llm:
        return LLMQueryRouter(catalog, schema, table, schema_info, llm_config)
    else:
        return QueryRouter(catalog, schema, table, schema_info)
