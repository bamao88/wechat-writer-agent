"""
带详细日志记录的文章生成脚本
记录所有检索内容、生成轮次、API 调用详情
"""
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from src.modules import retrieval, generator
from src.models import SearchResult
import re


class DetailedLogger:
    """详细日志记录器"""

    def __init__(self, topic: str):
        self.topic = topic
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = f"logs/generation_{self.timestamp}.md"
        self.logs = []

        # 创建日志目录
        os.makedirs("logs", exist_ok=True)

        # 初始化日志文件
        self._write_header()

    def _write_header(self):
        """写入日志头部"""
        header = f"""# 文章生成详细日志

**选题**: {self.topic}
**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**日志文件**: {self.log_file}

---

"""
        self._append_log(header)

    def _append_log(self, content: str):
        """追加日志内容"""
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(content)

    def log_section(self, title: str, content: str = ""):
        """记录章节"""
        section = f"\n## {title}\n\n{content}\n"
        self._append_log(section)
        print(f"\n{'='*60}")
        print(f"{title}")
        print('='*60)

    def log_subsection(self, title: str, content: str = ""):
        """记录子章节"""
        section = f"\n### {title}\n\n{content}\n"
        self._append_log(section)
        print(f"\n{title}")
        print('-'*40)

    def log_retrieval_start(self, query: str, notebook_id: str = None, notebook_url: str = None):
        """记录检索开始"""
        self.log_section("📚 阶段 1: NotebookLM 检索")

        info = f"**检索查询**: {query}\n"
        if notebook_id:
            info += f"**Notebook ID**: {notebook_id}\n"
        if notebook_url:
            info += f"**Notebook URL**: {notebook_url}\n"
        info += f"**开始时间**: {datetime.now().strftime('%H:%M:%S')}\n"

        self._append_log(info)
        print(info)

    def log_retrieval_results(self, results: list):
        """记录检索结果"""
        self.log_subsection(f"检索结果 (共 {len(results)} 条)")

        if not results:
            self._append_log("⚠️ **未检索到任何结果**\n")
            print("⚠️ 未检索到任何结果")
            return

        for i, result in enumerate(results, 1):
            result_text = f"\n#### 素材 {i}\n\n"
            result_text += f"**来源**: {result.source or '无来源信息'}\n\n"
            result_text += f"**内容**:\n```\n{result.content[:500]}{'...' if len(result.content) > 500 else ''}\n```\n"
            result_text += f"\n**完整长度**: {len(result.content)} 字符\n"

            self._append_log(result_text)
            print(f"\n素材 {i}: {result.source or '无来源'}")
            print(f"长度: {len(result.content)} 字符")

    def log_generation_start(self, search_results: list, model: str):
        """记录生成开始"""
        self.log_section("✍️ 阶段 2: 文章生成")

        info = f"**使用模型**: {model}\n"
        info += f"**输入素材数**: {len(search_results)} 条\n"
        info += f"**开始时间**: {datetime.now().strftime('%H:%M:%S')}\n"
        info += f"**最大轮次**: 10\n"

        self._append_log(info)
        print(info)

    def log_turn(self, turn: int, request_type: str, details: str):
        """记录单个轮次"""
        self.log_subsection(f"🔄 第 {turn} 轮 - {request_type}")

        turn_info = f"**时间**: {datetime.now().strftime('%H:%M:%S')}\n\n"
        turn_info += f"{details}\n"

        self._append_log(turn_info)
        print(f"\n第 {turn} 轮: {request_type}")

    def log_final_article(self, article):
        """记录最终文章"""
        self.log_section("📄 生成结果")

        result = f"**标题**: {article.title}\n\n"
        result += f"**字数**: {len(article.content)} 字符\n\n"
        result += f"**素材摘要**: {article.source_summary}\n\n"
        result += f"---\n\n**完整内容**:\n\n{article.content}\n"

        self._append_log(result)

        print(f"\n标题: {article.title}")
        print(f"字数: {len(article.content)} 字符")
        print(f"素材摘要: {article.source_summary}")

    def log_error(self, error: Exception):
        """记录错误"""
        self.log_section("❌ 错误信息")

        error_info = f"**错误类型**: {type(error).__name__}\n\n"
        error_info += f"**错误信息**: {str(error)}\n\n"

        import traceback
        error_info += f"**堆栈跟踪**:\n```\n{traceback.format_exc()}\n```\n"

        self._append_log(error_info)
        print(f"\n❌ 错误: {str(error)}")


def generate_with_detailed_logs(
    topic: str,
    api_key: str,
    model: str = "claude-3-5-sonnet-20241022",
    notebook_id: str = None,
    notebook_url: str = None
):
    """
    带详细日志的文章生成

    Args:
        topic: 文章主题
        api_key: Anthropic API Key
        model: 使用的模型
        notebook_id: NotebookLM 笔记本 ID
        notebook_url: NotebookLM 笔记本 URL

    Returns:
        生成的文章对象
    """
    logger = DetailedLogger(topic)

    try:
        # 阶段 1: 检索
        logger.log_retrieval_start(topic, notebook_id, notebook_url)

        search_results = retrieval.search(
            query=topic,
            notebook_id=notebook_id,
            notebook_url=notebook_url
        )

        logger.log_retrieval_results(search_results)

        # 阶段 2: 生成（需要包装 generator 来记录详细轮次）
        logger.log_generation_start(search_results, model)

        # 调用生成器（这里我们需要手动记录每一轮）
        article = generator_with_logs(
            topic=topic,
            search_results=search_results,
            api_key=api_key,
            model=model,
            notebook_id=notebook_id,
            notebook_url=notebook_url,
            logger=logger
        )

        # 记录最终结果
        logger.log_final_article(article)

        print(f"\n✅ 生成完成！详细日志已保存到: {logger.log_file}")

        return article, logger.log_file

    except Exception as e:
        logger.log_error(e)
        raise


def generator_with_logs(
    topic: str,
    search_results: list,
    api_key: str,
    model: str,
    notebook_id: str,
    notebook_url: str,
    logger: DetailedLogger,
    max_turns: int = 10
):
    """
    带日志记录的生成器包装
    """
    from anthropic import Anthropic
    import os

    if not api_key:
        raise ValueError("请提供 ANTHROPIC_API_KEY")

    # 处理自定义 base_url
    base_url = os.getenv("ANTHROPIC_BASE_URL")
    if base_url:
        # 确保 base_url 格式正确
        if base_url.endswith('/v1'):
            base_url = base_url[:-3]  # 移除末尾的 /v1
        logger._append_log(f"\n**使用自定义 base_url**: {base_url}\n")
        print(f"\n使用自定义 base_url: {base_url}")
        client = Anthropic(api_key=api_key, base_url=base_url)
    else:
        client = Anthropic(api_key=api_key)

    # 构建系统提示词
    system_prompt = generator._get_system_prompt()

    # 构建初始用户消息
    user_message = generator._build_user_message(topic, search_results)

    # 记录初始消息
    logger.log_subsection("📝 初始提示")
    logger._append_log(f"**系统提示词长度**: {len(system_prompt)} 字符\n\n")
    logger._append_log(f"**用户消息**:\n```\n{user_message[:1000]}{'...' if len(user_message) > 1000 else ''}\n```\n")

    messages = [{"role": "user", "content": user_message}]

    # 工具定义
    tools = [{
        "name": "query_notebooklm",
        "description": "查询 NotebookLM 知识库获取更多相关信息、案例、观点等内容。",
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
            # 记录请求
            logger.log_turn(turn + 1, "API 请求", f"发送请求到模型 {model}...")

            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=system_prompt,
                tools=tools,
                messages=messages
            )

            # 记录响应
            response_details = f"**停止原因**: {response.stop_reason}\n"
            response_details += f"**内容块数量**: {len(response.content)}\n\n"

            # 检查是否需要工具调用
            if response.stop_reason == "tool_use":
                # 添加助手消息
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })

                # 处理工具调用
                tool_results = []
                for content_block in response.content:
                    if content_block.type == "tool_use":
                        tool_name = content_block.name
                        tool_input = content_block.input

                        response_details += f"**工具调用**: {tool_name}\n"
                        response_details += f"**查询问题**: {tool_input.get('question', 'N/A')}\n\n"

                        if tool_name == "query_notebooklm":
                            try:
                                additional_results = retrieval.search(
                                    tool_input["question"],
                                    notebook_id=notebook_id,
                                    notebook_url=notebook_url
                                )
                                result_text = additional_results[0].content if additional_results else "未找到相关内容"

                                response_details += f"**检索结果长度**: {len(result_text)} 字符\n"
                                response_details += f"**检索结果预览**: {result_text[:200]}...\n"
                            except Exception as e:
                                result_text = f"检索失败: {str(e)}"
                                response_details += f"**检索失败**: {str(e)}\n"

                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": content_block.id,
                                "content": result_text
                            })

                logger._append_log(response_details)

                # 添加工具结果
                messages.append({
                    "role": "user",
                    "content": tool_results
                })

            elif response.stop_reason == "end_turn":
                # Agent 完成任务
                text_content = ""
                for content_block in response.content:
                    if hasattr(content_block, "text"):
                        text_content += content_block.text

                response_details += f"**生成内容长度**: {len(text_content)} 字符\n"
                response_details += f"**内容预览**: {text_content[:200]}...\n"

                logger._append_log(response_details)

                if text_content:
                    # 解析文章内容
                    return generator._parse_article(text_content, topic, search_results)
                else:
                    raise RuntimeError("生成的文章内容为空")

            else:
                # 其他停止原因
                text_content = ""
                for content_block in response.content:
                    if hasattr(content_block, "text"):
                        text_content += content_block.text

                response_details += f"**生成内容长度**: {len(text_content)} 字符\n"
                logger._append_log(response_details)

                if text_content:
                    return generator._parse_article(text_content, topic, search_results)
                else:
                    raise RuntimeError(f"意外的停止原因: {response.stop_reason}")

        except Exception as e:
            logger._append_log(f"\n⚠️ **第 {turn + 1} 轮出错**: {str(e)}\n")
            if turn == max_turns - 1:
                raise RuntimeError(f"生成失败: {str(e)}")

    # 达到最大轮次
    raise RuntimeError("达到最大轮次限制，生成未完成")


def main():
    """主函数"""
    # 加载环境变量
    load_dotenv()

    # 检查 API Key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ 错误：未设置 ANTHROPIC_API_KEY")
        print("请在 .env 文件中设置 ANTHROPIC_API_KEY")
        return

    # 获取模型配置
    model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

    print("\n" + "="*60)
    print("🚀 带详细日志的文章生成器")
    print("="*60)

    # 选题
    topic = "产品经理如何做技术选型调研"

    print(f"\n📝 选题: {topic}")
    print(f"🤖 模型: {model}")
    print(f"📚 使用 NotebookLM 检索")

    try:
        # 生成文章
        article, log_file = generate_with_detailed_logs(
            topic=topic,
            api_key=api_key,
            model=model
        )

        # 保存文章到单独文件
        article_file = f"generated/{topic.replace(' ', '_').replace('/', '_')}.md"
        os.makedirs("generated", exist_ok=True)

        with open(article_file, "w", encoding="utf-8") as f:
            f.write(article.content)

        print(f"\n✅ 文章已保存到: {article_file}")
        print(f"📋 详细日志: {log_file}")

        print("\n" + "="*60)
        print("生成完成！")
        print("="*60)

    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
