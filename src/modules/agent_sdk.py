"""Claude Agent SDK 封装模块"""
import os
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from claude_agent_sdk import query, ClaudeAgentOptions, HookMatcher
from ..hooks.logging_hooks import (
    pre_tool_use_hook,
    post_tool_use_hook,
    stop_hook,
    user_prompt_submit_hook
)


@dataclass
class AgentRunMetrics:
    """Agent 运行指标数据类"""

    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    errors: List[str] = field(default_factory=list)

    @property
    def runtime_seconds(self) -> float:
        """计算运行时长（秒）"""
        if self.end_time is not None:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    @property
    def tool_call_count(self) -> int:
        """返回工具调用次数"""
        return len(self.tool_calls)


class AgentSDKRunner:
    """Claude Agent SDK 运行器，集成hooks日志记录"""

    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float,
        notebook_id: Optional[str] = None,
        notebook_url: Optional[str] = None
    ):
        """
        初始化SDK运行器

        Args:
            api_key: Claude API密钥
            model: 模型名称
            temperature: 温度参数
            notebook_id: NotebookLM笔记本ID（可选）
            notebook_url: NotebookLM笔记本URL（可选）
        """
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.notebook_id = notebook_id
        self.notebook_url = notebook_url

    def _get_tools_config(self) -> List[Dict[str, Any]]:
        """
        获取工具配置

        Returns:
            工具定义列表（若无NotebookLM则为空列表）
        """
        if not self.notebook_id:
            return []

        return [{
            "name": "query_notebooklm",
            "type": "custom",
            "description": "Query NotebookLM for information from uploaded sources",
            "input_schema": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question to ask NotebookLM"
                    }
                },
                "required": ["question"]
            }
        }]

    def _build_user_message(
        self,
        topic: str,
        search_results: List[Any]
    ) -> str:
        """
        构建用户消息

        Args:
            topic: 文章主题
            search_results: 搜索结果列表

        Returns:
            构建的用户消息字符串
        """
        message = f"选题：{topic}\n\n"

        if search_results:
            message += "已为你检索到以下素材：\n\n"
            for i, result in enumerate(search_results, 1):
                message += f"【素材 {i}】\n{result.content}\n\n"
                if result.source:
                    message += f"来源：{result.source}\n\n"

            message += "请基于以上素材，结合你的理解，撰写一篇高质量的公众号文章。"
        else:
            message += "未检索到相关素材，请基于你的理解撰写文章，必要时可以使用工具追加检索。"

        return message

    def _create_hooks(self, metrics: AgentRunMetrics) -> Dict[str, Any]:
        """
        创建hooks配置，注入metrics实例

        Args:
            metrics: AgentRunMetrics实例

        Returns:
            hooks配置字典
        """
        # 使用lambda闭包注入metrics
        return {
            "PreToolUse": [
                HookMatcher(
                    hooks=[lambda input_data, tool_use_id, context: pre_tool_use_hook(
                        input_data, tool_use_id, context, metrics
                    )]
                )
            ],
            "PostToolUse": [
                HookMatcher(
                    hooks=[lambda input_data, tool_use_id, context: post_tool_use_hook(
                        input_data, tool_use_id, context, metrics
                    )]
                )
            ],
            "Stop": [
                HookMatcher(
                    hooks=[lambda input_data, tool_use_id, context: stop_hook(
                        input_data, tool_use_id, context, metrics
                    )],
                    timeout=180  # 3分钟超时
                )
            ],
            "UserPromptSubmit": [
                HookMatcher(
                    hooks=[lambda input_data, tool_use_id, context: user_prompt_submit_hook(
                        input_data, tool_use_id, context, metrics
                    )]
                )
            ]
        }

    async def generate(
        self,
        topic: str,
        search_results: List[Any],
        system_prompt: str,
        max_turns: int = 10
    ) -> tuple[str, AgentRunMetrics]:
        """
        生成文章内容

        Args:
            topic: 文章主题
            search_results: 搜索结果列表
            system_prompt: 系统提示词
            max_turns: 最大轮次

        Returns:
            (生成的文章文本, AgentRunMetrics实例)
        """
        # 创建metrics实例
        metrics = AgentRunMetrics()

        # 构建用户消息
        user_message = self._build_user_message(topic, search_results)

        # 获取工具配置
        tools = self._get_tools_config()

        # 创建hooks配置
        hooks = self._create_hooks(metrics)

        # 配置SDK options
        env_vars = {}
        if os.getenv("ANTHROPIC_BASE_URL"):
            env_vars["ANTHROPIC_BASE_URL"] = os.getenv("ANTHROPIC_BASE_URL")

        options = ClaudeAgentOptions(
            model=self.model,
            max_turns=max_turns,
            tools=tools if tools else None,
            hooks=hooks,
            system_prompt=system_prompt,
            env=env_vars
        )

        # 调用SDK query
        result_text = ""
        async for message in query(prompt=user_message, options=options):
            if hasattr(message, 'text') and message.text:
                result_text += message.text

            # 更新token统计（如果可用）
            if hasattr(message, 'usage'):
                metrics.total_tokens = getattr(message.usage, 'total_tokens', 0)
                metrics.prompt_tokens = getattr(message.usage, 'prompt_tokens', 0)
                metrics.completion_tokens = getattr(message.usage, 'completion_tokens', 0)

        # 标记结束时间
        metrics.end_time = time.time()

        return result_text, metrics
