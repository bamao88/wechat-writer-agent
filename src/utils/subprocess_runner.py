"""增强型子进程执行器

提供完整的子进程错误捕获、日志记录和环境变量传递支持。
专门用于诊断和执行 Agent SDK 技能调用。
"""
import subprocess
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, List


logger = logging.getLogger(__name__)


class SubprocessRunner:
    """增强型子进程执行器，提供完整的错误信息捕获"""

    def __init__(self, logger_instance: Optional[logging.Logger] = None):
        """
        初始化子进程执行器

        Args:
            logger_instance: 日志记录器实例（可选）
        """
        self.logger = logger_instance or logger

    def run(
        self,
        cmd: List[str],
        timeout: int = 30,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行子进程并返回详细结果

        Args:
            cmd: 命令及参数列表
            timeout: 超时秒数（默认30秒）
            env: 环境变量字典（None表示继承当前进程环境）
            cwd: 工作目录（None表示使用当前目录）

        Returns:
            包含以下键的字典:
            - success (bool): 是否成功（returncode == 0）
            - stdout (str): 标准输出
            - stderr (str): 标准错误输出
            - returncode (int): 进程退出码
            - error_message (str): 错误描述（成功时为None）
            - timeout_occurred (bool): 是否发生超时
        """
        cmd_str = ' '.join(cmd)
        self.logger.info(f"[SubprocessRunner] 执行命令: {cmd_str}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                cwd=cwd,
                errors='replace'  # 处理编码问题
            )

            success = result.returncode == 0

            # 记录输出到日志
            if result.stdout:
                self.logger.debug(f"[SubprocessRunner] stdout: {result.stdout[:500]}")
            if result.stderr:
                level = logging.WARNING if success else logging.ERROR
                self.logger.log(level, f"[SubprocessRunner] stderr: {result.stderr[:2000]}")

            return {
                "success": success,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "error_message": None if success else f"退出码 {result.returncode}",
                "timeout_occurred": False
            }

        except subprocess.TimeoutExpired as e:
            self.logger.error(f"[SubprocessRunner] 子进程超时: {timeout}秒")

            # 处理 TimeoutExpired 的 stdout/stderr（可能是 bytes 或 None）
            stdout_str = None
            stderr_str = None
            if e.stdout:
                stdout_str = e.stdout.decode('utf-8', errors='replace') if isinstance(e.stdout, bytes) else e.stdout
            if e.stderr:
                stderr_str = e.stderr.decode('utf-8', errors='replace') if isinstance(e.stderr, bytes) else e.stderr

            return {
                "success": False,
                "stdout": stdout_str,
                "stderr": stderr_str,
                "returncode": -1,
                "error_message": f"超时(>{timeout}秒)",
                "timeout_occurred": True
            }

        except FileNotFoundError as e:
            self.logger.error(f"[SubprocessRunner] 命令未找到: {cmd[0]}")
            return {
                "success": False,
                "stdout": None,
                "stderr": None,
                "returncode": -1,
                "error_message": f"命令未找到: {cmd[0]}",
                "timeout_occurred": False
            }

        except Exception as e:
            self.logger.error(f"[SubprocessRunner] 子进程异常: {type(e).__name__}: {e}")
            return {
                "success": False,
                "stdout": None,
                "stderr": None,
                "returncode": -1,
                "error_message": f"异常: {type(e).__name__}: {e}",
                "timeout_occurred": False
            }


def run_skill_subprocess(
    skill_name: str,
    script_name: str,
    args: List[str],
    timeout: int = 30,
    env: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    便捷函数：执行 ~/.claude/skills/ 下的技能脚本

    Args:
        skill_name: 技能名称（如 "notebooklm"）
        script_name: 脚本名称（如 "ask_question.py"）
        args: 脚本参数列表
        timeout: 超时秒数（默认30秒）
        env: 环境变量字典（None表示继承当前进程环境）

    Returns:
        包含执行结果的字典（同 SubprocessRunner.run）

    Raises:
        FileNotFoundError: 技能目录或脚本不存在
    """
    # 构建技能脚本路径
    user_skills_dir = Path.home() / ".claude" / "skills" / skill_name
    script_path = user_skills_dir / "scripts" / "run.py"

    if not user_skills_dir.exists():
        raise FileNotFoundError(f"技能目录不存在: {user_skills_dir}")

    if not script_path.exists():
        raise FileNotFoundError(f"技能脚本不存在: {script_path}")

    # 构建命令: python run.py script_name.py args...
    cmd = ["python", str(script_path), script_name] + args

    # 使用 SubprocessRunner 执行
    runner = SubprocessRunner()
    return runner.run(cmd, timeout=timeout, env=env)
