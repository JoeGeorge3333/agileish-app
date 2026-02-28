# Requirements Document

## Introduction

The Predictive Maintenance Data App Factory is a governed, self-service data application for business users built on Databricks using Streamlit. The system enables users to explore predictive maintenance datasets through visual KPIs, interactive dashboards, and a conversational chat interface while enforcing governance policies through Unity Catalog.

## Glossary

- **Data_App**: The Streamlit application running on Databricks Apps platform
- **Unity_Catalog**: Databricks data governance layer providing access control and data discovery
- **Dataset_Selector**: Component allowing users to choose from available catalog tables
- **Schema_Introspector**: Component that analyzes table schemas to detect column types and purposes
- **KPI_Engine**: Component that computes key performance indicators from selected datasets
- **Chart_Generator**: Component that creates visualizations based on inferred column types
- **Chat_Interface**: Conversational UI for natural language data queries
- **Query_Router**: Component that converts natural language to SQL query templates
- **Guardrails_Engine**: Component that validates and restricts SQL queries for safety
- **Secure_View**: Unity Catalog view with governance policies applied (masking, filtering)
- **Base_Table**: Original table in Unity Catalog without additional governance layers

## Requirements

### Requirement 1: Application Structure and Navigation

**User Story:** As a business user, I want to navigate between different application features, so that I can access KPIs, explore data, and chat with data from a single interface.

#### Acceptance Criteria

1. THE Data_App SHALL provide a multi-page Streamlit application with sidebar navigation
2. THE Data_App SHALL include an Overview page for KPIs and charts
3. THE Data_App SHALL include an Explore page for data filtering and preview
4. THE Data_App SHALL include a Chat page for conversational data queries
5. WHEN a user selects a navigation option, THE Data_App SHALL display the corresponding page without requiring page reload

### Requirement 2: Dataset Selection and Schema Introspection

**User Story:** As a business user, I want to select from available datasets and have the app adapt to different schemas, so that I can work with multiple predictive maintenance datasets.

#### Acceptance Criteria

1. THE Dataset_Selector SHALL query Unity Catalog to list available tables from catalog "dataknobs_predictive_maintenance_and_asset_management" and schema "datasets"
2. WHEN a user selects a dataset, THE Schema_Introspector SHALL analyze the table schema and detect column types
3. THE Schema_Introspector SHALL identify time columns based on date or timestamp data types
4. THE Schema_Introspector SHALL identify ID columns based on naming patterns (asset_id, machine_id, unit, engine_id)
5. THE Schema_Introspector SHALL identify label columns based on naming patterns (failure, fault, target, y, label)
6. THE Schema_Introspector SHALL classify columns as categorical or numeric based on data types
7. WHEN schema introspection completes, THE Data_App SHALL adapt all features to use the detected column types

### Requirement 3: KPI Computation and Display

**User Story:** As a business analyst, I want to see key performance indicators for the selected dataset, so that I can quickly understand data characteristics and quality.

#### Acceptance Criteria

1. THE KPI_Engine SHALL compute at least 5 key performance indicators for the selected dataset
2. THE KPI_Engine SHALL compute row count for all datasets
3. WHEN a time column exists, THE KPI_Engine SHALL compute date range (min and max dates)
4. THE KPI_Engine SHALL compute data missingness percentage across all columns
5. WHEN a label column exists, THE KPI_Engine SHALL compute failure rate or label distribution
6. WHEN an ID column exists, THE KPI_Engine SHALL compute count of unique assets or entities
7. WHEN required columns do not exist for a KPI, THE KPI_Engine SHALL compute alternative metrics and display an explanation of the fallback choice
8. THE Data_App SHALL display all computed KPIs on the Overview page

### Requirement 4: Data Visualization

**User Story:** As a business analyst, I want to see visualizations of the dataset, so that I can identify patterns and trends in predictive maintenance data.

#### Acceptance Criteria

1. THE Chart_Generator SHALL create at least 3 different visualization types for the selected dataset
2. WHEN a time column exists, THE Chart_Generator SHALL create a time trend visualization
3. WHEN categorical columns exist, THE Chart_Generator SHALL create a category breakdown visualization
4. WHEN numeric columns exist, THE Chart_Generator SHALL create a distribution or histogram visualization
5. WHEN required columns do not exist for a visualization type, THE Chart_Generator SHALL create alternative visualizations and display an explanation
6. THE Data_App SHALL display all generated visualizations on the Overview page

### Requirement 5: Data Exploration and Filtering

**User Story:** As a data analyst, I want to filter and preview dataset contents, so that I can examine specific subsets of data and download results.

#### Acceptance Criteria

1. THE Data_App SHALL provide dynamic filters on the Explore page based on detected column types
2. WHEN a time column exists, THE Data_App SHALL provide a date range filter
3. WHEN categorical columns exist, THE Data_App SHALL provide selectbox filters showing top N categories
4. WHEN numeric columns exist, THE Data_App SHALL provide range slider filters for key numeric fields
5. WHEN filters are applied, THE Data_App SHALL display a preview of filtered data
6. THE Data_App SHALL provide a download option for filtered data results

### Requirement 6: Conversational Chat Interface

**User Story:** As a business user, I want to ask questions about data in natural language, so that I can get insights without writing SQL queries.

#### Acceptance Criteria

1. THE Chat_Interface SHALL use Streamlit chat UI components (st.chat_message and st.chat_input)
2. THE Chat_Interface SHALL maintain message history for the current session
3. WHEN a user submits a natural language question, THE Query_Router SHALL convert it to a SQL query using template matching
4. THE Query_Router SHALL support intent templates for: count queries, summary statistics, trend analysis, top categories, and failure rate calculations
5. WHEN a query is generated, THE Guardrails_Engine SHALL validate it before execution
6. WHEN a query executes successfully, THE Chat_Interface SHALL return a short narrative answer
7. WHEN a query executes successfully, THE Chat_Interface SHALL display results as a dataframe or table
8. WHEN query results are chartable (2-column time series or category aggregate), THE Chat_Interface SHALL generate and display a visualization
9. THE Chat_Interface SHALL provide example questions to guide users

### Requirement 7: Query Guardrails and Safety

**User Story:** As a data governance officer, I want to ensure users can only execute safe queries, so that data integrity and system resources are protected.

#### Acceptance Criteria

1. THE Guardrails_Engine SHALL enforce SELECT-only queries and reject DDL or DML statements
2. THE Guardrails_Engine SHALL enforce single statement execution and reject multi-statement queries
3. THE Guardrails_Engine SHALL restrict queries to the selected table or approved secure views
4. WHEN a query does not specify a row limit, THE Guardrails_Engine SHALL apply a default LIMIT clause
5. WHEN a query violates guardrails, THE Guardrails_Engine SHALL reject it and return a descriptive error message
6. THE Guardrails_Engine SHALL validate SQL syntax before execution

### Requirement 8: Authentication and User Identity

**User Story:** As a system administrator, I want users to authenticate through Databricks SSO, so that access is controlled without custom login screens.

#### Acceptance Criteria

1. THE Data_App SHALL rely on Databricks Apps platform authentication for user access
2. THE Data_App SHALL NOT implement a custom login form or authentication screen
3. WHEN authentication information is available, THE Data_App SHALL display current user identity
4. WHEN authentication information is not available, THE Data_App SHALL display "Authenticated via Databricks Apps"

### Requirement 9: Governance and Secure Data Access

**User Story:** As a data governance officer, I want the app to use governed data access patterns, so that sensitive data is protected according to Unity Catalog policies.

#### Acceptance Criteria

1. WHEN a secure view exists for a table (naming pattern: <table>_secure_vw), THE Data_App SHALL query the secure view instead of the base table
2. WHEN a secure view does not exist, THE Data_App SHALL query the base table directly
3. THE Data_App SHALL provide governance documentation explaining allowed datasets
4. THE Data_App SHALL provide governance documentation explaining SELECT-only policy
5. THE Data_App SHALL provide governance documentation explaining query guardrails and resource limits
6. THE Data_App SHALL provide governance documentation explaining conceptual roles (viewer, analyst, admin)
7. THE Data_App SHALL provide governance documentation explaining how row-level security and column masking are applied in Unity Catalog

### Requirement 10: Performance and Resource Management

**User Story:** As a system administrator, I want the app to use compute resources efficiently, so that costs are controlled and performance is maintained.

#### Acceptance Criteria

1. THE Data_App SHALL use LIMIT clauses in queries to restrict result set sizes
2. THE Data_App SHALL use aggregate queries instead of full table scans where possible
3. WHEN computing KPIs, THE Data_App SHALL optimize queries to minimize data transfer
4. WHEN generating visualizations, THE Data_App SHALL limit data points to maintain rendering performance

### Requirement 11: Robustness and Error Handling

**User Story:** As a business user, I want the app to handle different dataset structures gracefully, so that I can work with various predictive maintenance tables without errors.

#### Acceptance Criteria

1. WHEN a dataset lacks expected columns, THE Data_App SHALL adapt functionality using available columns
2. WHEN column inference fails, THE Data_App SHALL provide fallback behavior and inform the user
3. WHEN a query fails, THE Chat_Interface SHALL display a user-friendly error message
4. WHEN data cannot be visualized, THE Chart_Generator SHALL skip that visualization and explain why
5. THE Data_App SHALL NOT hard-code column names except when inferred through schema introspection

### Requirement 12: Modular Architecture for Future Extensions

**User Story:** As a developer, I want the chat system to be modular, so that I can integrate external LLM services like Genie Conversation API without rewriting core logic.

#### Acceptance Criteria

1. THE Query_Router SHALL implement a rules-based template matching system as the default query generation method
2. THE Query_Router SHALL provide an interface that allows swapping in alternative query generation implementations
3. THE Data_App SHALL function completely with the rules-based router without requiring external LLM API calls
4. WHERE an external LLM integration is configured, THE Query_Router SHALL support using it as an alternative to template matching
