# 需求规格: 微信公众号文章撰写 Agent

**定义日期:** 2026-01-27
**核心价值:** Agent 能在写作过程中智能决策何时查询知识库

## v0.1 需求

里程碑 v0.1 的需求,每个需求对应路线图的阶段。

### 工具注册配置

- [x] **TOOL-01**: Agent SDK 正确配置 `setting_sources` 参数以启用 Skill 加载
- [x] **TOOL-02**: Agent SDK 使用 `allowed_tools` 参数(不是 `tools`)注册 NotebookLM 工具
- [x] **TOOL-03**: 添加 `claude-agent-sdk>=0.1.23` 到项目依赖
- [x] **TOOL-04**: SDK 启动时能成功发现并注册 NotebookLM 工具

### 工具调用验证

- [x] **VAL-01**: Agent 在需要知识时自动调用 NotebookLM 工具(不是手动调用)
- [x] **VAL-02**: 日志系统正确记录 tool_call_count > 0(不再是永远为 0)
- [x] **VAL-03**: 工具调用日志包含工具名称、调用时机、返回结果摘要
- [x] **VAL-04**: 可以通过测试验证工具确实被调用(不是假阳性)

### 错误处理和日志

- [ ] **ERR-01**: 子进程调用 NotebookLM 失败时有明确错误信息
- [ ] **ERR-02**: NotebookLM 查询超时(>10秒)时有超时处理
- [ ] **ERR-03**: 工具调用失败时 Agent 能优雅降级(不崩溃)
- [ ] **ERR-04**: 日志系统记录工具调用的完整生命周期(注册、调用、响应、错误)

### MiniMax API 兼容性

- [x] **API-01**: 验证 MiniMax API 的 tool use 协议兼容性
- [x] **API-02**: 确认 MiniMax API 正确处理工具定义和调用
- [x] **API-03**: 测试 MiniMax API 的会话历史格式要求
- [ ] **API-04**: 记录 MiniMax API 与官方 Anthropic API 的差异

## v0.2 需求(后续里程碑)

推迟到未来版本的功能。

### 检索功能

- **RETR-01**: 预检索功能实现 - Pipeline 阶段 1 自动检索初始素材
- **RETR-02**: 按需检索功能验证 - Agent 在写作过程中智能决策何时查询
- **RETR-03**: 多轮检索支持 - Agent 可以根据生成结果追加查询

### 端到端集成

- **INT-01**: 完整管道测试 - 端到端验证:预检索 → 智能生成 → 飞书存储
- **INT-02**: 性能优化 - 减少 NotebookLM 子进程调用开销(当前 3-5秒/次)

## 范围外功能

明确排除的功能,记录原因以防范围蔓延。

| 功能 | 原因 |
|------|------|
| 多工具并行调用 | v0.1 只有一个工具,不需要并行 |
| 工具调用缓存 | 优化性能,但不影响核心功能验证 |
| 替换子进程为原生集成 | 现有 Skill 架构可用,不需要重构 |
| 流式工具响应 | NotebookLM 查询本身需要完整结果 |
| 工具调用重试机制 | 简单失败处理即可,高级重试延后 |

## 需求追溯

需求到阶段的映射。

| 需求 | 阶段 | 状态 |
|------|------|------|
| TOOL-01 | 阶段 1 | Complete |
| TOOL-02 | 阶段 1 | Complete |
| TOOL-03 | 阶段 1 | Complete |
| TOOL-04 | 阶段 1 | Complete |
| API-01 | 阶段 1 | Complete |
| API-02 | 阶段 1 | Complete |
| VAL-01 | 阶段 2 | Complete |
| VAL-02 | 阶段 2 | Complete |
| VAL-03 | 阶段 2 | Complete |
| VAL-04 | 阶段 2 | Complete |
| API-03 | 阶段 2 | Complete |
| ERR-01 | 阶段 3 | Pending |
| ERR-02 | 阶段 3 | Pending |
| ERR-03 | 阶段 3 | Pending |
| ERR-04 | 阶段 3 | Pending |
| API-04 | 阶段 3 | Pending |

**覆盖率:**
- v0.1 需求: 16 个
- 已映射到阶段: 16 个 ✓
- 未映射: 0

---
*需求定义于: 2026-01-27*
*最后更新: 2026-01-28 - 阶段 1-2 完成*
