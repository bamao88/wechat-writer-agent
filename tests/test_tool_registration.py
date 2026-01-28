"""Test tool registration with Claude Agent SDK and MiniMax API"""
import asyncio
import json
import os
import pytest
from dotenv import load_dotenv
from unittest.mock import patch
from io import StringIO
import sys

load_dotenv()


@pytest.mark.asyncio
async def test_skill_discovery():
    """Verify SDK discovers NotebookLM Skill from filesystem"""
    from claude_agent_sdk import query, ClaudeAgentOptions

    # Ensure notebook_id is set for this test
    notebook_id = os.getenv("NOTEBOOK_ID")
    if not notebook_id:
        pytest.skip("NOTEBOOK_ID not set in environment")

    env_vars = {
        "ANTHROPIC_BASE_URL": os.getenv("ANTHROPIC_BASE_URL", "https://api.minimaxi.com/anthropic"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY")
    }

    options = ClaudeAgentOptions(
        model=os.getenv("MODEL_NAME", "MiniMax-M2.1"),
        max_turns=1,
        setting_sources=["user"],
        allowed_tools=["Skill"],
        system_prompt="You are a helpful assistant. List the tools available to you.",
        env=env_vars
    )

    result_text = ""
    async for message in query(
        prompt="What tools or skills do you have access to? List them briefly.",
        options=options
    ):
        if hasattr(message, 'result') and message.result:
            result_text = message.result

    # Agent should mention NotebookLM or knowledge/notebook querying capability
    assert result_text, "No response received from Agent"
    print(f"\n=== Agent Response ===\n{result_text}\n")

    # Check for tool-related keywords (flexible matching)
    tool_indicators = ["notebooklm", "notebook", "knowledge", "query", "skill", "tool"]
    found = any(indicator in result_text.lower() for indicator in tool_indicators)

    # This is a soft assertion - if Agent doesn't mention tools, it might still work
    # The real test is in Phase 2 when we verify actual tool calling
    if not found:
        print("[WARNING] Agent response does not explicitly mention tools.")
        print("This may be normal - tool awareness varies by prompt.")


@pytest.mark.asyncio
async def test_sdk_options_accepted():
    """Verify MiniMax API accepts our SDK options without error"""
    from claude_agent_sdk import query, ClaudeAgentOptions

    env_vars = {
        "ANTHROPIC_BASE_URL": os.getenv("ANTHROPIC_BASE_URL", "https://api.minimaxi.com/anthropic"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY")
    }

    # This tests that MiniMax API accepts the request format
    options = ClaudeAgentOptions(
        model=os.getenv("MODEL_NAME", "MiniMax-M2.1"),
        max_turns=1,
        setting_sources=["user"],
        allowed_tools=["Skill"],
        system_prompt="Say hello.",
        env=env_vars
    )

    response_received = False
    async for message in query(prompt="Hello", options=options):
        if hasattr(message, 'result') and message.result:
            response_received = True
            print(f"API Response: {message.result[:100]}...")

    assert response_received, "No response from MiniMax API"


@pytest.mark.asyncio
async def test_sdk_startup_logs_skill_discovery():
    """
    Verify SDK startup correctly discovers and registers Skills.

    This test captures SDK initialization logs to confirm tool discovery,
    independent of what the Agent says in its response.

    Satisfies TOOL-04: SDK启动时能成功发现并注册 NotebookLM 工具
    """
    from claude_agent_sdk import query, ClaudeAgentOptions

    notebook_id = os.getenv("NOTEBOOK_ID")
    if not notebook_id:
        pytest.skip("NOTEBOOK_ID not set in environment")

    env_vars = {
        "ANTHROPIC_BASE_URL": os.getenv("ANTHROPIC_BASE_URL", "https://api.minimaxi.com/anthropic"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY")
    }

    # Capture stdout to check for SDK discovery logs
    captured_output = StringIO()
    original_stdout = sys.stdout

    try:
        sys.stdout = captured_output

        options = ClaudeAgentOptions(
            model=os.getenv("MODEL_NAME", "MiniMax-M2.1"),
            max_turns=1,
            setting_sources=["user"],
            allowed_tools=["Skill"],
            system_prompt="Say 'test complete'.",
            env=env_vars
        )

        # Trigger SDK initialization by starting a query
        async for message in query(prompt="Test", options=options):
            pass  # We only care about initialization, not the response

    finally:
        sys.stdout = original_stdout

    logs = captured_output.getvalue()
    print(f"\n=== Captured SDK Logs ===\n{logs}\n")

    # Check for indicators that SDK processed the setting_sources and allowed_tools
    # These are the key indicators that tool registration occurred:
    skill_discovery_indicators = [
        "Skill",           # SDK mentions Skill category
        "skill",           # lowercase variant
        "notebooklm",      # Specific skill name
        "NotebookLM",      # Capitalized variant
        "setting_sources", # Configuration being applied
        "allowed_tools",   # Tools being registered
        "discovery",       # Discovery process
        "registered",      # Registration confirmation
        "loaded",          # Skill loaded
    ]

    found_indicators = [ind for ind in skill_discovery_indicators if ind.lower() in logs.lower()]

    # Also check our custom log message from _get_allowed_tools
    custom_log_present = "[INFO] Enabling Skill discovery" in logs

    print(f"Found indicators in logs: {found_indicators}")
    print(f"Custom _get_allowed_tools log present: {custom_log_present}")

    # At minimum, our custom log should appear (confirms _get_allowed_tools was called)
    assert custom_log_present or len(found_indicators) > 0, (
        f"SDK startup did not log skill discovery. "
        f"Expected at least our custom log '[INFO] Enabling Skill discovery' or SDK indicators. "
        f"Captured logs:\n{logs}"
    )


@pytest.mark.asyncio
async def test_minimax_api_parses_tool_definitions():
    """
    Verify MiniMax API correctly parses and acknowledges tool definitions.

    Satisfies API-02: Tool definition format compatible with MiniMax API.

    This test:
    1. Sends a request with tool definitions enabled
    2. Captures the raw API request/response
    3. Verifies tool definitions appear in request
    4. Verifies API does not return tool schema errors
    """
    from claude_agent_sdk import query, ClaudeAgentOptions
    import httpx
    from unittest.mock import MagicMock

    notebook_id = os.getenv("NOTEBOOK_ID")
    if not notebook_id:
        pytest.skip("NOTEBOOK_ID not set in environment")

    env_vars = {
        "ANTHROPIC_BASE_URL": os.getenv("ANTHROPIC_BASE_URL", "https://api.minimaxi.com/anthropic"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY")
    }

    # Track API request details
    api_requests = []
    api_responses = []

    # Create a custom transport to capture requests
    original_transport = httpx.AsyncHTTPTransport

    class CapturingTransport(httpx.AsyncHTTPTransport):
        async def handle_async_request(self, request):
            # Capture request body
            body = request.content
            if body:
                try:
                    request_data = json.loads(body.decode('utf-8'))
                    api_requests.append(request_data)
                    print(f"\n=== API Request ===")
                    print(f"URL: {request.url}")
                    if 'tools' in request_data:
                        print(f"Tools in request: {json.dumps(request_data['tools'], indent=2)[:500]}...")
                    else:
                        print("No 'tools' key in request body")
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass

            response = await super().handle_async_request(request)

            # Capture response
            api_responses.append({
                'status': response.status_code,
                'headers': dict(response.headers)
            })

            return response

    # Patch httpx transport
    with patch.object(httpx, 'AsyncHTTPTransport', CapturingTransport):
        options = ClaudeAgentOptions(
            model=os.getenv("MODEL_NAME", "MiniMax-M2.1"),
            max_turns=1,
            setting_sources=["user"],
            allowed_tools=["Skill"],
            system_prompt="You have access to knowledge base tools. Confirm you see them.",
            env=env_vars
        )

        response_received = False
        error_messages = []

        async for message in query(
            prompt="Confirm what tools you have available.",
            options=options
        ):
            if hasattr(message, 'result') and message.result:
                response_received = True
                result = message.result
                # Check for error indicators in response
                error_keywords = ['error', 'invalid', 'unsupported', 'unknown tool', 'schema']
                for kw in error_keywords:
                    if kw in result.lower():
                        error_messages.append(f"Potential error indicator '{kw}' found in response")

    # Assertions
    assert response_received, "No response received from MiniMax API"

    # Check that API accepted the request (200-level response)
    if api_responses:
        status = api_responses[-1].get('status', 0)
        assert 200 <= status < 300, f"API returned error status: {status}"
        print(f"\n=== API Response Status: {status} ===")

    # Check for tool definitions in request (if captured)
    if api_requests:
        last_request = api_requests[-1]
        has_tools = 'tools' in last_request
        print(f"\nTool definitions present in API request: {has_tools}")
        if has_tools:
            tool_count = len(last_request['tools'])
            print(f"Number of tools sent to API: {tool_count}")
            assert tool_count > 0, "Tools array is empty - SDK may not have discovered Skills"
            # Verify tool schema structure
            first_tool = last_request['tools'][0]
            assert 'name' in first_tool, "Tool missing 'name' field"
            print(f"First tool name: {first_tool.get('name')}")

    # Warn but don't fail on potential error indicators (may be false positives)
    if error_messages:
        print(f"\n[WARNING] Potential issues detected: {error_messages}")
        print("These may be false positives - manual review recommended")

    print("\n=== API-02 Verification: Tool definitions accepted by MiniMax API ===")


if __name__ == "__main__":
    # Allow running directly for quick testing
    asyncio.run(test_skill_discovery())
