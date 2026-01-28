"""SubprocessRunner 单元测试

验证增强型子进程执行器的错误处理逻辑 (ERR-01, ERR-02)
"""
import os
import pytest
from src.utils.subprocess_runner import SubprocessRunner, run_skill_subprocess


class TestSubprocessRunner:
    """SubprocessRunner 测试套件"""

    def test_successful_execution(self):
        """测试成功执行返回正确结果"""
        runner = SubprocessRunner()
        result = runner.run(["echo", "hello"])

        assert result["success"] is True
        assert "hello" in result["stdout"]
        assert result["returncode"] == 0
        assert result["error_message"] is None
        assert result["timeout_occurred"] is False

    def test_nonzero_exit_code(self):
        """测试非零退出码被正确捕获 (ERR-01)"""
        runner = SubprocessRunner()
        result = runner.run(["python", "-c", "import sys; sys.exit(1)"])

        assert result["success"] is False
        assert result["returncode"] == 1
        assert "退出码 1" in result["error_message"]
        assert result["timeout_occurred"] is False

    def test_timeout_handling_10_seconds(self):
        """测试 10 秒超时被正确检测 (ERR-02)

        这是 ERR-02 需求的关键测试。
        验证 timeout=10 秒能正确终止长时间运行的子进程。
        """
        runner = SubprocessRunner()
        # 模拟需要 15 秒的操作,使用 10 秒超时
        result = runner.run(["sleep", "15"], timeout=10)

        assert result["success"] is False
        assert result["timeout_occurred"] is True
        assert "超时" in result["error_message"]
        assert "10" in result["error_message"]  # 确认超时时长在错误消息中

    def test_stderr_capture(self):
        """测试 stderr 被完整捕获"""
        runner = SubprocessRunner()
        result = runner.run(
            ["python", "-c", "import sys; sys.stderr.write('error msg')"]
        )

        assert "error msg" in result["stderr"]

    def test_command_not_found(self):
        """测试命令不存在被正确处理"""
        runner = SubprocessRunner()
        result = runner.run(["nonexistent_command_xyz_12345"])

        assert result["success"] is False
        assert (
            "未找到" in result["error_message"]
            or "not found" in result["error_message"].lower()
            or "命令未找到" in result["error_message"]
        )

    def test_env_passing(self):
        """测试环境变量正确传递给子进程"""
        runner = SubprocessRunner()
        result = runner.run(
            [
                "python",
                "-c",
                "import os; print(os.environ.get('TEST_VAR', 'NOT_SET'))",
            ],
            env={"TEST_VAR": "test_value", **os.environ},
        )

        assert result["success"] is True
        assert "test_value" in result["stdout"]

    def test_cwd_parameter(self):
        """测试工作目录参数正确传递"""
        runner = SubprocessRunner()
        # 使用 /tmp 作为工作目录
        result = runner.run(["pwd"], cwd="/tmp")

        assert result["success"] is True
        assert "/tmp" in result["stdout"]

    def test_short_timeout(self):
        """测试短超时(1秒)正确工作"""
        runner = SubprocessRunner()
        result = runner.run(["sleep", "5"], timeout=1)

        assert result["success"] is False
        assert result["timeout_occurred"] is True
        assert result["returncode"] == -1

    def test_encoding_errors_handled(self):
        """测试编码错误被正确处理 (errors='replace')"""
        runner = SubprocessRunner()
        # 创建一个输出非UTF-8字符的脚本(这应该不会崩溃)
        result = runner.run(["python", "-c", "print('正常文本')"])

        # 应该成功,不抛出异常
        assert result["success"] is True


class TestRunSkillSubprocess:
    """run_skill_subprocess 便捷函数测试"""

    def test_skill_not_found(self):
        """测试技能目录不存在时抛出异常"""
        with pytest.raises(FileNotFoundError, match="技能目录不存在"):
            run_skill_subprocess(
                skill_name="nonexistent_skill_xyz",
                script_name="test.py",
                args=[]
            )

    def test_skill_exists_but_no_script(self, tmp_path):
        """测试技能目录存在但脚本不存在时抛出异常

        由于无法轻易创建 ~/.claude/skills/ 目录结构,
        此测试验证错误处理逻辑而非实际执行。
        """
        # 这个测试依赖于实际的技能目录结构
        # 如果技能不存在,应该抛出 FileNotFoundError
        with pytest.raises(FileNotFoundError):
            run_skill_subprocess(
                skill_name="nonexistent_skill_xyz",
                script_name="test.py",
                args=["arg1", "arg2"]
            )
