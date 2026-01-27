"""测试 MiniMax temperature 参数验证"""
import pytest
from src.utils.temperature import validate_temperature


class TestTemperatureValidation:
    """Temperature 验证测试"""

    def test_zero_temperature_adjusted_to_minimum(self):
        """测试 0.0 被调整为最小值 0.001"""
        assert validate_temperature(0.0) == 0.001

    def test_negative_temperature_adjusted_to_minimum(self):
        """测试负数被调整为最小值"""
        assert validate_temperature(-0.5) == 0.001
        assert validate_temperature(-1.0) == 0.001

    def test_valid_temperature_unchanged(self):
        """测试有效范围内的值不变"""
        assert validate_temperature(0.001) == 0.001
        assert validate_temperature(0.5) == 0.5
        assert validate_temperature(0.7) == 0.7
        assert validate_temperature(0.9) == 0.9

    def test_max_temperature_valid(self):
        """测试最大值 1.0 有效"""
        assert validate_temperature(1.0) == 1.0

    def test_over_max_clamped_to_one(self):
        """测试超出最大值被限制为 1.0"""
        assert validate_temperature(1.1) == 1.0
        assert validate_temperature(1.5) == 1.0
        assert validate_temperature(2.0) == 1.0
