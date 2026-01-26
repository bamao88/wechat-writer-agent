"""
测试数据结构定义
"""
import pytest
from src.models import SearchResult, Article, DocResult, PipelineResult


class TestSearchResult:
    """测试 SearchResult 数据类"""

    def test_create_search_result(self):
        """测试创建 SearchResult"""
        result = SearchResult(
            content="这是检索到的内容",
            source="来源示例"
        )
        assert result.content == "这是检索到的内容"
        assert result.source == "来源示例"

    def test_search_result_with_empty_source(self):
        """测试创建无来源的 SearchResult"""
        result = SearchResult(
            content="内容",
            source=""
        )
        assert result.content == "内容"
        assert result.source == ""


class TestArticle:
    """测试 Article 数据类"""

    def test_create_article(self):
        """测试创建 Article"""
        article = Article(
            title="测试标题",
            content="# 测试标题\n\n这是正文内容",
            source_summary="基于 3 条检索结果生成"
        )
        assert article.title == "测试标题"
        assert "测试标题" in article.content
        assert article.source_summary == "基于 3 条检索结果生成"


class TestDocResult:
    """测试 DocResult 数据类"""

    def test_create_doc_result(self):
        """测试创建 DocResult"""
        doc = DocResult(
            doc_id="doc123",
            doc_url="https://feishu.cn/docx/doc123"
        )
        assert doc.doc_id == "doc123"
        assert "feishu.cn" in doc.doc_url


class TestPipelineResult:
    """测试 PipelineResult 数据类"""

    def test_create_pipeline_result_without_feishu(self):
        """测试创建不含飞书结果的 PipelineResult"""
        article = Article(
            title="标题",
            content="内容",
            source_summary="摘要"
        )
        result = PipelineResult(article=article)

        assert result.article == article
        assert result.doc_result is None
        assert result.record_id is None

    def test_create_pipeline_result_with_feishu(self):
        """测试创建包含飞书结果的 PipelineResult"""
        article = Article(
            title="标题",
            content="内容",
            source_summary="摘要"
        )
        doc = DocResult(
            doc_id="doc123",
            doc_url="https://feishu.cn/docx/doc123"
        )
        result = PipelineResult(
            article=article,
            doc_result=doc,
            record_id="rec123"
        )

        assert result.article == article
        assert result.doc_result == doc
        assert result.record_id == "rec123"
