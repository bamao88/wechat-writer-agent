# 代码库结构

**分析日期:** 2026-01-27

## 目录布局

```
wechat-writer-agent/
├── src/                           # 核心库代码
│   ├── __init__.py               # 包标记
│   ├── main.py                   # 管道编排器(227 行)
│   ├── models.py                 # 数据契约
│   ├── modules/                  # 功能模块
│   │   ├── __init__.py          # 模块导入
│   │   ├── retrieval.py         # NotebookLM 集成(124 行)
│   │   ├── generator.py         # 文章生成(393 行)
│   │   ├── agent_sdk.py         # Claude SDK 包装器(250 行)
│   │   ├── feishu_doc.py        # 飞书文档 API(438 行)
│   │   └── feishu_table.py      # 飞书多维表格 API(231 行)
│   ├── hooks/                    # 仪器化
│   │   ├── __init__.py
│   │   ├── logging_hooks.py     # SDK 生命周期钩子(126 行)
│   │   └── log_generator.py     # Markdown 日志生成(169 行)
│   └── utils/                    # 工具函数
│       ├── __init__.py
│       └── temperature.py        # 参数验证(30 行)
├── tests/                        # 测试套件
│   ├── test_setup.py
│   ├── test_generator.py
│   ├── test_generator_sdk.py
│   ├── test_agent_sdk_runner.py
│   ├── test_log_generator.py
│   ├── test_feishu_doc.py
│   ├── test_feishu_table_real.py
│   ├── test_writer_agent.py
│   └── ... (14+ 测试文件)
├── docs/                         # 文档
│   ├── README.md
│   ├── skills.md
│   ├── agent_logs.md
│   └── ... (项目文档)
├── write_prompt/                 # 提示词版本
│   ├── V1.md
│   └── V2_example.md
├── logs/                         # 运行时日志(生成)
├── .planning/                    # GSD 规划文档
├── .venv/                        # Python 虚拟环境
├── writer_agent.py               # 高级 writer agent API(232 行)
├── main.py                       # CLI 入口点(49 行)
├── cli.py                        # 额外 CLI 工具
├── notebooklm_tool.py           # NotebookLM 工具包装器
├── pytest.ini                    # 测试配置
├── requirements.txt              # Python 依赖
├── .env.example                  # 环境变量模板
└── .gitignore                    # Git 忽略规则
```

## 目录用途

**src/**
- 用途: 包含生产代码的核心库
- 包含: 按功能组织的 Python 模块
- 关键文件: `main.py`(编排器)、`models.py`(契约)

**src/modules/**
- 用途: 功能实现
- 包含: 检索、生成、飞书集成、SDK 包装器
- 关键文件: `generator.py`(最大模块)、`feishu_doc.py`(飞书 API 客户端)

**src/hooks/**
- 用途: SDK 生命周期事件的仪器化
- 包含: 钩子实现和日志生成
- 关键文件: `logging_hooks.py`(钩子定义)、`log_generator.py`(markdown 输出)

**src/utils/**
- 用途: 共享工具和验证器
- 包含: 温度验证函数
- 关键文件: `temperature.py`(参数验证)

**tests/**
- 用途: 单元和集成测试
- 包含: 每个模块的测试文件
- 关键文件: `test_generator.py`、`test_generator_sdk.py`、`test_agent_sdk_runner.py`

**docs/**
- 用途: 项目文档
- 包含: README、指南、日志
- 关键文件: `README.md`(主文档)、`agent_logs.md`(日志指南)

**write_prompt/**
- 用途: 版本化的系统提示词
- 包含: 提示词变体和示例
- 关键文件: `V1.md`(当前)、`V2_example.md`(未来)

**logs/**
- 用途: 运行时执行日志(在运行时生成)
- 包含: 执行跟踪和指标
- 关键文件: 动态生成的 JSON/markdown 日志

**.planning/**
- 用途: GSD(目标计划交付)规划文档
- 包含: 架构、结构、约定、问题分析
- 关键文件: `ARCHITECTURE.md`、`STRUCTURE.md`、`CONVENTIONS.md`、`CONCERNS.md`

## 关键文件位置

**入口点:**
- `main.py`(项目根目录): 带环境加载的 CLI 入口点
- `writer_agent.py`: WechatWriterAgent 类的高级 API
- `src/main.py`: 用于程序化使用的管道函数

**配置:**
- `.env.example`: 环境变量模板
- `pytest.ini`: 测试运行器配置
- `requirements.txt`: Python 包依赖

**核心逻辑:**
- `src/modules/generator.py`: 带双路径的文章生成(SDK vs Anthropic)
- `src/modules/agent_sdk.py`: Claude Agent SDK 包装器和指标收集
- `src/modules/retrieval.py`: NotebookLM 子进程集成
- `src/modules/feishu_doc.py`: 飞书文档创建和 Markdown 转换
- `src/modules/feishu_table.py`: 飞书多维表格操作

**模型和契约:**
- `src/models.py`: SearchResult、Article、DocResult、PipelineResult 的 Dataclasses
- `src/modules/agent_sdk.py`: SDK 指标的 AgentRunMetrics dataclass

**测试:**
- `tests/test_generator.py`: Generator 模块测试
- `tests/test_generator_sdk.py`: SDK 路径测试
- `tests/test_feishu_doc.py`: 飞书集成测试
- `tests/test_agent_sdk_runner.py`: AgentSDKRunner 测试
- `tests/test_log_generator.py`: 日志生成测试

## 命名约定

**文件:**
- `snake_case.py`: 所有 Python 文件使用 snake_case
- 测试文件: `test_<模块>.py`(例如 `test_generator.py`)
- 提示词文件: 大写版本标识符(例如 `V1.md`、`V2_example.md`)
- 文档: 主要文档用 `UPPERCASE.md`,支持文档用 `lowercase.md`

**目录:**
- `snake_case/`: 所有目录使用 snake_case
- 功能模块: `src/modules/` 用于业务逻辑
- 测试目录: 项目根目录的 `tests/`
- 文档: 项目根目录的 `docs/`
- 规划: GSD 分析的 `.planning/codebase/`

**函数和类:**
- 函数: `snake_case()`(例如 `run_pipeline`、`search`、`create_doc`)
- 类: `PascalCase`(例如 `WechatWriterAgent`、`AgentSDKRunner`、`FeishuTokenManager`)
- Dataclasses: `PascalCase`(例如 `Article`、`SearchResult`、`AgentRunMetrics`)
- 常量: `UPPER_SNAKE_CASE`(例如 `REQUIRED_FIELDS`、`VALID_STATUSES`)

**模块:**
- 基于函数的模块: 以主要函数命名(例如 `retrieval.py::search()`)
- 基于类的模块: 以主要类命名(例如 `agent_sdk.py::AgentSDKRunner`)
- 多功能模块: 以功能命名(例如 `feishu_doc.py` 用于飞书文档)

## 新代码添加位置

**新功能(例如微信集成):**
- 主要代码: `src/modules/wechat_api.py`(与 feishu_doc.py 并列)
- 测试: `tests/test_wechat_api.py`
- 更新: `src/modules/__init__.py` 以导出新模块
- 集成点: `src/main.py` 编排器(添加阶段 5)

**新工具/验证器:**
- 实现: `src/utils/<名称>.py`
- 测试: `tests/test_<名称>.py`
- 更新: 如果是公共 API 的一部分,更新 `src/utils/__init__.py`

**新钩子/仪器:**
- 实现: `src/hooks/<功能>_hooks.py`
- 测试: `tests/test_<功能>_hooks.py`
- 更新: `src/hooks/__init__.py` 用于导出
- 集成: 在 `AgentSDKRunner._register_hooks()` 中注册

**新测试:**
- 位置: `tests/test_<模块>.py`(镜像 `src/` 结构)
- 格式: 使用 pytest,从 conftest.py 使用 fixtures(如果存在)
- 运行: `pytest tests/test_<模块>.py -v`

**新文档:**
- 主要文档: `.planning/codebase/<UPPERCASE>.md`(仅 GSD 分析)
- 项目文档: `docs/<lowercase>.md`
- 运行指南: `docs/<功能>_setup.md`

## 特殊目录

**logs/**
- 用途: 运行时执行日志和指标
- 生成: 是(在运行时创建)
- 提交: 否(在 .gitignore 中)
- 内容: JSON 指标文件,来自 LogDocumentGenerator 的 markdown 日志
- 清理: 手动(可以安全删除旧日志)

**.planning/codebase/**
- 用途: GSD 编排器分析文档
- 生成: 否(通过 /gsd:map-codebase 手动创建)
- 提交: 是(跟踪架构决策)
- 内容: ARCHITECTURE.md、STRUCTURE.md、CONVENTIONS.md、CONCERNS.md
- 编辑: 当架构更改时更新

**.venv/**
- 用途: Python 虚拟环境
- 生成: 是(通过 `python -m venv .venv` 创建)
- 提交: 否(在 .gitignore 中)
- 清理: 可以安全删除;使用 `python -m venv .venv && pip install -r requirements.txt` 重新生成

**write_prompt/**
- 用途: agent 的版本化系统提示词
- 生成: 否(手动维护)
- 提交: 是(提示词版本是架构决策)
- 内容: 具有不同提示词策略的 Markdown 文件
- 使用: 通过 generator.py 的 `_get_system_prompt(version)` 加载

---

*结构分析: 2026-01-27*
