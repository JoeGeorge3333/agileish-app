"""
Unit tests for guardrails module.

Tests validation of:
- SELECT-only queries (reject DDL/DML)
- Single statement queries
- Table restrictions
- LIMIT clause injection
- SQL syntax validation
"""

import pytest
from components.guardrails import (
    validate_select_only,
    validate_single_statement,
    validate_table_restriction,
    inject_limit_clause,
    validate_sql_syntax,
    validate_query,
    GuardrailViolation,
    DEFAULT_LIMIT
)


class TestSelectOnlyValidation:
    """Test SELECT-only validation (Requirement 7.1)"""
    
    def test_valid_select_query(self):
        """Valid SELECT query should pass"""
        query = "SELECT * FROM table1"
        validate_select_only(query)  # Should not raise
    
    def test_reject_drop_statement(self):
        """DROP statement should be rejected"""
        query = "DROP TABLE table1"
        with pytest.raises(GuardrailViolation) as exc_info:
            validate_select_only(query)
        assert "DROP" in str(exc_info.value)
        assert "not allowed" in str(exc_info.value)
    
    def test_reject_insert_statement(self):
        """INSERT statement should be rejected"""
        query = "INSERT INTO table1 VALUES (1, 2, 3)"
        with pytest.raises(GuardrailViolation) as exc_info:
            validate_select_only(query)
        assert "INSERT" in str(exc_info.value)
    
    def test_reject_update_statement(self):
        """UPDATE statement should be rejected"""
        query = "UPDATE table1 SET col1 = 'value'"
        with pytest.raises(GuardrailViolation) as exc_info:
            validate_select_only(query)
        assert "UPDATE" in str(exc_info.value)
    
    def test_reject_delete_statement(self):
        """DELETE statement should be rejected"""
        query = "DELETE FROM table1 WHERE id = 1"
        with pytest.raises(GuardrailViolation) as exc_info:
            validate_select_only(query)
        assert "DELETE" in str(exc_info.value)
    
    def test_reject_create_statement(self):
        """CREATE statement should be rejected"""
        query = "CREATE TABLE table1 (id INT)"
        with pytest.raises(GuardrailViolation) as exc_info:
            validate_select_only(query)
        assert "CREATE" in str(exc_info.value)
    
    def test_reject_alter_statement(self):
        """ALTER statement should be rejected"""
        query = "ALTER TABLE table1 ADD COLUMN col1 INT"
        with pytest.raises(GuardrailViolation) as exc_info:
            validate_select_only(query)
        assert "ALTER" in str(exc_info.value)
    
    def test_reject_truncate_statement(self):
        """TRUNCATE statement should be rejected"""
        query = "TRUNCATE TABLE table1"
        with pytest.raises(GuardrailViolation) as exc_info:
            validate_select_only(query)
        assert "TRUNCATE" in str(exc_info.value)
    
    def test_column_named_dropped_allowed(self):
        """Column name containing forbidden keyword should be allowed"""
        query = "SELECT dropped_count FROM table1"
        validate_select_only(query)  # Should not raise


class TestSingleStatementValidation:
    """Test single statement validation (Requirement 7.2)"""
    
    def test_single_statement_allowed(self):
        """Single statement should pass"""
        query = "SELECT * FROM table1"
        validate_single_statement(query)  # Should not raise
    
    def test_reject_multiple_statements(self):
        """Multiple statements should be rejected"""
        query = "SELECT * FROM table1; SELECT * FROM table2"
        with pytest.raises(GuardrailViolation) as exc_info:
            validate_single_statement(query)
        assert "Multiple statements" in str(exc_info.value)
        assert "2 statements" in str(exc_info.value)
    
    def test_trailing_semicolon_allowed(self):
        """Single statement with trailing semicolon should pass"""
        query = "SELECT * FROM table1;"
        validate_single_statement(query)  # Should not raise
    
    def test_reject_three_statements(self):
        """Three statements should be rejected"""
        query = "SELECT 1; SELECT 2; SELECT 3"
        with pytest.raises(GuardrailViolation) as exc_info:
            validate_single_statement(query)
        assert "3 statements" in str(exc_info.value)


class TestTableRestriction:
    """Test table restriction validation (Requirement 7.3)"""
    
    def test_allowed_table_passes(self):
        """Query with allowed table should pass"""
        query = "SELECT * FROM table1"
        allowed = ["table1"]
        validate_table_restriction(query, allowed)  # Should not raise
    
    def test_reject_disallowed_table(self):
        """Query with disallowed table should be rejected"""
        query = "SELECT * FROM table2"
        allowed = ["table1"]
        with pytest.raises(GuardrailViolation) as exc_info:
            validate_table_restriction(query, allowed)
        assert "table2" in str(exc_info.value)
        assert "not in the allowed list" in str(exc_info.value)
    
    def test_fully_qualified_table_name(self):
        """Fully qualified table name should be validated"""
        query = "SELECT * FROM catalog.schema.table1"
        allowed = ["catalog.schema.table1"]
        validate_table_restriction(query, allowed)  # Should not raise
    
    def test_partial_table_name_matching(self):
        """Partial table name should match fully qualified allowed name"""
        query = "SELECT * FROM table1"
        allowed = ["catalog.schema.table1"]
        validate_table_restriction(query, allowed)  # Should not raise
    
    def test_join_with_allowed_tables(self):
        """JOIN with allowed tables should pass"""
        query = "SELECT * FROM table1 JOIN table2 ON table1.id = table2.id"
        allowed = ["table1", "table2"]
        validate_table_restriction(query, allowed)  # Should not raise
    
    def test_reject_join_with_disallowed_table(self):
        """JOIN with disallowed table should be rejected"""
        query = "SELECT * FROM table1 JOIN table3 ON table1.id = table3.id"
        allowed = ["table1", "table2"]
        with pytest.raises(GuardrailViolation) as exc_info:
            validate_table_restriction(query, allowed)
        assert "table3" in str(exc_info.value)
    
    def test_reject_when_no_tables_allowed(self):
        """Query should be rejected when no tables are allowed"""
        query = "SELECT * FROM table1"
        allowed = []
        with pytest.raises(GuardrailViolation) as exc_info:
            validate_table_restriction(query, allowed)
        assert "No tables are currently allowed" in str(exc_info.value)


class TestLimitClauseInjection:
    """Test LIMIT clause injection (Requirement 7.4)"""
    
    def test_inject_limit_when_missing(self):
        """LIMIT should be injected when not present"""
        query = "SELECT * FROM table1"
        result = inject_limit_clause(query)
        assert "LIMIT" in result.upper()
        assert str(DEFAULT_LIMIT) in result
    
    def test_preserve_existing_limit(self):
        """Existing LIMIT should be preserved"""
        query = "SELECT * FROM table1 LIMIT 50"
        result = inject_limit_clause(query)
        assert result == query
        assert "LIMIT 50" in result
    
    def test_custom_default_limit(self):
        """Custom default limit should be applied"""
        query = "SELECT * FROM table1"
        result = inject_limit_clause(query, default_limit=500)
        assert "LIMIT 500" in result
    
    def test_remove_trailing_semicolon(self):
        """Trailing semicolon should be handled correctly"""
        query = "SELECT * FROM table1;"
        result = inject_limit_clause(query)
        assert result.endswith(str(DEFAULT_LIMIT))
        assert not result.endswith(";")


class TestSQLSyntaxValidation:
    """Test SQL syntax validation (Requirement 7.6)"""
    
    def test_valid_select_query(self):
        """Valid SELECT query should pass"""
        query = "SELECT * FROM table1"
        validate_sql_syntax(query)  # Should not raise
    
    def test_reject_empty_query(self):
        """Empty query should be rejected"""
        query = ""
        with pytest.raises(GuardrailViolation) as exc_info:
            validate_sql_syntax(query)
        assert "empty" in str(exc_info.value).lower()
    
    def test_reject_non_select_query(self):
        """Non-SELECT query should be rejected"""
        query = "SHOW TABLES"
        with pytest.raises(GuardrailViolation) as exc_info:
            validate_sql_syntax(query)
        assert "SELECT" in str(exc_info.value)
    
    def test_reject_unbalanced_parentheses(self):
        """Unbalanced parentheses should be rejected"""
        query = "SELECT * FROM table1 WHERE (col1 = 1"
        with pytest.raises(GuardrailViolation) as exc_info:
            validate_sql_syntax(query)
        assert "parentheses" in str(exc_info.value).lower()
    
    def test_reject_unbalanced_quotes(self):
        """Unbalanced quotes should be rejected"""
        query = "SELECT * FROM table1 WHERE col1 = 'value"
        with pytest.raises(GuardrailViolation) as exc_info:
            validate_sql_syntax(query)
        assert "quotes" in str(exc_info.value).lower()
    
    def test_allow_select_without_from(self):
        """SELECT without FROM should be allowed for simple expressions"""
        query = "SELECT 1 + 1"
        validate_sql_syntax(query)  # Should not raise
    
    def test_reject_where_without_from(self):
        """WHERE clause without FROM should be rejected"""
        query = "SELECT * WHERE col1 = 1"
        with pytest.raises(GuardrailViolation) as exc_info:
            validate_sql_syntax(query)
        assert "FROM" in str(exc_info.value)


class TestCompleteValidation:
    """Test complete validation pipeline"""
    
    def test_valid_query_passes_all_checks(self):
        """Valid query should pass all validation checks"""
        query = "SELECT * FROM table1 WHERE col1 = 1"
        allowed = ["table1"]
        validated_query, limit_added = validate_query(query, allowed)
        
        assert "LIMIT" in validated_query.upper()
        assert limit_added is True
    
    def test_query_with_limit_not_modified(self):
        """Query with existing LIMIT should not be modified"""
        query = "SELECT * FROM table1 LIMIT 50"
        allowed = ["table1"]
        validated_query, limit_added = validate_query(query, allowed)
        
        assert validated_query == query
        assert limit_added is False
    
    def test_invalid_query_raises_descriptive_error(self):
        """Invalid query should raise descriptive error"""
        query = "DROP TABLE table1"
        allowed = ["table1"]
        
        with pytest.raises(GuardrailViolation) as exc_info:
            validate_query(query, allowed)
        
        # Error message should be descriptive (either syntax or SELECT-only check)
        error_msg = str(exc_info.value)
        assert "Query rejected" in error_msg
        # Should mention either DROP or SELECT requirement
        assert ("DROP" in error_msg or "SELECT" in error_msg)
    
    def test_multiple_violations_caught(self):
        """First violation should be caught and reported"""
        query = "DROP TABLE table1; DROP TABLE table2"
        allowed = ["table1"]
        
        with pytest.raises(GuardrailViolation):
            validate_query(query, allowed)
    
    def test_skip_limit_injection(self):
        """LIMIT injection can be skipped"""
        query = "SELECT * FROM table1"
        allowed = ["table1"]
        validated_query, limit_added = validate_query(query, allowed, apply_limit=False)
        
        assert "LIMIT" not in validated_query.upper()
        assert limit_added is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
