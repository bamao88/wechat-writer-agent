"""日志文档生成器 - 从metrics生成markdown格式日志"""
import json
import os
from datetime import datetime
from typing import Any, Optional


class LogDocumentGenerator:
    """日志文档生成器"""

    def __init__(self, topic: str, metrics: Any, max_result_length: Optional[int] = None):
        """
        初始化日志生成器

        Args:
            topic: 文章主题
            metrics: AgentRunMetrics实例
            max_result_length: 工具结果最大长度（None表示不截断）
        """
        self.topic = topic
        self.metrics = metrics
        self.timestamp = datetime.now()
        self.max_result_length = max_result_length

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

## Configuration Summary

- **Notebook ID**: {os.getenv('NOTEBOOK_ID', 'Not set')}
- **Notebook URL**: {os.getenv('NOTEBOOK_URL', 'Not set')}
- **USE_AGENT_SDK**: {os.getenv('USE_AGENT_SDK', 'true')}

"""

        # 添加工具调用诊断提示
        if self.metrics.tool_call_count == 0:
            if not os.getenv('NOTEBOOK_ID'):
                md += "> ⚠️ **工具调用为0原因**: Notebook ID未设置，工具未注册\n\n"
            else:
                md += "> ✅ **工具调用为0原因**: Agent智能决策（预检索结果充分）\n\n"

        md += """---

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

        # 添加Prompts章节
        md += "## Prompts\n\n"

        if self.metrics.system_prompt:
            md += "### System Prompt\n\n"
            md += f"```\n{self.metrics.system_prompt}\n```\n\n"

        if self.metrics.initial_user_message:
            md += "### Initial User Message\n\n"
            preview_length = 1000
            msg = self.metrics.initial_user_message
            if len(msg) > preview_length:
                md += f"```\n{msg[:preview_length]}...\n```\n\n"
                md += f"**完整长度**: {len(msg)} 字符\n\n"
            else:
                md += f"```\n{msg}\n```\n\n"

        md += "---\n\n"

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

                # 添加结果预览（可配置截断）
                result = call.get('result', 'N/A')
                if result:
                    result_str = str(result)
                    if self.max_result_length is not None and len(result_str) > self.max_result_length:
                        result_str = result_str[:self.max_result_length] + f"...\n\n(完整长度: {len(str(result))} 字符)"

                    md += f"""**Result Preview**:
```
{result_str}
```

---

"""

        # 添加对话消息流章节（如果有）
        if self.metrics.messages:
            md += "\n## Messages Flow\n\n"
            md += f"**总消息数**: {len(self.metrics.messages)}\n\n"

            for idx, msg in enumerate(self.metrics.messages, 1):
                msg_type = msg.get('type', 'Unknown')
                timestamp = datetime.fromtimestamp(msg.get('timestamp', 0))

                md += f"### Message {idx}: {msg_type}\n\n"
                md += f"**时间**: {timestamp.strftime('%H:%M:%S')}\n\n"

                if 'stop_reason' in msg:
                    md += f"**Stop Reason**: {msg['stop_reason']}\n\n"

                if 'result_length' in msg:
                    md += f"**内容长度**: {msg['result_length']} 字符\n\n"

                if 'usage' in msg:
                    usage = msg['usage']
                    if isinstance(usage, dict):
                        md += f"**Token使用**:\n"
                        if 'input_tokens' in usage:
                            md += f"- Input: {usage['input_tokens']}\n"
                        if 'cache_read_input_tokens' in usage:
                            md += f"- Cache Read: {usage['cache_read_input_tokens']}\n"
                        if 'output_tokens' in usage:
                            md += f"- Output: {usage['output_tokens']}\n"
                        md += "\n"

                md += "---\n\n"

        # 添加错误章节（如果有）
        if self.metrics.errors:
            md += "\n## Errors\n\n"
            for error in self.metrics.errors:
                md += f"- {error}\n"

        return md
