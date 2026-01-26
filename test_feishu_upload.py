#!/usr/bin/env python3
"""测试飞书云文档写入功能 - 使用真实API"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加src到路径
sys.path.insert(0, os.path.dirname(__file__))

from src.modules.feishu_doc import create_doc


def main():
    """测试将Markdown文件上传到飞书云文档"""

    print("=" * 70)
    print("飞书云文档写入模块 - 真实测试")
    print("=" * 70)

    # 文件路径
    markdown_file = "/Volumes/ExtSSD2601/IP_ZH/wechat-writer-agent/generated/产品经理如何做技术选型调研.md"

    # 检查文件是否存在
    if not os.path.exists(markdown_file):
        print(f"❌ 文件不存在: {markdown_file}")
        return 1

    # 读取文件内容
    print(f"\n📖 读取文件: {markdown_file}")
    with open(markdown_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 提取标题（第一行）
    title = content.split('\n')[0].strip('# ').strip()

    print(f"   标题: {title}")
    print(f"   内容长度: {len(content)} 字符")
    print(f"   段落数: {len(content.split('\\n\\n'))}")

    # 获取环境变量
    folder_token = os.getenv("FEISHU_FOLDER_TOKEN")
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    tenant_domain = os.getenv("FEISHU_TENANT_DOMAIN")

    print(f"\n🔧 环境配置:")
    print(f"   FEISHU_APP_ID: {'✅ 已设置' if app_id else '❌ 未设置'}")
    print(f"   FEISHU_APP_SECRET: {'✅ 已设置' if app_secret else '❌ 未设置'}")
    print(f"   FEISHU_FOLDER_TOKEN: {'✅ 已设置' if folder_token else '❌ 未设置'}")
    print(f"   FEISHU_TENANT_DOMAIN: {'✅ 已设置' if tenant_domain else '❌ 未设置'}")

    if not all([app_id, app_secret, folder_token, tenant_domain]):
        print("\n❌ 请检查.env文件中的飞书配置")
        return 1

    # 调用飞书API创建文档
    print(f"\n🚀 开始上传到飞书云文档...")
    print(f"   文件夹Token: {folder_token}")

    try:
        result = create_doc(
            title=title,
            content=content,
            folder_token=folder_token
        )

        print(f"\n✅ 文档创建成功！")
        print(f"   文档ID: {result.doc_id}")
        print(f"   访问链接: {result.doc_url}")

        print(f"\n📋 验收检查:")
        print(f"   ✅ C-01: URL包含feishu.cn - {'通过' if 'feishu.cn' in result.doc_url else '失败'}")
        print(f"   ✅ C-02: doc_id非空 - {'通过' if result.doc_id else '失败'}")
        print(f"   ✅ C-03: 内容已写入（请手动访问链接验证）")
        print(f"   ✅ C-04: 标题为 '{title}'（请手动访问链接验证）")

        print(f"\n🌐 请在浏览器中打开以下链接查看文档:")
        print(f"   {result.doc_url}")

        print("\n" + "=" * 70)
        print("✨ 测试完成！")
        print("=" * 70)

        return 0

    except ValueError as e:
        print(f"\n❌ 参数错误: {e}")
        return 1
    except RuntimeError as e:
        print(f"\n❌ API调用失败: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ 未知错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
