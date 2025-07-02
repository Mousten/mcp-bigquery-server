"""FastAPI routes for tool operations."""
from typing import Dict, Any
from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from ..handlers.tools import query_tool_handler, get_datasets_handler


def create_tools_router(bigquery_client, event_manager, knowledge_base) -> APIRouter:
    """Create router for tool-related endpoints."""
    router = APIRouter(prefix="/tools", tags=["tools"])

    @router.post("/query")
    async def query_tool_fastapi(payload: Dict[str, Any] = Body(...)):
        """Execute a read-only SQL query on BigQuery."""
        sql = payload.get("sql", "")
        maximum_bytes_billed = payload.get("maximum_bytes_billed", 1000000000)
        use_cache = payload.get("use_cache", True)
        user_id = payload.get("user_id")
        # Remove session_id and force_refresh, as query_tool_handler does not accept them
        result = await query_tool_handler(
            bigquery_client, event_manager, sql, maximum_bytes_billed,
            knowledge_base, use_cache, user_id
        )
        if isinstance(result, tuple) and len(result) == 2:
            return JSONResponse(content=result[0], status_code=result[1])
        return result

    @router.post("/execute_bigquery_sql")
    async def execute_bigquery_sql_fastapi(payload: Dict[str, Any] = Body(...)):
        sql = payload.get("sql", "")
        maximum_bytes_billed = payload.get("maximum_bytes_billed", 1000000000)
        use_cache = payload.get("use_cache", True)
        user_id = payload.get("user_id")
        # Remove session_id and force_refresh, as query_tool_handler does not accept them
        result = await query_tool_handler(
            bigquery_client, event_manager, sql, maximum_bytes_billed,
            knowledge_base, use_cache, user_id
        )
        if isinstance(result, tuple) and len(result) == 2:
            return JSONResponse(content=result[0], status_code=result[1])
        return result

    @router.get("/datasets")
    async def get_datasets_fastapi():
        """Retrieve all datasets."""
        result = await get_datasets_handler(bigquery_client)
        if isinstance(result, tuple) and len(result) == 2:
            return JSONResponse(content=result[0], status_code=result[1])
        return result

    return router