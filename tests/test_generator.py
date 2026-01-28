"""测试生成模块"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from src.modules import generator
from src.models import SearchResult, Article


class TestGenerator:
    """测试 generator.generate 函数"""

    @patch('src.modules.generator.Anthropic')
    def test_generate_basic_flow(self, mock_anthropic_class):
        """测试基本生成流程"""
        # Mock Anthropic client
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # Mock API 响应
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"

        # Mock content block with text
        mock_content_block = MagicMock()
        mock_content_block.text = "# 测试文章标题\n\n这是文章的正文内容。"
        mock_response.content = [mock_content_block]

        mock_client.messages.create.return_value = mock_response

        # 执行
        search_results = [SearchResult(content="测试素材内容", source="测试来源")]
        article = generator.generate(
            topic="测试选题",
            search_results=search_results,
            api_key="test-key"
        )

        # 验证
        assert isinstance(article, Article)
        assert article.title == "测试文章标题"
        assert "文章的正文内容" in article.content
        assert "1 条检索结果" in article.source_summary
        assert "测试来源" in article.source_summary

    @patch('src.modules.generator.retrieval.search')
    @patch('src.modules.generator.Anthropic')
    def test_generate_with_tool_use(self, mock_anthropic_class, mock_search):
        """测试工具调用流程"""
        # Mock Anthropic client
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # 第一次响应：tool_use
        mock_tool_use_response = MagicMock()
        mock_tool_use_response.stop_reason = "tool_use"

        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "query_notebooklm"
        mock_tool_block.input = {"question": "测试问题"}
        mock_tool_block.id = "tool123"

        mock_tool_use_response.content = [mock_tool_block]

        # 第二次响应：end_turn with article
        mock_end_response = MagicMock()
        mock_end_response.stop_reason = "end_turn"

        mock_text_block = MagicMock()
        mock_text_block.text = "# 完整文章\n\n基于检索结果的内容。"
        mock_end_response.content = [mock_text_block]

        # 设置 messages.create 返回值序列
        mock_client.messages.create.side_effect = [
            mock_tool_use_response,
            mock_end_response
        ]

        # Mock retrieval.search
        mock_search.return_value = [SearchResult(content="追加检索内容", source="")]

        # 执行
        search_results = [SearchResult(content="初始素材", source="")]
        article = generator.generate(
            topic="测试选题",
            search_results=search_results,
            api_key="test-key",
            notebook_id="notebook123"
        )

        # 验证
        assert isinstance(article, Article)
        assert article.title == "完整文章"

        # 验证调用了 retrieval.search
        mock_search.assert_called_once_with(
            "测试问题",
            notebook_id="notebook123",
            notebook_url=None
        )

        # 验证 API 被调用了两次
        assert mock_client.messages.create.call_count == 2

    def test_generate_raises_value_error_without_api_key(self):
        """测试缺少 API Key 时抛出异常"""
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            generator.generate(
                topic="测试",
                search_results=[],
                api_key=""
            )

    @patch('src.modules.generator.Anthropic')
    def test_generate_with_empty_search_results(self, mock_anthropic_class):
        """测试空检索结果时仍能生成文章"""
        # Mock Anthropic client
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # Mock API 响应
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"

        mock_content_block = MagicMock()
        mock_content_block.text = "# 基于理解的文章\n\n没有素材也能写。"
        mock_response.content = [mock_content_block]

        mock_client.messages.create.return_value = mock_response

        # 执行（空的 search_results）
        article = generator.generate(
            topic="测试选题",
            search_results=[],
            api_key="test-key"
        )

        # 验证
        assert isinstance(article, Article)
        assert "无检索结果" in article.source_summary or "AI 理解" in article.source_summary

    @patch('src.modules.generator.Anthropic')
    def test_generate_extracts_title_from_markdown(self, mock_anthropic_class):
        """测试正确提取 Markdown 标题"""
        # Mock Anthropic client
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # Mock API 响应
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"

        mock_content_block = MagicMock()
        mock_content_block.text = """# 这是标题

这是第一段。

## 这是二级标题

这是第二段。"""
        mock_response.content = [mock_content_block]

        mock_client.messages.create.return_value = mock_response

        # 执行
        article = generator.generate(
            topic="测试选题",
            search_results=[],
            api_key="test-key"
        )

        # 验证标题提取
        assert article.title == "这是标题"
        assert "# 这是标题" in article.content

    @patch('src.modules.generator.Anthropic')
    def test_generate_handles_no_title_in_markdown(self, mock_anthropic_class):
        """测试无标题时使用 topic 作为标题"""
        # Mock Anthropic client
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # Mock API 响应（无 # 标题）
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"

        mock_content_block = MagicMock()
        mock_content_block.text = "这是没有标题的正文内容。"
        mock_response.content = [mock_content_block]

        mock_client.messages.create.return_value = mock_response

        # 执行
        article = generator.generate(
            topic="默认标题",
            search_results=[],
            api_key="test-key"
        )

        # 验证使用 topic 作为标题
        assert article.title == "默认标题"
        assert "# 默认标题" in article.content

    @patch('src.modules.generator.Anthropic')
    def test_generate_max_turns_exceeded(self, mock_anthropic_class):
        """测试达到最大轮次时抛出异常"""
        # Mock Anthropic client
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # Mock API 始终返回 tool_use（永远不结束）
        mock_response = MagicMock()
        mock_response.stop_reason = "tool_use"

        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "query_notebooklm"
        mock_tool_block.input = {"question": "测试"}
        mock_tool_block.id = "tool123"

        mock_response.content = [mock_tool_block]

        mock_client.messages.create.return_value = mock_response

        # Mock retrieval
        with patch('src.modules.generator.retrieval.search') as mock_search:
            mock_search.return_value = [SearchResult(content="内容", source="")]

            # 执行并期望异常
            with pytest.raises(RuntimeError, match="最大轮次"):
                generator.generate(
                    topic="测试",
                    search_results=[],
                    api_key="test-key",
                    max_turns=2  # 设置较小的 max_turns
                )

    @patch('src.modules.generator.retrieval.search')
    @patch('src.modules.generator.Anthropic')
    def test_generate_with_notebook_parameters(self, mock_anthropic_class, mock_search):
        """测试 notebook_id 和 notebook_url 参数传递"""
        # Mock Anthropic client
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # 第一次响应：tool_use
        mock_tool_use_response = MagicMock()
        mock_tool_use_response.stop_reason = "tool_use"

        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "query_notebooklm"
        mock_tool_block.input = {"question": "测试问题"}
        mock_tool_block.id = "tool123"

        mock_tool_use_response.content = [mock_tool_block]

        # 第二次响应：end_turn
        mock_end_response = MagicMock()
        mock_end_response.stop_reason = "end_turn"

        mock_text_block = MagicMock()
        mock_text_block.text = "# 文章\n\n内容"
        mock_end_response.content = [mock_text_block]

        mock_client.messages.create.side_effect = [
            mock_tool_use_response,
            mock_end_response
        ]

        # Mock search
        mock_search.return_value = [SearchResult(content="内容", source="")]

        # 执行（提供 notebook_url）
        generator.generate(
            topic="测试",
            search_results=[],
            api_key="test-key",
            notebook_url="https://notebooklm.google.com/notebook/test"
        )

        # 验证 notebook_url 被传递
        mock_search.assert_called_once_with(
            "测试问题",
            notebook_id=None,
            notebook_url="https://notebooklm.google.com/notebook/test"
        )

    @patch('src.modules.generator.retrieval.search')
    @patch('src.modules.generator.Anthropic')
    def test_generate_handles_tool_call_error(self, mock_anthropic_class, mock_search):
        """测试工具调用失败时的错误处理"""
        # Mock Anthropic client
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # 第一次响应：tool_use
        mock_tool_use_response = MagicMock()
        mock_tool_use_response.stop_reason = "tool_use"

        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "query_notebooklm"
        mock_tool_block.input = {"question": "测试问题"}
        mock_tool_block.id = "tool123"

        mock_tool_use_response.content = [mock_tool_block]

        # 第二次响应：end_turn
        mock_end_response = MagicMock()
        mock_end_response.stop_reason = "end_turn"

        mock_text_block = MagicMock()
        mock_text_block.text = "# 文章\n\n即使检索失败也能继续。"
        mock_end_response.content = [mock_text_block]

        mock_client.messages.create.side_effect = [
            mock_tool_use_response,
            mock_end_response
        ]

        # Mock search 抛出异常
        mock_search.side_effect = RuntimeError("检索服务不可用")

        # 执行（应该捕获异常并继续）
        article = generator.generate(
            topic="测试",
            search_results=[],
            api_key="test-key"
        )

        # 验证文章仍然生成
        assert isinstance(article, Article)
        assert article.title == "文章"

    @patch('src.modules.generator.Anthropic')
    def test_generate_with_multiple_sources(self, mock_anthropic_class):
        """测试多个来源的素材摘要"""
        # Mock Anthropic client
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # Mock API 响应
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"

        mock_content_block = MagicMock()
        mock_content_block.text = "# 文章\n\n内容"
        mock_response.content = [mock_content_block]

        mock_client.messages.create.return_value = mock_response

        # 执行（多个有来源的检索结果）
        search_results = [
            SearchResult(content="内容1", source="来源A"),
            SearchResult(content="内容2", source="来源B"),
            SearchResult(content="内容3", source="来源C"),
            SearchResult(content="内容4", source="来源D"),
        ]
        article = generator.generate(
            topic="测试",
            search_results=search_results,
            api_key="test-key"
        )

        # 验证素材摘要包含来源信息
        assert "4 条检索结果" in article.source_summary
        assert "来源A" in article.source_summary
        assert "来源B" in article.source_summary
        assert "来源C" in article.source_summary
        # 应该有 "等" 因为只显示前3个
        assert " 等" in article.source_summary

    @patch('src.modules.generator.Anthropic')
    def test_generate_handles_empty_response(self, mock_anthropic_class):
        """测试空响应时抛出异常"""
        # Mock Anthropic client
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # Mock API 返回空内容
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = []

        mock_client.messages.create.return_value = mock_response

        # 执行并期望异常
        with pytest.raises(RuntimeError, match="为空"):
            generator.generate(
                topic="测试",
                search_results=[],
                api_key="test-key"
            )

    @patch('src.modules.generator.retrieval.search')
    @patch('src.modules.generator.Anthropic')
    def test_generate_with_empty_tool_result(self, mock_anthropic_class, mock_search):
        """测试工具调用返回空结果时的处理"""
        # Mock Anthropic client
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # 第一次响应：tool_use
        mock_tool_use_response = MagicMock()
        mock_tool_use_response.stop_reason = "tool_use"

        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "query_notebooklm"
        mock_tool_block.input = {"question": "测试问题"}
        mock_tool_block.id = "tool123"

        mock_tool_use_response.content = [mock_tool_block]

        # 第二次响应：end_turn
        mock_end_response = MagicMock()
        mock_end_response.stop_reason = "end_turn"

        mock_text_block = MagicMock()
        mock_text_block.text = "# 文章\n\n即使检索为空也能继续。"
        mock_end_response.content = [mock_text_block]

        mock_client.messages.create.side_effect = [
            mock_tool_use_response,
            mock_end_response
        ]

        # Mock search 返回空列表
        mock_search.return_value = []

        # 执行
        article = generator.generate(
            topic="测试",
            search_results=[],
            api_key="test-key"
        )

        # 验证文章生成成功，工具结果应为 "未找到相关内容"
        assert isinstance(article, Article)
        assert article.title == "文章"

    @patch('src.modules.generator.Anthropic')
    def test_generate_with_custom_model(self, mock_anthropic_class):
        """测试使用自定义模型参数"""
        # Mock Anthropic client
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # Mock API 响应
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"

        mock_content_block = MagicMock()
        mock_content_block.text = "# 文章\n\n内容"
        mock_response.content = [mock_content_block]

        mock_client.messages.create.return_value = mock_response

        # 执行（使用自定义模型）
        generator.generate(
            topic="测试",
            search_results=[],
            api_key="test-key",
            model="claude-3-opus-20240229"
        )

        # 验证 model 参数传递正确
        call_args = mock_client.messages.create.call_args
        assert call_args[1]['model'] == "claude-3-opus-20240229"

    @patch('src.modules.generator.Anthropic')
    def test_generate_with_multiple_text_blocks(self, mock_anthropic_class):
        """测试响应包含多个文本块的情况"""
        # Mock Anthropic client
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # Mock API 响应包含多个文本块
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"

        mock_block1 = MagicMock()
        mock_block1.text = "# 文章标题\n\n"

        mock_block2 = MagicMock()
        mock_block2.text = "这是第一部分。\n\n"

        mock_block3 = MagicMock()
        mock_block3.text = "这是第二部分。"

        mock_response.content = [mock_block1, mock_block2, mock_block3]

        mock_client.messages.create.return_value = mock_response

        # 执行
        article = generator.generate(
            topic="测试",
            search_results=[],
            api_key="test-key"
        )

        # 验证所有文本块都被合并
        assert article.title == "文章标题"
        assert "第一部分" in article.content
        assert "第二部分" in article.content

    @patch('src.modules.generator.Anthropic')
    def test_generate_with_unexpected_stop_reason_and_content(self, mock_anthropic_class):
        """测试其他停止原因但有内容的情况"""
        # Mock Anthropic client
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # Mock API 返回其他停止原因
        mock_response = MagicMock()
        mock_response.stop_reason = "max_tokens"

        mock_content_block = MagicMock()
        mock_content_block.text = "# 文章\n\n内容被截断了"
        mock_response.content = [mock_content_block]

        mock_client.messages.create.return_value = mock_response

        # 执行（应该仍然能生成文章）
        article = generator.generate(
            topic="测试",
            search_results=[],
            api_key="test-key"
        )

        # 验证文章生成
        assert isinstance(article, Article)
        assert article.title == "文章"

    @patch('src.modules.generator.Anthropic')
    def test_generate_with_unexpected_stop_reason_without_content(self, mock_anthropic_class):
        """测试其他停止原因且无内容的情况"""
        # Mock Anthropic client
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # Mock API 返回其他停止原因且无内容
        mock_response = MagicMock()
        mock_response.stop_reason = "stop_sequence"
        mock_response.content = []

        mock_client.messages.create.return_value = mock_response

        # 执行并期望异常
        with pytest.raises(RuntimeError, match="意外的停止原因"):
            generator.generate(
                topic="测试",
                search_results=[],
                api_key="test-key"
            )

    @patch('src.modules.generator.Anthropic')
    def test_generate_api_error_retry(self, mock_anthropic_class):
        """测试 API 调用失败后的重试逻辑"""
        # Mock Anthropic client
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # 第一次调用失败
        # 第二次调用成功
        mock_success_response = MagicMock()
        mock_success_response.stop_reason = "end_turn"

        mock_content_block = MagicMock()
        mock_content_block.text = "# 重试后的文章\n\n成功生成。"
        mock_success_response.content = [mock_content_block]

        mock_client.messages.create.side_effect = [
            Exception("网络错误"),
            mock_success_response
        ]

        # 执行（第一次失败，第二次成功）
        article = generator.generate(
            topic="测试",
            search_results=[],
            api_key="test-key",
            max_turns=3
        )

        # 验证最终成功生成
        assert isinstance(article, Article)
        assert article.title == "重试后的文章"
        # 验证调用了两次
        assert mock_client.messages.create.call_count == 2

    @patch('src.modules.generator.Anthropic')
    def test_generate_api_error_max_turns_reached(self, mock_anthropic_class):
        """测试 API 持续失败直到达到最大轮次"""
        # Mock Anthropic client
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # 所有调用都失败
        mock_client.messages.create.side_effect = Exception("持续失败")

        # 执行并期望异常
        with pytest.raises(RuntimeError, match="生成失败"):
            generator.generate(
                topic="测试",
                search_results=[],
                api_key="test-key",
                max_turns=2
            )

        # 验证尝试了 max_turns 次
        assert mock_client.messages.create.call_count == 2


class TestHelperFunctions:
    """测试辅助函数"""

    def test_get_system_prompt(self):
        """测试获取系统提示词"""
        prompt = generator._get_system_prompt()

        assert isinstance(prompt, str)
        assert len(prompt) > 100
        assert "公众号" in prompt or "文章" in prompt

    def test_build_user_message_with_results(self):
        """测试构建包含检索结果的用户消息"""
        search_results = [
            SearchResult(content="内容1", source="来源1"),
            SearchResult(content="内容2", source="")
        ]

        message = generator._build_user_message("测试选题", search_results)

        assert "测试选题" in message
        assert "内容1" in message
        assert "内容2" in message
        assert "来源1" in message

    def test_build_user_message_without_results(self):
        """测试构建无检索结果的用户消息"""
        message = generator._build_user_message("测试选题", [])

        assert "测试选题" in message
        assert "未检索到" in message or "无" in message

    def test_parse_article_with_title(self):
        """测试解析包含标题的文章"""
        text = "# 文章标题\n\n这是正文。"
        search_results = [SearchResult(content="素材", source="来源A")]

        article = generator._parse_article(text, "原始选题", search_results)

        assert article.title == "文章标题"
        assert "# 文章标题" in article.content
        assert "1 条检索结果" in article.source_summary

    def test_parse_article_without_title(self):
        """测试解析无标题的文章"""
        text = "这是没有标题的正文。"
        search_results = []

        article = generator._parse_article(text, "默认标题", search_results)

        assert article.title == "默认标题"
        assert "# 默认标题" in article.content
        assert "无检索结果" in article.source_summary

    def test_parse_article_with_no_sources(self):
        """测试解析时所有检索结果都没有来源"""
        text = "# 文章标题\n\n正文内容"
        search_results = [
            SearchResult(content="内容1", source=""),
            SearchResult(content="内容2", source=""),
        ]

        article = generator._parse_article(text, "选题", search_results)

        assert article.title == "文章标题"
        assert "2 条检索结果" in article.source_summary
        # 没有来源信息时，不应该出现 "来源包括"
        assert "来源包括" not in article.source_summary

    def test_parse_article_with_exactly_three_sources(self):
        """测试解析时正好有3个来源（边界情况）"""
        text = "# 标题\n\n正文"
        search_results = [
            SearchResult(content="内容1", source="来源A"),
            SearchResult(content="内容2", source="来源B"),
            SearchResult(content="内容3", source="来源C"),
        ]

        article = generator._parse_article(text, "选题", search_results)

        assert "3 条检索结果" in article.source_summary
        assert "来源A" in article.source_summary
        assert "来源B" in article.source_summary
        assert "来源C" in article.source_summary
        # 正好3个时，不应该有 "等"
        assert " 等" not in article.source_summary

    @patch('src.modules.generator.Anthropic')
    def test_generate_uses_validated_temperature(self, mock_anthropic_class):
        """测试 generate 函数使用验证后的 temperature (MiniMax API)"""
        import os
        from unittest.mock import patch

        # Set MiniMax base URL so temperature=0.0 gets converted to 0.001
        with patch.dict(os.environ, {
            'ANTHROPIC_BASE_URL': 'https://api.minimaxi.com/anthropic'
        }):
            # Mock client
            mock_client = MagicMock()
            mock_anthropic_class.return_value = mock_client

            # Mock response
            mock_response = MagicMock()
            mock_response.stop_reason = "end_turn"
            mock_content = MagicMock()
            mock_content.text = "# 测试文章\n\n内容"
            mock_response.content = [mock_content]
            mock_client.messages.create.return_value = mock_response

            # 测试 temperature=0.0 被调整
            article = generator.generate(
                topic="测试",
                search_results=[],
                api_key="test-key",
                temperature=0.0  # 应该被调整为 0.001 (MiniMax only)
            )

            # 验证实际调用参数
            call_args = mock_client.messages.create.call_args
            assert call_args[1]['temperature'] == 0.001

    @patch('src.modules.generator.Anthropic')
    def test_generate_with_minimax_base_url(self, mock_anthropic_class):
        """测试使用 MiniMax base_url 创建客户端"""
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {
            'ANTHROPIC_BASE_URL': 'https://api.minimaxi.com/anthropic'
        }):
            mock_client = MagicMock()
            mock_anthropic_class.return_value = mock_client

            # Mock response
            mock_response = MagicMock()
            mock_response.stop_reason = "end_turn"
            mock_content = MagicMock()
            mock_content.text = "# 文章标题\n\n文章内容"
            mock_response.content = [mock_content]
            mock_client.messages.create.return_value = mock_response

            article = generator.generate(
                topic="测试MiniMax",
                search_results=[],
                api_key="minimax-key",
                model="MiniMax-M2.1"
            )

            # 验证使用了 MiniMax base_url with Authorization header
            mock_anthropic_class.assert_called_once_with(
                api_key="minimax-key",
                base_url='https://api.minimaxi.com/anthropic',
                default_headers={'Authorization': 'Bearer minimax-key'}
            )

            assert article.title == "文章标题"
