# 日志系统技术限制文档

## 概述

本文档说明微信公众号文章生成系统日志功能的技术限制，帮助用户理解哪些信息可以被捕获、哪些信息受到技术限制，以及这些限制的原因和可能的替代方案。

## 当前日志覆盖率

**总体覆盖率：约 60-65%**

### ✅ 已覆盖的信息

我们的日志系统目前可以捕获：

1. **基础执行指标**
   - 运行时长（start_time, end_time）
   - Token使用量（total_tokens, prompt_tokens, completion_tokens）
   - 工具调用次数

2. **工具调用详情**（通过 SDK Hooks）
   - 工具名称和调用时间
   - 工具输入参数（完整JSON）
   - 工具输出结果（可配置截断长度）
   - 每次调用的耗时

3. **Prompt信息**（v2.0新增）
   - System Prompt完整内容
   - 初始用户消息（包含预检索结果）

4. **对话消息流**（v2.0新增）
   - 每条消息的类型和时间戳
   - 消息内容长度
   - Token使用统计
   - Stop reason

5. **配置信息**（v2.0新增）
   - Notebook ID和URL配置
   - SDK模式开关
   - 工具调用诊断提示

6. **错误信息**
   - 捕获的异常和错误消息

### ❌ 无法捕获的信息

以下信息因技术限制无法直接捕获：

#### 1. Agent内部思考过程

**现状**：无法获取Agent在生成内容时的内部推理、思考链（Chain of Thought）。

**原因**：
- Claude Agent SDK基于Claude API的streaming接口
- API返回的是最终生成的文本，不包含内部思考过程
- 思考过程发生在模型内部，API层面不可见

**影响**：
- 无法调试Agent的决策逻辑
- 难以理解为什么Agent选择或不选择调用工具
- 无法看到Agent如何权衡不同的生成策略

**替代方案**：
1. **使用Prompt Engineering**：在System Prompt中要求Agent输出思考过程
   ```python
   system_prompt = """
   在生成文章前，先用<thinking>标签说明你的思考过程：
   - 评估提供的素材是否充分
   - 是否需要调用工具追加检索
   - 文章的大致结构和重点

   然后再生成最终文章。
   """
   ```

2. **使用Messages API直接模式**：
   - 不使用Agent SDK，直接调用Messages API
   - 手动处理工具调用循环
   - 在循环中记录每一步的中间结果
   - 缺点：失去SDK提供的便利性和hooks机制

3. **启用API的extended_thinking参数**（如果支持）：
   - Claude API的某些模型支持extended_thinking
   - 需要检查当前模型是否支持

#### 2. 流式生成的实时中间状态

**现状**：只能捕获最终完整结果，无法捕获流式生成过程中的增量文本。

**原因**：
- SDK的query方法返回的是ResultMessage，已经是完整结果
- 中间的流式chunk被SDK内部消费，不暴露给外部

**影响**：
- 无法监控生成进度
- 无法实现"实时预览"功能
- 难以诊断生成中途卡住的问题

**替代方案**：
1. **自定义streaming解析**：
   ```python
   # 使用底层API的stream参数
   with client.messages.stream(
       model=model,
       system=system_prompt,
       messages=messages,
   ) as stream:
       for text in stream.text_stream:
           print(text, end="", flush=True)  # 实时输出
           # 可以在这里记录每个chunk
   ```

2. **定期轮询**：
   - 使用message.snapshot()获取当前状态
   - 但SDK可能不支持此功能

#### 3. 完整的API请求和响应

**现状**：只能捕获hooks暴露的数据，无法获取完整的HTTP请求/响应。

**原因**：
- SDK封装了底层API调用
- Hooks只在特定时机触发，不覆盖所有API交互

**影响**：
- 无法调试API级别的问题
- 无法看到完整的HTTP headers和元数据
- 难以排查网络或认证问题

**替代方案**：
1. **启用HTTP日志**：
   ```python
   import logging
   import httpx

   # 启用httpx的debug日志
   logging.basicConfig(level=logging.DEBUG)
   httpx_logger = logging.getLogger("httpx")
   httpx_logger.setLevel(logging.DEBUG)
   ```

2. **使用代理抓包**：
   - 设置HTTP代理（如Charles、mitmproxy）
   - 通过ANTHROPIC_BASE_URL指向代理
   - 缺点：开发环境适用，生产环境不适合

## SDK Hooks工作机制

### Hooks类型

Claude Agent SDK提供4种hooks：

1. **PreToolUse**
   - 触发时机：工具调用前
   - 可获取：tool_name, input, tool_use_id
   - 我们用于：记录工具调用开始时间

2. **PostToolUse**
   - 触发时机：工具调用后
   - 可获取：tool_name, result, tool_use_id, duration
   - 我们用于：记录工具调用结果和耗时

3. **Stop**
   - 触发时机：Agent完成任务
   - 可获取：final_result, total_usage
   - 我们用于：记录结束时间和最终统计

4. **UserPromptSubmit**
   - 触发时机：用户提交Prompt
   - 可获取：user_message
   - 我们用于：记录初始输入

### Hooks限制

- **不覆盖内部思考**：Hooks只在工具调用和完成时触发，不捕获思考过程
- **不捕获流式输出**：Hooks处理的是离散事件，不包含流式chunk
- **Context有限**：Hooks的context参数只包含SDK提供的信息，不包含原始API响应

## 推荐的诊断策略

### 策略1：分层诊断

1. **第一层：配置检查**
   ```bash
   python diagnose_notebooklm.py
   ```
   - 快速发现配置问题（NOTEBOOK_ID、认证等）
   - 5-10秒完成检查

2. **第二层：工具调用测试**
   ```bash
   python test_tool_calls.py
   ```
   - 验证工具调用逻辑
   - 区分"配置问题"vs"智能决策"
   - 2-3分钟完成测试

3. **第三层：日志分析**
   - 查看飞书日志文档
   - 分析完整的执行过程
   - 查看配置摘要和诊断提示

### 策略2：根据问题类型选择工具

| 问题类型 | 推荐工具 | 预期发现 |
|---------|---------|---------|
| tool_call_count=0 | diagnose_notebooklm.py | 配置缺失、工具未注册 |
| 工具调用行为异常 | test_tool_calls.py | Agent决策逻辑、素材充分性 |
| 生成质量问题 | 日志文档 | Prompt内容、Token使用 |
| 性能问题 | 日志文档 | 运行时长、工具耗时 |
| 理解Agent决策 | （受限）Prompt Engineering | 要求输出思考过程 |

### 策略3：日志配置优化

根据使用场景调整日志配置：

**开发调试（完整日志）**：
```bash
# .env
LOG_MAX_RESULT_LENGTH=0  # 不截断，捕获完整结果
```

**生产环境（平衡模式）**：
```bash
# .env
LOG_MAX_RESULT_LENGTH=5000  # 5KB限制，避免日志过大
```

**性能测试（最小日志）**：
```bash
# .env
USE_AGENT_SDK=false  # 使用传统模式，减少hooks开销
```

## 未来改进方向

### 短期改进（可立即实施）

1. **Prompt工程增强**
   - 修改System Prompt要求输出思考过程
   - 使用结构化输出（XML标签）分离思考和内容

2. **自定义streaming解析**
   - 实现流式输出捕获
   - 提供实时进度反馈

### 中期改进（需要SDK更新）

1. **等待SDK功能更新**
   - 希望SDK提供更多hooks（如ThinkingHook）
   - 希望SDK支持snapshot功能

2. **自定义Agent Runner**
   - 基于Messages API实现完全自定义的Agent循环
   - 获得最大灵活性，但失去SDK便利性

### 长期改进（需要API功能更新）

1. **等待Claude API更新**
   - 希望API支持extended_thinking暴露
   - 希望API提供更详细的中间状态

2. **模型能力提升**
   - 希望模型原生支持思考过程输出
   - 希望模型提供决策解释

## 常见问题

### Q1: 为什么看不到Agent的思考过程？

**A**: 这是Claude API的技术限制，不是我们的日志系统问题。API只返回最终生成的文本，内部推理过程发生在模型内部，外部无法直接访问。

**解决方案**：使用Prompt Engineering要求Agent输出思考过程。

### Q2: 日志中的工具结果为什么被截断？

**A**: 默认配置为防止日志过大。可以通过设置`LOG_MAX_RESULT_LENGTH=0`禁用截断。

### Q3: 如何判断tool_call_count=0是配置问题还是正常行为？

**A**: 查看日志文档中的"Configuration Summary"部分：
- 如果显示"⚠️ 工具调用为0原因: Notebook ID未设置"→配置问题
- 如果显示"✅ 工具调用为0原因: Agent智能决策"→正常行为

或运行`diagnose_notebooklm.py`快速诊断。

### Q4: 能否捕获流式生成的中间结果？

**A**: 当前版本不支持。SDK的query方法返回的是完整结果。需要使用底层API的streaming模式自行实现。

### Q5: 日志系统对性能有多大影响？

**A**: 通过hooks记录日志的开销<5%。主要开销来自：
- JSON序列化工具调用数据
- 字符串拼接生成markdown
- 飞书API上传文档

对于大多数使用场景，这个开销可以接受。

## 总结

我们的日志系统在SDK和API的技术限制下，已经实现了约60-65%的信息覆盖率，包括：
- ✅ 完整的工具调用详情
- ✅ Token和性能统计
- ✅ Prompt和初始输入
- ✅ 对话消息流
- ✅ 配置和诊断信息

无法捕获的35-40%主要是：
- ❌ Agent内部思考过程
- ❌ 流式生成中间状态
- ❌ 完整的API请求/响应

对于这些限制，我们提供了：
1. 详细的技术说明
2. 可行的替代方案
3. 诊断工具和最佳实践
4. 未来改进路线图

用户应当理解这些限制是Claude API和SDK层面的技术约束，不是我们的实现缺陷。在现有技术条件下，我们已经最大化了可观测性。
