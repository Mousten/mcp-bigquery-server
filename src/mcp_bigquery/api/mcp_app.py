"""MCP application setup and resource/tool registration."""
from fastmcp import FastMCP
from ..handlers.resources import list_resources_handler, read_resource_handler
from ..handlers.tools import (
    query_tool_handler,
    get_datasets_handler,
    get_tables_handler,
    get_table_schema_handler,
)


def create_mcp_app(bigquery_client, config, event_manager) -> FastMCP:
    """Create and configure the FastMCP application."""
    mcp_app = FastMCP(
        name="mcp-bigquery-server",
        version="0.1.0",
        description="A FastMCP server for securely accessing BigQuery datasets with support for HTTP and Stdio transport.",
    )

    @mcp_app.resource("resources://list")
    async def list_resources_mcp() -> dict:
        """List all available BigQuery datasets and tables."""
        result = await list_resources_handler(bigquery_client, config)
        if isinstance(result, tuple):
            result, _ = result  # Ignore status code if present
        return result

    @mcp_app.resource("bigquery://{project_id}/{dataset_id}/{table_id}")
    async def read_resource_mcp(
        project_id: str, dataset_id: str, table_id: str
    ) -> dict:
        """Retrieve metadata for a specific BigQuery table."""
        result = await read_resource_handler(
            bigquery_client, config, project_id, dataset_id, table_id
        )
        if isinstance(result, tuple):
            result, _ = result
        return result

    @mcp_app.tool(
        name="execute_bigquery_sql", description="Execute a read-only SQL query on BigQuery."
    )
    async def execute_bigquery_sql(
        sql: str, maximum_bytes_billed: int = 1000000000
    ) -> dict:
        """Execute a read-only SQL query on BigQuery."""
        result = await query_tool_handler(
            bigquery_client, event_manager, sql, maximum_bytes_billed
        )
        if isinstance(result, tuple):
            result, _ = result
        return result

    @mcp_app.tool(
        name="get_datasets",
        description="Retrieve the list of all datasets in the current project.",
    )
    async def get_datasets() -> dict:
        """Retrieve the list of all datasets in the current project."""
        result = await get_datasets_handler(bigquery_client)
        if isinstance(result, tuple):
            result, _ = result
        return result

    @mcp_app.tool(
        name="get_tables", description="Retrieve all tables within a specific dataset."
    )
    async def get_tables(dataset_id: str) -> dict:
        """Retrieve all tables within a specific dataset."""
        result = await get_tables_handler(bigquery_client, dataset_id)
        if isinstance(result, tuple):
            result, _ = result
        return result

    @mcp_app.tool(
        name="get_table_schema",
        description="Retrieve schema details for a specific table.",
    )
    async def get_table_schema(dataset_id: str, table_id: str) -> dict:
        """Retrieve schema details for a specific table."""
        result = await get_table_schema_handler(bigquery_client, dataset_id, table_id)
        if isinstance(result, tuple):
            result, _ = result
        return result

    return mcp_app