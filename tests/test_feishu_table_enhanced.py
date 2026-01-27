"""测试飞书表格新增字段"""
import pytest
from src.modules.feishu_table import _validate_optional_fields


class TestFeishuTableEnhancements:
    """测试飞书表格新字段验证"""

    def test_validate_optional_fields_valid(self):
        """测试有效的可选字段"""
        fields = {
            "运行时长（秒）": 45.67,
            "Token使用量": 1500,
            "工具调用次数": 3,
            "日志文档URL": "https://feishu.cn/docx/abc123"
        }

        # 不应抛出异常
        _validate_optional_fields(fields)

    def test_validate_runtime_seconds_type(self):
        """测试运行时长类型验证"""
        # 整数应该可以
        _validate_optional_fields({"运行时长（秒）": 45})

        # 浮点数应该可以
        _validate_optional_fields({"运行时长（秒）": 45.67})

        # 字符串应该报错
        with pytest.raises(ValueError, match="运行时长"):
            _validate_optional_fields({"运行时长（秒）": "not a number"})

    def test_validate_token_usage_type(self):
        """测试Token使用量类型验证"""
        # 整数应该可以
        _validate_optional_fields({"Token使用量": 1500})

        # 浮点数应该报错（必须是整数）
        with pytest.raises(ValueError, match="Token使用量"):
            _validate_optional_fields({"Token使用量": 1500.5})

        # 字符串应该报错
        with pytest.raises(ValueError, match="Token使用量"):
            _validate_optional_fields({"Token使用量": "not an int"})

    def test_validate_tool_call_count_type(self):
        """测试工具调用次数类型验证"""
        # 整数应该可以
        _validate_optional_fields({"工具调用次数": 5})

        # 浮点数应该报错
        with pytest.raises(ValueError, match="工具调用次数"):
            _validate_optional_fields({"工具调用次数": 5.5})

        # 字符串应该报错
        with pytest.raises(ValueError, match="工具调用次数"):
            _validate_optional_fields({"工具调用次数": "not an int"})

    def test_validate_log_url_type(self):
        """测试日志文档URL类型验证"""
        # 字符串应该可以
        _validate_optional_fields({"日志文档URL": "https://feishu.cn/docx/test"})

        # 数字应该报错
        with pytest.raises(ValueError, match="日志文档URL"):
            _validate_optional_fields({"日志文档URL": 12345})

        # 列表应该报错
        with pytest.raises(ValueError, match="日志文档URL"):
            _validate_optional_fields({"日志文档URL": ["not", "a", "string"]})

    def test_optional_fields_none_allowed(self):
        """测试None值应该被允许"""
        fields = {
            "运行时长（秒）": None,
            "Token使用量": None,
            "工具调用次数": None,
            "日志文档URL": None
        }

        # 不应抛出异常
        _validate_optional_fields(fields)

    def test_optional_fields_can_be_omitted(self):
        """测试可选字段可以不提供"""
        # 空字典应该通过
        _validate_optional_fields({})

        # 只提供部分字段应该通过
        _validate_optional_fields({"Token使用量": 1000})

    def test_mixed_valid_and_invalid_fields(self):
        """测试混合有效和无效字段"""
        fields = {
            "运行时长（秒）": 45.67,  # 有效
            "Token使用量": "invalid",  # 无效
        }

        with pytest.raises(ValueError, match="Token使用量"):
            _validate_optional_fields(fields)

    def test_empty_string_url(self):
        """测试空字符串URL"""
        # 空字符串应该被允许（作为字符串类型）
        _validate_optional_fields({"日志文档URL": ""})

    def test_zero_values(self):
        """测试零值"""
        fields = {
            "运行时长（秒）": 0.0,
            "Token使用量": 0,
            "工具调用次数": 0
        }

        # 不应抛出异常
        _validate_optional_fields(fields)
