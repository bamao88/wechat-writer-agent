"""
编程式调用示例
展示如何在代码中使用新的模块化 API
"""
import os
from dotenv import load_dotenv
from src.main import run_pipeline


def example_basic():
    """基础示例：生成一篇文章（使用 active notebook）"""
    print("="*60)
    print("示例 1: 基础用法（使用 active notebook）")
    print("="*60)

    # 不指定 notebook，将使用 NotebookLM 库中的 active notebook
    api_key = os.getenv("ANTHROPIC_API_KEY")

    result = run_pipeline(
        topic="AI 产品经理的一天",
        api_key=api_key,
        enable_feishu=False  # 阶段一禁用飞书
    )

    print("\n生成的文章：")
    print(result.article.content)
    print(f"\n素材来源: {result.article.source_summary}")


def example_with_notebook_id():
    """示例：使用 notebook ID"""
    print("\n" + "="*60)
    print("示例 2: 使用指定的 notebook ID")
    print("="*60)

    # 使用 NotebookLM 库中的特定笔记本 ID
    # 可以通过 `python ~/.claude/skills/notebooklm/scripts/run.py notebook_manager.py list` 查看
    api_key = os.getenv("ANTHROPIC_API_KEY")

    result = run_pipeline(
        topic="为什么好的产品需要克制",
        api_key=api_key,
        notebook_id="my_notebook_id",
        enable_feishu=False
    )

    print("\n生成的文章：")
    print(result.article.content)


def example_with_notebook_url():
    """示例：使用 notebook URL"""
    print("\n" + "="*60)
    print("示例 3: 使用 NotebookLM 笔记本 URL")
    print("="*60)

    # 直接使用 NotebookLM 笔记本的 URL
    # 格式：https://notebooklm.google.com/notebook/xxx
    api_key = os.getenv("ANTHROPIC_API_KEY")

    result = run_pipeline(
        topic="从 0 到 1 做一个 AI 功能",
        api_key=api_key,
        notebook_url="https://notebooklm.google.com/notebook/YOUR_NOTEBOOK_ID",
        enable_feishu=False
    )

    print("\n生成的文章：")
    print(result.article.content)


def example_save_to_file():
    """示例：保存文章到文件"""
    print("\n" + "="*60)
    print("示例 4: 生成并保存文章")
    print("="*60)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    topic = "内容创作的三个阶段"

    result = run_pipeline(
        topic=topic,
        api_key=api_key,
        enable_feishu=False
    )

    # 保存到文件
    filename = f"generated_{topic.replace(' ', '_')}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(result.article.content)

    print(f"\n✅ 文章已保存到: {filename}")


def main():
    """运行所有示例"""
    # 加载环境变量
    load_dotenv()

    # 检查 Anthropic API Key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ 错误：未设置 ANTHROPIC_API_KEY")
        print("请创建 .env 文件并设置 ANTHROPIC_API_KEY")
        return

    print("\n💡 提示：使用前请确保：")
    print("  1. 已安装 NotebookLM skill (在 ~/.claude/skills/notebooklm)")
    print("  2. 已完成 Google 认证")
    print("  3. 已添加至少一个 notebook 到库中，或设置了 active notebook\n")

    # 运行示例（根据需要取消注释）
    try:
        example_basic()
        # example_with_notebook_id()
        # example_with_notebook_url()
        # example_save_to_file()

    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
