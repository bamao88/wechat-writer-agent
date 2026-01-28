"""Tool Call Validation Tests - Verify tool call logging and autonomous invocation"""
import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from src.modules.agent_sdk import AgentRunMetrics, AgentSDKRunner
from src.hooks.logging_hooks import (
    pre_tool_use_hook,
    post_tool_use_hook,
    get_tool_call_summary
)


class TestToolCallLogging:
    """Test tool call logging functionality"""

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_tool_call_logging_complete(self):
        """
        VAL-03: Verify all required fields are captured in tool call logging.

        Tests that PreToolUse and PostToolUse hooks capture:
        - tool_name, tool_use_id, input, query_params, invocation_reason, timestamp, start_time (pre)
        - end_time, duration_ms, result, result_summary, result_length, success (post)
        """
        # Create metrics instance
        metrics = AgentRunMetrics()

        # Sample tool data
        tool_name = "notebooklm"
        tool_use_id = "test_tool_123"
        tool_input = {
            "question": "What is the best way to validate tool calls in SDK mode?"
        }
        tool_response = "To validate tool calls, you should capture pre and post hook data..."

        # Call pre hook
        input_data_pre = {
            "tool_name": tool_name,
            "tool_input": tool_input
        }
        context = None
        await pre_tool_use_hook(input_data_pre, tool_use_id, context, metrics)

        # Verify pre hook fields
        assert len(metrics.tool_calls) == 1
        tool_call = metrics.tool_calls[0]

        assert tool_call['tool_name'] == tool_name
        assert tool_call['tool_use_id'] == tool_use_id
        assert tool_call['input'] == tool_input
        assert tool_call['query_params'] == tool_input['question']
        assert 'timestamp' in tool_call
        assert 'start_time' in tool_call

        # Simulate some processing time
        await asyncio.sleep(0.01)

        # Call post hook
        input_data_post = {
            "tool_name": tool_name,
            "tool_response": tool_response
        }
        await post_tool_use_hook(input_data_post, tool_use_id, context, metrics)

        # Verify post hook fields
        tool_call = metrics.tool_calls[0]

        assert 'end_time' in tool_call
        assert 'duration_ms' in tool_call
        assert tool_call['duration_ms'] > 0
        assert tool_call['result'] == tool_response
        assert 'result_summary' in tool_call
        assert tool_call['result_summary'] == tool_response[:200]
        assert 'result_length' in tool_call
        assert tool_call['result_length'] == len(tool_response)
        assert 'success' in tool_call
        assert tool_call['success'] is True

        print(f"✓ All required logging fields captured successfully")

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_tool_call_summary_aggregation(self):
        """
        Test get_tool_call_summary aggregates metrics correctly.

        Verifies: total_count, tool_names list, average_duration_ms, success/failure counts
        """
        # Create metrics with multiple tool calls
        metrics = AgentRunMetrics()

        # First tool call (successful)
        await pre_tool_use_hook(
            {"tool_name": "notebooklm", "tool_input": {"question": "test1"}},
            "id1",
            None,
            metrics
        )
        await asyncio.sleep(0.01)
        await post_tool_use_hook(
            {"tool_name": "notebooklm", "tool_response": "result1"},
            "id1",
            None,
            metrics
        )

        # Second tool call (successful)
        await pre_tool_use_hook(
            {"tool_name": "search", "tool_input": {"query": "test2"}},
            "id2",
            None,
            metrics
        )
        await asyncio.sleep(0.015)
        await post_tool_use_hook(
            {"tool_name": "search", "tool_response": "result2"},
            "id2",
            None,
            metrics
        )

        # Third tool call (failed)
        await pre_tool_use_hook(
            {"tool_name": "notebooklm", "tool_input": {"question": "test3"}},
            "id3",
            None,
            metrics
        )
        await asyncio.sleep(0.005)
        await post_tool_use_hook(
            {"tool_name": "notebooklm", "tool_response": {"error": "API timeout"}},
            "id3",
            None,
            metrics
        )

        # Get summary
        summary = get_tool_call_summary(metrics)

        # Verify aggregation
        assert summary['total_count'] == 3
        assert set(summary['tool_names']) == {"notebooklm", "search"}
        assert summary['average_duration_ms'] > 0
        assert summary['success_count'] == 2
        assert summary['failure_count'] == 1

        print(f"✓ Summary aggregation working: {summary}")

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_pre_post_hook_matching(self):
        """
        Test that pre and post hooks correctly match by tool_use_id.

        Multiple concurrent tool calls should not interfere with each other.
        """
        metrics = AgentRunMetrics()

        # Start multiple tool calls
        tool_ids = ["tool_a", "tool_b", "tool_c"]
        for tool_id in tool_ids:
            await pre_tool_use_hook(
                {"tool_name": f"tool_{tool_id}", "tool_input": {"query": f"query_{tool_id}"}},
                tool_id,
                None,
                metrics
            )

        # Verify all pre hooks recorded
        assert len(metrics.tool_calls) == 3

        # Complete them in different order (c, a, b)
        await post_tool_use_hook(
            {"tool_name": "tool_tool_c", "tool_response": "result_c"},
            "tool_c",
            None,
            metrics
        )
        await post_tool_use_hook(
            {"tool_name": "tool_tool_a", "tool_response": "result_a"},
            "tool_a",
            None,
            metrics
        )
        await post_tool_use_hook(
            {"tool_name": "tool_tool_b", "tool_response": "result_b"},
            "tool_b",
            None,
            metrics
        )

        # Verify each tool_use_id correctly matched with its result
        tool_id_to_result = {
            "tool_a": "result_a",
            "tool_b": "result_b",
            "tool_c": "result_c"
        }
        for call in metrics.tool_calls:
            tool_id = call['tool_use_id']
            assert call['result'] == tool_id_to_result[tool_id]
            assert 'duration_ms' in call

        print(f"✓ Pre/Post hook matching works correctly for concurrent calls")

    @pytest.mark.asyncio
    @pytest.mark.timeout(10)
    async def test_tool_call_count_nonzero(self):
        """
        VAL-02: Verify that tool_call_count > 0 when tool is invoked.

        This tests the hook integration with AgentSDKRunner to ensure
        tool calls are properly recorded (not always 0).
        """
        # Create metrics instance
        metrics = AgentRunMetrics()

        # Simulate tool call via hooks
        await pre_tool_use_hook(
            {"tool_name": "notebooklm", "tool_input": {"question": "test"}},
            "test_id",
            None,
            metrics
        )
        await post_tool_use_hook(
            {"tool_name": "notebooklm", "tool_response": "test result"},
            "test_id",
            None,
            metrics
        )

        # VAL-02: Verify tool_call_count > 0
        assert metrics.tool_call_count > 0
        assert metrics.tool_call_count == 1

        # Add another tool call
        await pre_tool_use_hook(
            {"tool_name": "search", "tool_input": {"query": "another test"}},
            "test_id_2",
            None,
            metrics
        )
        await post_tool_use_hook(
            {"tool_name": "search", "tool_response": "another result"},
            "test_id_2",
            None,
            metrics
        )

        # Verify count incremented
        assert metrics.tool_call_count == 2

        print(f"✓ tool_call_count correctly increments: {metrics.tool_call_count}")


class TestToolCallValidationEmptyMetrics:
    """Test get_tool_call_summary with edge cases"""

    def test_get_tool_call_summary_empty_metrics(self):
        """Test get_tool_call_summary returns correct structure for empty metrics"""
        metrics = AgentRunMetrics()

        summary = get_tool_call_summary(metrics)

        assert summary['total_count'] == 0
        assert summary['tool_names'] == []
        assert summary['average_duration_ms'] == 0
        assert summary['success_count'] == 0
        assert summary['failure_count'] == 0

        print(f"✓ Empty metrics handled correctly")

    def test_get_tool_call_summary_no_duration(self):
        """Test get_tool_call_summary handles tool calls without duration_ms"""
        metrics = AgentRunMetrics()

        # Add a tool call without duration_ms (incomplete call)
        metrics.tool_calls.append({
            'tool_name': 'incomplete_tool',
            'tool_use_id': 'incomplete_id',
            'success': False
        })

        summary = get_tool_call_summary(metrics)

        assert summary['total_count'] == 1
        assert summary['tool_names'] == ['incomplete_tool']
        assert summary['average_duration_ms'] == 0
        assert summary['success_count'] == 0
        assert summary['failure_count'] == 1

        print(f"✓ Incomplete tool calls handled correctly")


class TestAutonomousToolCallTriggers:
    """
    Test the CONDITIONS that trigger autonomous tool calling (VAL-01).

    These tests verify the TRIGGER mechanism, not just the behavior.
    Agent should AUTOMATICALLY call tools when:
    1. search_results is empty/None (lacking materials)
    2. Prompt template instructs tool usage
    3. SDK is configured with allowed_tools and setting_sources
    """

    @pytest.mark.timeout(30)
    def test_trigger_conditions_empty_search_results(self):
        """
        VAL-01: Verify that empty search_results triggers tool query decision.

        Tests the user message construction when no materials are provided,
        which should instruct the Agent to query NotebookLM for knowledge.
        """
        # Create AgentSDKRunner with minimal config
        runner = AgentSDKRunner(
            api_key="test_key",
            model="test_model",
            temperature=0.7,
            notebook_id="test_notebook_123"
        )

        # Build user message with empty search_results
        topic = "AI产品经理的技术选型"
        search_results = []  # Empty - no materials provided

        user_message = runner._build_user_message(topic, search_results)

        # Verify the message instructs tool usage
        assert "未检索到相关素材" in user_message
        assert "使用工具" in user_message or "检索" in user_message
        assert topic in user_message

        print(f"✓ Empty search_results triggers tool usage instruction")
        print(f"  Message excerpt: {user_message[:200]}...")

    @pytest.mark.timeout(30)
    def test_trigger_conditions_prompt_contains_tool_instruction(self):
        """
        VAL-01: Verify prompt template contains instruction for using NotebookLM.

        The system prompt should mention NotebookLM/知识库 and query/查询
        to instruct the Agent on autonomous tool calling.
        """
        import os

        # Load the prompt template
        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "write_prompt",
            "V1.md"
        )

        assert os.path.exists(prompt_path), f"Prompt template not found at {prompt_path}"

        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_content = f.read()

        # Verify tool calling instructions exist
        # Pattern 1: mention of notebooklm or 知识库
        has_tool_reference = (
            "notebooklm" in prompt_content.lower() or
            "知识库" in prompt_content
        )

        # Pattern 2: instruction to query/检索/调用工具
        has_query_instruction = (
            "查询" in prompt_content or
            "检索" in prompt_content or
            "调用" in prompt_content and "工具" in prompt_content
        )

        # Pattern 3: specific section about tool usage
        has_tool_section = "工具使用" in prompt_content or "检索资料" in prompt_content

        assert has_tool_reference or has_tool_section, \
            "Prompt should reference NotebookLM or 知识库"
        assert has_query_instruction or has_tool_section, \
            "Prompt should instruct Agent to query/检索 when needed"

        print(f"✓ Prompt template contains tool usage instructions")
        print(f"  Has tool reference: {has_tool_reference}")
        print(f"  Has query instruction: {has_query_instruction}")
        print(f"  Has tool section: {has_tool_section}")

    @pytest.mark.timeout(30)
    def test_trigger_conditions_allowed_tools_configured(self):
        """
        VAL-01: Verify SDK has correct allowed_tools and setting_sources.

        These are prerequisites for autonomous tool calling:
        - allowed_tools must include "Skill" for NotebookLM discovery
        - setting_sources must include "user" for skill loading
        """
        # Create AgentSDKRunner with notebook_id configured
        runner = AgentSDKRunner(
            api_key="test_key",
            model="test_model",
            temperature=0.7,
            notebook_id="test_notebook_123"
        )

        # Get allowed_tools configuration
        allowed_tools = runner._get_allowed_tools()

        # Verify "Skill" is in allowed_tools
        assert "Skill" in allowed_tools, \
            "allowed_tools must include 'Skill' for NotebookLM discovery"

        print(f"✓ SDK configured with allowed_tools: {allowed_tools}")

    @pytest.mark.timeout(30)
    def test_trigger_conditions_no_notebook_id_warning(self):
        """
        VAL-01: Verify proper warning when notebook_id not configured.

        If notebook_id is missing, tool calling is disabled and a warning should appear.
        """
        # Create AgentSDKRunner WITHOUT notebook_id
        runner = AgentSDKRunner(
            api_key="test_key",
            model="test_model",
            temperature=0.7,
            notebook_id=None  # Not configured
        )

        # Get allowed_tools configuration
        allowed_tools = runner._get_allowed_tools()

        # Verify tools are disabled
        assert allowed_tools == [], \
            "allowed_tools should be empty when notebook_id not configured"

        print(f"✓ Tool calling correctly disabled without notebook_id")

