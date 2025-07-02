from typing import Dict, Any
import requests
import json

from ai_agent.tool_interface.mcp_tools import MCPTools
from ai_agent.utils.error_handler import handle_mcp_error
from ai_agent.agent_core.system_message import SYSTEM_MESSAGE
from ai_agent.data_models.query_result import QueryResult # Import QueryResult

class AgentBrain:
    def __init__(self, mcp_client: MCPTools):
        self.mcp_client = mcp_client
        self.system_message = SYSTEM_MESSAGE

    async def process_request(self, user_request: str, user_id: str = "anonymous", session_id: str = "default_session") -> str:
        """Processes a user request and returns a response."""
        print(f"\nAgentBrain received request: {user_request}")
        print(f"Using system message (excerpt):\n{self.system_message[:200]}...")

        # --- Initial hardcoded query for demonstration ---
        # In a real scenario, an LLM would generate this SQL based on user_request
        # and schema knowledge.
        sql_query = "SELECT 1 as test_column, 'hello' as message;"
        print(f"Generated SQL query (hardcoded for now):\n{sql_query}")

        try:
            print("Executing BigQuery SQL via MCP server...")
            raw_response = self.mcp_client.execute_bigquery_sql(
                sql=sql_query,
                user_id=user_id,
                session_id=session_id,
                # Applying a guideline: Add LIMIT clauses to exploratory queries
                # For this simple query, it's not strictly necessary but demonstrates the principle.
                maximum_bytes_billed=10000000 # 10MB limit for safety
            )
            
            query_result = QueryResult.from_mcp_response(raw_response)

            if query_result.is_error:
                return f"Error executing query: {query_result.error}"
            
            print(f"Query execution successful. Raw result:\n{json.dumps(query_result.result, indent=2)}")

            # --- Apply Response Formatting Guidelines ---
            formatted_response = f"Here is the result of your query:\n\n```sql\n{sql_query}\n```\n\n```json\n{json.dumps(query_result.result, indent=2)}\n```\n\nKey Insights: The query successfully returned a single row with a test number and a greeting message."

            return formatted_response

        except requests.exceptions.RequestException as e:
            user_friendly_error = handle_mcp_error(e)
            return f"An error occurred while processing your request: {user_friendly_error}"
        except Exception as e:
            return f"An unexpected error occurred: {e}"