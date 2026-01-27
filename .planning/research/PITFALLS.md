# Domain Pitfalls: Agent SDK Tool Calling

**Domain:** Claude Agent SDK tool calling with third-party API and subprocess integration
**Researched:** 2026-01-27
**Context:** Fixing tool calling in wechat-writer-agent (MiniMax API + subprocess NotebookLM)

---

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: Tool Definition vs Tool Registration Mismatch

**What goes wrong:** Prompt references `query_notebooklm` tool, but SDK is passed `["notebooklm"]` skill name. Agent receives no matching tool and silently ignores tool use requests, resulting in `tool_call_count: 0`.

**Why it happens:**
- Claude Agent SDK expects skill names (like `"notebooklm"`)
- Prompts reference specific tool names within those skills (like `query_notebooklm`)
- SDK doesn't automatically map skill names to tool names
- No error is raised when tools aren't found - failure is silent

**Consequences:**
- Agent never calls tools despite correct prompting
- `tool_call_count` remains 0 in all runs
- Manual tool execution works fine, masking the integration issue
- Debugging is extremely difficult due to lack of error messages

**Prevention:**
1. **Align naming across layers:**
   ```python
   # Option 1: Pass the actual tool name
   tools = ["query_notebooklm"]  # matches prompt

   # Option 2: Use skill namespace format
   tools = ["notebooklm:ask_question"]

   # Option 3: Update prompt to match skill name
   # In prompt: "Use the `notebooklm` tool..."
   ```

2. **Verify tool registration at startup:**
   ```python
   def _verify_tools_registered(self, tools: List[str]) -> None:
       """Verify tools are actually available to SDK"""
       # Query SDK for available tools
       # Log warning if tools don't exist
       # Fail fast rather than silent failure
   ```

3. **Add explicit validation:**
   ```python
   if tools and not self._tools_available(tools):
       raise ValueError(f"Tools not available: {tools}")
   ```

**Detection:**
- Log tool names at registration: `print(f"Registering tools: {tools}")`
- Check SDK documentation for exact tool name format
- Test with forced tool use (`tool_choice: {"type": "tool", "name": "..."}`
- Monitor for `tool_call_count: 0` despite appropriate prompts

**Confidence:** HIGH - Directly observed in project diagnostics (TOOL_CALL_DIAGNOSIS.md)

---

### Pitfall 2: Third-Party API Tool Calling Incompatibility

**What goes wrong:** MiniMax's Anthropic-compatible endpoint ignores critical parameters and has subtle differences in tool calling behavior compared to native Anthropic API.

**Why it happens:**
- MiniMax API silently ignores: `top_k`, `stop_sequences`, `service_tier`, `mcp_servers`, `context_management`, `container`
- Tool calling support exists but may have format differences
- Conversation history requirements differ (MiniMax requires ALL content blocks including thinking/text/tool_use)
- SDK makes assumptions based on official Anthropic API behavior

**Consequences:**
- Tools appear to be called but results aren't processed
- Conversation context breaks silently
- No error messages - endpoint just returns incomplete responses
- Debugging requires API-level logging to detect

**Prevention:**
1. **Verify third-party API compatibility explicitly:**
   ```python
   # Document known limitations
   MINIMAX_IGNORED_PARAMS = [
       'top_k', 'stop_sequences', 'service_tier',
       'mcp_servers', 'context_management', 'container'
   ]

   # Warn if using incompatible features
   if api_is_minimax and any(param in options for param in MINIMAX_IGNORED_PARAMS):
       logger.warning(f"MiniMax API ignores: {MINIMAX_IGNORED_PARAMS}")
   ```

2. **Implement conversation history correctly for third-party APIs:**
   ```python
   # MiniMax requirement: include ALL content blocks
   messages.append({
       "role": "assistant",
       "content": response.content  # Full content array, not just tool_use
   })
   ```

3. **Add API compatibility layer:**
   ```python
   class APICompatibilityLayer:
       def adjust_for_provider(self, provider: str, options: dict) -> dict:
           if provider == "minimax":
               # Strip unsupported parameters
               # Adjust tool format if needed
               # Add required context blocks
   ```

**Detection:**
- Test with official Anthropic API first (establish baseline)
- Enable API request/response logging
- Compare tool call format between APIs
- Monitor for incomplete assistant messages
- Check if conversation history format matches API requirements

**Confidence:** HIGH - Verified from MiniMax official documentation (platform.minimax.io)

---

### Pitfall 3: Subprocess Tool Silent Failure

**What goes wrong:** Tools that run in subprocesses (like NotebookLM) fail silently without error messages. Agent reports successful completion, but filesystem shows no changes.

**Why it happens:**
- Subprocess has no TTY/terminal attached
- Interactive tools (like `AskUserQuestion`) fail silently when they can't render TUI
- SDK catches exceptions but only returns error message, not stack traces
- Edit/Write tools report false success without actual execution
- Agent hallucinates completed actions

**Consequences:**
- Agent claims files were created/modified but they don't exist
- Verification steps don't catch the failure
- No error logs or warnings generated
- Users discover failures only through manual verification
- Complete loss of trust in agent output

**Prevention:**
1. **Validate tool results immediately:**
   ```python
   async def call_subprocess_tool(tool_name: str, args: dict) -> dict:
       result = await subprocess_call(tool_name, args)

       # Verify actual outcome
       if tool_name == "write_file":
           if not os.path.exists(args['path']):
               raise ToolExecutionError(f"File not created: {args['path']}")

       return result
   ```

2. **Prefer direct Python function calls over subprocess:**
   ```python
   # BAD: Subprocess call
   tools = ["notebooklm"]  # Runs as subprocess

   # GOOD: Direct function call via SDK MCP Servers
   from claude_agent_sdk import tool

   @tool
   def query_notebooklm(question: str) -> str:
       # Runs in your process, not subprocess
       return direct_function_call(question)
   ```

3. **Enable full error logging:**
   ```bash
   export ANTHROPIC_LOG=debug
   ```

4. **Intercept tool errors before sending to Claude:**
   ```python
   for message in runner:
       tool_response = runner.generate_tool_call_response()

       if tool_response:
           for block in tool_response.content:
               if block.is_error:
                   # Log full error details
                   logger.error(f"Tool failed: {block.content}")

                   # Verify claimed success
                   if "success" in str(block.content).lower():
                       raise ToolHallucinationError("Tool claimed success but failed")
   ```

**Detection:**
- Manual verification of all file operations
- Check for `is_error: true` in tool results
- Look for missing stack traces in logs
- Monitor issue trackers (anthropics/claude-code#5405)
- Test with `ANTHROPIC_LOG=debug` to see full errors

**Confidence:** HIGH - Documented in GitHub issue #5405 (claude-code tools failing silently)

---

## Moderate Pitfalls

Mistakes that cause delays or technical debt.

### Pitfall 4: Tool Result Formatting Breaks Parallel Calls

**What goes wrong:** Sending separate user messages for each tool result instead of bundling them in one message prevents future parallel tool calls.

**Why it happens:**
- Natural to send tool results as they complete
- SDK accepts multiple separate messages without error
- Claude "learns" from conversation history that tools should be called sequentially
- Parallel calling rate drops from ~2.5 tools/message to ~1.0

**Consequences:**
- Performance degrades as agent uses sequential calls
- API costs increase due to extra round-trips
- User experience suffers from slower responses
- Issue is invisible without metrics tracking

**Prevention:**
```python
# ❌ WRONG: Separate messages kill parallel calling
for tool_use in tool_uses:
    result = execute_tool(tool_use)
    runner.append_messages({
        "role": "user",
        "content": [{"type": "tool_result", ...}]
    })

# ✅ CORRECT: Bundle all results in single message
tool_results = []
for tool_use in tool_uses:
    result = execute_tool(tool_use)
    tool_results.append({"type": "tool_result", ...})

runner.append_messages({
    "role": "user",
    "content": tool_results  # All results together
})
```

**Detection:**
- Calculate average tools per tool-calling message
- Should be > 1.5 if parallel calling works
- Monitor API call count vs tool use count
- Look for sequential patterns in conversation history

**Confidence:** HIGH - Documented in official Anthropic tool use guide

---

### Pitfall 5: Tool Schema Validation Not Enforced

**What goes wrong:** Claude generates tool calls with missing required parameters or wrong types, leading to runtime errors in tool execution.

**Why it happens:**
- Default tool definitions don't enforce strict schema validation
- Claude may guess at missing parameters (especially Haiku models)
- Schema descriptions are unclear or incomplete
- Tool examples not provided for complex inputs

**Consequences:**
- Tool calls fail at execution time
- Claude retries 2-3 times before giving up
- Extra API calls and latency
- Poor user experience with "tool failed" messages

**Prevention:**
1. **Use strict tool definitions (2026 feature):**
   ```python
   tools = [{
       "name": "query_notebooklm",
       "description": "...",
       "input_schema": {...},
       "strict": True  # Guarantees schema conformance
   }]
   ```

2. **Provide detailed descriptions:**
   ```python
   # ❌ BAD
   "description": "Query notebook"

   # ✅ GOOD
   "description": """Query NotebookLM knowledge base using natural language.

   Use this when:
   - User asks for specific information
   - Need to verify facts
   - Looking for examples or case studies

   The question should be:
   - Natural language (not keywords)
   - Specific and focused
   - Complete sentence

   Returns: Relevant excerpts from knowledge base with source citations."""
   ```

3. **Add input examples for complex tools:**
   ```python
   tools = [{
       "name": "query_notebooklm",
       "input_schema": {...},
       "input_examples": [
           {"question": "Why should product managers participate in technology selection?"},
           {"question": "What are common mistakes in technical architecture decisions?"}
       ]
   }]
   ```

**Detection:**
- Monitor tool call retry patterns
- Look for "missing required parameter" in logs
- Track tool call success rate
- Enable schema validation debugging

**Confidence:** MEDIUM - Based on official documentation and best practices

---

### Pitfall 6: Prompt Doesn't Force Tool Use

**What goes wrong:** Agent generates reasonable output without calling tools, even when tools would provide better/required information.

**Why it happens:**
- Prompts suggest tool use but don't require it
- Agent evaluates tools as "optional nice-to-have"
- Agent's general knowledge seems sufficient
- No explicit forcing in `tool_choice` parameter

**Consequences:**
- `tool_call_count: 0` despite available tools
- Agent uses outdated training knowledge instead of current data
- Inconsistent behavior across runs
- Missing domain-specific information

**Prevention:**
1. **Make tool use mandatory in prompt:**
   ```markdown
   # ❌ WEAK
   You can use the query_notebooklm tool to search the knowledge base.

   # ✅ STRONG
   **CRITICAL**: You MUST call the query_notebooklm tool before writing.

   Even if the provided materials seem sufficient:
   1. Call the tool to verify information
   2. Call the tool to find additional examples
   3. Call the tool to get domain-specific details

   Do not skip this step under any circumstances.
   ```

2. **Use tool_choice parameter for critical tools:**
   ```python
   # Force specific tool on first turn
   options = ClaudeAgentOptions(
       tool_choice={"type": "tool", "name": "query_notebooklm"},
       ...
   )
   ```

3. **Add verification prompts:**
   ```markdown
   After retrieving information with query_notebooklm, verify:
   - Did you call the tool at least once?
   - Did you incorporate the tool results into your response?
   - Are you using knowledge base information, not general knowledge?
   ```

**Detection:**
- Monitor `tool_call_count` in metrics
- Compare output quality with vs without tool use
- Check if agent references tool results in response
- A/B test forced vs optional tool use

**Confidence:** MEDIUM - Based on project diagnostics showing smart agent decisions

---

## Minor Pitfalls

Mistakes that cause annoyance but are fixable.

### Pitfall 7: Insufficient Debugging Visibility

**What goes wrong:** Tool calling fails but logs don't show why, making debugging a guessing game.

**Why it happens:**
- Default logging level hides important details
- SDK swallows errors and returns minimal messages
- No structured logging of tool registration
- Token usage not tracked
- Conversation history not preserved

**Consequences:**
- Hours wasted debugging obvious issues
- Can't reproduce failures
- Can't verify fixes worked
- No performance baselines

**Prevention:**
```python
# 1. Enable debug logging
os.environ['ANTHROPIC_LOG'] = 'debug'

# 2. Log tool registration
print(f"[DEBUG] Registering tools: {tools}")
print(f"[DEBUG] Tools available: {sdk.list_tools()}")  # If SDK provides this

# 3. Create comprehensive metrics
@dataclass
class AgentRunMetrics:
    start_time: float
    end_time: Optional[float]
    tool_calls: List[Dict[str, Any]]
    total_tokens: int
    system_prompt: str
    initial_user_message: str
    messages: List[Dict[str, Any]]  # Full conversation history

    def tool_call_count(self) -> int:
        return len(self.tool_calls)

# 4. Write detailed logs
with open('run_log.md', 'w') as f:
    f.write(f"## Configuration\n")
    f.write(f"- Model: {model}\n")
    f.write(f"- Tools: {tools}\n")
    f.write(f"- Notebook ID: {notebook_id}\n\n")

    f.write(f"## Execution\n")
    f.write(f"- Tool calls: {metrics.tool_call_count()}\n")
    f.write(f"- Tokens: {metrics.total_tokens}\n")
    f.write(f"- Runtime: {metrics.runtime_seconds:.2f}s\n")
```

**Detection:**
- If you can't quickly answer "why isn't this working?", logging is insufficient
- If you need to add `print()` statements to debug, logging is insufficient

**Confidence:** HIGH - Based on project's logging system implementation

---

### Pitfall 8: Max Tokens Truncates Tool Use

**What goes wrong:** Response hits `max_tokens` limit mid-tool-call, leaving incomplete tool use block that can't be processed.

**Why it happens:**
- `max_tokens` set too low for complex responses
- Agent writes verbose text before tool use
- Tool schemas are large (counts toward output tokens)

**Consequences:**
- Tool call silently fails
- `stop_reason: max_tokens` but no error raised
- Must retry entire request with higher limit

**Prevention:**
```python
# 1. Check for truncation during tool use
if response.stop_reason == "max_tokens":
    last_block = response.content[-1]
    if last_block.type == "tool_use":
        # Retry with higher limit
        response = client.messages.create(
            max_tokens=4096,  # Increased
            ...
        )

# 2. Set generous max_tokens when using tools
options = ClaudeAgentOptions(
    max_tokens=4096,  # Not 1024
    ...
)

# 3. Monitor truncation rate
if metrics.stop_reason == "max_tokens":
    logger.warning(f"Response truncated at {max_tokens} tokens")
```

**Detection:**
- Check `stop_reason` in response
- Look for incomplete tool_use blocks
- Monitor average completion token usage

**Confidence:** MEDIUM - Documented in official API documentation

---

### Pitfall 9: Tool Results Not Following Format Requirements

**What goes wrong:** Tool results are sent with text content before `tool_result` blocks, causing 400 errors like "tool_use ids were found without tool_result blocks immediately after".

**Why it happens:**
- Natural to add explanatory text before results
- Format requirement is non-obvious
- Error message is cryptic

**Consequences:**
- Request fails with 400 error
- Conversation broken, must restart
- User confused by error message

**Prevention:**
```python
# ❌ WRONG: Text before tool results
messages.append({
    "role": "user",
    "content": [
        {"type": "text", "text": "Here are the results:"},  # ERROR
        {"type": "tool_result", "tool_use_id": "...", ...}
    ]
})

# ✅ CORRECT: Tool results first, text after (if needed)
messages.append({
    "role": "user",
    "content": [
        {"type": "tool_result", "tool_use_id": "...", ...},
        {"type": "text", "text": "What should I do next?"}  # OK after
    ]
})

# ✅ BEST: Tool results only
messages.append({
    "role": "user",
    "content": [
        {"type": "tool_result", "tool_use_id": "...", ...}
    ]
})
```

**Detection:**
- Error message mentions "tool_use ids"
- 400 error during tool result submission
- Check content array ordering

**Confidence:** HIGH - Explicitly documented in Anthropic tool use guide

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Initial tool integration | Tool name mismatch (#1) | Test with forced tool choice first |
| Third-party API integration | Parameter compatibility (#2) | Test with official API baseline |
| Subprocess tools | Silent failures (#3) | Add explicit verification layer |
| Performance optimization | Parallel calling (#4) | Bundle tool results correctly from start |
| Production deployment | Insufficient logging (#7) | Implement comprehensive metrics early |

---

## Verification Checklist

Before marking tool calling as "working":

- [ ] `tool_call_count > 0` in actual runs (not just test/forced mode)
- [ ] Tool names in prompt match tool registration exactly
- [ ] All tool results follow correct format (tool_result blocks first)
- [ ] Tool results bundled together for parallel calling
- [ ] Debug logging enabled and showing tool registration
- [ ] Metrics tracked: token usage, runtime, tool call count
- [ ] Tested with official Anthropic API (if using third-party)
- [ ] Subprocess tools verified by checking actual filesystem/state
- [ ] Tool schema validation working (no parameter errors)
- [ ] Max tokens sufficient for tool use + response

---

## Quick Diagnosis Guide

**Symptom: tool_call_count = 0**
1. Check tool name matches prompt (Pitfall #1)
2. Enable debug logging (`ANTHROPIC_LOG=debug`)
3. Strengthen prompt to force tool use (Pitfall #6)
4. Verify third-party API supports tool calling (Pitfall #2)

**Symptom: Tool results not processed**
1. Check content block ordering (Pitfall #9)
2. Verify conversation history format (Pitfall #2)
3. Check for `max_tokens` truncation (Pitfall #8)

**Symptom: Tools called but no effects**
1. Check subprocess execution (Pitfall #3)
2. Verify tool results for `is_error: true`
3. Check filesystem/state manually

**Symptom: Parallel calling not working**
1. Bundle tool results in single message (Pitfall #4)
2. Strengthen system prompt for parallel use
3. Calculate avg tools/message metric

---

## Sources

**HIGH Confidence (Official documentation):**
- [How to implement tool use - Claude API Docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/implement-tool-use)
- [MiniMax Anthropic API Compatibility](https://platform.minimax.io/docs/api-reference/text-anthropic-api)
- [Claude Agent SDK Overview](https://docs.claude.com/en/docs/claude-code/sdk/sdk-overview)

**MEDIUM Confidence (GitHub issues, community):**
- [GitHub Issue #5405: Tools failing silently](https://github.com/anthropics/claude-code/issues/5405)
- [Medium: When Claude Can't Ask - Tool SDK Problems](https://oneryalcin.medium.com/when-claude-cant-ask-building-interactive-tools-for-the-agent-sdk-64ccc89558fa)
- [liteLLM MiniMax Provider Docs](https://docs.litellm.ai/docs/providers/minimax)

**Project-Specific Evidence:**
- `TOOL_CALL_DIAGNOSIS.md` - Tool name mismatch analysis
- `TEST_REPORT.md` - Verification that manual tool calls work
- `src/modules/agent_sdk.py` - Current tool registration implementation
