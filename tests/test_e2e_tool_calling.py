"""End-to-End Tool Calling Integration Tests

These tests verify that the Agent autonomously calls tools and uses returned
knowledge in real generation scenarios.

Tests cover:
- VAL-01: Agent automatically calls NotebookLM tool (not manual)
- VAL-04: Verifiable tool call (not false positive)

These are integration tests requiring API access. Run with:
    pytest tests/test_e2e_tool_calling.py -v -s --timeout=300 -m integration
"""
import pytest
import asyncio
import os
from dotenv import load_dotenv
from src.modules.agent_sdk import AgentSDKRunner, AgentRunMetrics

# Load environment
load_dotenv()


@pytest.mark.integration
@pytest.mark.timeout(180)
@pytest.mark.asyncio
async def test_autonomous_tool_call_e2e():
    """
    VAL-01: End-to-end test proving Agent autonomously calls NotebookLM tool.

    This test verifies the ENTIRE chain:
    1. Agent receives prompt with empty search_results (lacking materials)
    2. Agent recognizes need for knowledge
    3. Agent autonomously invokes NotebookLM tool (no human intervention)
    4. Tool returns knowledge
    5. Agent uses knowledge in generation

    Success criteria:
    - tool_call_count > 0 (proves tool was called)
    - tool_calls[0]['tool_name'] contains 'notebooklm' (correct tool)
    - No test code manually invoked the tool (fully autonomous)
    """
    # Get API configuration
    api_key = os.getenv("ANTHROPIC_API_KEY")
    base_url = os.getenv("ANTHROPIC_BASE_URL")
    model = os.getenv("ANTHROPIC_MODEL", "MiniMax-M2.1")
    notebook_id = os.getenv("NOTEBOOK_ID")

    # Skip if no credentials
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set - cannot test API")
    if not notebook_id:
        pytest.skip("NOTEBOOK_ID not set - tool calling disabled")

    print(f"\n{'='*70}")
    print("Test: Autonomous Tool Call E2E")
    print(f"{'='*70}")
    print(f"API: {base_url or 'default'}")
    print(f"Model: {model}")
    print(f"Notebook: {notebook_id[:20]}...")

    # Create AgentSDKRunner
    runner = AgentSDKRunner(
        api_key=api_key,
        model=model,
        temperature=0.7,
        notebook_id=notebook_id
    )

    # Topic that clearly needs knowledge from personal experiences
    topic = "请根据我的个人经历写一篇关于创业的文章"

    # CRITICAL: Pass empty search_results to force tool calling
    # This simulates "lacking materials" condition that should trigger autonomous query
    search_results = []

    # System prompt that instructs tool usage
    system_prompt = """你是一个智能写作助手。

当用户需要素材但没有提供时，你应该主动使用NotebookLM工具查询知识库获取相关信息。

请根据用户的需求，决定是否需要查询知识库，并撰写文章。"""

    print(f"\nInput:")
    print(f"  Topic: {topic}")
    print(f"  Search results: [] (empty - should trigger tool call)")
    print(f"  Max turns: 5")

    # Run generation with 120-second timeout
    print(f"\nRunning generation (120s timeout)...")
    result_text, metrics = await asyncio.wait_for(
        runner.generate(
            topic=topic,
            search_results=search_results,
            system_prompt=system_prompt,
            max_turns=5
        ),
        timeout=120.0
    )

    # Assertions
    print(f"\n{'='*70}")
    print("Results:")
    print(f"{'='*70}")
    print(f"Runtime: {metrics.runtime_seconds:.2f}s")
    print(f"Tool calls: {metrics.tool_call_count}")
    print(f"Result length: {len(result_text)} chars")

    # VAL-01: Verify tool was autonomously called
    assert metrics.tool_call_count > 0, \
        "Agent did not call any tools - VAL-01 FAILED (no autonomous tool calling)"

    print(f"\n✓ VAL-01 PASSED: tool_call_count = {metrics.tool_call_count}")

    # Verify it was the NotebookLM tool
    tool_call = metrics.tool_calls[0]
    tool_name = tool_call.get('tool_name', '').lower()

    print(f"\nTool call details:")
    print(f"  Tool name: {tool_call.get('tool_name')}")
    print(f"  Query params: {tool_call.get('query_params', 'N/A')[:100]}...")
    print(f"  Duration: {tool_call.get('duration_ms', 0):.2f}ms")
    print(f"  Success: {tool_call.get('success', False)}")

    assert 'notebooklm' in tool_name or 'notebook' in tool_name or 'knowledge' in tool_name, \
        f"Wrong tool called: {tool_call.get('tool_name')} - expected NotebookLM"

    print(f"✓ Correct tool called: {tool_call.get('tool_name')}")

    # VAL-04: Verify this is a real tool call (not false positive)
    assert tool_call.get('tool_use_id') is not None, \
        "No tool_use_id - may be false positive"
    assert tool_call.get('start_time') is not None, \
        "No start_time - may be false positive"
    assert tool_call.get('end_time') is not None, \
        "No end_time - may be false positive"

    print(f"\n✓ VAL-04 PASSED: Tool call is verifiable (has ID, timestamps)")


@pytest.mark.integration
@pytest.mark.timeout(180)
@pytest.mark.asyncio
async def test_tool_knowledge_appears_in_output():
    """
    Verify that knowledge returned from tool actually appears in generated output.

    This proves the Agent not only CALLS the tool but also USES the returned knowledge.

    Success criteria:
    - Tool is called (tool_call_count > 0)
    - Tool returns non-empty result
    - Some portion of tool result appears in final output
    """
    # Get API configuration
    api_key = os.getenv("ANTHROPIC_API_KEY")
    notebook_id = os.getenv("NOTEBOOK_ID")

    if not api_key or not notebook_id:
        pytest.skip("API credentials not available")

    print(f"\n{'='*70}")
    print("Test: Tool Knowledge Appears in Output")
    print(f"{'='*70}")

    # Create runner
    runner = AgentSDKRunner(
        api_key=api_key,
        model=os.getenv("ANTHROPIC_MODEL", "MiniMax-M2.1"),
        temperature=0.7,
        notebook_id=notebook_id
    )

    # Topic requiring specific knowledge
    topic = "写一篇关于人工智能产品经理的文章"
    search_results = []  # Empty to force tool calling

    system_prompt = """你是一个智能写作助手。

当需要素材时，使用NotebookLM工具查询知识库。
使用查询到的知识撰写文章。"""

    print(f"\nRunning generation with tool calling...")
    result_text, metrics = await asyncio.wait_for(
        runner.generate(
            topic=topic,
            search_results=search_results,
            system_prompt=system_prompt,
            max_turns=5
        ),
        timeout=120.0
    )

    print(f"\nResults:")
    print(f"  Tool calls: {metrics.tool_call_count}")
    print(f"  Result length: {len(result_text)} chars")

    # Verify tool was called
    assert metrics.tool_call_count > 0, "No tool calls made"

    # Get tool results
    tool_results = []
    for tool_call in metrics.tool_calls:
        result = tool_call.get('result')
        if result and isinstance(result, str) and len(result) > 10:
            tool_results.append(result)
        elif result and isinstance(result, dict):
            # Handle structured result
            result_str = str(result)
            if len(result_str) > 10:
                tool_results.append(result_str)

    print(f"\nTool results found: {len(tool_results)}")

    if not tool_results:
        pytest.skip("Tool returned empty results - cannot verify knowledge usage")

    # Check if any tool result content appears in output
    # We look for substantial overlap (not just single words)
    knowledge_used = False
    for tool_result in tool_results:
        # Extract key phrases from tool result (>5 chars)
        result_phrases = [phrase.strip() for phrase in tool_result.split() if len(phrase.strip()) > 5]

        # Check how many phrases appear in output
        matches = sum(1 for phrase in result_phrases[:20] if phrase in result_text)  # Check first 20 phrases

        if matches >= 3:  # At least 3 key phrases from tool result appear in output
            knowledge_used = True
            print(f"\n✓ Knowledge used: {matches} key phrases from tool result appear in output")
            break

    assert knowledge_used, \
        "Tool was called but knowledge does not appear in output - Agent may not be using tool results"

    print(f"✓ Tool knowledge verified in output")


@pytest.mark.integration
@pytest.mark.timeout(180)
@pytest.mark.asyncio
async def test_tool_call_metrics_complete():
    """
    VAL-03: Verify that tool call metrics contain all required fields.

    This test ensures that when a tool is called, comprehensive metrics
    are captured for debugging and verification.

    Required fields:
    - tool_name
    - tool_use_id
    - input / query_params
    - start_time / end_time / duration_ms
    - result / result_summary / result_length
    - success (bool)
    """
    # Get API configuration
    api_key = os.getenv("ANTHROPIC_API_KEY")
    notebook_id = os.getenv("NOTEBOOK_ID")

    if not api_key or not notebook_id:
        pytest.skip("API credentials not available")

    print(f"\n{'='*70}")
    print("Test: Tool Call Metrics Complete")
    print(f"{'='*70}")

    # Create runner
    runner = AgentSDKRunner(
        api_key=api_key,
        model=os.getenv("ANTHROPIC_MODEL", "MiniMax-M2.1"),
        temperature=0.7,
        notebook_id=notebook_id
    )

    # Simple topic to trigger tool call
    topic = "查询我的创业经历并写一篇文章"
    search_results = []

    system_prompt = """你是一个智能写作助手。当需要素材时，使用NotebookLM工具查询知识库。"""

    print(f"\nRunning generation...")
    result_text, metrics = await asyncio.wait_for(
        runner.generate(
            topic=topic,
            search_results=search_results,
            system_prompt=system_prompt,
            max_turns=5
        ),
        timeout=120.0
    )

    print(f"\nTool calls: {metrics.tool_call_count}")

    # Verify at least one tool call
    assert metrics.tool_call_count > 0, "No tool calls to verify metrics"

    # Check each tool call has required fields
    required_fields = [
        'tool_name',
        'tool_use_id',
        'start_time',
        'end_time',
        'duration_ms',
        'result',
        'success'
    ]

    for i, tool_call in enumerate(metrics.tool_calls, 1):
        print(f"\nTool call {i}:")

        for field in required_fields:
            assert field in tool_call, f"Tool call {i} missing required field: {field}"
            print(f"  ✓ {field}: {str(tool_call[field])[:50]}...")

        # Verify field types and values
        assert isinstance(tool_call['tool_name'], str), "tool_name must be string"
        assert isinstance(tool_call['tool_use_id'], str), "tool_use_id must be string"
        assert isinstance(tool_call['start_time'], (int, float)), "start_time must be numeric"
        assert isinstance(tool_call['end_time'], (int, float)), "end_time must be numeric"
        assert isinstance(tool_call['duration_ms'], (int, float)), "duration_ms must be numeric"
        assert isinstance(tool_call['success'], bool), "success must be boolean"

        # Verify duration makes sense
        assert tool_call['duration_ms'] > 0, "duration_ms must be positive"
        assert tool_call['end_time'] >= tool_call['start_time'], "end_time must be >= start_time"

        # VAL-03: Check optional but recommended fields
        optional_fields = ['query_params', 'result_summary', 'result_length']
        for field in optional_fields:
            if field in tool_call:
                print(f"  ✓ {field}: {str(tool_call[field])[:50]}...")

    print(f"\n✓ VAL-03 PASSED: All required metrics fields present and valid")


@pytest.mark.integration
@pytest.mark.timeout(180)
@pytest.mark.asyncio
async def test_multiple_tool_calls_in_sequence():
    """
    Test that Agent can make multiple tool calls in a single session.

    This verifies that tool calling mechanism works repeatedly, not just once.

    Success criteria:
    - Multiple tool calls made (tool_call_count >= 2)
    - Each call has unique tool_use_id
    - All calls properly logged
    """
    # Get API configuration
    api_key = os.getenv("ANTHROPIC_API_KEY")
    notebook_id = os.getenv("NOTEBOOK_ID")

    if not api_key or not notebook_id:
        pytest.skip("API credentials not available")

    print(f"\n{'='*70}")
    print("Test: Multiple Tool Calls in Sequence")
    print(f"{'='*70}")

    # Create runner
    runner = AgentSDKRunner(
        api_key=api_key,
        model=os.getenv("ANTHROPIC_MODEL", "MiniMax-M2.1"),
        temperature=0.7,
        notebook_id=notebook_id
    )

    # Topic that may require multiple queries
    topic = "写一篇关于我创业经历和产品设计理念的文章"
    search_results = []

    system_prompt = """你是一个智能写作助手。

当需要素材时，使用NotebookLM工具查询知识库。
你可以进行多次查询以获取充分的信息。"""

    print(f"\nRunning generation with potential for multiple tool calls...")
    result_text, metrics = await asyncio.wait_for(
        runner.generate(
            topic=topic,
            search_results=search_results,
            system_prompt=system_prompt,
            max_turns=10  # Allow more turns for multiple calls
        ),
        timeout=180.0
    )

    print(f"\nResults:")
    print(f"  Tool calls: {metrics.tool_call_count}")
    print(f"  Result length: {len(result_text)} chars")

    # Note: We don't strictly require multiple calls (depends on Agent's decision)
    # But if multiple calls were made, verify they're properly tracked
    if metrics.tool_call_count >= 2:
        print(f"\n✓ Multiple tool calls detected: {metrics.tool_call_count}")

        # Verify each call has unique tool_use_id
        tool_use_ids = [call.get('tool_use_id') for call in metrics.tool_calls]
        assert len(tool_use_ids) == len(set(tool_use_ids)), \
            "Tool calls have duplicate tool_use_ids"

        # Print each call
        for i, call in enumerate(metrics.tool_calls, 1):
            print(f"\n  Call {i}:")
            print(f"    Tool: {call.get('tool_name')}")
            print(f"    ID: {call.get('tool_use_id')}")
            print(f"    Query: {call.get('query_params', 'N/A')[:50]}...")
            print(f"    Duration: {call.get('duration_ms', 0):.2f}ms")

        print(f"\n✓ All tool calls properly tracked with unique IDs")
    else:
        print(f"\nNote: Only {metrics.tool_call_count} tool call(s) made")
        print("  This is acceptable - Agent decides when to query based on need")

    # At minimum, verify at least one tool call
    assert metrics.tool_call_count > 0, "No tool calls made"


@pytest.mark.integration
@pytest.mark.timeout(60)
@pytest.mark.asyncio
async def test_no_tool_call_when_materials_provided():
    """
    Test that Agent does NOT call tools when sufficient materials are provided.

    This verifies that tool calling is CONDITIONAL - only when needed.

    Success criteria:
    - tool_call_count == 0 (no tools called)
    - Article still generated successfully
    """
    # Get API configuration
    api_key = os.getenv("ANTHROPIC_API_KEY")
    notebook_id = os.getenv("NOTEBOOK_ID")

    if not api_key or not notebook_id:
        pytest.skip("API credentials not available")

    print(f"\n{'='*70}")
    print("Test: No Tool Call When Materials Provided")
    print(f"{'='*70}")

    # Create runner
    runner = AgentSDKRunner(
        api_key=api_key,
        model=os.getenv("ANTHROPIC_MODEL", "MiniMax-M2.1"),
        temperature=0.7,
        notebook_id=notebook_id
    )

    # Create a simple mock SearchResult class
    class MockSearchResult:
        def __init__(self, content, source):
            self.content = content
            self.source = source

    # Provide sufficient materials
    topic = "写一篇关于人工智能的文章"
    search_results = [
        MockSearchResult(
            content="人工智能是计算机科学的一个分支，致力于开发能够执行通常需要人类智能的任务的系统。",
            source="AI基础知识"
        ),
        MockSearchResult(
            content="机器学习是人工智能的核心技术之一，通过数据训练模型来实现智能行为。",
            source="机器学习概述"
        )
    ]

    system_prompt = """你是一个智能写作助手。

当用户提供了充分素材时，直接基于素材撰写。
只有在素材不足时才使用NotebookLM工具查询知识库。"""

    print(f"\nRunning generation with provided materials...")
    print(f"  Search results: {len(search_results)} items provided")

    result_text, metrics = await asyncio.wait_for(
        runner.generate(
            topic=topic,
            search_results=search_results,
            system_prompt=system_prompt,
            max_turns=5
        ),
        timeout=60.0
    )

    print(f"\nResults:")
    print(f"  Tool calls: {metrics.tool_call_count}")
    print(f"  Result length: {len(result_text)} chars")

    # Verify no tool calls were made
    assert metrics.tool_call_count == 0, \
        f"Agent made {metrics.tool_call_count} tool call(s) despite having materials"

    # Verify article was still generated
    assert len(result_text) > 0, "No output generated"

    print(f"\n✓ Correct behavior: No tool calls when materials provided")
    print(f"✓ Article generated successfully: {len(result_text)} chars")
