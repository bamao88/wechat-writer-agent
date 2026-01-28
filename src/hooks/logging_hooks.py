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
    tool_call_record = {
        'tool_name': input_data.get('tool_name'),
        'tool_use_id': tool_use_id,
        'input': input_data.get('tool_input', {}),
        'timestamp': time.time(),
        'start_time': time.time()
    }

    metrics.tool_calls.append(tool_call_record)

    print(f"[PRE-TOOL] {tool_call_record['tool_name']} - ID: {tool_use_id}")

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
    # 找到对应的pre记录并更新
    for record in metrics.tool_calls:
        if record.get('tool_use_id') == tool_use_id:
            record['end_time'] = time.time()
            record['duration_ms'] = (record['end_time'] - record['start_time']) * 1000
            record['result'] = input_data.get('tool_response')
            break

    print(f"[POST-TOOL] {input_data.get('tool_name')} completed")

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
