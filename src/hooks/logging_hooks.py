"""Logging Hooks - Claude Agent SDK 生命周期钩子实现

WARNING: Async Safety Requirements
===================================
All hooks in this module MUST be async-safe to prevent blocking the SSE stream.

CRITICAL RULES:
1. ALL hooks are async functions (async def) - this is required for SDK compatibility
2. NEVER use synchronous input() or other blocking IO operations in hooks
3. Use print() for logging (non-blocking) - DO NOT use blocking file operations
4. Hooks should complete quickly (<100ms typical) to avoid stream delays

MiniMax Streaming Context:
- MiniMax M2.1 uses SSE (Server-Sent Events) for streaming responses
- Blocking operations freeze the async event loop
- Frozen event loop cannot process SSE chunks → connection timeout (60s)
- Use anyio.to_thread.run_sync() if you must call synchronous code

Reference: .planning/research/SDK与MiniMax流式传输实现的兼容性架构与工程解决方案深度报告.md
"""
import time
from typing import Dict, Any, Optional


async def pre_tool_use_hook(
    input_data: Dict[str, Any],
    tool_use_id: Optional[str],
    context: Any,
    metrics: Any
) -> Dict[str, Any]:
    """
    PreToolUse Hook: 工具调用前触发

    记录工具名称、输入参数、开始时间

    Args:
        input_data: 包含tool_name和tool_input的字典
        tool_use_id: 工具使用ID
        context: 上下文对象
        metrics: AgentRunMetrics实例

    Returns:
        空字典（不阻塞执行）
    """
    tool_input = input_data.get('tool_input', {})

    # Extract query parameters (for NotebookLM, this is the "question" field)
    query_params = None
    if isinstance(tool_input, dict):
        query_params = tool_input.get('question') or tool_input.get('query') or str(tool_input)

    # Extract invocation reason from context if available
    invocation_reason = None
    if context and hasattr(context, 'invocation_reason'):
        invocation_reason = context.invocation_reason

    tool_call_record = {
        'tool_name': input_data.get('tool_name'),
        'tool_use_id': tool_use_id,
        'input': tool_input,
        'query_params': query_params,
        'invocation_reason': invocation_reason,
        'timestamp': time.time(),
        'start_time': time.time()
    }

    metrics.tool_calls.append(tool_call_record)

    # Log more detail
    print(f"[PRE-TOOL] {tool_call_record['tool_name']} - ID: {tool_use_id}")
    if query_params:
        print(f"  Query: {query_params[:100]}...")

    return {}


async def post_tool_use_hook(
    input_data: Dict[str, Any],
    tool_use_id: Optional[str],
    context: Any,
    metrics: Any
) -> Dict[str, Any]:
    """
    PostToolUse Hook: 工具调用后触发

    更新对应记录的结束时间、耗时、结果

    Args:
        input_data: 包含tool_response的字典
        tool_use_id: 工具使用ID
        context: 上下文对象
        metrics: AgentRunMetrics实例

    Returns:
        空字典
    """
    tool_response = input_data.get('tool_response')

    # Calculate result summary and metadata
    result_summary = None
    result_length = 0
    success = False

    if tool_response:
        result_str = str(tool_response)
        result_length = len(result_str)
        result_summary = result_str[:200]  # First 200 chars for logging

        # Check if result is successful (not an error)
        success = True
        if isinstance(tool_response, dict):
            if tool_response.get('error') or tool_response.get('status') == 'error':
                success = False
        elif isinstance(tool_response, str):
            if tool_response.lower().startswith('error'):
                success = False

    # 找到对应的pre记录并更新
    for record in metrics.tool_calls:
        if record.get('tool_use_id') == tool_use_id:
            record['end_time'] = time.time()
            record['duration_ms'] = (record['end_time'] - record['start_time']) * 1000
            record['result'] = tool_response
            record['result_summary'] = result_summary
            record['result_length'] = result_length
            record['success'] = success
            break

    print(f"[POST-TOOL] {input_data.get('tool_name')} completed")
    print(f"  Duration: {record.get('duration_ms', 0):.2f}ms | Success: {success} | Result length: {result_length}")

    return {}


async def stop_hook(
    input_data: Dict[str, Any],
    tool_use_id: Optional[str],
    context: Any,
    metrics: Any
) -> Dict[str, Any]:
    """
    Stop Hook: Agent运行结束时触发

    标记结束时间，打印汇总统计

    Args:
        input_data: 钩子输入数据
        tool_use_id: 工具使用ID（通常为None）
        context: 上下文对象
        metrics: AgentRunMetrics实例

    Returns:
        空字典
    """
    metrics.end_time = time.time()

    print(f"[STOP] Agent run completed")
    print(f"  Tool calls: {metrics.tool_call_count}")
    print(f"  Runtime: {metrics.runtime_seconds:.2f}s")

    return {}


async def user_prompt_submit_hook(
    input_data: Dict[str, Any],
    tool_use_id: Optional[str],
    context: Any,
    metrics: Any
) -> Dict[str, Any]:
    """
    UserPromptSubmit Hook: 用户提交prompt时触发

    记录初始topic

    Args:
        input_data: 包含prompt的字典
        tool_use_id: 工具使用ID（通常为None）
        context: 上下文对象
        metrics: AgentRunMetrics实例

    Returns:
        空字典
    """
    prompt = input_data.get('prompt', '')
    print(f"[USER-PROMPT] Topic: {prompt[:100]}...")

    return {}


def get_tool_call_summary(metrics: Any) -> Dict[str, Any]:
    """
    Get summary statistics about tool calls from metrics.

    Args:
        metrics: AgentRunMetrics instance with tool_calls list

    Returns:
        Dict containing:
        - total_count: Total number of tool calls
        - tool_names: List of unique tool names called
        - average_duration_ms: Average duration across all calls
        - success_count: Number of successful calls
        - failure_count: Number of failed calls
    """
    if not hasattr(metrics, 'tool_calls') or not metrics.tool_calls:
        return {
            'total_count': 0,
            'tool_names': [],
            'average_duration_ms': 0,
            'success_count': 0,
            'failure_count': 0
        }

    tool_calls = metrics.tool_calls
    total_count = len(tool_calls)

    # Get unique tool names
    tool_names = list(set(call.get('tool_name') for call in tool_calls if call.get('tool_name')))

    # Calculate average duration
    durations = [call.get('duration_ms', 0) for call in tool_calls if 'duration_ms' in call]
    average_duration_ms = sum(durations) / len(durations) if durations else 0

    # Count successes and failures
    success_count = sum(1 for call in tool_calls if call.get('success', False))
    failure_count = total_count - success_count

    return {
        'total_count': total_count,
        'tool_names': tool_names,
        'average_duration_ms': average_duration_ms,
        'success_count': success_count,
        'failure_count': failure_count
    }
