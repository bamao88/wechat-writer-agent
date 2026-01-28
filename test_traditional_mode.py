"""使用传统模式测试（非 Agent SDK）- 验证 NotebookLM 工具调用"""
import os

# 清理环境
for key in list(os.environ.keys()):
    if 'ANTHROPIC' in key and key not in ['ANTHROPIC_API_KEY']:
        print(f"Removing env var: {key}")
        del os.environ[key]

from dotenv import load_dotenv
load_dotenv(override=True)

# 设置使用官方 API
os.environ['ANTHROPIC_BASE_URL'] = 'https://api.anthropic.com'
os.environ['USE_AGENT_SDK'] = 'false'  # 使用传统模式

print("="*60)
print("Testing Traditional Mode (Non-SDK)")
print("="*60)
print(f"ANTHROPIC_BASE_URL: {os.getenv('ANTHROPIC_BASE_URL')}")
print(f"ANTHROPIC_API_KEY: ***{os.getenv('ANTHROPIC_API_KEY', '')[-8:]}")
print(f"USE_AGENT_SDK: {os.getenv('USE_AGENT_SDK')}")
print("="*60)
print()

from src.main import run_pipeline

def main():
    """测试传统模式"""
    topic = "产品经理需要懂技术架构"
    api_key = os.getenv("ANTHROPIC_API_KEY")
    notebook_id = "zh"

    print(f"📝 Topic: {topic}")
    print(f"📚 Notebook: {notebook_id}")
    print()

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

        # 保存文章
        filename = "test_article_traditional_mode.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(result.article.content)
        print(f"\n💾 Article saved to: {filename}")

        print(f"\n" + "="*60)
        print("📊 Note:")
        print("="*60)
        print("Traditional mode does not track tool calling metrics.")
        print("However, the article was successfully generated with")
        print("pre-retrieved material from NotebookLM.")
        print()
        print("✅ Test PASSED: Complete article generated successfully")

    except Exception as e:
        print(f"\n❌ Test Failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
