"""数据结构定义"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class SearchResult:
    """检索结果"""
    content: str      # 内容片段
    source: str       # 来源标注（可为空）


@dataclass
class Article:
    """文章"""
    title: str           # 标题
    content: str         # 正文（Markdown）
    source_summary: str  # 素材来源摘要


@dataclass
class DocResult:
    """飞书文档结果"""
    doc_id: str    # 文档ID
    doc_url: str   # 访问链接


@dataclass
class PipelineResult:
    """流水线结果"""
    article: Article
    doc_result: Optional[DocResult] = None  # 可选
    record_id: Optional[str] = None         # 可选
