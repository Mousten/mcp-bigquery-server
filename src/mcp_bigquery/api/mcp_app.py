"""MCP application setup and resource/tool registration."""
from fastmcp import FastMCP
from typing import Optional, List
from ..handlers.resources import list_resources_handler, read_resource_handler
from ..handlers.tools import (
    query_tool_handler,
    get_datasets_handler,
    get_tables_handler,
    get_table_schema_handler,
    # New enhanced tool handlers
    get_query_suggestions_handler,
    explain_table_handler,
    analyze_query_performance_handler,
    get_schema_changes_handler,
    cache_management_handler,
)
from ..core.supabase_client import SupabaseKnowledgeBase


def create_mcp_app(bigquery_client, config, event_manager) -> FastMCP:
    """Create and configure the FastMCP application."""
    mcp_app = FastMCP(
        name="mcp-bigquery-server",
        version="0.1.0",
        description="A FastMCP server for securely accessing BigQuery datasets with support for HTTP and Stdio transport.",
    )

    # Instantiate the Supabase knowledge base
    knowledge_base = SupabaseKnowledgeBase(
        # supabase_url=config.SUPABASE_URL,
        # supabase_key=config.SUPABASE_ANON_KEY,
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

    # EXISTING TOOLS
    @mcp_app.tool(
        name="execute_bigquery_sql", 
        description="Execute a read-only SQL query on BigQuery with caching support."
    )
    async def execute_bigquery_sql(
        sql: str, 
        maximum_bytes_billed: int = 1000000000,
        use_cache: bool = True,
        user_id: Optional[str] = None
    ) -> dict:
        """Execute a read-only SQL query on BigQuery with enhanced caching and analytics."""
        result = await query_tool_handler(
            bigquery_client, 
            event_manager, 
            sql, 
            maximum_bytes_billed, 
            knowledge_base=knowledge_base,
            use_cache=use_cache,
            user_id=user_id
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
        name="get_tables", 
        description="Retrieve all tables within a specific dataset."
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

    # NEW ENHANCED TOOLS
    @mcp_app.tool(
        name="get_query_suggestions",
        description="Get AI-powered query recommendations based on schema and usage patterns."
    )
    async def get_query_suggestions(
        tables_mentioned: Optional[List[str]] = None,
        query_context: Optional[str] = None,
        limit: int = 5
    ) -> dict:
        """Get intelligent query suggestions based on table schemas and historical usage patterns."""
        result = await get_query_suggestions_handler(
            bigquery_client,
            knowledge_base,
            tables_mentioned,
            query_context,
            limit
        )
        if isinstance(result, tuple):
            result, _ = result
        return result

    @mcp_app.tool(
        name="explain_table",
        description="Get rich table documentation with business context and column details."
    )
    async def explain_table(
        project_id: str,
        dataset_id: str,
        table_id: str
    ) -> dict:
        """Provide comprehensive table documentation including schema, business context, and usage patterns."""
        result = await explain_table_handler(
            bigquery_client,
            knowledge_base,
            project_id,
            dataset_id,
            table_id
        )
        if isinstance(result, tuple):
            result, _ = result
        return result

    @mcp_app.tool(
        name="analyze_query_performance",
        description="Analyze historical query performance for optimization insights."
    )
    async def analyze_query_performance(
        sql: Optional[str] = None,
        tables_accessed: Optional[List[str]] = None,
        time_range_hours: int = 168,
        user_id: Optional[str] = None
    ) -> dict:
        """Analyze query performance patterns and provide optimization recommendations."""
        result = await analyze_query_performance_handler(
            knowledge_base,
            sql,
            tables_accessed,
            time_range_hours,
            user_id
        )
        if isinstance(result, tuple):
            result, _ = result
        return result

    @mcp_app.tool(
        name="get_schema_changes",
        description="Track schema evolution and changes over time for a specific table."
    )
    async def get_schema_changes(
        project_id: str,
        dataset_id: str,
        table_id: str,
        limit: int = 10
    ) -> dict:
        """Retrieve schema change history and evolution analysis for a table."""
        result = await get_schema_changes_handler(
            knowledge_base,
            project_id,
            dataset_id,
            table_id,
            limit
        )
        if isinstance(result, tuple):
            result, _ = result
        return result

    @mcp_app.tool(
        name="manage_cache",
        description="Manual cache control operations (clear, refresh, stats)."
    )
    async def manage_cache(
        action: str,
        target: Optional[str] = None,
        project_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
        table_id: Optional[str] = None
    ) -> dict:
        """
        Manage query cache with various operations.
        
        Available actions:
        - clear_all: Clear all cache entries
        - clear_table: Clear cache for specific table (requires project_id, dataset_id, table_id)
        - clear_expired: Remove expired cache entries
        - cache_stats: Get cache usage statistics
        - cache_top_queries: Get most frequently accessed cached queries
        """
        result = await cache_management_handler(
            knowledge_base,
            action,
            target,
            project_id,
            dataset_id,
            table_id
        )
        if isinstance(result, tuple):
            result, _ = result
        return result

    return mcp_app