"""
NotebookLMTool 单元测试
测试 NotebookLMTool 类的核心功能

优先级: P0
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import subprocess

# 添加父目录到路径以导入模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from notebooklm_tool import NotebookLMTool, create_notebooklm_tool


class TestNotebookLMToolInitialization:
    """测试 NotebookLMTool 初始化"""

    @patch('notebooklm_tool.Path.exists')
    def test_default_initialization(self, mock_exists):
        """测试默认初始化（使用活动笔记本）"""
        mock_exists.return_value = True

        tool = NotebookLMTool()

        assert tool is not None
        assert tool.notebook_id is None
        assert tool.notebook_url is None
        assert str(tool.skill_dir).endswith(".claude/skills/notebooklm")

    @patch('notebooklm_tool.Path.exists')
    def test_initialization_with_notebook_id(self, mock_exists):
        """测试使用 notebook_id 初始化"""
        mock_exists.return_value = True

        tool = NotebookLMTool(notebook_id="test_notebook")

        assert tool.notebook_id == "test_notebook"
        assert tool.notebook_url is None

    @patch('notebooklm_tool.Path.exists')
    def test_initialization_with_notebook_url(self, mock_exists):
        """测试使用 notebook_url 初始化"""
        mock_exists.return_value = True

        url = "https://notebooklm.google.com/notebook/123"
        tool = NotebookLMTool(notebook_url=url)

        assert tool.notebook_url == url
        assert tool.notebook_id is None

    @patch('notebooklm_tool.Path.exists')
    def test_initialization_with_invalid_path(self, mock_exists):
        """测试无效路径初始化（应抛出错误）"""
        mock_exists.return_value = False

        with pytest.raises(ValueError) as exc_info:
            NotebookLMTool()

        assert "NotebookLM skill 未安装" in str(exc_info.value)

    @patch('notebooklm_tool.Path.exists')
    def test_create_notebooklm_tool_function(self, mock_exists):
        """测试工厂函数 create_notebooklm_tool"""
        mock_exists.return_value = True

        tool = create_notebooklm_tool(notebook_id="test")

        assert isinstance(tool, NotebookLMTool)
        assert tool.notebook_id == "test"


class TestNotebookLMToolDefinition:
    """测试 Tool Definition"""

    @patch('notebooklm_tool.Path.exists')
    def test_get_tool_definition_structure(self, mock_exists):
        """测试 get_tool_definition 返回正确的工具定义格式"""
        mock_exists.return_value = True
        tool = NotebookLMTool()

        definition = tool.get_tool_definition()

        # 检查必需字段
        assert "name" in definition
        assert "description" in definition
        assert "input_schema" in definition

        # 检查名称
        assert definition["name"] == "query_notebooklm"

        # 检查 input_schema 结构
        schema = definition["input_schema"]
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema

    @patch('notebooklm_tool.Path.exists')
    def test_get_tool_definition_schema(self, mock_exists):
        """测试 input_schema 符合 JSON Schema 规范"""
        mock_exists.return_value = True
        tool = NotebookLMTool()

        definition = tool.get_tool_definition()
        schema = definition["input_schema"]

        # 检查 question 字段
        assert "question" in schema["properties"]
        assert schema["properties"]["question"]["type"] == "string"
        assert "description" in schema["properties"]["question"]

        # 检查必需字段
        assert "question" in schema["required"]

    @patch('notebooklm_tool.Path.exists')
    def test_get_tool_definition_description(self, mock_exists):
        """测试工具描述包含关键信息"""
        mock_exists.return_value = True
        tool = NotebookLMTool()

        definition = tool.get_tool_definition()

        assert len(definition["description"]) > 0
        assert isinstance(definition["description"], str)


class TestNotebookLMToolQuery:
    """测试 Query 功能"""

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_query_normal(self, mock_run, mock_exists):
        """测试正常查询"""
        mock_exists.return_value = True

        # 模拟成功的查询响应
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Question: 测试问题\n==========\n这是答案内容\n=========="
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        tool = NotebookLMTool()
        result = tool.query("什么是人工智能？")

        assert isinstance(result, str)
        assert len(result) > 0
        assert "这是答案内容" in result

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_query_empty_question(self, mock_run, mock_exists):
        """测试空问题查询"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Question: \n==========\n\n=========="
        mock_run.return_value = mock_result

        tool = NotebookLMTool()
        result = tool.query("")

        # 应该返回某种结果，不崩溃
        assert isinstance(result, str)

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_query_special_characters(self, mock_run, mock_exists):
        """测试特殊字符问题查询"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = 'Question: AI的"未来"\n==========\n特殊字符答案\n=========='
        mock_run.return_value = mock_result

        tool = NotebookLMTool()
        result = tool.query('AI的"未来"是什么？')

        assert isinstance(result, str)
        assert "特殊字符答案" in result

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_query_timeout(self, mock_run, mock_exists):
        """测试超时场景"""
        mock_exists.return_value = True
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=180)

        tool = NotebookLMTool()
        result = tool.query("复杂问题")

        assert "超时" in result
        assert isinstance(result, str)

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_query_with_notebook_id(self, mock_run, mock_exists):
        """测试使用 notebook_id 查询"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Question: test\n==========\nanswer\n=========="
        mock_run.return_value = mock_result

        tool = NotebookLMTool(notebook_id="test_notebook")
        result = tool.query("测试问题")

        # 验证调用时传递了 notebook_id
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "--notebook-id" in cmd
        assert "test_notebook" in cmd

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_query_with_notebook_url(self, mock_run, mock_exists):
        """测试使用 notebook_url 查询（优先于 notebook_id）"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Question: test\n==========\nanswer\n=========="
        mock_run.return_value = mock_result

        url = "https://notebooklm.google.com/notebook/123"
        tool = NotebookLMTool(notebook_url=url, notebook_id="ignored")
        result = tool.query("测试问题")

        # 验证调用时传递了 notebook_url，而不是 notebook_id
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "--notebook-url" in cmd
        assert url in cmd
        assert "--notebook-id" not in cmd

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_query_not_authenticated_error(self, mock_run, mock_exists):
        """测试未认证错误处理"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Error: Not authenticated"
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        tool = NotebookLMTool()
        result = tool.query("测试问题")

        assert "未认证" in result
        assert "auth_manager.py setup" in result

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_query_no_notebooks_error(self, mock_run, mock_exists):
        """测试笔记本不存在错误处理"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "No notebooks in library"
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        tool = NotebookLMTool()
        result = tool.query("测试问题")

        assert "未找到笔记本" in result
        assert "notebook_manager.py add" in result

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_query_generic_error(self, mock_run, mock_exists):
        """测试一般错误处理"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Some other error"
        mock_run.return_value = mock_result

        tool = NotebookLMTool()
        result = tool.query("测试问题")

        assert "查询失败" in result
        assert "Some other error" in result

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_query_removes_follow_up_reminder(self, mock_exists, mock_run):
        """测试查询结果移除 follow-up reminder"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = """Question: test
==========
答案内容
EXTREMELY IMPORTANT: Please follow up...
=========="""
        mock_run.return_value = mock_result

        tool = NotebookLMTool()
        result = tool.query("测试")

        assert "EXTREMELY IMPORTANT" not in result
        assert "答案内容" in result


class TestNotebookLMToolIntegration:
    """集成测试（需要实际的 NotebookLM Skill 安装）"""

    def test_skill_path_structure(self):
        """测试技能路径结构"""
        skill_dir = Path.home() / ".claude" / "skills" / "notebooklm"

        # 这个测试可能会失败，如果 skill 未安装
        # 但它验证了我们期望的路径结构
        expected_script = skill_dir / "scripts" / "run.py"

        # 仅验证路径构造正确
        assert str(skill_dir).endswith("notebooklm")
        assert str(expected_script).endswith("run.py")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
