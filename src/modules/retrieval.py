"""模块A：NotebookLM 检索"""

import subprocess
import sys
from typing import List, Optional
from pathlib import Path
from ..models import SearchResult


def search(
    query: str,
    notebook_id: Optional[str] = None,
    notebook_url: Optional[str] = None
) -> List[SearchResult]:
    """
    从 NotebookLM 检索相关内容

    Args:
        query: 检索问题
        notebook_id: 笔记本 ID（可选）
        notebook_url: 笔记本 URL（可选）

    Returns:
        检索结果列表

    Raises:
        ValueError: NotebookLM skill 未安装
        TimeoutError: 查询超时
        RuntimeError: 查询失败
    """
    # 验证 skill 是否已安装
    skill_dir = Path.home() / ".claude" / "skills" / "notebooklm"
    run_script = skill_dir / "scripts" / "run.py"

    if not skill_dir.exists():
        raise ValueError(
            f"NotebookLM skill 未安装。请先安装：\n"
            f"mkdir -p ~/.claude/skills && cd ~/.claude/skills && "
            f"git clone https://github.com/PleasePrompto/notebooklm-skill notebooklm"
        )

    try:
        # 构建命令行参数
        cmd = [
            sys.executable,
            str(run_script),
            "ask_question.py",
            "--question", query
        ]

        # 添加 notebook 参数
        if notebook_url:
            cmd.extend(["--notebook-url", notebook_url])
        elif notebook_id:
            cmd.extend(["--notebook-id", notebook_id])
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
                raise RuntimeError(
                    "NotebookLM 未认证。请先运行认证设置：\n"
                    f"python {run_script} auth_manager.py setup"
                )
            elif "No notebooks in library" in error_msg or "not found" in error_msg:
                raise RuntimeError(
                    "未找到笔记本。请先添加笔记本到库中：\n"
                    f"python {run_script} notebook_manager.py add --url YOUR_NOTEBOOK_URL --name NAME"
                )
            else:
                raise RuntimeError(f"查询失败: {error_msg}")

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

        if not answer:
            answer = output

        # 返回结构化结果
        # NotebookLM 目前不提供结构化的来源信息，所以 source 为空
        # 整个答案作为一个 SearchResult 返回
        if answer:
            return [SearchResult(content=answer, source="")]
        else:
            return []

    except subprocess.TimeoutExpired:
        raise TimeoutError("查询超时（3分钟），NotebookLM 可能正在处理较复杂的问题。")
    except (ValueError, RuntimeError, TimeoutError):
        # 重新抛出已知异常
        raise
    except Exception as e:
        raise RuntimeError(f"查询失败: {str(e)}")
