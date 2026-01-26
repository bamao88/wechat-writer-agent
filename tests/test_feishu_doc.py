"""模块C：飞书云文档写入 - 单元测试"""

import os
import time
from unittest.mock import Mock, patch, MagicMock
import pytest

from src.modules.feishu_doc import (
    FeishuTokenManager,
    MarkdownToBlockConverter,
    create_doc,
    _token_cache
)
from src.models import DocResult


class TestFeishuTokenManager:
    """FeishuTokenManager 测试"""

    def setup_method(self):
        """每个测试前清空缓存"""
        global _token_cache
        _token_cache["token"] = None
        _token_cache["expires_at"] = 0

    def test_get_token_uses_cache(self):
        """测试token缓存机制"""
        # 设置有效缓存
        _token_cache["token"] = "cached_token"
        _token_cache["expires_at"] = time.time() + 3600

        manager = FeishuTokenManager("test_id", "test_secret")
        token = manager.get_token()

        assert token == "cached_token"

    def test_token_refresh_on_expiry(self):
        """测试token过期自动刷新"""
        # 设置已过期缓存
        _token_cache["token"] = "old_token"
        _token_cache["expires_at"] = time.time() - 100

        manager = FeishuTokenManager("test_id", "test_secret")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "new_token",
            "expire": 7200
        }

        with patch('requests.post', return_value=mock_response):
            token = manager.get_token()

        assert token == "new_token"
        assert _token_cache["token"] == "new_token"

    def test_get_token_raises_on_auth_failure(self):
        """测试认证失败抛出异常"""
        manager = FeishuTokenManager("test_id", "test_secret")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 99991663,
            "msg": "app access token invalid"
        }

        with patch('requests.post', return_value=mock_response):
            with pytest.raises(RuntimeError, match="飞书认证失败"):
                manager.get_token()

    def test_get_token_with_network_retry(self):
        """测试网络错误重试"""
        import requests
        manager = FeishuTokenManager("test_id", "test_secret")

        # 第一次超时，第二次成功
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "code": 0,
            "tenant_access_token": "retry_token",
            "expire": 7200
        }

        with patch('requests.post', side_effect=[
            requests.exceptions.RequestException("Network error"),
            mock_response_success
        ]):
            token = manager.get_token()

        assert token == "retry_token"

    def test_init_raises_on_empty_credentials(self):
        """测试空凭证抛出异常"""
        with pytest.raises(ValueError, match="app_id 和 app_secret 不能为空"):
            FeishuTokenManager("", "secret")

        with pytest.raises(ValueError, match="app_id 和 app_secret 不能为空"):
            FeishuTokenManager("id", "")


class TestMarkdownToBlockConverter:
    """MarkdownToBlockConverter 测试"""

    def test_convert_simple_paragraph(self):
        """测试普通段落转换"""
        converter = MarkdownToBlockConverter()
        markdown = "这是一个简单段落。"

        blocks = converter.convert(markdown)

        assert len(blocks) == 1
        assert blocks[0]["block_type"] == 2
        assert blocks[0]["text"]["elements"][0]["text_run"]["content"] == "这是一个简单段落。"

    def test_convert_heading_levels(self):
        """测试标题级别转换"""
        converter = MarkdownToBlockConverter()
        markdown = """# 一级标题

## 二级标题

### 三级标题"""

        blocks = converter.convert(markdown)

        assert len(blocks) == 3
        assert blocks[0]["text"]["style"]["heading_level"] == 1
        assert blocks[0]["text"]["elements"][0]["text_run"]["content"] == "一级标题"

        assert blocks[1]["text"]["style"]["heading_level"] == 2
        assert blocks[1]["text"]["elements"][0]["text_run"]["content"] == "二级标题"

        assert blocks[2]["text"]["style"]["heading_level"] == 3
        assert blocks[2]["text"]["elements"][0]["text_run"]["content"] == "三级标题"

    def test_convert_multiline_content(self):
        """测试多行内容转换"""
        converter = MarkdownToBlockConverter()
        markdown = """# 标题

第一段内容。

第二段内容。"""

        blocks = converter.convert(markdown)

        assert len(blocks) == 3
        assert blocks[0]["text"]["style"]["heading_level"] == 1
        assert blocks[1]["text"]["elements"][0]["text_run"]["content"] == "第一段内容。"
        assert blocks[2]["text"]["elements"][0]["text_run"]["content"] == "第二段内容。"

    def test_convert_empty_content(self):
        """测试空内容"""
        converter = MarkdownToBlockConverter()

        assert converter.convert("") == []
        assert converter.convert("   ") == []
        assert converter.convert("\n\n") == []

    def test_convert_preserves_paragraph_breaks(self):
        """测试段落分割保留"""
        converter = MarkdownToBlockConverter()
        markdown = "段落一\n\n段落二\n\n段落三"

        blocks = converter.convert(markdown)

        assert len(blocks) == 3
        assert blocks[0]["text"]["elements"][0]["text_run"]["content"] == "段落一"
        assert blocks[1]["text"]["elements"][0]["text_run"]["content"] == "段落二"
        assert blocks[2]["text"]["elements"][0]["text_run"]["content"] == "段落三"


class TestCreateDoc:
    """create_doc 核心验收测试"""

    def setup_method(self):
        """每个测试前清空缓存"""
        global _token_cache
        _token_cache["token"] = None
        _token_cache["expires_at"] = 0

    @patch.dict(os.environ, {
        "FEISHU_APP_ID": "test_app_id",
        "FEISHU_APP_SECRET": "test_app_secret",
        "FEISHU_TENANT_DOMAIN": "test_domain"
    })
    @patch('src.modules.feishu_doc.requests.post')
    def test_create_doc_returns_valid_url(self, mock_post):
        """C-01: 返回的URL包含feishu.cn"""
        # Mock token获取
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "test_token",
            "expire": 7200
        }

        # Mock创建文档
        mock_create_response = Mock()
        mock_create_response.status_code = 200
        mock_create_response.json.return_value = {
            "code": 0,
            "data": {
                "document": {
                    "document_id": "test_doc_id_123"
                }
            }
        }

        # Mock写入内容
        mock_write_response = Mock()
        mock_write_response.status_code = 200
        mock_write_response.json.return_value = {"code": 0}

        mock_post.side_effect = [
            mock_token_response,
            mock_create_response,
            mock_write_response
        ]

        result = create_doc(
            title="测试文档",
            content="# 测试内容",
            folder_token="test_folder"
        )

        assert "feishu.cn" in result.doc_url
        assert result.doc_url == "https://test_domain.feishu.cn/docx/test_doc_id_123"

    @patch.dict(os.environ, {
        "FEISHU_APP_ID": "test_app_id",
        "FEISHU_APP_SECRET": "test_app_secret",
        "FEISHU_TENANT_DOMAIN": "test_domain"
    })
    @patch('src.modules.feishu_doc.requests.post')
    def test_create_doc_returns_valid_doc_id(self, mock_post):
        """C-02: 返回的doc_id非空且有效"""
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "test_token",
            "expire": 7200
        }

        mock_create_response = Mock()
        mock_create_response.status_code = 200
        mock_create_response.json.return_value = {
            "code": 0,
            "data": {
                "document": {
                    "document_id": "valid_doc_123"
                }
            }
        }

        mock_write_response = Mock()
        mock_write_response.status_code = 200
        mock_write_response.json.return_value = {"code": 0}

        mock_post.side_effect = [
            mock_token_response,
            mock_create_response,
            mock_write_response
        ]

        result = create_doc(
            title="测试文档",
            content="# 测试",
            folder_token="test_folder"
        )

        assert result.doc_id is not None
        assert result.doc_id != ""
        assert result.doc_id == "valid_doc_123"

    @patch.dict(os.environ, {
        "FEISHU_APP_ID": "test_app_id",
        "FEISHU_APP_SECRET": "test_app_secret",
        "FEISHU_TENANT_DOMAIN": "test_domain"
    })
    @patch('src.modules.feishu_doc.requests.post')
    def test_create_doc_writes_content_correctly(self, mock_post):
        """C-03: 文档内容包含输入的内容"""
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "test_token",
            "expire": 7200
        }

        mock_create_response = Mock()
        mock_create_response.status_code = 200
        mock_create_response.json.return_value = {
            "code": 0,
            "data": {
                "document": {
                    "document_id": "doc_123"
                }
            }
        }

        mock_write_response = Mock()
        mock_write_response.status_code = 200
        mock_write_response.json.return_value = {"code": 0}

        mock_post.side_effect = [
            mock_token_response,
            mock_create_response,
            mock_write_response
        ]

        test_content = "# 测试标题\n\n这是测试内容。"
        create_doc(
            title="测试文档",
            content=test_content,
            folder_token="test_folder"
        )

        # 验证写入调用
        write_call = mock_post.call_args_list[2]
        write_payload = write_call[1]['json']

        assert 'children' in write_payload
        blocks = write_payload['children']

        # 验证包含标题和内容
        assert len(blocks) == 2
        assert blocks[0]['text']['elements'][0]['text_run']['content'] == "测试标题"
        assert blocks[1]['text']['elements'][0]['text_run']['content'] == "这是测试内容。"

    @patch.dict(os.environ, {
        "FEISHU_APP_ID": "test_app_id",
        "FEISHU_APP_SECRET": "test_app_secret",
        "FEISHU_TENANT_DOMAIN": "test_domain"
    })
    @patch('src.modules.feishu_doc.requests.post')
    def test_create_doc_sets_title_correctly(self, mock_post):
        """C-04: 文档标题与输入一致"""
        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "test_token",
            "expire": 7200
        }

        mock_create_response = Mock()
        mock_create_response.status_code = 200
        mock_create_response.json.return_value = {
            "code": 0,
            "data": {
                "document": {
                    "document_id": "doc_123"
                }
            }
        }

        mock_write_response = Mock()
        mock_write_response.status_code = 200
        mock_write_response.json.return_value = {"code": 0}

        mock_post.side_effect = [
            mock_token_response,
            mock_create_response,
            mock_write_response
        ]

        test_title = "我的测试文档标题"
        create_doc(
            title=test_title,
            content="# 内容",
            folder_token="test_folder"
        )

        # 验证创建文档调用
        create_call = mock_post.call_args_list[1]
        create_payload = create_call[1]['json']

        assert create_payload['title'] == test_title

    def test_create_doc_raises_on_missing_params(self):
        """测试参数验证"""
        with pytest.raises(ValueError, match="文档标题不能为空"):
            create_doc(title="", content="content", folder_token="token")

        with pytest.raises(ValueError, match="文档内容不能为空"):
            create_doc(title="title", content="", folder_token="token")

        with pytest.raises(ValueError, match="folder_token不能为空"):
            create_doc(title="title", content="content", folder_token="")

    @patch.dict(os.environ, {
        "FEISHU_APP_ID": "test_app_id",
        "FEISHU_APP_SECRET": "test_app_secret",
        "FEISHU_TENANT_DOMAIN": "test_domain"
    })
    @patch('src.modules.feishu_doc.requests.post')
    def test_create_doc_raises_on_auth_failure(self, mock_post):
        """测试认证失败处理"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "code": 99991663,
            "msg": "app access token invalid"
        }

        mock_post.return_value = mock_response

        with pytest.raises(RuntimeError, match="飞书认证失败"):
            create_doc(
                title="测试",
                content="内容",
                folder_token="token"
            )

    @patch.dict(os.environ, {
        "FEISHU_APP_ID": "test_app_id",
        "FEISHU_APP_SECRET": "test_app_secret",
        "FEISHU_TENANT_DOMAIN": "test_domain"
    })
    @patch('src.modules.feishu_doc.requests.post')
    def test_create_doc_retries_on_network_error(self, mock_post):
        """测试网络错误重试机制"""
        import requests

        mock_token_response = Mock()
        mock_token_response.status_code = 200
        mock_token_response.json.return_value = {
            "code": 0,
            "tenant_access_token": "test_token",
            "expire": 7200
        }

        mock_create_response = Mock()
        mock_create_response.status_code = 200
        mock_create_response.json.return_value = {
            "code": 0,
            "data": {
                "document": {
                    "document_id": "doc_123"
                }
            }
        }

        mock_write_response = Mock()
        mock_write_response.status_code = 200
        mock_write_response.json.return_value = {"code": 0}

        # 第一次token失败，第二次成功
        mock_post.side_effect = [
            requests.exceptions.RequestException("Network error"),
            mock_token_response,
            mock_create_response,
            mock_write_response
        ]

        result = create_doc(
            title="测试",
            content="# 内容",
            folder_token="token"
        )

        assert result.doc_id == "doc_123"

    @patch.dict(os.environ, {
        "FEISHU_APP_ID": "test_app_id",
        "FEISHU_APP_SECRET": "test_app_secret",
        "FEISHU_TENANT_DOMAIN": "test_domain"
    })
    @patch('src.modules.feishu_doc.requests.post')
    def test_create_doc_timeout_handling(self, mock_post):
        """测试超时处理"""
        import requests

        # 所有请求都超时
        mock_post.side_effect = requests.exceptions.Timeout("Request timeout")

        with pytest.raises(RuntimeError, match="获取token超时"):
            create_doc(
                title="测试",
                content="内容",
                folder_token="token"
            )

    @patch.dict(os.environ, {})
    def test_create_doc_raises_on_missing_env_vars(self):
        """测试环境变量缺失"""
        with pytest.raises(ValueError, match="请在环境变量中配置 FEISHU_APP_ID 和 FEISHU_APP_SECRET"):
            create_doc(
                title="测试",
                content="内容",
                folder_token="token"
            )

    @patch.dict(os.environ, {
        "FEISHU_APP_ID": "test_app_id",
        "FEISHU_APP_SECRET": "test_app_secret"
    })
    def test_create_doc_raises_on_missing_tenant_domain(self):
        """测试TENANT_DOMAIN缺失"""
        with pytest.raises(ValueError, match="请在环境变量中配置 FEISHU_TENANT_DOMAIN"):
            create_doc(
                title="测试",
                content="内容",
                folder_token="token"
            )
