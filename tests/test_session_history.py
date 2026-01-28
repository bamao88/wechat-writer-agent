"""测试会话历史格式和多轮对话处理"""
import pytest
from unittest.mock import MagicMock
from src.modules.agent_sdk import AgentRunMetrics


@pytest.mark.timeout(10)
class TestSessionHistoryFormat:
    """测试会话历史记录格式"""

    def test_multi_turn_with_tool_calls(self):
        """测试包含工具调用的多轮对话"""
        metrics = AgentRunMetrics()

        # 模拟对话流程:
        # 1. 用户初始消息
        metrics.conversation_history.append({
            "role": "user",
            "content": [{"type": "text", "text": "检索关于AI的信息"}],
            "timestamp": 1000.0
        })

        # 2. 助手响应 - 包含thinking和tool_use
        metrics.add_assistant_message(
            content_blocks=[
                {"type": "thinking", "thinking": "需要检索NotebookLM"},
                {"type": "tool_use", "id": "toolu_01", "name": "notebooklm_query", "input": {"query": "AI"}}
            ],
            stop_reason="tool_use"
        )

        # 3. 工具结果返回
        metrics.add_tool_result("toolu_01", "AI是人工智能的简称...")

        # 4. 助手最终响应
        metrics.add_assistant_message(
            content_blocks=[
                {"type": "text", "text": "根据检索结果，AI是..."}
            ],
            stop_reason="end_turn"
        )

        # 验证消息顺序和类型
        assert len(metrics.conversation_history) == 4
        assert metrics.conversation_history[0]["role"] == "user"
        assert metrics.conversation_history[1]["role"] == "assistant"
        assert metrics.conversation_history[1]["stop_reason"] == "tool_use"
        assert metrics.conversation_history[2]["role"] == "user"
        assert metrics.conversation_history[2]["content"][0]["type"] == "tool_result"
        assert metrics.conversation_history[3]["role"] == "assistant"
        assert metrics.conversation_history[3]["stop_reason"] == "end_turn"

    def test_history_format_with_thinking(self):
        """测试thinking内容的记录和统计"""
        metrics = AgentRunMetrics()

        # 添加包含thinking的助手消息
        metrics.add_assistant_message(
            content_blocks=[
                {"type": "thinking", "thinking": "我需要仔细思考..."},
                {"type": "text", "text": "答案是..."}
            ]
        )

        # 验证thinking被正确记录
        assert len(metrics.conversation_history) == 1
        content = metrics.conversation_history[0]["content"]
        thinking_blocks = [b for b in content if b.get("type") == "thinking"]
        assert len(thinking_blocks) == 1
        assert "思考" in thinking_blocks[0]["thinking"]

        # 验证get_history_summary正确识别thinking
        summary = metrics.get_history_summary()
        assert summary["has_thinking"] is True
        assert summary["total_messages"] == 1
        assert summary["assistant_messages"] == 1

    def test_tool_result_format(self):
        """测试tool_result消息格式"""
        metrics = AgentRunMetrics()

        # 测试各种类型的工具结果
        test_cases = [
            ("toolu_01", "字符串结果"),
            ("toolu_02", {"data": "字典结果"}),
            ("toolu_03", ["列表", "结果"]),
            ("toolu_04", 123),
        ]

        for tool_use_id, result in test_cases:
            metrics.add_tool_result(tool_use_id, result)

        # 验证所有tool_result都被正确格式化
        assert len(metrics.conversation_history) == 4
        for i, (tool_use_id, result) in enumerate(test_cases):
            msg = metrics.conversation_history[i]
            assert msg["role"] == "user"
            assert len(msg["content"]) == 1
            content_block = msg["content"][0]
            assert content_block["type"] == "tool_result"
            assert content_block["tool_use_id"] == tool_use_id
            assert content_block["content"] == str(result)
            assert "timestamp" in msg

    def test_history_summary_accuracy(self):
        """测试历史摘要统计准确性"""
        metrics = AgentRunMetrics()

        # 构建已知的对话历史
        # 2个用户消息
        metrics.conversation_history.append({"role": "user", "content": []})
        metrics.add_tool_result("toolu_01", "result")

        # 3个助手消息
        metrics.add_assistant_message([{"type": "text", "text": "msg1"}])
        metrics.add_assistant_message([
            {"type": "thinking", "thinking": "思考中"},
            {"type": "tool_use", "id": "toolu_01", "name": "query"}
        ])
        metrics.add_assistant_message([{"type": "text", "text": "msg2"}])

        summary = metrics.get_history_summary()

        # 验证统计准确性
        assert summary["total_messages"] == 5
        assert summary["user_messages"] == 2
        assert summary["assistant_messages"] == 3
        assert summary["tool_result_count"] == 1
        assert summary["has_thinking"] is True
        assert summary["has_tool_calls"] is True

    def test_conversation_context_preservation(self):
        """测试多轮对话中上下文保留"""
        metrics = AgentRunMetrics()

        # 模拟3轮对话
        rounds = [
            ("用户: 第1轮问题", "助手: 第1轮回答"),
            ("用户: 第2轮问题", "助手: 第2轮回答"),
            ("用户: 第3轮问题", "助手: 第3轮回答"),
        ]

        for user_msg, assistant_msg in rounds:
            metrics.conversation_history.append({
                "role": "user",
                "content": [{"type": "text", "text": user_msg}]
            })
            metrics.add_assistant_message([
                {"type": "text", "text": assistant_msg}
            ])

        # 验证历史保留了所有轮次
        assert len(metrics.conversation_history) == 6  # 3轮 × 2条消息

        # 验证消息顺序正确
        for i in range(3):
            user_idx = i * 2
            assistant_idx = i * 2 + 1
            assert metrics.conversation_history[user_idx]["role"] == "user"
            assert metrics.conversation_history[assistant_idx]["role"] == "assistant"
            assert f"第{i+1}轮" in metrics.conversation_history[user_idx]["content"][0]["text"]
            assert f"第{i+1}轮" in metrics.conversation_history[assistant_idx]["content"][0]["text"]

        # 验证早期消息仍然存在
        first_user_msg = metrics.conversation_history[0]
        assert first_user_msg["role"] == "user"
        assert "第1轮问题" in first_user_msg["content"][0]["text"]


@pytest.mark.timeout(10)
class TestHistorySummaryEdgeCases:
    """测试历史摘要边界情况"""

    def test_empty_history(self):
        """测试空历史记录"""
        metrics = AgentRunMetrics()
        summary = metrics.get_history_summary()

        assert summary["total_messages"] == 0
        assert summary["user_messages"] == 0
        assert summary["assistant_messages"] == 0
        assert summary["tool_result_count"] == 0
        assert summary["has_thinking"] is False
        assert summary["has_tool_calls"] is False

    def test_history_without_tool_calls(self):
        """测试无工具调用的对话"""
        metrics = AgentRunMetrics()

        metrics.conversation_history.append({"role": "user", "content": []})
        metrics.add_assistant_message([{"type": "text", "text": "纯文本回答"}])

        summary = metrics.get_history_summary()

        assert summary["total_messages"] == 2
        assert summary["has_tool_calls"] is False
        assert summary["tool_result_count"] == 0

    def test_history_without_thinking(self):
        """测试无thinking内容的对话"""
        metrics = AgentRunMetrics()

        metrics.conversation_history.append({"role": "user", "content": []})
        metrics.add_assistant_message([{"type": "text", "text": "直接回答"}])

        summary = metrics.get_history_summary()

        assert summary["has_thinking"] is False

    def test_multiple_tool_results_in_one_message(self):
        """测试单条消息包含多个tool_result"""
        metrics = AgentRunMetrics()

        # 手动构建包含多个tool_result的消息
        metrics.conversation_history.append({
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "toolu_01", "content": "result1"},
                {"type": "tool_result", "tool_use_id": "toolu_02", "content": "result2"},
            ]
        })

        summary = metrics.get_history_summary()
        assert summary["tool_result_count"] == 2
