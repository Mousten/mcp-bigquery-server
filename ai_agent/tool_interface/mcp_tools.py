import json
from typing import Dict, Any, Optional, List

class MCPTools:
    def __init__(self, base_url: str = "http://localhost:8005"):
        self.base_url = base_url

    def _post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        import requests
        url = self.base_url + endpoint
        try:
            resp = requests.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Error communicating with MCP server at {url}: {e}")
            raise

    def _get(self, endpoint: str) -> Dict[str, Any]:
        import requests
        url = self.base_url + endpoint
        try:
            resp = requests.get(url)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            print(f"Error communicating with MCP server at {url}: {e}")
            raise

    # --- Core BigQuery Data Access Tools ---

    def execute_bigquery_sql(
        self,
        sql: str,
        maximum_bytes_billed: int = 100000000,
        use_cache: bool = True,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        payload = {
            "sql": sql,
            "maximum_bytes_billed": maximum_bytes_billed,
            "use_cache": use_cache,
            "force_refresh": force_refresh
        }
        if user_id:
            payload["user_id"] = user_id
        if session_id:
            payload["session_id"] = session_id
        return self._post("/tools/execute_bigquery_sql", payload)

    def get_datasets(self) -> Dict[str, Any]:
        # The MCP server's get_datasets is a GET request to /resources/list
        return self._get("/resources/list")

    def get_tables(self, dataset_id: str) -> Dict[str, Any]:
        # The MCP server's get_tables is a POST request
        return self._post("/tools/get_tables", {"dataset_id": dataset_id})

    def get_table_schema(
        self,
        dataset_id: str,
        table_id: str,
        include_documentation: bool = True,
        include_samples: bool = True
    ) -> Dict[str, Any]:
        # The MCP server's get_table_schema is a POST request
        payload = {
            "dataset_id": dataset_id,
            "table_id": table_id,
            "include_documentation": include_documentation,
            "include_samples": include_samples
        }
        return self._post("/tools/get_table_schema", payload)

    # --- Enhanced Intelligence & Analytics Tools ---

    def get_query_suggestions(
        self,
        tables_mentioned: Optional[List[str]] = None,
        query_context: Optional[str] = None,
        limit: int = 5,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        payload = {
            "limit": limit
        }
        if tables_mentioned:
            payload["tables_mentioned"] = tables_mentioned
        if query_context:
            payload["query_context"] = query_context
        if user_id:
            payload["user_id"] = user_id
        if session_id:
            payload["session_id"] = session_id
        return self._post("/tools/get_query_suggestions", payload)

    def explain_table(
        self,
        project_id: str,
        dataset_id: str,
        table_id: str,
        include_usage_stats: bool = True,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        payload = {
            "project_id": project_id,
            "dataset_id": dataset_id,
            "table_id": table_id,
            "include_usage_stats": include_usage_stats
        }
        if user_id:
            payload["user_id"] = user_id
        if session_id:
            payload["session_id"] = session_id
        return self._post("/tools/explain_table", payload)

    def analyze_query_performance(
        self,
        sql: Optional[str] = None,
        tables_accessed: Optional[List[str]] = None,
        time_range_hours: int = 168,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        include_recommendations: bool = True
    ) -> Dict[str, Any]:
        payload = {
            "time_range_hours": time_range_hours,
            "include_recommendations": include_recommendations
        }
        if sql:
            payload["sql"] = sql
        if tables_accessed:
            payload["tables_accessed"] = tables_accessed
        if user_id:
            payload["user_id"] = user_id
        if session_id:
            payload["session_id"] = session_id
        return self._post("/tools/analyze_query_performance", payload)

    def get_schema_changes(
        self,
        project_id: str,
        dataset_id: str,
        table_id: str,
        limit: int = 10,
        include_impact_analysis: bool = True,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        payload = {
            "project_id": project_id,
            "dataset_id": dataset_id,
            "table_id": table_id,
            "limit": limit,
            "include_impact_analysis": include_impact_analysis
        }
        if user_id:
            payload["user_id"] = user_id
        if session_id:
            payload["session_id"] = session_id
        return self._post("/tools/get_schema_changes", payload)

    # --- System & User Management Tools ---

    def manage_cache(
        self,
        action: str,
        target: Optional[str] = None,
        project_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
        table_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        payload = {
            "action": action
        }
        if target:
            payload["target"] = target
        if project_id:
            payload["project_id"] = project_id
        if dataset_id:
            payload["dataset_id"] = dataset_id
        if table_id:
            payload["table_id"] = table_id
        if user_id:
            payload["user_id"] = user_id
        if session_id:
            payload["session_id"] = session_id
        return self._post("/tools/manage_cache", payload)

    def health_check(self) -> Dict[str, Any]:
        return self._get("/health")

    def get_user_preferences(self, session_id=None, user_id=None) -> dict:
        payload = {}
        if session_id:
            payload["session_id"] = session_id
        if user_id:
            payload["user_id"] = user_id
        return self._post("/preferences/get", payload)

    def set_user_preferences(self, preferences, session_id=None, user_id=None) -> dict:
        payload = {"preferences": preferences}
        if session_id:
            payload["session_id"] = session_id
        if user_id:
            payload["user_id"] = user_id
        return self._post("/preferences/set", payload)
