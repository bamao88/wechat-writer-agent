"""模块D：飞书多维表格"""

import os
import time
from typing import Dict, List
import requests

# 复用模块 C 的 Token Manager
from .feishu_doc import FeishuTokenManager


# 必填字段定义
REQUIRED_FIELDS = ["选题名称", "文章链接", "创建时间", "状态"]

# 状态枚举值
VALID_STATUSES = ["草稿", "待审核", "已发布"]


def _validate_required_fields(fields: dict) -> None:
    """
    验证必填字段

    Args:
        fields: 字段字典

    Raises:
        ValueError: 必填字段缺失
    """
    for field in REQUIRED_FIELDS:
        if field not in fields or not fields[field]:
            raise ValueError(f"必填字段缺失: {field}")


def _validate_field_types(fields: dict) -> None:
    """
    验证字段类型

    Args:
        fields: 字段字典

    Raises:
        ValueError: 字段类型错误
    """
    # 创建时间必须是整数
    if not isinstance(fields.get("创建时间"), int):
        raise ValueError("创建时间必须是整数（毫秒级时间戳）")


def _validate_field_values(fields: dict) -> None:
    """
    验证字段值（枚举值）

    Args:
        fields: 字段字典

    Raises:
        ValueError: 枚举值无效
    """
    status = fields.get("状态")
    if status not in VALID_STATUSES:
        raise ValueError(f"无效的状态值: {status}，有效值为: {', '.join(VALID_STATUSES)}")


def _validate_optional_fields(fields: dict) -> None:
    """
    验证可选字段（新增的4个日志字段）

    Args:
        fields: 字段字典

    Raises:
        ValueError: 字段类型错误
    """
    # 运行时长（秒）- 数字类型（int或float）
    if "运行时长（秒）" in fields:
        value = fields["运行时长（秒）"]
        if value is not None and not isinstance(value, (int, float)):
            raise ValueError("运行时长（秒）必须是数字类型")

    # Token使用量 - 整数类型
    if "Token使用量" in fields:
        value = fields["Token使用量"]
        if value is not None and not isinstance(value, int):
            raise ValueError("Token使用量必须是整数类型")

    # 工具调用次数 - 整数类型
    if "工具调用次数" in fields:
        value = fields["工具调用次数"]
        if value is not None and not isinstance(value, int):
            raise ValueError("工具调用次数必须是整数类型")

    # 日志文档URL - 字符串类型
    if "日志文档URL" in fields:
        value = fields["日志文档URL"]
        if value is not None and not isinstance(value, str):
            raise ValueError("日志文档URL必须是字符串类型")


def _insert_record_api(
    access_token: str,
    app_token: str,
    table_id: str,
    fields: dict
) -> str:
    """
    调用飞书 API 插入记录

    Args:
        access_token: 访问令牌
        app_token: 多维表格 app_token
        table_id: 表格 table_id
        fields: 字段数据

    Returns:
        记录 ID

    Raises:
        RuntimeError: API 调用失败
    """
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "fields": fields
    }

    max_retries = 1
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=30
            )

            if response.status_code == 429:
                # API限流
                if attempt < 3:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
                raise RuntimeError("飞书API限流，请稍后重试")

            if response.status_code != 200:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("msg", "未知错误")
                    raise RuntimeError(f"插入记录失败，HTTP状态码: {response.status_code}, 错误信息: {error_msg}")
                except:
                    raise RuntimeError(f"插入记录失败，HTTP状态码: {response.status_code}")

            data = response.json()

            if data.get("code") != 0:
                error_msg = data.get("msg", "未知错误")
                raise RuntimeError(f"插入记录失败: {error_msg}")

            # 提取 record_id
            record_id = data.get("data", {}).get("record", {}).get("record_id")

            if not record_id:
                raise RuntimeError("响应中未包含 record_id")

            return record_id

        except requests.exceptions.Timeout:
            if attempt < max_retries:
                time.sleep(2)
                continue
            raise RuntimeError("请求超时")
        except requests.exceptions.RequestException as e:
            if attempt < max_retries:
                time.sleep(2)
                continue
            raise RuntimeError(f"网络请求失败: {str(e)}")


def insert_record(fields: dict) -> str:
    """
    插入多维表格记录

    Args:
        fields: 字段字典，必填字段包括：
            - 选题名称: str
            - 文章链接: str
            - 创建时间: int (毫秒时间戳)
            - 状态: str ("草稿" / "待审核" / "已发布")

    Returns:
        记录 ID

    Raises:
        ValueError: 必填字段缺失或无效
        RuntimeError: 认证失败、网络错误或API调用失败
    """
    # 1. 验证字段
    _validate_required_fields(fields)
    _validate_field_types(fields)
    _validate_field_values(fields)

    # 新增：验证可选字段（日志相关字段）
    _validate_optional_fields(fields)

    # 2. 读取环境变量
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    app_token = os.getenv("FEISHU_BITABLE_APP_TOKEN")
    table_id = os.getenv("FEISHU_BITABLE_TABLE_ID")

    if not app_id or not app_secret:
        raise ValueError("请在环境变量中配置 FEISHU_APP_ID 和 FEISHU_APP_SECRET")

    if not app_token:
        raise ValueError("请在环境变量中配置 FEISHU_BITABLE_APP_TOKEN")

    if not table_id:
        raise ValueError("请在环境变量中配置 FEISHU_BITABLE_TABLE_ID")

    # 3. 获取 token
    token_manager = FeishuTokenManager(app_id, app_secret)
    access_token = token_manager.get_token()

    # 4. 调用 API 插入记录
    record_id = _insert_record_api(access_token, app_token, table_id, fields)

    return record_id
