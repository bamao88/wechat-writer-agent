"""完整流程测试脚本 - 测试选题：产品经理要参与技术选型"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入主流程
from src.main import run_pipeline


def test_full_pipeline():
    """测试完整流程：检索 -> 生成 -> 飞书文档 -> 飞书表格"""

    print("\n" + "="*80)
    print("🚀 完整流程测试：产品经理要参与技术选型")
    print("="*80)

    # 1. 准备参数
    topic = "产品经理要参与技术选型"
    api_key = os.getenv("ANTHROPIC_API_KEY")
    folder_token = os.getenv("FEISHU_FOLDER_TOKEN")

    if not api_key:
        print("❌ 错误：未找到 ANTHROPIC_API_KEY")
        sys.exit(1)

    print(f"\n📝 选题: {topic}")
    print(f"🔑 API Key: {api_key[:20]}...")
    print(f"📁 飞书文件夹: {folder_token}")
    print(f"\n⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # 2. 运行完整流程
        print("\n" + "-"*80)
        print("步骤 1: 开始 NotebookLM 检索...")
        print("-"*80)

        result = run_pipeline(
            topic=topic,
            api_key=api_key,
            folder_token=folder_token,
            enable_feishu=True,  # 启用飞书功能
            max_retries=1
        )

        # 3. 输出结果
        print("\n" + "="*80)
        print("✅ 流程执行成功！")
        print("="*80)

        print(f"\n📊 检索结果:")
        print(f"   - 检索到 {len(result.search_results)} 条相关素材")
        for i, sr in enumerate(result.search_results[:3], 1):
            print(f"   {i}. {sr.content[:100]}...")

        print(f"\n📄 文章生成:")
        print(f"   - 标题: {result.article.title}")
        print(f"   - 字数: {len(result.article.content)} 字符")
        print(f"   - 素材摘要: {result.article.source_summary[:100]}...")

        if result.doc_result:
            print(f"\n📝 飞书文档:")
            print(f"   - 文档ID: {result.doc_result.doc_id}")
            print(f"   - 文档URL: {result.doc_result.doc_url}")

        if result.record_id:
            print(f"\n📊 飞书表格:")
            print(f"   - 记录ID: {result.record_id}")

        # 4. 保存文章到本地
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"output/article_{timestamp}.md"
        os.makedirs("output", exist_ok=True)

        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# {result.article.title}\n\n")
            f.write(result.article.content)
            f.write(f"\n\n---\n\n")
            f.write(f"**素材来源**: {result.article.source_summary}\n")
            if result.doc_result:
                f.write(f"**飞书文档**: {result.doc_result.doc_url}\n")
            if result.record_id:
                f.write(f"**表格记录**: {result.record_id}\n")

        print(f"\n💾 文章已保存到: {filename}")

        # 5. 输出完整文章内容
        print("\n" + "="*80)
        print("📄 生成的完整文章")
        print("="*80)
        print(result.article.content)

        print(f"\n⏰ 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    except Exception as e:
        print(f"\n❌ 执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    test_full_pipeline()
