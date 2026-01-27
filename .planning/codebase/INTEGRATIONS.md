# 外部集成

**分析日期:** 2026-01-27

## APIs 与外部服务

**LLM 提供商:**
- MiniMax / Anthropic 兼容 API - 使用 Claude 模型进行内容生成
  - SDK/客户端: `anthropic` 包
  - 认证: `ANTHROPIC_API_KEY` (环境变量)
  - 端点: 通过 `ANTHROPIC_BASE_URL` 可配置 (默认为 Anthropic 端点)
  - 模型: `ANTHROPIC_MODEL` 环境变量
  - 用途: 使用多轮 agent 循环和工具调用进行文章生成

**Google NotebookLM:**
- 通过 Claude 技能系统集成 (`~/.claude/skills/notebooklm/`)
- 实现: 使用 `retrieval.search()` 本地子进程执行
- 认证: 由本地 NotebookLM 技能处理 (需要通过 `auth_manager.py setup` 设置认证)
- 用途: 知识库搜索和检索文章上下文
- 位置: `src/modules/retrieval.py`
- 支持的模式:
  - 通过笔记本 URL 查询: `--notebook-url`
  - 通过笔记本 ID 查询: `--notebook-id`
  - 如果未提供则自动检测活动笔记本

**飞书开放 APIs:**
- Tenant Access Token API - 认证
  - 端点: `https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal`
  - 客户端: `requests` 库
  - 认证: App ID 和 App Secret (`FEISHU_APP_ID`, `FEISHU_APP_SECRET`)
  - 令牌缓存: 2小时默认过期时间, 带100秒缓冲
  - 位置: `src/modules/feishu_doc.py:FeishuTokenManager`

- Document API (云文档)
  - 端点: `https://open.feishu.cn/open-apis/docx/v1/documents`
  - 方法: POST 创建文档
  - 认证: Tenant Access Token API 的 Bearer 令牌
  - 用途: 创建云文档并写入文章内容
  - 块格式: Markdown 转换为飞书块结构
  - 重试逻辑: 针对 429 (限流) 响应的指数退避
  - 位置: `src/modules/feishu_doc.py:create_doc()`

- Bitable (多维表格) API
  - 端点: `https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records`
  - 方法: POST 插入记录
  - 认证: Tenant Access Token API 的 Bearer 令牌
  - 用途: 存储文章元数据 (标题、链接、时间戳、状态)
  - 可选字段: 运行时指标、令牌使用量、工具调用次数、日志文档 URL
  - 必需字段: `选题名称` (主题), `文章链接` (文章链接), `创建时间` (时间戳), `状态` (状态)
  - 位置: `src/modules/feishu_table.py:insert_record()`

## 数据存储

**数据库:**
- 未检测到 - 应用程序是无状态的, 仅使用外部服务

**文件存储:**
- 飞书云文档 (`feishu_doc.py`)
  - 在飞书工作区存储文章内容
  - Markdown 转换为基于块的格式
  - 返回文档 URL 供参考

- 本地文件系统 (日志)
  - 日志文件存储在 `logs/` 目录
  - 格式: Markdown (LogDocumentGenerator 生成的 .md 文件)
  - 可选上传到飞书云文档

**缓存:**
- 内存令牌缓存 (模块级 `_token_cache`)
  - 位置: `src/modules/feishu_doc.py`
  - 持续时间: 2小时 (通过 API 响应可配置)
  - 缓冲: 刷新前100秒安全边距
  - 策略: `get_token()` 调用时惰性刷新

## 认证与身份

**认证提供商:**

**飞书:**
- 实现: OAuth 2.0 应用程序凭证
  - 类型: 内部应用认证 (tenant_access_token)
  - 凭证: App ID + App Secret (环境变量)
  - 令牌端点: `https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal`
  - 令牌生命周期: ~2小时 (7200秒)
  - 位置: `src/modules/feishu_doc.py:FeishuTokenManager`

**Anthropic/MiniMax:**
- 实现: API 密钥认证
  - 头部: `Authorization: Bearer {API_KEY}`
  - 管理: `anthropic` SDK
  - 环境变量: `ANTHROPIC_API_KEY`

**NotebookLM:**
- 实现: 通过 Claude 技能本地凭证存储
  - 设置: `~/.claude/skills/notebooklm/scripts/run.py auth_manager.py setup`
  - 范围: 每台机器认证, 由技能系统缓存
  - 位置: `src/modules/retrieval.py`

## 监控与可观测性

**错误跟踪:**
- 未检测到 - 应用程序将错误记录到控制台并抛出异常

**日志:**
- 控制台输出: 进度指示器、步骤摘要、错误消息
  - 位置: `src/main.py:run_pipeline()` (打印状态)
- 本地文件: `logs/` 目录中的 Markdown 日志
  - 生成者: `src/hooks/log_generator.py:LogDocumentGenerator`
  - 内容: 执行摘要、工具调用、指标、配置
  - 可选: 通过 `feishu_doc.create_doc()` 上传到飞书云文档

**指标收集:**
- Agent SDK 钩子: `src/hooks/logging_hooks.py`
  - Pre-tool-use hook: 捕获工具调用详情
  - Post-tool-use hook: 捕获工具结果
  - Stop hook: 最终执行状态
  - User prompt submit hook: 初始用户消息
- 跟踪的指标: `src/modules/agent_sdk.py:AgentRunMetrics`
  - 运行时持续时间 (秒)
  - 使用的总令牌数
  - 提示令牌 / 完成令牌
  - 工具调用次数
  - 系统提示词和初始用户消息
  - 完整消息历史

## CI/CD 与部署

**托管:**
- 非云托管 - 本地 CLI 应用程序
- 可以容器化 (Docker) 进行部署
- 支持作为计划任务或手动调用运行

**CI 管道:**
- 未检测到 - 无 GitHub Actions 或 CI 配置文件
- 测试框架: pytest 在 `pytest.ini` 中配置

## 环境配置

**完整功能所需的环境变量:**
- `ANTHROPIC_API_KEY` - LLM 提供商 API 密钥 (关键)
- `FEISHU_APP_ID` - 飞书认证 (文档/表格操作必需)
- `FEISHU_APP_SECRET` - 飞书认证密钥 (必需)
- `FEISHU_TENANT_DOMAIN` - 飞书工作区域名 (文档 URL 必需)
- `FEISHU_BITABLE_APP_TOKEN` - 表格集成 (如果不存储记录则可选)
- `FEISHU_BITABLE_TABLE_ID` - 表格集成 (如果不存储记录则可选)

**可选环境变量:**
- `ANTHROPIC_BASE_URL` - API 路由的自定义端点 (启用 MiniMax 兼容性)
- `ANTHROPIC_MODEL` - 模型选择 (默认为 `MiniMax-M2.1`)
- `NOTEBOOK_ID` / `NOTEBOOK_URL` - NotebookLM 知识库 (检索可选)
- `NOTEBOOK_NAME` - 笔记本显示名称 (默认: `my_knowledge`)
- `USE_AGENT_SDK` - 启用带完整日志的 agent 模式 (默认: `true`)
- `PROMPT_VERSION` - 提示词模板版本 (默认: `write_prompt/` 目录中的 `V1`)
- `LOG_MAX_RESULT_LENGTH` - 工具结果截断 (默认: `0` = 无限制)

**密钥位置:**
- `.env` 文件 (本地, 不应提交)
- 参考: `.env.example` (可安全提交)

## Webhooks 与回调

**传入:**
- 不适用 - 应用程序是拉取式的, 非事件驱动

**传出:**
- 无 - 所有操作都是直接 API 调用

## API 限流与节流

**飞书 APIs:**
- 限流响应: HTTP 429
- 重试策略: 指数退避 (2^attempt 秒)
- 最大重试: 3次限流尝试
- 退避延迟: 尝试1、2、3分别为1秒、2秒、4秒
- 位置: `src/modules/feishu_doc.py` (行 308-314, 405-410)

**Anthropic API:**
- 由 `anthropic` SDK 管理 (应用程序代码中无显式重试)

**NotebookLM:**
- 查询超时: 180秒 (3分钟)
- 位置: `src/modules/retrieval.py:search()` (行 63)

## 集成数据流

**内容生成管道:**
1. **检索** → 通过子进程访问 NotebookLM (`retrieval.search()`)
2. **生成** → Anthropic API 并可选地回调 NotebookLM 工具 (`generator.generate()`)
3. **文档创建** → 飞书云文档 API (`feishu_doc.create_doc()`)
4. **记录插入** → 飞书 Bitable API (`feishu_table.insert_record()`)
5. **日志归档** → 可选上传到飞书云文档

---

*集成审计: 2026-01-27*
