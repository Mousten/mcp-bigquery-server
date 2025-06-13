# MCP BigQuery Server

A FastMCP server for securely accessing BigQuery datasets with support for HTTP and Stdio transport.

## Features

- **Multiple Transport Methods**: HTTP, Stdio, and SSE (Server-Sent Events)
- **BigQuery Integration**: Secure access to BigQuery datasets and tables
- **Real-time Events**: Server-Sent Events for query monitoring and system status
- **Read-only Queries**: Safety-first approach with read-only SQL execution
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

2. Edit `.env` with your BigQuery project details:

```bash
PROJECT_ID=your-project-id
LOCATION=US
KEY_FILE=/path/to/your/service-account-key.json  # Optional
```
```bash
cp .env.example .env
```

2. Edit `.env` with your BigQuery project details:
```bash
PROJECT_ID=your-project-id
LOCATION=US
KEY_FILE=/path/to/your/service-account-key.json  # Optional
```

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
# Edit .env with your BigQuery project details
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
        "KEY_FILE": "/path/to/your/service-account-key.json"
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
        "KEY_FILE": "C:\\path\\to\\your\\service-account-key.json"
      }
    }
  }
}
```

#### Alternative Windows Configuration (using Python directly):

```json
{
  "mcpServers": {
    "mcp-bigquery": {
      "command": "python",
      "args": ["-m", "mcp_bigquery.main", "--transport", "stdio"],
      "cwd": "C:\\path\\to\\your\\project",
      "env": {
        "PROJECT_ID": "your-project-id",
        "LOCATION": "US",
        "KEY_FILE": "C:\\path\\to\\your\\service-account-key.json"
      }
    }
  }
}
```

### 3. Authentication Setup

Choose one of two authentication methods:

**Option A: Service Account Key File**
1. Create a service account in Google Cloud Console
2. Download the JSON key file
3. Set the `KEY_FILE` environment variable to the path of this file

**Option B: Default Credentials**
1. Install and configure Google Cloud SDK: `gcloud auth application-default login`
2. Remove the `KEY_FILE` from the environment variables

### 4. Restart Claude Desktop

After saving the configuration file, restart Claude Desktop completely for the changes to take effect.

### 5. Using the Server

Once configured, you can interact with your BigQuery data through Claude Desktop:

- "What datasets do I have available in BigQuery?"
- "Show me the schema for the [dataset].[table] table"
- "Run a query to get the first 10 rows from [dataset].[table]"

The server provides these tools to Claude:
- `execute_bigquery_sql` - Execute read-only SQL queries
- `get_datasets` - List all datasets
- `get_tables` - Get tables in a dataset
- `get_table_schema` - Get detailed table schema

### Troubleshooting

If the server doesn't connect:

1. **Check the logs**: Claude Desktop shows error messages if the server fails to start
2. **Verify paths**: Ensure all file paths in the configuration are correct and accessible
3. **Test standalone**: Run `mcp-bigquery --transport stdio` in your terminal to check for errors
4. **Check permissions**: Ensure your service account has BigQuery Data Viewer and BigQuery Job User permissions
5. **Windows path format**: Use double backslashes (`\\`) and include the `.exe` extension

## API Endpoints

### Resources
- `GET /resources/list` - List all available datasets and tables
- `GET /bigquery/{project_id}/{dataset_id}/{table_id}` - Get table metadata

### Tools
- `POST /tools/execute_bigquery_sql` - Execute read-only SQL queries

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
- `execute_bigquery_sql` - Execute a read-only SQL query on BigQuery.
- `get_datasets` - Get list of datasets
- `get_tables` - Get tables in a dataset
- `get_table_schema` - Get table schema details

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
│   ├── core/                  # Core utilities (BigQuery client, JSON encoder)
│   ├── events/                # Event management system
│   ├── handlers/              # Business logic handlers
│   ├── api/                   # FastAPI and FastMCP applications
│   ├── routes/                # FastAPI route definitions
│   └── main.py                # Entry point
├── tests/                     # Test suite
├── pyproject.toml            # Project configuration
└── README.md                 # This file
```

## Authentication

The server supports two authentication methods:

1. **Service Account Key File**: Specify the path in the `KEY_FILE` environment variable
2. **Default Credentials**: Uses Google Cloud SDK default credentials if no key file is provided

## Security

- All SQL queries are restricted to read-only operations
- Forbidden keywords (INSERT, UPDATE, DELETE, CREATE, DROP, ALTER) are blocked
- Project ID validation ensures queries only run against the configured project
- Configurable query cost limits via `maximum_bytes_billed` parameter

## Event Streaming

The server provides real-time events via Server-Sent Events (SSE):

- **System Events**: Server health, connection status
- **Query Events**: Query start, progress, completion, errors
- **Resource Events**: Dataset and table updates

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request