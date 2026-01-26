#!/usr/bin/env python3
"""测试飞书多维表格真实 API"""

import os
import sys
import time
from dotenv import load_dotenv
import requests

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

from src.modules.feishu_table import insert_record
from src.modules.feishu_doc import FeishuTokenManager


def get_table_list(app_token: str, access_token: str):
    """获取多维表格中的所有数据表"""
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code != 200:
            print(f"❌ 获取表格列表失败，HTTP状态码: {response.status_code}")
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
    print("飞书多维表格写入模块 - 真实API测试")
    print("=" * 70)

    # 检查环境变量
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    app_token = os.getenv("FEISHU_BITABLE_APP_TOKEN")
    table_id = os.getenv("FEISHU_BITABLE_TABLE_ID")

    print(f"\n🔧 环境配置:")
    print(f"   APP_ID: {'✅ ' + app_id if app_id else '❌ 未配置'}")
    print(f"   APP_SECRET: {'✅ ' + ('*' * 20) if app_secret else '❌ 未配置'}")
    print(f"   APP_TOKEN: {'✅ ' + app_token if app_token else '❌ 未配置'}")
    print(f"   TABLE_ID: {'✅ ' + table_id if table_id and table_id != 'your-table-id-here' else '❌ 未配置'}")

    if not app_id or not app_secret or not app_token:
        print("\n❌ 缺少必要的环境变量配置")
        return 1

    # 获取 access token
    print(f"\n🔑 获取访问令牌...")
    try:
        token_manager = FeishuTokenManager(app_id, app_secret)
        access_token = token_manager.get_token()
        print(f"✅ 令牌获取成功")
    except Exception as e:
        print(f"❌ 令牌获取失败: {str(e)}")
        return 1

    # 如果 TABLE_ID 未配置，先获取表格列表
    if not table_id or table_id == "your-table-id-here":
        print(f"\n📋 TABLE_ID 未配置，正在获取多维表格中的数据表列表...")
        tables = get_table_list(app_token, access_token)

        if not tables:
            print("❌ 无法获取表格列表")
            return 1

        if len(tables) == 0:
            print("❌ 多维表格中没有数据表，请先在飞书中创建数据表")
            return 1

        print(f"\n找到 {len(tables)} 个数据表:")
        for i, table in enumerate(tables, 1):
            print(f"   {i}. {table.get('name', '未命名')} (ID: {table.get('table_id', 'N/A')})")

        # 使用第一个表格
        table_id = tables[0].get("table_id")
        table_name = tables[0].get("name", "未命名")

        print(f"\n💡 使用第一个数据表: {table_name}")
        print(f"   TABLE_ID: {table_id}")
        print(f"\n   请将以下内容添加到 .env 文件:")
        print(f"   FEISHU_BITABLE_TABLE_ID={table_id}")

        # 临时设置环境变量用于测试
        os.environ["FEISHU_BITABLE_TABLE_ID"] = table_id

    # 准备测试数据
    fields = {
        "选题名称": f"测试选题 - API验证 ({time.strftime('%Y-%m-%d %H:%M:%S')})",
        "文章链接": "https://izux3goqsa.feishu.cn/docx/test_api_verification",
        "创建时间": int(time.time() * 1000),
        "状态": "草稿"
    }

    print(f"\n📝 测试数据:")
    for key, value in fields.items():
        print(f"   {key}: {value}")

    # 执行插入测试
    print(f"\n🚀 开始插入记录...")
    try:
        record_id = insert_record(fields)

        print(f"\n✅ 记录插入成功！")
        print(f"   记录ID: {record_id}")
        print(f"\n🔗 请在飞书多维表格中查看新记录:")
        print(f"   https://izux3goqsa.feishu.cn/base/{app_token}")

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
