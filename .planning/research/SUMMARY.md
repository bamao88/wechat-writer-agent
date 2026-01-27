# Project Research Summary

**Project:** WeChat Writer Agent - Agent SDK Tool Calling Fix
**Domain:** Python LLM Agent with Knowledge Base Integration
**Researched:** 2026-01-27
**Confidence:** HIGH

## Executive Summary

This project aims to fix the Agent SDK tool calling mechanism for a WeChat content generation agent that uses Claude's Agent SDK, MiniMax API (Anthropic-compatible), and a subprocess-based NotebookLM tool for knowledge retrieval. The core issue is a critical configuration mismatch: the code returns tool names as strings (`["notebooklm"]`) but fails to configure the SDK to load tools from the filesystem via `setting_sources` parameter.

Research confirms this is NOT an API compatibility issue—MiniMax fully supports tool use. The recommended fix is straightforward: add `setting_sources=["user", "project"]` to `ClaudeAgentOptions` and change the parameter from `tools=` to `allowed_tools=["Skill"]`. This enables the SDK to discover and load Skills from `~/.claude/skills/notebooklm/`. An alternative approach is to wrap the NotebookLM subprocess as an in-process MCP server, which offers better observability and error handling at the cost of additional code.

The main risk is subprocess tool failures happening silently without proper validation. This can be mitigated by implementing explicit verification of tool outputs (e.g., checking if retrieved content is non-empty) and maintaining comprehensive logging via the existing hooks system.

## Key Findings

### Recommended Stack

The project uses a well-architected stack with Claude Agent SDK + MiniMax API + subprocess tools. The critical finding is that Claude Agent SDK has three distinct tool integration patterns, and the current implementation doesn't properly use any of them.

**Core technologies:**
- **Claude Agent SDK (Python)**: Agent orchestration with tool calling, session management, and hooks — currently missing proper tool registration configuration
- **MiniMax API (Anthropic-compatible)**: Fully supports tool use protocol including tool_use/tool_result blocks and multi-turn conversations — NOT the source of the problem
- **NotebookLM Skill (subprocess)**: Verified working via direct testing, returns ~2000 chars of content — the tool itself is functional
- **Hook System (AgentRunMetrics)**: Well-designed for capturing tool call lifecycle events via Pre/Post/Stop hooks — will work correctly once tools are registered

**Critical missing dependency:** `claude-agent-sdk>=0.8.0` is NOT in requirements.txt but is imported in code.

### Expected Features

The research identifies that the core feature requirement is **autonomous tool invocation**—the agent must decide when to call NotebookLM based on context, not be prompted every time.

**Must have (table stakes):**
- Tool discovery and registration (currently broken)
- Autonomous tool invocation (blocked by registration issue)
- Multi-turn tool conversations (supported by API)
- Tool call logging and metrics (implemented, waiting for tools to work)

**Should have (competitive):**
- Intelligent tool selection (agent only calls when materials insufficient)
- Cost-aware tool usage (avoid redundant subprocess calls to NotebookLM)
- Strong error handling for subprocess failures

**Defer (v2+):**
- Parallel tool calls (not needed for single-tool system)
- Progressive tool loading (overkill for 1 tool)
- Programmatic tool calling (adds complexity)

### Architecture Approach

The recommended architecture is **In-Process MCP Server Wrapping Subprocess** (Pattern 2 from architecture research). This hybrid pattern keeps the existing subprocess call in `retrieval.py` but wraps it in an SDK MCP server for proper registration.

**Major components:**
1. **AgentSDKRunner** — Creates in-process MCP server using `create_sdk_mcp_server()` with `@tool` decorator wrapping `retrieval.search()`
2. **Tool Handler** — Async function that calls existing subprocess, formats results as MCP response with proper error handling
3. **Hook System** — Existing Pre/Post/Stop hooks capture metrics via lambda closures, no changes needed

**Alternative architecture:** Register NotebookLM as a proper Skill with SKILL.md file and use `setting_sources=["user", "project"]` + `allowed_tools=["Skill"]`. This is simpler (fewer code changes) but requires verifying that the NotebookLM skill has proper SKILL.md metadata.

### Critical Pitfalls

1. **Tool Definition vs Registration Mismatch** — Prompt references tool names that SDK can't find because `setting_sources` is missing. Results in silent failure with `tool_call_count: 0`. Prevention: Add `setting_sources` parameter and verify tool names match between prompt and registration.

2. **Third-Party API Parameter Compatibility** — MiniMax API silently ignores parameters like `mcp_servers`, `context_management`, etc. However, tool calling itself IS supported. Prevention: Strip unsupported parameters and follow MiniMax's requirement to include all content blocks (thinking/text/tool_use) in conversation history.

3. **Subprocess Tool Silent Failure** — Tools running in subprocesses fail without stack traces, agent hallucinates success. Prevention: Validate tool results immediately (e.g., check for non-empty content), prefer in-process wrappers over pure subprocess, enable `ANTHROPIC_LOG=debug`.

4. **Prompt Doesn't Force Tool Use** — Current prompt suggests tool use but doesn't require it, so agent skips tools when it thinks materials are sufficient. Prevention: Make tool use mandatory in prompt ("You MUST call..."), use `tool_choice` parameter for first turn.

5. **Tool Result Formatting** — Sending text before tool_result blocks causes 400 errors. Prevention: Always put tool_result blocks first in content array, bundle multiple tool results in single user message to enable parallel calling.

## Implications for Roadmap

Based on research, a focused 3-phase approach addresses the core issue while building toward production readiness:

### Phase 1: Fix Tool Registration (CRITICAL - 1 hour)
**Rationale:** This is the root cause blocking all tool calls. Must be fixed before anything else works.

**Delivers:**
- Tool calls working (`tool_call_count > 0`)
- SDK properly discovers and loads NotebookLM tool
- Hooks fire and capture metrics

**Addresses:**
- Tool discovery (FEATURES.md table stakes)
- Tool registration (ARCHITECTURE.md integration point)
- `claude-agent-sdk` dependency added to requirements.txt

**Avoids:**
- Pitfall #1 (tool name mismatch) by using correct SDK parameters
- Silent failures by enabling proper error paths

**Implementation:**
- Add `setting_sources=["user", "project"]` to `ClaudeAgentOptions`
- Change `tools=` parameter to `allowed_tools=["Skill"]`
- Add `claude-agent-sdk>=0.8.0` to requirements.txt
- Test with empty materials to force tool call

### Phase 2: Strengthen Tool Use & Validation (CRITICAL - 2 hours)
**Rationale:** Once tools are registered, ensure they're actually called and results are valid. Addresses prompt weakness and subprocess validation gaps.

**Delivers:**
- Agent autonomously calls tools when needed
- Tool results validated before use
- Error handling for subprocess failures
- Comprehensive metrics proving tool use works

**Uses:**
- Prompt engineering (mandatory tool use language)
- `tool_choice` parameter for forced invocation
- Result validation patterns (check non-empty content)

**Implements:**
- Enhanced prompt with mandatory tool use instructions
- Tool result validation layer (detect empty/error responses)
- Error handling for subprocess timeouts/failures
- Integration tests verifying tool lifecycle

**Avoids:**
- Pitfall #6 (weak prompts) by making tool use mandatory
- Pitfall #3 (silent failures) by validating outputs
- Pitfall #7 (insufficient logging) by capturing full metrics

### Phase 3: Production Polish (IMPORTANT - 1.5 hours)
**Rationale:** After core functionality works, add observability and edge case handling for production deployment.

**Delivers:**
- Detailed logging and metrics reports
- Edge case handling (missing notebook_id, timeouts)
- Documentation of configuration options
- Regression test suite

**Uses:**
- LogDocumentGenerator for markdown reports
- Existing hook system for metrics
- Debug logging (`ANTHROPIC_LOG=debug`)

**Implements:**
- Tool call visualization in logs (input/output/duration)
- Graceful degradation when notebook_id not set
- Timeout handling for subprocess calls
- Configuration validation and clear error messages

**Avoids:**
- Pitfall #7 (insufficient debugging) by comprehensive logging
- Pitfall #8 (max_tokens truncation) by monitoring stop_reason
- Pitfall #9 (tool result format) by validating content block ordering

### Phase Ordering Rationale

- **Phase 1 first** because nothing works until tool registration is fixed—this is the critical blocker
- **Phase 2 before 3** because validation and prompting affect behavior; need stable behavior before optimizing observability
- **Architecture choice (Skills vs MCP)** should be decided in Phase 1—Skills approach is simpler (fewer code changes) but requires verifying SKILL.md exists; MCP approach gives more control but requires new code

The dependency chain is linear: Registration → Invocation → Validation → Observability. Each phase builds on the previous and cannot be skipped.

### Research Flags

**Phases NOT needing deeper research** (standard patterns):
- **Phase 1:** Tool registration patterns well-documented in official SDK docs, straightforward config change
- **Phase 2:** Prompt engineering and validation are standard practices, no novel patterns needed
- **Phase 3:** Logging patterns established, hooks system already implemented

**Areas to validate during implementation:**
- **NotebookLM SKILL.md format:** If using Skills approach, verify SKILL.md exists and has correct tool definitions
- **MiniMax conversation history:** Ensure full content blocks (thinking/text/tool_use) are preserved as documented
- **Tool name format:** Test to confirm exact tool name used by SDK (may be `notebooklm`, `ask_question`, or `mcp__notebooklm__query` depending on approach)

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified with official Claude SDK docs and MiniMax API docs; root cause identified in code |
| Features | HIGH | Clear table-stakes requirements; agent behavior well-understood from diagnostics |
| Architecture | HIGH | Multiple approaches documented; in-process MCP pattern proven in SDK examples |
| Pitfalls | HIGH | Most pitfalls directly observed in project diagnostics or documented in official guides |

**Overall confidence:** HIGH

The root cause is definitively identified (missing `setting_sources` configuration), the fix is well-documented in official SDK docs, and the tool itself is verified working via direct testing. The primary uncertainty is choosing between Skills approach (simpler) vs MCP approach (more control), but both paths are viable.

### Gaps to Address

- **Tool name verification:** Need to test exact tool name format once SDK is configured—may require iterating between `notebooklm`, `Skill`, or MCP naming conventions
- **SKILL.md contents:** If using Skills approach, must verify `~/.claude/skills/notebooklm/SKILL.md` exists and is properly formatted; if missing, either create it or switch to MCP approach
- **MiniMax-specific quirks:** While tool use is supported, need to validate conversation history format matches MiniMax's documented requirements (include all content blocks)
- **Performance baseline:** Need to measure subprocess overhead (estimated 3-5s per call) to determine if caching/optimization needed for production use

## Sources

### Primary (HIGH confidence)
- [Agent Skills in the SDK - Claude Docs](https://platform.claude.com/docs/en/agent-sdk/skills) — Skills discovery, `setting_sources`, SKILL.md format
- [Agent SDK Reference - Python](https://platform.claude.com/docs/en/agent-sdk/python) — `ClaudeAgentOptions` parameters, correct API usage
- [MiniMax Anthropic API Documentation](https://platform.minimax.io/docs/api-reference/text-anthropic-api) — Tool use support confirmed, parameter compatibility matrix
- [Custom Tools - Claude SDK](https://platform.claude.com/docs/en/agent-sdk/custom-tools) — MCP server creation, `@tool` decorator, tool registration
- [Implement Tool Use - Claude Docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/implement-tool-use) — Tool result formatting, error handling, parallel calling best practices

### Secondary (MEDIUM confidence)
- [Advanced Tool Use - Anthropic Engineering](https://www.anthropic.com/engineering/advanced-tool-use) — Tool Search Tool, Programmatic Calling (deferred features)
- [Agent System Design Patterns - Databricks](https://docs.databricks.com/aws/en/generative-ai/guide/agent-system-design-patterns) — Single vs multi-agent patterns
- [Claude Agent Skills Deep Dive](https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/) — Community analysis of Skills system internals

### Project-Specific Evidence
- `TOOL_CALL_DIAGNOSIS.md` — Root cause analysis showing `tool_call_count: 0` despite tool registration logs
- `TEST_REPORT.md` — Verification that NotebookLM subprocess works correctly via direct invocation
- `src/modules/agent_sdk.py` — Current implementation showing `tools=` parameter and missing `setting_sources`
- `write_prompt/V1.md` — Prompt referencing `query_notebooklm` tool name

---
*Research completed: 2026-01-27*
*Ready for roadmap: yes*
