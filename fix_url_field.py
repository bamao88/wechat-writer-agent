#!/usr/bin/env python3
"""将URL字段改为文本字段"""

import os
import sys
from dotenv import load_dotenv
import requests

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

from src.modules.feishu_doc import FeishuTokenManager


def update_field(app_token: str, table_id: str, field_id: str, access_token: str):
    """更新字段类型"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields/{field_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # 将URL字段改为文本字段
    payload = {
        "field_name": "文章链接",
        "type": 1,  # 1 = 文本
        "property": None
    }

    try:
        response = requests.put(url, json=payload, headers=headers, timeout=30)

        if response.status_code != 200:
            print(f"❌ 更新失败 (HTTP {response.status_code})")
            print(f"   响应: {response.text}")
            return False

        data = response.json()

        if data.get("code") != 0:
            print(f"❌ 更新失败: {data.get('msg', '未知错误')}")
            return False

        print(f"✅ 字段更新成功")
        return True

    except Exception as e:
        print(f"❌ 更新失败: {str(e)}")
        return False


def main():
    print("=" * 70)
    print("将URL字段改为文本字段")
    print("=" * 70)

    # 环境变量
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    app_token = os.getenv("FEISHU_BITABLE_APP_TOKEN")
    table_id = "tblI0sffMPHRkXhW"
    field_id = "fldOMpt4vG"  # 文章链接字段的ID

    # 获取 token
    print(f"\n🔑 获取访问令牌...")
    try:
        token_manager = FeishuTokenManager(app_id, app_secret)
        access_token = token_manager.get_token()
        print(f"✅ 令牌获取成功")
    except Exception as e:
        print(f"❌ 令牌获取失败: {str(e)}")
        return 1

    print(f"\n🔧 更新字段类型...")
    if update_field(app_token, table_id, field_id, access_token):
        print(f"\n✅ 字段已更新为文本类型，现在可以测试了:")
        print(f"   python test_feishu_table_real.py")
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit(main())
