"""
测试检索模块
改造自 test_notebooklm_tool.py
"""
import pytest
from unittest.mock import patch, MagicMock
from src.modules import retrieval
from src.models import SearchResult


class TestRetrievalSearch:
    """测试 retrieval.search 函数"""

    @patch('src.modules.retrieval.subprocess.run')
    @patch('src.modules.retrieval.Path')
    def test_search_returns_list_of_search_results(self, mock_path, mock_run):
        """测试 search 返回 SearchResult 列表"""
        # Mock skill 目录存在
        mock_path.home.return_value.__truediv__.return_value.exists.return_value = True

        # Mock subprocess 返回成功结果
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Question: test\n==========\n这是检索结果\n==========",
            stderr=""
        )

        results = retrieval.search("测试查询")

        assert isinstance(results, list)
        assert len(results) > 0
        assert isinstance(results[0], SearchResult)
        assert results[0].content == "这是检索结果"
        assert results[0].source == ""  # NotebookLM 不提供来源

    @patch('src.modules.retrieval.subprocess.run')
    @patch('src.modules.retrieval.Path')
    def test_search_with_notebook_id(self, mock_path, mock_run):
        """测试使用 notebook_id 检索"""
        mock_path.home.return_value.__truediv__.return_value.exists.return_value = True
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Question: test\n==========\n结果\n==========",
            stderr=""
        )

        results = retrieval.search("查询", notebook_id="nb123")

        # 验证调用参数包含 notebook_id
        call_args = mock_run.call_args[0][0]
        assert "--notebook-id" in call_args
        assert "nb123" in call_args

    @patch('src.modules.retrieval.subprocess.run')
    @patch('src.modules.retrieval.Path')
    def test_search_with_notebook_url(self, mock_path, mock_run):
        """测试使用 notebook_url 检索"""
        mock_path.home.return_value.__truediv__.return_value.exists.return_value = True
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Question: test\n==========\n结果\n==========",
            stderr=""
        )

        results = retrieval.search("查询", notebook_url="https://example.com/nb")

        # 验证调用参数包含 notebook_url
        call_args = mock_run.call_args[0][0]
        assert "--notebook-url" in call_args
        assert "https://example.com/nb" in call_args

    @patch('src.modules.retrieval.Path')
    def test_search_raises_value_error_when_skill_not_installed(self, mock_path):
        """测试 skill 未安装时抛出 ValueError"""
        mock_path.home.return_value.__truediv__.return_value.exists.return_value = False

        with pytest.raises(ValueError, match="NotebookLM skill 未安装"):
            retrieval.search("查询")

    @patch('src.modules.retrieval.subprocess.run')
    @patch('src.modules.retrieval.Path')
    def test_search_raises_runtime_error_on_auth_failure(self, mock_path, mock_run):
        """测试认证失败时抛出 RuntimeError"""
        mock_path.home.return_value.__truediv__.return_value.exists.return_value = True
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Not authenticated"
        )

        with pytest.raises(RuntimeError, match="未认证"):
            retrieval.search("查询")

    @patch('src.modules.retrieval.subprocess.run')
    @patch('src.modules.retrieval.Path')
    def test_search_raises_timeout_error(self, mock_path, mock_run):
        """测试超时时抛出 TimeoutError"""
        mock_path.home.return_value.__truediv__.return_value.exists.return_value = True
        mock_run.side_effect = Exception("Timeout")

        # 模拟 subprocess.TimeoutExpired
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=180)

        with pytest.raises(TimeoutError, match="查询超时"):
            retrieval.search("查询")

    @patch('src.modules.retrieval.subprocess.run')
    @patch('src.modules.retrieval.Path')
    def test_search_returns_empty_list_when_no_result(self, mock_path, mock_run):
        """测试无结果时返回空列表"""
        mock_path.home.return_value.__truediv__.return_value.exists.return_value = True
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Question: test\n==========\n==========",  # 空结果
            stderr=""
        )

        results = retrieval.search("不存在的查询")

        assert isinstance(results, list)
        assert len(results) == 0
