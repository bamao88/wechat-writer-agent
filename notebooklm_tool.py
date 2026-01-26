"""
NotebookLM 工具接口
提供查询 NotebookLM 知识库的功能
"""
import subprocess
import json
import sys
from typing import Optional
from pathlib import Path


class NotebookLMTool:
    """NotebookLM 查询工具"""

    def __init__(self, notebook_id: Optional[str] = None, notebook_url: Optional[str] = None):
        """
        初始化 NotebookLM 工具

        Args:
            notebook_id: NotebookLM 笔记本 ID（从库中获取）
            notebook_url: NotebookLM 笔记本 URL（直接指定）
        """
        self.notebook_id = notebook_id
        self.notebook_url = notebook_url
        self.skill_dir = Path.home() / ".claude" / "skills" / "notebooklm"
        self.run_script = self.skill_dir / "scripts" / "run.py"

        # 验证 skill 是否已安装
        if not self.skill_dir.exists():
            raise ValueError(
                f"NotebookLM skill 未安装。请先安装：\n"
                f"mkdir -p ~/.claude/skills && cd ~/.claude/skills && "
                f"git clone https://github.com/PleasePrompto/notebooklm-skill notebooklm"
            )

    def query(self, question: str) -> str:
        """
        查询 NotebookLM 知识库

        Args:
            question: 查询问题

        Returns:
            查询结果文本
        """
        try:
            # 构建命令行参数
            cmd = [
                sys.executable,
                str(self.run_script),
                "ask_question.py",
                "--question", question
            ]

            # 添加 notebook 参数
            if self.notebook_url:
                cmd.extend(["--notebook-url", self.notebook_url])
            elif self.notebook_id:
                cmd.extend(["--notebook-id", self.notebook_id])
            # 如果都没有，脚本会自动使用 active notebook

            # 调用脚本
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=180  # 3分钟超时
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                if "Not authenticated" in error_msg:
                    return (
                        "⚠️ NotebookLM 未认证。请先运行认证设置：\n"
                        f"python {self.run_script} auth_manager.py setup"
                    )
                elif "No notebooks in library" in error_msg or "not found" in error_msg:
                    return (
                        "⚠️ 未找到笔记本。请先添加笔记本到库中：\n"
                        f"python {self.run_script} notebook_manager.py add --url YOUR_NOTEBOOK_URL --name NAME"
                    )
                else:
                    return f"查询失败: {error_msg}"

            # 提取答案
            # 脚本输出格式：Question: xxx \n === \n answer \n ===
            output = result.stdout

            # 查找分隔符之间的内容
            lines = output.split('\n')
            answer_lines = []
            in_answer = False

            for line in lines:
                if '=' * 10 in line:
                    if not in_answer:
                        in_answer = True
                    else:
                        break
                elif in_answer and line.strip():
                    # 跳过 "Question:" 行
                    if not line.startswith("Question:"):
                        answer_lines.append(line)

            answer = '\n'.join(answer_lines).strip()

            # 移除 follow-up reminder（如果存在）
            if "EXTREMELY IMPORTANT" in answer:
                answer = answer.split("EXTREMELY IMPORTANT")[0].strip()

            return answer if answer else output

        except subprocess.TimeoutExpired:
            return "查询超时（3分钟），NotebookLM 可能正在处理较复杂的问题。"
        except Exception as e:
            return f"查询失败: {str(e)}"

    def get_tool_definition(self) -> dict:
        """
        返回工具定义（用于 Claude Agent SDK）
        """
        return {
            "name": "query_notebooklm",
            "description": "查询 NotebookLM 知识库获取相关信息、案例、观点等内容。当需要补充具体案例、数据、引用之前的观点或背景知识时使用此工具。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "要查询的问题或关键词，例如：'关于 AI 产品的案例'、'我对内容创作的看法'"
                    }
                },
                "required": ["question"]
            }
        }


def create_notebooklm_tool(
    notebook_id: Optional[str] = None,
    notebook_url: Optional[str] = None
) -> NotebookLMTool:
    """
    创建 NotebookLM 工具实例

    Args:
        notebook_id: NotebookLM 笔记本 ID（从库中获取，优先级低于 URL）
        notebook_url: NotebookLM 笔记本 URL（直接指定，优先级高）

    Returns:
        NotebookLMTool 实例

    Note:
        如果都不提供，将使用 NotebookLM 库中的 active notebook
    """
    return NotebookLMTool(notebook_id=notebook_id, notebook_url=notebook_url)
