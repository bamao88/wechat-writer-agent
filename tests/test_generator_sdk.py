"""测试generator.py的SDK集成函数"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.modules import generator
from src.modules.agent_sdk import AgentRunMetrics
from src.models import SearchResult, Article


class TestGenerateWithSDK:
    """测试generate_with_sdk函数"""

    @pytest.mark.asyncio
    @patch('src.modules.generator.AgentSDKRunner')
    async def test_generate_with_sdk_basic(self, mock_runner_class):
        """测试基本的SDK生成流程"""
        # Mock AgentSDKRunner实例
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        # Mock generate方法返回
        article_text = """# 测试标题

这是文章内容。"""

        metrics = AgentRunMetrics()
        metrics.end_time = metrics.start_time + 10
        metrics.total_tokens = 1000
        metrics.tool_calls = [{'tool_name': 'test'}]

        mock_runner.generate = AsyncMock(return_value=(article_text, metrics))

        # 调用函数
        article, metrics_dict = await generator.generate_with_sdk(
            topic="测试选题",
            search_results=[],
            api_key="test-key",
            model="claude-sonnet-4"
        )

        # 验证返回值
        assert isinstance(article, Article)
        assert article.title == "测试标题"
        assert "文章内容" in article.content

        assert isinstance(metrics_dict, dict)
        assert 'runtime_seconds' in metrics_dict
        assert 'tool_call_count' in metrics_dict
        assert 'total_tokens' in metrics_dict
        assert 'log_markdown' in metrics_dict

    @pytest.mark.asyncio
    @patch('src.modules.generator.AgentSDKRunner')
    async def test_generate_with_sdk_creates_runner_with_correct_params(self, mock_runner_class):
        """测试使用正确参数创建runner"""
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        article_text = "# 标题\n内容"
        metrics = AgentRunMetrics()
        mock_runner.generate = AsyncMock(return_value=(article_text, metrics))

        await generator.generate_with_sdk(
            topic="测试",
            search_results=[],
            api_key="my-api-key",
            model="claude-opus-4",
            temperature=0.8,
            notebook_id="nb-123",
            notebook_url="https://notebook.url",
            max_turns=15
        )

        # 验证AgentSDKRunner初始化参数
        mock_runner_class.assert_called_once_with(
            api_key="my-api-key",
            model="claude-opus-4",
            temperature=0.8,
            notebook_id="nb-123",
            notebook_url="https://notebook.url"
        )

        # 验证generate调用参数
        mock_runner.generate.assert_called_once()
        call_kwargs = mock_runner.generate.call_args[1]
        assert call_kwargs['topic'] == "测试"
        assert call_kwargs['max_turns'] == 15

    @pytest.mark.asyncio
    @patch('src.modules.generator.AgentSDKRunner')
    async def test_generate_with_sdk_includes_search_results(self, mock_runner_class):
        """测试传递搜索结果"""
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        article_text = "# 标题\n内容"
        metrics = AgentRunMetrics()
        mock_runner.generate = AsyncMock(return_value=(article_text, metrics))

        search_results = [
            SearchResult(content="素材1", source="来源1"),
            SearchResult(content="素材2", source="来源2")
        ]

        await generator.generate_with_sdk(
            topic="测试",
            search_results=search_results,
            api_key="key"
        )

        # 验证search_results被传递
        call_kwargs = mock_runner.generate.call_args[1]
        assert call_kwargs['search_results'] == search_results
        assert len(call_kwargs['search_results']) == 2

    @pytest.mark.asyncio
    @patch('src.modules.generator.LogDocumentGenerator')
    @patch('src.modules.generator.AgentSDKRunner')
    async def test_generate_with_sdk_generates_log_document(
        self,
        mock_runner_class,
        mock_log_gen_class
    ):
        """测试生成日志文档"""
        # Mock runner
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        article_text = "# 标题\n内容"
        metrics = AgentRunMetrics()
        mock_runner.generate = AsyncMock(return_value=(article_text, metrics))

        # Mock log generator
        mock_log_gen = MagicMock()
        mock_log_gen_class.return_value = mock_log_gen
        mock_log_gen.generate_markdown.return_value = "# Log Document\n..."

        # 调用
        article, metrics_dict = await generator.generate_with_sdk(
            topic="测试选题",
            search_results=[],
            api_key="key"
        )

        # 验证LogDocumentGenerator被调用
        mock_log_gen_class.assert_called_once_with("测试选题", metrics)
        mock_log_gen.generate_markdown.assert_called_once()

        # 验证log_markdown在返回值中
        assert metrics_dict['log_markdown'] == "# Log Document\n..."

    @pytest.mark.asyncio
    @patch('src.modules.generator.AgentSDKRunner')
    async def test_generate_with_sdk_metrics_dict_structure(self, mock_runner_class):
        """测试metrics_dict包含所有必需字段"""
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        article_text = "# 标题\n内容"
        metrics = AgentRunMetrics()
        metrics.end_time = metrics.start_time + 45.5
        metrics.total_tokens = 2500
        metrics.prompt_tokens = 1000
        metrics.completion_tokens = 1500
        metrics.tool_calls = [
            {'tool_name': 'tool1'},
            {'tool_name': 'tool2'},
            {'tool_name': 'tool3'}
        ]

        mock_runner.generate = AsyncMock(return_value=(article_text, metrics))

        article, metrics_dict = await generator.generate_with_sdk(
            topic="测试",
            search_results=[],
            api_key="key"
        )

        # 验证所有必需字段存在
        assert 'runtime_seconds' in metrics_dict
        assert 'tool_call_count' in metrics_dict
        assert 'total_tokens' in metrics_dict
        assert 'prompt_tokens' in metrics_dict
        assert 'completion_tokens' in metrics_dict
        assert 'log_markdown' in metrics_dict

        # 验证值正确
        assert metrics_dict['runtime_seconds'] == pytest.approx(45.5, rel=0.1)
        assert metrics_dict['tool_call_count'] == 3
        assert metrics_dict['total_tokens'] == 2500
        assert metrics_dict['prompt_tokens'] == 1000
        assert metrics_dict['completion_tokens'] == 1500

    @pytest.mark.asyncio
    @patch('src.modules.generator.AgentSDKRunner')
    async def test_generate_with_sdk_parses_article_correctly(self, mock_runner_class):
        """测试正确解析文章"""
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        article_text = """# 这是文章标题

这是第一段内容。

这是第二段内容。"""

        metrics = AgentRunMetrics()
        mock_runner.generate = AsyncMock(return_value=(article_text, metrics))

        search_results = [SearchResult(content="素材", source="来源A")]

        article, metrics_dict = await generator.generate_with_sdk(
            topic="测试选题",
            search_results=search_results,
            api_key="key"
        )

        # 验证文章解析
        assert article.title == "这是文章标题"
        assert "这是第一段内容" in article.content
        assert "这是第二段内容" in article.content
        assert "来源A" in article.source_summary

    @pytest.mark.asyncio
    @patch('src.modules.generator.AgentSDKRunner')
    async def test_generate_with_sdk_default_parameters(self, mock_runner_class):
        """测试默认参数"""
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        article_text = "# 标题\n内容"
        metrics = AgentRunMetrics()
        mock_runner.generate = AsyncMock(return_value=(article_text, metrics))

        # 仅使用必需参数
        await generator.generate_with_sdk(
            topic="测试",
            search_results=[],
            api_key="key"
        )

        # 验证默认值
        init_kwargs = mock_runner_class.call_args[1]
        assert init_kwargs['model'] == "MiniMax-M2.1"
        assert init_kwargs['temperature'] == 0.7
        assert init_kwargs['notebook_id'] is None
        assert init_kwargs['notebook_url'] is None

        gen_kwargs = mock_runner.generate.call_args[1]
        assert gen_kwargs['max_turns'] == 10

    @pytest.mark.asyncio
    async def test_generate_with_sdk_validates_api_key(self):
        """测试验证API key"""
        with pytest.raises(ValueError, match="请提供 ANTHROPIC_API_KEY"):
            await generator.generate_with_sdk(
                topic="测试",
                search_results=[],
                api_key=""
            )

    @pytest.mark.asyncio
    @patch('src.modules.generator.validate_temperature')
    @patch('src.modules.generator.AgentSDKRunner')
    async def test_generate_with_sdk_validates_temperature(
        self,
        mock_runner_class,
        mock_validate_temp
    ):
        """测试验证temperature参数"""
        mock_runner = MagicMock()
        mock_runner_class.return_value = mock_runner

        article_text = "# 标题\n内容"
        metrics = AgentRunMetrics()
        mock_runner.generate = AsyncMock(return_value=(article_text, metrics))

        mock_validate_temp.return_value = 0.8

        await generator.generate_with_sdk(
            topic="测试",
            search_results=[],
            api_key="key",
            temperature=0.8
        )

        # 验证调用了validate_temperature
        mock_validate_temp.assert_called_once_with(0.8)
