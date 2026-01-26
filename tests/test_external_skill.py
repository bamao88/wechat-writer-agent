"""
外部 Skill 集成测试
测试与外部 NotebookLM Skill 的集成

优先级: P1
"""
import pytest
import sys
import subprocess
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加父目录到路径以导入模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from notebooklm_tool import NotebookLMTool


class TestSubprocessCalling:
    """测试 Subprocess 调用"""

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_subprocess_command_structure(self, mock_run, mock_exists):
        """验证 subprocess 正确调用 run.py ask_question.py"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Question: test\n==========\nanswer\n=========="
        mock_run.return_value = mock_result

        tool = NotebookLMTool()
        tool.query("测试问题")

        # 验证调用结构
        call_args = mock_run.call_args
        cmd = call_args[0][0]

        # 验证命令包含必要元素
        assert any("run.py" in str(c) for c in cmd)
        assert "ask_question.py" in cmd
        assert "--question" in cmd
        assert "测试问题" in cmd

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_subprocess_parameters_passed_correctly(self, mock_run, mock_exists):
        """验证参数正确传递"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Question: test\n==========\nanswer\n=========="
        mock_run.return_value = mock_result

        tool = NotebookLMTool(notebook_id="test_id")
        tool.query("测试问题")

        call_args = mock_run.call_args
        cmd = call_args[0][0]

        # 验证 notebook_id 参数
        assert "--notebook-id" in cmd
        assert "test_id" in cmd

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_subprocess_timeout_configuration(self, mock_run, mock_exists):
        """验证超时配置正确"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Question: test\n==========\nanswer\n=========="
        mock_run.return_value = mock_result

        tool = NotebookLMTool()
        tool.query("测试问题")

        # 验证 timeout 参数
        call_args = mock_run.call_args
        assert call_args[1]['timeout'] == 180

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_subprocess_output_capture(self, mock_run, mock_exists):
        """验证输出捕获配置"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Question: test\n==========\nanswer\n=========="
        mock_run.return_value = mock_result

        tool = NotebookLMTool()
        tool.query("测试问题")

        call_args = mock_run.call_args
        assert call_args[1]['capture_output'] is True
        assert call_args[1]['text'] is True


class TestOutputParsing:
    """测试输出解析"""

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_parse_standard_output(self, mock_run, mock_exists):
        """测试解析标准输出格式"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = """Question: 什么是AI？
==========
人工智能是计算机科学的一个分支。
=========="""
        mock_run.return_value = mock_result

        tool = NotebookLMTool()
        result = tool.query("什么是AI？")

        assert "人工智能是计算机科学的一个分支" in result
        assert "Question:" not in result  # 应该被移除
        assert "=" not in result  # 分隔符应该被移除

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_parse_multiline_answer(self, mock_run, mock_exists):
        """测试解析多行答案"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = """Question: test
==========
第一行答案
第二行答案
第三行答案
=========="""
        mock_run.return_value = mock_result

        tool = NotebookLMTool()
        result = tool.query("test")

        assert "第一行答案" in result
        assert "第二行答案" in result
        assert "第三行答案" in result

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_parse_with_follow_up_reminder(self, mock_run, mock_exists):
        """测试移除 follow-up reminder"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = """Question: test
==========
答案内容在这里
EXTREMELY IMPORTANT: Please make sure to...
=========="""
        mock_run.return_value = mock_result

        tool = NotebookLMTool()
        result = tool.query("test")

        assert "答案内容在这里" in result
        assert "EXTREMELY IMPORTANT" not in result

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_parse_empty_answer(self, mock_run, mock_exists):
        """测试解析空答案"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = """Question: test
==========

=========="""
        mock_run.return_value = mock_result

        tool = NotebookLMTool()
        result = tool.query("test")

        # 应该返回原始输出或空字符串，不应该崩溃
        assert isinstance(result, str)


class TestAuthenticationErrors:
    """测试认证错误处理"""

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_not_authenticated_error_detection(self, mock_run, mock_exists):
        """测试检测未认证错误"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Error: Not authenticated. Please run setup."
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        tool = NotebookLMTool()
        result = tool.query("测试")

        assert "未认证" in result

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_authentication_error_message_includes_guidance(self, mock_run, mock_exists):
        """验证认证错误提示包含指引"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Not authenticated"
        mock_run.return_value = mock_result

        tool = NotebookLMTool()
        result = tool.query("测试")

        # 应该包含设置指引
        assert "auth_manager.py" in result
        assert "setup" in result


class TestNotebookErrors:
    """测试笔记本相关错误"""

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_no_notebooks_error(self, mock_run, mock_exists):
        """测试无笔记本错误"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "No notebooks in library"
        mock_run.return_value = mock_result

        tool = NotebookLMTool()
        result = tool.query("测试")

        assert "未找到笔记本" in result
        assert "notebook_manager.py" in result

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_notebook_not_found_error(self, mock_run, mock_exists):
        """测试笔记本未找到错误"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Notebook not found in library"
        mock_run.return_value = mock_result

        tool = NotebookLMTool()
        result = tool.query("测试")

        assert "未找到笔记本" in result

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_invalid_notebook_url_error(self, mock_run, mock_exists):
        """测试无效笔记本 URL 错误"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Invalid notebook URL"
        mock_run.return_value = mock_result

        tool = NotebookLMTool(notebook_url="invalid-url")
        result = tool.query("测试")

        assert "查询失败" in result


class TestNotebookParameters:
    """测试笔记本参数"""

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_active_notebook_used_by_default(self, mock_run, mock_exists):
        """测试默认使用 active notebook"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Question: test\n==========\nanswer\n=========="
        mock_run.return_value = mock_result

        tool = NotebookLMTool()
        tool.query("测试")

        call_args = mock_run.call_args
        cmd = call_args[0][0]

        # 不应该有 notebook 参数
        assert "--notebook-id" not in cmd
        assert "--notebook-url" not in cmd

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_notebook_id_parameter(self, mock_run, mock_exists):
        """测试 notebook_id 参数传递"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Question: test\n==========\nanswer\n=========="
        mock_run.return_value = mock_result

        tool = NotebookLMTool(notebook_id="my_notebook")
        tool.query("测试")

        call_args = mock_run.call_args
        cmd = call_args[0][0]

        assert "--notebook-id" in cmd
        assert "my_notebook" in cmd

    @patch('notebooklm_tool.Path.exists')
    @patch('notebooklm_tool.subprocess.run')
    def test_notebook_url_priority_over_id(self, mock_run, mock_exists):
        """测试 notebook_url 优先于 notebook_id"""
        mock_exists.return_value = True

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Question: test\n==========\nanswer\n=========="
        mock_run.return_value = mock_result

        url = "https://notebooklm.google.com/notebook/abc123"
        tool = NotebookLMTool(notebook_url=url, notebook_id="should_be_ignored")
        tool.query("测试")

        call_args = mock_run.call_args
        cmd = call_args[0][0]

        # 应该使用 URL，不使用 ID
        assert "--notebook-url" in cmd
        assert url in cmd
        assert "--notebook-id" not in cmd


@pytest.mark.integration
class TestRealSkillIntegration:
    """真实 Skill 集成测试（需要真实环境）

    使用 pytest -m integration 运行这些测试
    """

    @pytest.mark.skip(reason="需要真实的 NotebookLM Skill 安装")
    def test_real_skill_path_exists(self):
        """测试真实 Skill 路径存在"""
        skill_dir = Path.home() / ".claude" / "skills" / "notebooklm"
        run_script = skill_dir / "scripts" / "run.py"

        assert skill_dir.exists(), f"Skill 目录不存在: {skill_dir}"
        assert run_script.exists(), f"run.py 脚本不存在: {run_script}"

    @pytest.mark.skip(reason="需要真实的 NotebookLM Skill 和认证")
    def test_real_subprocess_call(self):
        """测试真实的 subprocess 调用"""
        skill_dir = Path.home() / ".claude" / "skills" / "notebooklm"
        run_script = skill_dir / "scripts" / "run.py"

        result = subprocess.run(
            [
                sys.executable,
                str(run_script),
                "ask_question.py",
                "--question", "测试问题"
            ],
            capture_output=True,
            text=True,
            timeout=180
        )

        # 验证命令执行
        assert result.returncode == 0 or "Not authenticated" in result.stderr

    @pytest.mark.skip(reason="需要真实的认证和笔记本")
    def test_real_query_execution(self):
        """测试真实的查询执行"""
        tool = NotebookLMTool()
        result = tool.query("什么是人工智能？")

        assert isinstance(result, str)
        assert len(result) > 0
        print(f"\n查询结果:\n{result}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
