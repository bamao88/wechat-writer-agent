# 技术栈

**分析日期:** 2026-01-27

## 编程语言

**主要语言:**
- Python 3.13.3 - 所有核心应用逻辑、模块和工具

## 运行时环境

**环境:**
- Python 3.13.3
- 虚拟环境: `.venv/` 目录(已存在)

**包管理器:**
- pip - Python 包管理
- 锁文件: 未检测到(使用 requirements.txt 而非锁文件)

## 框架

**核心框架:**
- Anthropic SDK (`anthropic>=0.39.0`) - 使用 Claude 模型进行文章生成的 LLM 集成
- Claude Agent SDK (`claude_agent_sdk`) - 支持工具调用和钩子的 Agent 框架,用于 NotebookLM 集成
- python-dotenv (`>=1.0.0`) - 环境配置加载

**测试框架:**
- pytest (`>=7.4.0`) - 测试框架和运行器
- pytest-timeout (`>=2.1.0`) - 测试执行超时控制
- pytest-mock (`>=3.11.0`) - Mock 和 fixture 支持
- pytest-cov (`>=4.1.0`) - 测试覆盖率报告

**HTTP/网络:**
- requests (`>=2.31.0`) - 用于飞书 API 调用和外部集成的 HTTP 客户端

## 关键依赖

**核心依赖:**
- `anthropic>=0.39.0` - 通过 MiniMax 或 Claude API 提供 Anthropic 客户端进行 LLM 推理
  - 支持自定义 base_url 进行 API 路由
  - 支持工具调用的 agentic 工作流
  - 支持消息流式传输

- `requests>=2.31.0` - 向飞书 API 发送 HTTP 请求
  - Token 刷新和缓存
  - Markdown 到飞书 Block 格式转换
  - 带重试逻辑的错误处理

- `claude_agent_sdk` - 用于结构化工具调用的本地 Agent SDK
  - 日志记录的钩子系统(pre_tool_use, post_tool_use, stop_hook, user_prompt_submit_hook)
  - 支持 NotebookLM 工具集成
  - 指标收集(tokens, runtime, tool calls)

- `python-dotenv>=1.0.0` - 配置管理
  - 从 .env 文件加载密钥和模型配置
  - 环境变量默认值

**测试基础设施:**
- `pytest>=7.4.0` - 主测试运行器
- `pytest-timeout>=2.1.0` - 超时强制执行
- `pytest-mock>=3.11.0` - Mock fixtures 和工具
- `pytest-cov>=4.1.0` - 覆盖率分析

## 配置

**环境变量:**
使用 `python-dotenv` 从 `.env` 文件加载环境变量:

**LLM 配置:**
- `ANTHROPIC_API_KEY` - MiniMax 或 Claude API 的 API 密钥
- `ANTHROPIC_BASE_URL` - 自定义 API 端点(例如 MiniMax 使用 `https://api.minimaxi.com/anthropic`)
- `ANTHROPIC_MODEL` - 模型标识符(默认: `MiniMax-M2.1`)

**NotebookLM 配置:**
- `NOTEBOOK_URL` - NotebookLM 笔记本的完整 URL
- `NOTEBOOK_ID` - 用于 API 调用的笔记本标识符
- `NOTEBOOK_NAME` - 笔记本显示名称(默认: `my_knowledge`)

**飞书集成:**
- `FEISHU_APP_ID` - 用于认证的飞书应用 ID
- `FEISHU_APP_SECRET` - 飞书应用密钥
- `FEISHU_TENANT_DOMAIN` - 用于构建文档 URL 的租户域名
- `FEISHU_FOLDER_TOKEN` - 云文档文件夹 token
- `FEISHU_BITABLE_APP_TOKEN` - 多维表格应用 token
- `FEISHU_BITABLE_TABLE_ID` - 用于记录插入的特定表 ID

**Agent 配置:**
- `USE_AGENT_SDK` - 启用/禁用 Claude Agent SDK 模式的功能标志(默认: `true`)
- `LOG_MAX_RESULT_LENGTH` - 工具结果截断长度(0 或空 = 不截断)
- `PROMPT_VERSION` - 要使用的提示词文件版本(例如 `write_prompt/` 目录中的 `V1`, `V2`)

**构建:**
- pytest.ini: `testpaths = tests`, `minversion = 7.0`
- 无构建系统(纯 Python,无需编译)

## 平台要求

**开发环境:**
- macOS 或 Linux(使用 subprocess 执行 NotebookLM skill)
- Python 3.13.3 或兼容版本
- 虚拟环境(推荐)
- Git(用于 NotebookLM skill 安装: `~/.claude/skills/notebooklm`)

**生产环境:**
- Python 3.13.3+
- 标准 HTTP 访问外部 API
  - Anthropic/MiniMax API 端点
  - 飞书开放平台 API (`https://open.feishu.cn/open-apis/`)
  - Google NotebookLM(通过本地 skill 集成)
- 访问本地 NotebookLM skill 安装(`~/.claude/skills/notebooklm/`)

**外部服务依赖:**
- 启用了云文档和多维表格的飞书工作区
- 具有适当权限的飞书应用凭据
- 已创建和认证的 NotebookLM 笔记本
- 具有配额的 Anthropic/MiniMax API 账户

---

*技术栈分析: 2026-01-27*
