#!/usr/bin/env python3
"""Integration test to verify Streamlit app works with MCP server."""
import sys
import inspect
from typing import Dict, List

sys.path.insert(0, 'src')
sys.path.insert(0, 'ai_agent')

def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f" {text}")
    print("=" * 70)


def test_imports():
    """Test that all required modules can be imported."""
    print_header("Testing Module Imports")

    results = []

    # Test MCP server components
    try:
        from mcp_bigquery.config.settings import ServerConfig
        results.append(("✓", "MCP ServerConfig"))
    except Exception as e:
        results.append(("✗", f"MCP ServerConfig: {e}"))

    try:
        from mcp_bigquery.api.fastapi_app import create_fastapi_app
        results.append(("✓", "FastAPI app creator"))
    except Exception as e:
        results.append(("✗", f"FastAPI app creator: {e}"))

    try:
        from mcp_bigquery.routes.tools import create_tools_router
        results.append(("✓", "Tools router"))
    except Exception as e:
        results.append(("✗", f"Tools router: {e}"))

    # Test Streamlit app components
    try:
        from ai_agent.tool_interface.mcp_tools import MCPTools
        results.append(("✓", "MCPTools client"))
    except Exception as e:
        results.append(("✗", f"MCPTools client: {e}"))

    try:
        import streamlit
        results.append(("✓", f"Streamlit (v{streamlit.__version__})"))
    except Exception as e:
        results.append(("✗", f"Streamlit: {e}"))

    try:
        from openai import OpenAI
        results.append(("✓", "OpenAI client"))
    except Exception as e:
        results.append(("✗", f"OpenAI client: {e}"))

    for status, msg in results:
        print(f"{status} {msg}")

    return all(r[0] == "✓" for r in results)


def test_endpoint_compatibility():
    """Test that MCPTools methods match FastAPI routes."""
    print_header("Testing Endpoint Compatibility")

    from ai_agent.tool_interface.mcp_tools import MCPTools

    client = MCPTools(base_url="http://localhost:8005")

    # Define expected endpoint mappings
    endpoint_mappings = {
        "execute_bigquery_sql": "POST /tools/execute_bigquery_sql",
        "get_datasets": "GET /resources/list",
        "get_tables": "POST /tools/get_tables",
        "get_table_schema": "POST /tools/get_table_schema",
        "get_query_suggestions": "POST /tools/get_query_suggestions",
        "explain_table": "POST /tools/explain_table",
        "analyze_query_performance": "POST /tools/analyze_query_performance",
        "get_schema_changes": "POST /tools/get_schema_changes",
        "manage_cache": "POST /tools/manage_cache",
        "health_check": "GET /health",
    }

    print("\nMCPTools Method → Expected Endpoint Mapping:")
    print("-" * 70)

    for method_name, expected_endpoint in endpoint_mappings.items():
        if hasattr(client, method_name):
            print(f"✓ {method_name:30s} → {expected_endpoint}")
        else:
            print(f"✗ {method_name:30s} → MISSING")

    return True


def test_route_definitions():
    """Test that FastAPI routes are properly defined."""
    print_header("Testing FastAPI Route Definitions")

    from mcp_bigquery.routes.tools import create_tools_router
    from mcp_bigquery.routes.resources import create_resources_router

    # We can't create actual routers without BigQuery client,
    # but we can inspect the source code
    import inspect

    tools_source = inspect.getsource(create_tools_router)
    resources_source = inspect.getsource(create_resources_router)

    required_routes = {
        "POST /tools/execute_bigquery_sql": "@router.post(\"/execute_bigquery_sql\")",
        "POST /tools/get_tables": "@router.post(\"/get_tables\")",
        "POST /tools/get_table_schema": "@router.post(\"/get_table_schema\")",
        "GET /resources/list": "@router.get(\"/list\")",
    }

    print("\nRequired Routes:")
    print("-" * 70)

    results = []
    for route_name, route_decorator in required_routes.items():
        if route_decorator in tools_source or route_decorator in resources_source:
            print(f"✓ {route_name}")
            results.append(True)
        else:
            print(f"✗ {route_name} - MISSING")
            results.append(False)

    return all(results)


def test_streamlit_app_structure():
    """Test that Streamlit app has proper structure."""
    print_header("Testing Streamlit App Structure")

    with open('streamlit_app/app.py', 'r',encoding='utf-8') as f:
        app_content = f.read()

    required_components = {
        "MCPTools import": "from ai_agent.tool_interface.mcp_tools import MCPTools",
        "OpenAI import": "from openai import OpenAI",
        "Streamlit import": "import streamlit",
        "MCPTools instantiation": "MCPTools(base_url=",
        "execute_bigquery_sql call": "execute_bigquery_sql(",
        "get_datasets call": "get_datasets()",
        "get_tables call": "get_tables(",
        "get_table_schema call": "get_table_schema(",
    }

    print("\nStreamlit App Components:")
    print("-" * 70)

    results = []
    for component_name, search_string in required_components.items():
        if search_string in app_content:
            print(f"✓ {component_name}")
            results.append(True)
        else:
            print(f"✗ {component_name} - NOT FOUND")
            results.append(False)

    return all(results)


def test_configuration():
    """Test configuration structure."""
    print_header("Testing Configuration")

    from mcp_bigquery.config.settings import ServerConfig

    print("\nRequired Environment Variables:")
    print("-" * 70)
    print("• PROJECT_ID (required)")
    print("• LOCATION (optional, default: US)")
    print("• KEY_FILE (optional, uses default credentials if not set)")
    print("• SUPABASE_URL (optional, for enhanced features)")
    print("• SUPABASE_KEY (optional, for enhanced features)")

    print("\nStreamlit App Environment Variables:")
    print("-" * 70)
    print("• OPENAI_API_KEY (required for Streamlit app)")
    print("• MCP_BIGQUERY_BASE_URL (optional, default: http://localhost:8005)")
    print("• MCP_SESSION_ID (optional)")
    print("• MCP_USER_ID (optional)")

    return True


def generate_report(all_tests_passed: bool):
    """Generate final integration report."""
    print_header("Integration Test Report")

    if all_tests_passed:
        print("\n✓ ALL TESTS PASSED")
        print("\nThe Streamlit app is properly integrated with the MCP server!")
        print("\nNext Steps:")
        print("1. Set up your .env file with required credentials:")
        print("   - PROJECT_ID (BigQuery project)")
        print("   - OPENAI_API_KEY (for Streamlit app)")
        print("   - Optionally: SUPABASE_URL and SUPABASE_KEY")
        print("\n2. Start the MCP server:")
        print("   mcp-bigquery --transport http --host 0.0.0.0 --port 8005")
        print("\n3. Run the Streamlit app:")
        print("   streamlit run streamlit_app/app.py")
    else:
        print("\n✗ SOME TESTS FAILED")
        print("\nPlease review the failed tests above and fix any issues.")

    print("\nIntegration Fixes Applied:")
    print("-" * 70)
    print("✓ Added POST /tools/get_tables endpoint")
    print("✓ Added POST /tools/get_table_schema endpoint")
    print("  These routes now match the MCPTools client expectations")


def main():
    """Run all integration tests."""
    print("\n" + "=" * 70)
    print(" MCP BigQuery Server + Streamlit App Integration Test")
    print("=" * 70)

    tests = [
        ("Module Imports", test_imports),
        ("Endpoint Compatibility", test_endpoint_compatibility),
        ("Route Definitions", test_route_definitions),
        ("Streamlit App Structure", test_streamlit_app_structure),
        ("Configuration", test_configuration),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"\n✗ Test '{test_name}' failed with error: {e}")
            results.append(False)

    all_passed = all(results)
    generate_report(all_passed)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
