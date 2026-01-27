"""测试AgentSDKRunner类"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.modules.agent_sdk import AgentSDKRunner, AgentRunMetrics
from src.models import SearchResult


# Helper function to create async iterator mock
async def async_iterator(items):
    """Create an async iterator from a list of items"""
    for item in items:
        yield item


class TestAgentSDKRunnerInit:
    """测试AgentSDKRunner初始化"""

    def test_init_with_required_params(self):
        """测试仅使用必需参数初始化"""
        runner = AgentSDKRunner(
            api_key="test-api-key",
            model="claude-sonnet-4",
            temperature=0.7
        )

        assert runner.api_key == "test-api-key"
        assert runner.model == "claude-sonnet-4"
        assert runner.temperature == 0.7
        assert runner.notebook_id is None
        assert runner.notebook_url is None

    def test_init_with_notebook_params(self):
        """测试包含NotebookLM参数初始化"""
        runner = AgentSDKRunner(
            api_key="test-key",
            model="claude-sonnet-4",
            temperature=0.5,
            notebook_id="nb-123",
            notebook_url="https://notebooklm.google.com/notebook/abc"
        )

        assert runner.notebook_id == "nb-123"
        assert runner.notebook_url == "https://notebooklm.google.com/notebook/abc"


class TestAgentSDKRunnerGetToolsConfig:
    """测试_get_tools_config方法"""

    def test_get_tools_config_without_notebook(self):
        """测试无NotebookLM时返回空工具列表"""
        runner = AgentSDKRunner(
            api_key="test-key",
            model="claude-sonnet-4",
            temperature=0.7
        )

        tools = runner._get_tools_config()

        assert tools == []

    def test_get_tools_config_with_notebook(self):
        """测试有NotebookLM时返回工具定义"""
        runner = AgentSDKRunner(
            api_key="test-key",
            model="claude-sonnet-4",
            temperature=0.7,
            notebook_id="nb-123",
            notebook_url="https://notebooklm.google.com/notebook/abc"
        )

        tools = runner._get_tools_config()

        assert len(tools) == 1
        assert tools[0]["name"] == "query_notebooklm"
        assert tools[0]["type"] == "custom"
        assert "description" in tools[0]
        assert "input_schema" in tools[0]

    def test_get_tools_config_includes_notebook_id_in_schema(self):
        """测试工具定义包含notebook_id"""
        runner = AgentSDKRunner(
            api_key="test-key",
            model="claude-sonnet-4",
            temperature=0.7,
            notebook_id="nb-456"
        )

        tools = runner._get_tools_config()

        # 验证schema包含必需的属性
        schema = tools[0]["input_schema"]
        assert schema["type"] == "object"
        assert "question" in schema["properties"]
        assert "question" in schema["required"]


class TestAgentSDKRunnerBuildUserMessage:
    """测试_build_user_message方法"""

    def test_build_user_message_with_search_results(self):
        """测试构建包含搜索结果的消息"""
        runner = AgentSDKRunner(
            api_key="test-key",
            model="claude-sonnet-4",
            temperature=0.7
        )

        search_results = [
            SearchResult(
                content="这是第一个素材的内容",
                source="来源1"
            ),
            SearchResult(
                content="这是第二个素材的内容",
                source="来源2"
            )
        ]

        message = runner._build_user_message("测试选题", search_results)

        assert "测试选题" in message
        assert "这是第一个素材的内容" in message
        assert "来源1" in message
        assert "这是第二个素材的内容" in message
        assert "来源2" in message

    def test_build_user_message_without_search_results(self):
        """测试构建无搜索结果的消息"""
        runner = AgentSDKRunner(
            api_key="test-key",
            model="claude-sonnet-4",
            temperature=0.7
        )

        message = runner._build_user_message("测试选题", [])

        assert "测试选题" in message
        assert message != ""

    def test_build_user_message_format(self):
        """测试消息格式正确"""
        runner = AgentSDKRunner(
            api_key="test-key",
            model="claude-sonnet-4",
            temperature=0.7
        )

        search_results = [
            SearchResult(
                content="Test content",
                source="Test source"
            )
        ]

        message = runner._build_user_message("Test Topic", search_results)

        # 验证基本结构
        assert isinstance(message, str)
        assert len(message) > 0
        assert "Test Topic" in message
        assert "Test content" in message


class TestAgentSDKRunnerCreateHooks:
    """测试_create_hooks方法"""

    def test_create_hooks_returns_dict(self):
        """测试返回hooks配置字典"""
        runner = AgentSDKRunner(
            api_key="test-key",
            model="claude-sonnet-4",
            temperature=0.7
        )

        metrics = AgentRunMetrics()
        hooks = runner._create_hooks(metrics)

        assert isinstance(hooks, dict)

    def test_create_hooks_includes_all_events(self):
        """测试包含所有必需的hook事件"""
        runner = AgentSDKRunner(
            api_key="test-key",
            model="claude-sonnet-4",
            temperature=0.7
        )

        metrics = AgentRunMetrics()
        hooks = runner._create_hooks(metrics)

        # 验证包含4个hook事件
        assert "PreToolUse" in hooks
        assert "PostToolUse" in hooks
        assert "Stop" in hooks
        assert "UserPromptSubmit" in hooks

    def test_create_hooks_injects_metrics(self):
        """测试hooks能访问metrics实例"""
        runner = AgentSDKRunner(
            api_key="test-key",
            model="claude-sonnet-4",
            temperature=0.7
        )

        metrics = AgentRunMetrics()
        hooks = runner._create_hooks(metrics)

        # 验证hooks配置格式
        for event_name in ["PreToolUse", "PostToolUse", "Stop", "UserPromptSubmit"]:
            assert isinstance(hooks[event_name], list)
            assert len(hooks[event_name]) > 0


class TestAgentSDKRunnerGenerate:
    """测试generate方法"""

    @pytest.mark.asyncio
    @patch('src.modules.agent_sdk.query')
    async def test_generate_basic_flow(self, mock_query):
        """测试基本生成流程"""
        # Mock SDK query返回
        mock_message = MagicMock()
        mock_message.text = "生成的文章内容"
        mock_message.stop_reason = "end_turn"

        mock_query.return_value = async_iterator([mock_message])

        runner = AgentSDKRunner(
            api_key="test-key",
            model="claude-sonnet-4",
            temperature=0.7
        )

        result_text, metrics = await runner.generate(
            topic="测试选题",
            search_results=[],
            system_prompt="系统提示",
            max_turns=5
        )

        # 验证返回值
        assert result_text == "生成的文章内容"
        assert isinstance(metrics, AgentRunMetrics)
        assert metrics.end_time is not None

    @pytest.mark.asyncio
    @patch('src.modules.agent_sdk.query')
    async def test_generate_calls_query_with_correct_params(self, mock_query):
        """测试调用query时使用正确的参数"""
        mock_message = MagicMock()
        mock_message.text = "内容"
        mock_message.stop_reason = "end_turn"
        mock_query.return_value = async_iterator([mock_message])

        runner = AgentSDKRunner(
            api_key="test-key",
            model="claude-sonnet-4",
            temperature=0.8
        )

        await runner.generate(
            topic="测试",
            search_results=[],
            system_prompt="提示",
            max_turns=10
        )

        # 验证query被调用
        mock_query.assert_called_once()
        call_kwargs = mock_query.call_args[1]

        # 验证关键参数
        assert "prompt" in call_kwargs
        assert call_kwargs["options"].model == "claude-sonnet-4"
        assert call_kwargs["options"].max_turns == 10
        assert call_kwargs["options"].system_prompt == "提示"

    @pytest.mark.asyncio
    @patch('src.modules.agent_sdk.query')
    async def test_generate_with_search_results(self, mock_query):
        """测试包含搜索结果的生成"""
        mock_message = MagicMock()
        mock_message.text = "基于搜索结果的文章"
        mock_message.stop_reason = "end_turn"
        mock_query.return_value = async_iterator([mock_message])

        runner = AgentSDKRunner(
            api_key="test-key",
            model="claude-sonnet-4",
            temperature=0.7
        )

        search_results = [
            SearchResult(
                content="参考资料内容",
                source="https://example.com"
            )
        ]

        result_text, metrics = await runner.generate(
            topic="测试选题",
            search_results=search_results,
            system_prompt="系统提示",
            max_turns=5
        )

        # 验证调用了query
        mock_query.assert_called_once()
        # 验证prompt包含搜索结果
        call_kwargs = mock_query.call_args[1]
        assert "参考资料内容" in call_kwargs["prompt"]

    @pytest.mark.asyncio
    @patch('src.modules.agent_sdk.query')
    async def test_generate_registers_hooks(self, mock_query):
        """测试generate注册hooks"""
        mock_message = MagicMock()
        mock_message.text = "内容"
        mock_message.stop_reason = "end_turn"
        mock_query.return_value = async_iterator([mock_message])

        runner = AgentSDKRunner(
            api_key="test-key",
            model="claude-sonnet-4",
            temperature=0.7
        )

        await runner.generate(
            topic="测试",
            search_results=[],
            system_prompt="提示",
            max_turns=5
        )

        # 验证hooks被传递
        call_kwargs = mock_query.call_args[1]
        assert "options" in call_kwargs
        assert hasattr(call_kwargs["options"], "hooks")
        assert call_kwargs["options"].hooks is not None

    @pytest.mark.asyncio
    @patch('src.modules.agent_sdk.query')
    async def test_generate_with_tools(self, mock_query):
        """测试包含工具配置的生成"""
        mock_message = MagicMock()
        mock_message.text = "使用工具的结果"
        mock_message.stop_reason = "end_turn"
        mock_query.return_value = async_iterator([mock_message])

        runner = AgentSDKRunner(
            api_key="test-key",
            model="claude-sonnet-4",
            temperature=0.7,
            notebook_id="nb-123"
        )

        await runner.generate(
            topic="测试",
            search_results=[],
            system_prompt="提示",
            max_turns=5
        )

        # 验证tools被传递
        call_kwargs = mock_query.call_args[1]
        assert "options" in call_kwargs
        assert hasattr(call_kwargs["options"], "tools")
        assert len(call_kwargs["options"].tools) > 0

    @pytest.mark.asyncio
    @patch('src.modules.agent_sdk.query')
    async def test_generate_accumulates_text_from_multiple_messages(self, mock_query):
        """测试从多个消息累积文本"""
        # Mock多个消息返回
        mock_msg1 = MagicMock()
        mock_msg1.text = "第一部分"
        mock_msg1.stop_reason = None

        mock_msg2 = MagicMock()
        mock_msg2.text = "第二部分"
        mock_msg2.stop_reason = "end_turn"

        mock_query.return_value = async_iterator([mock_msg1, mock_msg2])

        runner = AgentSDKRunner(
            api_key="test-key",
            model="claude-sonnet-4",
            temperature=0.7
        )

        result_text, metrics = await runner.generate(
            topic="测试",
            search_results=[],
            system_prompt="提示",
            max_turns=5
        )

        # 验证文本被累积
        assert "第一部分" in result_text
        assert "第二部分" in result_text

    @pytest.mark.asyncio
    @patch('src.modules.agent_sdk.query')
    async def test_generate_returns_metrics(self, mock_query):
        """测试返回完整的metrics"""
        mock_message = MagicMock()
        mock_message.text = "内容"
        mock_message.stop_reason = "end_turn"
        mock_query.return_value = async_iterator([mock_message])

        runner = AgentSDKRunner(
            api_key="test-key",
            model="claude-sonnet-4",
            temperature=0.7
        )

        result_text, metrics = await runner.generate(
            topic="测试",
            search_results=[],
            system_prompt="提示",
            max_turns=5
        )

        # 验证metrics包含必需字段
        assert isinstance(metrics, AgentRunMetrics)
        assert metrics.start_time > 0
        assert metrics.end_time is not None
        assert metrics.end_time >= metrics.start_time
