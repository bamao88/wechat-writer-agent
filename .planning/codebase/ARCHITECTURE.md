# Architecture

**Analysis Date:** 2026-01-27

## Pattern Overview

**Overall:** Pipeline/Orchestrator Pattern with Feature Toggle

**Key Characteristics:**
- Four-stage content production pipeline with clear separation of concerns
- Pluggable backend implementations (Anthropic SDK vs Claude Agent SDK)
- Feature flag-based decision routing at orchestration layer
- Integration with external services via specialized adapter modules
- Metrics collection and logging through hook-based instrumentation

## Layers

**Orchestration Layer:**
- Purpose: Coordinate the four-stage pipeline, manage retries, and control feature toggles
- Location: `src/main.py`
- Contains: `run_pipeline()` function with retry logic, error handling strategies, and conditional execution paths
- Depends on: All other modules (retrieval, generator, feishu_doc, feishu_table)
- Used by: `writer_agent.py` (interactive agent) and external CLI scripts

**Retrieval Layer:**
- Purpose: Query NotebookLM knowledge bases for source material
- Location: `src/modules/retrieval.py`
- Contains: External subprocess calls to NotebookLM skill; error handling for auth/notebook not found
- Depends on: External NotebookLM skill via subprocess
- Used by: Generator layer (during generation, not pipeline start)

**Generation Layer:**
- Purpose: Generate articles using Claude API with optional SDK integration
- Location: `src/modules/generator.py`
- Contains: Two implementations - `generate()` (Anthropic SDK) and `generate_with_sdk()` (Claude Agent SDK); prompt management; article parsing
- Depends on: Retrieval (for additional queries during generation), agent_sdk (optional), log_generator, temperature validator
- Used by: Orchestration layer

**Integration Adapters Layer:**
- Purpose: Handle external service communication
- Location: `src/modules/feishu_doc.py`, `src/modules/feishu_table.py`
- Contains: Feishu API clients, token management, Markdown-to-blocks conversion, field validation
- Depends on: Token managers, HTTP requests library
- Used by: Orchestration layer (stages 3-4)

**Instrumentation Layer:**
- Purpose: Capture metrics and logs for SDK-based execution
- Location: `src/hooks/logging_hooks.py`, `src/hooks/log_generator.py`
- Contains: Hook implementations for pre/post tool use, stop events; markdown log generation
- Depends on: AgentRunMetrics data structure
- Used by: agent_sdk (registers hooks), generator (generates markdown logs)

**Models Layer:**
- Purpose: Define data contracts between stages
- Location: `src/models.py`
- Contains: SearchResult, Article, DocResult, PipelineResult dataclasses
- Depends on: Nothing (pure data definitions)
- Used by: All other layers

## Data Flow

**Stage 1 - Retrieval:**

1. Orchestrator calls `retrieval.search(topic, notebook_id, notebook_url)`
2. Retrieval spawns subprocess to NotebookLM skill
3. NotebookLM returns SearchResult list
4. Results passed to Stage 2; empty list if retrieval fails

**Stage 2 - Generation (Two Paths):**

**Path A (USE_AGENT_SDK=false):**
1. `generator.generate()` receives topic + search results
2. Builds system prompt + user message with pre-retrieved content
3. Calls Anthropic client with tool definition for NotebookLM
4. Agent loop: handles tool_use responses, calls retrieval if needed
5. Extracts article from final response
6. Returns Article object (no metrics)

**Path B (USE_AGENT_SDK=true):**
1. `generator.generate_with_sdk()` receives topic + search results
2. Creates AgentSDKRunner instance
3. Registers hooks (pre_tool_use_hook, post_tool_use_hook, stop_hook)
4. Calls `runner.generate()` with system prompt and user message
5. SDK executes agent loop, hooks capture tool calls and metrics
6. LogDocumentGenerator converts metrics to markdown log
7. Returns (Article, metrics_dict) tuple with log_markdown included

**Stage 3 - Feishu Document:**

1. If enable_feishu=true and folder_token provided:
2. `feishu_doc.create_doc()` gets tenant access token from Feishu API
3. MarkdownToBlockConverter transforms article content into Feishu blocks
4. Calls Feishu API to create document and write content blocks
5. Returns DocResult with doc_url
6. Log document also created if metrics present

**Stage 4 - Feishu Table:**

1. If Stage 3 succeeded and enable_feishu=true:
2. Builds record_fields dict with required fields (topic, doc_url, timestamp, status)
3. Optionally adds metrics fields if using SDK (runtime_seconds, tool_call_count, etc.)
4. `feishu_table.insert_record()` validates fields (required, types, enums)
5. Calls Feishu API to insert record into multidimensional table
6. Returns record_id

**State Management:**
- Each stage maintains independent state: search_results, article, doc_result, record_id
- Failures in stages 3-4 are non-fatal; pipeline completes if doc or table writes fail
- Stage 2 failures are fatal (article generation is required)
- Retry logic applies only to stages 1 and 3

## Key Abstractions

**Pipeline:**
- Purpose: Defines the complete content production workflow
- Examples: `run_pipeline()` in `src/main.py`
- Pattern: Linear four-stage orchestrator with error handlers

**Article:**
- Purpose: Represents generated content
- Examples: `src/models.py::Article` (title, content, source_summary)
- Pattern: Simple dataclass contract

**AgentSDKRunner:**
- Purpose: Encapsulates Claude Agent SDK execution with metrics collection
- Examples: `src/modules/agent_sdk.py::AgentSDKRunner`
- Pattern: Wrapper class that initializes SDK client and executes with hooks

**FeishuTokenManager:**
- Purpose: Caches and refreshes Feishu API tokens
- Examples: `src/modules/feishu_doc.py::FeishuTokenManager`
- Pattern: Global token cache with refresh-on-expiry logic

**MarkdownToBlockConverter:**
- Purpose: Transforms Markdown into Feishu document block format
- Examples: `src/modules/feishu_doc.py::MarkdownToBlockConverter`
- Pattern: Stateless converter with parsing rules for headings, lists, code

## Entry Points

**CLI Entry (Interactive Agent):**
- Location: `main.py` (project root)
- Triggers: `python main.py`
- Responsibilities: Loads environment, creates WechatWriterAgent, starts interactive loop

**Pipeline Entry (Batch Mode):**
- Location: `src/main.py::run_pipeline()`
- Triggers: Called by orchestrator scripts or writer_agent
- Responsibilities: Executes four-stage pipeline with retry logic and metrics collection

**Writer Agent Entry (High-level API):**
- Location: `writer_agent.py::WechatWriterAgent`
- Triggers: Instantiated by external code or CLI
- Responsibilities: Manages conversation state, coordinates pipeline calls, handles user interactions

## Error Handling

**Strategy:** Fault tolerance with non-fatal degradation for non-critical stages

**Patterns:**
- **Retrieval failures:** Retry max_retries times; on final failure, continue with empty results and mark as "无检索结果"
- **Generation failures:** Fatal; raises RuntimeError to caller
- **Document creation failures:** Retry max_retries times; on final failure, log warning but continue (doc_result=None)
- **Table insertion failures:** Non-fatal; logs error but returns (record_id=None); pipeline completes successfully
- **Field validation failures:** Raises ValueError immediately
- **Token acquisition failures:** RuntimeError with helpful message (NotImplementedError for unimplemented features)

## Cross-Cutting Concerns

**Logging:**
- Print statements for progress (pipeline stages)
- Hook-based metrics capture (SDK mode only)
- LogDocumentGenerator creates markdown logs from metrics

**Validation:**
- Temperature parameter validation in temperature.py
- Required fields validation in feishu_table.py
- API Key presence checks at entry points

**Authentication:**
- Feishu token manager handles OAuth flow and caching
- Anthropic API key via environment variables
- NotebookLM skill authentication via external script

---

*Architecture analysis: 2026-01-27*
