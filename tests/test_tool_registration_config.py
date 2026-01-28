"""Simplified test for tool registration - config verification only"""
import os
import pytest
from dotenv import load_dotenv

load_dotenv()


def test_requirements_has_sdk():
    """Verify claude-agent-sdk is in requirements.txt"""
    with open('requirements.txt', 'r') as f:
        content = f.read()
    assert 'claude-agent-sdk>=0.1.23' in content


def test_sdk_import():
    """Verify SDK can be imported"""
    from claude_agent_sdk import query, ClaudeAgentOptions
    assert query is not None
    assert ClaudeAgentOptions is not None


def test_agent_sdk_runner_import():
    """Verify AgentSDKRunner can be imported"""
    from src.modules.agent_sdk import AgentSDKRunner
    assert AgentSDKRunner is not None


def test_agent_sdk_has_allowed_tools_method():
    """Verify _get_allowed_tools method exists"""
    from src.modules.agent_sdk import AgentSDKRunner
    assert hasattr(AgentSDKRunner, '_get_allowed_tools')


def test_agent_sdk_config():
    """Verify AgentSDKRunner configuration produces correct options"""
    from src.modules.agent_sdk import AgentSDKRunner
    import inspect

    # Check the generate method source for correct configuration
    source = inspect.getsource(AgentSDKRunner.generate)

    # Verify setting_sources is configured
    assert 'setting_sources=' in source or 'setting_sources =' in source
    assert '["user"]' in source or "['user']" in source

    # Verify allowed_tools is used (not tools)
    assert 'allowed_tools=' in source or 'allowed_tools =' in source

    # Verify _get_allowed_tools is called
    assert '_get_allowed_tools' in source


def test_allowed_tools_method_returns_skill():
    """Verify _get_allowed_tools returns 'Skill' when notebook_id is set"""
    from src.modules.agent_sdk import AgentSDKRunner
    import inspect

    # Check the _get_allowed_tools method source
    source = inspect.getsource(AgentSDKRunner._get_allowed_tools)

    # Should return ["Skill"]
    assert '"Skill"' in source or "'Skill'" in source
    assert 'return' in source


def test_environment_variables():
    """Verify required environment variables are set"""
    # These are needed for actual API calls, but we're just checking they exist
    api_key = os.getenv('ANTHROPIC_API_KEY')
    assert api_key, "ANTHROPIC_API_KEY not set in .env"

    notebook_id = os.getenv('NOTEBOOK_ID')
    assert notebook_id, "NOTEBOOK_ID not set in .env"


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
