"""
带详细日志记录的文章生成脚本（使用 OpenAI 兼容 API 调用 Claude）
记录所有检索内容、生成轮次、API 调用详情
"""
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from src.modules import retrieval
from src.models import SearchResult, Article
import re


class DetailedLogger:
    """详细日志记录器"""

    def __init__(self, topic: str, prompt_name: str = "default"):
        self.topic = topic
        self.prompt_name = prompt_name
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = f"logs/generation_{self.timestamp}_{prompt_name}.md"
        self.logs = []

        # 创建日志目录
        os.makedirs("logs", exist_ok=True)

        # 初始化日志文件
        self._write_header()

    def _write_header(self):
        """写入日志头部"""
        header = f"""# 文章生成详细日志

**选题**: {self.topic}
**提示词**: {self.prompt_name}
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

    def log_retrieval_start(self, query: str):
        """记录检索开始"""
        self.log_section("📚 阶段 1: NotebookLM 检索")

        info = f"**检索查询**: {query}\n"
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
        info += f"**API 格式**: OpenAI 兼容接口\n"

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
    base_url: str,
    model: str = "claude-sonnet-4-5-20250929",
    system_prompt: str = "",
    prompt_name: str = "default"
):
    """
    带详细日志的文章生成（使用 OpenAI 兼容接口）

    Args:
        topic: 文章主题
        api_key: API Key
        base_url: API Base URL
        model: 使用的模型
        system_prompt: 系统提示词
        prompt_name: 提示词名称

    Returns:
        生成的文章对象和日志文件路径
    """
    logger = DetailedLogger(topic, prompt_name)

    try:
        # 阶段 1: 检索
        logger.log_retrieval_start(topic)

        search_results = retrieval.search(query=topic)

        logger.log_retrieval_results(search_results)

        # 阶段 2: 生成
        logger.log_generation_start(search_results, model)

        # 调用生成器
        article = generator_with_logs(
            topic=topic,
            search_results=search_results,
            api_key=api_key,
            base_url=base_url,
            model=model,
            logger=logger,
            system_prompt=system_prompt
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
    base_url: str,
    model: str,
    logger: DetailedLogger,
    system_prompt: str
):
    """
    带日志记录的生成器（使用 OpenAI SDK）

    Args:
        topic: 文章主题
        search_results: 检索结果列表
        api_key: API Key
        base_url: API Base URL
        model: 使用的模型
        logger: 日志记录器
        system_prompt: 系统提示词
    """
    from openai import OpenAI

    if not api_key:
        raise ValueError("请提供 API_KEY")

    # 创建 OpenAI 客户端（增加超时时间）
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=120.0,  # 增加到 120 秒
        max_retries=2   # 自动重试 2 次
    )

    logger._append_log(f"\n**API Base URL**: {base_url}\n")
    logger._append_log(f"**使用模型**: {model}\n\n")

    # 构建用户消息（限制每条素材最多 2000 字符）
    user_message = f"选题：{topic}\n\n"
    if search_results:
        user_message += "已为你检索到以下素材：\n\n"
        for i, result in enumerate(search_results, 1):
            # 限制每条素材的长度
            content = result.content[:2000] if len(result.content) > 2000 else result.content
            user_message += f"【素材 {i}】\n{content}\n\n"
            if result.source:
                user_message += f"来源：{result.source}\n\n"
        user_message += "请基于以上素材，结合你的理解，撰写一篇高质量的公众号文章。"
    else:
        user_message += "未检索到相关素材，请基于你的理解撰写文章。"

    # 记录初始消息
    logger.log_subsection("📝 初始提示")
    logger._append_log(f"**系统提示词长度**: {len(system_prompt)} 字符\n\n")
    logger._append_log(f"**用户消息长度**: {len(user_message)} 字符\n\n")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]

    # 调用 API
    turn = 1
    logger.log_turn(turn, "API 请求", f"发送请求到模型 {model}...")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=4096,
            temperature=0.7
        )

        # 提取生成的内容
        text_content = response.choices[0].message.content

        # 记录响应
        response_details = f"**完成原因**: {response.choices[0].finish_reason}\n"
        response_details += f"**生成内容长度**: {len(text_content)} 字符\n"
        response_details += f"**Token 使用**: prompt={response.usage.prompt_tokens}, completion={response.usage.completion_tokens}, total={response.usage.total_tokens}\n"
        response_details += f"\n**内容预览**:\n```\n{text_content[:300]}...\n```\n"

        logger._append_log(response_details)

        # 解析文章
        article = _parse_article(text_content, topic, search_results)

        return article

    except Exception as e:
        logger._append_log(f"\n⚠️ **生成出错**: {str(e)}\n")
        raise RuntimeError(f"生成失败: {str(e)}")


def _parse_article(text: str, topic: str, search_results: list) -> Article:
    """
    解析生成的文本，提取标题、正文和素材摘要
    """
    # 提取标题（第一个 # 开头的行）
    title_match = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()
        content = text
    else:
        # 如果没有找到标题，使用主题作为标题
        title = topic
        content = f"# {topic}\n\n{text}"

    # 生成素材来源摘要
    if search_results:
        source_summary = f"基于 {len(search_results)} 条检索结果生成"
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


def discover_prompt_files(prompt_dir: str) -> list[str]:
    """
    发现并返回提示词目录中的所有有效提示词文件

    Args:
        prompt_dir: 提示词目录路径

    Returns:
        有效提示词文件的绝对路径列表（已排序）

    Raises:
        FileNotFoundError: 目录不存在
        ValueError: 目录为空或没有有效的提示词文件
    """
    # 检查目录是否存在
    if not os.path.exists(prompt_dir):
        raise FileNotFoundError(f"提示词目录不存在: {prompt_dir}")

    if not os.path.isdir(prompt_dir):
        raise NotADirectoryError(f"路径不是目录: {prompt_dir}")

    # 扫描目录中的文件
    valid_files = []
    valid_extensions = {'.txt', '.md'}

    for filename in os.listdir(prompt_dir):
        # 过滤隐藏文件
        if filename.startswith('.'):
            continue

        # 过滤特殊文件
        if filename in {'.DS_Store'} or filename.endswith('~') or filename.endswith('.bak'):
            continue

        # 构建完整路径
        full_path = os.path.join(prompt_dir, filename)

        # 只包含常规文件，跳过目录
        if not os.path.isfile(full_path):
            continue

        # 检查文件扩展名
        _, ext = os.path.splitext(filename)
        if ext.lower() in valid_extensions:
            valid_files.append(full_path)

    # 检查是否找到有效文件
    if not valid_files:
        raise ValueError(f"在 {prompt_dir} 目录中未找到有效的提示词文件（支持 .txt 和 .md 格式）")

    # 返回排序后的文件列表
    return sorted(valid_files)


def load_prompt_from_file(prompt_path: str) -> str:
    """
    从文件中加载提示词内容

    Args:
        prompt_path: 提示词文件路径

    Returns:
        提示词内容字符串

    Raises:
        IOError: 文件读取失败
        ValueError: 文件内容为空
    """
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()

        if not content:
            raise ValueError(f"提示词文件为空: {prompt_path}")

        return content

    except UnicodeDecodeError as e:
        raise IOError(f"无法读取文件（编码错误）: {prompt_path} - {str(e)}")
    except Exception as e:
        raise IOError(f"读取文件失败: {prompt_path} - {str(e)}")


def main():
    """主函数 - 迭代处理多个提示词文件"""
    # 加载环境变量
    load_dotenv()

    # 检查 API Key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ 错误：未设置 ANTHROPIC_API_KEY")
        exit(1)

    # 获取配置
    base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.chatanywhere.tech/v1")
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")

    print("\n" + "="*60)
    print("🚀 带详细日志的文章生成器（OpenAI 兼容接口）")
    print("="*60)

    # 定义常量
    PROMPT_DIR = "write_prompt"
    topic = "产品经理如何做技术选型调研"

    print(f"\n📝 选题: {topic}")
    print(f"🤖 模型: {model}")
    print(f"🔗 API: {base_url}")
    print(f"📚 使用 NotebookLM 检索")

    # 发现提示词文件
    try:
        prompt_files = discover_prompt_files(PROMPT_DIR)
        print(f"\n✅ 发现 {len(prompt_files)} 个提示词文件")
    except (FileNotFoundError, ValueError) as e:
        print(f"\n❌ 错误: {str(e)}")
        exit(1)

    # 迭代处理每个提示词
    success_count = 0
    total = len(prompt_files)

    for i, prompt_file in enumerate(prompt_files, 1):
        print("\n" + "="*60)
        print(f"🔄 处理提示词 {i}/{total}")
        print("="*60)

        # 提取提示词文件名（不含扩展名）
        prompt_filename = os.path.basename(prompt_file)
        prompt_name = os.path.splitext(prompt_filename)[0]

        try:
            # 加载提示词内容
            system_prompt = load_prompt_from_file(prompt_file)
            print(f"📝 使用提示词: {prompt_filename}")

            # 生成唯一时间戳
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # 生成文章
            article, log_file = generate_with_detailed_logs(
                topic=topic,
                api_key=api_key,
                base_url=base_url,
                model=model,
                system_prompt=system_prompt,
                prompt_name=prompt_name
            )

            # 保存文章到单独文件
            topic_sanitized = topic.replace(' ', '_').replace('/', '_')
            article_file = f"generated/{topic_sanitized}_{prompt_name}_{timestamp}.md"
            os.makedirs("generated", exist_ok=True)

            with open(article_file, "w", encoding="utf-8") as f:
                f.write(article.content)

            print(f"\n✅ 文章已保存到: {article_file}")
            print(f"📋 详细日志: {log_file}")

            success_count += 1

        except Exception as e:
            print(f"\n❌ 处理提示词 '{prompt_filename}' 时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            print(f"\n⚠️  跳过此提示词，继续处理下一个...")
            continue

    # 最终总结
    print("\n" + "="*60)
    print(f"🎉 所有提示词处理完成！共生成 {success_count}/{total} 篇文章")
    print("="*60)


if __name__ == "__main__":
    main()

