# Architecture Research: Agent SDK Tool Calling

**Domain:** Agent SDK Tool Calling with Subprocess Integration
**Researched:** 2026-01-27
**Confidence:** HIGH

## Current Architecture

### System Overview (AS-IS)

```
┌─────────────────────────────────────────────────────────────┐
│                      Pipeline Layer                          │
│  ┌──────────┐ ┌──────────┐ ┌─────────┐ ┌─────────┐         │
│  │ Retrieval│→│Generator │→│Document │→│  Table  │         │
│  └────┬─────┘ └────┬─────┘ └─────────┘ └─────────┘         │
│       │            │                                         │
│       │            │ (dual mode)                             │
│       │            ├─────────┐                               │
├───────┴────────────┴─────────┴───────────────────────────────┤
│                   Generation Layer                            │
│  ┌─────────────────────┐  ┌─────────────────────────┐        │
│  │  Traditional Mode   │  │    Agent SDK Mode       │        │
│  │  (Messages API)     │  │  (query() with tools)   │        │
│  │  - Manual loop      │  │  - Autonomous loop      │        │
│  │  - Tools handled    │  │  - BROKEN: tools not    │        │
│  │    manually         │  │    registered properly  │        │
│  └─────────────────────┘  └──────────┬──────────────┘        │
│                                      │                        │
├──────────────────────────────────────┴────────────────────────┤
│                   Tool Layer (Hybrid)                         │
│  ┌────────────────────────────────────────────────┐           │
│  │  NotebookLM Retrieval (Subprocess)             │           │
│  │  - Lives at ~/.claude/skills/notebooklm/       │           │
│  │  - Called via subprocess.run()                 │           │
│  │  - Returns SearchResult                        │           │
│  └────────────────────────────────────────────────┘           │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│                   Hooks Layer                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐          │
│  │PreToolUse    │ │PostToolUse   │ │Stop/Submit   │          │
│  │(start time)  │ │(metrics)     │ │(finalize)    │          │
│  └──────────────┘ └──────────────┘ └──────────────┘          │
│  ↓ Collects metrics into AgentRunMetrics                      │
│  ↓ Generates markdown logs via LogDocumentGenerator           │
└────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Current Implementation |
|-----------|----------------|------------------------|
| `main.py` / `cli.py` | Entry point, orchestrates pipeline | Calls pipeline steps sequentially |
| `src/modules/retrieval.py` | Pre-retrieval via NotebookLM subprocess | subprocess.run() to skill scripts |
| `src/modules/generator.py` | Dual-mode generation orchestrator | `generate()` (traditional) vs `generate_with_sdk()` |
| `src/modules/agent_sdk.py` | Agent SDK wrapper with hooks | AgentSDKRunner, query() call, tools=[strings] |
| `src/hooks/logging_hooks.py` | Lifecycle event handlers | Pre/Post/Stop hooks inject metrics |
| `src/hooks/log_generator.py` | Metrics to markdown conversion | LogDocumentGenerator |
| `notebooklm_tool.py` | NotebookLM wrapper (unused) | Tool definition + subprocess call |
| `~/.claude/skills/notebooklm/` | External skill (subprocess) | Python scripts via run.py wrapper |

## Problem Analysis

### Current Issue: Tool Registration Mismatch

**What's broken:**
```python
# In agent_sdk.py, line 86
def _get_tools_config(self) -> List[str]:
    return ["notebooklm"]  # Returns skill name as string
```

**Why it fails:**
1. SDK expects **skill names** to match installed skills in `~/.claude/skills/`
2. Skill discovery requires `setting_sources=["user", "project"]` configuration
3. Current code assumes skill name alone is sufficient (it's not)
4. Missing: MCP server registration for subprocess tools

### Root Cause

The Agent SDK has **two distinct tool systems**:

1. **Skills** (filesystem-based, discovered from `~/.claude/skills/`)
   - Enabled via: `allowed_tools=["Skill", ...]`
   - Requires: `setting_sources=["user", "project"]`
   - Format: Tool name as string
   - Discovery: Automatic from SKILL.md files

2. **Custom MCP Tools** (programmatic, in-process or external)
   - Enabled via: `mcp_servers={"server-name": McpServerConfig}`
   - Format: Tool referenced as `mcp__server-name__tool-name`
   - Discovery: Registered explicitly in code

**Current code mixes these systems incorrectly:**
- Returns `["notebooklm"]` expecting it to work as a skill
- NotebookLM is NOT registered as a filesystem skill with SKILL.md
- NotebookLM is NOT registered as an MCP server
- Result: SDK can't find the tool at all

## Recommended Architecture (TO-BE)

### Approach 1: External MCP Server (Subprocess Pattern)

**Best for:** Preserving subprocess isolation, matching skill architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Agent SDK Layer                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  query() with mcp_servers configuration             │   │
│  └───────────────────────┬──────────────────────────────┘   │
├──────────────────────────┴───────────────────────────────────┤
│                   MCP Server Registry                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  External MCP Server: "notebooklm"                   │   │
│  │  - Type: StdioServerParameters                       │   │
│  │  - Command: ["python", "run.py", "mcp_server.py"]   │   │
│  │  - Cwd: ~/.claude/skills/notebooklm/                │   │
│  └────────────────────┬─────────────────────────────────┘   │
├───────────────────────┴──────────────────────────────────────┤
│                   Tool Executor                              │
│  SDK sends tool request                                      │
│     ↓                                                         │
│  Spawns subprocess with MCP protocol                         │
│     ↓                                                         │
│  Subprocess executes ask_question.py                         │
│     ↓                                                         │
│  Returns result via stdout (MCP format)                      │
│     ↓                                                         │
│  SDK receives and processes result                           │
└───────────────────────────────────────────────────────────────┘
```

**Implementation:**
```python
# In agent_sdk.py
from claude_agent_sdk import StdioServerParameters

def _get_mcp_servers(self) -> dict:
    if not self.notebook_id:
        return {}

    skill_dir = Path.home() / ".claude" / "skills" / "notebooklm"

    return {
        "notebooklm": StdioServerParameters(
            command=["python", str(skill_dir / "scripts" / "run.py"), "mcp_server.py"],
            cwd=str(skill_dir),
            env={
                "NOTEBOOK_ID": self.notebook_id,
                "NOTEBOOK_URL": self.notebook_url or ""
            }
        )
    }

# In ClaudeAgentOptions
options = ClaudeAgentOptions(
    model=self.model,
    max_turns=max_turns,
    mcp_servers=self._get_mcp_servers(),
    allowed_tools=["mcp__notebooklm__query"],  # MCP tool reference format
    hooks=hooks,
    system_prompt=system_prompt
)
```

**New file needed:** `~/.claude/skills/notebooklm/scripts/mcp_server.py`
- Implements MCP server protocol
- Wraps existing ask_question.py logic
- Communicates via stdio with MCP JSON-RPC format

### Approach 2: In-Process MCP Server (Hybrid Pattern)

**Best for:** Simplicity, avoiding subprocess overhead

```
┌─────────────────────────────────────────────────────────────┐
│                   Agent SDK Layer                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  query() with mcp_servers configuration             │   │
│  └───────────────────────┬──────────────────────────────┘   │
├──────────────────────────┴───────────────────────────────────┤
│                   MCP Server Registry                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  SDK MCP Server: "notebooklm" (in-process)          │   │
│  │  - Created with create_sdk_mcp_server()             │   │
│  │  - Tool: "query" with handler function              │   │
│  └────────────────────┬─────────────────────────────────┘   │
├───────────────────────┴──────────────────────────────────────┤
│                   Tool Handler (Python)                      │
│  SDK calls handler function directly                         │
│     ↓                                                         │
│  Handler calls retrieval.search()                            │
│     ↓                                                         │
│  retrieval.search() spawns subprocess                        │
│     ↓                                                         │
│  Returns SearchResult                                        │
│     ↓                                                         │
│  Handler formats as MCP response                             │
└───────────────────────────────────────────────────────────────┘
```

**Implementation:**
```python
# In agent_sdk.py
from claude_agent_sdk import create_sdk_mcp_server, tool
from src.modules import retrieval

def _create_notebooklm_tool(self):
    @tool(
        name="query",
        description="Query NotebookLM knowledge base for relevant information, cases, and insights."
    )
    async def query_notebooklm(question: str) -> dict:
        """
        Args:
            question: The question or keyword to search for
        """
        try:
            results = retrieval.search(
                query=question,
                notebook_id=self.notebook_id,
                notebook_url=self.notebook_url
            )
            if results:
                return {
                    "content": [{
                        "type": "text",
                        "text": results[0].content
                    }]
                }
            else:
                return {
                    "content": [{
                        "type": "text",
                        "text": "No relevant content found."
                    }]
                }
        except Exception as e:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Query failed: {str(e)}"
                }]
            }

    return create_sdk_mcp_server(
        name="notebooklm",
        version="1.0.0",
        tools=[query_notebooklm]
    )

# In ClaudeAgentOptions
mcp_servers = {}
if self.notebook_id:
    mcp_servers["notebooklm"] = self._create_notebooklm_tool()

options = ClaudeAgentOptions(
    model=self.model,
    max_turns=max_turns,
    mcp_servers=mcp_servers,
    allowed_tools=["mcp__notebooklm__query"],
    hooks=hooks,
    system_prompt=system_prompt
)
```

### Approach 3: Skill Registration (Pure Skill Pattern)

**Best for:** Leveraging existing skill ecosystem, no code changes to SDK wrapper

**Requirements:**
1. Move NotebookLM to proper skill structure
2. Create proper SKILL.md file
3. Register as filesystem skill

**Implementation:**
```
~/.claude/skills/notebooklm/
├── SKILL.md                      # Skill metadata (MUST EXIST)
├── scripts/
│   ├── run.py                    # Existing wrapper
│   ├── ask_question.py           # Existing query script
│   └── ... (other scripts)
└── data/                         # Existing data dir
```

**SKILL.md format:**
```markdown
---
name: notebooklm
description: Query NotebookLM knowledge base for source-grounded answers
---

# NotebookLM Tool

Query your NotebookLM notebooks directly for citation-backed answers.

## When to Use
- Need domain-specific knowledge from uploaded documents
- Want source-grounded responses to reduce hallucinations
- Require citations from specific notebooks

## Tool Definition

### query_notebooklm

Query the NotebookLM knowledge base.

**Parameters:**
- `question` (string, required): The question or keyword to search for

**Example:**
```
query_notebooklm(question="What are the key insights about AI agents?")
```
```

**Code changes:**
```python
# In agent_sdk.py
options = ClaudeAgentOptions(
    model=self.model,
    max_turns=max_turns,
    setting_sources=["user", "project"],  # Enable skill discovery
    allowed_tools=["Skill"],              # Enable Skill meta-tool
    hooks=hooks,
    system_prompt=system_prompt
)
```

**Note:** This approach currently WON'T work because NotebookLM skill doesn't expose programmatic tool definitions. Skills are primarily prompt-based, not executable tools.

## Recommended Approach: Approach 2 (In-Process MCP)

**Rationale:**

1. **Minimal changes**: Keeps subprocess call in retrieval.py
2. **Best compatibility**: Works with existing code structure
3. **Simpler debugging**: All in one process, easier to trace
4. **Hooks work correctly**: MCP tool calls trigger Pre/Post hooks
5. **No new files**: Doesn't require new MCP server script

**Trade-offs:**
- Subprocess call inside in-process handler (hybrid pattern)
- Not "pure" in-process (still spawns subprocess internally)

**Why not Approach 1 (External MCP)?**
- Requires new mcp_server.py script implementing MCP protocol
- More complex: double subprocess (SDK spawns server, server spawns skill)
- Harder to debug: multiple process boundaries

**Why not Approach 3 (Pure Skill)?**
- NotebookLM skill doesn't expose executable tools yet
- Would require skill rewrite to support programmatic invocation
- Skills are primarily prompt-based, not tool-based

## Architectural Patterns

### Pattern 1: In-Process MCP Tool Wrapping Subprocess

**What:** SDK MCP server runs in-process, but delegates to subprocess tool

**When to use:** When you have existing subprocess-based tools but need SDK integration

**Trade-offs:**
- Pro: Preserves existing subprocess isolation
- Pro: Simple integration layer
- Pro: Subprocess tool can be used by both SDK and traditional mode
- Con: Subprocess overhead remains
- Con: Hybrid pattern (not pure in-process)

**Example:**
```python
from claude_agent_sdk import create_sdk_mcp_server, tool
from src.modules import retrieval

@tool(name="query", description="Query knowledge base")
async def query_tool(question: str) -> dict:
    # In-process handler delegates to subprocess tool
    results = retrieval.search(query=question, notebook_id=self.notebook_id)
    return {"content": [{"type": "text", "text": results[0].content}]}

# Register in-process MCP server
mcp_server = create_sdk_mcp_server(
    name="notebooklm",
    version="1.0.0",
    tools=[query_tool]
)
```

### Pattern 2: Hook Injection via Lambda Closures

**What:** Pass stateful metrics object to hooks via lambda closures

**When to use:** When hooks need to share state across lifecycle events

**Trade-offs:**
- Pro: Clean separation of concerns
- Pro: Metrics object lifecycle managed externally
- Pro: Hooks remain stateless functions
- Con: Lambda allocation overhead
- Con: Metrics must be thread-safe if used concurrently

**Example:**
```python
metrics = AgentRunMetrics()

hooks = {
    "PreToolUse": [
        HookMatcher(
            hooks=[lambda input_data, tool_use_id, context:
                   pre_tool_use_hook(input_data, tool_use_id, context, metrics)]
        )
    ],
    "PostToolUse": [
        HookMatcher(
            hooks=[lambda input_data, tool_use_id, context:
                   post_tool_use_hook(input_data, tool_use_id, context, metrics)]
        )
    ]
}
```

### Pattern 3: Tool Reference Naming Convention

**What:** MCP tools use naming pattern `mcp__server-name__tool-name`

**When to use:** When allowing specific MCP tools (not all tools from a server)

**Trade-offs:**
- Pro: Fine-grained tool access control
- Pro: Explicit about which tools are allowed
- Con: Must know exact tool names
- Con: Verbose for servers with many tools

**Example:**
```python
options = ClaudeAgentOptions(
    mcp_servers={
        "notebooklm": notebooklm_server,
        "database": database_server
    },
    allowed_tools=[
        "mcp__notebooklm__query",      # Only query from notebooklm
        "mcp__database__read",          # Only read from database
        # "mcp__database__write" is NOT allowed
    ]
)
```

## Data Flow

### Current Flow (Broken)

```
User Request
    ↓
retrieval.search(topic)  [Pre-retrieval via subprocess]
    ↓
generate_with_sdk(topic, results)
    ↓
AgentSDKRunner.generate()
    ↓
query(prompt, options={tools: ["notebooklm"]})  ← FAILS HERE
    ↓
Agent tries to find "notebooklm" tool
    ↓
Tool not found (not registered as Skill or MCP)
    ↓
Agent continues without tool calls
    ↓
Returns article without additional retrieval
```

### Recommended Flow (In-Process MCP)

```
User Request
    ↓
retrieval.search(topic)  [Pre-retrieval via subprocess]
    ↓
generate_with_sdk(topic, results)
    ↓
AgentSDKRunner.generate()
    ↓
Creates in-process MCP server with retrieval wrapper
    ↓
query(prompt, options={
    mcp_servers: {"notebooklm": in_process_server},
    allowed_tools: ["mcp__notebooklm__query"]
})
    ↓
Agent decides to call tool
    ↓
PreToolUse hook (metrics.tool_calls.append())
    ↓
SDK calls in-process handler
    ↓
Handler calls retrieval.search() [subprocess]
    ↓
Subprocess returns result
    ↓
Handler formats as MCP response
    ↓
PostToolUse hook (metrics updates)
    ↓
Agent receives result, continues generation
    ↓
Stop hook (finalize metrics)
    ↓
Returns article + metrics
```

### Hook Lifecycle

```
query() called
    ↓
UserPromptSubmit hook fires
    ↓
Agent analyzes prompt, decides on actions
    ↓
[If tool needed]
    ↓
PreToolUse hook fires
    - Records tool_name, tool_use_id, input, start_time
    - Appends to metrics.tool_calls list
    ↓
Tool executes
    ↓
PostToolUse hook fires
    - Finds matching record by tool_use_id
    - Updates end_time, duration_ms, result
    ↓
Agent processes result, may call more tools
    ↓
[Loop until agent decides to stop]
    ↓
Stop hook fires
    - Sets metrics.end_time
    - Logs summary (tool count, runtime)
    ↓
query() returns
    ↓
LogDocumentGenerator creates markdown
```

## Integration Points

### Component Integration Map

| Component A | Component B | Integration | Changes Needed |
|-------------|-------------|-------------|----------------|
| `agent_sdk.py` | `retrieval.py` | In-process MCP handler calls retrieval.search() | Add MCP tool wrapper |
| `agent_sdk.py` | SDK `query()` | Pass mcp_servers dict instead of tools list | Change _get_tools_config() |
| `agent_sdk.py` | `logging_hooks.py` | Hooks receive metrics via closure | No change (working) |
| `generator.py` | `agent_sdk.py` | Calls AgentSDKRunner.generate() | No change |
| `retrieval.py` | NotebookLM subprocess | subprocess.run() to skill | No change |

### Modified Integration Points (Approach 2)

**1. agent_sdk.py modifications:**

```python
# OLD (line 71-86)
def _get_tools_config(self) -> List[str]:
    if not self.notebook_id:
        return []
    return ["notebooklm"]  # ← WRONG

# NEW
def _get_mcp_servers(self) -> dict:
    """Create in-process MCP server for NotebookLM"""
    if not self.notebook_id:
        return {}

    @tool(
        name="query",
        description="Query NotebookLM knowledge base for relevant information"
    )
    async def query_notebooklm(question: str) -> dict:
        try:
            results = retrieval.search(
                query=question,
                notebook_id=self.notebook_id,
                notebook_url=self.notebook_url
            )
            if results:
                return {
                    "content": [{
                        "type": "text",
                        "text": results[0].content
                    }]
                }
            else:
                return {
                    "content": [{
                        "type": "text",
                        "text": "No relevant content found."
                    }]
                }
        except Exception as e:
            return {
                "content": [{
                    "type": "text",
                    "text": f"Query failed: {str(e)}"
                }]
            }

    server = create_sdk_mcp_server(
        name="notebooklm",
        version="1.0.0",
        tools=[query_notebooklm]
    )

    return {"notebooklm": server}
```

**2. ClaudeAgentOptions changes (line 196-208):**

```python
# OLD
tools = self._get_tools_config()
options = ClaudeAgentOptions(
    model=self.model,
    max_turns=max_turns,
    tools=tools if tools else None,  # ← WRONG
    hooks=hooks,
    system_prompt=system_prompt,
    env=env_vars
)

# NEW
mcp_servers = self._get_mcp_servers()
options = ClaudeAgentOptions(
    model=self.model,
    max_turns=max_turns,
    mcp_servers=mcp_servers if mcp_servers else None,
    allowed_tools=["mcp__notebooklm__query"] if mcp_servers else None,
    hooks=hooks,
    system_prompt=system_prompt,
    env=env_vars
)
```

### Imports to Add

```python
# In agent_sdk.py (top of file)
from claude_agent_sdk import query, ClaudeAgentOptions, HookMatcher, create_sdk_mcp_server, tool
from . import retrieval  # Add this import
```

## Build Order Recommendation

### Phase 1: Fix Tool Registration (CRITICAL)
**Target:** Get tools working at all

1. **Modify `agent_sdk.py`:**
   - Add `create_sdk_mcp_server` and `tool` imports
   - Replace `_get_tools_config()` with `_get_mcp_servers()`
   - Update `ClaudeAgentOptions` to use `mcp_servers` and `allowed_tools`

2. **Test with minimal change:**
   - Run with SDK mode enabled
   - Verify PreToolUse hook fires
   - Confirm tool call appears in metrics

**Files changed:**
- `src/modules/agent_sdk.py` (modify existing)

**Dependencies:**
- None (self-contained change)

**Success criteria:**
- Tool calls > 0 in metrics
- No "tool not found" behavior
- Hooks fire correctly

### Phase 2: Validate Tool Response Format
**Target:** Ensure tool returns work correctly

1. **Test tool return format:**
   - Verify MCP response format matches SDK expectations
   - Check that agent can parse tool results
   - Validate error handling paths

2. **Refine handler:**
   - Format errors as proper MCP responses
   - Add timeout handling
   - Add result validation

**Files changed:**
- `src/modules/agent_sdk.py` (refine handler)

**Dependencies:**
- Phase 1 complete

**Success criteria:**
- Agent successfully uses tool results in article
- Error cases handled gracefully
- PostToolUse hook shows valid results

### Phase 3: Metrics & Logging Verification
**Target:** Ensure complete observability

1. **Validate metrics collection:**
   - Check tool_calls list populated correctly
   - Verify duration_ms calculated
   - Confirm results captured

2. **Test log generation:**
   - Run LogDocumentGenerator
   - Verify tool calls appear in markdown
   - Check formatting of tool inputs/outputs

**Files changed:**
- `src/hooks/log_generator.py` (potentially refine formatting)

**Dependencies:**
- Phase 1-2 complete

**Success criteria:**
- Markdown logs show complete tool lifecycle
- Tool input/output visible
- Duration metrics accurate

### Phase 4: Edge Cases & Polish
**Target:** Production readiness

1. **Test edge cases:**
   - Notebook ID not set (graceful degradation)
   - Subprocess timeout
   - Multiple tool calls in sequence
   - Tool call during pre-retrieval vs agent-initiated

2. **Polish:**
   - Improve error messages
   - Add debug logging
   - Document configuration options

**Files changed:**
- `src/modules/agent_sdk.py` (error handling)
- Documentation

**Dependencies:**
- Phase 1-3 complete

**Success criteria:**
- All edge cases handled
- Clear error messages
- Documentation updated

## Anti-Patterns

### Anti-Pattern 1: Returning Tool Names as Strings Without Registration

**What people do:** Return tool names in a list expecting SDK to "figure it out"
```python
def _get_tools_config(self) -> List[str]:
    return ["notebooklm"]  # Assumes SDK knows what this is
```

**Why it's wrong:**
- SDK has no way to discover what "notebooklm" means
- Not a built-in tool (like "Bash", "Read", "Grep")
- Not a registered Skill (no SKILL.md in proper location)
- Not a registered MCP server
- Result: Tool silently ignored

**Do this instead:**
```python
def _get_mcp_servers(self) -> dict:
    # Explicitly create and register the tool
    server = create_sdk_mcp_server(
        name="notebooklm",
        tools=[query_tool]  # Actual tool implementation
    )
    return {"notebooklm": server}
```

### Anti-Pattern 2: Mixing Skill and MCP Tool Registration

**What people do:** Try to use both skill names and MCP servers interchangeably
```python
options = ClaudeAgentOptions(
    tools=["notebooklm"],  # Skill name?
    mcp_servers={"notebooklm": server},  # MCP server?
    allowed_tools=["notebooklm"]  # Which one?
)
```

**Why it's wrong:**
- `tools` parameter is for built-in tool filtering (deprecated in newer versions)
- Skill discovery requires `setting_sources` and `allowed_tools=["Skill"]`
- MCP tools require `mcp_servers` and `allowed_tools=["mcp__server__tool"]`
- Mixing them creates ambiguity and failures

**Do this instead:**
```python
# For MCP tools (recommended)
options = ClaudeAgentOptions(
    mcp_servers={"notebooklm": server},
    allowed_tools=["mcp__notebooklm__query"]
)

# OR for Skills (if applicable)
options = ClaudeAgentOptions(
    setting_sources=["user", "project"],
    allowed_tools=["Skill"]
)

# NOT both at once (unless you know what you're doing)
```

### Anti-Pattern 3: Subprocess Tool Without MCP Wrapper

**What people do:** Call subprocess directly from agent, bypassing SDK tool system
```python
# Inside generation loop
result = subprocess.run(["python", "skill.py", question])
# Agent never "sees" this as a tool call
```

**Why it's wrong:**
- Hooks don't fire (no metrics)
- Agent can't learn from tool use
- No retry/error handling from SDK
- Breaks agent loop pattern
- Can't be logged or observed

**Do this instead:**
```python
# Wrap subprocess in MCP tool handler
@tool(name="query")
async def query_tool(question: str) -> dict:
    result = subprocess.run(["python", "skill.py", question])
    # SDK sees this as a proper tool call
    return {"content": [{"type": "text", "text": result.stdout}]}

# Register as MCP server
mcp_server = create_sdk_mcp_server(tools=[query_tool])
```

### Anti-Pattern 4: Ignoring MCP Response Format

**What people do:** Return raw strings or objects instead of MCP format
```python
@tool(name="query")
async def query_tool(question: str):
    result = do_query(question)
    return result  # Wrong: returns string directly
```

**Why it's wrong:**
- SDK expects specific format: `{"content": [{"type": "text", "text": "..."}]}`
- Other formats cause deserialization errors
- Tool results won't be properly parsed
- Agent may not receive the data

**Do this instead:**
```python
@tool(name="query")
async def query_tool(question: str) -> dict:
    result = do_query(question)
    return {
        "content": [{
            "type": "text",
            "text": result
        }]
    }  # Proper MCP format
```

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1-10 users | Current in-process MCP approach is fine |
| 10-100 users | Consider connection pooling for subprocess calls, add caching layer |
| 100-1000 users | Move to external MCP server (Approach 1) for process isolation, add request queuing |
| 1000+ users | Dedicated MCP service, load balancing, async processing |

### Scaling Priorities

1. **First bottleneck:** Subprocess startup overhead
   - Each tool call spawns new browser session via NotebookLM skill
   - Mitigation: Add result caching in retrieval.py
   - Alternative: Implement session pooling in NotebookLM skill

2. **Second bottleneck:** MCP tool registration overhead
   - In-process server recreated on each SDK run
   - Mitigation: Cache MCP server instance at module level
   - Alternative: Move to long-lived external MCP server

## Sources

**Agent SDK Architecture:**
- [Agent SDK overview - Claude API Docs](https://platform.claude.com/docs/en/agent-sdk/overview)
- [Building agents with the Claude Agent SDK - Anthropic](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)
- [Claude Agent Skills: A First Principles Deep Dive](https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/)

**MCP Tool Integration:**
- [Custom Tools - Claude API Docs](https://platform.claude.com/docs/en/agent-sdk/custom-tools)
- [Connect to external tools with MCP - Claude API Docs](https://platform.claude.com/docs/en/agent-sdk/mcp)
- [MCP Tools Guide — claude_agent_sdk](https://hexdocs.pm/claude_agent_sdk/mcp-tools.html)

**Subprocess Tool Patterns:**
- [Anthropic's Agent SDK Unlocks Autonomous Development](https://www.startuphub.ai/ai-news/ai-video/2026/anthropics-agent-sdk-unlocks-autonomous-development/)
- [Getting started with Anthropic Claude Agent SDK — Python](https://medium.com/@aiablog/getting-started-with-anthropic-claude-agent-sdk-python-826a2216381d)

**Skills System:**
- [Agent Skills in the SDK - Claude API Docs](https://platform.claude.com/docs/en/agent-sdk/skills)
- [Agent Skills - Claude API Docs](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)

---
*Architecture research for: Agent SDK Tool Calling with Subprocess Integration*
*Researched: 2026-01-27*
*Confidence: HIGH - Based on official documentation, codebase analysis, and verified patterns*
