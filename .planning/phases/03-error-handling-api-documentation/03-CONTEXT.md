# Phase 3: 错误处理与 API 差异文档化 - Context

**Gathered:** 2026-01-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Handle tool calling failures when using Agent SDK with official Anthropic API. System must diagnose and fix the "Command failed with exit code 1" error preventing NotebookLM skill execution through Agent SDK.

**Critical goal:** Make real test case work end-to-end (官方API + Claude Agent SDK + NotebookLM skill).

**Scope:** Focus on Agent SDK + Official API integration. MiniMax API documentation (API-04) is lower priority since Phase 4 successfully migrated to official API.

</domain>

<decisions>
## Implementation Decisions

### Subprocess error detection
- **Debug-first approach:** Investigate root cause of exit code 1 before implementing error handling
- **Comprehensive SDK setup verification:**
  1. Verify skill discovery - Does Agent SDK find NotebookLM in ~/.claude/skills/?
  2. Verify configuration passing - Is notebook_id being passed correctly to the skill?
  3. Verify API compatibility - Does official API block skill execution?
- **Fix root cause only:** Once root cause identified, implement targeted fix. Only add error handling if issue persists after fix.

### Implementation priority
1. **Phase 1: Debug** - Systematic diagnosis of Agent SDK + NotebookLM + Official API integration
2. **Phase 2: Fix root cause** - Address the specific issue found (likely configuration or SDK setup)
3. **Phase 3 (conditional): Error handling** - Only if root cause cannot be fully fixed, add graceful error handling

### Success metric
Real test case passes:
```python
# Test: 产品经理需要懂技术架构
result = run_pipeline(
    topic="产品经理需要懂技术架构",
    api_key=official_api_key,
    notebook_id="zh",
    enable_feishu=False
)

assert result.metrics['tool_call_count'] > 0  # NotebookLM was called
assert len(result.article.content) > 500      # Article generated
```

### Claude's Discretion
- Exact debugging steps and diagnostic tools
- Log formatting and verbosity during debug phase
- Whether to keep diagnostic code after fix or remove it
- Error message wording if error handling is needed

</decisions>

<specifics>
## Specific Ideas

**Known good state:**
- Traditional mode (USE_AGENT_SDK=false) works with official API
- NotebookLM skill works standalone (tested: `python ~/.claude/skills/notebooklm/scripts/run.py ask_question.py`)
- Pre-retrieval through subprocess works (Phase 2 verified)

**Known failure:**
- Agent SDK mode (USE_AGENT_SDK=true) + official API throws:
  ```
  Exception: Command failed with exit code 1 (exit code: 1)
  Error output: Check stderr output for details
  ```

**Hypothesis:**
Issue is likely in Agent SDK setup or skill invocation, not in NotebookLM skill itself (since skill works standalone).

</specifics>

<deferred>
## Deferred Ideas

**MiniMax API difference documentation (API-04):**
- Document MiniMax vs Official API differences
- Lower priority since we're now primarily using official API
- Consider removing from Phase 3 scope or creating separate documentation task

**General error handling framework:**
- Comprehensive tool call lifecycle logging (ERR-04)
- Timeout detection for all skills (ERR-02)
- Graceful degradation for any tool failure (ERR-03)
- Only implement if needed after root cause fix

**Error message design:**
- User-facing error messages
- Recovery suggestions
- Defer until we know what errors actually occur in production

</deferred>

---

*Phase: 03-error-handling-api-documentation*
*Context gathered: 2026-01-28*
