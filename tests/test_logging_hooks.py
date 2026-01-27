"""测试Logging Hooks"""
import pytest
import time
from src.hooks.logging_hooks import (
    pre_tool_use_hook,
    post_tool_use_hook,
    stop_hook,
    user_prompt_submit_hook
)
from src.modules.agent_sdk import AgentRunMetrics


class TestLoggingHooks:
    """测试所有logging hooks"""

    @pytest.mark.asyncio
    async def test_pre_tool_use_hook_records_data(self):
        """测试pre_tool_use_hook记录数据"""
        metrics = AgentRunMetrics()
        input_data = {
            'hook_event_name': 'PreToolUse',
            'tool_name': 'query_notebooklm',
            'tool_input': {'question': '测试问题'}
        }

        result = await pre_tool_use_hook(input_data, 'test-id-123', None, metrics)

        # 验证返回空dict
        assert result == {}
        # 验证记录了工具调用
        assert len(metrics.tool_calls) == 1
        assert metrics.tool_calls[0]['tool_name'] == 'query_notebooklm'
        assert metrics.tool_calls[0]['tool_use_id'] == 'test-id-123'
        assert metrics.tool_calls[0]['input'] == {'question': '测试问题'}

    @pytest.mark.asyncio
    async def test_pre_tool_use_hook_returns_empty_dict(self):
        """测试pre_tool_use_hook返回空dict（不阻塞）"""
        metrics = AgentRunMetrics()
        input_data = {
            'tool_name': 'test_tool',
            'tool_input': {}
        }

        result = await pre_tool_use_hook(input_data, 'test-id', None, metrics)

        assert result == {}
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_post_tool_use_hook_updates_record(self):
        """测试post_tool_use_hook更新记录"""
        metrics = AgentRunMetrics()

        # 先添加一个pre记录
        start_time = time.time()
        metrics.tool_calls.append({
            'tool_name': 'test_tool',
            'tool_use_id': 'test-id-456',
            'input': {},
            'start_time': start_time
        })

        # 模拟post hook
        input_data = {
            'hook_event_name': 'PostToolUse',
            'tool_name': 'test_tool',
            'tool_response': '测试结果'
        }

        result = await post_tool_use_hook(input_data, 'test-id-456', None, metrics)

        # 验证返回空dict
        assert result == {}
        # 验证更新了记录
        assert 'end_time' in metrics.tool_calls[0]
        assert 'duration_ms' in metrics.tool_calls[0]
        assert metrics.tool_calls[0]['result'] == '测试结果'

    @pytest.mark.asyncio
    async def test_post_tool_use_hook_calculates_duration(self):
        """测试post_tool_use_hook计算耗时"""
        metrics = AgentRunMetrics()

        # 添加pre记录
        start_time = time.time()
        metrics.tool_calls.append({
            'tool_name': 'test_tool',
            'tool_use_id': 'test-id-789',
            'start_time': start_time
        })

        # 等待一小段时间
        time.sleep(0.1)

        # 调用post hook
        input_data = {
            'tool_name': 'test_tool',
            'tool_response': 'result'
        }

        await post_tool_use_hook(input_data, 'test-id-789', None, metrics)

        # 验证duration_ms大于100ms
        assert metrics.tool_calls[0]['duration_ms'] >= 100

    @pytest.mark.asyncio
    async def test_stop_hook_marks_end_time(self):
        """测试stop_hook标记结束时间"""
        metrics = AgentRunMetrics()
        assert metrics.end_time is None

        input_data = {
            'hook_event_name': 'Stop'
        }

        result = await stop_hook(input_data, None, None, metrics)

        # 验证返回空dict
        assert result == {}
        # 验证设置了end_time
        assert metrics.end_time is not None
        assert metrics.end_time > metrics.start_time

    @pytest.mark.asyncio
    async def test_stop_hook_prints_summary(self, capsys):
        """测试stop_hook打印摘要"""
        metrics = AgentRunMetrics()
        metrics.tool_calls = [{'tool_name': 'test1'}, {'tool_name': 'test2'}]
        metrics.end_time = metrics.start_time + 5.5

        input_data = {'hook_event_name': 'Stop'}

        await stop_hook(input_data, None, None, metrics)

        # 验证有打印输出
        captured = capsys.readouterr()
        assert '[STOP]' in captured.out or 'completed' in captured.out.lower()

    @pytest.mark.asyncio
    async def test_user_prompt_submit_hook_logs_topic(self, capsys):
        """测试user_prompt_submit_hook记录topic"""
        metrics = AgentRunMetrics()
        input_data = {
            'hook_event_name': 'UserPromptSubmit',
            'prompt': '这是一个测试选题'
        }

        result = await user_prompt_submit_hook(input_data, None, None, metrics)

        # 验证返回空dict
        assert result == {}

        # 验证有打印输出
        captured = capsys.readouterr()
        assert 'USER-PROMPT' in captured.out or 'Topic' in captured.out

    @pytest.mark.asyncio
    async def test_metrics_shared_across_hooks(self):
        """测试metrics在hooks间共享"""
        metrics = AgentRunMetrics()

        # 第一个hook添加数据
        input_data1 = {
            'tool_name': 'tool1',
            'tool_input': {}
        }
        await pre_tool_use_hook(input_data1, 'id-1', None, metrics)

        # 第二个hook也能看到数据
        assert len(metrics.tool_calls) == 1

        # 第三个hook继续添加
        input_data2 = {
            'tool_name': 'tool2',
            'tool_input': {}
        }
        await pre_tool_use_hook(input_data2, 'id-2', None, metrics)

        # 验证共享状态
        assert len(metrics.tool_calls) == 2
        assert metrics.tool_call_count == 2
