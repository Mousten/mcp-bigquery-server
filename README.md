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

For enhanced caching and analytics features, you'll need a Supabase project with the following tables:

- `query_cache` - Stores cached query results
- `table_dependencies` - Tracks table dependencies for cache invalidation
- `query_history` - Historical query execution patterns
- `query_templates` - Reusable query templates
- `column_documentation` - Business context for table columns
- `event_log` - System event tracking

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