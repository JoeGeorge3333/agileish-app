# User Roles and Permissions

## Overview

This document describes the conceptual user roles for the Predictive Maintenance Data App and their associated permissions. Role-based access control is implemented through Unity Catalog groups and policies.

## Role Definitions

### 1. Viewer Role

**Purpose**: Read-only access to view KPIs and explore data through the application interface.

**Permissions**:
- ✅ Access the application through Databricks Apps
- ✅ View KPI Overview page
- ✅ View data on Explore page with filters
- ✅ Use Chat Interface for natural language queries
- ✅ Download filtered data (up to 10,000 rows)
- ❌ Cannot execute custom SQL queries
- ❌ Cannot access base tables (only secure views)
- ❌ Cannot modify data or schema

**Unity Catalog Permissions**:
```sql
-- Grant SELECT on secure views only
GRANT SELECT ON VIEW catalog.schema.sensor_data_secure_vw TO `viewers_group`;

-- Deny access to base tables
DENY SELECT ON TABLE catalog.schema.sensor_data TO `viewers_group`;
```

**Use Cases**:
- Business analysts reviewing KPIs
- Stakeholders monitoring data quality
- Report consumers viewing dashboards

**Data Access**:
- Secure views with row-level security applied
- Column masking for sensitive fields
- Time-based filtering (e.g., last 30 days only)

---

### 2. Analyst Role

**Purpose**: Advanced data exploration and analysis with broader data access.

**Permissions**:
- ✅ All Viewer permissions
- ✅ Access to more columns (less masking)
- ✅ Access to historical data (longer time windows)
- ✅ Download larger datasets (up to 10,000 rows)
- ✅ View detailed failure analysis
- ❌ Cannot modify data or schema
- ❌ Cannot access PII or highly sensitive data

**Unity Catalog Permissions**:
```sql
-- Grant SELECT on secure views with analyst-level access
GRANT SELECT ON VIEW catalog.schema.sensor_data_analyst_vw TO `analysts_group`;

-- Grant SELECT on additional tables
GRANT SELECT ON TABLE catalog.schema.failure_logs TO `analysts_group`;
```

**Use Cases**:
- Data analysts performing root cause analysis
- Data scientists exploring patterns
- Operations teams investigating failures

**Data Access**:
- Secure views with relaxed row-level security
- Reduced column masking
- Access to historical data (e.g., last 12 months)
- Access to detailed failure logs

---

### 3. Admin Role

**Purpose**: Full administrative access for data stewardship and governance.

**Permissions**:
- ✅ All Analyst permissions
- ✅ Access to base tables (not just secure views)
- ✅ View all columns without masking
- ✅ Access to all historical data
- ✅ Manage Unity Catalog permissions
- ✅ Create and modify secure views
- ✅ View audit logs
- ❌ Cannot modify data through the application (SELECT-only still enforced)

**Unity Catalog Permissions**:
```sql
-- Grant SELECT on all tables
GRANT SELECT ON SCHEMA catalog.schema TO `admins_group`;

-- Grant ability to manage views
GRANT CREATE VIEW ON SCHEMA catalog.schema TO `admins_group`;
GRANT ALTER VIEW ON SCHEMA catalog.schema TO `admins_group`;

-- Grant ability to manage permissions
GRANT MANAGE GRANTS ON SCHEMA catalog.schema TO `admins_group`;
```

**Use Cases**:
- Data stewards managing governance policies
- Database administrators maintaining tables
- Security officers auditing access

**Data Access**:
- Full access to base tables
- No column masking
- No row-level filtering
- Access to audit logs

---

## Permission Matrix

| Feature | Viewer | Analyst | Admin |
|---------|--------|---------|-------|
| **Application Access** |
| KPI Overview Page | ✅ | ✅ | ✅ |
| Explore Page | ✅ | ✅ | ✅ |
| Chat Interface | ✅ | ✅ | ✅ |
| Download Data | ✅ (10K rows) | ✅ (10K rows) | ✅ (10K rows) |
| **Data Access** |
| Secure Views | ✅ | ✅ | ✅ |
| Base Tables | ❌ | ❌ | ✅ |
| Historical Data | 30 days | 12 months | All |
| Sensitive Columns | Masked | Partially Masked | Unmasked |
| **Row-Level Security** |
| Own Region Only | ✅ | ❌ | ❌ |
| All Regions | ❌ | ✅ | ✅ |
| **Administrative** |
| View Audit Logs | ❌ | ❌ | ✅ |
| Manage Permissions | ❌ | ❌ | ✅ |
| Create Views | ❌ | ❌ | ✅ |
| Modify Schema | ❌ | ❌ | ❌* |

*Note: Even admins cannot modify data through the application due to SELECT-only guardrails.

---

## Role Assignment

### Unity Catalog Groups

Roles are implemented using Unity Catalog groups:

```sql
-- Create groups
CREATE GROUP IF NOT EXISTS viewers_group;
CREATE GROUP IF NOT EXISTS analysts_group;
CREATE GROUP IF NOT EXISTS admins_group;

-- Add users to groups
ALTER GROUP viewers_group ADD USER 'user1@company.com';
ALTER GROUP analysts_group ADD USER 'user2@company.com';
ALTER GROUP admins_group ADD USER 'admin@company.com';
```

### Secure View Implementation

Secure views implement role-based access:

```sql
-- Viewer secure view (restricted access)
CREATE OR REPLACE VIEW sensor_data_secure_vw AS
SELECT 
    timestamp,
    asset_id,
    sensor_value,
    'REDACTED' AS location,  -- Masked for viewers
    category,
    status
FROM sensor_data
WHERE 
    -- Row-level security: own region only
    region = current_user_region()
    -- Time-based filtering: last 30 days only
    AND timestamp >= current_date() - INTERVAL 30 DAYS;

-- Analyst secure view (broader access)
CREATE OR REPLACE VIEW sensor_data_analyst_vw AS
SELECT 
    timestamp,
    asset_id,
    sensor_value,
    location,  -- Unmasked for analysts
    category,
    status,
    failure_code  -- Additional column for analysts
FROM sensor_data
WHERE 
    -- No region restriction for analysts
    -- Time-based filtering: last 12 months
    timestamp >= current_date() - INTERVAL 12 MONTHS;
```

---

## Access Control Examples

### Example 1: Viewer Access

**User**: `viewer@company.com` (member of `viewers_group`)

**Query**:
```sql
SELECT * FROM sensor_data_secure_vw WHERE status = 'active';
```

**Result**:
- ✅ Query succeeds
- Returns data from last 30 days only
- Location column shows 'REDACTED'
- Only shows data for user's region

---

### Example 2: Analyst Access

**User**: `analyst@company.com` (member of `analysts_group`)

**Query**:
```sql
SELECT * FROM sensor_data_analyst_vw WHERE failure_code IS NOT NULL;
```

**Result**:
- ✅ Query succeeds
- Returns data from last 12 months
- Location column shows actual values
- Shows data from all regions
- Includes failure_code column

---

### Example 3: Admin Access

**User**: `admin@company.com` (member of `admins_group`)

**Query**:
```sql
SELECT * FROM sensor_data WHERE timestamp < '2020-01-01';
```

**Result**:
- ✅ Query succeeds (if executed outside the app)
- ❌ Query rejected by app guardrails (base table not in allowed list)
- Admin must use secure views through the app
- Can access base tables through SQL editor or notebooks

---

## Role Transition

### Promoting Users

To promote a user from Viewer to Analyst:

```sql
-- Remove from viewers group
ALTER GROUP viewers_group DROP USER 'user@company.com';

-- Add to analysts group
ALTER GROUP analysts_group ADD USER 'user@company.com';
```

### Demoting Users

To demote a user from Analyst to Viewer:

```sql
-- Remove from analysts group
ALTER GROUP analysts_group DROP USER 'user@company.com';

-- Add to viewers group
ALTER GROUP viewers_group ADD USER 'user@company.com';
```

---

## Audit and Compliance

### Access Logging

All data access is logged in Unity Catalog audit logs:

```sql
-- View access logs
SELECT 
    user_identity,
    action_name,
    request_params,
    response_status,
    event_time
FROM system.access.audit
WHERE 
    service_name = 'unityCatalog'
    AND action_name = 'getTable'
    AND event_time >= current_date() - INTERVAL 7 DAYS
ORDER BY event_time DESC;
```

### Permission Reviews

Regular permission reviews should be conducted:

1. **Monthly**: Review group memberships
2. **Quarterly**: Review secure view definitions
3. **Annually**: Review role definitions and permissions

---

## Best Practices

### For Administrators

1. **Principle of Least Privilege**: Grant minimum necessary permissions
2. **Regular Reviews**: Conduct periodic access reviews
3. **Group-Based Access**: Use groups, not individual user grants
4. **Document Changes**: Maintain change log for permission updates
5. **Test Policies**: Verify RLS and masking work as expected

### For Users

1. **Request Appropriate Role**: Request the role that matches your job function
2. **Report Issues**: Report any unexpected data access
3. **Follow Policies**: Adhere to data usage policies
4. **Protect Credentials**: Do not share login credentials

### For Data Stewards

1. **Define Clear Roles**: Ensure role definitions match business needs
2. **Implement RLS**: Use row-level security in secure views
3. **Mask Sensitive Data**: Apply column masking for PII
4. **Monitor Usage**: Review access patterns and audit logs

---

## Summary

The Predictive Maintenance Data App implements **role-based access control** through:

- **Three conceptual roles**: Viewer, Analyst, Admin
- **Unity Catalog groups**: Map roles to groups
- **Secure views**: Implement RLS and column masking
- **Application guardrails**: Enforce SELECT-only policy
- **Audit logging**: Track all data access

This approach ensures:
- ✅ Appropriate access based on job function
- ✅ Protection of sensitive data
- ✅ Compliance with data governance policies
- ✅ Auditability of all data access
