# Testing Patterns

**Analysis Date:** 2026-01-27

## Test Framework

**Runner:**
- pytest 7.4.0+ (see `requirements.txt`)
- Config: `pytest.ini`

**Assertion Library:**
- pytest's built-in assertions (assert statements)
- No external assertion library (pytest native)

**Run Commands:**
```bash
pytest tests/                          # Run all tests
pytest tests/ -v                       # Verbose output
pytest tests/ -k test_generate         # Run tests matching pattern
pytest tests/ --tb=short               # Short traceback format
pytest tests/test_generator.py::TestGenerator::test_generate_basic_flow  # Specific test
pytest tests/ --cov=src                # Coverage report
pytest tests/ --cov=src --cov-report=html  # HTML coverage
```

**Pytest.ini Configuration** (from `pytest.ini`):
- Test discovery: `python_files = test_*.py`, `python_classes = Test*`, `python_functions = test_*`
- Test path: `testpaths = tests`
- Output options: `-v` (verbose), `--tb=short` (short traceback), `--strict-markers` (enforce marker definitions), `-ra` (show all summary)
- Custom markers: `integration` (real environment tests), `slow` (long-running tests)
- Minimum pytest version: 7.0

## Test File Organization

**Location:**
- Co-located in dedicated `tests/` directory (not alongside source)
- Mirrored structure: `tests/test_module_name.py` for `src/modules/module_name.py`

**Naming:**
- `test_generator.py` for `src/modules/generator.py`
- `test_retrieval.py` for `src/modules/retrieval.py`
- `test_feishu_doc.py` for `src/modules/feishu_doc.py`
- `test_agent_sdk.py` exists (testing `src/modules/agent_sdk.py`)
- `test_logging_hooks.py` for `src/hooks/logging_hooks.py`
- `test_log_generator.py` for `src/hooks/log_generator.py`
- `test_setup.py` for environment setup validation

**Structure:**
```
tests/
├── test_generator.py           # 40 test functions
├── test_generator_sdk.py       # SDK integration tests
├── test_agent_sdk_runner.py    # AgentSDKRunner class tests
├── test_retrieval.py           # Retrieval module tests
├── test_feishu_doc.py          # Feishu document API tests
├── test_feishu_bitable.py      # Feishu table API tests
├── test_logging_hooks.py       # Hook lifecycle tests
├── test_log_generator.py       # Log document generation
├── test_writer_agent.py        # Pipeline integration
└── test_setup.py               # Environment checks
```

## Test Structure

**Suite Organization** (see `tests/test_generator.py`):
```python
class TestGenerator:
    """测试 generator.generate 函数"""

    @patch('src.modules.generator.Anthropic')
    def test_generate_basic_flow(self, mock_anthropic_class):
        """Test description in docstring"""
        # Setup
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # Execute
        article = generator.generate(
            topic="测试选题",
            search_results=search_results,
            api_key="test-key"
        )

        # Verify
        assert isinstance(article, Article)
        assert article.title == "测试文章标题"

class TestHelperFunctions:
    """测试辅助函数"""

    def test_get_system_prompt(self):
        """测试获取系统提示词"""
        prompt = generator._get_system_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0
```

**Patterns:**
- Class-based organization: one test class per function/feature
- Test methods prefixed with `test_`: `test_generate_basic_flow`
- Docstrings on each test explaining what's being tested
- Three-section structure: Setup/Arrange, Execute/Act, Verify/Assert

## Mocking

**Framework:** unittest.mock (Python standard library)

**Patterns** (see `tests/test_generator.py`):
```python
from unittest.mock import patch, MagicMock, PropertyMock, AsyncMock

# Decorator-based patching (most common)
@patch('src.modules.generator.Anthropic')
def test_generate_basic_flow(self, mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client

    # Setup mock response
    mock_response = MagicMock()
    mock_response.stop_reason = "end_turn"
    mock_response.content = [mock_content_block]
    mock_client.messages.create.return_value = mock_response

# Side effects for sequential returns
mock_client.messages.create.side_effect = [
    mock_tool_use_response,  # First call
    mock_end_response        # Second call
]

# Context manager style (less common in this codebase)
with patch('src.modules.retrieval.subprocess.run') as mock_run:
    mock_run.return_value = MagicMock(returncode=0, stdout="result")
```

**Async Mocking** (see `tests/test_generator_sdk.py`):
```python
@pytest.mark.asyncio
async def test_generate_with_sdk_basic(self, mock_runner_class):
    mock_runner = MagicMock()
    mock_runner_class.return_value = mock_runner

    # AsyncMock for async methods
    mock_runner.generate = AsyncMock(return_value=(article_text, metrics))

    article, metrics_dict = await generator.generate_with_sdk(...)
    assert isinstance(article, Article)
```

**What to Mock:**
- External API clients: Anthropic, requests
- System calls: subprocess.run, Path operations
- Time-dependent operations: time.time()
- NotebookLM queries and Feishu API calls
- Avoid mocking: dataclass constructors, simple utilities, type conversions

**What NOT to Mock:**
- Dataclass models (SearchResult, Article, etc.)
- Pure utility functions (validate_temperature)
- Internal helper functions (_get_system_prompt, _build_user_message)
- The functions being tested themselves

## Fixtures and Factories

**Test Data** (see `tests/test_generator.py`):
```python
# Inline data creation (most common pattern)
search_results = [SearchResult(content="测试素材内容", source="测试来源")]

# Reusable in tests
article = Article(
    title="测试标题",
    content="测试内容",
    source_summary="测试来源"
)

# Mock objects for complex responses
mock_response = MagicMock()
mock_response.stop_reason = "end_turn"
mock_content_block = MagicMock()
mock_content_block.text = "# 标题\n\n内容"
mock_response.content = [mock_content_block]
```

**Test Setup with setup_method** (see `tests/test_feishu_doc.py`):
```python
class TestFeishuTokenManager:
    """FeishuTokenManager 测试"""

    def setup_method(self):
        """每个测试前清空缓存"""
        global _token_cache
        _token_cache["token"] = None
        _token_cache["expires_at"] = 0

    def test_get_token_uses_cache(self):
        """Test with clean state"""
        ...
```

**Location:**
- Test data created inline in test functions (no separate fixtures module)
- Global state reset in `setup_method()` for tests requiring clean state
- Mock objects created in each test for isolation
- No pytest fixtures (fixture functions) currently used

## Coverage

**Requirements:** Not explicitly enforced (no minimum coverage in pytest.ini)

**View Coverage:**
```bash
pytest tests/ --cov=src --cov-report=term-missing   # Terminal with missing lines
pytest tests/ --cov=src --cov-report=html           # HTML report in htmlcov/
pytest tests/ --cov=src --cov-report=json           # JSON format
```

**Coverage Analysis:**
- 22 test files in `tests/` directory
- Test count: 40+ test methods in test_generator.py alone
- Coverage tool: pytest-cov (see requirements.txt)

## Test Types

**Unit Tests:**
- Scope: Individual functions and methods
- Approach: Mock all external dependencies
- Examples: `test_generate_basic_flow`, `test_search_returns_list_of_search_results`
- Isolation: Each test is independent with fresh mocks

**Integration Tests:**
- Marked with `@pytest.mark.integration`
- Scope: Multiple components together
- Approach: Real API calls (when environment available) or realistic mocks
- Examples: `test_pipeline` tests, feishu API integration tests
- Note: Can be slow, skipped in CI without integration marker

**E2E Tests:**
- Not explicitly present as separate category
- Achieved through integration tests calling full pipeline
- Would require real NotebookLM, Feishu, and Anthropic API setup

## Common Patterns

**Async Testing** (see `tests/test_generator_sdk.py`, `tests/test_logging_hooks.py`):
```python
@pytest.mark.asyncio
async def test_generate_with_sdk_basic(self, mock_runner_class):
    """Test async function"""
    mock_runner = MagicMock()
    mock_runner.generate = AsyncMock(return_value=(article_text, metrics))

    # Await the async function
    article, metrics_dict = await generator.generate_with_sdk(
        topic="测试选题",
        search_results=[],
        api_key="test-key"
    )

    # Verify
    assert isinstance(article, Article)

# Helper for async iterators (see test_agent_sdk_runner.py)
async def async_iterator(items):
    """Create an async iterator from a list of items"""
    for item in items:
        yield item
```

**Error Testing** (see `tests/test_generator.py`):
```python
# Exception matching
def test_generate_raises_value_error_without_api_key(self):
    """测试缺少 API Key 时抛出异常"""
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        generator.generate(
            topic="测试",
            search_results=[],
            api_key=""
        )

# Exception with error message validation
def test_search_raises_value_error_when_skill_not_installed(self, mock_path):
    """测试 skill 未安装时抛出 ValueError"""
    mock_path.home.return_value.__truediv__.return_value.exists.return_value = False

    with pytest.raises(ValueError, match="NotebookLM skill 未安装"):
        retrieval.search("查询")
```

**Spy Pattern** (verifying calls made):
```python
# Verify retrieval.search was called with correct args
mock_search.assert_called_once_with(
    "测试问题",
    notebook_id="notebook123",
    notebook_url=None
)

# Verify API call count
assert mock_client.messages.create.call_count == 2
```

**Parametric Testing:**
- Not extensively used (no @pytest.mark.parametrize detected)
- Could be used for testing multiple temperature values, model names, etc.

**Test Markers** (from pytest.ini):
```python
@pytest.mark.integration      # Requires real services
@pytest.mark.slow             # Long-running tests
@pytest.mark.asyncio          # Async test (from pytest-asyncio plugin)
```

## Test Dependencies

**Pytest Plugins:**
- `pytest-mock` (3.11.0+): For additional mocking utilities
- `pytest-timeout` (2.1.0+): For test timeouts
- `pytest-cov` (4.1.0+): For coverage reporting
- `pytest-asyncio`: Implicit (for @pytest.mark.asyncio)

**Import Patterns in Tests:**
```python
import pytest
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock
from src.modules import generator
from src.models import SearchResult, Article
from src.modules.agent_sdk import AgentRunMetrics
```

## Best Practices in This Codebase

1. **Test Naming is Descriptive**: `test_generate_with_tool_use` clearly states what scenario is tested

2. **Docstrings Explain Context**: Each test has a docstring describing what it validates

3. **Mocks are Specific**: Mock only what's needed (e.g., mock Anthropic client, not SearchResult)

4. **State Isolation**: setup_method() clears caches before each test to prevent cross-test contamination

5. **Clear Assertions**: Assertions are specific with multiple checks:
   ```python
   assert isinstance(article, Article)
   assert article.title == "完整文章"
   mock_search.assert_called_once_with(...)
   ```

6. **Error Conditions Tested**: Both success and failure paths (ValueError, RuntimeError, TimeoutError)

7. **Call Verification**: Both return values AND side effects verified:
   ```python
   assert article.title == "Title"  # Return value
   mock_search.assert_called_once()  # Side effect
   ```

---

*Testing analysis: 2026-01-27*
