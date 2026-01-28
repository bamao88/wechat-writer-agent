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
    system_prompt: Optional[str] = None  # 系统提示词
    initial_user_message: Optional[str] = None  # 初始用户消息
    messages: List[Dict[str, Any]] = field(default_factory=list)  # 对话消息流

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

    def _get_allowed_tools(self) -> List[str]:
        """
        Get list of allowed tools for SDK.

        Returns:
            List of tool categories to enable. Uses "Skill" to enable
            all Skills discovered from setting_sources directories.
        """
        if not self.notebook_id:
            print("[WARNING] notebook_id not set, NotebookLM tool not registered")
            print("  Hint: Set NOTEBOOK_ID in .env to enable tool calling")
            return []

        print(f"[INFO] Enabling Skill discovery (notebook_id={self.notebook_id[:20]}...)")
        # Return "Skill" to enable all Skills from setting_sources
        # SDK will auto-discover tools from ~/.claude/skills/ and .claude/skills/
        return ["Skill"]

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

        # 存储system prompt和初始消息
        metrics.system_prompt = system_prompt

        # 构建用户消息
        user_message = self._build_user_message(topic, search_results)
        metrics.initial_user_message = user_message

        # 获取工具配置
        allowed_tools = self._get_allowed_tools()

        # 创建hooks配置
        hooks = self._create_hooks(metrics)

        # 配置SDK options
        env_vars = {}
        if os.getenv("ANTHROPIC_BASE_URL"):
            env_vars["ANTHROPIC_BASE_URL"] = os.getenv("ANTHROPIC_BASE_URL")

        options = ClaudeAgentOptions(
            model=self.model,
            max_turns=max_turns,
            setting_sources=["user"],  # Load Skills from ~/.claude/skills/
            allowed_tools=allowed_tools if allowed_tools else None,  # Enable Skill discovery
            hooks=hooks,
            system_prompt=system_prompt,
            env=env_vars
        )

        # 调用SDK query
        result_text = ""
        async for message in query(prompt=user_message, options=options):
            # 记录消息到messages流
            message_record = {
                'timestamp': time.time(),
                'type': type(message).__name__,
            }

            # ResultMessage 包含最终结果
            if hasattr(message, 'result'):
                result_text = message.result
                if result_text is not None:
                    message_record['result'] = result_text
                    message_record['result_length'] = len(result_text)

            # 更新token统计（如果可用）
            if hasattr(message, 'usage') and message.usage:
                message_record['usage'] = message.usage
                # usage 是一个字典
                if isinstance(message.usage, dict):
                    input_tokens = message.usage.get('input_tokens', 0)
                    cache_read_tokens = message.usage.get('cache_read_input_tokens', 0)
                    output_tokens = message.usage.get('output_tokens', 0)

                    # 总输入 = 新输入 + 缓存读取
                    metrics.prompt_tokens = input_tokens + cache_read_tokens
                    metrics.completion_tokens = output_tokens
                    metrics.total_tokens = metrics.prompt_tokens + metrics.completion_tokens

            # 记录stop_reason（如果有）
            if hasattr(message, 'stop_reason'):
                message_record['stop_reason'] = message.stop_reason

            # 添加到messages列表
            metrics.messages.append(message_record)

        # 标记结束时间
        metrics.end_time = time.time()

        return result_text, metrics
