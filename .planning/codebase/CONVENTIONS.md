# 编码规范

**分析日期:** 2026-01-27

## 命名模式

**文件:**
- 小写加下划线: `generator.py`, `feishu_doc.py`, `logging_hooks.py`
- 模块文件使用描述性名词: `retrieval.py`, `agent_sdk.py`
- 测试文件遵循 `test_*.py` 模式: `test_generator.py`, `test_feishu_doc.py`
- 配置文件使用小写: `pytest.ini`, `.env.example`

**函数:**
- 小写加下划线: `generate()`, `validate_temperature()`, `run_pipeline()`
- 私有/内部函数带下划线前缀: `_get_system_prompt()`, `_build_user_message()`, `_parse_article()`
- 异步函数遵循相同命名: `generate_with_sdk()`, `pre_tool_use_hook()`, `post_tool_use_hook()`

**变量:**
- 小写加下划线: `search_results`, `api_key`, `folder_token`, `max_turns`
- 常量使用大写: `USE_AGENT_SDK` (基于环境变量的特性开关)
- 模块级缓存带下划线前缀: `_token_cache` (见 `src/modules/feishu_doc.py`)
- 类属性遵循小写约定: `self.api_key`, `self.model`, `self.temperature`

**类型:**
- 数据结构使用数据类: `SearchResult`, `Article`, `DocResult`, `PipelineResult` (见 `src/models.py`)
- 有状态组件使用类: `FeishuTokenManager`, `LogDocumentGenerator`, `AgentSDKRunner`
- 后缀模式: `Result` 用于返回类型, `Manager` 用于有状态服务

## 代码风格

**格式化:**
- 未发现显式的代码检查工具配置 (相当于 eslint/prettier)
- 一致的缩进: 4个空格 (Python 标准)
- 行长度: 遵循 Python PEP 8 (代码中见到 80-99 字符范围)
- 导入语句在文件顶部分组组织

**代码检查:**
- 未检测到 `.pylintrc`, `.flake8` 或其他代码检查配置文件
- 代码遵循隐式的 PEP 8 约定
- 一致使用类型提示: `def search(query: str, notebook_id: Optional[str] = None) -> List[SearchResult]`

## 导入组织

**顺序:**
1. 标准库导入: `os`, `sys`, `time`, `asyncio`, `json`, `re`, `subprocess`, `pathlib`
2. 第三方库导入: `anthropic`, `requests`, `dotenv`, `pytest`, `dataclasses`
3. 相对导入 (本地模块): `from ..models import SearchResult`, `from . import retrieval`

**路径别名:**
- 使用 `..` 进行相对导入 (访问父包): `from ..models import SearchResult`, `from ..utils import validate_temperature`
- 直接子模块导入: `from . import retrieval`, `from .agent_sdk import AgentSDKRunner`
- 未检测到绝对路径别名 (如 `@/` 或 `@src/`)

**代码库示例:**
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

## 错误处理

**模式:**
- 使用描述性消息显式抛出异常 (见 `src/modules/retrieval.py`):
  ```python
  if not skill_dir.exists():
      raise ValueError(
          f"NotebookLM skill 未安装。请先安装：\n"
          f"mkdir -p ~/.claude/skills && cd ~/.claude/skills && "
          f"git clone https://github.com/PleasePrompto/notebooklm-skill notebooklm"
      )
  ```
- ValueError 用于无效参数, RuntimeError 用于操作失败
- 错误消息包含上下文和补救步骤
- 带最大尝试次数的重试逻辑: `for attempt in range(max_retries + 1)` (见 `src/main.py`)
- 优雅降级: 搜索可以失败但管道继续执行并返回空结果
- CLI 中的全局错误处理: try-except 并打印追踪信息 (见 `cli.py`)

**使用的异常类型:**
- `ValueError`: API 密钥缺失、无效参数、技能未安装
- `RuntimeError`: API 失败、认证失败、查询失败、网络错误
- `TimeoutError`: 查询超时 (180秒 在 `retrieval.search()` 中)
- `NotImplementedError`: 未实现的功能 (飞书云文档创建)

## 日志记录

**框架:** 使用 `print()` 进行控制台输出 (无日志框架)

**模式:**
- 使用表情符号指示器的结构化输出: `✅ `, `❌ `, `⚠️ `, `🚀 `, `📚 `, `✍️  `, `📄 `, `📊 ` (见 `src/main.py`)
- 带分隔符的进度指示器: `print(f"\n{'='*60}")`, `print(f"{'—'*60}")`
- 基于阶段的输出: "阶段 1/4: 检索素材", "阶段 2/4: 生成文章"
- 基于钩子的工具调用日志: `[PRE-TOOL]`, `[POST-TOOL]` (见 `src/hooks/logging_hooks.py`)
- 工具调用日志记录: 工具名称、输入、输出、持续时间、时间戳 (见 `AgentRunMetrics.tool_calls`)
- 日志文档生成: markdown 格式带指标摘要 (见 `src/hooks/log_generator.py`)

## 注释

**何时添加注释:**
- 所有公共函数和类都有文档字符串 (存在模块级文档字符串)
- 复杂业务逻辑: 说明为什么 (而非是什么)
- 不明显的解析逻辑 (例如, `retrieval.py` 中使用分隔符的输出解析)
- 必要时注释解释上下文 (例如, 令牌刷新逻辑中的"预留100秒缓冲")

**JSDoc/TSDoc:**
- 使用 Python 文档字符串 (三引号字符串) 和结构化格式:
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
- 记录 Args, Returns 和 Raises 部分
- 注意: 文档字符串中的模式 (例如, `src/main.py` 中异常处理策略的"Note:"部分)

## 函数设计

**大小:**
- 函数通常 15-50 行 (小型、专注的函数)
- 生成器函数较长 (40-200+ 行包含 agent 循环逻辑)
- 为清晰提取辅助函数: `_get_system_prompt()`, `_build_user_message()`, `_parse_article()`

**参数:**
- 所有参数都有类型提示: `query: str`, `notebook_id: Optional[str] = None`
- 可选参数使用默认参数
- 未强制使用仅关键字参数 (接受位置参数和关键字参数)
- 每个函数最多 8 个参数 (见 `generate()` 有 7 个参数)

**返回值:**
- 显式返回类型: `-> Article`, `-> List[SearchResult]`, `-> Dict[str, Any]`
- 复杂对象使用数据类返回 (见 `Article`, `DocResult`, `PipelineResult`)
- 多个值使用元组返回: `-> Tuple[Article, Dict[str, Any]]` (在 `generate_with_sdk()` 中)
- 简单操作返回单个值或 None

## 模块设计

**导出:**
- 模块导出顶级函数和类
- `src/modules/__init__.py` 为方便导入子模块: `from . import retrieval`, `from . import generator`
- `src/utils/__init__.py` 导出工具函数: `from .temperature import validate_temperature`

**桶文件 (Barrel Files):**
- `src/__init__.py` 存在 (空)
- `src/modules/__init__.py` 提供模块导入 (见上述模式)
- `src/hooks/__init__.py` 存在 (空)
- `src/utils/__init__.py` 导出公共工具

## 数据结构约定

**数据类** (见 `src/models.py`):
- 用于具有明确字段的简单数据容器
- 类似不可变的使用方式 (测试中无初始化后的修改)
- 每个属性都有字段注释

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

## 配置模式

**环境变量:**
- 在 CLI 中使用 `python-dotenv` 加载: `load_dotenv()`
- 使用 `os.getenv()` 检查并带后备: `os.getenv("ANTHROPIC_API_KEY")`
- 作为布尔环境变量的特性开关: `USE_AGENT_SDK = os.getenv("USE_AGENT_SDK", "true").lower() == "true"`
- `.env.example` 中的配置带注释说明每个设置

---

*约定分析: 2026-01-27*
