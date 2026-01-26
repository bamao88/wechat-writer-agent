"""
环境测试脚本
检查所有依赖和配置是否正确
"""
import os
import sys


def test_python_version():
    """测试 Python 版本"""
    print("1. 检查 Python 版本...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"   ❌ Python 版本过低: {version.major}.{version.minor}.{version.micro}")
        print("   需要 Python 3.8 或更高版本")
        return False


def test_dependencies():
    """测试依赖包"""
    print("\n2. 检查依赖包...")

    dependencies = {
        "anthropic": "Anthropic SDK",
        "dotenv": "python-dotenv"
    }

    all_ok = True
    for module, name in dependencies.items():
        try:
            if module == "dotenv":
                __import__("dotenv")
            else:
                __import__(module)
            print(f"   ✅ {name}")
        except ImportError:
            print(f"   ❌ {name} 未安装")
            all_ok = False

    if not all_ok:
        print("\n   请运行: pip install -r requirements.txt")

    return all_ok


def test_env_file():
    """测试环境变量文件"""
    print("\n3. 检查环境变量配置...")

    if os.path.exists(".env"):
        print("   ✅ .env 文件存在")

        # 尝试加载
        from dotenv import load_dotenv
        load_dotenv()

        all_ok = True

        # 检查 API Key
        if os.getenv("ANTHROPIC_API_KEY"):
            api_key = os.getenv("ANTHROPIC_API_KEY")
            masked_key = api_key[:10] + "..." + api_key[-4:] if len(api_key) > 14 else "***"
            print(f"   ✅ ANTHROPIC_API_KEY 已设置: {masked_key}")
        else:
            print("   ❌ ANTHROPIC_API_KEY 未设置")
            all_ok = False

        if not all_ok:
            print("\n   请在 .env 文件中添加必需的环境变量")

        return all_ok
    else:
        print("   ❌ .env 文件不存在")
        print("   请复制 .env.example 并填入配置")
        return False


def test_api_connection():
    """测试 API 连接"""
    print("\n4. 测试 Anthropic API 连接...")

    try:
        from dotenv import load_dotenv
        from anthropic import Anthropic

        load_dotenv()
        api_key = os.getenv("ANTHROPIC_API_KEY")

        if not api_key:
            print("   ⏭️  跳过（API Key 未设置）")
            return False

        client = Anthropic(api_key=api_key)

        # 发送一个简单的测试请求
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=10,
            messages=[{"role": "user", "content": "Hi"}]
        )

        print("   ✅ API 连接成功")
        print(f"   使用模型: claude-3-5-sonnet-20241022")
        return True

    except Exception as e:
        print(f"   ❌ API 连接失败: {str(e)}")
        return False


def test_notebooklm_skill():
    """测试 NotebookLM Skill 安装"""
    print("\n5. 测试 NotebookLM Skill...")

    skill_path = os.path.expanduser("~/.claude/skills/notebooklm")

    if not os.path.exists(skill_path):
        print("   ❌ NotebookLM Skill 未安装")
        print("   请运行: mkdir -p ~/.claude/skills && cd ~/.claude/skills && git clone https://github.com/PleasePrompto/notebooklm-skill notebooklm")
        return False

    print("   ✅ NotebookLM Skill 已安装")

    # 检查关键脚本
    ask_script = os.path.join(skill_path, "scripts", "ask_question.py")
    if os.path.exists(ask_script):
        print("   ✅ ask_question.py 脚本存在")
    else:
        print("   ❌ ask_question.py 脚本不存在")
        return False

    return True


def test_notebooklm_auth():
    """测试 NotebookLM 认证"""
    print("\n6. 测试 NotebookLM 认证...")

    auth_file = os.path.expanduser("~/.claude/skills/notebooklm/data/browser_state/state.json")

    if os.path.exists(auth_file):
        print("   ✅ 认证文件存在")
        return True
    else:
        print("   ❌ 未完成 Google 认证")
        print("   请运行: python ~/.claude/skills/notebooklm/scripts/run.py auth_manager.py setup")
        return False


def test_notebooklm_library():
    """测试 NotebookLM 笔记本库"""
    print("\n7. 测试 NotebookLM 笔记本库...")

    library_file = os.path.expanduser("~/.claude/skills/notebooklm/data/library.json")

    if not os.path.exists(library_file):
        print("   ⚠️  笔记本库为空")
        print("   建议添加笔记本: python ~/.claude/skills/notebooklm/scripts/run.py notebook_manager.py add --url YOUR_URL --name NAME")
        return False

    try:
        import json
        with open(library_file, 'r') as f:
            library = json.load(f)

        notebooks = library.get('notebooks', [])
        active_id = library.get('active_notebook_id')

        if not notebooks:
            print("   ⚠️  笔记本库为空")
            print("   建议添加笔记本: python ~/.claude/skills/notebooklm/scripts/run.py notebook_manager.py add --url YOUR_URL --name NAME")
            return False

        print(f"   ✅ 找到 {len(notebooks)} 个笔记本")

        if active_id:
            active_nb = next((nb for nb in notebooks if nb['id'] == active_id), None)
            if active_nb:
                print(f"   ✅ Active notebook: {active_nb['name']}")
            else:
                print("   ⚠️  Active notebook ID 无效")
        else:
            print("   ⚠️  未设置 active notebook")
            print("   建议设置: python ~/.claude/skills/notebooklm/scripts/run.py notebook_manager.py activate --id ID")

        return True

    except Exception as e:
        print(f"   ❌ 读取库文件失败: {e}")
        return False


def test_notebooklm_tool():
    """测试 NotebookLM 工具集成"""
    print("\n8. 测试 NotebookLM 工具集成...")

    try:
        from notebooklm_tool import create_notebooklm_tool

        tool = create_notebooklm_tool()
        print("   ✅ NotebookLM 工具初始化成功")

        # 注意：不实际运行查询测试，因为需要浏览器
        print("   💡 要测试实际查询，请运行:")
        print("      python ~/.claude/skills/notebooklm/scripts/run.py ask_question.py --question '测试问题'")

        return True

    except Exception as e:
        print(f"   ❌ NotebookLM 工具初始化失败: {str(e)}")
        return False


def main():
    """运行所有测试"""
    print("="*60)
    print("🔧 环境配置检查")
    print("="*60)

    results = []

    results.append(("Python 版本", test_python_version()))
    results.append(("依赖包", test_dependencies()))
    results.append(("环境变量", test_env_file()))
    results.append(("API 连接", test_api_connection()))
    results.append(("NotebookLM Skill 安装", test_notebooklm_skill()))
    results.append(("NotebookLM 认证", test_notebooklm_auth()))
    results.append(("NotebookLM 笔记本库", test_notebooklm_library()))
    results.append(("NotebookLM 工具集成", test_notebooklm_tool()))

    # 总结
    print("\n" + "="*60)
    print("📊 检查结果")
    print("="*60)

    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")

    all_passed = all(r for _, r in results)

    if all_passed:
        print("\n🎉 所有检查通过！可以运行 python main.py 开始使用")
    else:
        print("\n⚠️  部分检查未通过，请按照上述提示修复问题")

    print("="*60)


if __name__ == "__main__":
    main()
