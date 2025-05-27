"""FastAPI routes for tool operations."""
from typing import Dict, Any
from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from ..handlers.tools import query_tool_handler


def create_tools_router(bigquery_client, event_manager) -> APIRouter:
    """Create router for tool-related endpoints."""
    router = APIRouter(prefix="/tools", tags=["tools"])

    @router.post("/query")
    async def query_tool_fastapi(payload: Dict[str, Any] = Body(...)):
        """Execute a read-only SQL query on BigQuery."""
        sql = payload.get("sql", "")
        maximum_bytes_billed = payload.get("maximum_bytes_billed", 1000000000)
        result = await query_tool_handler(bigquery_client, event_manager, sql, maximum_bytes_billed)
        if isinstance(result, tuple) and len(result) == 2:
            return JSONResponse(content=result[0], status_code=result[1])
        return result

    return router