# Technology Stack

**Analysis Date:** 2026-01-27

## Languages

**Primary:**
- Python 3.13.3 - All core application logic, modules, and utilities

## Runtime

**Environment:**
- Python 3.13.3
- Virtual environment: `.venv/` directory (present)

**Package Manager:**
- pip - Python package management
- Lockfile: Not detected (requirements.txt used instead of lock file)

## Frameworks

**Core:**
- Anthropic SDK (`anthropic>=0.39.0`) - LLM integration for article generation using Claude models
- Claude Agent SDK (`claude_agent_sdk`) - Agent framework with tool calling and hooks support for NotebookLM integration
- python-dotenv (`>=1.0.0`) - Environment configuration loading

**Testing:**
- pytest (`>=7.4.0`) - Test framework and runner
- pytest-timeout (`>=2.1.0`) - Test execution timeout control
- pytest-mock (`>=3.11.0`) - Mocking and fixture support
- pytest-cov (`>=4.1.0`) - Test coverage reporting

**HTTP/Networking:**
- requests (`>=2.31.0`) - HTTP client for Feishu API calls and external integrations

## Key Dependencies

**Critical:**
- `anthropic>=0.39.0` - Provides Anthropic client for LLM inference via MiniMax or Claude APIs
  - Supports custom base_url for API routing
  - Tool calling for agentic workflows
  - Message streaming support

- `requests>=2.31.0` - HTTP requests to Feishu (飞书) APIs
  - Token refresh and caching
  - Markdown to Feishu Block format conversion
  - Error handling with retry logic

- `claude_agent_sdk` - Local agent SDK for structured tool calling
  - Hook system for logging (pre_tool_use, post_tool_use, stop_hook, user_prompt_submit_hook)
  - Supports NotebookLM tool integration
  - Metrics collection (tokens, runtime, tool calls)

- `python-dotenv>=1.0.0` - Configuration management
  - Loads .env file for secrets and model configuration
  - Environment variable defaults

**Testing Infrastructure:**
- `pytest>=7.4.0` - Main test runner
- `pytest-timeout>=2.1.0` - Timeout enforcement
- `pytest-mock>=3.11.0` - Mocking fixtures and utilities
- `pytest-cov>=4.1.0` - Coverage analysis

## Configuration

**Environment:**
Environment variables loaded from `.env` file using `python-dotenv`:

**LLM Configuration:**
- `ANTHROPIC_API_KEY` - API key for MiniMax or Claude API
- `ANTHROPIC_BASE_URL` - Custom API endpoint (e.g., `https://api.minimaxi.com/anthropic` for MiniMax)
- `ANTHROPIC_MODEL` - Model identifier (default: `MiniMax-M2.1`)

**NotebookLM Configuration:**
- `NOTEBOOK_URL` - Full URL to NotebookLM notebook
- `NOTEBOOK_ID` - Notebook identifier for API calls
- `NOTEBOOK_NAME` - Display name for notebook (default: `my_knowledge`)

**Feishu Integration:**
- `FEISHU_APP_ID` - Feishu application ID for authentication
- `FEISHU_APP_SECRET` - Feishu application secret
- `FEISHU_TENANT_DOMAIN` - Tenant domain for document URL construction
- `FEISHU_FOLDER_TOKEN` - Cloud document folder token
- `FEISHU_BITABLE_APP_TOKEN` - Multi-dimensional table app token
- `FEISHU_BITABLE_TABLE_ID` - Specific table ID for record insertion

**Agent Configuration:**
- `USE_AGENT_SDK` - Feature flag to enable/disable Claude Agent SDK mode (default: `true`)
- `LOG_MAX_RESULT_LENGTH` - Tool result truncation length (0 or empty = no truncation)
- `PROMPT_VERSION` - Prompt file version to use (e.g., `V1`, `V2` from `write_prompt/` directory)

**Build:**
- pytest.ini: `testpaths = tests`, `minversion = 7.0`
- No build system (pure Python, no compilation)

## Platform Requirements

**Development:**
- macOS or Linux (uses subprocess for NotebookLM skill execution)
- Python 3.13.3 or compatible
- Virtual environment (recommended)
- Git (for NotebookLM skill installation: `~/.claude/skills/notebooklm`)

**Production:**
- Python 3.13.3+
- Standard HTTP access to external APIs
  - Anthropic/MiniMax API endpoint
  - Feishu (飞书) open APIs (`https://open.feishu.cn/open-apis/`)
  - Google NotebookLM (via local skill integration)
- Access to local NotebookLM skill installation (`~/.claude/skills/notebooklm/`)

**External Service Dependencies:**
- Feishu workspace with cloud documents and multi-dimensional tables enabled
- Feishu application credentials with appropriate permissions
- NotebookLM notebook created and authenticated
- Anthropic/MiniMax API account with quota

---

*Stack analysis: 2026-01-27*
