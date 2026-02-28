# Deployment Guide

## Application Overview

The Predictive Maintenance Data App is a Databricks Streamlit application that provides:

- **KPI Overview**: Key performance indicators and visualizations
- **Data Exploration**: Interactive filtering and data preview
- **Chat Interface**: Natural language queries with automatic SQL generation

## Application Structure

```
.
├── app.py                          # Main Streamlit entry point
├── components/
│   ├── __init__.py
│   ├── db.py                       # Database connection and queries
│   ├── schema_introspector.py     # Schema analysis and column detection
│   ├── guardrails.py               # Query validation and safety
│   ├── kpi_engine.py               # KPI computation
│   ├── kpi_page.py                 # KPI Overview page
│   ├── chart_generator.py          # Visualization generation
│   ├── explore_page.py             # Data Exploration page
│   ├── query_router.py             # Natural language to SQL
│   ├── chat_page.py                # Chat Interface page
│   └── test_*.py                   # Unit tests (156 tests)
├── governance/
│   ├── steering_doc.md             # Governance policies
│   ├── guardrails.md               # Query guardrails documentation
│   └── roles.md                    # User roles and permissions
├── requirements.txt                # Python dependencies
├── requirements-dev.txt            # Dev dependencies (no Databricks)
└── README.md                       # Project documentation
```

## Prerequisites

### Databricks Environment

- Databricks workspace with Apps enabled
- Unity Catalog configured
- SQL Warehouse available
- Catalog: `dataknobs_predictive_maintenance_and_asset_management`
- Schema: `datasets`

### Python Environment

- Python 3.9 or higher
- pip package manager

## Deployment Steps

### 1. Prepare Application Files

```bash
# Clone or copy application files to deployment directory
cd /path/to/deployment

# Verify all files are present
ls -la app.py components/ governance/ requirements.txt
```

### 2. Install Dependencies

```bash
# Create virtual environment (optional for local testing)
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Run Tests (Optional)

```bash
# Verify all tests pass before deployment
pytest components/ -q

# Expected output:
# 156 passed in ~1.5s
```

### 4. Deploy to Databricks Apps

#### Option A: Using Databricks CLI

```bash
# Install Databricks CLI
pip install databricks-cli

# Configure authentication
databricks configure --token

# Deploy app
databricks apps create \
  --name "predictive-maintenance-app" \
  --source-path . \
  --entry-point app.py
```

#### Option B: Using Databricks UI

1. Navigate to Databricks workspace
2. Go to **Apps** section
3. Click **Create App**
4. Upload application files:
   - `app.py`
   - `components/` directory
   - `requirements.txt`
5. Set entry point: `app.py`
6. Configure compute: Select SQL Warehouse
7. Click **Deploy**

### 5. Configure Unity Catalog Access

```sql
-- Grant SELECT permissions on catalog and schema
GRANT USAGE ON CATALOG dataknobs_predictive_maintenance_and_asset_management TO `app_users`;
GRANT USAGE ON SCHEMA dataknobs_predictive_maintenance_and_asset_management.datasets TO `app_users`;
GRANT SELECT ON SCHEMA dataknobs_predictive_maintenance_and_asset_management.datasets TO `app_users`;

-- Create secure views (optional but recommended)
CREATE OR REPLACE VIEW sensor_data_secure_vw AS
SELECT 
    timestamp,
    asset_id,
    sensor_value,
    category,
    status
FROM sensor_data
WHERE timestamp >= current_date() - INTERVAL 30 DAYS;

-- Grant access to secure views
GRANT SELECT ON VIEW sensor_data_secure_vw TO `app_users`;
```

### 6. Verify Deployment

1. Access the deployed app URL
2. Verify sidebar navigation works
3. Test each page:
   - KPI Overview: Check KPIs and charts load
   - Explore Data: Test filters and data preview
   - Chat Interface: Try example questions
4. Verify guardrails work (try invalid queries)
5. Check secure view detection (🔒 indicator)

## Configuration

### Environment Variables

The application uses Databricks session context for authentication. No additional environment variables are required.

### Catalog and Schema

To change the default catalog and schema, update `components/kpi_page.py`:

```python
# Default catalog and schema for predictive maintenance datasets
DEFAULT_CATALOG = "your_catalog_name"
DEFAULT_SCHEMA = "your_schema_name"
```

### Resource Limits

To adjust resource limits, update constants in respective modules:

**Query Limits** (`components/guardrails.py`):
```python
DEFAULT_LIMIT = 1000  # Default row limit for queries
```

**Visualization Limits** (`components/chart_generator.py`):
```python
MAX_TIME_SERIES_POINTS = 1000  # Max data points for time series
MAX_CATEGORY_VALUES = 20       # Max categories to show
```

**Download Limits** (`components/explore_page.py`):
```python
MAX_DOWNLOAD_LIMIT = 10000  # Maximum rows for download
```

## Monitoring and Maintenance

### Application Logs

View application logs in Databricks Apps console:

1. Navigate to **Apps** section
2. Select your app
3. Click **Logs** tab
4. Filter by log level (INFO, WARNING, ERROR)

### Query Audit Logs

Monitor query execution in Unity Catalog:

```sql
SELECT 
    user_identity,
    action_name,
    request_params,
    response_status,
    event_time
FROM system.access.audit
WHERE 
    service_name = 'unityCatalog'
    AND event_time >= current_date() - INTERVAL 7 DAYS
ORDER BY event_time DESC;
```

### Performance Monitoring

Monitor SQL Warehouse query performance:

1. Navigate to **SQL Warehouses**
2. Select your warehouse
3. Click **Query History**
4. Review execution times and resource usage

## Troubleshooting

### Issue: "No tables found in catalog.schema"

**Cause**: Application cannot access Unity Catalog tables.

**Solution**:
1. Verify catalog and schema names are correct
2. Check Unity Catalog permissions
3. Ensure SQL Warehouse is running
4. Verify network connectivity

### Issue: "Failed to establish database connection"

**Cause**: Cannot connect to Databricks SQL Warehouse.

**Solution**:
1. Verify SQL Warehouse is running
2. Check warehouse permissions
3. Verify Databricks Apps authentication
4. Review application logs for details

### Issue: "Query validation failed"

**Cause**: Query violates guardrails.

**Solution**:
1. Review error message for specific violation
2. Ensure query is SELECT-only
3. Verify table name is correct
4. Check for syntax errors

### Issue: "Module not found" errors

**Cause**: Missing dependencies.

**Solution**:
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Verify installation
pip list | grep -E "streamlit|pandas|databricks"
```

## Security Considerations

### Authentication

- Application uses Databricks Apps SSO
- No custom authentication required
- User identity passed to Unity Catalog

### Authorization

- Unity Catalog enforces access control
- Row-level security via secure views
- Column masking for sensitive data

### Query Safety

- SELECT-only enforcement via guardrails
- Single statement validation
- Table restriction validation
- Automatic LIMIT clause injection

### Audit Trail

- All queries logged in Unity Catalog
- Access patterns tracked
- Guardrail violations logged

## Scaling Considerations

### Concurrent Users

- Databricks Apps handles concurrent sessions
- Each user gets isolated session state
- SQL Warehouse auto-scales for query load

### Data Volume

- Query limits prevent excessive data transfer
- Aggregate queries minimize data movement
- Caching reduces repeated queries

### Performance Optimization

1. **Use Secure Views**: Pre-filter data at source
2. **Enable Caching**: Cache schema introspection results
3. **Optimize Queries**: Use aggregate functions
4. **Scale Warehouse**: Increase warehouse size for heavy load

## Backup and Recovery

### Application Code

- Store code in version control (Git)
- Tag releases for rollback capability
- Document configuration changes

### Unity Catalog Metadata

- Unity Catalog metadata is automatically backed up
- Secure view definitions stored in metastore
- Permissions tracked in audit logs

## Support and Documentation

### User Documentation

- **Governance**: See `governance/` directory
- **Guardrails**: See `governance/guardrails.md`
- **Roles**: See `governance/roles.md`

### Developer Documentation

- **Setup**: See `SETUP.md`
- **Changes**: See `CHANGES.md`
- **Tests**: Run `pytest components/ -v`

### Getting Help

1. Review application logs
2. Check Unity Catalog audit logs
3. Consult governance documentation
4. Contact Databricks support

## Summary

The Predictive Maintenance Data App is production-ready with:

- ✅ 156 passing unit tests
- ✅ Comprehensive governance documentation
- ✅ Query guardrails for safety
- ✅ Unity Catalog integration
- ✅ Secure view support
- ✅ Role-based access control
- ✅ Audit logging
- ✅ Performance optimization

Deploy with confidence!
