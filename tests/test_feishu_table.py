"""测试飞书多维表格模块"""

import os
import pytest
from unittest.mock import Mock, patch, call

from src.modules.feishu_table import insert_record
import src.modules.feishu_doc as feishu_doc


class TestInsertRecord:
    """insert_record 核心验收测试"""

    def setup_method(self):
        """每个测试前清除token缓存"""
        feishu_doc._token_cache["token"] = None
        feishu_doc._token_cache["expires_at"] = 0

    @patch.dict(os.environ, {
        "FEISHU_APP_ID": "test_app_id",
        "FEISHU_APP_SECRET": "test_app_secret",
        "FEISHU_BITABLE_APP_TOKEN": "test_app_token",
        "FEISHU_BITABLE_TABLE_ID": "test_table_id"
    })
    @patch('requests.post')
    def test_insert_record_returns_valid_record_id(self, mock_post):
        """D-01: 正常插入时返回非空 record_id"""
        # Mock token 响应
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "test_token",
            "expire": 7200
        }

        # Mock 插入响应
        mock_insert_response = Mock()
        mock_insert_response.status_code = 200
        mock_insert_response.json.return_value = {
            "code": 0,
            "data": {
                "record": {
                    "record_id": "rec_test_123"
                }
            }
        }

        # First call is for token, second call is for insert
        mock_post.side_effect = [mock_token_response, mock_insert_response]

        fields = {
            "选题名称": "测试选题",
            "文章链接": "https://example.com/doc",
            "创建时间": 1704067200000,
            "状态": "草稿"
        }

        record_id = insert_record(fields)

        assert record_id is not None
        assert record_id != ""
        assert record_id == "rec_test_123"

    @patch.dict(os.environ, {
        "FEISHU_APP_ID": "test_app_id",
        "FEISHU_APP_SECRET": "test_app_secret",
        "FEISHU_BITABLE_APP_TOKEN": "test_app_token",
        "FEISHU_BITABLE_TABLE_ID": "test_table_id"
    })
    @patch('requests.post')
    def test_insert_record_writes_fields_correctly(self, mock_post):
        """D-02: 字段值正确写入"""
        # Mock token 响应
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "test_token",
            "expire": 7200
        }

        # Mock 插入响应
        mock_insert_response = Mock()
        mock_insert_response.status_code = 200
        mock_insert_response.json.return_value = {
            "code": 0,
            "data": {
                "record": {
                    "record_id": "rec_test_456"
                }
            }
        }

        mock_post.side_effect = [mock_token_response, mock_insert_response]

        test_fields = {
            "选题名称": "AI产品经理复盘",
            "文章链接": "https://feishu.cn/docs/xxx",
            "创建时间": 1704067200000,
            "状态": "草稿"
        }

        insert_record(test_fields)

        # 验证 API 调用 - second call is the insert
        assert mock_post.call_count == 2
        insert_call = mock_post.call_args_list[1]
        insert_payload = insert_call[1]['json']

        assert 'fields' in insert_payload
        fields_data = insert_payload['fields']

        assert fields_data["选题名称"] == "AI产品经理复盘"
        assert fields_data["文章链接"] == "https://feishu.cn/docs/xxx"
        assert fields_data["创建时间"] == 1704067200000
        assert fields_data["状态"] == "草稿"

    def test_insert_record_raises_on_missing_required_field(self):
        """D-03: 必填字段缺失时抛出 ValueError"""
        # 缺少"选题名称"
        fields = {
            "文章链接": "https://example.com",
            "创建时间": 1704067200000,
            "状态": "草稿"
        }

        with pytest.raises(ValueError, match="必填字段缺失"):
            insert_record(fields)

        # 缺少"文章链接"
        fields = {
            "选题名称": "测试",
            "创建时间": 1704067200000,
            "状态": "草稿"
        }

        with pytest.raises(ValueError, match="必填字段缺失"):
            insert_record(fields)

        # 缺少"创建时间"
        fields = {
            "选题名称": "测试",
            "文章链接": "https://example.com",
            "状态": "草稿"
        }

        with pytest.raises(ValueError, match="必填字段缺失"):
            insert_record(fields)

        # 缺少"状态"
        fields = {
            "选题名称": "测试",
            "文章链接": "https://example.com",
            "创建时间": 1704067200000
        }

        with pytest.raises(ValueError, match="必填字段缺失"):
            insert_record(fields)

    def test_insert_record_validates_field_types(self):
        """创建时间必须是整数"""
        fields = {
            "选题名称": "测试",
            "文章链接": "https://example.com",
            "创建时间": "invalid_timestamp",  # 应该是 int
            "状态": "草稿"
        }

        with pytest.raises(ValueError, match="创建时间必须是整数"):
            insert_record(fields)

    def test_insert_record_validates_enum_values(self):
        """状态必须是有效枚举值"""
        fields = {
            "选题名称": "测试",
            "文章链接": "https://example.com",
            "创建时间": 1704067200000,
            "状态": "无效状态"  # 应该是 "草稿"/"待审核"/"已发布"
        }

        with pytest.raises(ValueError, match="无效的状态值"):
            insert_record(fields)

    @patch.dict(os.environ, {}, clear=True)
    def test_insert_record_raises_on_missing_env_vars(self):
        """环境变量缺失时抛出错误"""
        fields = {
            "选题名称": "测试",
            "文章链接": "https://example.com",
            "创建时间": 1704067200000,
            "状态": "草稿"
        }

        with pytest.raises(ValueError, match="请在环境变量中配置"):
            insert_record(fields)

    @patch.dict(os.environ, {
        "FEISHU_APP_ID": "test_app_id",
        "FEISHU_APP_SECRET": "test_app_secret",
        "FEISHU_BITABLE_APP_TOKEN": "test_app_token",
        "FEISHU_BITABLE_TABLE_ID": "test_table_id"
    })
    @patch('requests.post')
    def test_insert_record_raises_on_auth_failure(self, mock_post):
        """认证失败时抛出 RuntimeError"""
        # Mock token 认证失败
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 99991663,
            "msg": "app access token invalid"
        }
        mock_post.return_value = mock_response

        fields = {
            "选题名称": "测试",
            "文章链接": "https://example.com",
            "创建时间": 1704067200000,
            "状态": "草稿"
        }

        with pytest.raises(RuntimeError, match="飞书认证失败"):
            insert_record(fields)

    @patch.dict(os.environ, {
        "FEISHU_APP_ID": "test_app_id",
        "FEISHU_APP_SECRET": "test_app_secret",
        "FEISHU_BITABLE_APP_TOKEN": "test_app_token",
        "FEISHU_BITABLE_TABLE_ID": "test_table_id"
    })
    @patch('requests.post')
    def test_insert_record_retries_on_network_error(self, mock_post):
        """网络错误时重试机制"""
        import requests as req_module

        # Mock token 响应
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "test_token",
            "expire": 7200
        }

        # Mock 插入响应
        mock_insert_response = Mock()
        mock_insert_response.status_code = 200
        mock_insert_response.json.return_value = {
            "code": 0,
            "data": {
                "record": {
                    "record_id": "rec_test_123"
                }
            }
        }

        # First call: token success, Second call: network error, Third call: insert success
        mock_post.side_effect = [
            mock_token_response,
            req_module.exceptions.RequestException("Network error"),
            mock_insert_response
        ]

        fields = {
            "选题名称": "测试",
            "文章链接": "https://example.com",
            "创建时间": 1704067200000,
            "状态": "草稿"
        }

        record_id = insert_record(fields)

        assert record_id == "rec_test_123"
        assert mock_post.call_count == 3

    @patch.dict(os.environ, {
        "FEISHU_APP_ID": "test_app_id",
        "FEISHU_APP_SECRET": "test_app_secret",
        "FEISHU_BITABLE_APP_TOKEN": "test_app_token",
        "FEISHU_BITABLE_TABLE_ID": "test_table_id"
    })
    @patch('requests.post')
    def test_insert_record_timeout_handling(self, mock_post):
        """请求超时处理"""
        import requests as req_module

        # Mock token 响应
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "test_token",
            "expire": 7200
        }

        # First call: token success, Second and third calls: timeout
        mock_post.side_effect = [
            mock_token_response,
            req_module.exceptions.Timeout("Request timeout"),
            req_module.exceptions.Timeout("Request timeout")
        ]

        fields = {
            "选题名称": "测试",
            "文章链接": "https://example.com",
            "创建时间": 1704067200000,
            "状态": "草稿"
        }

        with pytest.raises(RuntimeError, match="请求超时"):
            insert_record(fields)

    @patch.dict(os.environ, {
        "FEISHU_APP_ID": "test_app_id",
        "FEISHU_APP_SECRET": "test_app_secret",
        "FEISHU_BITABLE_APP_TOKEN": "test_app_token",
        "FEISHU_BITABLE_TABLE_ID": "test_table_id"
    })
    @patch('requests.post')
    @patch('time.sleep')  # Mock sleep to speed up test
    def test_insert_record_handles_rate_limiting(self, mock_sleep, mock_post):
        """API限流处理"""
        # Mock token 响应
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "test_token",
            "expire": 7200
        }

        # Mock 429 响应（限流）
        mock_rate_limit_response = Mock()
        mock_rate_limit_response.status_code = 429

        # Mock 成功响应
        mock_success_response = Mock()
        mock_success_response.status_code = 200
        mock_success_response.json.return_value = {
            "code": 0,
            "data": {
                "record": {
                    "record_id": "rec_test_789"
                }
            }
        }

        # First call: token, Second call: 429, Third call: success
        mock_post.side_effect = [
            mock_token_response,
            mock_rate_limit_response,
            mock_success_response
        ]

        fields = {
            "选题名称": "测试",
            "文章链接": "https://example.com",
            "创建时间": 1704067200000,
            "状态": "草稿"
        }

        record_id = insert_record(fields)

        assert record_id == "rec_test_789"
        assert mock_post.call_count == 3
