"""
Integration test for LLM provider invocation with real API calls.

This script tests actual LLM invocations to verify:
1. Each provider responds correctly
2. Response format matches expected schema
3. JSON parsing works correctly
4. Message formatting is correct for each SDK

IMPORTANT: This script requires valid API keys set as environment variables:
- OPENAI_API_KEY
- ANTHROPIC_API_KEY
- GEMINI_API_KEY
"""
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

from streamlit_app.app import (
    LLMProvider,
    LLMClientWrapper,
    initialise_llm_client,
    invoke_llm,
    parse_json_response,
    PROVIDER_MODEL_DEFAULTS,
)


def test_simple_json_question(provider: LLMProvider, api_key: str) -> bool:
    """Test a simple question that should return JSON with SQL."""
    print(f"\n{'='*70}")
    print(f"Testing {provider.value} with simple SQL generation")
    print('='*70)

    if not api_key:
        print(f"⚠️  No API key found for {provider.value}, skipping...")
        return None

    try:
        # Initialize client
        llm_client = initialise_llm_client(provider, api_key)
        if not llm_client:
            print(f"❌ Failed to initialize {provider.value} client")
            return False

        print(f"✅ {provider.value} client initialized")

        # Create a simple test question
        test_messages = [
            {
                "role": "system",
                "content": (
                    "You are a BigQuery SQL expert. "
                    "Generate a simple SQL query based on the user's question. "
                    "Respond ONLY with valid JSON in this exact format:\n"
                    '{"sql": "SELECT * FROM table LIMIT 10", "analysis_steps": ["Step 1", "Step 2"]}'
                ),
            },
            {
                "role": "user",
                "content": (
                    "Generate SQL to get the first 10 rows from the table "
                    "`ando-big-query.AndoSalesDataPrep.BoltOrderSales`. "
                    "Respond with JSON only."
                ),
            },
        ]

        print(f"📤 Sending request to {provider.value}...")

        # Invoke LLM
        response_text = invoke_llm(
            llm_client=llm_client,
            model=PROVIDER_MODEL_DEFAULTS[provider],
            messages=test_messages,
            temperature=0.1,
        )

        print(f"📥 Raw response from {provider.value}:")
        print(f"   {response_text[:200]}...")

        # Try to parse JSON
        try:
            response_json = parse_json_response(response_text)
            print(f"✅ JSON parsed successfully")
            print(f"   Keys: {list(response_json.keys())}")

            if "sql" in response_json:
                sql = response_json["sql"]
                print(f"✅ SQL field found: {sql[:100] if sql else 'NULL'}...")

                if sql:
                    print(f"✅ {provider.value} successfully generated SQL")
                    return True
                else:
                    print(f"❌ SQL field is null or empty")
                    print(f"   Full response: {json.dumps(response_json, indent=2)}")
                    return False
            else:
                print(f"❌ No 'sql' field in response")
                print(f"   Full response: {json.dumps(response_json, indent=2)}")
                return False

        except Exception as e:
            print(f"❌ Failed to parse JSON: {e}")
            print(f"   Raw response: {response_text}")
            return False

    except Exception as e:
        print(f"❌ {provider.value} test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_schema_question(provider: LLMProvider, api_key: str) -> bool:
    """Test the actual failing question: 'Show me the schema of...'"""
    print(f"\n{'='*70}")
    print(f"Testing {provider.value} with schema question (reproducing error)")
    print('='*70)

    if not api_key:
        print(f"⚠️  No API key found for {provider.value}, skipping...")
        return None

    try:
        # Initialize client
        llm_client = initialise_llm_client(provider, api_key)
        if not llm_client:
            print(f"❌ Failed to initialize {provider.value} client")
            return False

        # Simulate the exact prompt from generate_sql_plan
        metadata = {
            "available_datasets": ["AndoSalesDataPrep"],
            "selected_dataset": "AndoSalesDataPrep",
            "table_schemas": {},
        }

        prompt_payload = {
            "question": "Show me the schema of ando-big-query.AndoSalesDataPrep.BoltOrderSales",
            "metadata": metadata,
            "guidelines": {
                "row_limit": 200,
                "dialect": "BigQuery Standard SQL",
                "safety": "Read-only queries only. Do not perform DML/DDL operations.",
            },
            "expected_response_schema": {
                "sql": "Required. Read-only SQL query or null if impossible.",
                "analysis_steps": "Ordered list describing how the query answers the question.",
                "assumptions": "List of assumptions or clarifications you made.",
                "follow_up_questions": "Optional list of follow-up suggestions for the user.",
                "confidence": "Float between 0 and 1 describing confidence in the analysis.",
            },
        }

        from streamlit_app.app import SYSTEM_MESSAGE

        test_messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert BigQuery data analyst."
                    " Use the provided metadata and follow the MCP BigQuery server guidelines below.\n\n"
                    f"Guidelines:\n{SYSTEM_MESSAGE}\n\n"
                    "Return a single JSON object that follows the expected schema."
                    " Keep SQL efficient and readable. Always include a LIMIT clause no higher than the requested limit"
                    " unless the user explicitly requests otherwise."
                    "\n\n**IMPORTANT:** When the user refers to 'the table' or 'this table' without specifying a name,"
                    " check the conversation history to identify which table was previously discussed."
                    " Extract the full table reference (project.dataset.table) from previous queries or questions."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(prompt_payload, indent=2),
            },
        ]

        print(f"📤 Sending schema question to {provider.value}...")

        # Invoke LLM
        response_text = invoke_llm(
            llm_client=llm_client,
            model=PROVIDER_MODEL_DEFAULTS[provider],
            messages=test_messages,
            temperature=0.1,
        )

        print(f"📥 Raw response from {provider.value}:")
        print(f"   {response_text[:300]}...")

        # Try to parse JSON
        try:
            response_json = parse_json_response(response_text)
            print(f"✅ JSON parsed successfully")
            print(f"   Keys: {list(response_json.keys())}")
            print(f"\n📋 Full response:")
            print(json.dumps(response_json, indent=2))

            if "sql" in response_json:
                sql = response_json["sql"]
                if sql:
                    print(f"\n✅ {provider.value} generated SQL for schema question")
                    print(f"   SQL: {sql}")
                    return True
                else:
                    print(f"\n❌ SQL field is null - this is the reported error!")
                    print(f"   Analysis steps: {response_json.get('analysis_steps')}")
                    return False
            else:
                print(f"❌ No 'sql' field in response")
                return False

        except Exception as e:
            print(f"❌ Failed to parse JSON: {e}")
            print(f"   Raw response: {response_text}")
            return False

    except Exception as e:
        print(f"❌ {provider.value} test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run integration tests for all providers."""
    print("="*70)
    print("LLM PROVIDER INTEGRATION TESTS")
    print("Testing actual API invocations with real API keys")
    print("="*70)

    # Get API keys from environment
    api_keys = {
        LLMProvider.OPENAI: os.getenv("OPENAI_API_KEY"),
        LLMProvider.ANTHROPIC: os.getenv("ANTHROPIC_API_KEY"),
        LLMProvider.GEMINI: os.getenv("GEMINI_API_KEY"),
    }

    # Check which providers have keys
    print("\n🔑 API Key Status:")
    for provider, key in api_keys.items():
        status = "✅ Found" if key else "❌ Missing"
        print(f"   {provider.value}: {status}")

    available_providers = [p for p, k in api_keys.items() if k]

    if not available_providers:
        print("\n❌ No API keys found! Set environment variables:")
        print("   - OPENAI_API_KEY")
        print("   - ANTHROPIC_API_KEY")
        print("   - GEMINI_API_KEY")
        return False

    print(f"\n📊 Testing {len(available_providers)} provider(s)")

    # Test 1: Simple SQL generation
    print("\n" + "="*70)
    print("TEST 1: Simple SQL Generation")
    print("="*70)

    simple_results = {}
    for provider in available_providers:
        result = test_simple_json_question(provider, api_keys[provider])
        simple_results[provider] = result

    # Test 2: Schema question (reproducing the error)
    print("\n" + "="*70)
    print("TEST 2: Schema Question (Reproducing Error)")
    print("="*70)

    schema_results = {}
    for provider in available_providers:
        result = test_schema_question(provider, api_keys[provider])
        schema_results[provider] = result

    # Print summary
    print("\n" + "="*70)
    print("INTEGRATION TEST SUMMARY")
    print("="*70)

    print("\n📊 Simple SQL Generation:")
    for provider in available_providers:
        result = simple_results.get(provider)
        status = "✅ PASS" if result else "❌ FAIL" if result is False else "⚠️  SKIP"
        print(f"   {provider.value}: {status}")

    print("\n📊 Schema Question:")
    for provider in available_providers:
        result = schema_results.get(provider)
        status = "✅ PASS" if result else "❌ FAIL" if result is False else "⚠️  SKIP"
        print(f"   {provider.value}: {status}")

    # Overall result
    all_simple_passed = all(r for r in simple_results.values() if r is not None)
    all_schema_passed = all(r for r in schema_results.values() if r is not None)

    print("\n" + "="*70)
    if all_simple_passed and all_schema_passed:
        print("✅ ALL TESTS PASSED")
        return True
    elif all_simple_passed:
        print("⚠️  PARTIAL SUCCESS: Simple SQL works, schema questions fail")
        print("    This suggests the system prompt needs adjustment")
        return False
    else:
        print("❌ TESTS FAILED")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
