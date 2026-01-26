"""
端到端 (E2E) 测试
测试完整的用户工作流

优先级: P0
"""
import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加父目录到路径以导入模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from writer_agent import WechatWriterAgent, create_writer_agent
from notebooklm_tool import NotebookLMTool


class TestE2EProgrammaticUsage:
    """测试程序化调用"""

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    def test_create_agent_default(self, mock_exists, mock_anthropic):
        """测试默认创建 Agent"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        agent = create_writer_agent()

        assert agent is not None
        assert isinstance(agent, WechatWriterAgent)

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    def test_create_agent_with_notebook_id(self, mock_exists, mock_anthropic):
        """测试使用 notebook_id 创建 Agent"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        agent = create_writer_agent(notebook_id="test_notebook")

        assert agent.notebooklm.notebook_id == "test_notebook"

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    def test_create_agent_with_notebook_url(self, mock_exists, mock_anthropic):
        """测试使用 notebook_url 创建 Agent"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        url = "https://notebooklm.google.com/notebook/123"
        agent = create_writer_agent(notebook_url=url)

        assert agent.notebooklm.notebook_url == url

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_write_article_basic(self, mock_run, mock_exists, mock_anthropic_class):
        """测试基本的文章生成流程"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        # 模拟 NotebookLM 查询
        mock_nb_result = Mock()
        mock_nb_result.returncode = 0
        mock_nb_result.stdout = "Question: test\n==========\nNotebookLM 答案\n=========="
        mock_run.return_value = mock_nb_result

        # 模拟 Anthropic API
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # 第一次调用：返回 tool_use
        mock_response_1 = Mock()
        mock_response_1.stop_reason = "tool_use"
        mock_content_block_text = Mock()
        mock_content_block_text.type = "text"
        mock_content_block_text.text = "让我查询一下知识库"
        mock_content_block_tool = Mock()
        mock_content_block_tool.type = "tool_use"
        mock_content_block_tool.name = "query_notebooklm"
        mock_content_block_tool.input = {"question": "测试查询"}
        mock_content_block_tool.id = "tool_123"
        mock_response_1.content = [mock_content_block_text, mock_content_block_tool]

        # 第二次调用：返回最终文章
        mock_response_2 = Mock()
        mock_response_2.stop_reason = "end_turn"
        mock_final_content = Mock()
        mock_final_content.text = "这是一篇关于人工智能的文章。人工智能正在改变我们的生活..."
        mock_final_content.type = "text"
        mock_response_2.content = [mock_final_content]

        mock_client.messages.create.side_effect = [mock_response_1, mock_response_2]

        # 创建 Agent 并生成文章
        agent = create_writer_agent()
        article = agent.write_article(
            topic="人工智能在教育中的应用",
            reference=""
        )

        # 验证结果
        assert isinstance(article, str)
        assert len(article) > 0
        assert "人工智能" in article or "文章" in article

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    def test_write_article_with_reference(self, mock_exists, mock_anthropic_class):
        """测试带参考资料的文章生成"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        # 模拟 Anthropic API - 直接返回文章，不调用工具
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_content = Mock()
        mock_content.text = "这是基于参考资料的文章内容..."
        mock_content.type = "text"
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response

        agent = create_writer_agent()
        article = agent.write_article(
            topic="测试主题",
            reference="这是参考资料"
        )

        # 验证 API 调用包含参考资料
        call_args = mock_client.messages.create.call_args
        messages = call_args[1]['messages']
        assert "参考资料" in messages[0]['content']

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    def test_agent_max_turns_limit(self, mock_exists, mock_anthropic_class):
        """测试 Agent 的最大轮次限制"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        # 模拟 Anthropic API - 持续返回 tool_use
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock()
        mock_response.stop_reason = "tool_use"
        mock_content = Mock()
        mock_content.type = "tool_use"
        mock_content.name = "query_notebooklm"
        mock_content.input = {"question": "测试"}
        mock_content.id = "tool_123"
        mock_response.content = [mock_content]

        mock_client.messages.create.return_value = mock_response

        agent = create_writer_agent()
        article = agent.write_article(
            topic="测试主题",
            max_turns=3  # 限制为3轮
        )

        # 验证 API 调用次数不超过 max_turns
        assert mock_client.messages.create.call_count <= 3

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    def test_agent_system_prompt(self, mock_exists, mock_anthropic_class):
        """测试 Agent 的系统提示词"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_content = Mock()
        mock_content.text = "文章内容"
        mock_content.type = "text"
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response

        agent = create_writer_agent()
        agent.write_article(topic="测试")

        # 验证系统提示词存在
        call_args = mock_client.messages.create.call_args
        system_prompt = call_args[1]['system']
        assert isinstance(system_prompt, str)
        assert len(system_prompt) > 0
        assert "query_notebooklm" in system_prompt or "知识库" in system_prompt


class TestE2EErrorHandling:
    """测试 E2E 错误处理"""

    @patch('notebooklm_tool.Path.exists')
    def test_missing_api_key(self, mock_exists):
        """测试缺失 API Key"""
        mock_exists.return_value = True

        # 清除环境变量
        if 'ANTHROPIC_API_KEY' in os.environ:
            del os.environ['ANTHROPIC_API_KEY']

        with pytest.raises(ValueError) as exc_info:
            create_writer_agent()

        assert "ANTHROPIC_API_KEY" in str(exc_info.value)

    @patch('writer_agent.Anthropic')
    def test_missing_notebooklm_skill(self, mock_anthropic):
        """测试 NotebookLM Skill 未安装"""
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        # 不需要 mock Path.exists，让它真实检查
        # 假设 skill 未安装在测试环境中
        with pytest.raises(ValueError) as exc_info:
            create_writer_agent()

        # 错误信息应该提示安装 skill
        assert "skill" in str(exc_info.value).lower() or "安装" in str(exc_info.value)


class TestE2EToolIntegration:
    """测试工具集成"""

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    def test_tool_definition_passed_to_claude(self, mock_exists, mock_anthropic_class):
        """测试 Tool Definition 正确传递给 Claude"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_content = Mock()
        mock_content.text = "文章"
        mock_content.type = "text"
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response

        agent = create_writer_agent()
        agent.write_article(topic="测试")

        # 验证 tools 参数
        call_args = mock_client.messages.create.call_args
        tools = call_args[1]['tools']
        assert isinstance(tools, list)
        assert len(tools) > 0
        assert tools[0]['name'] == 'query_notebooklm'

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_tool_result_integration(self, mock_run, mock_exists, mock_anthropic_class):
        """测试工具结果正确集成到对话流"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        # 模拟 NotebookLM 查询
        mock_nb_result = Mock()
        mock_nb_result.returncode = 0
        mock_nb_result.stdout = "Question: test\n==========\n查询结果内容\n=========="
        mock_run.return_value = mock_nb_result

        # 模拟 Anthropic API
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # 第一次：tool_use
        mock_response_1 = Mock()
        mock_response_1.stop_reason = "tool_use"
        mock_tool_block = Mock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "query_notebooklm"
        mock_tool_block.input = {"question": "测试问题"}
        mock_tool_block.id = "tool_123"
        mock_response_1.content = [mock_tool_block]

        # 第二次：end_turn
        mock_response_2 = Mock()
        mock_response_2.stop_reason = "end_turn"
        mock_final = Mock()
        mock_final.text = "最终文章"
        mock_final.type = "text"
        mock_response_2.content = [mock_final]

        mock_client.messages.create.side_effect = [mock_response_1, mock_response_2]

        agent = create_writer_agent()
        article = agent.write_article(topic="测试")

        # 验证第二次调用包含 tool_result
        assert mock_client.messages.create.call_count == 2
        second_call_args = mock_client.messages.create.call_args_list[1]
        messages = second_call_args[1]['messages']

        # 应该有3条消息：user, assistant (tool_use), user (tool_result)
        assert len(messages) == 3
        assert messages[2]['role'] == 'user'
        assert messages[2]['content'][0]['type'] == 'tool_result'
        assert "查询结果内容" in messages[2]['content'][0]['content']


class TestE2EOutputValidation:
    """测试输出验证"""

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    def test_article_output_format(self, mock_exists, mock_anthropic_class):
        """测试文章输出格式"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_content = Mock()
        mock_content.text = "# 测试标题\n\n这是文章正文..."
        mock_content.type = "text"
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response

        agent = create_writer_agent()
        article = agent.write_article(topic="测试主题")

        # 验证输出是字符串
        assert isinstance(article, str)
        # 验证输出不为空
        assert len(article) > 0
        # 验证输出包含内容
        assert "文章" in article or "标题" in article


@pytest.mark.integration
class TestE2ERealAPI:
    """集成测试（需要真实 API 和 Skill）

    这些测试需要：
    1. 有效的 ANTHROPIC_API_KEY
    2. 已安装的 NotebookLM Skill
    3. 已认证的 Google 账号
    4. 至少一个可用的笔记本

    使用 pytest -m integration 运行这些测试
    """

    @pytest.mark.skip(reason="需要真实 API Key 和 NotebookLM Skill")
    def test_real_article_generation(self):
        """测试真实的文章生成（需要真实环境）"""
        # 这个测试只在手动测试时运行
        agent = create_writer_agent()
        article = agent.write_article(
            topic="AI 测试文章",
            reference="",
            max_turns=5
        )

        assert isinstance(article, str)
        assert len(article) > 100
        print(f"\n生成的文章:\n{article}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
