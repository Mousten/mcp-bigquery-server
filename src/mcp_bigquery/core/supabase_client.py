"""Supabase client for caching and knowledge base functionality."""
import os
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from supabase import create_client, Client
from ..core.json_encoder import CustomJSONEncoder


class SupabaseKnowledgeBase:
    """Supabase-backed knowledge base and caching layer."""

    def __init__(self):
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables.")
        self.supabase: Client = create_client(
            str(supabase_url),
            str(supabase_key)
        )
    
    def _generate_query_hash(self, sql: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Generate a unique hash for a query."""
        query_string = sql.strip().lower()
        if params:
            query_string += json.dumps(params, sort_keys=True)
        return hashlib.sha256(query_string.encode()).hexdigest()
    
    async def get_cached_query(self, sql: str, max_age_hours: int = 24) -> Optional[Dict[str, Any]]:
        """Retrieve cached query result if available and not expired."""
        query_hash = self._generate_query_hash(sql)
        
        try:
            result = self.supabase.table("query_cache").select("*").eq(
                "query_hash", query_hash
            ).gte(
                "expires_at", datetime.now().isoformat()
            ).execute()
            
            if result.data:
                # Update hit count
                self.supabase.table("query_cache").update({
                    "hit_count": result.data[0]["hit_count"] + 1
                }).eq("id", result.data[0]["id"]).execute()
                
                return {
                    "cached": True,
                    "result": result.data[0]["result_data"],
                    "metadata": result.data[0]["metadata"],
                    "cached_at": result.data[0]["created_at"]
                }
        except Exception as e:
            print(f"Error retrieving cached query: {e}")
        
        return None
    
    async def cache_query_result(
        self, 
        sql: str, 
        result_data: List[Dict[str, Any]], 
        metadata: Dict[str, Any],
        tables_accessed: List[str],
        ttl_hours: int = 24
    ) -> bool:
        """Cache query result with metadata and table dependencies."""
        query_hash = self._generate_query_hash(sql)
        expires_at = datetime.now() + timedelta(hours=ttl_hours)
        
        try:
            # Insert cache entry
            cache_result = self.supabase.table("query_cache").insert({
                "query_hash": query_hash,
                "sql_query": sql,
                "result_data": result_data,
                "metadata": metadata,
                "expires_at": expires_at.isoformat()
            }).execute()
            
            if cache_result.data:
                cache_id = cache_result.data[0]["id"]
                
                # Insert table dependencies
                dependencies = []
                for table_path in tables_accessed:
                    parts = table_path.split(".")
                    if len(parts) >= 2:
                        dependencies.append({
                            "query_cache_id": cache_id,
                            "project_id": parts[0] if len(parts) == 3 else metadata.get("project_id"),
                            "dataset_id": parts[-2],
                            "table_id": parts[-1]
                        })
                
                if dependencies:
                    self.supabase.table("table_dependencies").insert(dependencies).execute()
                
                return True
                
        except Exception as e:
            print(f"Error caching query result: {e}")
        
        return False
    
    async def invalidate_cache_for_table(self, project_id: str, dataset_id: str, table_id: str):
        """Invalidate all cached queries that depend on a specific table."""
        try:
            # Find all cache entries that depend on this table
            deps_result = self.supabase.table("table_dependencies").select(
                "query_cache_id"
            ).eq("project_id", project_id).eq("dataset_id", dataset_id).eq("table_id", table_id).execute()
            
            if deps_result.data:
                cache_ids = [dep["query_cache_id"] for dep in deps_result.data]
                
                # Set expiration to now for these cache entries
                self.supabase.table("query_cache").update({
                    "expires_at": datetime.now().isoformat()
                }).in_("id", cache_ids).execute()
                
                print(f"Invalidated {len(cache_ids)} cached queries for {project_id}.{dataset_id}.{table_id}")
                
        except Exception as e:
            print(f"Error invalidating cache: {e}")
    
    async def track_schema_change(
        self, 
        project_id: str, 
        dataset_id: str, 
        table_id: str, 
        new_schema: List[Dict[str, Any]],
        metadata: Dict[str, Any]
    ) -> bool:
        """Track schema changes and automatically invalidate affected cache entries."""
        try:
            # Get current schema version
            current_result = self.supabase.table("schema_snapshots").select(
                "schema_version"
            ).eq("project_id", project_id).eq("dataset_id", dataset_id).eq("table_id", table_id).order(
                "schema_version", desc=True
            ).limit(1).execute()
            
            next_version = 1
            if current_result.data:
                next_version = current_result.data[0]["schema_version"] + 1
            
            # Insert new schema snapshot
            self.supabase.table("schema_snapshots").insert({
                "project_id": project_id,
                "dataset_id": dataset_id,
                "table_id": table_id,
                "schema_version": next_version,
                "schema_data": new_schema,
                "row_count": metadata.get("num_rows"),
                "size_bytes": metadata.get("num_bytes")
            }).execute()
            
            # Invalidate related cache entries
            await self.invalidate_cache_for_table(project_id, dataset_id, table_id)
            
            return True
            
        except Exception as e:
            print(f"Error tracking schema change: {e}")
            return False
    
    async def get_column_documentation(
        self, 
        project_id: str, 
        dataset_id: str, 
        table_id: str
    ) -> Dict[str, Dict[str, Any]]:
        """Get documentation for all columns in a table."""
        try:
            result = self.supabase.table("column_documentation").select("*").eq(
                "project_id", project_id
            ).eq("dataset_id", dataset_id).eq("table_id", table_id).execute()
            
            docs = {}
            for doc in result.data:
                docs[doc["column_name"]] = {
                    "description": doc["description"],
                    "business_rules": doc["business_rules"],
                    "sample_values": doc["sample_values"],
                    "data_quality_notes": doc["data_quality_notes"]
                }
            
            return docs
            
        except Exception as e:
            print(f"Error getting column documentation: {e}")
            return {}
    
    async def save_query_pattern(
        self, 
        sql: str, 
        execution_stats: Dict[str, Any], 
        tables_accessed: List[str],
        success: bool,
        error_message: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """Save query execution pattern for analysis."""
        try:
            self.supabase.table("query_history").insert({
                "user_id": user_id,
                "sql_query": sql,
                "execution_time_ms": execution_stats.get("duration_ms"),
                "bytes_processed": execution_stats.get("total_bytes_processed"),
                "success": success,
                "error_message": error_message,
                "tables_accessed": tables_accessed
            }).execute()
            
        except Exception as e:
            print(f"Error saving query pattern: {e}")
    
    async def get_query_suggestions(
        self, 
        tables_mentioned: List[str], 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Get query template suggestions based on tables mentioned."""
        try:
            # This would use more sophisticated matching in a real implementation
            result = self.supabase.table("query_templates").select("*").order(
                "usage_count", desc=True
            ).limit(limit).execute()
            
            suggestions = []
            for template in result.data:
                suggestions.append({
                    "name": template["name"],
                    "description": template["description"],
                    "template_sql": template["template_sql"],
                    "parameters": template["parameters"],
                    "usage_count": template["usage_count"]
                })
            
            return suggestions
            
        except Exception as e:
            print(f"Error getting query suggestions: {e}")
            return []