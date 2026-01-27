# 测试模式

**分析日期:** 2026-01-27

## 测试框架

**运行器:**
- pytest 7.4.0+ (见 `requirements.txt`)
- 配置: `pytest.ini`

**断言库:**
- pytest 内置断言 (assert 语句)
- 无外部断言库 (pytest 原生)

**运行命令:**
```bash
pytest tests/                          # 运行所有测试
pytest tests/ -v                       # 详细输出
pytest tests/ -k test_generate         # 运行匹配模式的测试
pytest tests/ --tb=short               # 短追踪格式
pytest tests/test_generator.py::TestGenerator::test_generate_basic_flow  # 特定测试
pytest tests/ --cov=src                # 覆盖率报告
pytest tests/ --cov=src --cov-report=html  # HTML 覆盖率
```

**Pytest.ini 配置** (来自 `pytest.ini`):
- 测试发现: `python_files = test_*.py`, `python_classes = Test*`, `python_functions = test_*`
- 测试路径: `testpaths = tests`
- 输出选项: `-v` (详细), `--tb=short` (短追踪), `--strict-markers` (强制标记定义), `-ra` (显示所有摘要)
- 自定义标记: `integration` (真实环境测试), `slow` (长运行测试)
- 最低 pytest 版本: 7.0

## 测试文件组织

**位置:**
- 集中放置在专用 `tests/` 目录中 (不与源代码并列)
- 镜像结构: `tests/test_module_name.py` 对应 `src/modules/module_name.py`

**命名:**
- `test_generator.py` 对应 `src/modules/generator.py`
- `test_retrieval.py` 对应 `src/modules/retrieval.py`
- `test_feishu_doc.py` 对应 `src/modules/feishu_doc.py`
- `test_agent_sdk.py` 存在 (测试 `src/modules/agent_sdk.py`)
- `test_logging_hooks.py` 对应 `src/hooks/logging_hooks.py`
- `test_log_generator.py` 对应 `src/hooks/log_generator.py`
- `test_setup.py` 用于环境设置验证

**结构:**
```
tests/
├── test_generator.py           # 40 个测试函数
├── test_generator_sdk.py       # SDK 集成测试
├── test_agent_sdk_runner.py    # AgentSDKRunner 类测试
├── test_retrieval.py           # Retrieval 模块测试
├── test_feishu_doc.py          # 飞书文档 API 测试
├── test_feishu_bitable.py      # 飞书表格 API 测试
├── test_logging_hooks.py       # 钩子生命周期测试
├── test_log_generator.py       # 日志文档生成
├── test_writer_agent.py        # 管道集成
└── test_setup.py               # 环境检查
```

## 测试结构

**测试套件组织** (见 `tests/test_generator.py`):
```python
class TestGenerator:
    """测试 generator.generate 函数"""

    @patch('src.modules.generator.Anthropic')
    def test_generate_basic_flow(self, mock_anthropic_class):
        """文档字符串中的测试描述"""
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

**模式:**
- 基于类的组织: 每个函数/特性一个测试类
- 测试方法带 `test_` 前缀: `test_generate_basic_flow`
- 每个测试都有文档字符串说明测试内容
- 三段式结构: Setup/Arrange, Execute/Act, Verify/Assert

## 模拟 (Mocking)

**框架:** unittest.mock (Python 标准库)

**模式** (见 `tests/test_generator.py`):
```python
from unittest.mock import patch, MagicMock, PropertyMock, AsyncMock

# 基于装饰器的补丁 (最常见)
@patch('src.modules.generator.Anthropic')
def test_generate_basic_flow(self, mock_anthropic_class):
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client

    # 设置模拟响应
    mock_response = MagicMock()
    mock_response.stop_reason = "end_turn"
    mock_response.content = [mock_content_block]
    mock_client.messages.create.return_value = mock_response

# 用于顺序返回的副作用
mock_client.messages.create.side_effect = [
    mock_tool_use_response,  # 第一次调用
    mock_end_response        # 第二次调用
]

# 上下文管理器风格 (此代码库中不常见)
with patch('src.modules.retrieval.subprocess.run') as mock_run:
    mock_run.return_value = MagicMock(returncode=0, stdout="result")
```

**异步模拟** (见 `tests/test_generator_sdk.py`):
```python
@pytest.mark.asyncio
async def test_generate_with_sdk_basic(self, mock_runner_class):
    mock_runner = MagicMock()
    mock_runner_class.return_value = mock_runner

    # 异步方法使用 AsyncMock
    mock_runner.generate = AsyncMock(return_value=(article_text, metrics))

    article, metrics_dict = await generator.generate_with_sdk(...)
    assert isinstance(article, Article)
```

**需要模拟的内容:**
- 外部 API 客户端: Anthropic, requests
- 系统调用: subprocess.run, Path 操作
- 时间依赖操作: time.time()
- NotebookLM 查询和飞书 API 调用
- 避免模拟: 数据类构造函数、简单工具、类型转换

**不应模拟的内容:**
- 数据类模型 (SearchResult, Article 等)
- 纯工具函数 (validate_temperature)
- 内部辅助函数 (_get_system_prompt, _build_user_message)
- 正在测试的函数本身

## 固件和工厂 (Fixtures and Factories)

**测试数据** (见 `tests/test_generator.py`):
```python
# 内联数据创建 (最常见模式)
search_results = [SearchResult(content="测试素材内容", source="测试来源")]

# 在测试中可重用
article = Article(
    title="测试标题",
    content="测试内容",
    source_summary="测试来源"
)

# 用于复杂响应的模拟对象
mock_response = MagicMock()
mock_response.stop_reason = "end_turn"
mock_content_block = MagicMock()
mock_content_block.text = "# 标题\n\n内容"
mock_response.content = [mock_content_block]
```

**使用 setup_method 进行测试设置** (见 `tests/test_feishu_doc.py`):
```python
class TestFeishuTokenManager:
    """FeishuTokenManager 测试"""

    def setup_method(self):
        """每个测试前清空缓存"""
        global _token_cache
        _token_cache["token"] = None
        _token_cache["expires_at"] = 0

    def test_get_token_uses_cache(self):
        """使用干净状态测试"""
        ...
```

**位置:**
- 测试数据在测试函数中内联创建 (无单独的固件模块)
- 在 `setup_method()` 中重置全局状态以确保干净状态
- 在每个测试中创建模拟对象以保持隔离
- 当前未使用 pytest 固件 (固件函数)

## 覆盖率

**要求:** 未显式强制执行 (pytest.ini 中无最低覆盖率)

**查看覆盖率:**
```bash
pytest tests/ --cov=src --cov-report=term-missing   # 终端显示缺失行
pytest tests/ --cov=src --cov-report=html           # HTML 报告在 htmlcov/
pytest tests/ --cov=src --cov-report=json           # JSON 格式
```

**覆盖率分析:**
- `tests/` 目录中有 22 个测试文件
- 测试数量: 仅 test_generator.py 就有 40+ 个测试方法
- 覆盖率工具: pytest-cov (见 requirements.txt)

## 测试类型

**单元测试:**
- 范围: 单个函数和方法
- 方法: 模拟所有外部依赖
- 示例: `test_generate_basic_flow`, `test_search_returns_list_of_search_results`
- 隔离: 每个测试独立且使用新的模拟

**集成测试:**
- 使用 `@pytest.mark.integration` 标记
- 范围: 多个组件一起测试
- 方法: 真实 API 调用 (环境可用时) 或真实模拟
- 示例: `test_pipeline` 测试, 飞书 API 集成测试
- 注意: 可能较慢, 在 CI 中不带集成标记时跳过

**E2E 测试:**
- 未作为单独类别明确存在
- 通过调用完整管道的集成测试实现
- 需要真实的 NotebookLM、飞书和 Anthropic API 设置

## 常见模式

**异步测试** (见 `tests/test_generator_sdk.py`, `tests/test_logging_hooks.py`):
```python
@pytest.mark.asyncio
async def test_generate_with_sdk_basic(self, mock_runner_class):
    """测试异步函数"""
    mock_runner = MagicMock()
    mock_runner.generate = AsyncMock(return_value=(article_text, metrics))

    # 等待异步函数
    article, metrics_dict = await generator.generate_with_sdk(
        topic="测试选题",
        search_results=[],
        api_key="test-key"
    )

    # 验证
    assert isinstance(article, Article)

# 异步迭代器辅助函数 (见 test_agent_sdk_runner.py)
async def async_iterator(items):
    """从项目列表创建异步迭代器"""
    for item in items:
        yield item
```

**错误测试** (见 `tests/test_generator.py`):
```python
# 异常匹配
def test_generate_raises_value_error_without_api_key(self):
    """测试缺少 API Key 时抛出异常"""
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        generator.generate(
            topic="测试",
            search_results=[],
            api_key=""
        )

# 带错误消息验证的异常
def test_search_raises_value_error_when_skill_not_installed(self, mock_path):
    """测试 skill 未安装时抛出 ValueError"""
    mock_path.home.return_value.__truediv__.return_value.exists.return_value = False

    with pytest.raises(ValueError, match="NotebookLM skill 未安装"):
        retrieval.search("查询")
```

**间谍模式** (验证进行的调用):
```python
# 验证 retrieval.search 使用正确参数被调用
mock_search.assert_called_once_with(
    "测试问题",
    notebook_id="notebook123",
    notebook_url=None
)

# 验证 API 调用次数
assert mock_client.messages.create.call_count == 2
```

**参数化测试:**
- 未广泛使用 (未检测到 @pytest.mark.parametrize)
- 可用于测试多个温度值、模型名称等

**测试标记** (来自 pytest.ini):
```python
@pytest.mark.integration      # 需要真实服务
@pytest.mark.slow             # 长运行测试
@pytest.mark.asyncio          # 异步测试 (来自 pytest-asyncio 插件)
```

## 测试依赖

**Pytest 插件:**
- `pytest-mock` (3.11.0+): 用于额外的模拟工具
- `pytest-timeout` (2.1.0+): 用于测试超时
- `pytest-cov` (4.1.0+): 用于覆盖率报告
- `pytest-asyncio`: 隐式 (用于 @pytest.mark.asyncio)

**测试中的导入模式:**
```python
import pytest
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock
from src.modules import generator
from src.models import SearchResult, Article
from src.modules.agent_sdk import AgentRunMetrics
```

## 此代码库中的最佳实践

1. **测试命名具有描述性**: `test_generate_with_tool_use` 清楚说明测试的场景

2. **文档字符串解释上下文**: 每个测试都有文档字符串描述验证内容

3. **模拟是具体的**: 只模拟所需内容 (例如, 模拟 Anthropic 客户端, 不模拟 SearchResult)

4. **状态隔离**: setup_method() 在每个测试前清除缓存以防止测试间污染

5. **清晰断言**: 断言具体且有多个检查:
   ```python
   assert isinstance(article, Article)
   assert article.title == "完整文章"
   mock_search.assert_called_once_with(...)
   ```

6. **测试错误条件**: 测试成功和失败路径 (ValueError, RuntimeError, TimeoutError)

7. **调用验证**: 验证返回值和副作用:
   ```python
   assert article.title == "Title"  # 返回值
   mock_search.assert_called_once()  # 副作用
   ```

---

*测试分析: 2026-01-27*
