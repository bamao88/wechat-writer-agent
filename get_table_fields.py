#!/usr/bin/env python3
"""获取飞书多维表格的字段信息"""

import os
import sys
from dotenv import load_dotenv
import requests
import json

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

from src.modules.feishu_doc import FeishuTokenManager


def get_table_fields(app_token: str, table_id: str, access_token: str):
    """获取数据表的字段列表"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code != 200:
            print(f"❌ 获取字段列表失败，HTTP状态码: {response.status_code}")
            print(f"   响应: {response.text}")
            return None

        data = response.json()

        if data.get("code") != 0:
            print(f"❌ API调用失败: {data.get('msg', '未知错误')}")
            return None

        return data.get("data", {}).get("items", [])

    except Exception as e:
        print(f"❌ 请求失败: {str(e)}")
        return None


def main():
    print("=" * 70)
    print("查看飞书多维表格字段信息")
    print("=" * 70)

    # 环境变量
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    app_token = os.getenv("FEISHU_BITABLE_APP_TOKEN")
    table_id = "tblI0sffMPHRkXhW"  # 刚才获取到的

    # 获取 token
    print(f"\n🔑 获取访问令牌...")
    try:
        token_manager = FeishuTokenManager(app_id, app_secret)
        access_token = token_manager.get_token()
        print(f"✅ 令牌获取成功")
    except Exception as e:
        print(f"❌ 令牌获取失败: {str(e)}")
        return 1

    # 获取字段列表
    print(f"\n📋 获取表格字段...")
    print(f"   APP_TOKEN: {app_token}")
    print(f"   TABLE_ID: {table_id}")

    fields = get_table_fields(app_token, table_id, access_token)

    if not fields:
        print("❌ 无法获取字段列表")
        return 1

    print(f"\n找到 {len(fields)} 个字段:\n")
    print(f"{'序号':<6} {'字段名':<25} {'字段类型':<15} {'字段ID'}")
    print("-" * 70)

    for i, field in enumerate(fields, 1):
        field_name = field.get("field_name", "未命名")
        field_type = field.get("type", "未知")
        field_id = field.get("field_id", "N/A")

        print(f"{i:<6} {field_name:<25} {field_type:<15} {field_id}")

    # 显示完整的JSON结构（用于调试）
    print(f"\n\n📄 完整字段信息（JSON格式）:")
    print("=" * 70)
    print(json.dumps(fields, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    exit(main())
