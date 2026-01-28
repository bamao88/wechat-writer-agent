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
from typing import Dict, Any, Optional, List


class ToolCallLifecycleLogger:
    """工具调用生命周期日志记录器

    记录工具调用的完整生命周期: registration → call_start → execution → response → error
    满足 ERR-04 需求: 提供完整的可观测性
    """

    PHASES = ["registration", "call_start", "execution", "response", "error"]

    def __init__(self, tool_name: str, tool_use_id: str):
        """
        初始化生命周期记录器

        Args:
            tool_name: 工具名称
            tool_use_id: 工具调用唯一ID
        """
        self.tool_name = tool_name
        self.tool_use_id = tool_use_id
        self.start_time = time.time()
        self.phases_logged: List[Dict[str, Any]] = []

    def log_phase(self, phase: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        记录生命周期阶段

        Args:
            phase: 阶段名称，必须在 PHASES 中
            details: 阶段详情（可选）

        Raises:
            ValueError: phase 不在 PHASES 中
        """
        if phase not in self.PHASES:
            raise ValueError(f"Invalid phase '{phase}'. Must be one of {self.PHASES}")

        timestamp = time.time()
        elapsed = timestamp - self.start_time

        # 记录阶段信息
        phase_record = {
            "phase": phase,
            "timestamp": timestamp,
            "elapsed": elapsed,
            "details": details or {}
        }
        self.phases_logged.append(phase_record)

        # 格式化日志输出
        log_parts = [
            f"[TOOL-LIFECYCLE] {self.tool_name}",
            f"ID: {self.tool_use_id}",
            f"Phase: {phase}"
        ]

        # 添加详情到日志
        if details:
            for key, value in details.items():
                # 截断过长的值
                value_str = str(value)
                if len(value_str) > 100:
                    value_str = value_str[:100] + "..."
                log_parts.append(f"{key}: {value_str}")

        print(" | ".join(log_parts))


async def pre_tool_use_hook(
    input_data: Dict[str, Any],
    tool_use_id: Optional[str],
    context: Any,
    metrics: Any
) -> Dict[str, Any]:
    """
    PreToolUse Hook: 工具调用前触发

    记录工具名称、输入参数、开始时间
    记录生命周期阶段: registration, call_start

    Args:
        input_data: 包含tool_name和tool_input的字典
        tool_use_id: 工具使用ID
        context: 上下文对象
        metrics: AgentRunMetrics实例

    Returns:
        空字典（不阻塞执行）
    """
    tool_name = input_data.get('tool_name')
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
        'tool_name': tool_name,
        'tool_use_id': tool_use_id,
        'input': tool_input,
        'query_params': query_params,
        'invocation_reason': invocation_reason,
        'timestamp': time.time(),
        'start_time': time.time()
    }

    metrics.tool_calls.append(tool_call_record)

    # 创建生命周期记录器并记录 registration 和 call_start 阶段
    lifecycle_logger = ToolCallLifecycleLogger(tool_name, tool_use_id)
    lifecycle_logger.log_phase("registration")
    lifecycle_logger.log_phase("call_start", {"Input": str(tool_input)[:200]})

    # 将 lifecycle_logger 存储在 tool_call_record 中，供 post_tool_use_hook 使用
    tool_call_record['lifecycle_logger'] = lifecycle_logger

    # Log more detail (保持现有日志格式)
    print(f"[PRE-TOOL] {tool_name} - ID: {tool_use_id}")
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
    记录生命周期阶段: execution, response, error

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
    record = None
    lifecycle_logger = None
    for rec in metrics.tool_calls:
        if rec.get('tool_use_id') == tool_use_id:
            record = rec
            rec['end_time'] = time.time()
            rec['duration_ms'] = (rec['end_time'] - rec['start_time']) * 1000
            rec['result'] = tool_response
            rec['result_summary'] = result_summary
            rec['result_length'] = result_length
            rec['success'] = success

            # 获取生命周期记录器
            lifecycle_logger = rec.get('lifecycle_logger')
            break

    # 使用生命周期记录器记录 execution, response 或 error 阶段
    if lifecycle_logger:
        duration_s = record.get('duration_ms', 0) / 1000
        lifecycle_logger.log_phase("execution", {"Duration": f"{duration_s:.2f}s"})

        if success:
            lifecycle_logger.log_phase(
                "response",
                {"Success": True, "Length": result_length}
            )
        else:
            # 提取错误信息
            error_msg = "Unknown error"
            stderr = None
            if isinstance(tool_response, dict):
                error_msg = tool_response.get('error', error_msg)
                stderr = tool_response.get('stderr')
            elif isinstance(tool_response, str):
                error_msg = tool_response[:200]

            lifecycle_logger.log_phase(
                "error",
                {"Error": error_msg, "Stderr": stderr if stderr else "N/A"}
            )

            # 记录工具失败到 metrics (如果 metrics 有 add_tool_failure 方法)
            if hasattr(metrics, 'add_tool_failure'):
                tool_name = record.get('tool_name', 'Unknown')
                metrics.add_tool_failure(tool_name, tool_use_id, error_msg, stderr)

    # 保持现有日志格式
    print(f"[POST-TOOL] {input_data.get('tool_name')} completed")
    if record:
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
