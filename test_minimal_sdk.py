"""最小化 Agent SDK + NotebookLM 调用测试"""
import os
import asyncio

# 清理环境
if 'ANTHROPIC_AUTH_TOKEN' in os.environ:
    del os.environ['ANTHROPIC_AUTH_TOKEN']

from dotenv import load_dotenv
load_dotenv(override=True)

from claude_agent_sdk import query, ClaudeAgentOptions

async def test_agent_sdk_notebooklm():
    """测试 Agent SDK 能否调用 NotebookLM skill"""

    print("="*60)
    print("Testing Agent SDK + NotebookLM Integration")
    print("="*60)

    # 配置
    api_key = os.getenv("ANTHROPIC_API_KEY")
    base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")

    print(f"API: {base_url}")
    print(f"API Key: ***{api_key[-8:] if api_key else 'Not set'}")
    print()

    # 简单的提示词，强制调用工具
    prompt = """我需要你帮我查询关于"产品经理需要懂技术架构"的知识。

请使用 NotebookLM工具查询相关内容，然后给我一个简短的总结（200字以内）。"""

    # 配置 Agent SDK
    env_vars = {
        "API_TIMEOUT_MS": "120000"  # 120秒超时
    }
    if base_url:
        env_vars["ANTHROPIC_BASE_URL"] = base_url

    options = ClaudeAgentOptions(
        model=os.getenv("MODEL_NAME", "claude-sonnet-4-5"),
        max_turns=5,
        setting_sources=["user"],  # Load Skills from ~/.claude/skills/
        allowed_tools=["Skill"],  # Enable all Skills
        env=env_vars
    )

    print("Calling Agent SDK...")
    print()

    try:
        result_text = ""
        tool_called = False

        async for message in query(prompt=prompt, options=options):
            print(f"Message type: {type(message).__name__}")

            # 检查是否调用了工具
            if hasattr(message, 'content'):
                content = message.content
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get('type') == 'tool_use':
                            tool_called = True
                            print(f"  ✅ Tool called: {block.get('name', 'unknown')}")

            # 获取最终结果
            if hasattr(message, 'result'):
                result_text = message.result

        print()
        print("="*60)
        print("Result:")
        print("="*60)
        print(result_text[:500] if result_text else "No result")
        print()

        print("="*60)
        print("Test Result:")
        print("="*60)
        if tool_called:
            print("✅ SUCCESS: NotebookLM skill was called")
        else:
            print("❌ FAIL: NotebookLM skill was NOT called")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_agent_sdk_notebooklm())
