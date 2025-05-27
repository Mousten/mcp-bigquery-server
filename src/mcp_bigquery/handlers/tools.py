"""Tool handlers for BigQuery operations."""
import json
import uuid
from typing import Dict, Any, Tuple, Union, List
from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPIError
from ..core.json_encoder import CustomJSONEncoder


async def query_tool_handler(
    bigquery_client, event_manager, sql: str, maximum_bytes_billed: int = 1000000000
) -> Union[Dict[str, Any], Tuple[Dict[str, Any], int]]:
    """Execute a read-only SQL query on BigQuery."""
    try:
        # Generate a query ID for tracking
        query_id = str(uuid.uuid4())

        # Broadcast query_start event
        await event_manager.broadcast(
            "queries",
            "query_start",
            {
                "query_id": query_id,
                "sql": sql,
                "maximum_bytes_billed": maximum_bytes_billed,
            },
        )

        # Ensure the query is read-only
        sql_upper = sql.upper()
        forbidden_keywords = ["INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER"]
        if any(keyword in sql_upper.split() for keyword in forbidden_keywords):
            await event_manager.broadcast(
                "queries",
                "query_error",
                {"query_id": query_id, "error": "Only READ operations are allowed."},
            )
            return {"error": "Only READ operations are allowed."}, 400

        # Configure and run the query
        job_config = bigquery.QueryJobConfig(maximum_bytes_billed=maximum_bytes_billed)

        # Execute query
        query_job = bigquery_client.query(sql, job_config=job_config)

        # Broadcast query_job_created event
        await event_manager.broadcast(
            "queries",
            "query_job_created",
            {
                "query_id": query_id,
                "job_id": query_job.job_id,
                "location": query_job.location,
            },
        )

        # Wait for results
        try:
            results = query_job.result()

            # Format results as list of dictionaries
            rows = [dict(row.items()) for row in results]

            # Broadcast query_complete event
            await event_manager.broadcast(
                "queries",
                "query_complete",
                {
                    "query_id": query_id,
                    "job_id": query_job.job_id,
                    "total_bytes_processed": query_job.total_bytes_processed,
                    "total_rows": (
                        query_job.total_rows
                        if hasattr(query_job, "total_rows")
                        else None
                    ),
                    "duration_ms": (
                        (query_job.ended - query_job.started).total_seconds() * 1000
                        if query_job.ended and query_job.started
                        else None
                    ),
                },
            )

            # Return properly formatted MCP response
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "query_id": query_id,
                                "result": rows,
                                "statistics": {
                                    "totalBytesProcessed": query_job.total_bytes_processed,
                                    "totalRows": (
                                        query_job.total_rows
                                        if hasattr(query_job, "total_rows")
                                        else None
                                    ),
                                    "started": (
                                        query_job.started.isoformat()
                                        if query_job.started
                                        else None
                                    ),
                                    "ended": (
                                        query_job.ended.isoformat()
                                        if query_job.ended
                                        else None
                                    ),
                                },
                            },
                            indent=2,
                            cls=CustomJSONEncoder,
                        ),
                    }
                ],
                "isError": False,
            }
        except Exception as e:
            # Broadcast query_error event
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
        print(f"Exception in query handler: {type(e).__name__}: {str(e)}")
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