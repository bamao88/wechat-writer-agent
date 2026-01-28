"""
主入口文件
运行此文件启动交互式写作 Agent
"""
import os
from dotenv import load_dotenv
from writer_agent import create_writer_agent


def main():
    """主函数"""
    # 加载环境变量（override=True 确保 .env 覆盖已有环境变量）
    load_dotenv(override=True)

    # 检查 Anthropic API Key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ 错误：未找到 ANTHROPIC_API_KEY 环境变量")
        print("\n请设置环境变量或创建 .env 文件")
        print("\n必需的环境变量：")
        print("  ANTHROPIC_API_KEY=your-api-key-here")
        print("\n可选的环境变量：")
        print("  NOTEBOOK_NAME=my_knowledge")
        return

    # 创建 Agent
    try:
        print("\n💡 提示：")
        print("  - 如果不指定 notebook_id 或 notebook_url，将使用 NotebookLM 库中的 active notebook")
        print("  - 可以通过以下命令查看可用的 notebooks：")
        print("    python ~/.claude/skills/notebooklm/scripts/run.py notebook_manager.py list")
        print()

        # 不指定 notebook，使用 active notebook
        # 如果需要指定特定 notebook，可以传入 notebook_id 或 notebook_url：
        # agent = create_writer_agent(notebook_id="your_notebook_id")
        # agent = create_writer_agent(notebook_url="https://notebooklm.google.com/notebook/xxx")
        agent = create_writer_agent()

        # 启动交互式写作
        agent.interactive_write()

    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
