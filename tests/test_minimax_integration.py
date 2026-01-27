"""MiniMax API 集成测试"""
import pytest
import os
from unittest.mock import patch
from writer_agent import WechatWriterAgent
from src.modules import generator
from src.models import SearchResult


@pytest.mark.integration
class TestMiniMaxIntegration:
    """MiniMax 集成测试（需要真实 API Key）"""

    @pytest.mark.skipif(
        not os.getenv("MiniMax_API_KEY"),
        reason="需要 MiniMax_API_KEY 环境变量"
    )
    def test_generator_with_real_minimax_api(self):
        """测试 generator 使用真实 MiniMax API"""
        api_key = os.getenv("MiniMax_API_KEY")

        # 临时设置 MiniMax base_url
        with patch.dict(os.environ, {
            'ANTHROPIC_BASE_URL': 'https://api.minimaxi.com/anthropic'
        }):
            # Mock NotebookLM（避免真实调用）
            with patch('src.modules.retrieval.search') as mock_search:
                mock_search.return_value = [
                    SearchResult(content="测试素材内容", source="")
                ]

                # 调用生成
                article = generator.generate(
                    topic="人工智能的应用",
                    search_results=[SearchResult(content="AI相关内容", source="")],
                    api_key=api_key,
                    model="MiniMax-M2.1",
                    max_turns=3,
                    temperature=0.7
                )

                # 验证
                assert article is not None
                assert article.title
                assert len(article.content) > 100

    @pytest.mark.skipif(
        not os.getenv("MiniMax_API_KEY"),
        reason="需要 MiniMax_API_KEY 环境变量"
    )
    def test_agent_with_real_minimax_api(self):
        """测试 Agent 使用真实 MiniMax API"""
        api_key = os.getenv("MiniMax_API_KEY")

        # 临时设置环境
        with patch.dict(os.environ, {
            'ANTHROPIC_API_KEY': api_key,
            'ANTHROPIC_BASE_URL': 'https://api.minimaxi.com/anthropic'
        }):
            # Mock NotebookLM
            with patch('notebooklm_tool.subprocess.run') as mock_nb:
                mock_nb.return_value.returncode = 0
                mock_nb.return_value.stdout = "Question: test\n==========\nAI测试内容\n=========="

                agent = WechatWriterAgent(model="MiniMax-M2.1")
                article = agent.write_article(
                    topic="测试MiniMax集成",
                    max_turns=3
                )

                # 验证
                assert article is not None
                assert len(article) > 50

    @pytest.mark.skipif(
        not os.getenv("MiniMax_API_KEY"),
        reason="需要 MiniMax_API_KEY 环境变量"
    )
    def test_tool_calling_with_minimax(self):
        """测试 MiniMax tool calling 功能"""
        api_key = os.getenv("MiniMax_API_KEY")

        with patch.dict(os.environ, {
            'ANTHROPIC_API_KEY': api_key,
            'ANTHROPIC_BASE_URL': 'https://api.minimaxi.com/anthropic'
        }):
            # Mock NotebookLM 返回特定内容
            with patch('notebooklm_tool.subprocess.run') as mock_nb:
                mock_nb.return_value.returncode = 0
                mock_nb.return_value.stdout = "Question: test\n==========\n特定标记内容:TOOL_CALLED\n=========="

                agent = WechatWriterAgent(model="MiniMax-M2.1")
                article = agent.write_article(
                    topic="需要查询知识库的主题",
                    max_turns=5
                )

                # 验证 tool 被调用（通过检查特定标记或 mock 调用）
                assert "TOOL_CALLED" in article or mock_nb.called
