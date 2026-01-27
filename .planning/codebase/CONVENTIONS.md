# Coding Conventions

**Analysis Date:** 2026-01-27

## Naming Patterns

**Files:**
- Lowercase with underscores: `generator.py`, `feishu_doc.py`, `logging_hooks.py`
- Module files use descriptive nouns: `retrieval.py`, `agent_sdk.py`
- Test files follow `test_*.py` pattern: `test_generator.py`, `test_feishu_doc.py`
- Configuration files use lowercase: `pytest.ini`, `.env.example`

**Functions:**
- Lowercase with underscores: `generate()`, `validate_temperature()`, `run_pipeline()`
- Private/internal functions prefixed with underscore: `_get_system_prompt()`, `_build_user_message()`, `_parse_article()`
- Async functions follow same naming: `generate_with_sdk()`, `pre_tool_use_hook()`, `post_tool_use_hook()`

**Variables:**
- Lowercase with underscores: `search_results`, `api_key`, `folder_token`, `max_turns`
- Constants in UPPERCASE: `USE_AGENT_SDK` (environment-based feature flags)
- Module-level caches prefixed with underscore: `_token_cache` (see `src/modules/feishu_doc.py`)
- Class attributes follow lowercase convention: `self.api_key`, `self.model`, `self.temperature`

**Types:**
- Dataclasses for data structures: `SearchResult`, `Article`, `DocResult`, `PipelineResult` (see `src/models.py`)
- Classes for stateful components: `FeishuTokenManager`, `LogDocumentGenerator`, `AgentSDKRunner`
- Suffix pattern: `Result` for return types, `Manager` for stateful services

## Code Style

**Formatting:**
- No explicit linter config (eslint/prettier equivalent) found
- Consistent indentation: 4 spaces (Python standard)
- Line length: appears to follow Python PEP 8 (80-99 char range seen in code)
- Imports are organized in groups at file top

**Linting:**
- No `.pylintrc`, `.flake8`, or linting config files detected
- Code follows implicit PEP 8 conventions
- Type hints used consistently: `def search(query: str, notebook_id: Optional[str] = None) -> List[SearchResult]`

## Import Organization

**Order:**
1. Standard library imports: `os`, `sys`, `time`, `asyncio`, `json`, `re`, `subprocess`, `pathlib`
2. Third-party imports: `anthropic`, `requests`, `dotenv`, `pytest`, `dataclasses`
3. Relative imports (local modules): `from ..models import SearchResult`, `from . import retrieval`

**Path Aliases:**
- Uses relative imports with `..` (parent package access): `from ..models import SearchResult`, `from ..utils import validate_temperature`
- Direct submodule imports: `from . import retrieval`, `from .agent_sdk import AgentSDKRunner`
- No absolute path aliases (like `@/` or `@src/`) detected

**Examples from codebase:**
```python
# src/modules/generator.py
import os
import re
from pathlib import Path
from anthropic import Anthropic
from typing import List, Optional, Dict, Any
from ..models import SearchResult, Article
from . import retrieval
from ..utils import validate_temperature
from .agent_sdk import AgentSDKRunner
from ..hooks.log_generator import LogDocumentGenerator
```

## Error Handling

**Patterns:**
- Explicit exception raising with descriptive messages (see `src/modules/retrieval.py`):
  ```python
  if not skill_dir.exists():
      raise ValueError(
          f"NotebookLM skill 未安装。请先安装：\n"
          f"mkdir -p ~/.claude/skills && cd ~/.claude/skills && "
          f"git clone https://github.com/PleasePrompto/notebooklm-skill notebooklm"
      )
  ```
- ValueError for invalid parameters, RuntimeError for operation failures
- Error messages include context and remediation steps
- Retry logic with max attempts: `for attempt in range(max_retries + 1)` (see `src/main.py`)
- Graceful degradation: searches can fail but pipeline continues with empty results
- Global error handling in CLI: try-except with traceback printing (see `cli.py`)

**Exception types used:**
- `ValueError`: API key missing, invalid parameters, skill not installed
- `RuntimeError`: API failures, authentication failures, query failures, network errors
- `TimeoutError`: Query timeouts (180s in `retrieval.search()`)
- `NotImplementedError`: Unimplemented features (Feishu cloud document creation)

## Logging

**Framework:** Console output with `print()` (no logger framework)

**Patterns:**
- Structured output with emoji indicators: `✅ `, `❌ `, `⚠️ `, `🚀 `, `📚 `, `✍️  `, `📄 `, `📊 ` (see `src/main.py`)
- Progress indicators with dividers: `print(f"\n{'='*60}")`, `print(f"{'—'*60}")`
- Stage-based output: "阶段 1/4: 检索素材", "阶段 2/4: 生成文章"
- Hook-based logging for tool calls: `[PRE-TOOL]`, `[POST-TOOL]` (see `src/hooks/logging_hooks.py`)
- Tool call logging records: tool name, input, output, duration, timestamps (see `AgentRunMetrics.tool_calls`)
- Log document generation: markdown format with metrics summary (see `src/hooks/log_generator.py`)

## Comments

**When to Comment:**
- Docstrings on all public functions and classes (module-level docstrings present)
- Complex business logic: clarifying why (not what) the code does
- Non-obvious parsing logic (e.g., output parsing with delimiters in `retrieval.py`)
- Comments explain context when needed (e.g., "预留100秒缓冲" in token refresh logic)

**JSDoc/TSDoc:**
- Uses Python docstrings (triple-quoted strings) with structured format:
  ```python
  def generate(
      topic: str,
      search_results: List[SearchResult],
      api_key: str,
      model: str = "MiniMax-M2.1",
      max_turns: int = 10,
      notebook_id: Optional[str] = None,
      notebook_url: Optional[str] = None,
      temperature: float = 0.7
  ) -> Article:
      """
      基于检索结果生成文章

      Args:
          topic: 文章主题
          search_results: 预先检索的结果列表
          api_key: Anthropic API Key
          model: 使用的模型
          max_turns: 最大对话轮数
          notebook_id: NotebookLM 笔记本 ID（用于追加检索）
          notebook_url: NotebookLM 笔记本 URL（用于追加检索）
          temperature: 生成温度参数

      Returns:
          生成的文章

      Raises:
          ValueError: API Key 无效
          RuntimeError: 生成失败
      """
  ```
- Documents Args, Returns, and Raises sections
- Note: patterns in docstrings (e.g., "Note:" section in `src/main.py` for exception handling strategy)

## Function Design

**Size:**
- Functions typically 15-50 lines (small, focused functions)
- Generator functions longer (40-200+ lines with agent loop logic)
- Helper functions extracted for clarity: `_get_system_prompt()`, `_build_user_message()`, `_parse_article()`

**Parameters:**
- Type hints on all parameters: `query: str`, `notebook_id: Optional[str] = None`
- Default parameters for optional arguments
- Keyword-only arguments not enforced (positional and keyword accepted)
- Maximum 8 parameters per function (see `generate()` with 7 params)

**Return Values:**
- Explicit return types: `-> Article`, `-> List[SearchResult]`, `-> Dict[str, Any]`
- Dataclass returns for complex objects (see `Article`, `DocResult`, `PipelineResult`)
- Tuple returns for multiple values: `-> Tuple[Article, Dict[str, Any]]` (in `generate_with_sdk()`)
- Single values or None for simple operations

## Module Design

**Exports:**
- Modules export top-level functions and classes
- `src/modules/__init__.py` imports submodules for convenience: `from . import retrieval`, `from . import generator`
- `src/utils/__init__.py` exports utility functions: `from .temperature import validate_temperature`

**Barrel Files:**
- `src/__init__.py` exists (empty)
- `src/modules/__init__.py` provides module imports (see pattern above)
- `src/hooks/__init__.py` exists (empty)
- `src/utils/__init__.py` exports public utilities

## Data Structure Conventions

**Dataclasses** (see `src/models.py`):
- Used for simple data containers with clear fields
- Immutable-like usage (no post-initialization mutations in tests)
- Field comments on each attribute

```python
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
```

## Configuration Patterns

**Environment Variables:**
- Loaded with `python-dotenv` in CLI: `load_dotenv()`
- Checked with `os.getenv()` with fallback: `os.getenv("ANTHROPIC_API_KEY")`
- Feature flags as boolean env vars: `USE_AGENT_SDK = os.getenv("USE_AGENT_SDK", "true").lower() == "true"`
- Configuration in `.env.example` with comments explaining each setting

---

*Convention analysis: 2026-01-27*
