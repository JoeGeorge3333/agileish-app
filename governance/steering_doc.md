# Data Governance Steering Document

## Overview

This document describes the governance policies and controls implemented in the Predictive Maintenance Data App to ensure secure, compliant, and controlled access to data through Unity Catalog.

## Allowed Datasets

### Catalog and Schema Scope

The application is restricted to query data from:

- **Catalog**: `dataknobs_predictive_maintenance_and_asset_management`
- **Schema**: `datasets`

All queries are automatically scoped to this catalog and schema. Users cannot query data from other catalogs or schemas.

### Table Access

Users can access any table within the allowed catalog and schema through the dataset selector dropdown. The application automatically:

1. Lists available tables using `SHOW TABLES IN <catalog>.<schema>`
2. Checks for secure views (tables with `_secure_vw` suffix)
3. Prioritizes secure views when available

## SELECT-Only Policy

### Query Restrictions

The application enforces a **SELECT-only policy** through the Guardrails Engine. All user queries are validated before execution to ensure:

1. **Only SELECT statements are allowed**
   - DDL statements (DROP, CREATE, ALTER, TRUNCATE, RENAME) are rejected
   - DML statements (INSERT, UPDATE, DELETE, MERGE) are rejected
   - DCL statements (GRANT, REVOKE) are rejected
   - Stored procedure calls (EXEC, EXECUTE, CALL) are rejected

2. **Single statement execution**
   - Multi-statement queries (separated by semicolons) are rejected
   - Prevents SQL injection and unauthorized operations

3. **Table restriction validation**
   - Queries can only reference the currently selected table
   - Attempts to query other tables are rejected

4. **Automatic LIMIT clause injection**
   - Queries without explicit LIMIT clauses have a default limit applied
   - Default limit: 1000 rows for KPI queries, 100 rows for chat queries
   - Prevents excessive data transfer and resource consumption

5. **SQL syntax validation**
   - Basic syntax checks before execution
   - Validates balanced parentheses and quotes
   - Ensures required clauses (FROM) are present when needed

### Example Rejected Queries

```sql
-- DDL - REJECTED
DROP TABLE my_table;
CREATE TABLE new_table (id INT);
ALTER TABLE my_table ADD COLUMN new_col STRING;

-- DML - REJECTED
INSERT INTO my_table VALUES (1, 2, 3);
UPDATE my_table SET col1 = 'value';
DELETE FROM my_table WHERE id = 1;

-- Multi-statement - REJECTED
SELECT * FROM table1; SELECT * FROM table2;

-- Unauthorized table access - REJECTED
SELECT * FROM other_catalog.other_schema.other_table;
```

### Example Allowed Queries

```sql
-- Simple SELECT - ALLOWED
SELECT * FROM my_table;

-- Aggregation - ALLOWED
SELECT category, COUNT(*) FROM my_table GROUP BY category;

-- Filtering - ALLOWED
SELECT * FROM my_table WHERE timestamp > '2024-01-01';

-- Joins within allowed table - ALLOWED (if secure view includes joins)
SELECT * FROM my_table WHERE id IN (SELECT id FROM my_table WHERE status = 'active');
```

## Secure Views and Row-Level Security

### Secure View Pattern

The application implements a **secure view pattern** for data governance:

1. **Naming Convention**: Secure views follow the pattern `<table_name>_secure_vw`
   - Example: `sensor_data` → `sensor_data_secure_vw`

2. **Automatic Detection**: The application automatically detects and uses secure views
   - When a secure view exists, it is used instead of the base table
   - Users see a 🔒 indicator when querying secure views

3. **Fallback Behavior**: If no secure view exists, the base table is queried directly

### Unity Catalog Governance Integration

Secure views in Unity Catalog can implement:

1. **Row-Level Security (RLS)**
   - Filter rows based on user identity or group membership
   - Example: `WHERE user_group = current_user()`

2. **Column Masking**
   - Mask sensitive columns based on user permissions
   - Example: `CASE WHEN is_member('sensitive_data_group') THEN ssn ELSE 'XXX-XX-XXXX' END`

3. **Dynamic Data Filtering**
   - Apply time-based or context-based filters
   - Example: `WHERE timestamp >= current_date() - INTERVAL 90 DAYS`

### Example Secure View Definition

```sql
CREATE OR REPLACE VIEW sensor_data_secure_vw AS
SELECT 
    timestamp,
    asset_id,
    sensor_value,
    -- Mask sensitive columns for non-privileged users
    CASE 
        WHEN is_member('data_engineers') THEN location
        ELSE 'REDACTED'
    END AS location,
    -- Apply row-level security
    category,
    status
FROM sensor_data
WHERE 
    -- Only show data for user's region
    region = current_user_region()
    -- Only show recent data for non-admin users
    AND (is_member('admins') OR timestamp >= current_date() - INTERVAL 30 DAYS);
```

## Resource Limits and Performance Controls

### Query Resource Limits

1. **Row Limits**
   - Default LIMIT: 1000 rows (KPI queries), 100 rows (chat queries)
   - Maximum download limit: 10,000 rows
   - Prevents excessive data transfer and memory usage

2. **Aggregate Queries**
   - KPI computations use aggregate queries (COUNT, AVG, MIN, MAX)
   - Minimizes data transfer by computing on the server side

3. **Data Point Limits for Visualizations**
   - Time series: Maximum 1000 data points
   - Category breakdowns: Top 20 categories only
   - Histogram bins: Maximum 50 bins

### Performance Optimization

1. **Schema Caching**
   - Schema introspection results are cached in session state
   - Reduces repeated DESCRIBE queries

2. **Lazy Loading**
   - Data is loaded on-demand, not preloaded
   - Filters are applied before data retrieval

3. **Efficient Aggregations**
   - Use SQL aggregations instead of fetching raw data
   - Example: `COUNT(*)` instead of fetching all rows and counting in Python

## Authentication and User Identity

### Databricks Apps Authentication

The application relies on **Databricks Apps platform authentication**:

1. **No Custom Login**: The app does not implement custom authentication
2. **SSO Integration**: Users authenticate through Databricks SSO
3. **Session Management**: Databricks Apps manages user sessions
4. **Identity Display**: The app displays "Authenticated via Databricks Apps"

### User Context

When available, the application can access:
- Current user identity
- User group memberships
- Workspace context

This information is used by Unity Catalog to enforce:
- Row-level security policies
- Column masking rules
- Access control lists (ACLs)

## Audit and Compliance

### Query Logging

All queries executed through the application are logged by:

1. **Databricks SQL Warehouse**: Query history and execution logs
2. **Unity Catalog**: Access audit logs
3. **Application Logs**: Query validation and guardrail violations

### Compliance Features

1. **Data Lineage**: Unity Catalog tracks data lineage for all queries
2. **Access Auditing**: All data access is logged with user identity
3. **Policy Enforcement**: Governance policies are enforced at the Unity Catalog level
4. **Immutable Logs**: Audit logs cannot be modified or deleted

## Governance Workflow

### Data Access Flow

```
User Request
    ↓
Dataset Selection (Catalog.Schema.Table)
    ↓
Secure View Detection (Check for _secure_vw)
    ↓
Query Generation (Natural Language → SQL or Manual)
    ↓
Guardrails Validation (SELECT-only, Single statement, Table restriction)
    ↓
LIMIT Clause Injection (If not present)
    ↓
Unity Catalog Authorization (RLS, Column Masking, ACLs)
    ↓
Query Execution (Databricks SQL Warehouse)
    ↓
Result Display (Dataframe, Chart, Narrative)
```

### Governance Layers

1. **Application Layer** (This App)
   - SELECT-only enforcement
   - Table restriction
   - Resource limits

2. **Unity Catalog Layer** (Databricks)
   - Row-level security
   - Column masking
   - Access control lists
   - Audit logging

3. **SQL Warehouse Layer** (Databricks)
   - Query execution
   - Resource management
   - Query history

## Best Practices

### For Data Stewards

1. **Create Secure Views**: Define secure views with appropriate RLS and masking
2. **Use Naming Convention**: Follow `<table>_secure_vw` pattern
3. **Test Policies**: Verify RLS and masking work as expected
4. **Document Policies**: Maintain documentation of governance rules

### For Users

1. **Use Dataset Selector**: Always select datasets through the UI
2. **Respect Limits**: Be mindful of row limits and resource usage
3. **Report Issues**: Report any unexpected data access or errors
4. **Follow Guidelines**: Adhere to data usage policies

### For Administrators

1. **Monitor Usage**: Review query logs and access patterns
2. **Update Policies**: Keep governance policies current
3. **Manage Permissions**: Use Unity Catalog groups for access control
4. **Audit Regularly**: Conduct periodic access audits

## Summary

The Predictive Maintenance Data App implements a **defense-in-depth** governance strategy:

- **Application-level controls**: SELECT-only, table restrictions, resource limits
- **Unity Catalog controls**: RLS, column masking, ACLs
- **Secure view pattern**: Automatic detection and usage of governed views
- **Audit and compliance**: Comprehensive logging and lineage tracking

This multi-layered approach ensures secure, compliant, and controlled data access while maintaining usability and performance.
