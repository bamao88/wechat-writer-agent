"""测试日志文档生成器"""
import pytest
import time
import json
from datetime import datetime
from src.hooks.log_generator import LogDocumentGenerator
from src.modules.agent_sdk import AgentRunMetrics


class TestLogDocumentGenerator:
    """测试 LogDocumentGenerator 类"""

    def test_generate_markdown_basic_structure(self):
        """测试生成markdown的基本结构"""
        topic = "测试主题"
        metrics = AgentRunMetrics()
        metrics.end_time = metrics.start_time + 10.5  # 10.5秒

        generator = LogDocumentGenerator(topic, metrics)
        markdown = generator.generate_markdown()

        # 验证包含标题
        assert "# Agent Run Log" in markdown
        # 验证包含topic
        assert "测试主题" in markdown
        # 验证包含运行时长
        assert "10.5" in markdown or "10.50" in markdown

    def test_markdown_includes_topic(self):
        """测试markdown包含topic"""
        topic = "产品经理如何做技术选型"
        metrics = AgentRunMetrics()

        generator = LogDocumentGenerator(topic, metrics)
        markdown = generator.generate_markdown()

        assert "产品经理如何做技术选型" in markdown

    def test_markdown_includes_metrics_summary(self):
        """测试markdown包含指标摘要"""
        metrics = AgentRunMetrics()
        metrics.total_tokens = 3245
        metrics.prompt_tokens = 1520
        metrics.completion_tokens = 1725
        metrics.end_time = metrics.start_time + 87.43

        generator = LogDocumentGenerator("测试", metrics)
        markdown = generator.generate_markdown()

        # 验证包含tokens信息
        assert "3245" in markdown
        assert "1520" in markdown
        assert "1725" in markdown
        # 验证包含运行时长
        assert "87.43" in markdown

    def test_markdown_tool_calls_section(self):
        """测试markdown包含工具调用章节"""
        metrics = AgentRunMetrics()
        metrics.tool_calls = [
            {
                'tool_name': 'query_notebooklm',
                'tool_use_id': 'toolu_01abc123',
                'input': {'question': '测试问题'},
                'result': '测试结果内容',
                'duration_ms': 2345.67,
                'start_time': time.time()
            }
        ]

        generator = LogDocumentGenerator("测试", metrics)
        markdown = generator.generate_markdown()

        # 验证包含工具调用信息
        assert "query_notebooklm" in markdown
        assert "toolu_01abc123" in markdown
        assert "2345.67" in markdown
        assert "测试问题" in markdown

    def test_markdown_errors_section(self):
        """测试markdown包含错误章节"""
        metrics = AgentRunMetrics()
        metrics.errors = [
            "Error 1: Something went wrong",
            "Error 2: Another issue"
        ]

        generator = LogDocumentGenerator("测试", metrics)
        markdown = generator.generate_markdown()

        # 验证包含错误信息
        assert "## Errors" in markdown or "## 错误" in markdown
        assert "Error 1: Something went wrong" in markdown
        assert "Error 2: Another issue" in markdown

    def test_json_formatting_in_markdown(self):
        """测试JSON格式化"""
        metrics = AgentRunMetrics()
        metrics.tool_calls = [
            {
                'tool_name': 'test_tool',
                'tool_use_id': 'test-id',
                'input': {'key1': 'value1', 'key2': 'value2'},
                'duration_ms': 100
            }
        ]

        generator = LogDocumentGenerator("测试", metrics)
        markdown = generator.generate_markdown()

        # 验证包含JSON格式（带缩进）
        assert "```json" in markdown
        assert '"key1"' in markdown or "'key1'" in markdown

    def test_result_preview_truncation(self):
        """测试结果预览截断（限制500字符）"""
        long_result = "A" * 1000  # 1000个字符
        metrics = AgentRunMetrics()
        metrics.tool_calls = [
            {
                'tool_name': 'test_tool',
                'tool_use_id': 'test-id',
                'input': {},
                'result': long_result,
                'duration_ms': 100
            }
        ]

        generator = LogDocumentGenerator("测试", metrics)
        markdown = generator.generate_markdown()

        # 验证结果被截断（应该包含...或者截断标记）
        # 结果不应该包含完整的1000个A
        assert markdown.count('A') <= 510  # 500 + 一些容差

    def test_handles_empty_metrics(self):
        """测试处理空指标"""
        metrics = AgentRunMetrics()
        # 不添加任何工具调用或错误

        generator = LogDocumentGenerator("空测试", metrics)
        markdown = generator.generate_markdown()

        # 应该仍然能生成文档，不报错
        assert "# Agent Run Log" in markdown
        assert "空测试" in markdown
        assert "0" in markdown  # 工具调用次数为0
