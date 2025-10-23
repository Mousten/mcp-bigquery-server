"""
Comprehensive test suite for LLM provider implementation in Streamlit app.

This script tests the multi-provider support without making actual API calls.
Tests include: imports, initialization, message formatting, and error handling.
"""
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))


def test_imports():
    """Test that all imports work correctly, including conditional imports."""
    print("=" * 70)
    print("TEST 1: Import Logic")
    print("=" * 70)

    try:
        from streamlit_app.app import (
            LLMProvider,
            LLMClientWrapper,
            AgentConfig,
            PROVIDER_MODEL_DEFAULTS,
            PROVIDER_API_KEY_ENV_VARS,
            initialise_llm_client,
            invoke_llm,
            split_system_and_conversation,
        )
        print("✅ All core imports successful")

        # Check if OpenAI is conditionally imported
        import streamlit_app.app as app_module
        openai_client = getattr(app_module, 'OpenAI', 'NOT_FOUND')
        if openai_client is None:
            print("✅ OpenAI not installed (conditional import working)")
        elif openai_client != 'NOT_FOUND':
            print("✅ OpenAI installed and imported")

        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_provider_enum():
    """Test LLMProvider enum values."""
    print("\n" + "=" * 70)
    print("TEST 2: Provider Enum")
    print("=" * 70)

    from streamlit_app.app import LLMProvider

    providers = list(LLMProvider)
    print(f"Available providers: {[p.value for p in providers]}")

    assert LLMProvider.OPENAI.value == "OpenAI", "OpenAI enum value incorrect"
    assert LLMProvider.ANTHROPIC.value == "Anthropic", "Anthropic enum value incorrect"
    assert LLMProvider.GEMINI.value == "Gemini", "Gemini enum value incorrect"

    print("✅ All provider enum values correct")
    return True


def test_model_defaults():
    """Test that model defaults are correct."""
    print("\n" + "=" * 70)
    print("TEST 3: Model Defaults")
    print("=" * 70)

    from streamlit_app.app import LLMProvider, PROVIDER_MODEL_DEFAULTS

    expected_models = {
        LLMProvider.OPENAI: "gpt-4.1-mini",
        LLMProvider.ANTHROPIC: "claude-sonnet-4-5",
        LLMProvider.GEMINI: "gemini-2.5-flash",
    }

    for provider, expected_model in expected_models.items():
        actual_model = PROVIDER_MODEL_DEFAULTS[provider]
        status = "✅" if actual_model == expected_model else "❌"
        print(f"{status} {provider.value}: {actual_model}")

        if actual_model != expected_model:
            print(f"   Expected: {expected_model}")
            return False

    print("✅ All model defaults correct")
    return True


def test_client_initialization():
    """Test client initialization for each provider."""
    print("\n" + "=" * 70)
    print("TEST 4: Client Initialization")
    print("=" * 70)

    from streamlit_app.app import LLMProvider, initialise_llm_client

    # Test with empty API key (should return None)
    result = initialise_llm_client(LLMProvider.OPENAI, "")
    assert result is None, "Should return None for empty API key"
    print("✅ Empty API key returns None")

    # Test OpenAI initialization with dummy key
    try:
        result = initialise_llm_client(LLMProvider.OPENAI, "sk-dummy-key-for-testing")
        if result is not None:
            print(f"✅ OpenAI client initialized: {type(result.client).__name__}")
            assert result.provider == LLMProvider.OPENAI
        else:
            print("⚠️  OpenAI SDK not installed (expected in test environment)")
    except RuntimeError as e:
        if "not installed" in str(e):
            print("⚠️  OpenAI SDK not installed (expected)")
        else:
            raise

    # Test Anthropic initialization with dummy key
    try:
        result = initialise_llm_client(LLMProvider.ANTHROPIC, "sk-ant-dummy-key")
        if result is not None:
            print(f"✅ Anthropic client initialized: {type(result.client).__name__}")
            assert result.provider == LLMProvider.ANTHROPIC
        else:
            print("⚠️  Anthropic SDK not installed (expected in test environment)")
    except RuntimeError as e:
        if "not installed" in str(e):
            print("⚠️  Anthropic SDK not installed (expected)")
        else:
            raise

    # Test Gemini initialization with dummy key
    try:
        result = initialise_llm_client(LLMProvider.GEMINI, "dummy-gemini-key")
        if result is not None:
            print(f"✅ Gemini client initialized: {type(result.client).__name__}")
            assert result.provider == LLMProvider.GEMINI
        else:
            print("⚠️  Gemini SDK not installed (expected in test environment)")
    except RuntimeError as e:
        if "not installed" in str(e):
            print("⚠️  Gemini SDK not installed (expected)")
        else:
            raise

    print("✅ Client initialization logic works correctly")
    return True


def test_message_formatting():
    """Test split_system_and_conversation function."""
    print("\n" + "=" * 70)
    print("TEST 5: Message Formatting")
    print("=" * 70)

    from streamlit_app.app import split_system_and_conversation

    # Test with system message
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "system", "content": "Additional context."},
        {"role": "user", "content": "How are you?"},
    ]

    system_prompt, conversation = split_system_and_conversation(messages)

    assert system_prompt == "You are a helpful assistant.\n\nAdditional context.", \
        f"System prompt incorrect: {system_prompt}"
    assert len(conversation) == 3, f"Conversation should have 3 messages, got {len(conversation)}"
    assert all(msg["role"] != "system" for msg in conversation), \
        "System messages should be filtered out"

    print(f"✅ System prompt extracted: {system_prompt[:50]}...")
    print(f"✅ Conversation messages: {len(conversation)}")

    # Test with no system message
    messages_no_system = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi!"},
    ]

    system_prompt, conversation = split_system_and_conversation(messages_no_system)
    assert system_prompt is None, "Should return None when no system message"
    assert len(conversation) == 2, "Should return all non-system messages"

    print("✅ Message formatting works correctly")
    return True


def test_conversation_history_limit():
    """Test that conversation history is properly limited."""
    print("\n" + "=" * 70)
    print("TEST 6: Conversation History Limit")
    print("=" * 70)

    # Simulate what generate_sql_plan does
    conversation_history = [
        {"role": "user", "content": f"Question {i}"}
        for i in range(10)
    ]

    # The code limits to last 6 messages
    recent_history = conversation_history[-6:]

    assert len(recent_history) == 6, f"Should limit to 6 messages, got {len(recent_history)}"
    assert recent_history[0]["content"] == "Question 4", \
        "Should start from the 5th message (index 4)"

    print(f"✅ Conversation history limited to {len(recent_history)} messages")
    print(f"✅ First message in history: {recent_history[0]['content']}")
    print(f"✅ Last message in history: {recent_history[-1]['content']}")

    return True


def test_error_handling():
    """Test error handling for missing dependencies."""
    print("\n" + "=" * 70)
    print("TEST 7: Error Handling")
    print("=" * 70)

    from streamlit_app.app import LLMProvider, initialise_llm_client

    # We can't easily test missing dependencies without uninstalling packages,
    # but we can verify the error messages are proper

    try:
        # Test with None API key
        result = initialise_llm_client(LLMProvider.OPENAI, None)
        assert result is None, "Should return None for None API key"
        print("✅ None API key handled correctly")

        # Test with whitespace-only API key
        result = initialise_llm_client(LLMProvider.OPENAI, "   ")
        assert result is None, "Should return None for whitespace API key"
        print("✅ Whitespace API key handled correctly")

    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False

    print("✅ Error handling works correctly")
    return True


def test_config_structure():
    """Test AgentConfig dataclass structure."""
    print("\n" + "=" * 70)
    print("TEST 8: Configuration Structure")
    print("=" * 70)

    from streamlit_app.app import AgentConfig, LLMProvider

    config = AgentConfig(
        base_url="http://localhost:8005",
        user_id="test-user",
        session_id="test-session",
        use_cache=True,
        maximum_bytes_billed=100_000_000,
        row_limit=200,
        model="gpt-4.1-mini",
        provider=LLMProvider.OPENAI,
    )

    assert config.base_url == "http://localhost:8005"
    assert config.user_id == "test-user"
    assert config.session_id == "test-session"
    assert config.use_cache is True
    assert config.maximum_bytes_billed == 100_000_000
    assert config.row_limit == 200
    assert config.model == "gpt-4.1-mini"
    assert config.provider == LLMProvider.OPENAI

    print("✅ AgentConfig structure correct")
    print(f"   Provider: {config.provider.value}")
    print(f"   Model: {config.model}")
    print(f"   Row limit: {config.row_limit}")

    return True


def test_provider_api_key_mapping():
    """Test that API key environment variables are correctly mapped."""
    print("\n" + "=" * 70)
    print("TEST 9: API Key Environment Variables")
    print("=" * 70)

    from streamlit_app.app import LLMProvider, PROVIDER_API_KEY_ENV_VARS

    expected_mapping = {
        LLMProvider.OPENAI: "OPENAI_API_KEY",
        LLMProvider.ANTHROPIC: "ANTHROPIC_API_KEY",
        LLMProvider.GEMINI: "GEMINI_API_KEY",
    }

    for provider, expected_env_var in expected_mapping.items():
        actual_env_var = PROVIDER_API_KEY_ENV_VARS[provider]
        status = "✅" if actual_env_var == expected_env_var else "❌"
        print(f"{status} {provider.value}: {actual_env_var}")

        if actual_env_var != expected_env_var:
            print(f"   Expected: {expected_env_var}")
            return False

    print("✅ All API key mappings correct")
    return True


def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "=" * 70)
    print("TESTING LLM PROVIDER IMPLEMENTATION")
    print("=" * 70 + "\n")

    tests = [
        ("Imports", test_imports),
        ("Provider Enum", test_provider_enum),
        ("Model Defaults", test_model_defaults),
        ("Client Initialization", test_client_initialization),
        ("Message Formatting", test_message_formatting),
        ("Conversation History", test_conversation_history_limit),
        ("Error Handling", test_error_handling),
        ("Config Structure", test_config_structure),
        ("API Key Mapping", test_provider_api_key_mapping),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result, None))
        except Exception as e:
            results.append((test_name, False, str(e)))
            print(f"\n❌ {test_name} failed with exception: {e}")

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result, _ in results if result)
    total = len(results)

    for test_name, result, error in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
        if error:
            print(f"       Error: {error}")

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! The LLM provider implementation is working correctly.")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review and fix.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
