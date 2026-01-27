# 微信公众号文章撰写 Agent

## What This Is

基于个人知识库（NotebookLM）的智能文章生成系统。给定选题后，Agent 自主查询混合知识库（个人经历 + 专业资料），通过多轮智能检索生成符合个人观点和风格的高质量公众号文章，并完整记录到飞书。

## Core Value

Agent 能在写作过程中智能决策何时查询知识库，实现真正的"知识驱动写作"——不是简单的素材堆砌，而是基于个人知识沉淀的深度内容创作。

## Requirements

### Validated

<!-- 从现有代码推断的已工作能力 -->

- ✓ 四阶段内容生产管道（检索-生成-文档-表格） — existing
- ✓ NotebookLM 手动检索功能（`retrieval.search()`） — existing
- ✓ 双模式文章生成（传统模式 + SDK 模式） — existing
- ✓ 飞书云文档存储集成 — existing
- ✓ 飞书多维表格记录集成 — existing
- ✓ 提示词版本管理（`write_prompt/` 目录） — existing
- ✓ 日志和指标收集框架（hooks 系统） — existing
- ✓ Markdown 到飞书 Block 格式转换 — existing
- ✓ 飞书 Token 管理和缓存 — existing

### Active

<!-- 当前要修复/实现的功能 -->

- [ ] **AGENT-01**: Agent SDK 工具调用机制修复 - Agent 能在生成时自动调用 NotebookLM 工具
- [ ] **RETR-01**: 预检索功能实现 - Pipeline 阶段 1 自动检索初始素材
- [ ] **RETR-02**: 按需检索功能验证 - Agent 在写作过程中智能决策何时查询
- [ ] **LOG-01**: 工具调用日志非零验证 - tool_call_count 正确反映实际调用次数
- [ ] **INT-01**: 完整管道测试 - 端到端验证：预检索 → 智能生成 → 飞书存储

### Out of Scope

- 实时协作编辑 — 单人使用工具，不需要多人同时编辑
- 自动发布到微信公众号 — 仅生成文章，发布由人工完成
- 多用户/团队管理 — 个人工具，无需用户系统
- 文章版本历史 — 飞书本身有版本管理
- AI 模型训练/微调 — 使用现成的 Claude 模型
- 实时流式输出 — 完整生成后一次性返回即可

## Context

### 技术环境

- **LLM**: 使用 MiniMax API（Anthropic 兼容接口），模型 MiniMax-M2.1
- **知识库**: Google NotebookLM，通过 Claude skill 系统本地集成
- **输出平台**: 飞书开放平台 API（云文档 + 多维表格）
- **开发环境**: macOS, Python 3.13.3, 虚拟环境

### 现有代码状态

基础管道已实现但有关键 bug：
- 检索模块手动可用，但 Agent 从不自动调用（tool_call_count 始终为 0）
- 双模式生成都能工作，但 SDK 模式的智能工具调用失效
- 飞书集成基本完成，能存储文档和记录元数据
- 日志系统框架完整，但因工具不被调用而无有效数据

### 知识库内容

NotebookLM 中存储混合知识库：
- 个人经历、思考、笔记、案例（个人观点来源）
- 行业报告、研究论文、最佳实践（专业知识支撑）

### 已知技术债务

从代码库分析发现的关键问题：
1. **Agent SDK 工具调用失效** (CRITICAL) - 核心功能不工作
2. 密钥暴露在 .env 文件中 - 安全风险
3. 全局 token 缓存不线程安全 - 并发问题
4. 子进程调用 NotebookLM 性能开销大 - 3-5秒/次

## Constraints

- **技术栈**: 必须使用 Python 3.13 + Claude SDK + NotebookLM + 飞书 API
- **API 端点**: 使用 MiniMax 的 Anthropic 兼容接口（已配置）
- **依赖外部 Skill**: 需要 `~/.claude/skills/notebooklm/` 正确安装和认证
- **网络访问**: 需要访问 MiniMax API、飞书开放平台、Google NotebookLM
- **单用户**: 个人工具，无需考虑多用户并发
- **同步执行**: 管道顺序执行，无需异步优化

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 使用 SDK 模式（而非传统模式） | 需要完整的工具调用日志和指标收集 | — Pending |
| 预检索 + 按需检索双阶段 | 既提供初始素材，又允许 Agent 智能追查 | — Pending |
| 混合知识库设计 | 结合个人见解和专业知识，生成独特内容 | — Pending |
| 四阶段管道架构 | 清晰分离关注点，易于调试和扩展 | ✓ Good |
| 飞书作为输出平台 | 团队协作友好，支持文档和数据表格 | ✓ Good |

---
*Last updated: 2026-01-27 after initialization*
