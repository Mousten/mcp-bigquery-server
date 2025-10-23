#!/usr/bin/env python3
"""Diagnostic script to check MCP server connectivity and configuration."""
import sys
import os
import json
from pathlib import Path

# Add paths
sys.path.insert(0, 'src')
sys.path.insert(0, 'ai_agent')


def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f" {text}")
    print("=" * 70)


def check_environment():
    """Check if required environment variables are set."""
    print_header("Checking Environment Variables")

    required_vars = ["PROJECT_ID"]
    optional_vars = ["LOCATION", "KEY_FILE", "SUPABASE_URL", "SUPABASE_KEY"]
    streamlit_vars = ["OPENAI_API_KEY", "MCP_BIGQUERY_BASE_URL"]

    print("\nRequired for MCP Server:")
    print("-" * 70)
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask the value for security
            masked = value[:8] + "..." if len(value) > 8 else "***"
            print(f"✓ {var:20s} = {masked}")
        else:
            print(f"✗ {var:20s} = NOT SET (REQUIRED!)")

    print("\nOptional for MCP Server:")
    print("-" * 70)
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            masked = value[:8] + "..." if len(value) > 8 else "***"
            print(f"✓ {var:20s} = {masked}")
        else:
            print(f"  {var:20s} = not set (using defaults)")

    print("\nRequired for Streamlit App:")
    print("-" * 70)
    for var in streamlit_vars:
        value = os.getenv(var)
        if value:
            masked = value[:8] + "..." if len(value) > 8 else "***"
            print(f"✓ {var:20s} = {masked}")
        else:
            default_msg = " (default: http://localhost:8005)" if var == "MCP_BIGQUERY_BASE_URL" else " (REQUIRED!)"
            print(f"{'✗' if 'KEY' in var else ' '} {var:20s} = not set{default_msg}")

    # Check if PROJECT_ID is set
    if not os.getenv("PROJECT_ID"):
        print("\n⚠️  WARNING: PROJECT_ID is not set!")
        print("   The MCP server will fail to start without this.")
        return False

    return True


def check_credentials():
    """Check BigQuery credentials."""
    print_header("Checking BigQuery Credentials")

    key_file = os.getenv("KEY_FILE")

    if key_file:
        print(f"\nUsing service account key file: {key_file}")
        if os.path.exists(key_file):
            print("✓ Key file exists")
            try:
                with open(key_file, 'r') as f:
                    key_data = json.load(f)
                if key_data.get("type") == "service_account":
                    print("✓ Valid service account key format")
                    print(f"  Project ID: {key_data.get('project_id', 'N/A')}")
                    print(f"  Client Email: {key_data.get('client_email', 'N/A')[:30]}...")
                else:
                    print("✗ Invalid key file format")
                    return False
            except Exception as e:
                print(f"✗ Error reading key file: {e}")
                return False
        else:
            print("✗ Key file does not exist at specified path")
            return False
    else:
        print("\nNo KEY_FILE specified - will use Application Default Credentials")
        print("  Make sure you've run: gcloud auth application-default login")

    return True


def check_server_running():
    """Check if MCP server is running."""
    print_header("Checking MCP Server")

    try:
        import requests
        base_url = os.getenv("MCP_BIGQUERY_BASE_URL", "http://localhost:8005")

        print(f"\nAttempting to connect to: {base_url}")

        # Try health check
        try:
            response = requests.get(f"{base_url}/health", timeout=5)
            if response.status_code == 200:
                print("✓ Server is running!")
                print(f"  Health check response: {response.json()}")
                return True
            else:
                print(f"✗ Server responded with status {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print("✗ Cannot connect to server")
            print("\n  Possible reasons:")
            print("  1. Server is not running")
            print("  2. Server is running on a different port")
            print("  3. Firewall is blocking the connection")
            print("\n  To start the server, run:")
            print("     mcp-bigquery --transport http --host 0.0.0.0 --port 8005")
            return False
        except Exception as e:
            print(f"✗ Error connecting to server: {e}")
            return False
    except ImportError:
        print("✗ 'requests' library not installed")
        print("  Run: pip install requests")
        return False


def check_server_endpoints():
    """Check if server endpoints are accessible."""
    print_header("Checking Server Endpoints")

    try:
        import requests
        base_url = os.getenv("MCP_BIGQUERY_BASE_URL", "http://localhost:8005")

        endpoints = [
            ("GET", "/health", "Health check"),
            ("GET", "/resources/list", "List datasets"),
            ("POST", "/tools/execute_bigquery_sql", "Execute query"),
            ("POST", "/tools/get_tables", "Get tables"),
            ("POST", "/tools/get_table_schema", "Get schema"),
        ]

        print("\nTesting endpoints:")
        print("-" * 70)

        all_ok = True
        for method, path, description in endpoints:
            full_url = f"{base_url}{path}"
            try:
                if method == "GET":
                    response = requests.get(full_url, timeout=5)
                else:
                    # Send minimal test payload
                    test_payload = {}
                    if "execute_bigquery_sql" in path:
                        test_payload = {"sql": "SELECT 1"}
                    elif "get_tables" in path:
                        test_payload = {"dataset_id": "test"}
                    elif "get_table_schema" in path:
                        test_payload = {"dataset_id": "test", "table_id": "test"}

                    response = requests.post(full_url, json=test_payload, timeout=5)

                # We expect some endpoints to fail with validation errors,
                # but they should return HTTP 400/422, not 404
                if response.status_code in [200, 400, 422, 500]:
                    print(f"✓ {method:4s} {path:35s} ({description})")
                elif response.status_code == 404:
                    print(f"✗ {method:4s} {path:35s} ({description}) - NOT FOUND")
                    all_ok = False
                else:
                    print(f"? {method:4s} {path:35s} ({description}) - Status {response.status_code}")
            except requests.exceptions.ConnectionError:
                print(f"✗ {method:4s} {path:35s} ({description}) - CONNECTION FAILED")
                all_ok = False
            except Exception as e:
                print(f"✗ {method:4s} {path:35s} ({description}) - {e}")
                all_ok = False

        return all_ok
    except ImportError:
        print("✗ 'requests' library not installed")
        return False


def test_mcp_tools_client():
    """Test the MCPTools client."""
    print_header("Testing MCPTools Client")

    try:
        from ai_agent.tool_interface.mcp_tools import MCPTools

        base_url = os.getenv("MCP_BIGQUERY_BASE_URL", "http://localhost:8005")
        client = MCPTools(base_url=base_url)

        print(f"\n✓ MCPTools client created with base_url: {base_url}")

        # Try to get datasets
        print("\nTrying to fetch datasets...")
        try:
            response = client.get_datasets()
            if "error" in response:
                print(f"✗ Error from server: {response['error']}")
                return False
            elif "datasets" in response:
                datasets = response.get("datasets", [])
                print(f"✓ Successfully fetched {len(datasets)} dataset(s)")
                if datasets:
                    print("\n  Available datasets:")
                    for ds in datasets[:5]:  # Show first 5
                        dataset_id = ds.get("dataset_id", "unknown")
                        print(f"    - {dataset_id}")
                    if len(datasets) > 5:
                        print(f"    ... and {len(datasets) - 5} more")
                else:
                    print("  (No datasets found - check your BigQuery project)")
                return True
            else:
                print(f"✗ Unexpected response format: {response}")
                return False
        except Exception as e:
            print(f"✗ Error calling get_datasets(): {e}")
            return False
    except ImportError as e:
        print(f"✗ Cannot import MCPTools: {e}")
        return False


def print_setup_guide():
    """Print setup instructions."""
    print_header("Setup Guide")

    print("""
To get the Streamlit app working with the MCP server:

1. Set up environment variables:

   For Windows (PowerShell):
   $env:PROJECT_ID="your-bigquery-project-id"
   $env:OPENAI_API_KEY="sk-your-openai-key"

   For Linux/Mac (Bash):
   export PROJECT_ID="your-bigquery-project-id"
   export OPENAI_API_KEY="sk-your-openai-key"

   Or create a .env file in the project root:
   PROJECT_ID=your-bigquery-project-id
   LOCATION=US
   KEY_FILE=path/to/service-account-key.json
   OPENAI_API_KEY=sk-your-openai-key
   MCP_BIGQUERY_BASE_URL=http://localhost:8005

2. Start the MCP server:

   mcp-bigquery --transport http --host 0.0.0.0 --port 8005

   You should see:
   "Starting server in HTTP mode on 0.0.0.0:8005..."

3. In a separate terminal, start the Streamlit app:

   streamlit run streamlit_app/app.py

   The app should open in your browser at http://localhost:8501

4. Verify the connection:

   - Check the Streamlit sidebar
   - You should see available datasets listed
   - If you see "No datasets available or the MCP server is unreachable",
     run this diagnostic script again

Common Issues:

• "No datasets available" → MCP server not running or wrong URL
• "Failed to load datasets: Connection refused" → Server not started
• "Configuration error: PROJECT_ID" → Environment variable not set
• "Invalid service account key" → Wrong path or corrupted key file
""")


def main():
    """Run all diagnostic checks."""
    print("\n" + "=" * 70)
    print(" MCP BigQuery Server Diagnostic Tool")
    print("=" * 70)

    checks = [
        ("Environment Variables", check_environment),
        ("BigQuery Credentials", check_credentials),
        ("MCP Server Running", check_server_running),
    ]

    results = []
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"\n✗ Check '{check_name}' failed with error: {e}")
            results.append((check_name, False))

    # Only check endpoints if server is running
    if results[2][1]:  # Server running check passed
        try:
            endpoint_result = check_server_endpoints()
            results.append(("Server Endpoints", endpoint_result))
        except Exception as e:
            print(f"\n✗ Endpoint check failed: {e}")
            results.append(("Server Endpoints", False))

        try:
            client_result = test_mcp_tools_client()
            results.append(("MCPTools Client", client_result))
        except Exception as e:
            print(f"\n✗ Client test failed: {e}")
            results.append(("MCPTools Client", False))

    # Print summary
    print_header("Diagnostic Summary")

    print("\nResults:")
    print("-" * 70)
    for check_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8s} {check_name}")

    all_passed = all(r[1] for r in results)

    if all_passed:
        print("\n✓ All checks passed!")
        print("\nThe MCP server is running and accessible.")
        print("You should be able to use the Streamlit app now.")
    else:
        print("\n✗ Some checks failed.")
        print("\nPlease review the errors above and follow the setup guide below.")
        print_setup_guide()

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
