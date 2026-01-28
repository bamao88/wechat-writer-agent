#!/usr/bin/env python
"""深度调试 Agent SDK 子进程调用机制

目标: 捕获SDK调用NotebookLM skill时的完整错误信息
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from claude_agent_sdk import query, ClaudeAgentOptions


async def debug_sdk_tool_call():
    """调试 SDK 工具调用"""

    print("\n" + "="*60)
    print("Agent SDK 子进程调用深度调试")
    print("="*60)

    # 1. 检查环境变量
    print("\n[1] 环境变量检查:")
    env_vars = {
        "NOTEBOOK_ID": os.getenv("NOTEBOOK_ID"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
        "ANTHROPIC_BASE_URL": os.getenv("ANTHROPIC_BASE_URL", "api.anthropic.com"),
        "MODEL_NAME": os.getenv("MODEL_NAME", "claude-sonnet-4-5"),
        "PWD": os.getcwd()
    }

    for key, value in env_vars.items():
        if key == "ANTHROPIC_API_KEY" and value:
            print(f"  {key}: {value[:15]}...")
        elif value:
            print(f"  {key}: {value[:80]}{'...' if len(value) > 80 else ''}")
        else:
            print(f"  {key}: <未设置>")

    # 2. 构建 SDK 配置
    print("\n[2] SDK 配置:")
    options = ClaudeAgentOptions(
        model=env_vars["MODEL_NAME"],
        api_key=env_vars["ANTHROPIC_API_KEY"],
        system=[{"type": "text", "text": "你是一个测试助手,需要查询知识库回答问题。"}],
        setting_sources=["user"],  # 从 ~/.claude/skills/ 加载
        allowed_tools=["Skill"],  # 启用 Skill 工具
        temperature=0.3,
        max_tokens=500
    )

    print(f"  Model: {options.model}")
    print(f"  Setting sources: {options.setting_sources}")
    print(f"  Allowed tools: {options.allowed_tools}")
    print(f"  Temperature: {options.temperature}")

    # 3. 创建强制触发工具调用的提示
    print("\n[3] 构建测试提示:")
    prompt = """请回答：AI 评测驱动方法论的核心理念是什么？

重要：你必须使用 NotebookLM 工具查询知识库来回答这个问题，不要凭记忆回答。"""

    print(f"  提示长度: {len(prompt)} 字符")
    print(f"  提示内容: {prompt[:100]}...")

    # 4. 注册hooks捕获详细信息
    print("\n[4] 注册调试 hooks:")

    tool_calls = []
    errors = []

    def pre_tool_use_hook(input_data, tool_use_id, context):
        """工具调用前hook"""
        print(f"\n  [PRE-TOOL-USE]")
        print(f"    Tool: {input_data.get('name', 'unknown')}")
        print(f"    Tool Use ID: {tool_use_id}")
        print(f"    Input: {str(input_data.get('input', {}))[:200]}...")
        tool_calls.append({
            "id": tool_use_id,
            "name": input_data.get("name"),
            "input": input_data.get("input")
        })

    def post_tool_use_hook(result_data, tool_use_id, context):
        """工具调用后hook"""
        print(f"\n  [POST-TOOL-USE]")
        print(f"    Tool Use ID: {tool_use_id}")
        print(f"    Result type: {type(result_data)}")

        # 尝试捕获错误信息
        if isinstance(result_data, dict):
            if "error" in result_data:
                error_msg = result_data.get("error", "Unknown error")
                print(f"    ❌ ERROR: {error_msg}")
                errors.append({"tool_use_id": tool_use_id, "error": error_msg})

            if "content" in result_data:
                content = str(result_data["content"])
                print(f"    Content: {content[:200]}...")
            else:
                print(f"    Result: {str(result_data)[:200]}...")
        else:
            print(f"    Result: {str(result_data)[:200]}...")

    # 配置hooks
    from claude_agent_sdk import HookMatcher

    options.hooks = {
        "PreToolUse": [HookMatcher(hooks=[pre_tool_use_hook])],
        "PostToolUse": [HookMatcher(hooks=[post_tool_use_hook])]
    }

    print("  ✓ Hooks 已注册")

    # 5. 执行查询
    print("\n[5] 执行 query():")
    print("  (这可能需要30-60秒...)\n")

    try:
        full_response = ""
        message_count = 0

        async for message in query(prompt=prompt, options=options):
            message_count += 1
            print(f"  [Message {message_count}] Type: {message.get('type', 'unknown')}")

            if message.get("type") == "text":
                content = message.get("content", "")
                full_response += content
                print(f"    Text: {content[:100]}...")

            elif message.get("type") == "tool_use":
                print(f"    Tool use: {message.get('name', 'unknown')}")

            elif message.get("type") == "error":
                error_msg = message.get("content", "Unknown error")
                print(f"    ❌ ERROR: {error_msg}")
                errors.append({"message": message_count, "error": error_msg})

        print(f"\n  ✓ 查询完成,共 {message_count} 条消息")
        print(f"  ✓ 生成内容长度: {len(full_response)} 字符")

        if full_response:
            print(f"\n  内容预览:\n{full_response[:300]}...")

    except Exception as e:
        print(f"\n  ❌ 查询失败: {e}")
        print(f"\n  错误类型: {type(e).__name__}")

        # 尝试获取更多错误信息
        import traceback
        print(f"\n  完整堆栈:")
        traceback.print_exc()

        errors.append({"exception": str(e), "type": type(e).__name__})

    # 6. 总结
    print("\n" + "="*60)
    print("调试总结")
    print("="*60)

    print(f"\n工具调用次数: {len(tool_calls)}")
    for i, call in enumerate(tool_calls, 1):
        print(f"  {i}. {call['name']} (ID: {call['id']})")

    print(f"\n错误数量: {len(errors)}")
    for i, error in enumerate(errors, 1):
        print(f"  {i}. {error}")

    if not errors:
        print("\n✅ 调试成功！SDK 工具调用正常工作")
        return True
    else:
        print("\n❌ 发现错误，需要进一步分析")

        # 7. 尝试直接调用技能进行对比
        print("\n" + "="*60)
        print("对比测试：直接调用 NotebookLM skill")
        print("="*60)

        from src.utils.subprocess_runner import run_skill_subprocess

        result = run_skill_subprocess(
            skill_name="notebooklm",
            script_name="ask_question.py",
            args=["--question", "AI 评测驱动方法论的核心理念是什么？", "--notebook-id", os.getenv("NOTEBOOK_ID")],
            timeout=30
        )

        print(f"\n直接调用结果:")
        print(f"  Success: {result['success']}")
        print(f"  Return code: {result['returncode']}")

        if result['success']:
            print(f"  Stdout length: {len(result['stdout'])} 字符")
            print(f"  Stdout preview: {result['stdout'][:300]}...")
        else:
            print(f"  Error: {result['error_message']}")
            if result['stderr']:
                print(f"  Stderr: {result['stderr'][:500]}...")

        return False


if __name__ == "__main__":
    success = asyncio.run(debug_sdk_tool_call())
    sys.exit(0 if success else 1)
