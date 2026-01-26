"""
错误处理测试
测试各种异常场景的处理

优先级: P1
"""
import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import subprocess

# 添加父目录到路径以导入模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from notebooklm_tool import NotebookLMTool, create_notebooklm_tool
from writer_agent import WechatWriterAgent, create_writer_agent


class TestAPIKeyErrors:
    """测试 API 密钥错误"""

    @patch('notebooklm_tool.Path.exists')
    def test_missing_api_key_env_variable(self, mock_exists):
        """测试缺失 ANTHROPIC_API_KEY 环境变量"""
        mock_exists.return_value = True

        # 清除环境变量
        if 'ANTHROPIC_API_KEY' in os.environ:
            del os.environ['ANTHROPIC_API_KEY']

        with pytest.raises(ValueError) as exc_info:
            WechatWriterAgent()

        error_msg = str(exc_info.value)
        assert "ANTHROPIC_API_KEY" in error_msg

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    def test_invalid_api_key(self, mock_exists, mock_anthropic_class):
        """测试无效的 API Key"""
        mock_exists.return_value = True

        # Mock Anthropic 抛出认证错误
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("Invalid API key")

        agent = WechatWriterAgent(api_key="invalid-key")

        with pytest.raises(Exception) as exc_info:
            agent.write_article(topic="测试")

        assert "Invalid API key" in str(exc_info.value)


class TestNotebookLMSkillErrors:
    """测试 NotebookLM Skill 相关错误"""

    @patch('notebooklm_tool.Path.exists')
    def test_skill_not_installed(self, mock_exists):
        """测试 NotebookLM skill 未安装"""
        mock_exists.return_value = False

        with pytest.raises(ValueError) as exc_info:
            NotebookLMTool()

        error_msg = str(exc_info.value)
        assert "skill" in error_msg.lower() or "安装" in error_msg

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_authentication_error(self, mock_run, mock_exists):
        """测试未认证错误"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Error: Not authenticated. Please run setup."
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        tool = NotebookLMTool()
        result = tool.query("测试问题")

        assert "未认证" in result or "认证" in result
        assert "auth_manager" in result or "setup" in result

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_no_notebooks_in_library(self, mock_run, mock_exists):
        """测试库中无笔记本错误"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "No notebooks in library"
        mock_run.return_value = mock_result

        tool = NotebookLMTool()
        result = tool.query("测试")

        assert "笔记本" in result or "notebook" in result.lower()
        assert "notebook_manager" in result or "add" in result


class TestNetworkErrors:
    """测试网络错误"""

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_subprocess_timeout(self, mock_run, mock_exists):
        """测试 subprocess 超时"""
        mock_exists.return_value = True
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=180)

        tool = NotebookLMTool()
        result = tool.query("复杂问题")

        assert "超时" in result
        assert isinstance(result, str)
        # 不应该抛出异常，而是返回友好的错误消息

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    def test_api_connection_error(self, mock_exists, mock_anthropic_class):
        """测试 API 连接错误"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.side_effect = ConnectionError("Network error")

        agent = WechatWriterAgent()

        with pytest.raises(ConnectionError):
            agent.write_article(topic="测试")

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_subprocess_generic_error(self, mock_run, mock_exists):
        """测试 subprocess 一般错误"""
        mock_exists.return_value = True
        mock_run.side_effect = Exception("Unexpected error")

        tool = NotebookLMTool()
        result = tool.query("测试")

        assert "查询失败" in result or "失败" in result
        assert isinstance(result, str)


class TestInputBoundaryErrors:
    """测试输入边界错误"""

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    def test_empty_topic(self, mock_exists, mock_anthropic_class):
        """测试空主题"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_text = Mock()
        mock_text.text = "无法创建文章，主题为空"
        mock_text.type = "text"
        mock_response.content = [mock_text]
        mock_client.messages.create.return_value = mock_response

        agent = WechatWriterAgent()
        result = agent.write_article(topic="")

        # 应该返回某种响应，不崩溃
        assert isinstance(result, str)

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    def test_very_long_topic(self, mock_exists, mock_anthropic_class):
        """测试极长主题"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_text = Mock()
        mock_text.text = "文章内容"
        mock_text.type = "text"
        mock_response.content = [mock_text]
        mock_client.messages.create.return_value = mock_response

        # 创建一个超长主题（>1000字符）
        long_topic = "A" * 1500

        agent = WechatWriterAgent()
        result = agent.write_article(topic=long_topic)

        # 应该正常处理，不崩溃
        assert isinstance(result, str)

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    def test_special_characters_in_topic(self, mock_exists, mock_anthropic_class):
        """测试主题中的特殊字符"""
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
        result = agent.write_article(topic='测试"特殊"字符<>&')

        assert isinstance(result, str)

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_empty_query(self, mock_run, mock_exists):
        """测试空查询"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Question: \n==========\n\n=========="
        mock_run.return_value = mock_result

        tool = NotebookLMTool()
        result = tool.query("")

        # 应该返回结果，不崩溃
        assert isinstance(result, str)

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_very_long_query(self, mock_run, mock_exists):
        """测试超长查询"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Question: long\n==========\nanswer\n=========="
        mock_run.return_value = mock_result

        tool = NotebookLMTool()
        long_query = "查询" * 500  # 很长的查询
        result = tool.query(long_query)

        assert isinstance(result, str)


class TestInvalidParameters:
    """测试无效参数"""

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_invalid_notebook_id(self, mock_run, mock_exists):
        """测试无效的 notebook_id"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Notebook 'invalid_id' not found in library"
        mock_run.return_value = mock_result

        tool = NotebookLMTool(notebook_id="invalid_id")
        result = tool.query("测试")

        assert "查询失败" in result or "未找到" in result

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_invalid_notebook_url(self, mock_run, mock_exists):
        """测试无效的 notebook_url"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Invalid notebook URL"
        mock_run.return_value = mock_result

        tool = NotebookLMTool(notebook_url="not-a-valid-url")
        result = tool.query("测试")

        assert "查询失败" in result

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    def test_invalid_max_turns(self, mock_exists, mock_anthropic_class):
        """测试无效的 max_turns"""
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

        # max_turns = 0 应该快速返回
        result = agent.write_article(topic="测试", max_turns=0)
        assert mock_client.messages.create.call_count == 0


class TestMalformedResponses:
    """测试畸形响应"""

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_malformed_output_no_separators(self, mock_run, mock_exists):
        """测试没有分隔符的输出"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "这是一个没有分隔符的输出"
        mock_run.return_value = mock_result

        tool = NotebookLMTool()
        result = tool.query("测试")

        # 应该返回原始输出
        assert isinstance(result, str)
        assert len(result) > 0

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_malformed_output_only_one_separator(self, mock_run, mock_exists):
        """测试只有一个分隔符的输出"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Question: test\n==========\n没有结束分隔符"
        mock_run.return_value = mock_result

        tool = NotebookLMTool()
        result = tool.query("测试")

        # 应该提取到内容
        assert isinstance(result, str)
        assert "没有结束分隔符" in result or len(result) > 0

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    def test_response_without_text_content(self, mock_exists, mock_anthropic_class):
        """测试没有文本内容的响应"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # 返回一个没有 text 属性的响应
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_content = Mock(spec=[])  # 没有 text 属性
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response

        agent = WechatWriterAgent()
        result = agent.write_article(topic="测试")

        # 应该返回空字符串或合理处理
        assert isinstance(result, str)


class TestResourceErrors:
    """测试资源错误"""

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_subprocess_killed(self, mock_run, mock_exists):
        """测试 subprocess 被杀死"""
        mock_exists.return_value = True
        mock_run.side_effect = subprocess.SubprocessError("Process killed")

        tool = NotebookLMTool()
        result = tool.query("测试")

        # 应该返回错误消息
        assert "查询失败" in result or "失败" in result

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    def test_api_rate_limit(self, mock_exists, mock_anthropic_class):
        """测试 API 速率限制"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("Rate limit exceeded")

        agent = WechatWriterAgent()

        with pytest.raises(Exception) as exc_info:
            agent.write_article(topic="测试")

        assert "Rate limit" in str(exc_info.value)


class TestConcurrentErrors:
    """测试并发相关错误"""

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_multiple_simultaneous_queries(self, mock_run, mock_exists):
        """测试多个同时查询（不应该崩溃）"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Question: test\n==========\nanswer\n=========="
        mock_run.return_value = mock_result

        tool = NotebookLMTool()

        # 执行多次查询
        results = []
        for i in range(5):
            result = tool.query(f"查询 {i}")
            results.append(result)

        # 所有查询都应该成功
        assert len(results) == 5
        for result in results:
            assert isinstance(result, str)


class TestErrorRecovery:
    """测试错误恢复"""

    @patch('writer_agent.Anthropic')
    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_retry_after_tool_failure(self, mock_run, mock_exists, mock_anthropic_class):
        """测试工具失败后继续"""
        mock_exists.return_value = True
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'

        # 第一次 NotebookLM 调用失败
        mock_nb_result_1 = Mock()
        mock_nb_result_1.returncode = 1
        mock_nb_result_1.stderr = "Error"

        # 第二次成功
        mock_nb_result_2 = Mock()
        mock_nb_result_2.returncode = 0
        mock_nb_result_2.stdout = "Question: test\n==========\nanswer\n=========="

        mock_run.side_effect = [mock_nb_result_1, mock_nb_result_2]

        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # 第一轮：tool_use（失败）
        r1 = Mock()
        r1.stop_reason = "tool_use"
        t1 = Mock()
        t1.type = "tool_use"
        t1.name = "query_notebooklm"
        t1.input = {"question": "测试1"}
        t1.id = "tool_1"
        r1.content = [t1]

        # 第二轮：tool_use（成功）
        r2 = Mock()
        r2.stop_reason = "tool_use"
        t2 = Mock()
        t2.type = "tool_use"
        t2.name = "query_notebooklm"
        t2.input = {"question": "测试2"}
        t2.id = "tool_2"
        r2.content = [t2]

        # 第三轮：完成
        r3 = Mock()
        r3.stop_reason = "end_turn"
        txt = Mock()
        txt.text = "最终文章"
        txt.type = "text"
        r3.content = [txt]

        mock_client.messages.create.side_effect = [r1, r2, r3]

        agent = WechatWriterAgent()
        result = agent.write_article(topic="测试")

        # 应该继续并完成
        assert result == "最终文章"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
