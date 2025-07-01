import requests
import json

def handle_mcp_error(e: requests.exceptions.RequestException) -> str:
    """Handles errors from MCP server communication and provides user-friendly messages."""
    if isinstance(e, requests.exceptions.ConnectionError):
        return (
            "Could not connect to the MCP BigQuery server. "
            "Please ensure the server is running and accessible at the configured address."
        )
    elif isinstance(e, requests.exceptions.Timeout):
        return "The request to the MCP BigQuery server timed out. The server might be overloaded or unreachable."
    elif isinstance(e, requests.exceptions.HTTPError):
        status_code = e.response.status_code
        if status_code == 400:
            try:
                error_details = e.response.json()
                if "error" in error_details:
                    return f"MCP Server Error (400 Bad Request): {error_details['error']}"
                return f"MCP Server Error (400 Bad Request): {e.response.text}"
            except json.JSONDecodeError:
                return f"MCP Server Error (400 Bad Request): {e.response.text}"
        elif status_code == 404:
            return (
                f"MCP Server Error (404 Not Found): The requested endpoint was not found. "
                f"Please check the server's API documentation and the client's endpoint configuration. "
                f"URL: {e.response.url}"
            )
        elif status_code == 500:
            return "MCP Server Error (500 Internal Server Error): An unexpected error occurred on the server."
        else:
            return f"MCP Server Error ({status_code} {e.response.reason}): {e.response.text}"
    else:
        return f"An unexpected error occurred while communicating with the MCP server: {e}"
