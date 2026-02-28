"""
Guardrails module for SQL query validation and safety enforcement.

Provides functions for:
- SELECT-only validation (reject DDL/DML)
- Single statement validation
- Table restriction validation
- Automatic LIMIT clause injection
- SQL syntax validation
- Descriptive error messages for violations
"""

import re
from typing import Tuple, Optional


# DDL/DML keywords that should be rejected
FORBIDDEN_KEYWORDS = [
    'DROP', 'CREATE', 'ALTER', 'TRUNCATE', 'RENAME',  # DDL
    'INSERT', 'UPDATE', 'DELETE', 'MERGE',  # DML
    'GRANT', 'REVOKE',  # DCL
    'EXEC', 'EXECUTE', 'CALL',  # Stored procedures
]

# Default row limit for queries without explicit LIMIT
DEFAULT_LIMIT = 1000


class GuardrailViolation(Exception):
    """Exception raised when a query violates guardrails."""
    pass


def validate_select_only(query: str) -> None:
    """
    Validate that query is SELECT-only and reject DDL/DML statements.
    
    Implements Requirement 7.1: Guardrails_Engine SHALL enforce SELECT-only 
    queries and reject DDL or DML statements.
    
    Args:
        query: SQL query string to validate
        
    Raises:
        GuardrailViolation: If query contains forbidden keywords
    """
    # Remove comments and normalize whitespace
    query_normalized = _normalize_query(query)
    
    # Check for forbidden keywords
    for keyword in FORBIDDEN_KEYWORDS:
        # Use word boundaries to avoid false positives (e.g., "dropped" column name)
        pattern = r'\b' + keyword + r'\b'
        if re.search(pattern, query_normalized, re.IGNORECASE):
            raise GuardrailViolation(
                f"Query rejected: {keyword} statements are not allowed. "
                f"Only SELECT queries are permitted for data safety."
            )


def validate_single_statement(query: str) -> None:
    """
    Validate that query contains only a single statement.
    
    Implements Requirement 7.2: Guardrails_Engine SHALL enforce single 
    statement execution and reject multi-statement queries.
    
    Args:
        query: SQL query string to validate
        
    Raises:
        GuardrailViolation: If query contains multiple statements
    """
    # Remove comments
    query_no_comments = _remove_comments(query)
    
    # Split by semicolons and filter out empty statements
    statements = [s.strip() for s in query_no_comments.split(';') if s.strip()]
    
    if len(statements) > 1:
        raise GuardrailViolation(
            f"Query rejected: Multiple statements detected ({len(statements)} statements). "
            f"Only single statement queries are allowed for security."
        )


def validate_table_restriction(query: str, allowed_tables: list) -> None:
    """
    Validate that query only accesses allowed tables.
    
    Implements Requirement 7.3: Guardrails_Engine SHALL restrict queries 
    to the selected table or approved secure views.
    
    Args:
        query: SQL query string to validate
        allowed_tables: List of allowed table names (can include catalog.schema.table format)
        
    Raises:
        GuardrailViolation: If query references tables not in allowed list
    """
    if not allowed_tables:
        raise GuardrailViolation(
            "Query rejected: No tables are currently allowed. "
            "Please select a dataset first."
        )
    
    # Normalize query
    query_normalized = _normalize_query(query)
    
    # Extract table references from FROM and JOIN clauses
    # Pattern matches: FROM table_name, JOIN table_name
    # Supports: table, schema.table, catalog.schema.table
    table_pattern = r'\b(?:FROM|JOIN)\s+([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+){0,2})\b'
    referenced_tables = re.findall(table_pattern, query_normalized, re.IGNORECASE)
    
    # Normalize allowed tables for comparison (lowercase, handle different formats)
    allowed_normalized = set()
    for table in allowed_tables:
        # Add the full table name
        allowed_normalized.add(table.lower())
        # Also add just the table name without catalog/schema for flexible matching
        table_parts = table.split('.')
        if len(table_parts) > 1:
            allowed_normalized.add(table_parts[-1].lower())  # Just table name
        if len(table_parts) > 2:
            allowed_normalized.add(f"{table_parts[-2]}.{table_parts[-1]}".lower())  # schema.table
    
    # Check each referenced table
    for table_ref in referenced_tables:
        table_ref_lower = table_ref.lower()
        
        # Check if table reference matches any allowed format
        if table_ref_lower not in allowed_normalized:
            raise GuardrailViolation(
                f"Query rejected: Table '{table_ref}' is not in the allowed list. "
                f"Only the selected dataset can be queried. "
                f"Allowed tables: {', '.join(allowed_tables)}"
            )


def inject_limit_clause(query: str, default_limit: int = DEFAULT_LIMIT) -> str:
    """
    Inject LIMIT clause if query doesn't already have one.
    
    Implements Requirement 7.4: WHEN a query does not specify a row limit, 
    Guardrails_Engine SHALL apply a default LIMIT clause.
    
    Args:
        query: SQL query string
        default_limit: Default row limit to apply (default: 1000)
        
    Returns:
        Query with LIMIT clause added if not present
    """
    query_normalized = _normalize_query(query)
    
    # Check if query already has a LIMIT clause
    if re.search(r'\bLIMIT\s+\d+', query_normalized, re.IGNORECASE):
        return query
    
    # Remove trailing semicolon if present
    query_stripped = query.rstrip().rstrip(';')
    
    # Add LIMIT clause
    return f"{query_stripped} LIMIT {default_limit}"


def validate_sql_syntax(query: str) -> None:
    """
    Perform basic SQL syntax validation.
    
    Implements Requirement 7.6: Guardrails_Engine SHALL validate SQL 
    syntax before execution.
    
    This performs basic validation checks. Full syntax validation happens
    at query execution time by the database engine.
    
    Args:
        query: SQL query string to validate
        
    Raises:
        GuardrailViolation: If query has obvious syntax issues
    """
    if not query or not query.strip():
        raise GuardrailViolation("Query rejected: Query cannot be empty.")
    
    query_normalized = _normalize_query(query)
    
    # Check for basic SELECT structure
    if not re.search(r'\bSELECT\b', query_normalized, re.IGNORECASE):
        raise GuardrailViolation(
            "Query rejected: Query must be a SELECT statement."
        )
    
    # Check for FROM clause (required for most queries)
    # Allow queries without FROM for simple expressions like SELECT 1+1
    # But if there's a WHERE/GROUP BY/ORDER BY, FROM is required
    has_clauses = any(
        re.search(rf'\b{clause}\b', query_normalized, re.IGNORECASE)
        for clause in ['WHERE', 'GROUP BY', 'ORDER BY', 'HAVING', 'JOIN']
    )
    
    if has_clauses and not re.search(r'\bFROM\b', query_normalized, re.IGNORECASE):
        raise GuardrailViolation(
            "Query rejected: Query with WHERE/GROUP BY/ORDER BY/HAVING/JOIN "
            "clauses must include a FROM clause."
        )
    
    # Check for balanced parentheses
    if query.count('(') != query.count(')'):
        raise GuardrailViolation(
            "Query rejected: Unbalanced parentheses detected."
        )
    
    # Check for balanced quotes (basic check)
    single_quotes = query.count("'")
    if single_quotes % 2 != 0:
        raise GuardrailViolation(
            "Query rejected: Unbalanced single quotes detected."
        )


def validate_query(
    query: str,
    allowed_tables: list,
    apply_limit: bool = True,
    default_limit: int = DEFAULT_LIMIT
) -> Tuple[str, bool]:
    """
    Validate query against all guardrails and return safe query.
    
    Implements Requirements 7.1-7.6: Complete guardrails validation pipeline.
    
    This is the main entry point for query validation. It performs all
    validation checks and returns a safe query with LIMIT clause applied.
    
    Args:
        query: SQL query string to validate
        allowed_tables: List of allowed table names
        apply_limit: Whether to inject LIMIT clause if missing (default: True)
        default_limit: Default row limit to apply (default: 1000)
        
    Returns:
        Tuple of (validated_query, limit_was_added)
        - validated_query: Safe query string with LIMIT clause if needed
        - limit_was_added: True if LIMIT clause was injected
        
    Raises:
        GuardrailViolation: If query violates any guardrail (with descriptive message)
    """
    # Requirement 7.6: Validate SQL syntax
    validate_sql_syntax(query)
    
    # Requirement 7.1: Enforce SELECT-only
    validate_select_only(query)
    
    # Requirement 7.2: Enforce single statement
    validate_single_statement(query)
    
    # Requirement 7.3: Restrict to allowed tables
    validate_table_restriction(query, allowed_tables)
    
    # Requirement 7.4: Apply LIMIT clause if needed
    limit_was_added = False
    validated_query = query
    
    if apply_limit:
        original_normalized = _normalize_query(query)
        validated_query = inject_limit_clause(query, default_limit)
        new_normalized = _normalize_query(validated_query)
        limit_was_added = (original_normalized != new_normalized)
    
    return (validated_query, limit_was_added)


def _normalize_query(query: str) -> str:
    """
    Normalize query for pattern matching.
    
    Removes comments and normalizes whitespace while preserving structure.
    
    Args:
        query: SQL query string
        
    Returns:
        Normalized query string
    """
    # Remove comments but preserve structure
    query_no_comments = _remove_comments(query)
    
    # Normalize whitespace (collapse multiple spaces to single space)
    normalized = re.sub(r'\s+', ' ', query_no_comments)
    
    return normalized.strip()


def _remove_comments(query: str) -> str:
    """
    Remove SQL comments from query.
    
    Handles both line comments (--) and block comments (/* */).
    
    Args:
        query: SQL query string
        
    Returns:
        Query with comments removed
    """
    # Remove line comments (-- comment)
    query = re.sub(r'--[^\n]*', '', query)
    
    # Remove block comments (/* comment */)
    query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
    
    return query
