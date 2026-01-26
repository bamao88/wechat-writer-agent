"""
WechatWriterAgent 集成测试
测试 Agent 与 NotebookLMTool 的集成

优先级: P1
"""
import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call

# 添加父目录到路径以导入模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from writer_agent import WechatWriterAgent, create_writer_agent
from notebooklm_tool import NotebookLMTool


class TestAgentInitialization:
    """测试 Agent 初始化"""

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    def test_agent_default_initialization(self, mock_exists, mock_anthropic):
        """测试默认参数创建 Agent"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key-123'

        agent = WechatWriterAgent()

        assert agent is not None
        assert agent.model == "claude-3-5-sonnet-20241022"
        assert agent.api_key == 'test-key-123'

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    def test_agent_custom_model(self, mock_exists, mock_anthropic):
        """测试自定义模型"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        agent = WechatWriterAgent(model="claude-opus-4")

        assert agent.model == "claude-opus-4"

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    def test_agent_with_notebook_id(self, mock_exists, mock_anthropic):
        """测试使用自定义 notebook_id 创建 Agent"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        agent = WechatWriterAgent(notebook_id="my_notebook")

        assert agent.notebooklm.notebook_id == "my_notebook"

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    def test_agent_with_notebook_url(self, mock_exists, mock_anthropic):
        """测试使用自定义 notebook_url 创建 Agent"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        url = "https://notebooklm.google.com/notebook/123"
        agent = WechatWriterAgent(notebook_url=url)

        assert agent.notebooklm.notebook_url == url

    @patch('notebooklm_tool.Path.exists')
    def test_agent_missing_api_key_env(self, mock_exists):
        """测试缺失 API Key 环境变量"""
        mock_exists.return_value = True

        if 'ANTHROPIC_API_KEY' in os.environ:
            del os.environ['ANTHROPIC_API_KEY']

        with pytest.raises(ValueError) as exc_info:
            WechatWriterAgent()

        assert "ANTHROPIC_API_KEY" in str(exc_info.value)

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    def test_agent_api_key_from_parameter(self, mock_exists, mock_anthropic):
        """测试从参数传入 API Key"""
        mock_exists.return_value = True

        agent = WechatWriterAgent(api_key="param-key")

        assert agent.api_key == "param-key"

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    def test_create_writer_agent_factory(self, mock_exists, mock_anthropic):
        """测试工厂函数"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        agent = create_writer_agent(notebook_id="test")

        assert isinstance(agent, WechatWriterAgent)
        assert agent.notebooklm.notebook_id == "test"


class TestToolCallHandling:
    """测试 Tool Call 处理"""

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_tool_call_execution(self, mock_run, mock_exists, mock_anthropic_class):
        """测试 Agent 在写作过程中调用 query_notebooklm"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        # Mock NotebookLM 查询
        mock_nb_result = Mock()
        mock_nb_result.returncode = 0
        mock_nb_result.stdout = "Question: test\n==========\n查询答案\n=========="
        mock_run.return_value = mock_nb_result

        # Mock Anthropic client
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # 第一次响应：tool_use
        mock_response_1 = Mock()
        mock_response_1.stop_reason = "tool_use"
        mock_tool = Mock()
        mock_tool.type = "tool_use"
        mock_tool.name = "query_notebooklm"
        mock_tool.input = {"question": "测试查询"}
        mock_tool.id = "tool_123"
        mock_response_1.content = [mock_tool]

        # 第二次响应：end_turn
        mock_response_2 = Mock()
        mock_response_2.stop_reason = "end_turn"
        mock_text = Mock()
        mock_text.text = "最终文章"
        mock_text.type = "text"
        mock_response_2.content = [mock_text]

        mock_client.messages.create.side_effect = [mock_response_1, mock_response_2]

        agent = WechatWriterAgent()
        result = agent.write_article(topic="测试")

        # 验证 tool 被调用
        assert mock_run.called
        assert result == "最终文章"

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    def test_tool_use_message_structure(self, mock_exists, mock_anthropic_class):
        """验证 tool_use 请求正确构造"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # 直接返回 end_turn
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_text = Mock()
        mock_text.text = "文章"
        mock_text.type = "text"
        mock_response.content = [mock_text]
        mock_client.messages.create.return_value = mock_response

        agent = WechatWriterAgent()
        agent.write_article(topic="测试")

        # 验证调用包含 tools 参数
        call_args = mock_client.messages.create.call_args
        assert 'tools' in call_args[1]
        tools = call_args[1]['tools']
        assert len(tools) > 0
        assert tools[0]['name'] == 'query_notebooklm'

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_tool_result_returned_to_claude(self, mock_run, mock_exists, mock_anthropic_class):
        """验证 tool_result 正确返回给 Claude"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        # Mock NotebookLM
        mock_nb_result = Mock()
        mock_nb_result.returncode = 0
        mock_nb_result.stdout = "Question: test\n==========\nNB答案\n=========="
        mock_run.return_value = mock_nb_result

        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # 第一次：tool_use
        mock_response_1 = Mock()
        mock_response_1.stop_reason = "tool_use"
        mock_tool = Mock()
        mock_tool.type = "tool_use"
        mock_tool.name = "query_notebooklm"
        mock_tool.input = {"question": "测试"}
        mock_tool.id = "tool_abc"
        mock_response_1.content = [mock_tool]

        # 第二次：end_turn
        mock_response_2 = Mock()
        mock_response_2.stop_reason = "end_turn"
        mock_text = Mock()
        mock_text.text = "文章"
        mock_text.type = "text"
        mock_response_2.content = [mock_text]

        mock_client.messages.create.side_effect = [mock_response_1, mock_response_2]

        agent = WechatWriterAgent()
        agent.write_article(topic="测试")

        # 验证第二次调用包含 tool_result
        assert mock_client.messages.create.call_count == 2
        second_call = mock_client.messages.create.call_args_list[1]
        messages = second_call[1]['messages']

        # 查找 tool_result 消息
        tool_result_msg = None
        for msg in messages:
            if msg['role'] == 'user' and isinstance(msg['content'], list):
                for content in msg['content']:
                    if isinstance(content, dict) and content.get('type') == 'tool_result':
                        tool_result_msg = content
                        break

        assert tool_result_msg is not None
        assert tool_result_msg['tool_use_id'] == "tool_abc"
        assert "NB答案" in tool_result_msg['content']


class TestMultiTurnConversation:
    """测试多轮对话"""

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_multiple_tool_calls(self, mock_run, mock_exists, mock_anthropic_class):
        """测试多次 tool call 的场景"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        # Mock NotebookLM
        mock_nb_result = Mock()
        mock_nb_result.returncode = 0
        mock_nb_result.stdout = "Question: test\n==========\n答案\n=========="
        mock_run.return_value = mock_nb_result

        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # 创建多轮响应
        responses = []

        # 第一轮：tool_use
        r1 = Mock()
        r1.stop_reason = "tool_use"
        t1 = Mock()
        t1.type = "tool_use"
        t1.name = "query_notebooklm"
        t1.input = {"question": "查询1"}
        t1.id = "tool_1"
        r1.content = [t1]
        responses.append(r1)

        # 第二轮：tool_use
        r2 = Mock()
        r2.stop_reason = "tool_use"
        t2 = Mock()
        t2.type = "tool_use"
        t2.name = "query_notebooklm"
        t2.input = {"question": "查询2"}
        t2.id = "tool_2"
        r2.content = [t2]
        responses.append(r2)

        # 第三轮：end_turn
        r3 = Mock()
        r3.stop_reason = "end_turn"
        txt = Mock()
        txt.text = "最终文章"
        txt.type = "text"
        r3.content = [txt]
        responses.append(r3)

        mock_client.messages.create.side_effect = responses

        agent = WechatWriterAgent()
        result = agent.write_article(topic="测试")

        # 验证多次调用
        assert mock_client.messages.create.call_count == 3
        assert mock_run.call_count == 2  # 两次 NotebookLM 查询

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    def test_max_turns_limit(self, mock_exists, mock_anthropic_class):
        """测试 Agent 的 10 轮对话限制"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # 始终返回 tool_use（模拟无限循环）
        mock_response = Mock()
        mock_response.stop_reason = "tool_use"
        mock_tool = Mock()
        mock_tool.type = "tool_use"
        mock_tool.name = "query_notebooklm"
        mock_tool.input = {"question": "test"}
        mock_tool.id = "tool_x"
        mock_response.content = [mock_tool]
        mock_client.messages.create.return_value = mock_response

        agent = WechatWriterAgent()
        result = agent.write_article(topic="测试", max_turns=5)

        # 验证不超过 max_turns
        assert mock_client.messages.create.call_count <= 5

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    def test_early_completion(self, mock_exists, mock_anthropic_class):
        """测试提前完成（第一轮就返回文章）"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # 第一次就返回 end_turn
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_text = Mock()
        mock_text.text = "快速完成的文章"
        mock_text.type = "text"
        mock_response.content = [mock_text]
        mock_client.messages.create.return_value = mock_response

        agent = WechatWriterAgent()
        result = agent.write_article(topic="测试", max_turns=10)

        # 验证只调用一次
        assert mock_client.messages.create.call_count == 1
        assert result == "快速完成的文章"


class TestSystemPrompt:
    """测试系统提示词"""

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    def test_system_prompt_exists(self, mock_exists, mock_anthropic_class):
        """测试系统提示词存在"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        agent = WechatWriterAgent()
        system_prompt = agent._get_system_prompt()

        assert isinstance(system_prompt, str)
        assert len(system_prompt) > 0

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    def test_system_prompt_content(self, mock_exists, mock_anthropic_class):
        """测试系统提示词包含关键指令"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        agent = WechatWriterAgent()
        system_prompt = agent._get_system_prompt()

        # 应该包含关键概念
        assert "query_notebooklm" in system_prompt or "知识库" in system_prompt
        assert "文章" in system_prompt

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    def test_system_prompt_passed_to_api(self, mock_exists, mock_anthropic_class):
        """测试系统提示词传递给 API"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_text = Mock()
        mock_text.text = "文章"
        mock_text.type = "text"
        mock_response.content = [mock_text]
        mock_client.messages.create.return_value = mock_response

        agent = WechatWriterAgent()
        agent.write_article(topic="测试")

        # 验证 system 参数
        call_args = mock_client.messages.create.call_args
        assert 'system' in call_args[1]
        system = call_args[1]['system']
        assert isinstance(system, str)
        assert len(system) > 0


class TestMessageConstruction:
    """测试消息构造"""

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    def test_initial_message_with_topic_only(self, mock_exists, mock_anthropic_class):
        """测试仅包含主题的初始消息"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_text = Mock()
        mock_text.text = "文章"
        mock_text.type = "text"
        mock_response.content = [mock_text]
        mock_client.messages.create.return_value = mock_response

        agent = WechatWriterAgent()
        agent.write_article(topic="AI技术")

        call_args = mock_client.messages.create.call_args
        messages = call_args[1]['messages']

        assert len(messages) >= 1
        assert messages[0]['role'] == 'user'
        assert "AI技术" in messages[0]['content']

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    def test_initial_message_with_reference(self, mock_exists, mock_anthropic_class):
        """测试包含参考资料的初始消息"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_text = Mock()
        mock_text.text = "文章"
        mock_text.type = "text"
        mock_response.content = [mock_text]
        mock_client.messages.create.return_value = mock_response

        agent = WechatWriterAgent()
        agent.write_article(topic="测试主题", reference="参考内容")

        call_args = mock_client.messages.create.call_args
        messages = call_args[1]['messages']

        content = messages[0]['content']
        assert "测试主题" in content
        assert "参考内容" in content


class TestStopReasonHandling:
    """测试不同 stop_reason 的处理"""

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    def test_handle_end_turn(self, mock_exists, mock_anthropic_class):
        """测试处理 end_turn"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_text = Mock()
        mock_text.text = "完成的文章"
        mock_text.type = "text"
        mock_response.content = [mock_text]
        mock_client.messages.create.return_value = mock_response

        agent = WechatWriterAgent()
        result = agent.write_article(topic="测试")

        assert result == "完成的文章"

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    def test_handle_unexpected_stop_reason(self, mock_exists, mock_anthropic_class):
        """测试处理意外的 stop_reason"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock()
        mock_response.stop_reason = "max_tokens"  # 意外的停止原因
        mock_text = Mock()
        mock_text.text = "部分文章"
        mock_text.type = "text"
        mock_response.content = [mock_text]
        mock_client.messages.create.return_value = mock_response

        agent = WechatWriterAgent()
        result = agent.write_article(topic="测试")

        # 应该返回当前内容，不崩溃
        assert isinstance(result, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
