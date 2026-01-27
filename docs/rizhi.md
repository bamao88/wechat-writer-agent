# Agent运行日志记录系统实施计划

**项目**: wechat-writer-agent
**目标**: 迁移到Claude Agent SDK并实现基于hooks的运行日志记录系统
**日期**: 2026-01-26
**状态**: 待审核

---

## 一、项目概述

### 1.1 目标

实现agent运行日志的自动记录和飞书集成：

1. **迁移到Claude Agent SDK**：从手动agent循环迁移到标准SDK
2. **Hooks日志记录**：使用SDK原生hooks捕获执行数据
3. **飞书云文档**：自动创建详细日志文档并上传
4. **飞书多维表格**：记录4个新字段（日志URL、运行时长、Token使用量、工具调用次数）
5. **向后兼容**：通过特性开关保持现有功能可用

### 1.2 核心价值

| 指标 | 当前状态 | 目标状态 |
|------|----------|----------|
| 日志记录 | 手动print，无结构化日志 | 自动化hooks记录，结构化存储 |
| 运行追溯 | 仅控制台输出 | 飞书云文档永久存档 |
| 性能分析 | 无法统计 | 自动记录时长、token、工具调用 |
| 开发调试 | 难以复现问题 | 完整日志可回溯每次运行 |

---

## 二、架构设计

### 2.1 系统架构

```
┌──────────────────────────────────────────────────────┐
│              CLI / Pipeline (main.py)                │
│          [特性开关: USE_AGENT_SDK=true/false]         │
└───────────────────┬──────────────────────────────────┘
                    │
        ┌───────────┴──────────┐
        │                      │
   [新路径]                 [旧路径保留]
        │                      │
┌───────▼──────────┐    ┌──────▼────────────┐
│ AgentSDKRunner   │    │ generator.py      │
│ (agent_sdk.py)   │    │ (现有Anthropic SDK)│
└───────┬──────────┘    └───────────────────┘
        │
        ├─ Hooks捕获数据
        │   ├─ PreToolUse: 记录工具调用
        │   ├─ PostToolUse: 记录执行结果
        │   ├─ UserPromptSubmit: 记录初始topic
        │   └─ Stop: 触发日志上传
        │
        ├─ 指标收集
        │   └─ AgentRunMetrics
        │       ├─ runtime_seconds
        │       ├─ tool_calls[]
        │       ├─ total_tokens
        │       └─ errors[]
        │
        └─ 日志生成与上传
            ├─ LogDocumentGenerator → Markdown
            ├─ feishu_doc.create_doc() → 飞书云文档
            └─ feishu_table.insert_record() → 记录4个新字段
```

### 2.2 数据流

```
用户输入topic
    ↓
Pipeline启动 (main.py)
    ↓
[特性开关判断]
    ↓
USE_AGENT_SDK=true ────────────┐
    ↓                          │
AgentSDKRunner.generate()      │
    ↓                          │
Claude Agent SDK query()       │
    ├─ Hook: UserPromptSubmit  │
    │  → 记录topic             │
    │                          │
    ├─ Hook: PreToolUse        │
    │  → 记录工具名、参数       │
    │                          │
    ├─ Agent执行工具            │
    │                          │
    ├─ Hook: PostToolUse       │
    │  → 记录结果、耗时         │
    │                          │
    ├─ 循环直至end_turn        │
    │                          │
    └─ Hook: Stop              │
       → 聚合所有指标           │
       → 生成日志文档           │
       → 上传到飞书             │
                               │
返回: (Article, metrics_dict) ─┘
    ↓
Pipeline继续：创建文章文档
    ↓
更新飞书表格（包含4个新字段）
```

---

## 三、关键文件变更

### 3.1 新增文件

#### 文件1: `src/modules/agent_sdk.py` (约250行)

**功能**: Claude Agent SDK封装，提供与现有generator相似的接口

**关键类和函数**:

```python
@dataclass
class AgentRunMetrics:
    """运行指标数据类"""
    start_time: float
    end_time: Optional[float]
    tool_calls: List[Dict]  # 每次工具调用的详细记录
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    errors: List[str]

    @property
    def runtime_seconds(self) -> float
    @property
    def tool_call_count(self) -> int

class AgentSDKRunner:
    """SDK运行器，集成hooks"""

    def __init__(
        api_key, model, temperature,
        notebook_id, notebook_url
    )

    def _create_hooks(self) -> dict:
        """创建hooks配置，注入metrics实例"""

    def _get_tools_config(self) -> list:
        """返回NotebookLM工具定义"""

    async def generate(
        topic, search_results,
        system_prompt, max_turns
    ) -> tuple[str, AgentRunMetrics]:
        """
        主生成函数
        1. 构建user_message
        2. 配置tools和hooks
        3. 调用SDK query()
        4. 返回文本和metrics
        """
```

**技术要点**:
- 使用`claude_agent_sdk.query()`替代`anthropic.Anthropic.messages.create()`
- Hooks通过lambda注入metrics实例以共享状态
- 支持MiniMax API（通过ANTHROPIC_BASE_URL环境变量）
- 异步函数设计（SDK query是async iterator）

---

#### 文件2: `src/hooks/__init__.py` (空文件)

```python
"""Hooks模块"""
```

---

#### 文件3: `src/hooks/logging_hooks.py` (约120行)

**功能**: 实现4个lifecycle hooks

**Hook实现**:

```python
async def pre_tool_use_hook(
    input_data: Dict,
    tool_use_id: str,
    context: Any,
    metrics: AgentRunMetrics
) -> Dict:
    """
    PreToolUse: 工具调用前
    - 记录tool_name, tool_input, timestamp
    - 添加到metrics.tool_calls列表
    - 返回空dict（允许执行）
    """

async def post_tool_use_hook(
    input_data: Dict,
    tool_use_id: str,
    context: Any,
    metrics: AgentRunMetrics
) -> Dict:
    """
    PostToolUse: 工具调用后
    - 根据tool_use_id找到对应记录
    - 补充end_time, duration_ms, result
    - 返回空dict
    """

async def stop_hook(
    input_data: Dict,
    tool_use_id: str,
    context: Any,
    metrics: AgentRunMetrics
) -> Dict:
    """
    Stop: agent运行结束
    - 打印汇总统计
    - 标记metrics.end_time
    - 返回空dict（这里不做上传，在外层处理）
    """

async def user_prompt_submit_hook(
    input_data: Dict,
    tool_use_id: str,
    context: Any,
    metrics: AgentRunMetrics
) -> Dict:
    """
    UserPromptSubmit: 用户提交prompt
    - 记录初始topic
    - 打印日志
    - 返回空dict
    """
```

**设计原则**:
- 所有hooks返回空dict（不阻塞、不修改输入）
- 通过metrics对象共享状态（闭包传递）
- 仅记录数据，不执行业务逻辑（如上传）
- 打印简短日志便于调试

---

#### 文件4: `src/hooks/log_generator.py` (约100行)

**功能**: 从metrics生成markdown格式日志文档

```python
class LogDocumentGenerator:
    """日志文档生成器"""

    def __init__(self, topic: str, metrics: AgentRunMetrics):
        self.topic = topic
        self.metrics = metrics
        self.timestamp = datetime.now()

    def generate_markdown(self) -> str:
        """
        生成markdown文档

        结构：
        # Agent Run Log
        - Topic
        - Timestamp
        - Runtime
        - Tool calls count

        ## Execution Summary
        - Tokens统计
        - 时间戳

        ## Tool Calls
        ### Tool Call 1: tool_name
        - Tool Use ID
        - Duration
        - Input (JSON)
        - Result (前500字符)

        ## Errors
        - 错误列表
        """
```

**输出示例**:
```markdown
# Agent Run Log

**Topic**: 产品经理如何做技术选型调研
**Timestamp**: 2026-01-26 14:30:15
**Runtime**: 87.43 seconds
**Tool Calls**: 3

---

## Execution Summary

- **Total Tokens**: 3245
- **Prompt Tokens**: 1520
- **Completion Tokens**: 1725
- **Start Time**: 14:28:48
- **End Time**: 14:30:15

---

## Tool Calls

### Tool Call 1: query_notebooklm

**Tool Use ID**: `toolu_01abc123`
**Duration**: 2345.67ms

**Input**:
```json
{
  "question": "产品经理技术选型的案例"
}
```

**Result Preview**:
```
根据我的经验，产品经理在做技术选型时...（前500字符）
```
```

---

### 3.2 修改文件

#### 修改1: `src/modules/generator.py`

**变更位置**: 文件开头和generate函数

```python
# 第6行后添加
USE_AGENT_SDK = os.getenv("USE_AGENT_SDK", "false").lower() == "true"

# 第21行generate函数后添加新函数
async def generate_with_sdk(
    topic: str,
    search_results: List[SearchResult],
    api_key: str,
    model: str = "MiniMax-M2.1",
    max_turns: int = 10,
    notebook_id: Optional[str] = None,
    notebook_url: Optional[str] = None,
    temperature: float = 0.7
) -> tuple[Article, dict]:
    """
    使用Claude Agent SDK生成文章（带metrics）

    Returns:
        (Article, metrics_dict)
        metrics_dict包含:
        - runtime_seconds: float
        - tool_call_count: int
        - total_tokens: int
        - prompt_tokens: int
        - completion_tokens: int
        - log_markdown: str
    """
    from .agent_sdk import AgentSDKRunner
    from ..hooks.log_generator import LogDocumentGenerator

    # 创建SDK runner
    runner = AgentSDKRunner(
        api_key=api_key,
        model=model,
        temperature=temperature,
        notebook_id=notebook_id,
        notebook_url=notebook_url
    )

    # 生成
    system_prompt = _get_system_prompt()
    result_text, metrics = await runner.generate(
        topic=topic,
        search_results=search_results,
        system_prompt=system_prompt,
        max_turns=max_turns
    )

    # 解析文章
    article = _parse_article(result_text, topic, search_results)

    # 生成日志文档
    log_gen = LogDocumentGenerator(topic, metrics)
    log_markdown = log_gen.generate_markdown()

    # 构建metrics字典
    metrics_dict = {
        'runtime_seconds': metrics.runtime_seconds,
        'tool_call_count': metrics.tool_call_count,
        'total_tokens': metrics.total_tokens,
        'prompt_tokens': metrics.prompt_tokens,
        'completion_tokens': metrics.completion_tokens,
        'log_markdown': log_markdown
    }

    return article, metrics_dict

# 原有generate()函数不变，供旧路径使用
```

**变更说明**:
- 添加`USE_AGENT_SDK`特性开关
- 新增`generate_with_sdk()`异步函数
- 保持`generate()`原有逻辑不变（向后兼容）

---

#### 修改2: `src/modules/feishu_table.py`

**变更位置**: 字段验证部分

```python
# 第13行保持不变
REQUIRED_FIELDS = ["选题名称", "文章链接", "创建时间", "状态"]

# 第61行后添加新函数
def _validate_optional_fields(fields: dict) -> None:
    """
    验证可选字段（新增的4个日志字段）

    Args:
        fields: 字段字典

    Raises:
        ValueError: 字段类型错误
    """
    # 运行时长（秒）- 数字类型
    if "运行时长（秒）" in fields:
        value = fields["运行时长（秒）"]
        if value is not None and not isinstance(value, (int, float)):
            raise ValueError("运行时长（秒）必须是数字类型")

    # Token使用量 - 整数类型
    if "Token使用量" in fields:
        value = fields["Token使用量"]
        if value is not None and not isinstance(value, int):
            raise ValueError("Token使用量必须是整数类型")

    # 工具调用次数 - 整数类型
    if "工具调用次数" in fields:
        value = fields["工具调用次数"]
        if value is not None and not isinstance(value, int):
            raise ValueError("工具调用次数必须是整数类型")

    # 日志文档URL - 字符串类型
    if "日志文档URL" in fields:
        value = fields["日志文档URL"]
        if value is not None and not isinstance(value, str):
            raise ValueError("日志文档URL必须是字符串类型")

# 第146行insert_record()函数中，在现有验证后添加
def insert_record(fields: dict) -> str:
    # ... 现有验证 ...
    _validate_required_fields(fields)
    _validate_field_types(fields)
    _validate_field_values(fields)

    # 新增：验证可选字段
    _validate_optional_fields(fields)

    # ... 其余代码不变 ...
```

**飞书表格字段配置**（需手动在飞书UI添加）:

| 字段名 | 字段类型 | 必填 | 说明 |
|--------|---------|------|------|
| 日志文档URL | URL | 否 | 指向飞书云文档的完整链接 |
| 运行时长（秒） | 数字 | 否 | 保留2位小数 |
| Token使用量 | 数字 | 否 | 整数，prompt + completion |
| 工具调用次数 | 数字 | 否 | 整数，工具调用总次数 |

---

#### 修改3: `src/main.py`

**变更位置**: 生成阶段和飞书记录阶段

```python
# 第8行后添加
USE_AGENT_SDK = os.getenv("USE_AGENT_SDK", "false").lower() == "true"

# 第97行（文章生成阶段）替换为
print(f"\n{'='*60}")
print("📝 阶段2：生成文章")
print(f"{'='*60}")

metrics_dict = None  # 初始化

if USE_AGENT_SDK:
    # 新路径：使用Claude Agent SDK
    print("🔧 使用 Claude Agent SDK（带hooks日志）")
    import asyncio
    article, metrics_dict = asyncio.run(generator.generate_with_sdk(
        topic=topic,
        search_results=search_results,
        api_key=api_key,
        model=os.getenv("ANTHROPIC_MODEL", "MiniMax-M2.1"),
        max_turns=max_turns,
        notebook_id=notebook_id,
        notebook_url=notebook_url
    ))
else:
    # 旧路径：使用原有Anthropic SDK
    print("🔧 使用 Anthropic SDK（原有实现）")
    article = generator.generate(
        topic=topic,
        search_results=search_results,
        api_key=api_key,
        model=os.getenv("ANTHROPIC_MODEL", "MiniMax-M2.1"),
        max_turns=max_turns,
        notebook_id=notebook_id,
        notebook_url=notebook_url
    )

print(f"✅ 文章生成完成")
print(f"   标题: {article.title}")
print(f"   字数: {len(article.content)} 字符")

# 如果有metrics，打印统计信息
if metrics_dict:
    print(f"\n📊 运行统计:")
    print(f"   运行时长: {metrics_dict['runtime_seconds']:.2f} 秒")
    print(f"   Token使用: {metrics_dict['total_tokens']} tokens")
    print(f"   工具调用: {metrics_dict['tool_call_count']} 次")

# 第150行（飞书表格更新阶段）添加日志上传逻辑
if enable_feishu:
    print(f"\n{'='*60}")
    print("📊 阶段4：更新飞书多维表格")
    print(f"{'='*60}")

    # 基础字段
    record_fields = {
        "选题名称": topic,
        "文章链接": doc_result.doc_url,
        "创建时间": int(time.time() * 1000),
        "状态": "草稿"
    }

    # 如果使用SDK且有metrics，上传日志并添加字段
    if metrics_dict:
        print("📄 上传运行日志到飞书...")

        # 上传日志文档
        if metrics_dict.get('log_markdown'):
            try:
                log_doc_result = feishu_doc.create_doc(
                    title=f"运行日志-{topic}",
                    content=metrics_dict['log_markdown'],
                    folder_token=folder_token
                )
                record_fields["日志文档URL"] = log_doc_result.doc_url
                print(f"   ✅ 日志文档: {log_doc_result.doc_url}")
            except Exception as e:
                print(f"   ⚠️ 日志文档上传失败: {e}")
                print(f"   ⏭️ 继续执行，日志字段留空")

        # 添加metrics字段
        record_fields["运行时长（秒）"] = round(metrics_dict['runtime_seconds'], 2)
        record_fields["Token使用量"] = metrics_dict['total_tokens']
        record_fields["工具调用次数"] = metrics_dict['tool_call_count']

        print(f"   📊 运行指标已添加到记录")

    # 插入记录
    record_id = feishu_table.insert_record(record_fields)
    print(f"✅ 记录已创建")
    print(f"   记录ID: {record_id}")
```

**关键变更**:
1. 根据`USE_AGENT_SDK`选择生成路径
2. 接收metrics_dict（新路径）或None（旧路径）
3. 上传日志文档到飞书（若metrics存在）
4. 向表格记录添加4个新字段

---

## 四、依赖和环境

### 4.1 新增依赖

```txt
# requirements.txt 添加
claude-agent-sdk>=0.1.0  # Claude Agent SDK
```

### 4.2 环境变量

```bash
# .env 添加特性开关
USE_AGENT_SDK=false  # 初始为false，测试后改为true

# 现有环境变量（保持不变）
ANTHROPIC_API_KEY=xxx
ANTHROPIC_BASE_URL=https://api.minimaxi.com/anthropic
ANTHROPIC_MODEL=MiniMax-M2.1

FEISHU_APP_ID=xxx
FEISHU_APP_SECRET=xxx
FEISHU_FOLDER_TOKEN=xxx
FEISHU_BITABLE_APP_TOKEN=xxx
FEISHU_BITABLE_TABLE_ID=xxx
```

---

## 五、测试计划

### 5.1 单元测试

#### 测试文件1: `tests/test_agent_sdk.py` (新建，15个测试)

```python
class TestAgentRunMetrics:
    """测试AgentRunMetrics数据类"""
    def test_runtime_seconds_calculation()
    def test_tool_call_count_property()
    def test_initial_state()

class TestAgentSDKRunner:
    """测试AgentSDKRunner"""
    @pytest.mark.asyncio
    @patch('src.modules.agent_sdk.query')
    async def test_generate_basic_flow()

    @pytest.mark.asyncio
    async def test_generate_with_tool_calls()

    @pytest.mark.asyncio
    async def test_hooks_registered()

    async def test_get_tools_config()
    async def test_build_user_message()
```

**覆盖目标**: 90%+ 覆盖率

---

#### 测试文件2: `tests/test_logging_hooks.py` (新建，12个测试)

```python
class TestLoggingHooks:
    """测试所有hooks"""

    @pytest.mark.asyncio
    async def test_pre_tool_use_hook_records_data()
    async def test_pre_tool_use_hook_returns_empty_dict()

    @pytest.mark.asyncio
    async def test_post_tool_use_hook_updates_record()
    async def test_post_tool_use_hook_calculates_duration()

    @pytest.mark.asyncio
    async def test_stop_hook_marks_end_time()
    async def test_stop_hook_prints_summary()

    @pytest.mark.asyncio
    async def test_user_prompt_submit_hook_logs_topic()

    async def test_metrics_shared_across_hooks()
```

---

#### 测试文件3: `tests/test_log_generator.py` (新建，8个测试)

```python
class TestLogDocumentGenerator:
    """测试日志文档生成"""

    def test_generate_markdown_basic_structure()
    def test_markdown_includes_topic()
    def test_markdown_includes_metrics_summary()
    def test_markdown_tool_calls_section()
    def test_markdown_errors_section()
    def test_json_formatting_in_markdown()
    def test_result_preview_truncation()
    def test_handles_empty_metrics()
```

---

#### 测试文件4: `tests/test_feishu_table_enhanced.py` (新建，10个测试)

```python
class TestFeishuTableEnhancements:
    """测试飞书表格新字段"""

    def test_validate_optional_fields_valid()
    def test_validate_runtime_seconds_type()
    def test_validate_token_usage_type()
    def test_validate_tool_call_count_type()
    def test_validate_log_url_type()

    def test_insert_record_with_all_new_fields()
    def test_insert_record_with_partial_new_fields()
    def test_insert_record_without_new_fields()

    def test_optional_fields_none_allowed()
    def test_optional_fields_validation_errors()
```

---

### 5.2 集成测试

#### 测试文件5: `tests/test_sdk_pipeline_integration.py` (新建，6个测试)

```python
class TestSDKPipelineIntegration:
    """测试SDK完整流程集成"""

    @pytest.mark.asyncio
    @patch('src.modules.agent_sdk.query')
    async def test_full_pipeline_with_sdk()

    @pytest.mark.asyncio
    async def test_metrics_flow_through_pipeline()

    @pytest.mark.asyncio
    async def test_log_document_upload()

    @pytest.mark.asyncio
    async def test_table_record_with_metrics()

    async def test_feature_flag_toggle()
    async def test_backward_compatibility()
```

---

### 5.3 手动验证清单

```markdown
## 功能验证

### SDK基础功能
- [ ] Claude Agent SDK query()执行成功
- [ ] NotebookLM工具可正常调用
- [ ] 多轮对话流程正常
- [ ] Token统计准确
- [ ] 支持MiniMax模型

### Hooks功能
- [ ] PreToolUse捕获工具调用
- [ ] PostToolUse记录执行结果
- [ ] Stop hook触发时机正确
- [ ] UserPromptSubmit记录topic
- [ ] Metrics数据完整准确

### 日志生成
- [ ] Markdown格式正确
- [ ] 包含所有必需字段
- [ ] JSON格式化正确
- [ ] 结果预览截断合理

### 飞书集成
- [ ] 日志文档成功上传
- [ ] 文档内容完整可读
- [ ] 表格记录包含4个新字段
- [ ] 字段值类型正确
- [ ] 上传失败时优雅降级

### 向后兼容
- [ ] USE_AGENT_SDK=false时使用旧实现
- [ ] 旧实现功能无影响
- [ ] 特性开关可随时切换
- [ ] 无breaking changes

### 性能和稳定性
- [ ] 运行时长统计准确（误差<1秒）
- [ ] 日志文档生成<5秒
- [ ] 飞书上传<10秒
- [ ] 无内存泄漏
- [ ] 错误处理正确
```

---

## 六、实施步骤

### Phase 1: 基础设施（2小时）

**步骤**:
1. 安装依赖: `pip install claude-agent-sdk`
2. 创建目录结构: `mkdir -p src/hooks`
3. 在飞书表格UI手动添加4个新字段
4. 验证环境: 测试SDK导入是否成功

**验收**:
- [ ] `import claude_agent_sdk` 成功
- [ ] 飞书表格显示4个新列
- [ ] `USE_AGENT_SDK=false` 在.env中

---

### Phase 2: 核心实现（6-8小时）

**步骤**:
1. 实现`src/modules/agent_sdk.py`（2小时）
   - AgentRunMetrics数据类
   - AgentSDKRunner类
   - generate()方法

2. 实现`src/hooks/logging_hooks.py`（2小时）
   - 4个hook函数
   - Metrics注入逻辑

3. 实现`src/hooks/log_generator.py`（1小时）
   - LogDocumentGenerator类
   - Markdown模板

4. 修改`src/modules/generator.py`（1小时）
   - 添加generate_with_sdk()
   - 特性开关逻辑

5. 修改`src/modules/feishu_table.py`（1小时）
   - _validate_optional_fields()
   - insert_record()增强

6. 修改`src/main.py`（1-2小时）
   - 生成阶段分支逻辑
   - 日志上传逻辑
   - 表格字段添加

**验收**:
- [ ] 所有文件创建/修改完成
- [ ] 代码可导入无语法错误
- [ ] Pylint/Flake8检查通过

---

### Phase 3: 单元测试（4-6小时）

**步骤**:
1. 编写`test_agent_sdk.py`（1.5小时）
2. 编写`test_logging_hooks.py`（1.5小时）
3. 编写`test_log_generator.py`（1小时）
4. 编写`test_feishu_table_enhanced.py`（1.5小时）
5. 运行测试并修复bug（1小时）

**验收**:
- [ ] 所有单元测试通过
- [ ] 覆盖率达到85%+
- [ ] 无测试警告

---

### Phase 4: 集成测试（3-4小时）

**步骤**:
1. 编写`test_sdk_pipeline_integration.py`（2小时）
2. Mock真实API响应（1小时）
3. 运行集成测试并修复bug（1小时）

**验收**:
- [ ] 集成测试全部通过
- [ ] Pipeline端到端流程正常

---

### Phase 5: 手动验证（3-4小时）

**步骤**:
1. **环境准备**（30分钟）
   - 配置.env: `USE_AGENT_SDK=true`
   - 准备测试topic

2. **功能测试**（1.5小时）
   - 运行完整pipeline
   - 检查日志文档
   - 验证飞书表格字段

3. **边界测试**（1小时）
   - 测试0个工具调用场景
   - 测试多工具调用场景
   - 测试飞书上传失败场景
   - 测试特性开关切换

4. **性能测试**（30分钟）
   - 测试运行时长统计准确性
   - 测试日志生成速度
   - 测试飞书上传速度

**验收**:
- [ ] 手动验证清单全部通过
- [ ] 无未捕获异常
- [ ] 性能指标合格

---

### Phase 6: 文档和发布（1-2小时）

**步骤**:
1. 更新`docs/status.md`（30分钟）
   - 添加hooks实现章节
   - 更新测试覆盖率

2. 编写使用文档（30分钟）
   - 如何启用SDK模式
   - 如何查看日志
   - 故障排查指南

3. 提交代码（30分钟）
   - Git commit（遵循现有规范）
   - 可选：创建PR

**验收**:
- [ ] 文档更新完成
- [ ] 代码已提交
- [ ] README包含hooks说明

---

## 七、风险与缓解

### 风险1: Claude Agent SDK与MiniMax API不兼容

**概率**: 中
**影响**: 高（无法使用SDK）

**缓解措施**:
1. **Phase 1验证**: 在实施前先运行简单SDK query测试
2. **环境变量支持**: 通过`ANTHROPIC_BASE_URL`环境变量配置
3. **降级方案**: 特性开关永久保持false，继续使用旧实现

**测试方法**:
```python
# 在Phase 1验证
from claude_agent_sdk import query, ClaudeAgentOptions
import os

async def test():
    async for msg in query(
        prompt="测试",
        options=ClaudeAgentOptions(
            model="MiniMax-M2.1",
            env={"ANTHROPIC_BASE_URL": os.getenv("ANTHROPIC_BASE_URL")}
        )
    ):
        print(msg)
```

---

### 风险2: Hooks无法获取Token统计

**概率**: 中
**影响**: 中（缺少Token字段）

**缓解措施**:
1. **查看SDK文档**: 确认ResultMessage是否包含usage字段
2. **Fallback方案**: 若SDK不提供，设置token字段为None
3. **手动估算**: 可选实现基于字符数的token估算

**代码准备**:
```python
# 在post_tool_use_hook中
if hasattr(input_data, 'usage'):
    metrics.total_tokens = input_data.usage.total_tokens
else:
    # Fallback: 估算或置None
    metrics.total_tokens = 0
```

---

### 风险3: 飞书日志上传失败导致pipeline中断

**概率**: 低
**影响**: 中（用户体验差）

**缓解措施**:
1. **Try-Catch包裹**: 所有飞书上传代码用try-except
2. **优雅降级**: 上传失败时仅打印警告，继续执行
3. **本地备份**: 可选保存日志到本地logs/目录

**实现**（已包含在main.py修改中）:
```python
try:
    log_doc_result = feishu_doc.create_doc(...)
    record_fields["日志文档URL"] = log_doc_result.doc_url
except Exception as e:
    print(f"⚠️ 日志文档上传失败: {e}")
    # 不设置URL字段，继续执行
```

---

### 风险4: Hooks超时

**概率**: 低
**影响**: 低（仅影响日志记录）

**缓解措施**:
1. **增加timeout**: Stop hook的timeout设为180秒
2. **异步上传**: 在hook中仅标记，实际上传在外层进行（当前设计）
3. **监控**: 打印hook执行时间

**配置**:
```python
# 在agent_sdk.py的_create_hooks()中
'Stop': [HookMatcher(
    hooks=[stop_hook],
    timeout=180  # 3分钟，足够上传
)]
```

---

### 风险5: 向后兼容性破坏

**概率**: 低
**影响**: 高（影响现有用户）

**缓解措施**:
1. **特性开关**: 默认关闭新功能
2. **保留旧代码**: 完全不修改现有generate()逻辑
3. **测试**: test_backward_compatibility确保旧路径正常
4. **文档**: 明确标注新功能为可选

**验证**:
```bash
# 测试旧路径
export USE_AGENT_SDK=false
python cli.py  # 应与现有行为一致
```

---

## 八、成功标准

### 8.1 功能性指标

- [x] Claude Agent SDK集成成功
- [x] 4个hooks正确捕获数据
- [x] 日志文档格式完整
- [x] 飞书集成4个新字段
- [x] 特性开关工作正常

### 8.2 质量指标

- [x] 单元测试覆盖率≥85%
- [x] 所有集成测试通过
- [x] 手动验证清单100%通过
- [x] 无P0/P1级别bug

### 8.3 性能指标

- [x] 运行时长统计误差<1秒
- [x] 日志生成耗时<5秒
- [x] 飞书上传耗时<10秒
- [x] 总overhead<20%（相对旧实现）

### 8.4 可用性指标

- [x] 文档完整清晰
- [x] 错误信息友好
- [x] 降级策略明确
- [x] 故障排查指南可用

---

## 九、后续优化方向（可选）

1. **日志检索**: 在飞书表格中添加日志内容全文搜索
2. **可视化**: 基于日志数据生成性能趋势图表
3. **告警**: Token使用量超阈值时发送通知
4. **批量分析**: 批量导出日志进行数据分析
5. **Hook扩展**: 添加更多hooks（如错误捕获、重试逻辑）

---

## 十、总结

本计划实现了完整的agent运行日志系统，通过Claude Agent SDK的hooks机制自动捕获执行数据，并与飞书深度集成。采用特性开关保证向后兼容，分阶段实施降低风险。预计总工时**20-26小时**，完成后将大幅提升系统可观测性和调试效率。
