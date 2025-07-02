"""Main entry point for the MCP BigQuery server."""
import sys
import argparse
from .config.settings import ServerConfig
from .core.bigquery_client import init_bigquery_client
from .events.manager import EventManager
from .api.fastapi_app import create_fastapi_app
from .api.mcp_app import create_mcp_app
from .routes.resources import create_resources_router, create_bigquery_router
from .routes.tools import create_tools_router
from .routes.events import create_events_router
from .routes.health import create_health_router


def main():
    """Main entry point for the application."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="MCP BigQuery Server")
    parser.add_argument(
        "--transport",
        choices=["http", "stdio", "sse"],
        default="http",
        help="Transport method (http, stdio, or sse)",
    )
    parser.add_argument("--port", type=int, default=8000, help="Port for server")
    parser.add_argument("--host", default="0.0.0.0", help="Host for server")
    args = parser.parse_args()

    # Load configuration
    config = ServerConfig.from_env()
    try:
        config.validate()
    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)

    # Initialize BigQuery client
    bigquery_client = init_bigquery_client(config)

    # Initialize event manager
    event_manager = EventManager()

    if args.transport == "sse":
        # Create MCP app for SSE mode
        mcp_app = create_mcp_app(bigquery_client, config, event_manager)
        print(f"Starting MCP server in SSE mode on {args.host}:{args.port}...")
        mcp_app.run(transport="sse", host=args.host, port=args.port)
    
    elif args.transport == "stdio":
        # Create MCP app for stdio mode
        mcp_app = create_mcp_app(bigquery_client, config, event_manager)
        print("Starting server in stdio mode...")
        mcp_app.run(transport="stdio")
    
    else:
        # Create FastAPI app for HTTP mode
        fastapi_app = create_fastapi_app()

        # Initialize SupabaseKnowledgeBase
        from .core.supabase_client import SupabaseKnowledgeBase
        knowledge_base = SupabaseKnowledgeBase(supabase_url=config.supabase_url, supabase_key=config.supabase_key)

        # Create and include routers
        resources_router = create_resources_router(bigquery_client, config)
        bigquery_router = create_bigquery_router(bigquery_client, config)
        tools_router = create_tools_router(bigquery_client, event_manager, knowledge_base)
        events_router = create_events_router(event_manager)
        health_router = create_health_router(event_manager)
        
        # Import and create preferences router
        from .routes.preferences import create_preferences_router
        preferences_router = create_preferences_router(knowledge_base)

        # Include all routers
        fastapi_app.include_router(resources_router)
        fastapi_app.include_router(bigquery_router)
        fastapi_app.include_router(tools_router)
        fastapi_app.include_router(events_router)
        fastapi_app.include_router(health_router)
        fastapi_app.include_router(preferences_router)

        print(f"Starting server in HTTP mode on {args.host}:{args.port}...")
        import uvicorn
        uvicorn.run(fastapi_app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()