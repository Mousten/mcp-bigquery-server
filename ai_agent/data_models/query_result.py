from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import json

@dataclass
class QueryStatistics:
    totalBytesProcessed: Optional[int] = None
    totalRows: Optional[int] = None
    duration_ms: Optional[float] = None
    started: Optional[str] = None
    ended: Optional[str] = None

@dataclass
class QueryResult:
    query_id: str
    result: List[Dict[str, Any]]
    cached: bool
    statistics: QueryStatistics = field(default_factory=QueryStatistics)
    cached_at: Optional[str] = None
    error: Optional[str] = None
    is_error: bool = False

    @classmethod
    def from_mcp_response(cls, response: Dict[str, Any]):
        """Converts a raw MCP server response into a QueryResult object."""
        content = response.get("content", [{}])
        is_error = response.get("isError", False)

        if is_error:
            error_text = content[0].get("text", "Unknown error from MCP server")
            return cls(query_id="", result=[], cached=False, is_error=True, error=error_text)

        try:
            # The actual result is usually a JSON string inside the 'text' field of the first content item
            result_data = json.loads(content[0].get("text", "{}"))
        except (json.JSONDecodeError, IndexError):
            result_data = {}

        query_id = result_data.get("query_id", "")
        result_rows = result_data.get("result", [])
        cached = result_data.get("cached", False)
        cached_at = result_data.get("cached_at")
        
        stats_data = result_data.get("statistics", {})
        statistics = QueryStatistics(**stats_data)

        return cls(
            query_id=query_id,
            result=result_rows,
            cached=cached,
            statistics=statistics,
            cached_at=cached_at,
            is_error=is_error
        )
