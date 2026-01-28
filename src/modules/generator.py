"""模块B：文章生成"""

import os
import re
from pathlib import Path
from anthropic import Anthropic
from typing import List, Optional, Dict, Any
from ..models import SearchResult, Article
from . import retrieval
from ..utils import validate_temperature
from .agent_sdk import AgentSDKRunner
from ..hooks.log_generator import LogDocumentGenerator


def _create_anthropic_client(api_key: str) -> Anthropic:
    """
    Create Anthropic client with automatic API mode detection.

    Official API: Uses standard authentication via api_key parameter only
    MiniMax API: Uses custom base_url and Authorization header

    Detection: If ANTHROPIC_BASE_URL contains 'minimaxi.com', use MiniMax mode
    """
    base_url = os.getenv("ANTHROPIC_BASE_URL")

    if not base_url:
        # Official Anthropic API: standard configuration
        print("Using official Anthropic API")
        return Anthropic(api_key=api_key)

    if "minimaxi.com" in base_url:
        # MiniMax API: requires custom Authorization header
        print(f"Using MiniMax API: {base_url}")
        return Anthropic(
            api_key=api_key,
            base_url=base_url,
            default_headers={"Authorization": f"Bearer {api_key}"}
        )

    # Other third-party API
    print(f"Using third-party API: {base_url}")
    return Anthropic(api_key=api_key, base_url=base_url)


def generate(
    topic: str,
    search_results: List[SearchResult],
    api_key: str,
    model: str = os.getenv("MODEL_NAME", "claude-sonnet-4-20250514"),
    max_turns: int = 10,
    notebook_id: Optional[str] = None,
    notebook_url: Optional[str] = None,
    temperature: float = 0.7
) -> Article:
    """
    基于检索结果生成文章

    Args:
        topic: 文章主题
        search_results: 预先检索的结果列表
        api_key: Anthropic API Key
        model: 使用的模型
        max_turns: 最大对话轮数
        notebook_id: NotebookLM 笔记本 ID（用于追加检索）
        notebook_url: NotebookLM 笔记本 URL（用于追加检索）
        temperature: 生成温度参数

    Returns:
        生成的文章

    Raises:
        ValueError: API Key 无效
        RuntimeError: 生成失败
    """
    if not api_key:
        raise ValueError("请提供 ANTHROPIC_API_KEY")

    # 验证 temperature 参数
    temperature = validate_temperature(temperature)

    # 创建客户端，支持自定义 base_url
    client = _create_anthropic_client(api_key)

    # 构建系统提示词
    system_prompt = _get_system_prompt()

    # 构建初始用户消息，包含预先检索的结果
    user_message = _build_user_message(topic, search_results)

    messages = [{"role": "user", "content": user_message}]

    # 工具定义（允许 Agent 追加检索）
    tools = [{
        "name": "query_notebooklm",
        "description": "查询 NotebookLM 知识库获取更多相关信息、案例、观点等内容。当预先提供的素材不够，需要补充具体案例、数据或背景知识时使用此工具。",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "要查询的问题或关键词"
                }
            },
            "required": ["question"]
        }
    }]

    # Agent 循环
    for turn in range(max_turns):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                temperature=temperature,
                system=system_prompt,
                tools=tools,
                messages=messages
            )

            # 检查是否需要工具调用
            if response.stop_reason == "tool_use":
                # 添加助手消息
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })

                # 处理工具调用（追加检索）
                tool_results = []
                for content_block in response.content:
                    if content_block.type == "tool_use":
                        tool_name = content_block.name
                        tool_input = content_block.input

                        if tool_name == "query_notebooklm":
                            # 调用检索模块追加检索
                            try:
                                additional_results = retrieval.search(
                                    tool_input["question"],
                                    notebook_id=notebook_id,
                                    notebook_url=notebook_url
                                )
                                result_text = additional_results[0].content if additional_results else "未找到相关内容"
                            except Exception as e:
                                result_text = f"检索失败: {str(e)}"

                            # 收集工具结果
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": content_block.id,
                                "content": result_text
                            })

                # 添加工具结果
                messages.append({
                    "role": "user",
                    "content": tool_results
                })

            elif response.stop_reason == "end_turn":
                # Agent 完成任务，提取文本内容
                text_content = ""
                for content_block in response.content:
                    if hasattr(content_block, "text"):
                        text_content += content_block.text

                if text_content:
                    # 解析文章内容
                    return _parse_article(text_content, topic, search_results)
                else:
                    raise RuntimeError("生成的文章内容为空")

            else:
                # 其他停止原因
                text_content = ""
                for content_block in response.content:
                    if hasattr(content_block, "text"):
                        text_content += content_block.text

                if text_content:
                    return _parse_article(text_content, topic, search_results)
                else:
                    raise RuntimeError(f"意外的停止原因: {response.stop_reason}")

        except Exception as e:
            if turn == max_turns - 1:
                raise RuntimeError(f"生成失败: {str(e)}")
            # 继续下一轮

    # 达到最大轮次
    raise RuntimeError("达到最大轮次限制，生成未完成")


def _get_system_prompt(version: Optional[str] = None) -> str:
    """
    获取系统提示词

    从 write_prompt/ 目录读取 prompt 文件

    Args:
        version: Prompt 版本号（如 "V1", "V2"）
                 如果为 None，则从环境变量 PROMPT_VERSION 读取
                 默认使用 "V1"

    Returns:
        Prompt 文本内容

    优先级：
    1. 参数 version
    2. 环境变量 PROMPT_VERSION
    3. 默认值 "V1"

    示例：
        - _get_system_prompt()          → 使用 V1.md
        - _get_system_prompt("V2")      → 使用 V2.md
        - PROMPT_VERSION=V3 环境变量    → 使用 V3.md
    """
    # 确定使用哪个版本
    if version is None:
        version = os.getenv("PROMPT_VERSION", "V1")

    prompt_dir = Path(__file__).parent.parent.parent / "write_prompt"
    prompt_file = prompt_dir / f"{version}.md"

    # 尝试读取指定版本的 prompt
    try:
        with open(prompt_file, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"✅ 使用 Prompt 版本: {version} ({prompt_file.name})")
            return content
    except FileNotFoundError:
        print(f"⚠️ 警告：未找到 prompt 文件 {prompt_file}")

        # 尝试降级到 V1
        if version != "V1":
            fallback_file = prompt_dir / "V1.md"
            try:
                with open(fallback_file, 'r', encoding='utf-8') as f:
                    print(f"   降级使用: V1.md")
                    return f.read()
            except FileNotFoundError:
                pass

        # 最终降级：返回简化的默认 prompt
        print("   使用内置默认 prompt")
        return """你是一个专业的公众号文章写作助手。

请基于提供的素材，撰写高质量的公众号文章。

输出格式：
- 使用 Markdown 格式
- 标题使用 # 开头
- 正文分段清晰"""
    except Exception as e:
        print(f"⚠️ 错误：无法读取 prompt 文件 {prompt_file}: {e}")
        print("   使用内置默认 prompt")
        return """你是一个专业的公众号文章写作助手。

请基于提供的素材，撰写高质量的公众号文章。

输出格式：
- 使用 Markdown 格式
- 标题使用 # 开头
- 正文分段清晰"""


def _build_user_message(topic: str, search_results: List[SearchResult]) -> str:
    """
    构建包含检索结果的用户消息

    Args:
        topic: 文章主题
        search_results: 检索结果列表

    Returns:
        用户消息文本
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


def _parse_article(text: str, topic: str, search_results: List[SearchResult]) -> Article:
    """
    解析生成的文本，提取标题、正文和素材摘要

    Args:
        text: 生成的文本
        topic: 原始主题
        search_results: 使用的检索结果

    Returns:
        Article 对象
    """
    # 提取标题（第一个 # 开头的行）
    title_match = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()
        # 正文是标题之后的内容
        content = text
    else:
        # 如果没有找到标题，使用主题作为标题
        title = topic
        content = f"# {topic}\n\n{text}"

    # 生成素材来源摘要
    if search_results:
        source_summary = f"基于 {len(search_results)} 条检索结果生成"
        # 如果有来源信息，添加到摘要中
        sources_with_info = [r.source for r in search_results if r.source]
        if sources_with_info:
            source_summary += f"，来源包括: {', '.join(sources_with_info[:3])}"
            if len(sources_with_info) > 3:
                source_summary += " 等"
    else:
        source_summary = "无检索结果，基于 AI 理解生成"

    return Article(
        title=title,
        content=content,
        source_summary=source_summary
    )


async def generate_with_sdk(
    topic: str,
    search_results: List[SearchResult],
    api_key: str,
    model: str = os.getenv("MODEL_NAME", "claude-sonnet-4-20250514"),
    max_turns: int = 10,
    notebook_id: Optional[str] = None,
    notebook_url: Optional[str] = None,
    temperature: float = 0.7
) -> tuple[Article, Dict[str, Any]]:
    """
    使用Claude Agent SDK生成文章（带metrics）

    Args:
        topic: 文章主题
        search_results: 预先检索的结果列表
        api_key: Anthropic API Key
        model: 使用的模型
        max_turns: 最大对话轮数
        notebook_id: NotebookLM 笔记本 ID（用于追加检索）
        notebook_url: NotebookLM 笔记本 URL（用于追加检索）
        temperature: 生成温度参数

    Returns:
        (Article, metrics_dict)
        metrics_dict包含:
        - runtime_seconds: float
        - tool_call_count: int
        - total_tokens: int
        - prompt_tokens: int
        - completion_tokens: int
        - log_markdown: str

    Raises:
        ValueError: API Key 无效或参数错误
        RuntimeError: 生成失败
    """
    # 1. 验证 API Key
    if not api_key:
        raise ValueError("请提供 ANTHROPIC_API_KEY")

    # 2. 验证 temperature 参数
    temperature = validate_temperature(temperature)

    # 3. 创建 SDK runner
    runner = AgentSDKRunner(
        api_key=api_key,
        model=model,
        temperature=temperature,
        notebook_id=notebook_id,
        notebook_url=notebook_url
    )

    # 4. 获取系统提示词
    system_prompt = _get_system_prompt()

    # 5. 生成文章
    result_text, metrics = await runner.generate(
        topic=topic,
        search_results=search_results,
        system_prompt=system_prompt,
        max_turns=max_turns
    )

    # 6. 解析文章
    article = _parse_article(result_text, topic, search_results)

    # 7. 生成日志文档
    # 从环境变量读取配置（0或空表示不截断）
    max_result_length = int(os.getenv("LOG_MAX_RESULT_LENGTH", "0")) or None
    log_gen = LogDocumentGenerator(topic, metrics, max_result_length=max_result_length)
    log_markdown = log_gen.generate_markdown()

    # 8. 构建 metrics 字典
    metrics_dict = {
        'runtime_seconds': metrics.runtime_seconds,
        'tool_call_count': metrics.tool_call_count,
        'total_tokens': metrics.total_tokens,
        'prompt_tokens': metrics.prompt_tokens,
        'completion_tokens': metrics.completion_tokens,
        'log_markdown': log_markdown
    }

    return article, metrics_dict
