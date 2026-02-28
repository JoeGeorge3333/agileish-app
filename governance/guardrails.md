# Query Guardrails Documentation

## Overview

The Guardrails Engine enforces query safety and security policies to protect data integrity and prevent unauthorized operations. All queries are validated before execution.

## Guardrail Rules

### 1. SELECT-Only Validation

**Rule**: Only SELECT statements are permitted. All DDL, DML, and DCL statements are rejected.

**Forbidden Keywords**:
- **DDL**: DROP, CREATE, ALTER, TRUNCATE, RENAME
- **DML**: INSERT, UPDATE, DELETE, MERGE
- **DCL**: GRANT, REVOKE
- **Procedures**: EXEC, EXECUTE, CALL

**Implementation**:
```python
def validate_select_only(query: str) -> None:
    """Reject queries containing forbidden keywords."""
    forbidden_keywords = [
        'DROP', 'CREATE', 'ALTER', 'TRUNCATE', 'RENAME',
        'INSERT', 'UPDATE', 'DELETE', 'MERGE',
        'GRANT', 'REVOKE',
        'EXEC', 'EXECUTE', 'CALL'
    ]
    # Check for forbidden keywords with word boundaries
    for keyword in forbidden_keywords:
        if re.search(r'\b' + keyword + r'\b', query, re.IGNORECASE):
            raise GuardrailViolation(f"Query rejected: {keyword} statements are not allowed.")
```

**Examples**:
```sql
-- ✅ ALLOWED
SELECT * FROM sensor_data;
SELECT COUNT(*) FROM sensor_data WHERE status = 'active';

-- ❌ REJECTED
DROP TABLE sensor_data;
INSERT INTO sensor_data VALUES (1, 2, 3);
UPDATE sensor_data SET status = 'inactive';
DELETE FROM sensor_data WHERE id = 1;
```

### 2. Single Statement Validation

**Rule**: Only single SQL statements are allowed. Multi-statement queries are rejected.

**Purpose**: Prevents SQL injection attacks and unauthorized batch operations.

**Implementation**:
```python
def validate_single_statement(query: str) -> None:
    """Ensure query contains only one statement."""
    statements = [s.strip() for s in query.split(';') if s.strip()]
    if len(statements) > 1:
        raise GuardrailViolation(
            f"Query rejected: Multiple statements detected ({len(statements)} statements). "
            f"Only single statement queries are allowed for security."
        )
```

**Examples**:
```sql
-- ✅ ALLOWED
SELECT * FROM sensor_data;
SELECT * FROM sensor_data LIMIT 100;

-- ❌ REJECTED
SELECT * FROM sensor_data; SELECT * FROM other_table;
SELECT COUNT(*) FROM table1; DROP TABLE table2;
```

### 3. Table Restriction Validation

**Rule**: Queries can only access the currently selected table or its secure view.

**Purpose**: Prevents unauthorized access to other tables in the catalog.

**Implementation**:
```python
def validate_table_restriction(query: str, allowed_tables: list) -> None:
    """Ensure query only references allowed tables."""
    # Extract table references from FROM and JOIN clauses
    table_pattern = r'\b(?:FROM|JOIN)\s+([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+){0,2})\b'
    referenced_tables = re.findall(table_pattern, query, re.IGNORECASE)
    
    # Check each referenced table against allowed list
    for table_ref in referenced_tables:
        if table_ref.lower() not in allowed_normalized:
            raise GuardrailViolation(
                f"Query rejected: Table '{table_ref}' is not in the allowed list."
            )
```

**Examples**:
```sql
-- Assume allowed table: catalog.schema.sensor_data

-- ✅ ALLOWED
SELECT * FROM sensor_data;
SELECT * FROM catalog.schema.sensor_data;
SELECT * FROM schema.sensor_data;

-- ❌ REJECTED
SELECT * FROM other_table;
SELECT * FROM catalog.schema.other_table;
SELECT * FROM sensor_data JOIN other_table ON sensor_data.id = other_table.id;
```

### 4. Automatic LIMIT Clause Injection

**Rule**: Queries without explicit LIMIT clauses have a default limit automatically applied.

**Purpose**: Prevents excessive data transfer and resource consumption.

**Default Limits**:
- KPI queries: 1000 rows
- Chat queries: 100 rows
- Explore page preview: 100 rows
- Download: 10,000 rows

**Implementation**:
```python
def inject_limit_clause(query: str, default_limit: int = 1000) -> str:
    """Add LIMIT clause if not present."""
    if not re.search(r'\bLIMIT\s+\d+', query, re.IGNORECASE):
        query = f"{query.strip().rstrip(';')} LIMIT {default_limit}"
    return query
```

**Examples**:
```sql
-- Input query (no LIMIT)
SELECT * FROM sensor_data WHERE status = 'active'

-- Output query (LIMIT added)
SELECT * FROM sensor_data WHERE status = 'active' LIMIT 1000

-- Input query (has LIMIT)
SELECT * FROM sensor_data LIMIT 50

-- Output query (unchanged)
SELECT * FROM sensor_data LIMIT 50
```

### 5. SQL Syntax Validation

**Rule**: Queries must have valid SQL syntax before execution.

**Checks**:
1. Query is not empty
2. Query contains SELECT keyword
3. FROM clause is present when required (with WHERE, GROUP BY, ORDER BY, etc.)
4. Parentheses are balanced
5. Single quotes are balanced

**Implementation**:
```python
def validate_sql_syntax(query: str) -> None:
    """Perform basic SQL syntax validation."""
    if not query or not query.strip():
        raise GuardrailViolation("Query rejected: Query cannot be empty.")
    
    if not re.search(r'\bSELECT\b', query, re.IGNORECASE):
        raise GuardrailViolation("Query rejected: Query must be a SELECT statement.")
    
    # Check balanced parentheses
    if query.count('(') != query.count(')'):
        raise GuardrailViolation("Query rejected: Unbalanced parentheses detected.")
    
    # Check balanced quotes
    if query.count("'") % 2 != 0:
        raise GuardrailViolation("Query rejected: Unbalanced single quotes detected.")
```

**Examples**:
```sql
-- ✅ ALLOWED
SELECT * FROM sensor_data;
SELECT COUNT(*) FROM sensor_data WHERE (status = 'active' OR status = 'pending');

-- ❌ REJECTED (empty query)
""

-- ❌ REJECTED (no SELECT)
FROM sensor_data WHERE id = 1

-- ❌ REJECTED (unbalanced parentheses)
SELECT * FROM sensor_data WHERE (status = 'active'

-- ❌ REJECTED (unbalanced quotes)
SELECT * FROM sensor_data WHERE status = 'active
```

## Validation Pipeline

All queries go through the complete validation pipeline:

```
Query Input
    ↓
1. SQL Syntax Validation
    ↓
2. SELECT-Only Validation
    ↓
3. Single Statement Validation
    ↓
4. Table Restriction Validation
    ↓
5. LIMIT Clause Injection (if needed)
    ↓
Validated Query → Execution
```

If any validation step fails, the query is rejected with a descriptive error message.

## Error Messages

Guardrail violations return user-friendly error messages:

### SELECT-Only Violation
```
Query rejected: DROP statements are not allowed. 
Only SELECT queries are permitted for data safety.
```

### Multi-Statement Violation
```
Query rejected: Multiple statements detected (2 statements). 
Only single statement queries are allowed for security.
```

### Table Restriction Violation
```
Query rejected: Table 'other_table' is not in the allowed list. 
Only the selected dataset can be queried. 
Allowed tables: catalog.schema.sensor_data
```

### Syntax Violation
```
Query rejected: Unbalanced parentheses detected.
```

## Usage in Application

### KPI Page
```python
# KPI queries use aggregate functions with high limits
query = "SELECT COUNT(*) FROM sensor_data"
validated_query, _ = validate_query(query, allowed_tables, default_limit=1000)
```

### Explore Page
```python
# Explore queries use filters with preview limits
query = "SELECT * FROM sensor_data WHERE status = 'active'"
validated_query, _ = validate_query(query, allowed_tables, default_limit=100)
```

### Chat Page
```python
# Chat queries use natural language conversion with guardrails
try:
    sql_query, intent = router.route_query(user_question)
    validated_query, _ = validate_query(sql_query, allowed_tables, default_limit=100)
    df = execute_query(validated_query)
except GuardrailViolation as e:
    st.error(f"Query validation failed: {str(e)}")
```

## Testing Guardrails

The guardrails module includes comprehensive unit tests:

```bash
# Run guardrails tests
pytest components/test_guardrails.py -v

# Test coverage includes:
# - SELECT-only validation (7 tests)
# - Single statement validation (4 tests)
# - Table restriction validation (7 tests)
# - LIMIT clause injection (4 tests)
# - SQL syntax validation (7 tests)
# - Complete validation pipeline (5 tests)
```

## Bypassing Guardrails

**Important**: Guardrails cannot be bypassed through the application UI. They are enforced at the code level before any query execution.

Administrators with direct database access can execute queries outside the application, but:
1. All queries are logged in Unity Catalog audit logs
2. Unity Catalog ACLs still apply
3. Row-level security and column masking still apply

## Best Practices

### For Users
1. Use the chat interface for natural language queries (guardrails applied automatically)
2. Use the explore page for filtered data access (guardrails applied automatically)
3. Do not attempt to bypass guardrails (violations are logged)

### For Developers
1. Always call `validate_query()` before executing user-provided SQL
2. Provide appropriate `allowed_tables` list for context
3. Set appropriate `default_limit` based on use case
4. Handle `GuardrailViolation` exceptions gracefully
5. Display user-friendly error messages

### For Administrators
1. Monitor guardrail violations in application logs
2. Review patterns of rejected queries
3. Update guardrail rules as needed
4. Educate users on proper query patterns

## Summary

The Guardrails Engine provides **defense-in-depth** query security:

- ✅ Prevents destructive operations (DDL/DML)
- ✅ Prevents SQL injection (single statement)
- ✅ Prevents unauthorized access (table restriction)
- ✅ Prevents resource exhaustion (automatic limits)
- ✅ Validates syntax before execution

Combined with Unity Catalog governance, this ensures secure and controlled data access.
