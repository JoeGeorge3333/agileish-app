"""
Unit tests for query router module.

Tests:
- Intent template matching
- SQL generation for each intent type
- Handling of ambiguous queries
- Modular interface
"""

import pytest
from components.query_router import (
    QueryRouter,
    LLMQueryRouter,
    QueryIntent,
    create_query_router
)
from components.schema_introspector import SchemaInfo


@pytest.fixture
def basic_schema_info():
    """Create a basic SchemaInfo for testing."""
    schema = SchemaInfo()
    schema.all_columns = ['id', 'timestamp', 'sensor_value', 'category', 'failure']
    schema.time_columns = ['timestamp']
    schema.id_columns = ['id']
    schema.label_columns = ['failure']
    schema.categorical_columns = ['category']
    schema.numeric_columns = ['sensor_value']
    schema.column_types = {
        'id': 'int',
        'timestamp': 'timestamp',
        'sensor_value': 'double',
        'category': 'string',
        'failure': 'int'
    }
    return schema


@pytest.fixture
def minimal_schema_info():
    """Create a minimal SchemaInfo with no special columns."""
    schema = SchemaInfo()
    schema.all_columns = ['col1', 'col2']
    schema.time_columns = []
    schema.id_columns = []
    schema.label_columns = []
    schema.categorical_columns = []
    schema.numeric_columns = []
    schema.column_types = {'col1': 'string', 'col2': 'string'}
    return schema


@pytest.fixture
def query_router(basic_schema_info):
    """Create a QueryRouter instance for testing."""
    return QueryRouter(
        catalog='test_catalog',
        schema='test_schema',
        table='test_table',
        schema_info=basic_schema_info
    )


class TestIntentDetection:
    """Test intent detection from natural language (Requirement 6.4)"""
    
    def test_detect_count_intent_how_many(self, query_router):
        """Detect count intent from 'how many' question"""
        intent = query_router._detect_intent("How many records are there?")
        assert intent == QueryIntent.COUNT
    
    def test_detect_count_intent_count(self, query_router):
        """Detect count intent from 'count' question"""
        intent = query_router._detect_intent("Count the total records")
        assert intent == QueryIntent.COUNT
    
    def test_detect_count_intent_number_of(self, query_router):
        """Detect count intent from 'number of' question"""
        intent = query_router._detect_intent("What is the number of entries?")
        assert intent == QueryIntent.COUNT
    
    def test_detect_summary_stats_intent_average(self, query_router):
        """Detect summary stats intent from 'average' question"""
        intent = query_router._detect_intent("What is the average sensor value?")
        assert intent == QueryIntent.SUMMARY_STATS
    
    def test_detect_summary_stats_intent_statistics(self, query_router):
        """Detect summary stats intent from 'statistics' question"""
        intent = query_router._detect_intent("Show me statistics")
        assert intent == QueryIntent.SUMMARY_STATS
    
    def test_detect_trend_intent_over_time(self, query_router):
        """Detect trend intent from 'over time' question"""
        intent = query_router._detect_intent("Show trends over time")
        assert intent == QueryIntent.TREND_ANALYSIS
    
    def test_detect_trend_intent_trend(self, query_router):
        """Detect trend intent from 'trend' question"""
        intent = query_router._detect_intent("What are the trends?")
        assert intent == QueryIntent.TREND_ANALYSIS
    
    def test_detect_top_categories_intent_top(self, query_router):
        """Detect top categories intent from 'top' question"""
        intent = query_router._detect_intent("What are the top categories?")
        assert intent == QueryIntent.TOP_CATEGORIES
    
    def test_detect_top_categories_intent_most_common(self, query_router):
        """Detect top categories intent from 'most common' question"""
        intent = query_router._detect_intent("Show me the most common categories")
        assert intent == QueryIntent.TOP_CATEGORIES
    
    def test_detect_failure_rate_intent(self, query_router):
        """Detect failure rate intent"""
        intent = query_router._detect_intent("What is the failure rate?")
        assert intent == QueryIntent.FAILURE_RATE
    
    def test_detect_failure_rate_intent_percentage(self, query_router):
        """Detect failure rate intent from 'failure percentage' question"""
        intent = query_router._detect_intent("Show me the failure percentage")
        assert intent == QueryIntent.FAILURE_RATE
    
    def test_detect_unknown_intent(self, query_router):
        """Detect unknown intent for ambiguous question"""
        intent = query_router._detect_intent("Tell me something interesting")
        assert intent == QueryIntent.UNKNOWN


class TestCountQueryGeneration:
    """Test count query generation (Requirement 6.4)"""
    
    def test_generate_count_query(self, query_router):
        """Generate valid count query"""
        sql, intent = query_router.route_query("How many records?")
        
        assert intent == QueryIntent.COUNT
        assert "SELECT COUNT(*)" in sql.upper()
        assert "test_catalog.test_schema.test_table" in sql
    
    def test_count_query_structure(self, query_router):
        """Count query should have correct structure"""
        sql = query_router._generate_count_query("How many?")
        
        assert sql.upper().startswith("SELECT")
        assert "COUNT(*)" in sql.upper()
        assert "FROM" in sql.upper()


class TestSummaryStatsQueryGeneration:
    """Test summary statistics query generation (Requirement 6.4)"""
    
    def test_generate_summary_stats_query(self, query_router):
        """Generate valid summary statistics query"""
        sql, intent = query_router.route_query("What are the average values?")
        
        assert intent == QueryIntent.SUMMARY_STATS
        assert "AVG" in sql.upper()
        assert "MIN" in sql.upper()
        assert "MAX" in sql.upper()
        assert "COUNT" in sql.upper()
        assert "sensor_value" in sql
    
    def test_summary_stats_without_numeric_columns(self, minimal_schema_info):
        """Summary stats should fail gracefully without numeric columns"""
        router = QueryRouter('cat', 'sch', 'tbl', minimal_schema_info)
        
        with pytest.raises(ValueError) as exc_info:
            router._generate_summary_stats_query("Show statistics")
        
        assert "No numeric columns" in str(exc_info.value)


class TestTrendAnalysisQueryGeneration:
    """Test trend analysis query generation (Requirement 6.4)"""
    
    def test_generate_trend_analysis_query(self, query_router):
        """Generate valid trend analysis query"""
        sql, intent = query_router.route_query("Show me trends over time")
        
        assert intent == QueryIntent.TREND_ANALYSIS
        assert "timestamp" in sql
        assert "GROUP BY" in sql.upper()
        assert "ORDER BY" in sql.upper()
        assert "DATE" in sql.upper()
    
    def test_trend_analysis_without_time_column(self, minimal_schema_info):
        """Trend analysis should fail gracefully without time column"""
        router = QueryRouter('cat', 'sch', 'tbl', minimal_schema_info)
        
        with pytest.raises(ValueError) as exc_info:
            router._generate_trend_analysis_query("Show trends")
        
        assert "No time column" in str(exc_info.value)
    
    def test_trend_analysis_with_numeric_column(self, query_router):
        """Trend analysis should include numeric aggregation when available"""
        sql = query_router._generate_trend_analysis_query("Show trends")
        
        assert "AVG(sensor_value)" in sql
        assert "record_count" in sql


class TestTopCategoriesQueryGeneration:
    """Test top categories query generation (Requirement 6.4)"""
    
    def test_generate_top_categories_query(self, query_router):
        """Generate valid top categories query"""
        sql, intent = query_router.route_query("What are the top categories?")
        
        assert intent == QueryIntent.TOP_CATEGORIES
        assert "category" in sql
        assert "GROUP BY" in sql.upper()
        assert "ORDER BY" in sql.upper()
        assert "DESC" in sql.upper()
        assert "LIMIT" in sql.upper()
    
    def test_top_categories_without_categorical_columns(self, minimal_schema_info):
        """Top categories should fail gracefully without categorical columns"""
        router = QueryRouter('cat', 'sch', 'tbl', minimal_schema_info)
        
        with pytest.raises(ValueError) as exc_info:
            router._generate_top_categories_query("Show top categories")
        
        assert "No categorical columns" in str(exc_info.value)


class TestFailureRateQueryGeneration:
    """Test failure rate query generation (Requirement 6.4)"""
    
    def test_generate_failure_rate_query(self, query_router):
        """Generate valid failure rate query"""
        sql, intent = query_router.route_query("What is the failure rate?")
        
        assert intent == QueryIntent.FAILURE_RATE
        assert "failure" in sql
        assert "CASE WHEN" in sql.upper()
        assert "failure_rate_percent" in sql
    
    def test_failure_rate_without_label_column(self, minimal_schema_info):
        """Failure rate should fail gracefully without label column"""
        router = QueryRouter('cat', 'sch', 'tbl', minimal_schema_info)
        
        with pytest.raises(ValueError) as exc_info:
            router._generate_failure_rate_query("What is the failure rate?")
        
        assert "No label column" in str(exc_info.value)


class TestAmbiguousQueries:
    """Test handling of ambiguous queries (Requirement 12.1)"""
    
    def test_unknown_intent_raises_error(self, query_router):
        """Unknown intent should raise descriptive error"""
        with pytest.raises(ValueError) as exc_info:
            query_router.route_query("Tell me something random")
        
        error_msg = str(exc_info.value)
        assert "couldn't understand" in error_msg.lower()
        # Should provide examples
        assert "Counts" in error_msg or "count" in error_msg.lower()


class TestModularInterface:
    """Test modular interface for alternative implementations (Requirement 12.2)"""
    
    def test_create_template_router(self, basic_schema_info):
        """Create template-based router using factory"""
        router = create_query_router(
            'cat', 'sch', 'tbl', basic_schema_info, use_llm=False
        )
        
        assert isinstance(router, QueryRouter)
        assert not isinstance(router, LLMQueryRouter)
    
    def test_create_llm_router(self, basic_schema_info):
        """Create LLM-based router using factory"""
        router = create_query_router(
            'cat', 'sch', 'tbl', basic_schema_info, use_llm=True
        )
        
        assert isinstance(router, LLMQueryRouter)
    
    def test_llm_router_fallback(self, basic_schema_info):
        """LLM router should fall back to template matching"""
        router = LLMQueryRouter('cat', 'sch', 'tbl', basic_schema_info)
        
        # Should work like template router for now
        sql, intent = router.route_query("How many records?")
        assert intent == QueryIntent.COUNT
        assert "COUNT(*)" in sql.upper()


class TestFullTableName:
    """Test full table name construction"""
    
    def test_full_table_name_construction(self, query_router):
        """Full table name should be properly constructed"""
        assert query_router.full_table_name == "test_catalog.test_schema.test_table"
    
    def test_queries_use_full_table_name(self, query_router):
        """All generated queries should use full table name"""
        sql, _ = query_router.route_query("How many records?")
        assert "test_catalog.test_schema.test_table" in sql


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
