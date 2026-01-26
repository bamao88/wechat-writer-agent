"""完整流程测试（使用 OpenAI SDK）：检索 -> 生成 -> 飞书文档 -> 飞书表格"""

import os
import sys
import re
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# 加载环境变量
load_dotenv()

# 导入模块
from src.modules import retrieval
from src.modules.feishu_doc import create_doc
from src.modules.feishu_table import insert_record
from src.models import Article


def generate_article_openai(topic: str, search_results: list, api_key: str, base_url: str, model: str):
    """使用 OpenAI SDK 生成文章"""

    # 创建 OpenAI 客户端
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=120.0,
        max_retries=2
    )

    # 构建系统提示词
    system_prompt = """你是一个专业的公众号文章写作助手。你的任务是帮助用户撰写高质量的公众号文章。

核心要求：
1. **使用提供的素材**：
   - 用户已经为你检索了相关素材，优先使用这些素材

2. **保持个人风格**：
   - 不要写成通识科普，要有明确的个人观点
   - 结合具体经验和案例
   - 保持真实性和独特性

3. **文章结构**：
   - 吸引人的标题和开头
   - 清晰的逻辑结构
   - 具体的案例支撑观点
   - 启发性的结论

4. **输出格式**：
   - 使用 Markdown 格式
   - 标题使用 # 开头（一级标题）
   - 正文分段清晰，适当使用二级标题（##）"""

    # 构建用户消息
    user_message = f"请根据以下素材，撰写一篇关于「{topic}」的公众号文章。\n\n"

    if search_results:
        user_message += "## 相关素材\n\n"
        for i, result in enumerate(search_results, 1):
            user_message += f"### 素材 {i}\n"
            user_message += f"{result.content}\n"
            if result.source:
                user_message += f"*来源: {result.source}*\n"
            user_message += "\n"
    else:
        user_message += "（未检索到素材，请基于主题理解撰写）\n\n"

    user_message += f"\n请撰写文章（要求：1000-2500字，有标题，有观点，有案例）："

    # 调用 API
    print("   调用 API 生成文章...")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        temperature=0.7,
        max_tokens=4096
    )

    # 解析响应
    content = response.choices[0].message.content

    # 提取标题
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()
    else:
        title = topic
        content = f"# {topic}\n\n{content}"

    # 生成素材摘要
    if search_results:
        source_summary = f"基于 {len(search_results)} 条检索结果生成"
        sources_with_info = [r.source for r in search_results if r.source]
        if sources_with_info:
            source_summary += f"，来源包括: {', '.join(sources_with_info[:3])}"
    else:
        source_summary = "无检索结果，基于 AI 理解生成"

    return Article(
        title=title,
        content=content,
        source_summary=source_summary
    )


def test_full_pipeline():
    """测试完整流程：检索 -> 生成 -> 飞书文档 -> 飞书表格"""

    print("\n" + "="*80)
    print("🚀 完整流程测试：产品经理要参与技术选型")
    print("="*80)

    # 1. 准备参数
    topic = "产品经理要参与技术选型"
    api_key = os.getenv("ANTHROPIC_API_KEY")
    base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.chatanywhere.tech/v1")
    model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
    folder_token = os.getenv("FEISHU_FOLDER_TOKEN")

    if not api_key:
        print("❌ 错误：未找到 ANTHROPIC_API_KEY")
        sys.exit(1)

    print(f"\n📝 选题: {topic}")
    print(f"🔑 API Key: {api_key[:20]}...")
    print(f"🌐 Base URL: {base_url}")
    print(f"🤖 模型: {model}")
    print(f"📁 飞书文件夹: {folder_token}")
    print(f"\n⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # 步骤 1: NotebookLM 检索
        print("\n" + "-"*80)
        print("步骤 1/4: NotebookLM 检索")
        print("-"*80)

        search_results = retrieval.search(query=topic)
        print(f"   ✅ 检索成功，获得 {len(search_results)} 条结果")

        # 步骤 2: 生成文章
        print("\n" + "-"*80)
        print("步骤 2/4: 生成文章")
        print("-"*80)

        article = generate_article_openai(topic, search_results, api_key, base_url, model)
        print(f"   ✅ 文章生成成功")
        print(f"   - 标题: {article.title}")
        print(f"   - 字数: {len(article.content)} 字符")

        # 步骤 3: 创建飞书文档
        print("\n" + "-"*80)
        print("步骤 3/4: 创建飞书文档")
        print("-"*80)

        doc_result = create_doc(
            title=article.title,
            content=article.content,
            folder_token=folder_token
        )
        print(f"   ✅ 飞书文档创建成功")
        print(f"   - 文档ID: {doc_result.doc_id}")
        print(f"   - 文档URL: {doc_result.doc_url}")

        # 步骤 4: 插入飞书表格记录
        print("\n" + "-"*80)
        print("步骤 4/4: 插入飞书表格记录")
        print("-"*80)

        current_timestamp = int(datetime.now().timestamp() * 1000)

        record_id = insert_record({
            "选题名称": topic,
            "文章链接": doc_result.doc_url,
            "创建时间": current_timestamp,
            "状态": "草稿"
        })
        print(f"   ✅ 表格记录插入成功")
        print(f"   - 记录ID: {record_id}")

        # 5. 保存文章到本地
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"output/article_{timestamp}.md"
        os.makedirs("output", exist_ok=True)

        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# {article.title}\n\n")
            f.write(article.content)
            f.write(f"\n\n---\n\n")
            f.write(f"**素材来源**: {article.source_summary}\n")
            f.write(f"**飞书文档**: {doc_result.doc_url}\n")
            f.write(f"**表格记录**: {record_id}\n")

        print(f"\n💾 文章已保存到: {filename}")

        # 6. 输出完整文章内容
        print("\n" + "="*80)
        print("📄 生成的完整文章")
        print("="*80)
        print(article.content)

        print("\n" + "="*80)
        print("✅ 流程执行成功！")
        print("="*80)
        print(f"\n📊 检索结果: {len(search_results)} 条")
        print(f"📝 飞书文档: {doc_result.doc_url}")
        print(f"📊 表格记录: {record_id}")
        print(f"💾 本地文件: {filename}")
        print(f"\n⏰ 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    except Exception as e:
        print(f"\n❌ 执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    test_full_pipeline()
