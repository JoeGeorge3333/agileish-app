# Dependency and Testing Improvements

## Summary

Fixed dependency conflicts and refactored database module to make Databricks packages optional for local testing.

## Changes Made

### 1. Fixed Protobuf Version Conflict

**Problem**: Streamlit requires `protobuf < 6`, but `protobuf 6.x` was installed, causing dependency conflicts.

**Solution**: Updated `requirements.txt` to explicitly pin protobuf version:
```
protobuf>=5.27.0,<6.0.0
```

### 2. Made Databricks Dependencies Optional

**Problem**: `databricks-sdk` was being imported at module load time, requiring Databricks credentials even for unit tests.

**Solution**: Refactored `components/db.py` to use lazy imports:

- Created `_get_databricks_sql()` function for lazy import of `databricks.sql`
- Created `_get_dbutils()` function for lazy import of `databricks.sdk.runtime.dbutils`
- These functions are only called when actually needed (at runtime in Databricks environment)
- Unit tests can now run without any Databricks packages installed

**Before**:
```python
from databricks import sql
from databricks.sdk.runtime import dbutils  # Fails immediately if not in Databricks
```

**After**:
```python
def _get_databricks_sql():
    """Lazy import of databricks.sql module."""
    global _sql
    if _sql is None:
        from databricks import sql
        _sql = sql
    return _sql
```

### 3. Updated Test Mocking Strategy

**Problem**: Tests were trying to mock `components.db.dbutils` which no longer exists as a module-level variable.

**Solution**: Updated `components/test_db.py` to mock the lazy import functions:
- Changed from `@patch('components.db.dbutils')` to `@patch('components.db._get_dbutils')`
- Changed from `@patch('components.db.sql.connect')` to `@patch('components.db._get_databricks_sql')`

### 4. Created Two Requirements Files

**requirements.txt** (Full installation for deployment):
```
pandas>=2.0.0,<3.0.0
streamlit>=1.28.0,<2.0.0
protobuf>=5.27.0,<6.0.0
pytest>=7.4.0,<8.0.0
databricks-sql-connector>=3.0.0,<4.0.0
databricks-sdk>=0.18.0,<1.0.0
```

**requirements-dev.txt** (Local development without Databricks):
```
pandas>=2.0.0,<3.0.0
streamlit>=1.28.0,<2.0.0
protobuf>=5.27.0,<6.0.0
pytest>=7.4.0,<8.0.0
# Databricks packages commented out - not needed for local testing
```

### 5. Created Setup Documentation

Created `SETUP.md` with:
- Instructions for creating clean virtual environment
- Two setup options (with/without Databricks dependencies)
- Troubleshooting guide for common issues
- Commands for running tests

## Test Results

All 156 tests pass successfully:

```bash
$ pytest components/ -q
....................................................... [ 35%]
....................................................... [ 70%]
..............................................          [100%]
156 passed in 1.03s
```

## Benefits

1. **No Databricks credentials needed for testing**: Developers can run all unit tests locally without Databricks access
2. **Faster test execution**: No need to load heavy Databricks SDK packages during testing
3. **Cleaner dependencies**: Clear separation between core dependencies and deployment-specific dependencies
4. **No version conflicts**: Protobuf version is properly pinned to avoid conflicts with Streamlit
5. **Better developer experience**: Clear setup instructions and troubleshooting guide

## Commands for Clean Setup

```bash
# Create clean virtual environment
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows

# Upgrade pip
pip install --upgrade pip

# Install dependencies (choose one):
pip install -r requirements-dev.txt  # For local development
pip install -r requirements.txt      # For full installation

# Run tests
pytest components/ -q
```

## Backward Compatibility

- All existing functionality remains unchanged
- Application still works in Databricks Apps environment
- No changes to public API or function signatures
- All 156 tests continue to pass
