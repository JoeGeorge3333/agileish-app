# Implementation Plan: my-data-app

## Overview

This implementation plan creates a Databricks Streamlit application for predictive maintenance data exploration. The app provides three main pages (KPI Overview, Data Exploration, and Chat Interface) with schema introspection to adapt to different datasets, query guardrails for safety, and Unity Catalog integration for governance.

## Tasks

- [ ] 1. Set up project structure and database utilities
  - [x] 1.1 Create database connection module (components/db.py)
    - Implement Databricks SQL connection using session context
    - Create query execution function with error handling
    - Implement Unity Catalog table listing function
    - Implement secure view detection (checks for _secure_vw suffix)
    - _Requirements: 2.1, 9.1, 9.2_
  
  - [x] 1.2 Create schema introspection module (components/schema_introspector.py)
    - Implement column type detection (time, ID, label, categorical, numeric)
    - Use naming patterns for ID columns (asset_id, machine_id, unit, engine_id)
    - Use naming patterns for label columns (failure, fault, target, y, label)
    - Cache introspection results in session state
    - _Requirements: 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

- [ ] 2. Implement query guardrails and safety validation
  - [x] 2.1 Create guardrails module (components/guardrails.py)
    - Implement SELECT-only validation (reject DDL/DML)
    - Implement single statement validation
    - Implement table restriction validation
    - Implement automatic LIMIT clause injection
    - Implement SQL syntax validation
    - Return descriptive error messages for violations
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_
  
  - [x] 2.2 Write unit tests for guardrails module
    - Test rejection of DROP, INSERT, UPDATE, DELETE statements
    - Test rejection of multi-statement queries
    - Test table restriction enforcement
    - Test LIMIT clause injection
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [ ] 3. Implement KPI computation engine
  - [x] 3.1 Create KPI engine module (components/kpi_engine.py)
    - Implement row count KPI computation
    - Implement date range KPI (when time column exists)
    - Implement data missingness KPI
    - Implement failure rate KPI (when label column exists)
    - Implement unique asset count KPI (when ID column exists)
    - Implement fallback logic when expected columns are missing
    - Use aggregate queries to minimize data transfer
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 10.2, 10.3_
  
  - [x] 3.2 Create KPI page component (components/kpi_page.py)
    - Display dataset selector dropdown
    - Display computed KPIs in metric cards
    - Show explanations for fallback KPIs
    - Handle missing columns gracefully
    - _Requirements: 3.8, 11.1, 11.2_

- [ ] 4. Implement data visualization engine
  - [x] 4.1 Create chart generator module (components/chart_generator.py)
    - Implement time trend visualization (when time column exists)
    - Implement category breakdown visualization (when categorical columns exist)
    - Implement distribution/histogram visualization (when numeric columns exist)
    - Implement fallback logic and explanations for missing columns
    - Limit data points for rendering performance
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 10.4_
  
  - [x] 4.2 Integrate visualizations into KPI page
    - Add chart rendering to kpi_page.py
    - Display all generated visualizations
    - Show explanations when visualizations are skipped
    - _Requirements: 4.6, 11.4_

- [ ] 5. Checkpoint - Ensure KPI and visualization features work
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Implement data exploration page
  - [x] 6.1 Create explore page component (components/explore_page.py)
    - Implement dynamic filter generation based on column types
    - Create date range filter (when time column exists)
    - Create selectbox filters for categorical columns (top N categories)
    - Create range slider filters for numeric columns
    - Display filtered data preview with pagination
    - Implement download button for filtered results
    - Apply LIMIT clauses to restrict result sizes
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 10.1_

- [ ] 7. Implement conversational chat interface
  - [x] 7.1 Create query router module (components/query_router.py)
    - Implement template matching for intent detection
    - Support count query templates
    - Support summary statistics templates
    - Support trend analysis templates
    - Support top categories templates
    - Support failure rate calculation templates
    - Provide modular interface for future LLM integration
    - _Requirements: 6.3, 6.4, 12.1, 12.2, 12.3, 12.4_
  
  - [ ] 7.2 Create chat page component (components/chat_page.py)
    - Implement Streamlit chat UI (st.chat_message, st.chat_input)
    - Maintain message history in session state
    - Integrate query router for natural language to SQL conversion
    - Integrate guardrails engine for query validation
    - Execute validated queries and display results
    - Generate narrative answers from query results
    - Display results as dataframes
    - Generate visualizations for chartable results (2-column time series or category aggregates)
    - Display example questions to guide users
    - Show user-friendly error messages on query failures
    - _Requirements: 6.1, 6.2, 6.5, 6.6, 6.7, 6.8, 6.9, 11.3_
  
  - [ ] 7.3 Write unit tests for query router
    - Test intent template matching
    - Test SQL generation for each intent type
    - Test handling of ambiguous queries
    - _Requirements: 6.4, 12.1_

- [ ] 8. Checkpoint - Ensure explore and chat features work
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Implement main application and navigation
  - [ ] 9.1 Create main application file (app.py)
    - Set up Streamlit multi-page configuration
    - Implement sidebar navigation
    - Display user identity (or "Authenticated via Databricks Apps")
    - Initialize session state for dataset selection and schema cache
    - Wire together KPI, Explore, and Chat pages
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 8.1, 8.2, 8.3, 8.4_
  
  - [ ] 9.2 Create requirements.txt with dependencies
    - Add streamlit
    - Add databricks-sql-connector
    - Add pandas
    - Add plotly or altair for visualizations
    - _Requirements: 1.1_

- [ ] 10. Create governance documentation
  - [ ] 10.1 Create or update governance/steering_doc.md
    - Document allowed datasets (catalog and schema)
    - Document SELECT-only policy
    - Document query guardrails and resource limits
    - Document row-level security and column masking approach
    - _Requirements: 9.3, 9.4, 9.5, 9.7_
  
  - [ ] 10.2 Create or update governance/roles.md
    - Document conceptual roles (viewer, analyst, admin)
    - Document permissions for each role
    - _Requirements: 9.6_

- [ ] 11. Final integration and testing
  - [ ] 11.1 Test end-to-end workflows
    - Test dataset selection and schema introspection
    - Test KPI computation with different datasets
    - Test data exploration with filters
    - Test chat interface with example queries
    - Test guardrails with invalid queries
    - Test secure view fallback logic
    - _Requirements: 2.7, 7.5, 9.1, 9.2, 11.1, 11.2_
  
  - [ ] 11.2 Verify error handling and robustness
    - Test with datasets missing expected columns
    - Test with datasets having different schemas
    - Verify fallback behaviors work correctly
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

- [ ] 12. Final checkpoint - Ensure all features work end-to-end
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- The implementation uses Python and Streamlit on Databricks Apps platform
- Schema introspection enables the app to adapt to different predictive maintenance datasets
- Query guardrails ensure safe data access without compromising governance
- The modular query router design allows future integration with LLM services like Genie Conversation API
