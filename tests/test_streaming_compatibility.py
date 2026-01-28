"""
Streaming Compatibility Tests

Tests verify that the SDK configuration is compatible with MiniMax streaming API:
1. Timeout configuration is properly set
2. Hooks are async-safe and non-blocking
3. Environment variables propagate correctly to SDK

Based on findings from:
.planning/research/SDK与MiniMax流式传输实现的兼容性架构与工程解决方案深度报告.md
"""
import asyncio
import inspect
import time
from unittest.mock import Mock, patch, AsyncMock
import pytest

from src.modules.agent_sdk import AgentSDKRunner
from src.hooks import logging_hooks


@pytest.mark.timeout(5)
def test_timeout_configuration():
    """
    Verify that AgentSDKRunner configures API_TIMEOUT_MS in env vars.

    Critical for MiniMax M2.1: SDK default 30s timeout is too short for
    reasoning tasks. Must be set to 3000000ms (3000s).
    """
    # Create runner instance
    runner = AgentSDKRunner(
        api_key="test-key",
        model="MiniMax-M2.1",
        temperature=0.7,
        notebook_id="test-notebook-id"
    )

    # Mock the query function to capture options
    with patch('src.modules.agent_sdk.query') as mock_query:
        # Configure mock to return async iterator
        async def mock_async_gen():
            # Return empty result to complete immediately
            mock_msg = Mock()
            mock_msg.result = "test result"
            mock_msg.usage = None
            yield mock_msg

        mock_query.return_value = mock_async_gen()

        # Run generate
        async def run_test():
            await runner.generate(
                topic="test topic",
                search_results=[],
                system_prompt="test prompt",
                max_turns=1
            )

        asyncio.run(run_test())

        # Verify query was called with correct options
        assert mock_query.called, "SDK query should be called"
        call_args = mock_query.call_args

        # Extract options from call
        options = call_args.kwargs['options']

        # Verify API_TIMEOUT_MS is in env vars
        assert hasattr(options, 'env'), "Options should have env attribute"
        assert options.env is not None, "Env vars should not be None"
        assert "API_TIMEOUT_MS" in options.env, "API_TIMEOUT_MS must be in env vars"
        assert options.env["API_TIMEOUT_MS"] == "3000000", "Timeout should be 3000000ms"


@pytest.mark.timeout(5)
@pytest.mark.asyncio
async def test_async_hooks_non_blocking():
    """
    Verify all hooks are async functions and complete quickly.

    Critical for MiniMax streaming: Synchronous hooks block the async event loop,
    preventing SSE stream processing and causing timeout after 60s.
    """
    # Get all hook functions from the module
    hooks = [
        logging_hooks.pre_tool_use_hook,
        logging_hooks.post_tool_use_hook,
        logging_hooks.stop_hook,
        logging_hooks.user_prompt_submit_hook
    ]

    # Verify all are async functions
    for hook in hooks:
        assert inspect.iscoroutinefunction(hook), \
            f"{hook.__name__} must be async function (async def)"

    # Test that hooks complete quickly with mock data
    mock_metrics = Mock()
    mock_metrics.tool_calls = []
    mock_metrics.end_time = None
    mock_metrics.tool_call_count = 0
    mock_metrics.runtime_seconds = 0.0

    test_data = {
        'tool_name': 'test_tool',
        'tool_input': {'arg': 'value'},
        'tool_response': 'test response',
        'prompt': 'test prompt'
    }

    # Run each hook with timeout to ensure no blocking
    for hook in hooks:
        start = time.time()

        try:
            # Use asyncio.timeout to ensure hook completes within 100ms
            async with asyncio.timeout(0.1):  # 100ms timeout
                result = await hook(
                    input_data=test_data,
                    tool_use_id="test-id",
                    context=Mock(),
                    metrics=mock_metrics
                )

            duration_ms = (time.time() - start) * 1000

            # Verify hook returned dict (SDK requirement)
            assert isinstance(result, dict), f"{hook.__name__} must return dict"

            # Verify hook completed quickly
            assert duration_ms < 100, \
                f"{hook.__name__} took {duration_ms:.1f}ms (should be <100ms)"

        except asyncio.TimeoutError:
            pytest.fail(f"{hook.__name__} timed out - likely contains blocking operation")


@pytest.mark.timeout(5)
def test_env_vars_propagation():
    """
    Verify environment variables propagate correctly to ClaudeAgentOptions.

    Tests that ANTHROPIC_BASE_URL and API_TIMEOUT_MS are properly passed
    to the SDK configuration.
    """
    with patch.dict('os.environ', {
        'ANTHROPIC_BASE_URL': 'https://api.minimaxi.com/anthropic'
    }):
        # Create runner
        runner = AgentSDKRunner(
            api_key="test-key",
            model="MiniMax-M2.1",
            temperature=0.7,
            notebook_id="test-notebook-id"
        )

        # Mock query to capture options
        with patch('src.modules.agent_sdk.query') as mock_query:
            async def mock_async_gen():
                mock_msg = Mock()
                mock_msg.result = "test"
                mock_msg.usage = None
                yield mock_msg

            mock_query.return_value = mock_async_gen()

            # Run generate
            async def run_test():
                await runner.generate(
                    topic="test",
                    search_results=[],
                    system_prompt="test",
                    max_turns=1
                )

            asyncio.run(run_test())

            # Verify options
            options = mock_query.call_args.kwargs['options']

            # Check ANTHROPIC_BASE_URL propagation
            assert "ANTHROPIC_BASE_URL" in options.env, \
                "ANTHROPIC_BASE_URL should propagate to SDK"
            assert options.env["ANTHROPIC_BASE_URL"] == "https://api.minimaxi.com/anthropic"

            # Check API_TIMEOUT_MS is always set
            assert "API_TIMEOUT_MS" in options.env
            assert options.env["API_TIMEOUT_MS"] == "3000000"


@pytest.mark.timeout(5)
def test_hooks_module_has_safety_warning():
    """
    Verify that the hooks module contains async safety documentation.

    Ensures future developers are warned about blocking operations.
    """
    # Read the hooks module docstring
    module_doc = logging_hooks.__doc__

    assert module_doc is not None, "Hooks module must have docstring"
    assert "async" in module_doc.lower() or "blocking" in module_doc.lower(), \
        "Module docstring should warn about async safety"
    assert "input()" in module_doc or "synchronous" in module_doc.lower(), \
        "Module docstring should warn about specific blocking operations"
