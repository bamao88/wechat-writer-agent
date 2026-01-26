"""CLI 交互层 - 保留原有的交互式体验"""

import os
import sys
from dotenv import load_dotenv
from src.main import run_pipeline


def interactive_mode():
    """交互式创作模式"""
    print("\n" + "="*60)
    print("🤖 IP内容工厂 - 公众号文章写作 Agent")
    print("="*60)

    # 获取选题
    print("\n📝 请输入文章选题:")
    topic = input("> ").strip()

    if not topic:
        print("❌ 选题不能为空")
        return

    # 询问是否启用飞书（阶段一默认禁用）
    print("\n📊 是否启用飞书集成？（阶段一功能未实现，建议输入 n）")
    print("   [y/N]:")
    enable_feishu_input = input("> ").strip().lower()
    enable_feishu = enable_feishu_input in ['y', 'yes']

    folder_token = None
    if enable_feishu:
        print("\n📁 请输入飞书文件夹 Token（可选，直接回车跳过）:")
        folder_token = input("> ").strip() or None

    # 执行流水线
    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("❌ 未找到 ANTHROPIC_API_KEY 环境变量")
            print("请在 .env 文件中设置或导出环境变量")
            return

        result = run_pipeline(
            topic=topic,
            api_key=api_key,
            enable_feishu=enable_feishu,
            folder_token=folder_token
        )

        # 输出结果
        print("\n" + "="*60)
        print("📄 生成的文章")
        print("="*60)
        print(f"\n{result.article.content}")

        # 保存到文件
        filename = f"article_{topic[:20].replace(' ', '_')}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(result.article.content)

        print(f"\n💾 文章已保存到: {filename}")

        if result.doc_result:
            print(f"🔗 飞书文档: {result.doc_result.doc_url}")

        if result.record_id:
            print(f"📊 表格记录ID: {result.record_id}")

    except Exception as e:
        print(f"\n❌ 执行失败: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    # 加载环境变量
    load_dotenv()

    # 验证 API Key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ 错误: 未设置 ANTHROPIC_API_KEY")
        print("\n请按以下步骤设置：")
        print("1. 复制 .env.example 为 .env")
        print("2. 在 .env 中设置你的 API Key")
        print("   ANTHROPIC_API_KEY=your-api-key-here")
        sys.exit(1)

    # 启动交互模式
    interactive_mode()


if __name__ == "__main__":
    main()
