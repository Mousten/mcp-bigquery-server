"""FastAPI application setup and middleware."""
import asyncio
from typing import Dict
from fastapi import FastAPI, Request

# Store active connections with their message queues
active_connections: Dict[str, asyncio.Queue] = {}


def create_fastapi_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="MCP BigQuery Server",
        description="A server for securely accessing BigQuery datasets with support for HTTP and Stdio transport.",
        version="0.1.0",
    )

    # Add logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        print(f"Received request: {request.method} {request.url}")
        try:
            response = await call_next(request)
            print(f"Response status: {response.status_code}")
            return response
        except Exception as e:
            print(f"Error processing request: {e}")
            raise

    return app