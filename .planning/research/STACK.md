# Technology Stack Research

**Project:** WeChat Writer Agent - Agent SDK Tool Calling Fix
**Domain:** Python LLM Agent with Knowledge Base Integration
**Researched:** 2026-01-27
**Confidence:** HIGH (verified with official documentation)

---

## Executive Summary

This research investigates the **Claude Agent SDK tool calling mechanism** and its integration with **MiniMax API** (Anthropic-compatible endpoint) and **subprocess-based tools** (NotebookLM skill).

**Key Finding:** The current implementation has a critical mismatch in how tools are registered. The SDK expects **Skill names** for filesystem-based tools, but requires **explicit configuration** to load Skills from the filesystem.

**Root Cause Identified:** The code passes `["notebooklm"]` as a tool name but **does not configure `setting_sources`** to load Skills from the filesystem. Without `setting_sources=["user", "project"]`, the SDK cannot discover or load Skills from `~/.claude/skills/`.

---

## Core Technologies

### 1. Claude Agent SDK (Python)

**Package:** `claude-agent-sdk` (formerly `claude-code-sdk`)
**Current Version in Use:** 0.x (based on `anthropic>=0.39.0` in requirements.txt)
**Purpose:** Provides agent orchestration with tool calling, session management, and hooks

#### Tool Registration Architecture

The Claude Agent SDK supports **three distinct tool integration patterns**:

##### Pattern A: Built-in Tools (Direct Registration)
```python
# Built-in tools like Read, Write, Bash, Grep, Glob
options = ClaudeAgentOptions(
    allowed_tools=["Read", "Write", "Bash", "Grep"]
)
```
**How it works:** Tool names reference CLI-provided tools. No additional configuration needed.

##### Pattern B: SDK MCP Servers (In-Process)
```python
from claude_agent_sdk import tool, create_sdk_mcp_server

@tool("query_kb", "Query knowledge base", {"question": str})
async def query_kb(args):
    return {"content": [{"type": "text", "text": "Result"}]}

server = create_sdk_mcp_server(
    name="knowledge",
    tools=[query_kb]
)

options = ClaudeAgentOptions(
    mcp_servers={"kb": server},
    allowed_tools=["mcp__kb__query_kb"]  # Format: mcp__{server}__{tool}
)
```
**How it works:** Tools run as Python functions in-process. No subprocess overhead.

##### Pattern C: Skills (Filesystem-Based, Subprocess)
```python
# Skills located in ~/.claude/skills/ or .claude/skills/
options = ClaudeAgentOptions(
    setting_sources=["user", "project"],  # CRITICAL: Required to load Skills
    allowed_tools=["Skill"]               # Enable Skill discovery
)
```
**How it works:**
1. SDK loads `SKILL.md` files from configured directories
2. Skills are subprocess-based (run via Claude CLI)
3. Tool names in Skills are auto-discovered by the SDK
4. Agent can invoke Skills by name

**CRITICAL FINDING:** The current code **fails at step 1** because `setting_sources` is not configured.

#### Current Code Analysis

**File:** `src/modules/agent_sdk.py:71-86`

```python
def _get_tools_config(self) -> List[str]:
    if not self.notebook_id:
        return []
    return ["notebooklm"]  # ❌ Returns Skill name but...

options = ClaudeAgentOptions(
    model=self.model,
    tools=tools if tools else None,  # ❌ Wrong parameter name
    # setting_sources=["user", "project"],  # ❌ MISSING - Skills won't load
    hooks=hooks,
    system_prompt=system_prompt
)
```

**Issues Identified:**

1. **Missing `setting_sources`**: Without this, SDK never loads Skills from filesystem
2. **Wrong parameter name**: Should use `allowed_tools`, not `tools`
3. **Tool name format unclear**: Should be `"Skill"` to enable all Skills, or `"notebooklm"` if that's the Skill's directory name

#### Correct Implementation (Pattern C - Skills)

```python
options = ClaudeAgentOptions(
    model=self.model,
    max_turns=max_turns,
    setting_sources=["user", "project"],  # ✅ Load Skills from filesystem
    allowed_tools=["Skill", "Read", "Write"],  # ✅ Enable Skill tool + others
    hooks=hooks,
    system_prompt=system_prompt,
    env=env_vars
)
```

**Explanation:**
- `setting_sources=["user", "project"]` tells SDK to scan `~/.claude/skills/` and `.claude/skills/`
- `allowed_tools=["Skill"]` enables the Skill discovery mechanism
- SDK auto-discovers `notebooklm` Skill from `~/.claude/skills/notebooklm/SKILL.md`
- Agent can then call tools defined in that Skill

#### Alternative Implementation (Pattern B - SDK MCP Server)

If subprocess overhead is a concern, convert NotebookLM to an in-process tool:

```python
from claude_agent_sdk import tool, create_sdk_mcp_server
import subprocess
import json

@tool(
    "query_notebooklm",
    "Query NotebookLM knowledge base for information",
    {"question": str}
)
async def query_notebooklm(args):
    """Wrapper that calls NotebookLM skill via subprocess"""
    result = subprocess.run([
        "python3",
        os.path.expanduser("~/.claude/skills/notebooklm/scripts/run.py"),
        "ask_question.py",
        "--question", args["question"],
        "--notebook-id", os.getenv("NOTEBOOK_ID")
    ], capture_output=True, text=True, timeout=30)

    if result.returncode != 0:
        return {
            "content": [{"type": "text", "text": f"Error: {result.stderr}"}],
            "is_error": True
        }

    return {
        "content": [{"type": "text", "text": result.stdout}]
    }

notebooklm_server = create_sdk_mcp_server(
    name="notebooklm",
    version="1.0.0",
    tools=[query_notebooklm]
)

options = ClaudeAgentOptions(
    mcp_servers={"notebooklm": notebooklm_server},
    allowed_tools=["mcp__notebooklm__query_notebooklm"],
    system_prompt=system_prompt
)
```

**Tradeoffs:**
- ✅ More control over tool execution
- ✅ Better error handling
- ✅ Metrics collection easier
- ❌ More code to maintain
- ❌ Still subprocess overhead (but more visible)

---

### 2. MiniMax API (Anthropic Compatibility)

**Endpoint:** `https://api.minimaxi.com/anthropic` (configured via `ANTHROPIC_BASE_URL`)
**Models:** MiniMax-M2.1, MiniMax-M2.1-lightning, MiniMax-M2
**Purpose:** Anthropic-compatible API endpoint for Claude SDK

#### Tool Use Compatibility

**Status:** ✅ **FULLY SUPPORTED**

MiniMax API implements Anthropic's tool use protocol completely:
- ✅ `tools` parameter with tool definitions
- ✅ `tool_choice` parameter for forced tool use
- ✅ `tool_use` content blocks in responses
- ✅ `tool_result` blocks in follow-up messages
- ✅ Multi-turn tool conversations

**Source:** [MiniMax Anthropic API Documentation](https://platform.minimax.io/docs/api-reference/text-anthropic-api)

#### Key Differences from Official Anthropic API

**Unsupported Features:**
- ❌ Image inputs (`image` content blocks)
- ❌ Document inputs (PDF, etc.)
- ❌ Parameters: `top_k`, `stop_sequences`, `service_tier`, `mcp_servers`, `context_management`, `container`

**Parameter Constraints:**
- **Temperature:** Must be in range `(0.0, 1.0]` (exclusive of 0.0)
  - Official Anthropic: `[0.0, 1.0]`
  - Current code uses `0.7` ✅ (within valid range)

**Critical Requirement for Multi-Turn Tool Conversations:**
> "In multi-turn function call conversations, the complete model response must be appended to the conversation history to maintain the continuity of the reasoning chain, including all content blocks: thinking/text/tool_use."

**Implication:** The SDK likely handles this automatically, but custom implementations must preserve full assistant messages.

#### Compatibility Verdict

**For this project:** ✅ **No blockers from MiniMax API**

The tool calling failure is **NOT due to MiniMax API limitations**. The API fully supports tool use. The issue is in SDK configuration.

---

### 3. NotebookLM Integration (Subprocess Tool)

**Location:** `~/.claude/skills/notebooklm/`
**Type:** Claude Code Skill (filesystem-based)
**Invocation:** Subprocess via Python scripts
**Status:** ✅ **Tool itself works** (verified in TOOL_CALL_DIAGNOSIS.md)

#### Skill Structure

```
~/.claude/skills/notebooklm/
├── SKILL.md                    # Skill definition (metadata, description)
├── scripts/
│   ├── run.py                  # Entry point for tool invocation
│   ├── ask_question.py         # Query handler
│   ├── notebook_manager.py     # Notebook CRUD operations
│   └── ...
└── data/                       # Notebook metadata storage
```

#### Tool Definition in SKILL.md

The `SKILL.md` file should contain YAML frontmatter like:

```yaml
---
name: notebooklm
description: Query Google NotebookLM knowledge base for information, cases, and insights
tools:
  - name: ask_question
    description: Ask a natural language question to the knowledge base
    input_schema:
      type: object
      properties:
        question:
          type: string
          description: Natural language question
        notebook-id:
          type: string
          description: Notebook identifier
      required:
        - question
---
```

**Note:** The exact format depends on the Skill's SKILL.md file. If not present, the SDK may not discover the tool.

#### Direct Testing (Works ✅)

```bash
python3 ~/.claude/skills/notebooklm/scripts/run.py ask_question.py \
  --question "产品经理为什么要参与技术选型？" \
  --notebook-id "my-knowledge"
```

**Result:** Returns ~2000 characters of relevant content

**Conclusion:** The tool itself is functional. The problem is SDK-level tool registration.

---

## Recommended Stack Configuration

### Primary Recommendation: Fix Skills Integration

**Why:** Minimal code changes, leverages existing infrastructure

**Changes Required:**

1. **Add `setting_sources` to SDK options**
2. **Use `allowed_tools` instead of `tools` parameter**
3. **Ensure SKILL.md is properly formatted**

**Implementation:**

```python
# src/modules/agent_sdk.py

class AgentSDKRunner:
    def __init__(self, api_key, model, temperature, notebook_id=None, notebook_url=None):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.notebook_id = notebook_id
        self.notebook_url = notebook_url

    def _get_allowed_tools(self) -> List[str]:
        """Get list of allowed tools"""
        tools = []

        if self.notebook_id:
            # Enable Skill discovery
            tools.append("Skill")
            print(f"[INFO] NotebookLM Skill enabled (notebook_id={self.notebook_id[:20]}...)")
        else:
            print("[WARNING] notebook_id未设置，NotebookLM工具未启用")

        return tools

    async def generate(self, topic, search_results, system_prompt, max_turns=10):
        metrics = AgentRunMetrics()
        metrics.system_prompt = system_prompt

        user_message = self._build_user_message(topic, search_results)
        metrics.initial_user_message = user_message

        # Get allowed tools
        allowed_tools = self._get_allowed_tools()

        # Create hooks configuration
        hooks = self._create_hooks(metrics)

        # Configure SDK options with Skills support
        env_vars = {}
        if os.getenv("ANTHROPIC_BASE_URL"):
            env_vars["ANTHROPIC_BASE_URL"] = os.getenv("ANTHROPIC_BASE_URL")

        options = ClaudeAgentOptions(
            model=self.model,
            max_turns=max_turns,
            setting_sources=["user", "project"],  # ✅ Load Skills from filesystem
            allowed_tools=allowed_tools,          # ✅ Enable Skill + others
            hooks=hooks,
            system_prompt=system_prompt,
            env=env_vars,
            temperature=self.temperature  # May need to pass via env or check SDK support
        )

        # Call SDK query
        result_text = ""
        async for message in query(prompt=user_message, options=options):
            # [Message handling code remains same]
            ...

        metrics.end_time = time.time()
        return result_text, metrics
```

**Additional Changes:**

1. **Verify SKILL.md format** in `~/.claude/skills/notebooklm/SKILL.md`
2. **Update prompt** to reference correct tool name (if needed)
3. **Test tool discovery** with `query(prompt="What Skills are available?")`

### Alternative: Convert to SDK MCP Server

**Why:** If Skills approach fails or needs more control

See "Alternative Implementation (Pattern B)" section above for complete code.

**Tradeoffs:**
- More code to maintain
- Better error handling and metrics
- No dependency on filesystem Skill loading

---

## Technology Versions and Compatibility

| Component | Version | Source | Notes |
|-----------|---------|--------|-------|
| **Python** | 3.13.3 | Local environment | ✅ Compatible |
| **anthropic SDK** | ≥0.39.0 | requirements.txt | Base SDK for API calls |
| **claude-agent-sdk** | 0.x (latest) | Inferred from code | Not in requirements.txt ❌ |
| **MiniMax API** | M2.1 | .env.example | ✅ Tool use fully supported |
| **NotebookLM Skill** | Custom | ~/.claude/skills/ | ✅ Verified working via subprocess |

### Critical Missing Dependency

**Issue:** `claude-agent-sdk` is **NOT in requirements.txt**

**Current requirements.txt:**
```txt
anthropic>=0.39.0
python-dotenv>=1.0.0
requests>=2.31.0
pytest>=7.4.0
pytest-timeout>=2.1.0
pytest-mock>=3.11.0
pytest-cov>=4.1.0
```

**Should be:**
```txt
anthropic>=0.39.0
claude-agent-sdk>=0.8.0  # ✅ Add this
python-dotenv>=1.0.0
requests>=2.31.0
pytest>=7.4.0
pytest-timeout>=2.1.0
pytest-mock>=3.11.0
pytest-cov>=4.1.0
```

**Installation:**
```bash
pip install claude-agent-sdk
```

---

## Logging and Metrics Collection

### Current Hook System

**Status:** ✅ **Well-designed** for tool call tracking

**Architecture:**
- `AgentRunMetrics` dataclass tracks tool calls, tokens, runtime
- Hooks inject metrics instance via closures
- `PreToolUse` / `PostToolUse` capture tool execution
- `LogDocumentGenerator` creates markdown reports

**Current Hooks:**
```python
hooks = {
    "PreToolUse": [HookMatcher(hooks=[pre_tool_use_hook])],
    "PostToolUse": [HookMatcher(hooks=[post_tool_use_hook])],
    "Stop": [HookMatcher(hooks=[stop_hook], timeout=180)],
    "UserPromptSubmit": [HookMatcher(hooks=[user_prompt_submit_hook])]
}
```

**Issue:** Hooks will only fire **if tools are actually called**. With current config, tools never get called, so hooks never run.

### Metrics to Track

**Currently Tracked:**
- ✅ Tool call count (`tool_call_count`)
- ✅ Tool execution duration (`duration_ms` per call)
- ✅ Tool input/output (stored in `tool_calls` list)
- ✅ Token usage (prompt, completion, total)
- ✅ Runtime (start/end time)

**After Fix, Will Automatically Track:**
- Skill invocation count
- Skill execution time
- Skill input (question) and output (retrieved content)
- Multi-turn tool conversations

**No Changes Needed:** The existing hooks system is SDK-agnostic and will work once tools are properly registered.

---

## Known Issues and Solutions

### Issue 1: Skills Not Loading ⭐⭐⭐⭐⭐ CRITICAL

**Symptom:** `tool_call_count: 0`, no tool invocations

**Root Cause:** Missing `setting_sources` in `ClaudeAgentOptions`

**Solution:**
```python
options = ClaudeAgentOptions(
    setting_sources=["user", "project"],  # Add this line
    allowed_tools=["Skill"],
    # ... rest of options
)
```

**Confidence:** HIGH (verified in official documentation)

### Issue 2: Wrong Parameter Name ⭐⭐⭐⭐

**Symptom:** `tools` parameter not recognized (may be ignored)

**Root Cause:** SDK uses `allowed_tools`, not `tools`

**Solution:**
```python
# Wrong
options = ClaudeAgentOptions(
    tools=["notebooklm"]  # ❌
)

# Correct
options = ClaudeAgentOptions(
    allowed_tools=["Skill"]  # ✅
)
```

**Confidence:** HIGH (verified in SDK reference docs)

### Issue 3: Tool Name Mismatch ⭐⭐⭐

**Symptom:** Even with `setting_sources`, tool not found

**Root Cause:** Prompt references `query_notebooklm`, but Skill may define different tool name

**Solution:**
1. Check `~/.claude/skills/notebooklm/SKILL.md` for actual tool name
2. Update prompt to match (e.g., `notebooklm` or `ask_question`)
3. Or use generic `"Skill"` and let Agent discover tools

**Confidence:** MEDIUM (depends on SKILL.md contents)

### Issue 4: Missing SDK Dependency ⭐⭐⭐⭐⭐ CRITICAL

**Symptom:** Import fails or wrong SDK version

**Root Cause:** `claude-agent-sdk` not in requirements.txt

**Solution:**
```bash
pip install claude-agent-sdk
echo "claude-agent-sdk>=0.8.0" >> requirements.txt
```

**Confidence:** HIGH

### Issue 5: Temperature Parameter ⭐⭐

**Symptom:** Temperature setting may be ignored

**Root Cause:** `ClaudeAgentOptions` may not have direct `temperature` parameter

**Solution:**
```python
# Check if SDK supports temperature parameter
# If not, may need to pass via env or use different approach
options = ClaudeAgentOptions(
    model=self.model,
    # temperature=self.temperature,  # May not be supported
    env={"ANTHROPIC_TEMPERATURE": str(self.temperature)},  # Alternative
    ...
)
```

**Confidence:** LOW (needs SDK version-specific verification)

---

## Implementation Roadmap

### Phase 1: Quick Fix (1 hour)

**Goal:** Get Skills loading and tool calls working

**Steps:**
1. Add `claude-agent-sdk>=0.8.0` to requirements.txt
2. Run `pip install claude-agent-sdk`
3. Update `AgentSDKRunner._get_tools_config()` → `_get_allowed_tools()`
4. Add `setting_sources=["user", "project"]` to `ClaudeAgentOptions`
5. Change `tools=` to `allowed_tools=`
6. Test with empty pre-search results to force tool call

**Expected Result:** `tool_call_count > 0` in logs

### Phase 2: Validation (30 minutes)

**Goal:** Verify tool integration works end-to-end

**Steps:**
1. Run agent with topic requiring knowledge base query
2. Check logs for tool invocations
3. Verify retrieved content quality
4. Ensure hooks capture metrics correctly

**Expected Result:** Agent autonomously calls NotebookLM when needed

### Phase 3: Polish (1 hour)

**Goal:** Improve error handling and observability

**Steps:**
1. Add try-catch around Skill loading
2. Add fallback if Skills not found
3. Improve logging (tool discovery, invocation, errors)
4. Document configuration requirements in README

**Expected Result:** Production-ready integration

---

## Testing Strategy

### Unit Tests

```python
# tests/test_agent_sdk_tools.py

async def test_skills_loading():
    """Verify Skills are loaded when setting_sources configured"""
    runner = AgentSDKRunner(
        api_key="test",
        model="test",
        temperature=0.7,
        notebook_id="test-id"
    )

    allowed_tools = runner._get_allowed_tools()
    assert "Skill" in allowed_tools

async def test_tool_discovery():
    """Verify SDK can discover NotebookLM Skill"""
    options = ClaudeAgentOptions(
        setting_sources=["user"],
        allowed_tools=["Skill"]
    )

    async for message in query(
        prompt="What Skills are available?",
        options=options
    ):
        # Should mention notebooklm in response
        pass
```

### Integration Tests

```python
# tests/test_integration.py

async def test_tool_invocation():
    """Verify Agent calls NotebookLM when needed"""
    runner = AgentSDKRunner(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        model="MiniMax-M2.1",
        temperature=0.7,
        notebook_id=os.getenv("NOTEBOOK_ID")
    )

    result, metrics = await runner.generate(
        topic="AI产品经理的技术选型方法",
        search_results=[],  # Empty to force tool call
        system_prompt="必须查询知识库",
        max_turns=5
    )

    assert metrics.tool_call_count > 0, "Tool should be called"
    assert any("notebooklm" in tc.get("tool_name", "") for tc in metrics.tool_calls)
```

---

## Configuration Examples

### Minimal Working Configuration

```python
# .env
ANTHROPIC_API_KEY=your-minimax-api-key
ANTHROPIC_BASE_URL=https://api.minimaxi.com/anthropic
ANTHROPIC_MODEL=MiniMax-M2.1
NOTEBOOK_ID=your-notebook-id
USE_AGENT_SDK=true

# src/modules/agent_sdk.py
options = ClaudeAgentOptions(
    model=self.model,
    max_turns=max_turns,
    setting_sources=["user"],  # Load Skills from ~/.claude/skills/
    allowed_tools=["Skill"],   # Enable Skill discovery
    system_prompt=system_prompt,
    env={"ANTHROPIC_BASE_URL": os.getenv("ANTHROPIC_BASE_URL")}
)
```

### Advanced Configuration (Multiple Tools)

```python
options = ClaudeAgentOptions(
    model=self.model,
    max_turns=max_turns,
    setting_sources=["user", "project"],
    allowed_tools=[
        "Skill",      # All Skills
        "Read",       # File reading
        "Grep",       # Code search
        "WebSearch"   # Web search (if needed)
    ],
    hooks=hooks,
    system_prompt=system_prompt,
    permission_mode="default",  # Require approval for edits
    env={
        "ANTHROPIC_BASE_URL": os.getenv("ANTHROPIC_BASE_URL"),
        "NOTEBOOK_ID": self.notebook_id
    }
)
```

---

## Performance Considerations

### Subprocess Overhead

**NotebookLM Skill invocation:**
- Process spawn: ~50-100ms
- Query execution: ~500-2000ms (depends on NotebookLM API)
- Total overhead: ~600-2100ms per call

**Optimization options:**
1. **Keep as Skill** (current): Simple, but subprocess overhead
2. **Convert to SDK MCP Server**: More code, same subprocess overhead
3. **Direct async integration**: Rewrite NotebookLM client in Python (most performant)

**Recommendation:** Keep as Skill for now (simplest fix). Consider optimization if performance becomes an issue.

### Token Usage with Extended Thinking

MiniMax M2.1 supports `thinking` content blocks (extended reasoning). This increases token usage but may improve tool use decisions.

**To enable thinking:**
```python
# In system prompt or via API parameter (if SDK supports)
# May increase prompt tokens by 20-50%
```

**Recommendation:** Test with and without thinking. May not be necessary if tool descriptions are clear.

---

## Migration Notes (from Traditional Mode)

### Traditional Mode (generator.py)

```python
# Works correctly with MiniMax API
tools = [{
    "name": "query_notebooklm",
    "description": "查询 NotebookLM 知识库",
    "input_schema": {
        "type": "object",
        "properties": {"question": {"type": "string"}},
        "required": ["question"]
    }
}]

response = client.messages.create(
    model=model,
    tools=tools,  # Direct tool definition
    messages=messages
)
```

**Why it works:**
- Tools defined inline with full schema
- Direct API call (no SDK layer)
- MiniMax API handles tool use correctly

### SDK Mode (agent_sdk.py)

```python
# Current (broken)
tools = ["notebooklm"]  # Just a name, SDK can't find it
options = ClaudeAgentOptions(tools=tools)  # Wrong parameter

# Fixed
options = ClaudeAgentOptions(
    setting_sources=["user"],  # Tell SDK where to find Skills
    allowed_tools=["Skill"]    # Enable Skill loading
)
```

**Key Difference:**
- SDK mode uses **indirection** (Skills in filesystem)
- Requires **explicit configuration** to load Skills
- More powerful (can update tools without code changes) but more setup

---

## Sources

### Official Documentation (HIGH Confidence)

- [Agent Skills in the SDK - Claude Docs](https://platform.claude.com/docs/en/agent-sdk/skills)
- [Agent SDK Reference - Python - Claude Docs](https://platform.claude.com/docs/en/agent-sdk/python)
- [MiniMax Anthropic API - Official Docs](https://platform.minimax.io/docs/api-reference/text-anthropic-api)
- [GitHub - anthropics/claude-agent-sdk-python](https://github.com/anthropics/claude-agent-sdk-python)

### Additional Resources (MEDIUM Confidence)

- [Agent SDK Overview - Claude Docs](https://platform.claude.com/docs/en/agent-sdk/overview)
- [Connect to External Tools with MCP - Claude Docs](https://platform.claude.com/docs/en/agent-sdk/mcp)
- [GitHub - anthropics/claude-agent-sdk-demos](https://github.com/anthropics/claude-agent-sdk-demos)

### Community Resources (LOW Confidence - Not Used)

- Medium articles and blog posts (verified against official docs)

---

## Confidence Assessment

| Area | Confidence | Rationale |
|------|------------|-----------|
| **Root Cause** | HIGH | Verified in official SDK docs: Skills require `setting_sources` |
| **Fix Strategy** | HIGH | Direct code examples from SDK reference |
| **MiniMax Compatibility** | HIGH | Official API docs confirm full tool use support |
| **NotebookLM Integration** | HIGH | Direct testing shows tool works via subprocess |
| **Performance Impact** | MEDIUM | Subprocess overhead estimates, not measured |
| **Alternative Approaches** | MEDIUM | SDK MCP pattern documented but not tested in this project |

---

## Next Steps for Milestone

1. **Immediate Fix** (Required):
   - Add `claude-agent-sdk` to requirements.txt
   - Update `ClaudeAgentOptions` with `setting_sources` and `allowed_tools`
   - Test tool invocation

2. **Validation** (Recommended):
   - Write integration test for tool calling
   - Verify hooks capture metrics
   - Document configuration in README

3. **Future Optimization** (Optional):
   - Consider converting to SDK MCP server if performance is an issue
   - Add retry logic for tool failures
   - Implement tool result caching

---

## Glossary

**Skill:** Filesystem-based tool definition in `.claude/skills/` or `~/.claude/skills/`
**SDK MCP Server:** In-process tool server using `@tool` decorator
**MCP (Model Context Protocol):** Standard for tool/resource providers
**setting_sources:** SDK parameter to specify where to load settings/Skills from
**allowed_tools:** SDK parameter to whitelist which tools the Agent can use
**Hook:** Callback function invoked at specific SDK lifecycle events
