"""
测试端到端流水线
改造自 test_e2e.py
"""
import pytest
from unittest.mock import patch, MagicMock
from src.main import run_pipeline
from src.models import Article, SearchResult, PipelineResult


class TestPipeline:
    """测试 run_pipeline 函数"""

    @patch('src.modules.generator.Anthropic')
    @patch('src.modules.retrieval.subprocess.run')
    @patch('src.modules.retrieval.Path')
    def test_pipeline_basic_flow(self, mock_path, mock_subprocess, mock_anthropic_class):
        """测试基本流水线流程（P0）"""
        # Mock NotebookLM skill 存在
        mock_path.home.return_value.__truediv__.return_value.exists.return_value = True

        # Mock 检索结果
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout="Question: test\n==========\n这是检索结果\n==========",
            stderr=""
        )

        # Mock Anthropic API 响应
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # 模拟生成完成
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_content_block = MagicMock()
        mock_content_block.text = "# 测试文章\n\n这是文章内容"
        mock_response.content = [mock_content_block]
        mock_client.messages.create.return_value = mock_response

        # 执行流水线
        result = run_pipeline(
            topic="测试选题",
            api_key="test-api-key",
            enable_feishu=False
        )

        # 验证结果
        assert isinstance(result, PipelineResult)
        assert isinstance(result.article, Article)
        assert result.article.title == "测试文章"
        assert "这是文章内容" in result.article.content
        assert result.doc_result is None
        assert result.record_id is None

    @patch('src.modules.generator.Anthropic')
    @patch('src.modules.retrieval.subprocess.run')
    @patch('src.modules.retrieval.Path')
    def test_pipeline_with_empty_search_results(self, mock_path, mock_subprocess, mock_anthropic_class):
        """测试检索无结果时流水线仍然运行（P0）"""
        mock_path.home.return_value.__truediv__.return_value.exists.return_value = True

        # Mock 检索无结果
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout="Question: test\n==========\n==========",  # 空结果
            stderr=""
        )

        # Mock 生成
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_content_block = MagicMock()
        mock_content_block.text = "# 文章标题\n\n文章内容"
        mock_response.content = [mock_content_block]
        mock_client.messages.create.return_value = mock_response

        # 执行流水线
        result = run_pipeline(
            topic="测试选题",
            api_key="test-api-key",
            enable_feishu=False
        )

        # 验证结果
        assert isinstance(result, PipelineResult)
        assert isinstance(result.article, Article)
        # 检查 source_summary 标注无检索结果
        assert "无检索结果" in result.article.source_summary or "0" in result.article.source_summary

    def test_pipeline_raises_value_error_without_api_key(self):
        """测试缺少 API Key 时抛出异常"""
        with pytest.raises(ValueError, match="API Key"):
            run_pipeline(
                topic="测试选题",
                api_key="",  # 空 API Key
                enable_feishu=False
            )

    @patch('src.modules.feishu_doc.create_doc')
    @patch('src.modules.generator.Anthropic')
    @patch('src.modules.retrieval.subprocess.run')
    @patch('src.modules.retrieval.Path')
    def test_pipeline_with_feishu_not_implemented(
        self, mock_path, mock_subprocess, mock_anthropic_class, mock_create_doc
    ):
        """测试启用飞书但功能未实现时的处理"""
        mock_path.home.return_value.__truediv__.return_value.exists.return_value = True
        mock_subprocess.return_value = MagicMock(
            returncode=0,
            stdout="Question: test\n==========\n结果\n==========",
            stderr=""
        )

        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_content_block = MagicMock()
        mock_content_block.text = "# 标题\n\n内容"
        mock_response.content = [mock_content_block]
        mock_client.messages.create.return_value = mock_response

        # Mock 飞书抛出 NotImplementedError
        mock_create_doc.side_effect = NotImplementedError("功能未实现")

        # 执行流水线（不应该抛出异常）
        result = run_pipeline(
            topic="测试选题",
            api_key="test-api-key",
            enable_feishu=True,
            folder_token="test-folder"
        )

        # 验证结果
        assert isinstance(result, PipelineResult)
        assert result.doc_result is None  # 飞书功能未实现
        assert result.record_id is None
