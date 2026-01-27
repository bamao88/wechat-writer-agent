# 架构

**分析日期:** 2026-01-27

## 模式概述

**整体:** 管道/编排器模式 + 功能开关

**关键特征:**
- 四阶段内容生产管道,关注点清晰分离
- 可插拔的后端实现(Anthropic SDK vs Claude Agent SDK)
- 在编排层基于功能标志的决策路由
- 通过专用适配器模块与外部服务集成
- 通过基于钩子的仪器进行指标收集和日志记录

## 分层

**编排层:**
- 目的: 协调四阶段管道,管理重试和控制功能开关
- 位置: `src/main.py`
- 包含: `run_pipeline()` 函数,包含重试逻辑、错误处理策略和条件执行路径
- 依赖: 所有其他模块(retrieval, generator, feishu_doc, feishu_table)
- 使用者: `writer_agent.py`(交互式 agent)和外部 CLI 脚本

**检索层:**
- 目的: 查询 NotebookLM 知识库获取素材
- 位置: `src/modules/retrieval.py`
- 包含: 对 NotebookLM skill 的外部子进程调用;认证/笔记本未找到的错误处理
- 依赖: 通过子进程的外部 NotebookLM skill
- 使用者: 生成层(在生成期间,而非管道开始时)

**生成层:**
- 目的: 使用 Claude API 生成文章,可选 SDK 集成
- 位置: `src/modules/generator.py`
- 包含: 两种实现 - `generate()`(Anthropic SDK) 和 `generate_with_sdk()`(Claude Agent SDK);提示词管理;文章解析
- 依赖: Retrieval(用于生成期间的额外查询)、agent_sdk(可选)、log_generator、temperature validator
- 使用者: 编排层

**集成适配器层:**
- 目的: 处理外部服务通信
- 位置: `src/modules/feishu_doc.py`, `src/modules/feishu_table.py`
- 包含: 飞书 API 客户端、token 管理、Markdown 到块的转换、字段验证
- 依赖: Token 管理器、HTTP 请求库
- 使用者: 编排层(阶段 3-4)

**仪器层:**
- 目的: 捕获基于 SDK 执行的指标和日志
- 位置: `src/hooks/logging_hooks.py`, `src/hooks/log_generator.py`
- 包含: pre/post 工具使用、停止事件的钩子实现;markdown 日志生成
- 依赖: AgentRunMetrics 数据结构
- 使用者: agent_sdk(注册钩子)、generator(生成 markdown 日志)

**模型层:**
- 目的: 定义阶段间的数据契约
- 位置: `src/models.py`
- 包含: SearchResult、Article、DocResult、PipelineResult dataclasses
- 依赖: 无(纯数据定义)
- 使用者: 所有其他层

## 数据流

**阶段 1 - 检索:**

1. 编排器调用 `retrieval.search(topic, notebook_id, notebook_url)`
2. Retrieval 生成子进程到 NotebookLM skill
3. NotebookLM 返回 SearchResult 列表
4. 结果传递到阶段 2;如果检索失败则为空列表

**阶段 2 - 生成(两条路径):**

**路径 A (USE_AGENT_SDK=false):**
1. `generator.generate()` 接收主题 + 搜索结果
2. 使用预检索内容构建系统提示词 + 用户消息
3. 使用 NotebookLM 的工具定义调用 Anthropic 客户端
4. Agent 循环: 处理 tool_use 响应,如需要调用检索
5. 从最终响应中提取文章
6. 返回 Article 对象(无指标)

**路径 B (USE_AGENT_SDK=true):**
1. `generator.generate_with_sdk()` 接收主题 + 搜索结果
2. 创建 AgentSDKRunner 实例
3. 注册钩子(pre_tool_use_hook, post_tool_use_hook, stop_hook)
4. 使用系统提示词和用户消息调用 `runner.generate()`
5. SDK 执行 agent 循环,钩子捕获工具调用和指标
6. LogDocumentGenerator 将指标转换为 markdown 日志
7. 返回包含 log_markdown 的 (Article, metrics_dict) 元组

**阶段 3 - 飞书文档:**

1. 如果 enable_feishu=true 且提供了 folder_token:
2. `feishu_doc.create_doc()` 从飞书 API 获取租户访问令牌
3. MarkdownToBlockConverter 将文章内容转换为飞书块
4. 调用飞书 API 创建文档并写入内容块
5. 返回带有 doc_url 的 DocResult
6. 如果存在指标,也创建日志文档

**阶段 4 - 飞书表格:**

1. 如果阶段 3 成功且 enable_feishu=true:
2. 使用必需字段构建 record_fields 字典(topic, doc_url, timestamp, status)
3. 如果使用 SDK,可选添加指标字段(runtime_seconds, tool_call_count 等)
4. `feishu_table.insert_record()` 验证字段(必需、类型、枚举)
5. 调用飞书 API 将记录插入多维表格
6. 返回 record_id

**状态管理:**
- 每个阶段维护独立状态: search_results, article, doc_result, record_id
- 阶段 3-4 的失败是非致命的;如果文档或表格写入失败,管道仍会完成
- 阶段 2 的失败是致命的(文章生成是必需的)
- 重试逻辑仅适用于阶段 1 和 3

## 关键抽象

**Pipeline:**
- 目的: 定义完整的内容生产工作流
- 示例: `src/main.py` 中的 `run_pipeline()`
- 模式: 带错误处理器的线性四阶段编排器

**Article:**
- 目的: 表示生成的内容
- 示例: `src/models.py::Article`(title, content, source_summary)
- 模式: 简单的 dataclass 契约

**AgentSDKRunner:**
- 目的: 封装带指标收集的 Claude Agent SDK 执行
- 示例: `src/modules/agent_sdk.py::AgentSDKRunner`
- 模式: 初始化 SDK 客户端并使用钩子执行的包装类

**FeishuTokenManager:**
- 目的: 缓存和刷新飞书 API tokens
- 示例: `src/modules/feishu_doc.py::FeishuTokenManager`
- 模式: 带到期刷新逻辑的全局 token 缓存

**MarkdownToBlockConverter:**
- 目的: 将 Markdown 转换为飞书文档块格式
- 示例: `src/modules/feishu_doc.py::MarkdownToBlockConverter`
- 模式: 带标题、列表、代码解析规则的无状态转换器

## 入口点

**CLI 入口(交互式 Agent):**
- 位置: `main.py`(项目根目录)
- 触发: `python main.py`
- 职责: 加载环境,创建 WechatWriterAgent,启动交互循环

**管道入口(批处理模式):**
- 位置: `src/main.py::run_pipeline()`
- 触发: 由编排器脚本或 writer_agent 调用
- 职责: 执行带重试逻辑和指标收集的四阶段管道

**Writer Agent 入口(高级 API):**
- 位置: `writer_agent.py::WechatWriterAgent`
- 触发: 由外部代码或 CLI 实例化
- 职责: 管理对话状态,协调管道调用,处理用户交互

## 错误处理

**策略:** 对非关键阶段采用容错和非致命降级

**模式:**
- **检索失败:** 重试 max_retries 次;最终失败时,继续使用空结果并标记为"无检索结果"
- **生成失败:** 致命;向调用者抛出 RuntimeError
- **文档创建失败:** 重试 max_retries 次;最终失败时,记录警告但继续(doc_result=None)
- **表格插入失败:** 非致命;记录错误但返回(record_id=None);管道成功完成
- **字段验证失败:** 立即抛出 ValueError
- **Token 获取失败:** 带有帮助消息的 RuntimeError(未实现功能为 NotImplementedError)

## 横切关注点

**日志记录:**
- 进度的 Print 语句(管道阶段)
- 基于钩子的指标捕获(仅 SDK 模式)
- LogDocumentGenerator 从指标创建 markdown 日志

**验证:**
- temperature.py 中的温度参数验证
- feishu_table.py 中的必需字段验证
- 入口点的 API Key 存在性检查

**认证:**
- 飞书 token 管理器处理 OAuth 流程和缓存
- 通过环境变量的 Anthropic API 密钥
- 通过外部脚本的 NotebookLM skill 认证

---

*架构分析: 2026-01-27*
