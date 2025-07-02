from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import json

@dataclass
class ColumnField:
    name: str
    type: str
    mode: str
    description: Optional[str] = None
    # Additional fields from column_documentation
    business_rules: Optional[List[str]] = field(default_factory=list)
    sample_values: Optional[Dict[str, Any]] = field(default_factory=dict)
    data_quality_notes: Optional[str] = None
    updated_by: Optional[str] = None
    updated_at: Optional[str] = None

@dataclass
class TableInfo:
    project_id: str
    dataset_id: str
    table_id: str
    full_name: str
    description: Optional[str] = None
    created: Optional[str] = None
    modified: Optional[str] = None
    num_rows: Optional[int] = None
    size_bytes: Optional[int] = None
    table_type: Optional[str] = None

@dataclass
class SchemaSnapshot:
    schema_version: int
    schema_data: List[Dict[str, Any]]
    created_at: str
    row_count: Optional[int] = None
    size_bytes: Optional[int] = None

@dataclass
class TableSchema:
    table_info: TableInfo
    schema: List[ColumnField]
    schema_history: List[SchemaSnapshot] = field(default_factory=list)
    usage_patterns: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mcp_explain_table_response(cls, response: Dict[str, Any]):
        """Converts a raw MCP server explain_table response into a TableSchema object."""
        content = response.get("content", [{}])
        is_error = response.get("isError", False)

        if is_error:
            # Handle error case, perhaps return a simplified error object or raise
            raise ValueError(f"Error in MCP explain_table response: {content[0].get('text', 'Unknown error')}")

        try:
            # The actual result is usually a JSON string inside the 'text' field of the first content item
            result_data = json.loads(content[0].get("text", "{}"))
        except (json.JSONDecodeError, IndexError):
            result_data = {}

        table_info_data = result_data.get("table_info", {})
        table_info = TableInfo(**table_info_data)

        schema_data = result_data.get("schema", [])
        schema = []
        for col_data in schema_data:
            # Ensure all expected fields are present, even if None
            col_field = ColumnField(
                name=col_data.get("name"),
                type=col_data.get("type"),
                mode=col_data.get("mode"),
                description=col_data.get("description"),
                business_rules=col_data.get("business_rules", []),
                sample_values=col_data.get("sample_values", {}),
                data_quality_notes=col_data.get("data_quality_notes"),
                updated_by=col_data.get("updated_by"),
                updated_at=col_data.get("updated_at"),
            )
            schema.append(col_field)

        schema_history_data = result_data.get("schema_history", [])
        schema_history = [SchemaSnapshot(**s) for s in schema_history_data]

        usage_patterns = result_data.get("usage_patterns", {})

        return cls(
            table_info=table_info,
            schema=schema,
            schema_history=schema_history,
            usage_patterns=usage_patterns
        )

    @classmethod
    def from_mcp_get_table_schema_response(cls, response: Dict[str, Any], dataset_id: str, table_id: str):
        """Converts a raw MCP server get_table_schema response into a TableSchema object (simplified)."""
        # This response is simpler, just a list of schema fields
        schema_data = response.get("schema", [])
        schema = []
        for col_data in schema_data:
            schema.append(ColumnField(
                name=col_data.get("name"),
                type=col_data.get("type"),
                mode=col_data.get("mode"),
                description=None # get_table_schema doesn't provide this
            ))
        
        # Create dummy TableInfo for this simpler response
        table_info = TableInfo(
            project_id="unknown", # Not provided by get_table_schema
            dataset_id=dataset_id,
            table_id=table_id,
            full_name=f"{dataset_id}.{table_id}"
        )

        return cls(
            table_info=table_info,
            schema=schema,
            schema_history=[],
            usage_patterns={}
        )
