"""日志文档生成器 - 从metrics生成markdown格式日志"""
import json
from datetime import datetime
from typing import Any


class LogDocumentGenerator:
    """日志文档生成器"""

    def __init__(self, topic: str, metrics: Any):
        """
        初始化日志生成器

        Args:
            topic: 文章主题
            metrics: AgentRunMetrics实例
        """
        self.topic = topic
        self.metrics = metrics
        self.timestamp = datetime.now()

    def generate_markdown(self) -> str:
        """
        生成markdown格式的日志文档

        Returns:
            markdown格式的日志文本
        """
        # 构建文档头部
        md = f"""# Agent Run Log

**Topic**: {self.topic}
**Timestamp**: {self.timestamp.strftime("%Y-%m-%d %H:%M:%S")}
**Runtime**: {self.metrics.runtime_seconds:.2f} seconds
**Tool Calls**: {self.metrics.tool_call_count}

---

## Execution Summary

- **Total Tokens**: {self.metrics.total_tokens}
- **Prompt Tokens**: {self.metrics.prompt_tokens}
- **Completion Tokens**: {self.metrics.completion_tokens}
- **Start Time**: {datetime.fromtimestamp(self.metrics.start_time).strftime("%H:%M:%S")}
"""

        # 添加结束时间（如果存在）
        if self.metrics.end_time:
            md += f"- **End Time**: {datetime.fromtimestamp(self.metrics.end_time).strftime('%H:%M:%S')}\n"

        md += "\n---\n\n"

        # 添加工具调用章节
        if self.metrics.tool_calls:
            md += "## Tool Calls\n\n"

            for idx, call in enumerate(self.metrics.tool_calls, 1):
                tool_name = call.get('tool_name', 'Unknown')
                tool_use_id = call.get('tool_use_id', 'N/A')
                duration_ms = call.get('duration_ms', 0)

                md += f"""### Tool Call {idx}: {tool_name}

**Tool Use ID**: `{tool_use_id}`
**Duration**: {duration_ms:.2f}ms

"""

                # 添加输入（JSON格式）
                tool_input = call.get('input', {})
                if tool_input:
                    md += "**Input**:\n```json\n"
                    md += json.dumps(tool_input, indent=2, ensure_ascii=False)
                    md += "\n```\n\n"

                # 添加结果预览（限制500字符）
                result = call.get('result', 'N/A')
                if result:
                    result_str = str(result)
                    if len(result_str) > 500:
                        result_str = result_str[:500] + "..."

                    md += f"""**Result Preview**:
```
{result_str}
```

---

"""

        # 添加错误章节（如果有）
        if self.metrics.errors:
            md += "\n## Errors\n\n"
            for error in self.metrics.errors:
                md += f"- {error}\n"

        return md
