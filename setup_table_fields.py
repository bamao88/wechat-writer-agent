#!/usr/bin/env python3
"""设置飞书多维表格的字段"""

import os
import sys
from dotenv import load_dotenv
import requests
import json

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

from src.modules.feishu_doc import FeishuTokenManager


def create_field(app_token: str, table_id: str, access_token: str, field_config: dict):
    """创建字段"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=field_config, headers=headers, timeout=30)

        if response.status_code != 200:
            print(f"   ❌ 失败 (HTTP {response.status_code})")
            print(f"      响应: {response.text}")
            return False

        data = response.json()

        if data.get("code") != 0:
            print(f"   ❌ 失败: {data.get('msg', '未知错误')}")
            return False

        field_id = data.get("data", {}).get("field", {}).get("field_id")
        print(f"   ✅ 成功 (ID: {field_id})")
        return True

    except Exception as e:
        print(f"   ❌ 失败: {str(e)}")
        return False


def main():
    print("=" * 70)
    print("设置飞书多维表格字段")
    print("=" * 70)

    # 环境变量
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    app_token = os.getenv("FEISHU_BITABLE_APP_TOKEN")
    table_id = "tblI0sffMPHRkXhW"

    # 获取 token
    print(f"\n🔑 获取访问令牌...")
    try:
        token_manager = FeishuTokenManager(app_id, app_secret)
        access_token = token_manager.get_token()
        print(f"✅ 令牌获取成功")
    except Exception as e:
        print(f"❌ 令牌获取失败: {str(e)}")
        return 1

    # 定义要创建的字段
    fields_to_create = [
        {
            "name": "选题名称",
            "config": {
                "field_name": "选题名称",
                "type": 1,  # 1 = 文本
                "property": None
            }
        },
        {
            "name": "文章链接",
            "config": {
                "field_name": "文章链接",
                "type": 15,  # 15 = URL
                "property": None
            }
        },
        {
            "name": "创建时间",
            "config": {
                "field_name": "创建时间",
                "type": 5,  # 5 = 日期
                "property": {
                    "date_formatter": "yyyy/MM/dd HH:mm",
                    "auto_fill": False
                }
            }
        },
        {
            "name": "状态",
            "config": {
                "field_name": "状态",
                "type": 3,  # 3 = 单选
                "property": {
                    "options": [
                        {"name": "草稿"},
                        {"name": "待审核"},
                        {"name": "已发布"}
                    ]
                }
            }
        }
    ]

    print(f"\n📋 准备创建 {len(fields_to_create)} 个字段:")

    success_count = 0
    for field_def in fields_to_create:
        print(f"\n创建字段: {field_def['name']}")
        if create_field(app_token, table_id, access_token, field_def['config']):
            success_count += 1

    print(f"\n{'='*70}")
    print(f"完成! 成功创建 {success_count}/{len(fields_to_create)} 个字段")
    print(f"{'='*70}")

    if success_count == len(fields_to_create):
        print(f"\n✅ 所有字段创建成功！现在可以运行真实API测试了:")
        print(f"   python test_feishu_table_real.py")
        return 0
    else:
        print(f"\n⚠️  部分字段创建失败，请检查错误信息")
        return 1


if __name__ == "__main__":
    exit(main())
