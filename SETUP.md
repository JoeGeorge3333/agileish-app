# Development Setup Guide

This guide explains how to set up a clean development environment for the Databricks Data App.

## Prerequisites

- Python 3.9 or higher
- pip (Python package installer)

## Setup Instructions

### Option 1: Local Development (Without Databricks Dependencies)

For local testing and development without Databricks packages:

```bash
# 1. Create a clean virtual environment
python -m venv venv

# 2. Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# 3. Upgrade pip
pip install --upgrade pip

# 4. Install development dependencies (without Databricks packages)
pip install -r requirements-dev.txt

# 5. Run tests to verify setup
pytest components/ -q
```

### Option 2: Full Installation (With Databricks Dependencies)

For deployment or testing with Databricks integration:

```bash
# 1. Create a clean virtual environment
python -m venv venv

# 2. Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# 3. Upgrade pip
pip install --upgrade pip

# 4. Install all dependencies including Databricks packages
pip install -r requirements.txt

# 5. Run tests to verify setup
pytest components/ -q
```

## Dependency Management

### Core Dependencies

- **pandas** (>=2.0.0, <3.0.0): Data manipulation and analysis
- **streamlit** (>=1.28.0, <2.0.0): Web application framework
- **protobuf** (>=5.27.0, <6.0.0): Protocol buffers (pinned to avoid conflicts with streamlit)
- **pytest** (>=7.4.0, <8.0.0): Testing framework

### Databricks Dependencies (Optional for Local Testing)

- **databricks-sql-connector** (>=3.0.0, <4.0.0): SQL connection to Databricks
- **databricks-sdk** (>=0.18.0, <1.0.0): Databricks SDK for runtime context

**Note**: The application uses lazy imports for Databricks packages, so they are only required when running in the Databricks Apps environment. All unit tests can run without these dependencies.

## Protobuf Version Conflict Resolution

Streamlit requires `protobuf < 6`, but some packages may install `protobuf >= 6`. The requirements files explicitly pin protobuf to version 5.x to avoid this conflict.

If you encounter protobuf version conflicts:

```bash
# Uninstall conflicting protobuf version
pip uninstall protobuf -y

# Reinstall with correct version
pip install "protobuf>=5.27.0,<6.0.0"
```

## Running Tests

```bash
# Run all tests
pytest components/ -v

# Run tests quietly (summary only)
pytest components/ -q

# Run specific test file
pytest components/test_db.py -v

# Run with coverage
pytest components/ --cov=components --cov-report=html
```

## Troubleshooting

### Import Errors for Databricks Packages

If you see import errors related to `databricks.sql` or `databricks.sdk.runtime`:

1. These are expected in local development environments
2. The application uses lazy imports and will only fail at runtime if you try to use database functions
3. All unit tests mock these dependencies and should pass without Databricks packages installed

### Protobuf Version Conflicts

If you see warnings about protobuf version conflicts:

```
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. 
This behaviour is the source of the following dependency conflicts.
streamlit X.X.X requires protobuf<6,>=3.20, but you have protobuf 6.X.X which is incompatible.
```

Solution:
```bash
pip install --force-reinstall "protobuf>=5.27.0,<6.0.0"
```

## Deactivating Virtual Environment

When you're done working:

```bash
deactivate
```

## Clean Reinstall

If you need to start fresh:

```bash
# Remove virtual environment
rm -rf venv

# Follow setup instructions again from step 1
```
