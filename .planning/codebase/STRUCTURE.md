# Codebase Structure

**Analysis Date:** 2026-01-27

## Directory Layout

```
wechat-writer-agent/
├── src/                           # Core library code
│   ├── __init__.py               # Package marker
│   ├── main.py                   # Pipeline orchestrator (227 lines)
│   ├── models.py                 # Data contracts
│   ├── modules/                  # Feature modules
│   │   ├── __init__.py          # Module imports
│   │   ├── retrieval.py         # NotebookLM integration (124 lines)
│   │   ├── generator.py         # Article generation (393 lines)
│   │   ├── agent_sdk.py         # Claude SDK wrapper (250 lines)
│   │   ├── feishu_doc.py        # Feishu document API (438 lines)
│   │   └── feishu_table.py      # Feishu multitable API (231 lines)
│   ├── hooks/                    # Instrumentation
│   │   ├── __init__.py
│   │   ├── logging_hooks.py     # SDK lifecycle hooks (126 lines)
│   │   └── log_generator.py     # Markdown log generation (169 lines)
│   └── utils/                    # Utilities
│       ├── __init__.py
│       └── temperature.py        # Parameter validation (30 lines)
├── tests/                        # Test suite
│   ├── test_setup.py
│   ├── test_generator.py
│   ├── test_generator_sdk.py
│   ├── test_agent_sdk_runner.py
│   ├── test_log_generator.py
│   ├── test_feishu_doc.py
│   ├── test_feishu_table_real.py
│   ├── test_writer_agent.py
│   └── ... (14+ test files)
├── docs/                         # Documentation
│   ├── README.md
│   ├── skills.md
│   ├── agent_logs.md
│   └── ... (project docs)
├── write_prompt/                 # Prompt versions
│   ├── V1.md
│   └── V2_example.md
├── logs/                         # Runtime logs (generated)
├── .planning/                    # GSD planning docs
├── .venv/                        # Python virtual environment
├── writer_agent.py               # High-level writer agent API (232 lines)
├── main.py                       # CLI entry point (49 lines)
├── cli.py                        # Additional CLI tools
├── notebooklm_tool.py           # NotebookLM tool wrapper
├── pytest.ini                    # Test configuration
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment template
└── .gitignore                    # Git ignore rules
```

## Directory Purposes

**src/**
- Purpose: Core library containing production code
- Contains: Python modules organized by feature
- Key files: `main.py` (orchestrator), `models.py` (contracts)

**src/modules/**
- Purpose: Feature implementations
- Contains: Retrieval, generation, Feishu integrations, SDK wrapper
- Key files: `generator.py` (largest module), `feishu_doc.py` (Feishu API client)

**src/hooks/**
- Purpose: Instrumentation for SDK lifecycle events
- Contains: Hook implementations and log generation
- Key files: `logging_hooks.py` (hook definitions), `log_generator.py` (markdown output)

**src/utils/**
- Purpose: Shared utilities and validators
- Contains: Temperature validation function
- Key files: `temperature.py` (parameter validation)

**tests/**
- Purpose: Unit and integration tests
- Contains: Test files for each module
- Key files: `test_generator.py`, `test_generator_sdk.py`, `test_agent_sdk_runner.py`

**docs/**
- Purpose: Project documentation
- Contains: README, guides, logs
- Key files: `README.md` (main docs), `agent_logs.md` (logging guide)

**write_prompt/**
- Purpose: Versioned system prompts
- Contains: Prompt variations and examples
- Key files: `V1.md` (current), `V2_example.md` (future)

**logs/**
- Purpose: Runtime execution logs (generated at runtime)
- Contains: Execution traces and metrics
- Key files: Dynamically generated JSON/markdown logs

**.planning/**
- Purpose: GSD (Goal-Scheduled Delivery) planning documents
- Contains: Architecture, structure, conventions, concerns analysis
- Key files: `ARCHITECTURE.md`, `STRUCTURE.md`, `CONVENTIONS.md`, `CONCERNS.md`

## Key File Locations

**Entry Points:**
- `main.py` (project root): CLI entry point with environment loading
- `writer_agent.py`: High-level API for WechatWriterAgent class
- `src/main.py`: Pipeline function for programmatic use

**Configuration:**
- `.env.example`: Template for environment variables
- `pytest.ini`: Test runner configuration
- `requirements.txt`: Python package dependencies

**Core Logic:**
- `src/modules/generator.py`: Article generation with dual paths (SDK vs Anthropic)
- `src/modules/agent_sdk.py`: Claude Agent SDK wrapper and metrics collection
- `src/modules/retrieval.py`: NotebookLM subprocess integration
- `src/modules/feishu_doc.py`: Feishu document creation and Markdown conversion
- `src/modules/feishu_table.py`: Feishu multidimensional table operations

**Models & Contracts:**
- `src/models.py`: Dataclasses for SearchResult, Article, DocResult, PipelineResult
- `src/modules/agent_sdk.py`: AgentRunMetrics dataclass for SDK metrics

**Testing:**
- `tests/test_generator.py`: Generator module tests
- `tests/test_generator_sdk.py`: SDK path tests
- `tests/test_feishu_doc.py`: Feishu integration tests
- `tests/test_agent_sdk_runner.py`: AgentSDKRunner tests
- `tests/test_log_generator.py`: Log generation tests

## Naming Conventions

**Files:**
- `snake_case.py`: All Python files use snake_case
- Test files: `test_<module>.py` (e.g., `test_generator.py`)
- Prompt files: Uppercase version identifier (e.g., `V1.md`, `V2_example.md`)
- Documentation: `UPPERCASE.md` for major docs, `lowercase.md` for supporting docs

**Directories:**
- `snake_case/`: All directories use snake_case
- Feature modules: `src/modules/` for business logic
- Test directory: `tests/` in project root
- Documentation: `docs/` in project root
- Planning: `.planning/codebase/` for GSD analysis

**Functions & Classes:**
- Functions: `snake_case()` (e.g., `run_pipeline`, `search`, `create_doc`)
- Classes: `PascalCase` (e.g., `WechatWriterAgent`, `AgentSDKRunner`, `FeishuTokenManager`)
- Dataclasses: `PascalCase` (e.g., `Article`, `SearchResult`, `AgentRunMetrics`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `REQUIRED_FIELDS`, `VALID_STATUSES`)

**Modules:**
- Function-based modules: Named after primary function (e.g., `retrieval.py::search()`)
- Class-based modules: Named after primary class (e.g., `agent_sdk.py::AgentSDKRunner`)
- Multi-feature modules: Named after feature (e.g., `feishu_doc.py` for Feishu docs)

## Where to Add New Code

**New Feature (e.g., WeChat Integration):**
- Primary code: `src/modules/wechat_api.py` (parallel to feishu_doc.py)
- Tests: `tests/test_wechat_api.py`
- Update: `src/modules/__init__.py` to export new module
- Integration point: `src/main.py` orchestrator (add stage 5)

**New Utility/Validator:**
- Implementation: `src/utils/<name>.py`
- Tests: `tests/test_<name>.py`
- Update: `src/utils/__init__.py` if part of public API

**New Hook/Instrumentation:**
- Implementation: `src/hooks/<feature>_hooks.py`
- Tests: `tests/test_<feature>_hooks.py`
- Update: `src/hooks/__init__.py` for exports
- Integration: Register in `AgentSDKRunner._register_hooks()`

**New Test:**
- Location: `tests/test_<module>.py` (mirrors `src/` structure)
- Format: Use pytest with fixtures from conftest.py (if exists)
- Run: `pytest tests/test_<module>.py -v`

**New Documentation:**
- Major docs: `.planning/codebase/<UPPERCASE>.md` (GSD analysis only)
- Project docs: `docs/<lowercase>.md`
- Run guides: `docs/<feature>_setup.md`

## Special Directories

**logs/**
- Purpose: Runtime execution logs and metrics
- Generated: Yes (created at runtime)
- Committed: No (in .gitignore)
- Contents: JSON metrics files, markdown logs from LogDocumentGenerator
- Cleanup: Manual (old logs can be deleted safely)

**.planning/codebase/**
- Purpose: GSD orchestrator analysis documents
- Generated: No (manually created by /gsd:map-codebase)
- Committed: Yes (tracks architectural decisions)
- Contents: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, CONCERNS.md
- Edit: Update when architecture changes

**.venv/**
- Purpose: Python virtual environment
- Generated: Yes (created by `python -m venv .venv`)
- Committed: No (in .gitignore)
- Cleanup: Safe to delete; regenerate with `python -m venv .venv && pip install -r requirements.txt`

**write_prompt/**
- Purpose: Versioned system prompts for agent
- Generated: No (maintained manually)
- Committed: Yes (prompt versions are architectural decisions)
- Contents: Markdown files with different prompt strategies
- Usage: Loaded by generator.py via `_get_system_prompt(version)`

---

*Structure analysis: 2026-01-27*
