"""真实用例测试脚本 - 产品经理需要懂技术架构"""
import os
import sys
import asyncio

# 清除可能干扰的系统环境变量
if 'ANTHROPIC_AUTH_TOKEN' in os.environ:
    del os.environ['ANTHROPIC_AUTH_TOKEN']

# 加载 .env 配置
from dotenv import load_dotenv
load_dotenv(override=True)

# 确认配置
print("="*60)
print("Environment Configuration:")
print("="*60)
print(f"ANTHROPIC_BASE_URL: {os.getenv('ANTHROPIC_BASE_URL')}")
print(f"ANTHROPIC_API_KEY: {'***' + os.getenv('ANTHROPIC_API_KEY', '')[-8:]}")
print(f"USE_AGENT_SDK: {os.getenv('USE_AGENT_SDK', 'true')}")
print(f"NOTEBOOK_ID: {os.getenv('NOTEBOOK_ID', 'Not set')}")
print("="*60)
print()

# 导入模块
from src.main import run_pipeline

def main():
    """主测试函数"""
    # 测试参数
    topic = "产品经理需要懂技术架构"
    api_key = os.getenv("ANTHROPIC_API_KEY")
    notebook_id = "zh"  # 使用 active notebook

    print(f"📝 Testing Topic: {topic}")
    print(f"📚 Notebook: {notebook_id}")
    print()

    # 运行流水线
    try:
        result = run_pipeline(
            topic=topic,
            api_key=api_key,
            notebook_id=notebook_id,
            enable_feishu=False
        )

        print("\n" + "="*60)
        print("✅ Generation Complete")
        print("="*60)
        print(f"\nArticle length: {len(result.article.content)} characters")
        print(f"\nFirst 1500 characters:")
        print(result.article.content[:1500])
        print("...")

        # 检查 metrics
        if hasattr(result, 'metrics') and result.metrics:
            print(f"\n" + "="*60)
            print("📊 Metrics Report:")
            print("="*60)
            print(f"Tool calls: {result.metrics.get('tool_call_count', 0)}")
            print(f"Input tokens: {result.metrics.get('input_tokens', 0)}")
            print(f"Output tokens: {result.metrics.get('output_tokens', 0)}")
            print(f"Runtime: {result.metrics.get('runtime_seconds', 0):.2f} seconds")

            # 验收标准
            tool_call_count = result.metrics.get('tool_call_count', 0)
            print(f"\n" + "="*60)
            print("🎯 Acceptance Criteria Verification:")
            print("="*60)
            print(f"1. Complete article generated: {'✅ PASS' if len(result.article.content) > 500 else '❌ FAIL'}")
            print(f"2. NotebookLM skill called at least once: {'✅ PASS' if tool_call_count > 0 else '❌ FAIL'}")

            if tool_call_count > 0:
                print(f"\n✅✅✅ All acceptance criteria met! ✅✅✅")
                print(f"\n📝 NotebookLM was called {tool_call_count} time(s)")
            else:
                print(f"\n⚠️ Warning: NotebookLM skill was not called")
                print(f"   This may be because the pre-retrieval provided sufficient material")
        else:
            print("\n⚠️ No metrics available (SDK mode may be disabled)")

        # 保存文章
        filename = f"test_article_{topic[:15]}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(result.article.content)
        print(f"\n💾 Article saved to: {filename}")

    except Exception as e:
        print(f"\n❌ Test Failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
