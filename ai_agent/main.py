import sys
import os
import asyncio
import requests

# Add the parent directory to the Python path to allow imports from ai_agent
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai_agent.tool_interface.mcp_tools import MCPTools
from ai_agent.agent_core.agent_brain import AgentBrain
from ai_agent.utils.error_handler import handle_mcp_error
from ai_agent.data_models.preference_models import UserPreferences # Import UserPreferences

async def main_async():
    print("Initializing MCPTools client...")
    # Ensure this base_url matches the port your MCP server is running on
    mcp_client = MCPTools(base_url="http://localhost:8005")
    agent_brain = AgentBrain(mcp_client=mcp_client)

    print("\n--- Testing health_check() ---")
    try:
        health_status = mcp_client.health_check()
        print("Successfully retrieved health status:")
        print(health_status)
    except requests.exceptions.RequestException as e:
        print(f"Failed to get health status: {handle_mcp_error(e)}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    print("\n--- Testing get_datasets() ---")
    try:
        datasets = mcp_client.get_datasets()
        print("Successfully retrieved datasets:")
        print(datasets)
    except requests.exceptions.RequestException as e:
        print(f"Failed to get datasets: {handle_mcp_error(e)}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    print("\n--- Testing get_user_preferences() (with dummy session_id) ---")
    try:
        raw_user_prefs = mcp_client.get_user_preferences(session_id="test_session_123")
        # Convert raw response to UserPreferences object
        user_prefs = UserPreferences.from_mcp_response(raw_user_prefs, "test_session_123", is_user_id=False)
        print("Successfully retrieved user preferences:")
        print(user_prefs)
    except requests.exceptions.RequestException as e:
        print(f"Failed to get user preferences: {handle_mcp_error(e)}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    print("\n--- Testing set_user_preferences() (with dummy session_id) ---")
    try:
        new_prefs_data = {"theme": "dark", "default_limit": 500}
        set_result = mcp_client.set_user_preferences(preferences=new_prefs_data, session_id="test_session_123")
        print("Successfully set user preferences:")
        print(set_result)
    except requests.exceptions.RequestException as e:
        print(f"Failed to set user preferences: {handle_mcp_error(e)}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    print("\n--- Testing get_user_preferences() again to confirm set ---")
    try:
        raw_user_prefs_confirm = mcp_client.get_user_preferences(session_id="test_session_123")
        user_prefs_confirm = UserPreferences.from_mcp_response(raw_user_prefs_confirm, "test_session_123", is_user_id=False)
        print("Successfully retrieved user preferences after setting:")
        print(user_prefs_confirm)
    except requests.exceptions.RequestException as e:
        print(f"Failed to get user preferences: {handle_mcp_error(e)}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    print("\n--- Testing AgentBrain.process_request() ---")
    sample_request = "Show me some test data."
    try:
        agent_response = await agent_brain.process_request(sample_request, user_id="test_user_001")
        print("\nAgentBrain Response:")
        print(agent_response)
    except Exception as e:
        print(f"Error from AgentBrain: {e}")

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
