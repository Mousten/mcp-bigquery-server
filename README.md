# MCP BigQuery Server

A FastMCP server for securely accessing BigQuery datasets with intelligent caching, schema evolution tracking, and query analytics via Supabase integration.

## Features

- **Multiple Transport Methods**: HTTP, Stdio, and SSE (Server-Sent Events)
- **BigQuery Integration**: Secure access to BigQuery datasets and tables
- **Intelligent Caching**: Query result caching with TTL management and dependency tracking
- **Supabase Knowledge Base**: Enhanced metadata storage and business context
- **Query Analytics**: Performance analysis and optimization recommendations
- **Schema Evolution Tracking**: Monitor table schema changes over time
- **AI-Powered Suggestions**: Query recommendations based on usage patterns
- **Real-time Events**: Server-Sent Events for query monitoring and system status
- **Read-only Queries**: Safety-first approach with read-only SQL execution
- **Row Level Security**: User-based access control and cache isolation
- **Comprehensive API**: RESTful endpoints and MCP protocol support

## Installation

Using `uv` (recommended):

```bash
# Clone the repository
git clone <repository-url>
cd mcp-bigquery-server

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

## Configuration

1. Copy the example environment file:

```bash
cp .env.example .env
```

2. Edit `.env` with your BigQuery and Supabase details:

```bash
# BigQuery Configuration
PROJECT_ID=your-project-id
LOCATION=US
KEY_FILE=/path/to/your/service-account-key.json  # Optional
DEFAULT_USER_ID=your-default-user-id  # Optional

# Supabase Configuration (for enhanced features)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key  # Recommended for full access
SUPABASE_ANON_KEY=your-anon-key  # Alternative with RLS
```

### Supabase Setup

For enhanced caching and analytics features, you'll need a Supabase project with the following tables and policies.  

- `query_cache` - Stores cached query results
- `table_dependencies` - Tracks table dependencies for cache invalidation
- `query_history` - Historical query execution patterns
- `query_templates` - Reusable query templates
- `column_documentation` - Business context for table columns
- `event_log` - System event tracking

**Run these SQL queries in your Supabase SQL editor to set up the schema:**

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Query Result Caching Tables
CREATE TABLE query_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  query_hash TEXT UNIQUE NOT NULL,
  sql_query TEXT NOT NULL,
  result_data JSONB NOT NULL,
  metadata JSONB NOT NULL, -- bytes processed, execution time, etc.
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
  hit_count INTEGER DEFAULT 0
);

-- Indexes for query_cache
CREATE INDEX idx_query_cache_hash ON query_cache(query_hash);
CREATE INDEX idx_query_cache_expires ON query_cache(expires_at);
CREATE INDEX idx_query_cache_created ON query_cache(created_at);

CREATE TABLE table_dependencies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  query_cache_id UUID REFERENCES query_cache(id) ON DELETE CASCADE,
  project_id TEXT NOT NULL,
  dataset_id TEXT NOT NULL,
  table_id TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for table_dependencies
CREATE INDEX idx_table_deps_lookup ON table_dependencies(project_id, dataset_id, table_id);
CREATE INDEX idx_table_deps_cache ON table_dependencies(query_cache_id);

-- 2. Schema Evolution & Knowledge Base Tables
CREATE TABLE schema_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id TEXT NOT NULL,
  dataset_id TEXT NOT NULL,
  table_id TEXT NOT NULL,
  schema_version INTEGER NOT NULL DEFAULT 1,
  schema_data JSONB NOT NULL,
  row_count BIGINT,
  size_bytes BIGINT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for schema_snapshots
CREATE UNIQUE INDEX idx_schema_version ON schema_snapshots(project_id, dataset_id, table_id, schema_version);
CREATE INDEX idx_schema_table ON schema_snapshots(project_id, dataset_id, table_id);

CREATE TABLE column_documentation (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id TEXT NOT NULL,
  dataset_id TEXT NOT NULL,
  table_id TEXT NOT NULL,
  column_name TEXT NOT NULL,
  description TEXT,
  business_rules TEXT[],
  sample_values JSONB,
  data_quality_notes TEXT,
  updated_by TEXT,
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for column_documentation
CREATE UNIQUE INDEX idx_column_docs_unique ON column_documentation(project_id, dataset_id, table_id, column_name);
CREATE INDEX idx_column_docs_table ON column_documentation(project_id, dataset_id, table_id);

-- 3. Query Analytics & Pattern Recognition Tables
CREATE TABLE query_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT,
  sql_query TEXT NOT NULL,
  execution_time_ms INTEGER,
  bytes_processed BIGINT,
  success BOOLEAN NOT NULL,
  error_message TEXT,
  tables_accessed TEXT[],
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for query_history
CREATE INDEX idx_query_history_user ON query_history(user_id);
CREATE INDEX idx_query_history_success ON query_history(success);
CREATE INDEX idx_query_history_created ON query_history(created_at);
CREATE INDEX idx_query_history_tables ON query_history USING GIN(tables_accessed);

CREATE TABLE query_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  description TEXT,
  template_sql TEXT NOT NULL,
  parameters JSONB NOT NULL DEFAULT '{}',
  usage_count INTEGER DEFAULT 0,
  tags TEXT[],
  created_by TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for query_templates
CREATE INDEX idx_query_templates_usage ON query_templates(usage_count DESC);
CREATE INDEX idx_query_templates_tags ON query_templates USING GIN(tags);

-- 4. Real-time Event Tracking
CREATE TABLE event_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type TEXT NOT NULL,
  event_data JSONB NOT NULL,
  user_id TEXT,
  session_id TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for event_log
CREATE INDEX idx_event_log_type ON event_log(event_type);
CREATE INDEX idx_event_log_user ON event_log(user_id);
CREATE INDEX idx_event_log_session ON event_log(session_id);
CREATE INDEX idx_event_log_created ON event_log(created_at);

-- 5. User Preferences & Settings
CREATE TABLE user_preferences (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT UNIQUE NOT NULL,
  preferences JSONB NOT NULL DEFAULT '{}',
  query_defaults JSONB NOT NULL DEFAULT '{}',
  favorite_queries UUID[] DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Row Level Security (RLS) Policies for BigQuery Cache Tables

-- First, ensure RLS is enabled on the tables
ALTER TABLE query_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE query_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE table_dependencies ENABLE ROW LEVEL SECURITY;
ALTER TABLE schema_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE column_documentation ENABLE ROW LEVEL SECURITY;
ALTER TABLE query_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE event_log ENABLE ROW LEVEL SECURITY;

-- Option 1: Allow all operations (least secure, but simplest for development)
-- Use this during development/testing phases

-- Allow all operations on query_cache
CREATE POLICY "Allow all operations on query_cache" ON query_cache
FOR ALL USING (true) WITH CHECK (true);

-- Allow all operations on query_history
CREATE POLICY "Allow all operations on query_history" ON query_history
FOR ALL USING (true) WITH CHECK (true);

-- Allow all operations on table_dependencies
CREATE POLICY "Allow all operations on table_dependencies" ON table_dependencies
FOR ALL USING (true) WITH CHECK (true);

-- Allow all operations on schema_snapshots
CREATE POLICY "Allow all operations on schema_snapshots" ON schema_snapshots
FOR ALL USING (true) WITH CHECK (true);

-- Allow all operations on column_documentation
CREATE POLICY "Allow all operations on column_documentation" ON column_documentation
FOR ALL USING (true) WITH CHECK (true);

-- Allow all operations on query_templates
CREATE POLICY "Allow all operations on query_templates" ON query_templates
FOR ALL USING (true) WITH CHECK (true);

-- Allow all operations on event_log
CREATE POLICY "Allow all operations on event_log" ON event_log
FOR ALL USING (true) WITH CHECK (true);

-- Option 2: User-based policies (more secure)
-- Uncomment and use these instead if you have user authentication

/*
-- Allow users to manage their own cache entries
CREATE POLICY "Users can manage own cache entries" ON query_cache
FOR ALL USING (auth.uid()::text = user_id OR user_id IS NULL);

-- Allow users to manage their own query history
CREATE POLICY "Users can manage own query history" ON query_history
FOR ALL USING (auth.uid()::text = user_id OR user_id IS NULL);

-- Allow all operations on system tables (no user-specific data)
CREATE POLICY "Allow system operations" ON table_dependencies
FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow system operations" ON schema_snapshots
FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow system operations" ON column_documentation
FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow system operations" ON query_templates
FOR ALL USING (true) WITH CHECK (true);

-- Allow users to create their own event log entries
CREATE POLICY "Users can create event logs" ON event_log
FOR INSERT WITH CHECK (auth.uid()::text = user_id OR user_id IS NULL);

CREATE POLICY "Users can read event logs" ON event_log
FOR SELECT USING (auth.uid()::text = user_id OR user_id IS NULL);
*/

-- Option 3: Service role policies (for backend services)
-- If your application uses a service role key, you might want to create
-- policies that allow the service role to perform all operations

/*
-- Create a function to check if the current role is the service role
CREATE OR REPLACE FUNCTION is_service_role()
RETURNS BOOLEAN AS $$
BEGIN
  RETURN current_setting('role') = 'service_role';
EXCEPTION
  WHEN others THEN
    RETURN false;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Service role policies
CREATE POLICY "Service role can manage query_cache" ON query_cache
FOR ALL USING (is_service_role()) WITH CHECK (is_service_role());

CREATE POLICY "Service role can manage query_history" ON query_history
FOR ALL USING (is_service_role()) WITH CHECK (is_service_role());
*/

-- Triggers for automatic timestamp updates
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_column_documentation_updated_at
    BEFORE UPDATE ON column_documentation
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_query_templates_updated_at
    BEFORE UPDATE ON query_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_preferences_updated_at
    BEFORE UPDATE ON user_preferences
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Cache Cleanup Function
CREATE OR REPLACE FUNCTION cleanup_expired_cache()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM query_cache WHERE expires_at < NOW();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;
```

**These tables enable:**
- Query result caching and dependency tracking
- Schema evolution and documentation
- Query analytics and pattern recognition
- Real-time event logging
- User preferences and settings

**Row Level Security (RLS)** is enabled for all tables.  
You can choose from several RLS policy options:
- **Option 1:** Allow all operations (for development/testing)
- **Option 2:** User-based policies (recommended for production with authentication)
- **Option 3:** Service role policies (for backend services)

Customize the RLS policies as needed for your environment.

The server will work without Supabase but with limited functionality.

## Usage

### Command Line

```bash
# HTTP mode (default)
mcp-bigquery --transport http --host 0.0.0.0 --port 8000

# Stdio mode (for MCP clients)
mcp-bigquery --transport stdio

# SSE mode
mcp-bigquery --transport sse --host 0.0.0.0 --port 8000
```

### Python API

```python
from mcp_bigquery.main import main
import sys

# Set command line arguments
sys.argv = ['mcp-bigquery', '--transport', 'http', '--port', '8000']
main()
```

## Using with Claude Desktop

To use this MCP BigQuery server with Claude Desktop, you need to configure it in your Claude Desktop configuration file.

### 1. Install and Configure the Server

First, ensure the server is installed and configured:

```bash
# Clone and install the server
git clone <repository-url>
cd mcp-bigquery-server
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# Set up environment variables
cp .env.example .env
# Edit .env with your BigQuery and Supabase project details
```

### 2. Configure Claude Desktop

Add the server to your Claude Desktop configuration file:

**Configuration file locations:**
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

#### For macOS/Linux:

```json
{
  "mcpServers": {
    "mcp-bigquery": {
      "command": "/path/to/your/project/.venv/bin/mcp-bigquery",
      "args": ["--transport", "stdio"],
      "env": {
        "PROJECT_ID": "your-project-id",
        "LOCATION": "US",
        "KEY_FILE": "/path/to/your/service-account-key.json",
        "SUPABASE_URL": "https://your-project.supabase.co",
        "SUPABASE_SERVICE_KEY": "your-service-role-key",
        "DEFAULT_USER_ID": "your-user-id"
      }
    }
  }
}
```

#### For Windows:

```json
{
  "mcpServers": {
    "mcp-bigquery": {
      "command": "C:\\path\\to\\your\\project\\.venv\\Scripts\\mcp-bigquery.exe",
      "args": ["--transport", "stdio"],
      "env": {
        "PROJECT_ID": "your-project-id",
        "LOCATION": "US",
        "KEY_FILE": "C:\\path\\to\\your\\service-account-key.json",
        "SUPABASE_URL": "https://your-project.supabase.co",
        "SUPABASE_SERVICE_KEY": "your-service-role-key",
        "DEFAULT_USER_ID": "your-user-id"
      }
    }
  }
}
```

### 3. Authentication Setup

**BigQuery Authentication** - Choose one of two authentication methods:

**Option A: Service Account Key File**
1. Create a service account in Google Cloud Console
2. Download the JSON key file
3. Set the `KEY_FILE` environment variable to the path of this file

**Option B: Default Credentials**
1. Install and configure Google Cloud SDK: `gcloud auth application-default login`
2. Remove the `KEY_FILE` from the environment variables

**Supabase Authentication** (Optional but recommended):
1. Create a Supabase project
2. Get your project URL and service role key from the Supabase dashboard
3. Set up the required database schema (see Supabase Setup section)

### 4. Restart Claude Desktop

After saving the configuration file, restart Claude Desktop completely for the changes to take effect.

### 5. Using the Server

Once configured, you can interact with your BigQuery data through Claude Desktop with enhanced capabilities:

**Basic Operations:**
- "What datasets do I have available in BigQuery?"
- "Show me the schema for the [dataset].[table] table"
- "Run a query to get the first 10 rows from [dataset].[table]"

**Enhanced Features (with Supabase):**
- "Analyze the performance of my recent queries"
- "What query suggestions do you have for the sales table?"
- "Show me the schema changes for [dataset].[table] over the last month"
- "Explain what the customer_events table is used for"
- "What are the cache statistics?"

## API Endpoints

### Resources
- `GET /resources/list` - List all available datasets and tables
- `GET /bigquery/{project_id}/{dataset_id}/{table_id}` - Get table metadata

### Tools
- `POST /tools/execute_bigquery_sql` - Execute read-only SQL queries with caching
- `POST /tools/get_datasets` - Get list of datasets with metadata
- `POST /tools/get_tables` - Get tables in a dataset with documentation
- `POST /tools/get_table_schema` - Get table schema with business context
- `POST /tools/get_query_suggestions` - Get AI-powered query recommendations
- `POST /tools/explain_table` - Get comprehensive table documentation
- `POST /tools/analyze_query_performance` - Analyze query performance patterns
- `POST /tools/get_schema_changes` - Track schema evolution over time
- `POST /tools/manage_cache` - Cache management operations
- `POST /tools/health_check` - System health check

### Events (SSE)
- `GET /events/system` - System status events
- `GET /events/queries` - Query execution events
- `GET /events/resources` - Resource update events

### Health
- `GET /health` - Health check endpoint

## MCP Tools and Resources

### Resources
- `resources://list` - List all BigQuery resources
- `bigquery://{project}/{dataset}/{table}` - Access specific table metadata

### Tools

#### Core BigQuery Tools
- `execute_bigquery_sql` - Execute a read-only SQL query with intelligent caching
  - Parameters: `sql`, `maximum_bytes_billed`, `use_cache`, `user_id`, `force_refresh`
- `get_datasets` - Get list of datasets with metadata
- `get_tables` - Get tables in a dataset with column documentation
- `get_table_schema` - Get comprehensive table schema details
  - Parameters: `dataset_id`, `table_id`, `include_samples`, `include_documentation`

#### Enhanced Analytics Tools (requires Supabase)
- `get_query_suggestions` - Get AI-powered query recommendations
  - Parameters: `tables_mentioned`, `query_context`, `limit`, `user_id`
- `explain_table` - Get comprehensive table documentation and business context
  - Parameters: `project_id`, `dataset_id`, `table_id`, `include_usage_stats`, `user_id`
- `analyze_query_performance` - Analyze historical query performance patterns
  - Parameters: `sql`, `tables_accessed`, `time_range_hours`, `user_id`, `include_recommendations`
- `get_schema_changes` - Track schema evolution and changes over time
  - Parameters: `project_id`, `dataset_id`, `table_id`, `limit`, `include_impact_analysis`, `user_id`

#### System Management Tools
- `manage_cache` - Comprehensive cache management operations
  - Parameters: `action`, `target`, `project_id`, `dataset_id`, `table_id`, `user_id`
- `health_check` - System health check including BigQuery, Supabase, and cache status
  - Parameters: `user_id`

## Intelligent Caching System

The server includes a sophisticated caching system powered by Supabase:

### Features
- **Query Result Caching**: Automatic caching of query results with configurable TTL
- **Table Dependency Tracking**: Cache invalidation based on table modifications
- **Cache Statistics**: Hit rates, performance metrics, and usage analytics
- **User-based Isolation**: Row Level Security for multi-tenant environments
- **Automatic Cleanup**: Expired cache entry removal

### Cache Management
```python
# Cache a query result (automatic)
result = await execute_bigquery_sql(sql="SELECT * FROM dataset.table", use_cache=True)

# Force cache refresh
result = await execute_bigquery_sql(sql="SELECT * FROM dataset.table", force_refresh=True)

# Get cache statistics
stats = await manage_cache(action="stats")

# Clean up expired entries
cleanup = await manage_cache(action="cleanup")
```

## Development

### Setup Development Environment

```bash
# Install with development dependencies
uv pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=src/mcp_bigquery --cov-report=html

# Format code
black src/ tests/
isort src/ tests/

# Type checking
mypy src/
```

### Project Structure

```
mcp-bigquery-server/
├── src/mcp_bigquery/          # Main package
│   ├── config/                # Configuration management
│   ├── core/                  # Core utilities (BigQuery client, Supabase client, JSON encoder)
│   ├── events/                # Event management system
│   ├── handlers/              # Business logic handlers
│   │   ├── resources.py       # Resource handlers
│   │   └── tools.py          # Tool handlers (query execution, analytics)
│   ├── api/                   # FastAPI and FastMCP applications
│   ├── routes/                # FastAPI route definitions
│   └── main.py                # Entry point
├── tests/                     # Test suite
├── pyproject.toml            # Project configuration
└── README.md                 # This file
```

## Authentication

### BigQuery Authentication
The server supports two authentication methods:

1. **Service Account Key File**: Specify the path in the `KEY_FILE` environment variable
2. **Default Credentials**: Uses Google Cloud SDK default credentials if no key file is provided

### Supabase Authentication
- **Service Role Key**: Full access to all tables (recommended for server deployment)
- **Anonymous Key**: Limited access with Row Level Security (RLS) policies

## Security

- All SQL queries are restricted to read-only operations
- Forbidden keywords (INSERT, UPDATE, DELETE, CREATE, DROP, ALTER) are blocked
- Project ID validation ensures queries only run against the configured project
- Configurable query cost limits via `maximum_bytes_billed` parameter
- Row Level Security (RLS) support for multi-tenant deployments
- User-based cache isolation and access control

## Event Streaming

The server provides real-time events via Server-Sent Events (SSE):

- **System Events**: Server health, connection status, Supabase connectivity
- **Query Events**: Query start, progress, completion, errors, cache hits/misses
- **Resource Events**: Dataset and table updates, schema changes
- **Analytics Events**: Performance insights, usage patterns

## Performance Considerations

- **Query Caching**: Significantly reduces BigQuery costs and improves response times
- **Connection Pooling**: Efficient BigQuery client management
- **Async Operations**: Non-blocking I/O for better concurrency
- **Lazy Loading**: Supabase connections initialized only when needed
- **Cache Optimization**: Intelligent cache key generation and dependency tracking

## Monitoring and Observability

The server provides comprehensive monitoring capabilities:

- **Health Checks**: BigQuery and Supabase connectivity status
- **Cache Metrics**: Hit rates, storage usage, performance statistics
- **Query Analytics**: Execution patterns, cost analysis, optimization recommendations
- **Event Logging**: Detailed audit trails for all operations
- **Error Tracking**: Comprehensive error logging and reporting

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

[Add your license information here]

## Changelog

### v0.2.0
- Added Supabase integration for enhanced caching and analytics
- Implemented intelligent query caching with table dependency tracking
- Added AI-powered query suggestions and table explanations
- Enhanced schema evolution tracking capabilities
- Improved performance analysis and optimization recommendations
- Added comprehensive event logging and audit trails
- Implemented Row Level Security (RLS) support for multi-tenant deployments