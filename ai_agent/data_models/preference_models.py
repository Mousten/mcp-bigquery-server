from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
import json

@dataclass
class QueryDefaults:
    maximum_bytes_billed: Optional[int] = None
    use_cache_aggressively: Optional[bool] = None
    # Add other query-related defaults here

@dataclass
class UserPreferences:
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    preferences: Dict[str, Any] = field(default_factory=dict)
    query_defaults: QueryDefaults = field(default_factory=QueryDefaults)
    favorite_queries: List[str] = field(default_factory=list) # Assuming list of query IDs or names

    @classmethod
    def from_mcp_response(cls, response: Dict[str, Any], identifier: str, is_user_id: bool):
        """Converts a raw MCP server get_user_preferences response into a UserPreferences object."""
        # The MCP response for get_user_preferences is directly the preferences dict
        # It might be wrapped in a 'preferences' key if the API changed.
        # Assuming the API returns {"preferences": {...}}
        
        raw_prefs = response.get("preferences", {})

        user_id = identifier if is_user_id else None
        session_id = identifier if not is_user_id else None

        query_defaults_data = raw_prefs.get("query_defaults", {})
        query_defaults = QueryDefaults(**query_defaults_data)

        return cls(
            user_id=user_id,
            session_id=session_id,
            preferences=raw_prefs.get("preferences", {}), # General preferences
            query_defaults=query_defaults,
            favorite_queries=raw_prefs.get("favorite_queries", [])
        )
