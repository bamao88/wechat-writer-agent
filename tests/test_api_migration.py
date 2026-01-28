"""
Migration validation tests for official Anthropic API.

These tests verify that the codebase correctly supports official API
while maintaining backward compatibility with MiniMax.
"""
import os
import pytest
from unittest.mock import patch, MagicMock


class TestDualModeDetection:
    """Test API mode detection logic."""

    def test_official_api_no_base_url(self):
        """Official API mode when ANTHROPIC_BASE_URL is not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove any existing ANTHROPIC_BASE_URL
            os.environ.pop("ANTHROPIC_BASE_URL", None)

            from src.modules.generator import _create_anthropic_client

            # Should not raise, should create client for official API
            client = _create_anthropic_client("test-api-key")
            assert client is not None
            # Official API base URL
            assert "anthropic.com" in str(client.base_url) or client.base_url is None

    def test_minimax_api_with_base_url(self):
        """MiniMax API mode when ANTHROPIC_BASE_URL contains minimaxi.com."""
        with patch.dict(os.environ, {"ANTHROPIC_BASE_URL": "https://api.minimaxi.com/anthropic/v1/messages"}):
            from importlib import reload
            import src.modules.generator as generator_module
            reload(generator_module)

            client = generator_module._create_anthropic_client("test-api-key")
            assert client is not None
            assert "minimaxi.com" in str(client.base_url)


class TestAdaptiveTimeout:
    """Test timeout adaptation based on API backend."""

    def test_official_api_timeout(self):
        """Official API should use 120s timeout."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_BASE_URL", None)

            from src.modules.agent_sdk import AgentSDKRunner
            runner = AgentSDKRunner("key", "claude-sonnet-4-5", 0.7)

            timeout = runner._get_api_timeout_ms()
            assert timeout == "120000"  # 120 seconds

    def test_minimax_api_timeout(self):
        """MiniMax API should use 3000s timeout."""
        with patch.dict(os.environ, {"ANTHROPIC_BASE_URL": "https://api.minimaxi.com/test"}):
            from importlib import reload
            import src.modules.agent_sdk as sdk_module
            reload(sdk_module)

            runner = sdk_module.AgentSDKRunner("key", "MiniMax-M2.1", 0.7)

            timeout = runner._get_api_timeout_ms()
            assert timeout == "3000000"  # 3000 seconds


class TestConditionalTemperature:
    """Test temperature validation based on API backend."""

    def test_official_api_allows_zero_temperature(self):
        """Official API should allow temperature=0.0."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_BASE_URL", None)

            from importlib import reload
            import src.utils.temperature as temp_module
            reload(temp_module)

            result = temp_module.validate_temperature(0.0)
            assert result == 0.0  # Unchanged

    def test_minimax_api_forces_nonzero_temperature(self):
        """MiniMax API should force temperature > 0.0."""
        with patch.dict(os.environ, {"ANTHROPIC_BASE_URL": "https://api.minimaxi.com/test"}):
            from importlib import reload
            import src.utils.temperature as temp_module
            reload(temp_module)

            result = temp_module.validate_temperature(0.0)
            assert result == 0.001  # Forced to minimum

    def test_normal_temperature_unchanged(self):
        """Normal temperature values should be unchanged."""
        from src.utils.temperature import validate_temperature

        assert validate_temperature(0.7) == 0.7
        assert validate_temperature(1.0) == 1.0


class TestDefaultModelConfiguration:
    """Test default model configuration."""

    def test_default_model_is_not_minimax(self):
        """Default model should not be MiniMax-M2.1."""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure MODEL_NAME is not set to force default
            os.environ.pop("MODEL_NAME", None)

            from importlib import reload
            import src.modules.generator as gen
            reload(gen)

            import inspect
            gen_sig = inspect.signature(gen.generate)
            gen_sdk_sig = inspect.signature(gen.generate_with_sdk)

            # Model parameter should NOT be MiniMax-M2.1
            model_default = str(gen_sig.parameters['model'].default)
            model_sdk_default = str(gen_sdk_sig.parameters['model'].default)

            # The defaults should either be:
            # 1. A Claude model name directly (e.g., "claude-sonnet-4-5")
            # 2. The result of os.getenv() which at import time resolves to the default
            assert "MiniMax-M2.1" != model_default, f"generate() should not default to MiniMax-M2.1, got: {model_default}"
            assert "MiniMax-M2.1" != model_sdk_default, f"generate_with_sdk() should not default to MiniMax-M2.1, got: {model_sdk_default}"


class TestMigrationChecklist:
    """
    Migration checklist tests - these verify the success criteria.

    MIG-01: System uses official Anthropic API (api.anthropic.com)
    MIG-02: MiniMax-specific code is conditional/removable
    MIG-03: Tool calling mechanism works (tested elsewhere)
    MIG-04: All integration tests pass (run full suite)
    """

    def test_mig_01_official_api_is_default(self):
        """MIG-01: Without ANTHROPIC_BASE_URL, official API is used."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_BASE_URL", None)

            from src.utils.temperature import is_minimax_api
            assert is_minimax_api() is False

    def test_mig_02_minimax_code_is_conditional(self):
        """MIG-02: MiniMax-specific behavior only activates with correct env var."""
        # Without MiniMax base URL
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_BASE_URL", None)

            from importlib import reload
            import src.utils.temperature as temp_module
            reload(temp_module)

            # Should NOT apply MiniMax constraints
            assert temp_module.validate_temperature(0.0) == 0.0

        # With MiniMax base URL
        with patch.dict(os.environ, {"ANTHROPIC_BASE_URL": "https://api.minimaxi.com/v1"}):
            reload(temp_module)

            # SHOULD apply MiniMax constraints
            assert temp_module.validate_temperature(0.0) == 0.001
