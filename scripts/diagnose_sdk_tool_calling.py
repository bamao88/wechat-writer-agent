#!/usr/bin/env python
"""Agent SDK 工具调用诊断脚本

系统性诊断 "Command failed with exit code 1" 错误的根本原因。

四阶段诊断流程:
1. 技能发现检查 - 验证技能目录和文件结构
2. 环境变量检查 - 验证必需配置是否设置
3. 独立技能调用测试 - 绕过SDK直接测试技能
4. Agent SDK 配置验证 - 验证SDK配置正确性

Usage:
    python scripts/diagnose_sdk_tool_calling.py [--verbose]
"""
import os
import sys
import argparse
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.subprocess_runner import SubprocessRunner


def print_section(title: str):
    """打印分节标题"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print('='*60)


def print_result(label: str, status: str, details: str = ""):
    """打印检查结果"""
    status_symbol = "✓" if status == "PASS" else "✗"
    print(f"{status_symbol} {label}: {status}")
    if details:
        print(f"  {details}")


def phase_1_skill_discovery(verbose: bool = False) -> dict:
    """阶段 1: 技能发现检查"""
    print_section("阶段 1: 技能发现检查")

    results = {
        "phase": "skill_discovery",
        "checks": [],
        "passed": 0,
        "failed": 0
    }

    # 检查技能目录
    user_skills_dir = Path.home() / ".claude" / "skills" / "notebooklm"
    if user_skills_dir.exists():
        results["checks"].append({
            "name": "技能目录存在",
            "status": "PASS",
            "path": str(user_skills_dir)
        })
        results["passed"] += 1
        print_result("技能目录", "PASS", str(user_skills_dir))
    else:
        results["checks"].append({
            "name": "技能目录存在",
            "status": "FAIL",
            "path": str(user_skills_dir)
        })
        results["failed"] += 1
        print_result("技能目录", "FAIL", f"目录不存在: {user_skills_dir}")
        return results

    # 检查 SKILL.md
    skill_md = user_skills_dir / "SKILL.md"
    if skill_md.exists():
        size = skill_md.stat().st_size
        results["checks"].append({
            "name": "SKILL.md 文件",
            "status": "PASS",
            "size": size
        })
        results["passed"] += 1
        print_result("SKILL.md 文件", "PASS", f"大小: {size} bytes")

        if verbose and size > 0:
            with open(skill_md, 'r', encoding='utf-8') as f:
                content = f.read(500)
                print(f"  前500字符: {content[:500]}")
    else:
        results["checks"].append({
            "name": "SKILL.md 文件",
            "status": "FAIL"
        })
        results["failed"] += 1
        print_result("SKILL.md 文件", "FAIL", "文件不存在")

    # 检查 run.py 脚本
    run_script = user_skills_dir / "scripts" / "run.py"
    if run_script.exists():
        results["checks"].append({
            "name": "run.py 脚本",
            "status": "PASS",
            "path": str(run_script)
        })
        results["passed"] += 1
        print_result("run.py 脚本", "PASS", str(run_script))

        # 检查可执行权限
        if os.access(run_script, os.X_OK):
            print_result("  可执行权限", "PASS", "脚本具有执行权限")
        else:
            print_result("  可执行权限", "INFO", "脚本无执行权限（但Python可执行）")
    else:
        results["checks"].append({
            "name": "run.py 脚本",
            "status": "FAIL"
        })
        results["failed"] += 1
        print_result("run.py 脚本", "FAIL", "脚本不存在")

    return results


def phase_2_environment_check(verbose: bool = False) -> dict:
    """阶段 2: 环境变量检查"""
    print_section("阶段 2: 环境变量检查")

    results = {
        "phase": "environment_check",
        "checks": [],
        "passed": 0,
        "failed": 0
    }

    # 检查 NOTEBOOK_ID
    notebook_id = os.getenv("NOTEBOOK_ID")
    if notebook_id:
        results["checks"].append({
            "name": "NOTEBOOK_ID",
            "status": "PASS",
            "value": notebook_id[:20] + "..."
        })
        results["passed"] += 1
        print_result("NOTEBOOK_ID", "PASS", f"已设置 ({notebook_id[:20]}...)")
    else:
        results["checks"].append({
            "name": "NOTEBOOK_ID",
            "status": "FAIL"
        })
        results["failed"] += 1
        print_result("NOTEBOOK_ID", "FAIL", "未设置（工具调用将失败）")

    # 检查 NOTEBOOK_URL (可选)
    notebook_url = os.getenv("NOTEBOOK_URL")
    if notebook_url:
        results["checks"].append({
            "name": "NOTEBOOK_URL",
            "status": "PASS",
            "value": notebook_url
        })
        results["passed"] += 1
        print_result("NOTEBOOK_URL", "PASS", f"已设置 ({notebook_url})")
    else:
        results["checks"].append({
            "name": "NOTEBOOK_URL",
            "status": "INFO"
        })
        print_result("NOTEBOOK_URL", "INFO", "未设置（可选）")

    # 检查 ANTHROPIC_API_KEY
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        results["checks"].append({
            "name": "ANTHROPIC_API_KEY",
            "status": "PASS",
            "value": api_key[:20] + "..."
        })
        results["passed"] += 1
        print_result("ANTHROPIC_API_KEY", "PASS", f"已设置 ({api_key[:20]}...)")
    else:
        results["checks"].append({
            "name": "ANTHROPIC_API_KEY",
            "status": "FAIL"
        })
        results["failed"] += 1
        print_result("ANTHROPIC_API_KEY", "FAIL", "未设置（API调用将失败）")

    # 检查 ANTHROPIC_BASE_URL (官方API不需要)
    base_url = os.getenv("ANTHROPIC_BASE_URL")
    if base_url:
        results["checks"].append({
            "name": "ANTHROPIC_BASE_URL",
            "status": "INFO",
            "value": base_url
        })
        print_result("ANTHROPIC_BASE_URL", "INFO", f"已设置 ({base_url})")
    else:
        results["checks"].append({
            "name": "ANTHROPIC_BASE_URL",
            "status": "INFO"
        })
        print_result("ANTHROPIC_BASE_URL", "INFO", "未设置（使用官方API）")

    return results


def phase_3_standalone_skill_test(verbose: bool = False) -> dict:
    """阶段 3: 独立技能调用测试"""
    print_section("阶段 3: 独立技能调用测试")

    results = {
        "phase": "standalone_skill_test",
        "checks": [],
        "passed": 0,
        "failed": 0
    }

    # 获取必需的环境变量
    notebook_id = os.getenv("NOTEBOOK_ID")
    if not notebook_id:
        results["checks"].append({
            "name": "技能调用测试",
            "status": "SKIP",
            "reason": "NOTEBOOK_ID 未设置"
        })
        print_result("技能调用测试", "SKIP", "需要 NOTEBOOK_ID 环境变量")
        return results

    # 构建测试命令
    user_skills_dir = Path.home() / ".claude" / "skills" / "notebooklm"
    run_script = user_skills_dir / "scripts" / "run.py"

    if not run_script.exists():
        results["checks"].append({
            "name": "技能调用测试",
            "status": "SKIP",
            "reason": "run.py 脚本不存在"
        })
        print_result("技能调用测试", "SKIP", "run.py 脚本不存在")
        return results

    # 使用 SubprocessRunner 执行测试
    cmd = [
        "python",
        str(run_script),
        "ask_question.py",
        "--question", "测试问题：什么是产品经理？",
        "--notebook-id", notebook_id
    ]

    print(f"\n执行命令: {' '.join(cmd)}")
    runner = SubprocessRunner()
    result = runner.run(cmd, timeout=60)  # 60秒超时

    if result["success"]:
        results["checks"].append({
            "name": "技能调用测试",
            "status": "PASS",
            "stdout_length": len(result["stdout"]) if result["stdout"] else 0
        })
        results["passed"] += 1
        print_result("技能调用测试", "PASS", f"输出长度: {len(result['stdout'])} 字符")

        if verbose and result["stdout"]:
            print(f"\nstdout 前500字符:")
            print(result["stdout"][:500])
    else:
        results["checks"].append({
            "name": "技能调用测试",
            "status": "FAIL",
            "error": result["error_message"],
            "returncode": result["returncode"],
            "stderr": result["stderr"][:500] if result["stderr"] else None
        })
        results["failed"] += 1
        print_result("技能调用测试", "FAIL", result["error_message"])

        if result["stderr"]:
            print(f"\nstderr 输出:")
            print(result["stderr"][:1000])

        if result["timeout_occurred"]:
            print("  ⚠ 注意: 测试超时，可能是网络问题或NotebookLM响应慢")

    return results


def phase_4_sdk_config_validation(verbose: bool = False) -> dict:
    """阶段 4: Agent SDK 配置验证"""
    print_section("阶段 4: Agent SDK 配置验证")

    results = {
        "phase": "sdk_config_validation",
        "checks": [],
        "passed": 0,
        "failed": 0
    }

    # 尝试导入 SDK
    try:
        from claude_agent_sdk import ClaudeAgentOptions
        results["checks"].append({
            "name": "SDK 导入",
            "status": "PASS"
        })
        results["passed"] += 1
        print_result("SDK 导入", "PASS", "claude_agent_sdk 可正常导入")
    except ImportError as e:
        results["checks"].append({
            "name": "SDK 导入",
            "status": "FAIL",
            "error": str(e)
        })
        results["failed"] += 1
        print_result("SDK 导入", "FAIL", f"无法导入 claude_agent_sdk: {e}")
        return results

    # 验证 SDK 配置
    try:
        options = ClaudeAgentOptions(
            setting_sources=["user"],  # 从 ~/.claude/skills/ 加载
            allowed_tools=["Skill"]     # 启用技能发现
        )
        results["checks"].append({
            "name": "SDK 配置创建",
            "status": "PASS"
        })
        results["passed"] += 1
        print_result("SDK 配置创建", "PASS", "ClaudeAgentOptions 配置有效")

        if verbose:
            print(f"  setting_sources: {options.setting_sources}")
            print(f"  allowed_tools: {options.allowed_tools}")
    except Exception as e:
        results["checks"].append({
            "name": "SDK 配置创建",
            "status": "FAIL",
            "error": str(e)
        })
        results["failed"] += 1
        print_result("SDK 配置创建", "FAIL", f"配置失败: {e}")

    return results


def print_summary(all_results: list):
    """打印诊断总结"""
    print_section("诊断总结")

    total_passed = sum(r["passed"] for r in all_results)
    total_failed = sum(r["failed"] for r in all_results)
    total_checks = total_passed + total_failed

    print(f"\n总计: {total_checks} 项检查")
    print(f"  ✓ 通过: {total_passed}")
    print(f"  ✗ 失败: {total_failed}")

    if total_failed == 0:
        print("\n🎉 所有检查通过！系统已就绪。")
        print("\n建议:")
        print("  - Agent SDK 工具调用配置正确")
        print("  - 可以进行端到端测试验证")
    else:
        print("\n⚠ 发现问题需要修复:")

        for result in all_results:
            failed_checks = [c for c in result["checks"] if c["status"] == "FAIL"]
            if failed_checks:
                print(f"\n{result['phase']}:")
                for check in failed_checks:
                    print(f"  - {check['name']}: {check.get('error', '检查失败')}")

        print("\n修复建议:")
        # 根据失败的阶段提供建议
        phase_failures = {r["phase"]: r["failed"] for r in all_results if r["failed"] > 0}

        if "skill_discovery" in phase_failures:
            print("  1. 确保 NotebookLM 技能已安装到 ~/.claude/skills/notebooklm/")
            print("     检查 SKILL.md 和 scripts/run.py 是否存在")

        if "environment_check" in phase_failures:
            print("  2. 在 .env 文件中设置必需的环境变量:")
            print("     NOTEBOOK_ID=your-notebook-id")
            print("     ANTHROPIC_API_KEY=your-api-key")

        if "standalone_skill_test" in phase_failures:
            print("  3. 独立技能调用失败，检查:")
            print("     - NotebookLM 技能代码是否正确")
            print("     - 网络连接是否正常")
            print("     - notebook_id 是否有效")

        if "sdk_config_validation" in phase_failures:
            print("  4. Agent SDK 配置问题:")
            print("     - 确保 claude-agent-sdk 已安装")
            print("     - 检查 SDK 版本兼容性")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Agent SDK 工具调用诊断脚本"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细输出"
    )
    args = parser.parse_args()

    print("Agent SDK 工具调用诊断")
    print("=" * 60)

    # 执行四个阶段的诊断
    results = []

    try:
        results.append(phase_1_skill_discovery(verbose=args.verbose))
        results.append(phase_2_environment_check(verbose=args.verbose))
        results.append(phase_3_standalone_skill_test(verbose=args.verbose))
        results.append(phase_4_sdk_config_validation(verbose=args.verbose))

        # 打印总结
        print_summary(results)

        # 退出码: 如果有任何失败，返回非零
        total_failed = sum(r["failed"] for r in results)
        sys.exit(0 if total_failed == 0 else 1)

    except KeyboardInterrupt:
        print("\n\n诊断被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n诊断过程中发生异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
