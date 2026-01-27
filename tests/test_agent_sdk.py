"""测试 Claude Agent SDK 集成模块"""
import pytest
import time
from unittest.mock import Mock, AsyncMock, patch
from src.modules.agent_sdk import AgentRunMetrics


class TestAgentRunMetrics:
    """测试 AgentRunMetrics 数据类"""

    def test_initial_state(self):
        """测试初始状态"""
        metrics = AgentRunMetrics()

        assert metrics.start_time > 0
        assert metrics.end_time is None
        assert metrics.tool_calls == []
        assert metrics.total_tokens == 0
        assert metrics.prompt_tokens == 0
        assert metrics.completion_tokens == 0
        assert metrics.errors == []

    def test_runtime_seconds_calculation_without_end_time(self):
        """测试运行时长计算（未结束）"""
        metrics = AgentRunMetrics()
        time.sleep(0.1)  # 等待100ms

        runtime = metrics.runtime_seconds

        assert runtime >= 0.1
        assert runtime < 0.2  # 应该在0.1到0.2秒之间

    def test_runtime_seconds_calculation_with_end_time(self):
        """测试运行时长计算（已结束）"""
        start = time.time()
        metrics = AgentRunMetrics()
        metrics.start_time = start
        metrics.end_time = start + 1.5  # 1.5秒后

        assert metrics.runtime_seconds == 1.5

    def test_tool_call_count_property(self):
        """测试工具调用次数属性"""
        metrics = AgentRunMetrics()

        # 初始为0
        assert metrics.tool_call_count == 0

        # 添加工具调用
        metrics.tool_calls.append({'tool_name': 'test1'})
        metrics.tool_calls.append({'tool_name': 'test2'})
        metrics.tool_calls.append({'tool_name': 'test3'})

        assert metrics.tool_call_count == 3

    def test_tool_calls_list_is_mutable(self):
        """测试tool_calls列表可修改"""
        metrics = AgentRunMetrics()

        tool_call = {
            'tool_name': 'query_notebooklm',
            'tool_use_id': 'test-id',
            'start_time': time.time()
        }

        metrics.tool_calls.append(tool_call)

        assert len(metrics.tool_calls) == 1
        assert metrics.tool_calls[0]['tool_name'] == 'query_notebooklm'

    def test_errors_list_is_mutable(self):
        """测试errors列表可修改"""
        metrics = AgentRunMetrics()

        metrics.errors.append("Test error 1")
        metrics.errors.append("Test error 2")

        assert len(metrics.errors) == 2
        assert "Test error 1" in metrics.errors
