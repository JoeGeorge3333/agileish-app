# Predictive Maintenance Data App

A governed, self-service data application for exploring predictive maintenance datasets on Databricks using Streamlit.

## Features

### 📊 KPI Overview
- Compute 5+ key performance indicators automatically
- Adaptive metrics based on dataset schema
- Interactive visualizations (time trends, category breakdowns, distributions)
- Fallback logic for missing columns

### 🔍 Data Exploration
- Dynamic filters based on column types (date range, categorical, numeric)
- Real-time data preview with pagination
- Download filtered results (up to 10,000 rows)
- Secure view support with governance indicators

### 💬 Chat Interface
- Natural language to SQL conversion
- Template-based query routing (5 intent types)
- Automatic query validation via guardrails
- Interactive results with charts and narratives
- Example questions to guide users

## Architecture

### Application Stack
- **Frontend**: Streamlit (Python web framework)
- **Backend**: Databricks SQL Warehouse
- **Governance**: Unity Catalog
- **Authentication**: Databricks Apps SSO

### Key Components

```
app.py                    # Main entry point with sidebar navigation
├── components/
│   ├── db.py            # Database connection (lazy imports)
│   ├── schema_introspector.py  # Column type detection
│   ├── guardrails.py    # Query validation (SELECT-only)
│   ├── kpi_engine.py    # KPI computation
│   ├── kpi_page.py      # KPI Overview page
│   ├── chart_generator.py  # Visualization generation
│   ├── explore_page.py  # Data Exploration page
│   ├── query_router.py  # Natural language to SQL
│   └── chat_page.py     # Chat Interface page
```

## Quick Start

### Local Development (Without Databricks)

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 2. Install dev dependencies (no Databricks packages)
pip install -r requirements-dev.txt

# 3. Run tests
pytest components/ -q
# Expected: 156 passed
```

### Full Installation (With Databricks)

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate

# 2. Install all dependencies
pip install -r requirements.txt

# 3. Run tests
pytest components/ -q
# Expected: 156 passed

# 4. Run app locally (requires Databricks credentials)
streamlit run app.py
```

## Governance and Security

### Query Guardrails

All queries are validated before execution:

- ✅ **SELECT-only**: DDL/DML statements rejected
- ✅ **Single statement**: Multi-statement queries rejected
- ✅ **Table restriction**: Only selected table accessible
- ✅ **Automatic LIMIT**: Default limits applied (100-1000 rows)
- ✅ **Syntax validation**: Basic SQL syntax checks

### Unity Catalog Integration

- **Secure Views**: Automatic detection of `_secure_vw` suffix
- **Row-Level Security**: Applied via secure views
- **Column Masking**: Sensitive data masked based on user role
- **Audit Logging**: All queries logged in Unity Catalog

### User Roles

| Role | Access | Data Scope | Permissions |
|------|--------|------------|-------------|
| **Viewer** | Secure views only | Last 30 days | Read-only, masked columns |
| **Analyst** | Secure views + logs | Last 12 months | Read-only, partial masking |
| **Admin** | All tables | All history | Read-only, no masking |

See `governance/roles.md` for details.

## Testing

### Run All Tests

```bash
pytest components/ -v
```

### Test Coverage

- **156 tests** across 8 modules
- **100% pass rate**
- Coverage includes:
  - Database connection (11 tests)
  - Schema introspection (22 tests)
  - Query guardrails (34 tests)
  - KPI engine (21 tests)
  - Chart generation (16 tests)
  - Data exploration (18 tests)
  - Query routing (29 tests)
  - Integration tests (5 tests)

### Test Modules

```bash
# Test specific module
pytest components/test_guardrails.py -v
pytest components/test_query_router.py -v
pytest components/test_kpi_engine.py -v
```

## Configuration

### Default Catalog and Schema

Edit `components/kpi_page.py`:

```python
DEFAULT_CATALOG = "dataknobs_predictive_maintenance_and_asset_management"
DEFAULT_SCHEMA = "datasets"
```

### Resource Limits

Edit respective module constants:

- **Query limits**: `components/guardrails.py` → `DEFAULT_LIMIT`
- **Visualization limits**: `components/chart_generator.py` → `MAX_TIME_SERIES_POINTS`
- **Download limits**: `components/explore_page.py` → `MAX_DOWNLOAD_LIMIT`

## Dependencies

### Core Dependencies

- `pandas>=2.0.0,<3.0.0` - Data manipulation
- `streamlit>=1.28.0,<2.0.0` - Web framework
- `protobuf>=5.27.0,<6.0.0` - Protocol buffers (pinned for Streamlit compatibility)
- `pytest>=7.4.0,<8.0.0` - Testing framework

### Databricks Dependencies (Optional for Local Testing)

- `databricks-sql-connector>=3.0.0,<4.0.0` - SQL connection
- `databricks-sdk>=0.18.0,<1.0.0` - Runtime context

**Note**: Databricks packages use lazy imports and are only required when running in Databricks Apps environment.

## Documentation

- **Setup Guide**: `SETUP.md` - Development environment setup
- **Deployment Guide**: `DEPLOYMENT.md` - Production deployment
- **Changes Log**: `CHANGES.md` - Recent improvements
- **Governance**: `governance/` - Policies and roles
  - `steering_doc.md` - Governance overview
  - `guardrails.md` - Query validation rules
  - `roles.md` - User roles and permissions

## Project Structure

```
.
├── app.py                      # Main Streamlit app
├── components/                 # Application modules
│   ├── __init__.py
│   ├── db.py                  # Database connection
│   ├── schema_introspector.py # Schema analysis
│   ├── guardrails.py          # Query validation
│   ├── kpi_engine.py          # KPI computation
│   ├── kpi_page.py            # KPI Overview page
│   ├── chart_generator.py     # Visualizations
│   ├── explore_page.py        # Data Exploration page
│   ├── query_router.py        # NL to SQL
│   ├── chat_page.py           # Chat Interface page
│   └── test_*.py              # Unit tests
├── governance/                 # Governance docs
│   ├── steering_doc.md        # Policies
│   ├── guardrails.md          # Query rules
│   └── roles.md               # User roles
├── requirements.txt            # Production dependencies
├── requirements-dev.txt        # Dev dependencies
├── SETUP.md                    # Setup guide
├── DEPLOYMENT.md               # Deployment guide
├── CHANGES.md                  # Change log
└── README.md                   # This file
```

## Key Features

### Schema Introspection

Automatically detects column types:
- **Time columns**: Based on data types (timestamp, date)
- **ID columns**: Based on naming patterns (asset_id, machine_id, unit)
- **Label columns**: Based on naming patterns (failure, fault, target)
- **Categorical columns**: String types
- **Numeric columns**: Numeric types

### Adaptive KPIs

Computes 5+ KPIs with fallback logic:
1. **Row count** (always available)
2. **Date range** (when time column exists)
3. **Data missingness** (always available)
4. **Failure rate** (when label column exists)
5. **Unique asset count** (when ID column exists)

### Natural Language Queries

Supports 5 query intents:
1. **Count queries**: "How many records?"
2. **Summary statistics**: "What is the average?"
3. **Trend analysis**: "Show trends over time"
4. **Top categories**: "What are the top categories?"
5. **Failure rate**: "What is the failure rate?"

## Performance

### Optimization Strategies

- **Aggregate queries**: Compute on server side (COUNT, AVG, MIN, MAX)
- **Query limits**: Automatic LIMIT clause injection
- **Schema caching**: Cache introspection results in session state
- **Lazy imports**: Databricks packages loaded only when needed
- **Data point limits**: Restrict visualization data points (1000 max)

### Resource Usage

- **Memory**: Minimal (aggregate queries, limited result sets)
- **Network**: Optimized (server-side computation, limited transfers)
- **Compute**: Efficient (SQL Warehouse auto-scaling)

## Troubleshooting

### Common Issues

**Issue**: Tests fail with import errors

**Solution**:
```bash
pip install -r requirements-dev.txt --force-reinstall
```

**Issue**: Protobuf version conflict

**Solution**:
```bash
pip install "protobuf>=5.27.0,<6.0.0" --force-reinstall
```

**Issue**: "No tables found" error

**Solution**:
- Verify catalog and schema names
- Check Unity Catalog permissions
- Ensure SQL Warehouse is running

See `DEPLOYMENT.md` for more troubleshooting tips.

## Contributing

### Development Workflow

1. Create feature branch
2. Make changes
3. Run tests: `pytest components/ -v`
4. Update documentation
5. Submit pull request

### Code Style

- Follow PEP 8 style guide
- Use type hints where appropriate
- Add docstrings to all functions
- Write unit tests for new features

### Testing Requirements

- All tests must pass before merge
- Maintain 100% test pass rate
- Add tests for new features
- Update tests for bug fixes

## License

[Your License Here]

## Support

For issues or questions:
1. Check documentation in `governance/` and `DEPLOYMENT.md`
2. Review application logs
3. Consult Unity Catalog audit logs
4. Contact Databricks support

## Acknowledgments

Built with:
- [Streamlit](https://streamlit.io/) - Web framework
- [Databricks](https://databricks.com/) - Data platform
- [Unity Catalog](https://www.databricks.com/product/unity-catalog) - Data governance
- [pandas](https://pandas.pydata.org/) - Data manipulation

---

**Status**: Production Ready ✅

**Tests**: 156 passed ✅

**Documentation**: Complete ✅

**Governance**: Implemented ✅
