# Feature Landscape: Agent SDK Tool Calling

**Domain:** LLM Agent Tool Calling with Claude SDK
**Researched:** 2026-01-27
**Confidence:** HIGH (verified with official Claude SDK docs + advanced tool use documentation)

## Table Stakes

Features users expect from a functional tool calling system. Missing = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Basic Tool Definition** | Core requirement for any tool calling system | Low | Tool name, description, input_schema (JSON Schema) |
| **Tool Discovery** | Agent must know what tools exist | Low | SDK loads tools from skill names or MCP servers |
| **Autonomous Tool Invocation** | Agent decides when to call tools based on task | Medium | Requires good tool descriptions + prompt engineering |
| **Tool Result Handling** | Agent must receive and use tool outputs | Low | Standard message format with tool_result blocks |
| **Error Handling** | Tools fail; agent must handle gracefully | Medium | is_error flag + retry logic |
| **Multi-turn Conversations** | Tool usage often requires multiple rounds | Medium | Message history management |
| **Tool Call Logging** | Must verify tools are actually called | Low | Track tool_use_id and tool_result pairs |

### Implementation Details

**Basic Tool Definition** (CURRENT ISSUE: Mismatch)
```python
# SDK expects skill name (string)
tools = ["notebooklm"]  # ✅ SDK format

# But prompt expects different name
# write_prompt/V1.md: "使用 `query_notebooklm` 工具"  # ❌ Mismatch
```

**Tool Discovery** (CURRENT STATUS: Partially working)
- SDK successfully loads skill: `[INFO] NotebookLM工具已注册`
- But tool naming mismatch prevents invocation
- Need to verify: `mcp__notebooklm__<function_name>` format

**Autonomous Tool Invocation** (CURRENT ISSUE: Never triggers)
- Tool call count always 0
- Agent generates article without calling tools
- Likely causes:
  1. Tool name mismatch (prompt vs SDK)
  2. Weak prompt instructions (not forcing tool use)
  3. SDK tool registration issue

---

## Differentiators

Features that set apart intelligent from basic tool calling. Not expected, but highly valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Parallel Tool Calls** | Efficiency: call multiple tools simultaneously | Medium | Reduces latency for independent operations |
| **Intelligent Tool Selection** | Agent only calls when needed, not every time | High | Requires sophisticated prompting + context awareness |
| **Progressive Tool Loading** | Only load tool definitions when relevant | High | Tool Search Tool feature (beta) - saves 85% tokens |
| **Programmatic Tool Calling** | Write code to orchestrate tools instead of sequential API calls | High | Reduces context pollution by 37% tokens |
| **Tool Use Examples** | Show concrete usage patterns beyond JSON schema | Medium | Improves accuracy from 72% to 90% on complex tools |
| **Strict Tool Validation** | Guarantee schema compliance (no invalid inputs) | Low | Add `strict: true` to tool definitions |
| **Cost-Aware Tool Usage** | Track token costs, avoid redundant calls | Medium | Important for expensive tools like NotebookLM (3-5s subprocess) |
| **Context-Aware Retries** | Retry with more context, not just raw retry | High | Agent learns from failures |

### Implementation Priorities for This Project

**HIGH PRIORITY: Intelligent Tool Selection**
- Core value: Agent decides when NotebookLM query is needed
- Current: Always provides pre-retrieved materials (module A)
- Goal: Agent autonomously queries when insufficient

**MEDIUM PRIORITY: Cost-Aware Tool Usage**
- NotebookLM has 3-5s subprocess overhead
- Agent should query once, reuse results
- Avoid redundant calls to same query

**LOW PRIORITY: Parallel Tool Calls**
- Not critical for MVP (single NotebookLM tool)
- Useful later if adding multiple tools

**DEFERRED: Progressive Tool Loading**
- Overkill for single-tool system
- Consider when scaling to 10+ tools

---

## Anti-Features

Features to explicitly NOT build. Common mistakes in tool calling systems.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Force Tool Use Every Time** | Defeats "intelligent agent" purpose; wastes API calls | Let agent decide based on context |
| **Overly Complex Tool Definitions** | Confuses agent, reduces accuracy | Keep descriptions clear, specific, 3-4 sentences |
| **Silent Tool Failures** | Impossible to debug | Log all tool calls, results, errors |
| **Tool Name Mismatches** | Causes silent failures (current issue) | Verify prompt and SDK use same names |
| **Inline Tool Execution** | Blocks agent loop, increases latency | Use async tools, subprocess for heavy operations |
| **Unlimited Retry Loops** | Infinite API costs | Set max_turns limit (10 is reasonable) |
| **Returning Raw JSON to Agent** | Pollutes context with structured data | Format tool results as readable text |
| **Separate Tool Result Messages** | Breaks parallel tool use pattern | All tool results in single user message |
| **Text Before Tool Results** | Causes 400 errors | Tool results FIRST, then optional text |

### Critical Anti-Patterns for This Project

**AVOID: Multiple tool definitions for same tool**
```python
# ❌ Wrong: Defining tool in generator.py AND agent_sdk.py
# Causes naming conflicts and confusion

# ✅ Right: Single source of truth
# Either: Use SDK skill system (notebooklm skill)
# Or: Define custom tool once in SDK runner
```

**AVOID: Vague prompt instructions**
```markdown
# ❌ Weak: "使用 `query_notebooklm` 工具检索NotebookLM知识库。"
# Agent ignores this soft suggestion

# ✅ Strong: "你**必须**先调用 `notebooklm` 工具至少一次。
# 即使提供了素材，也要验证和补充信息。"
```

**AVOID: Assuming training data is current**
```python
# ❌ Wrong: Relying on Claude's general knowledge
# Training data is 6-18 months old

# ✅ Right: Force tool use to get current data
# system_prompt: "不要使用你的通用知识，必须基于知识库中的实际内容写作。"
```

---

## Feature Dependencies

```
Tool Definition
    ↓
Tool Discovery (SDK loads skill)
    ↓
Tool Registration (added to allowed_tools)
    ↓
Autonomous Invocation (agent decides to call)
    ↓
Tool Execution (subprocess to NotebookLM)
    ↓
Result Handling (format response)
    ↓
Multi-turn Conversation (agent continues with results)
```

**Critical Path Issues:**
1. **Tool Definition** ✅ Done (notebooklm skill exists)
2. **Tool Discovery** ✅ Done (SDK logs "工具已注册")
3. **Tool Registration** ⚠️ Uncertain (name mismatch?)
4. **Autonomous Invocation** ❌ BLOCKED (tool_call_count = 0)

**Root Cause Analysis:**
- Prompt says: `query_notebooklm`
- SDK registers: `notebooklm` (skill name)
- MCP format: `mcp__notebooklm__ask_question`
- Agent sees: ??? (likely doesn't find matching tool)

---

## MVP Recommendation

For MVP (First Milestone: 修复工具调用), prioritize:

1. **Fix Tool Name Mismatch** (P0 - BLOCKING)
   - Verify correct tool name format in SDK
   - Update prompt to use exact name
   - Test: tool_call_count > 0

2. **Strengthen Prompt Instructions** (P0 - BLOCKING)
   - Make tool use mandatory, not optional
   - Add explicit conditions: "如果素材不足，必须调用工具"
   - Test: agent calls tool even with pre-retrieved materials

3. **Add Tool Call Validation** (P0 - CRITICAL)
   - Verify tool_use_id matches tool_result
   - Log tool inputs and outputs
   - Test: can prove tool was actually called

4. **Error Handling** (P1 - IMPORTANT)
   - Catch subprocess errors (NotebookLM)
   - Return meaningful error messages
   - Test: agent handles tool failures gracefully

5. **Basic Logging** (P1 - IMPORTANT)
   - Track: tool name, inputs, outputs, errors
   - Already implemented: AgentRunMetrics
   - Test: logs show complete tool call lifecycle

Defer to post-MVP:

- **Parallel Tool Calls** - Not needed for single tool
- **Progressive Tool Loading** - Overkill for 1-tool system
- **Programmatic Tool Calling** - Adds complexity without clear ROI
- **Tool Use Examples** - Try strong descriptions first
- **Intelligent Retry Logic** - Handle basic retries first

---

## Feature Complexity Matrix

| Feature | Implementation Effort | Debugging Difficulty | Production Risk |
|---------|---------------------|---------------------|----------------|
| **Fix tool name mismatch** | 1 hour | Low | Low |
| **Strengthen prompts** | 30 min | Low | Low |
| **Tool call validation** | 2 hours | Medium | Low |
| **Error handling** | 3 hours | Medium | Medium |
| **Parallel tool calls** | 5 hours | High | Medium |
| **Intelligent selection** | Already designed | Medium | Low |
| **Cost tracking** | 2 hours | Low | Low |
| **Progressive loading** | 10+ hours | High | High |

---

## Current System Gaps

Based on diagnosis in TOOL_CALL_DIAGNOSIS.md:

### Gap 1: Tool Name Format Uncertainty ⭐⭐⭐⭐⭐

**Problem:**
- Skill name: `notebooklm`
- Prompt expects: `query_notebooklm`
- MCP format: `mcp__notebooklm__ask_question`?

**Investigation Needed:**
```python
# Test different formats:
tools = ["notebooklm"]  # Current
tools = ["query_notebooklm"]  # Try 1
tools = ["mcp__notebooklm__ask_question"]  # Try 2

# Or query SDK for registered tool names:
# Check SDK logs for actual tool names available
```

### Gap 2: Prompt Weakness ⭐⭐⭐

**Problem:** Current prompt is suggestive, not mandatory

**Current:**
```markdown
### 第二步：检索资料

使用 `query_notebooklm` 工具检索NotebookLM知识库。
```

**Proposed:**
```markdown
### 第二步：检索资料（必需）

**重要**: 在开始写作前，你**必须**先调用 NotebookLM 工具至少一次。

即使用户已经提供了素材，你也必须：
1. 调用工具验证信息
2. 补充更多细节
3. 查找相关案例

工具调用格式：`<tool_name>`（待确认正确名称）

不要使用你的通用知识。必须基于知识库中的实际内容写作。
```

### Gap 3: No Tool Call Verification ⭐⭐⭐⭐

**Problem:** Can't distinguish between:
- Agent chose not to call tool (intelligent decision)
- Agent tried but tool name mismatched (configuration error)
- Agent never saw tool (registration failure)

**Solution:** Add verification checkpoints
```python
# In hooks/logging_hooks.py
def pre_tool_use_hook(input_data, tool_use_id, context, metrics):
    print(f"[TOOL CALL] Tool: {input_data.get('name')}")
    print(f"[TOOL CALL] Input: {input_data.get('input')}")
    # This proves tool was actually invoked

# In test scripts
assert metrics.tool_call_count > 0, "Tool was never called"
assert any("notebooklm" in call for call in metrics.tool_calls), \
    "NotebookLM tool was not called"
```

### Gap 4: Subprocess Error Handling ⭐⭐

**Problem:** NotebookLM calls subprocess (3-5s), can fail

**Current:** No specific error handling for subprocess failures

**Needed:**
```python
try:
    result = subprocess.run([...], timeout=10, capture_output=True)
    if result.returncode != 0:
        return {
            "content": [{
                "type": "text",
                "text": f"NotebookLM query failed: {result.stderr}"
            }],
            "is_error": True
        }
except subprocess.TimeoutExpired:
    return {
        "content": [{
            "type": "text",
            "text": "NotebookLM query timed out after 10s"
        }],
        "is_error": True
    }
```

---

## Testing Strategy

### Unit Tests

```python
def test_tool_name_format():
    """Verify tool name matches between prompt and SDK"""
    runner = AgentSDKRunner(...)
    tools = runner._get_tools_config()
    assert "notebooklm" in tools or "mcp__notebooklm__ask_question" in tools

def test_tool_registration():
    """Verify SDK logs show tool registered"""
    # Capture stdout
    # Assert: "[INFO] NotebookLM工具已注册"

def test_tool_invocation():
    """Verify tool is actually called"""
    result, metrics = await generate_with_sdk(
        topic="测试选题",
        search_results=[],  # Empty to force tool use
        ...
    )
    assert metrics.tool_call_count > 0, "Tool not called"
```

### Integration Tests

```python
def test_end_to_end_tool_call():
    """Full workflow: agent calls tool, gets result, generates article"""
    # 1. Start with empty materials
    # 2. Agent should call NotebookLM
    # 3. Get real results from skill
    # 4. Generate article using results
    # 5. Verify tool_call_count = 1
    # 6. Verify article mentions NotebookLM data

def test_tool_error_handling():
    """Agent handles tool failures gracefully"""
    # Mock NotebookLM skill to return error
    # Verify agent doesn't crash
    # Verify error logged in metrics
```

### Manual Tests

```bash
# Test 1: Empty materials (should force tool use)
USE_AGENT_SDK=true python -m src.cli generate \
  --topic "产品经理为什么要参与技术选型？" \
  --no-search  # Force tool use

# Expect: tool_call_count > 0

# Test 2: Rich materials (agent decides)
USE_AGENT_SDK=true python -m src.cli generate \
  --topic "产品经理为什么要参与技术选型？"  \
  --search  # Pre-retrieve materials

# Expect: tool_call_count = 0 or 1 (agent decides)

# Test 3: Verify tool name
USE_AGENT_SDK=true ANTHROPIC_LOG=debug python -m src.cli generate ...
# Check logs for tool registration format
```

---

## Success Criteria

MVP is complete when:

- [ ] Tool call count > 0 (tools actually invoked)
- [ ] Logs show tool name, input, output, timing
- [ ] Agent handles tool errors without crashing
- [ ] Can distinguish "chose not to call" vs "failed to call"
- [ ] Prompt and SDK use matching tool names
- [ ] Tests verify tool was called (not false positive)

Quality indicators:

- **Reliable:** Tool calling works consistently (>90% success rate)
- **Observable:** Logs prove tool was called with what input
- **Intelligent:** Agent only calls when materials insufficient
- **Resilient:** Graceful handling of subprocess failures
- **Fast:** Tool calls don't add >10s to generation time

---

## Sources

### Official Documentation (HIGH confidence)
- [Agent SDK Custom Tools](https://platform.claude.com/docs/en/agent-sdk/custom-tools) - Tool definition, MCP servers, naming format
- [Agent SDK Skills](https://platform.claude.com/docs/en/agent-sdk/skills) - Skill discovery, filesystem structure, setting_sources
- [Advanced Tool Use](https://www.anthropic.com/engineering/advanced-tool-use) - Tool Search Tool, Programmatic Tool Calling, best practices
- [Implement Tool Use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/implement-tool-use) - Tool definitions, descriptions, workflow, error handling

### Architecture Patterns (MEDIUM confidence)
- [Agent System Design Patterns](https://docs.databricks.com/aws/en/generative-ai/guide/agent-system-design-patterns) - Single agent vs multi-agent, deterministic vs agentic
- [The Ultimate LLM Agent Build Guide](https://www.vellum.ai/blog/the-ultimate-llm-agent-build-guide) - Tool calling mechanics, decision framework
- [Agent Design Patterns](https://rlancemartin.github.io/2026/01/09/agent_design/) - Start simple, progressive disclosure, error handling

### Current Codebase (HIGH confidence)
- `TOOL_CALL_DIAGNOSIS.md` - Complete diagnosis of current issues
- `src/modules/agent_sdk.py` - Current SDK implementation
- `src/modules/generator.py` - Traditional mode (working reference)
- `write_prompt/V1.md` - Current prompt with tool instructions
