"""Enhanced tool handlers for BigQuery operations with Supabase caching and knowledge base integration."""
import json
import uuid
import re
from typing import Dict, Any, Tuple, Union, List, Optional
from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPIError
from ..core.json_encoder import CustomJSONEncoder
from ..core.supabase_client import SupabaseKnowledgeBase


def extract_table_references(sql: str) -> List[str]:
    """Extract table references from SQL query."""
    pattern = r'FROM\s+`?([a-zA-Z0-9_.-]+)`?|JOIN\s+`?([a-zA-Z0-9_.-]+)`?'
    matches = re.findall(pattern, sql, re.IGNORECASE)
    tables = []
    for match in matches:
        table = match[0] or match[1]
        if table:
            tables.append(table)
    return tables


async def query_tool_handler(
    bigquery_client,
    event_manager,
    sql: str,
    maximum_bytes_billed: int = 1000000000,
    knowledge_base: Optional[SupabaseKnowledgeBase] = None,
    use_cache: bool = True,
    user_id: Optional[str] = None,
) -> Union[Dict[str, Any], Tuple[Dict[str, Any], int]]:
    """Enhanced query handler with caching and knowledge base integration."""
    try:
        query_id = str(uuid.uuid4())
        tables_accessed = extract_table_references(sql)

        # Check cache first if enabled and knowledge_base is provided
        cached_result = None
        if use_cache and knowledge_base is not None:
            cached_result = await knowledge_base.get_cached_query(sql)
            if cached_result:
                await event_manager.broadcast(
                    "queries",
                    "query_cache_hit",
                    {
                        "query_id": query_id,
                        "sql": sql[:100] + "..." if len(sql) > 100 else sql,
                        "cached_at": cached_result["cached_at"],
                    },
                )
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                {
                                    "query_id": query_id,
                                    "result": cached_result["result"],
                                    "cached": True,
                                    "cached_at": cached_result["cached_at"],
                                    "statistics": cached_result["metadata"],
                                },
                                indent=2,
                                cls=CustomJSONEncoder,
                            ),
                        }
                    ],
                    "isError": False,
                }

        # Proceed with normal query execution
        await event_manager.broadcast(
            "queries",
            "query_start",
            {
                "query_id": query_id,
                "sql": sql,
                "maximum_bytes_billed": maximum_bytes_billed,
                "tables_accessed": tables_accessed,
            },
        )

        # Security check
        sql_upper = sql.upper()
        forbidden_keywords = ["INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER"]
        if any(keyword in sql_upper.split() for keyword in forbidden_keywords):
            if knowledge_base is not None:
                await knowledge_base.save_query_pattern(
                    sql, {}, tables_accessed, False, "Only READ operations are allowed.", user_id
                )
            return {"error": "Only READ operations are allowed."}, 400

        # Execute query
        job_config = bigquery.QueryJobConfig(maximum_bytes_billed=maximum_bytes_billed)
        query_job = bigquery_client.query(sql, job_config=job_config)

        try:
            results = query_job.result()
            rows = [dict(row.items()) for row in results]

            # Prepare statistics
            statistics = {
                "totalBytesProcessed": query_job.total_bytes_processed,
                "totalRows": getattr(query_job, "total_rows", None),
                "duration_ms": (
                    (query_job.ended - query_job.started).total_seconds() * 1000
                    if query_job.ended and query_job.started
                    else None
                ),
                "started": query_job.started.isoformat() if query_job.started else None,
                "ended": query_job.ended.isoformat() if query_job.ended else None,
            }

            # Cache the result if caching is enabled and knowledge_base is provided
            if use_cache and knowledge_base is not None and len(rows) > 0:
                await knowledge_base.cache_query_result(
                    sql, rows, statistics, tables_accessed
                )

            # Save query pattern for analysis
            if knowledge_base is not None:
                await knowledge_base.save_query_pattern(
                    sql, statistics, tables_accessed, True, user_id=user_id
                )

            await event_manager.broadcast(
                "queries",
                "query_complete",
                {
                    "query_id": query_id,
                    "job_id": query_job.job_id,
                    "statistics": statistics,
                },
            )

            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "query_id": query_id,
                                "result": rows,
                                "cached": False,
                                "statistics": statistics,
                            },
                            indent=2,
                            cls=CustomJSONEncoder,
                        ),
                    }
                ],
                "isError": False,
            }

        except Exception as e:
            # Save failed query pattern
            if knowledge_base is not None:
                await knowledge_base.save_query_pattern(
                    sql, {}, tables_accessed, False, str(e), user_id
                )

            await event_manager.broadcast(
                "queries",
                "query_error",
                {
                    "query_id": query_id,
                    "job_id": query_job.job_id if query_job else None,
                    "error": str(e),
                },
            )
            raise

    except GoogleAPIError as e:
        return {"error": f"BigQuery API error: {str(e)}"}, 500
    except Exception as e:
        print(f"Exception in enhanced query handler: {type(e).__name__}: {str(e)}")
        return {"error": f"Unexpected error: {str(e)}"}, 500


async def get_datasets_handler(bigquery_client) -> Union[Dict[str, Any], Tuple[Dict[str, Any], int]]:
    """Retrieve the list of all datasets in the current project."""
    try:
        datasets = list(bigquery_client.list_datasets())
        dataset_list = [{"dataset_id": dataset.dataset_id} for dataset in datasets]
        return {"datasets": dataset_list}
    except GoogleAPIError as e:
        return {"error": f"BigQuery API error: {str(e)}"}, 500
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}, 500


async def get_tables_handler(bigquery_client, dataset_id: str) -> Union[Dict[str, Any], Tuple[Dict[str, Any], int]]:
    """Retrieve all tables within a specific dataset."""
    try:
        tables = list(bigquery_client.list_tables(dataset_id))
        table_list = [{"table_id": table.table_id} for table in tables]
        return {"tables": table_list}
    except GoogleAPIError as e:
        return {"error": f"BigQuery API error: {str(e)}"}, 500
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}, 500


async def get_table_schema_handler(
    bigquery_client, dataset_id: str, table_id: str
) -> Union[Dict[str, Any], Tuple[Dict[str, Any], int]]:
    """Retrieve schema details for a specific table."""
    try:
        table_ref = bigquery_client.dataset(dataset_id).table(table_id)
        table = bigquery_client.get_table(table_ref)
        schema = [
            {"name": field.name, "type": field.field_type, "mode": field.mode}
            for field in table.schema
        ]
        return {"schema": schema}
    except GoogleAPIError as e:
        return {"error": f"BigQuery API error: {str(e)}"}, 500
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}, 500