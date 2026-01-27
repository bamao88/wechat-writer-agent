# Phase 1: 工具注册与协议验证 - Research

**Researched:** 2026-01-28
**Domain:** Claude Agent SDK Tool Registration & MiniMax API Protocol Validation
**Confidence:** HIGH

## Summary

This research investigates **tool registration mechanisms in Claude Agent SDK** and **MiniMax API's Anthropic-compatible tool calling protocol**. The goal is to enable NotebookLM Skill integration for knowledge base querying during article generation.

**Key Finding:** The current codebase has a critical configuration gap. The SDK requires explicit `setting_sources` configuration to load Skills from the filesystem, but this parameter is missing. Additionally, the wrong parameter name (`tools` instead of `allowed_tools`) is used.

**MiniMax API Compatibility:** ✅ MiniMax API **fully supports** Anthropic's tool calling protocol, including `tool_use` blocks, `tool_result` responses, and multi-turn conversations. The API is not a blocker.

**Primary recommendation:** Add `setting_sources=["user", "project"]` and `allowed_tools=["Skill"]` to `ClaudeAgentOptions` to enable filesystem-based Skill loading. This is a minimal-change fix that leverages the existing NotebookLM Skill infrastructure.

## Standard Stack

The established libraries/tools for Claude Agent SDK tool integration:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| claude-agent-sdk | 0.1.23+ | Agent orchestration with tool calling, session management, hooks | Official Anthropic SDK, replaces deprecated claude-code-sdk |
| anthropic | ≥0.39.0 | Base API client for Claude models | Required peer dependency for claude-agent-sdk |
| mcp | ≥0.1.0 | Model Context Protocol implementation | Required by claude-agent-sdk for tool/resource providers |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| anyio | ≥4.0.0 | Async I/O abstraction | Required by claude-agent-sdk for async operations |
| python-dotenv | ≥1.0.0 | Environment variable loading | Configuration management (.env files) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Skills (filesystem) | SDK MCP Servers (in-process) | More control and better error handling, but more code to maintain |
| claude-agent-sdk | Direct Anthropic API + manual loop | Full control but need to implement agent loop, session management, hooks |

**Installation:**
```bash
pip install claude-agent-sdk>=0.1.23
```

**Critical Note:** The requirements.txt currently **does not include** claude-agent-sdk, yet the code imports from it. This is a missing dependency that must be added.

## Architecture Patterns

### Recommended Project Structure
```
src/
├── modules/
│   ├── agent_sdk.py      # SDK orchestration, options configuration
│   └── generator.py      # Traditional API mode (fallback)
├── hooks/
│   └── logging_hooks.py  # PreToolUse, PostToolUse, Stop hooks
└── notebooklm_tool.py    # Standalone tool wrapper (optional)

~/.claude/skills/         # User Skills (loaded via setting_sources)
└── notebooklm/
    ├── SKILL.md          # Skill metadata and tool definitions
    └── scripts/          # Tool implementation scripts
```

### Pattern 1: Skills-Based Tool Registration (Recommended)
**What:** Load tools from filesystem directories as Skills
**When to use:** External tools that run as subprocesses, team-shared tools, tools that need versioning

**Example:**
```python
# Source: Claude Agent SDK Documentation
from claude_agent_sdk import query, ClaudeAgentOptions

options = ClaudeAgentOptions(
    model="MiniMax-M2.1",
    setting_sources=["user", "project"],  # Load Skills from filesystem
    allowed_tools=["Skill"],              # Enable Skill discovery
    system_prompt=system_prompt,
    env={"ANTHROPIC_BASE_URL": "https://api.minimaxi.com/anthropic"}
)

async for message in query(prompt=user_message, options=options):
    # SDK automatically discovers and enables tools from Skills
    pass
```

**How it works:**
1. SDK scans `~/.claude/skills/` (user) and `.claude/skills/` (project)
2. Loads `SKILL.md` files with tool definitions
3. Makes tools available to Agent via subprocess invocation
4. Agent decides when to call tools based on system prompt and context

### Pattern 2: SDK MCP Server (Alternative)
**What:** Define tools as Python functions using `@tool` decorator
**When to use:** Performance-critical tools, need tight integration, better error handling

**Example:**
```python
# Source: Claude Agent SDK Documentation
from claude_agent_sdk import tool, create_sdk_mcp_server, ClaudeAgentOptions

@tool("query_kb", "Query knowledge base", {"question": str})
async def query_knowledge_base(args):
    # Tool implementation here
    result = await fetch_from_kb(args["question"])
    return {"content": [{"type": "text", "text": result}]}

server = create_sdk_mcp_server(
    name="knowledge",
    version="1.0.0",
    tools=[query_knowledge_base]
)

options = ClaudeAgentOptions(
    mcp_servers={"kb": server},
    allowed_tools=["mcp__kb__query_kb"]  # Format: mcp__{server}__{tool}
)
```

**Tradeoffs:**
- ✅ More control, better error handling, easier debugging
- ❌ More code to maintain, still has subprocess overhead if wrapping external tools

### Pattern 3: Current Code (Broken)
**What:** Passes tool names without filesystem configuration
**Why it fails:** SDK doesn't know where to find Skills

```python
# Current implementation (BROKEN)
def _get_tools_config(self) -> List[str]:
    return ["notebooklm"]  # Just a name, no loading mechanism

options = ClaudeAgentOptions(
    model=self.model,
    tools=tools if tools else None,  # ❌ Wrong parameter name
    # setting_sources missing ❌
    hooks=hooks,
    system_prompt=system_prompt
)
```

**Fix:**
```python
# Fixed implementation
def _get_allowed_tools(self) -> List[str]:
    """Get list of allowed tools"""
    tools = []
    if self.notebook_id:
        tools.append("Skill")  # Enable Skill discovery
        print(f"[INFO] NotebookLM Skill enabled")
    return tools

options = ClaudeAgentOptions(
    model=self.model,
    max_turns=max_turns,
    setting_sources=["user", "project"],  # ✅ Enable filesystem loading
    allowed_tools=self._get_allowed_tools(),  # ✅ Correct parameter
    hooks=hooks,
    system_prompt=system_prompt,
    env=env_vars
)
```

### Anti-Patterns to Avoid
- **Listing all available tools:** Security risk. Only enable tools the Agent actually needs
- **Omitting setting_sources:** SDK cannot load Skills without explicit configuration (changed in 2026)
- **Using `tools` parameter:** Outdated parameter name. Use `allowed_tools` instead
- **Hardcoding tool names:** Use `"Skill"` for discovery, or ensure name matches SKILL.md definition
- **Including "user" when custom API key needed:** User settings override environment variables

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Agent orchestration loop | Custom message loop with tool handling | `claude_agent_sdk.query()` | Handles multi-turn conversations, tool invocations, session management, error recovery |
| Tool execution lifecycle | Manual pre/post processing | SDK Hooks (PreToolUse, PostToolUse, Stop) | Standardized lifecycle, permission control, logging injection points |
| MCP server implementation | Custom JSON-RPC server | `create_sdk_mcp_server()` with `@tool` | In-process, no subprocess overhead, type-safe |
| Skill discovery | Manual file scanning | `setting_sources` + `allowed_tools=["Skill"]` | SDK handles SKILL.md parsing, validation, registration |
| Multi-turn tool conversations | Manual message history management | SDK automatic context preservation | MiniMax API requires full assistant messages in history |

**Key insight:** Tool calling in LLM agents has many edge cases (permission handling, error recovery, context preservation, subprocess management). The SDK abstracts these complexities with battle-tested implementations.

## Common Pitfalls

### Pitfall 1: Skills Not Loading (setting_sources Missing)
**What goes wrong:** Agent never calls tools despite correct SKILL.md and tool names
**Why it happens:** SDK default behavior changed in 2026. Now requires explicit `setting_sources` configuration for filesystem access
**How to avoid:**
```python
options = ClaudeAgentOptions(
    setting_sources=["user", "project"],  # REQUIRED for Skills
    allowed_tools=["Skill"]
)
```
**Warning signs:**
- `tool_call_count: 0` in metrics
- No tool-related logs from SDK
- Agent generates responses without querying knowledge base

### Pitfall 2: Wrong Parameter Name (tools vs allowed_tools)
**What goes wrong:** Tools parameter silently ignored, SDK uses default tool set
**Why it happens:** Parameter rename during SDK refactoring (claude-code-sdk → claude-agent-sdk)
**How to avoid:** Use `allowed_tools` not `tools`
```python
# Wrong
options = ClaudeAgentOptions(tools=["Skill"])  # ❌

# Correct
options = ClaudeAgentOptions(allowed_tools=["Skill"])  # ✅
```
**Warning signs:**
- No error message but tools not working
- SDK documentation examples use `allowed_tools`

### Pitfall 3: User Settings Override Environment Variables
**What goes wrong:** Custom API keys or base URLs in code ignored
**Why it happens:** When `setting_sources` includes "user", `~/.claude/settings.json` takes precedence
**How to avoid:**
```python
# If using custom MiniMax API endpoint
options = ClaudeAgentOptions(
    setting_sources=["project"],  # Exclude "user" to prevent override
    allowed_tools=["Skill"],
    env={"ANTHROPIC_BASE_URL": "https://api.minimaxi.com/anthropic"}
)

# Or: Don't set API_KEY in ~/.claude/settings.json
```
**Warning signs:**
- API calls go to official Anthropic endpoint instead of MiniMax
- Authentication errors with MiniMax key

### Pitfall 4: Tool Name Mismatch (Prompt vs Skill Definition)
**What goes wrong:** Agent tries to call tool by wrong name, gets "tool not found" error
**Why it happens:** Prompt references `query_notebooklm`, but SKILL.md defines different tool name
**How to avoid:**
1. Check `~/.claude/skills/notebooklm/SKILL.md` for actual tool names
2. Update system prompt to match, or use generic description
3. Test with `allowed_tools=["Skill"]` which auto-discovers all tools
**Warning signs:**
- SDK logs show "tool not available" errors
- Agent apologizes for not being able to use tools

### Pitfall 5: Missing SDK Dependency
**What goes wrong:** Import errors or wrong SDK version behaviors
**Why it happens:** `claude-agent-sdk` not in requirements.txt (current issue in this project)
**How to avoid:**
```bash
# Add to requirements.txt
claude-agent-sdk>=0.1.23

# Install
pip install claude-agent-sdk
```
**Warning signs:**
- `ImportError: No module named 'claude_agent_sdk'`
- Unexpected behaviors if old version cached

### Pitfall 6: Temperature Out of Range for MiniMax
**What goes wrong:** API returns 400 error for temperature value
**Why it happens:** MiniMax requires temperature in `(0.0, 1.0]` (exclusive of 0.0), while official Anthropic allows `[0.0, 1.0]` (inclusive)
**How to avoid:**
```python
# MiniMax-compatible temperature
temperature = max(0.01, min(1.0, user_temperature))  # Clamp to (0.0, 1.0]
```
**Warning signs:**
- API errors mentioning temperature validation
- Current code uses 0.7 ✅ (already in valid range)

## Code Examples

Verified patterns from official sources:

### Minimal Working Configuration
```python
# Source: Claude Agent SDK Documentation
from claude_agent_sdk import query, ClaudeAgentOptions
import os

# For MiniMax API
env_vars = {
    "ANTHROPIC_BASE_URL": "https://api.minimaxi.com/anthropic",
    "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY")
}

options = ClaudeAgentOptions(
    model="MiniMax-M2.1",
    max_turns=10,
    setting_sources=["user", "project"],  # Load Skills
    allowed_tools=["Skill"],              # Enable all Skills
    system_prompt="你是一个AI写作助手...",
    env=env_vars
)

async for message in query(prompt="写一篇关于AI的文章", options=options):
    if hasattr(message, 'result'):
        print(message.result)
```

### With Hooks for Metrics Collection
```python
# Source: Project codebase (hooks/logging_hooks.py)
from claude_agent_sdk import ClaudeAgentOptions, HookMatcher

def create_hooks(metrics):
    """Create hooks with metrics injection"""
    return {
        "PreToolUse": [
            HookMatcher(hooks=[
                lambda input_data, tool_use_id, ctx:
                    pre_tool_use_hook(input_data, tool_use_id, ctx, metrics)
            ])
        ],
        "PostToolUse": [
            HookMatcher(hooks=[
                lambda input_data, tool_use_id, ctx:
                    post_tool_use_hook(input_data, tool_use_id, ctx, metrics)
            ])
        ],
        "Stop": [
            HookMatcher(
                hooks=[lambda input_data, tool_use_id, ctx:
                    stop_hook(input_data, tool_use_id, ctx, metrics)
                ],
                timeout=180
            )
        ]
    }

options = ClaudeAgentOptions(
    model=model,
    setting_sources=["user", "project"],
    allowed_tools=["Skill"],
    hooks=create_hooks(metrics),
    system_prompt=system_prompt,
    env=env_vars
)
```

### SDK MCP Server Alternative
```python
# Source: Claude Agent SDK Documentation
from claude_agent_sdk import tool, create_sdk_mcp_server, ClaudeAgentOptions
import subprocess
import os

@tool(
    "query_notebooklm",
    "Query NotebookLM knowledge base for information, cases, and insights",
    {"question": str}
)
async def query_notebooklm(args):
    """Wrapper that calls NotebookLM skill via subprocess"""
    result = subprocess.run(
        [
            "python3",
            os.path.expanduser("~/.claude/skills/notebooklm/scripts/run.py"),
            "ask_question.py",
            "--question", args["question"],
            "--notebook-id", os.getenv("NOTEBOOK_ID")
        ],
        capture_output=True,
        text=True,
        timeout=180
    )

    if result.returncode != 0:
        return {
            "content": [{"type": "text", "text": f"Error: {result.stderr}"}],
            "is_error": True
        }

    return {"content": [{"type": "text", "text": result.stdout}]}

# Create MCP server
notebooklm_server = create_sdk_mcp_server(
    name="notebooklm",
    version="1.0.0",
    tools=[query_notebooklm]
)

# Use in options
options = ClaudeAgentOptions(
    mcp_servers={"notebooklm": notebooklm_server},
    allowed_tools=["mcp__notebooklm__query_notebooklm"],
    system_prompt=system_prompt
)
```

### Tool Call Verification
```python
# Source: Project diagnostic code
async def verify_tool_registration():
    """Verify that Skills are loaded and tools are available"""
    options = ClaudeAgentOptions(
        model="MiniMax-M2.1",
        setting_sources=["user"],
        allowed_tools=["Skill"],
        env={"ANTHROPIC_BASE_URL": os.getenv("ANTHROPIC_BASE_URL")}
    )

    # Ask Agent to list available tools
    async for message in query(
        prompt="What tools are available to you?",
        options=options
    ):
        print(message)

    # Expected: Agent mentions NotebookLM or knowledge base query tool
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `claude-code-sdk` package | `claude-agent-sdk` package | Q4 2025 | Package rename, cleaner API, MCP integration |
| Auto-load all settings | Explicit `setting_sources` required | January 2026 | Better isolation, must configure explicitly |
| `tools` parameter | `allowed_tools` parameter | Q4 2025 | Clearer naming, aligns with security model |
| Built-in temperature in options | Pass via env or external config | Varies by SDK version | Check SDK version documentation |

**Deprecated/outdated:**
- `claude-code-sdk`: Replaced by `claude-agent-sdk` (must update imports and package name)
- `ClaudeCodeOptions`: Renamed to `ClaudeAgentOptions`
- Auto-loading user settings: Now requires explicit `setting_sources=["user"]`
- `tools` parameter: Use `allowed_tools` instead

## Open Questions

Things that couldn't be fully resolved:

1. **SKILL.md Format Validation**
   - What we know: NotebookLM Skill exists at `~/.claude/skills/notebooklm/` and works via subprocess
   - What's unclear: Whether SKILL.md follows current format expectations for SDK auto-discovery
   - Recommendation: Verify SKILL.md has proper YAML frontmatter with tool definitions. If missing, SDK may not discover tools even with correct `setting_sources`

2. **Temperature Parameter in ClaudeAgentOptions**
   - What we know: MiniMax requires temperature ∈ (0.0, 1.0], current code uses 0.7
   - What's unclear: Whether `ClaudeAgentOptions` accepts `temperature` parameter directly or requires env variable
   - Recommendation: Test both approaches. Current code may need to pass temperature via `env` dict or system prompt

3. **Tool Name in System Prompt**
   - What we know: Current prompt references `query_notebooklm` tool
   - What's unclear: Actual tool name defined in NotebookLM's SKILL.md
   - Recommendation: Either update prompt to generic phrasing ("use available tools to query knowledge base") or verify SKILL.md tool name matches

4. **Skill Permission Model**
   - What we know: Hooks can approve/deny tool use via `permissionDecision`
   - What's unclear: Whether subprocess-based Skills require explicit permission configuration
   - Recommendation: Test with default permission model first, add explicit approval logic if needed

## Sources

### Primary (HIGH confidence)
- [Agent Skills in the SDK - Claude API Docs](https://platform.claude.com/docs/en/agent-sdk/skills)
- [Connect to external tools with MCP - Claude API Docs](https://platform.claude.com/docs/en/agent-sdk/mcp)
- [Agent SDK reference - Python - Claude API Docs](https://platform.claude.com/docs/en/agent-sdk/python)
- [claude-agent-sdk · PyPI](https://pypi.org/project/claude-agent-sdk/)
- [GitHub - anthropics/claude-agent-sdk-python](https://github.com/anthropics/claude-agent-sdk-python)
- [Compatible Anthropic API - MiniMax API Docs](https://platform.minimax.io/docs/api-reference/text-anthropic-api)

### Secondary (MEDIUM confidence)
- [Claude Agent Skills: A First Principles Deep Dive](https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/)
- [The Complete Guide to Building Agents with the Claude Agent SDK](https://nader.substack.com/p/the-complete-guide-to-building-agents)
- [Common Pitfalls with the Claude Agent SDK](https://liruifengv.com/posts/claude-agent-sdk-pitfalls-en/)

### Tertiary (LOW confidence - for context)
- [MiniMax | liteLLM](https://docs.litellm.ai/docs/providers/minimax)
- [Fix Common Claude Code Sub-Agent Setup Problems](https://www.arsturn.com/blog/fixing-common-claude-code-sub-agent-problems)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Verified with PyPI metadata and official documentation
- Architecture: HIGH - Direct examples from SDK reference documentation
- MiniMax compatibility: HIGH - Official API documentation confirms full tool use support
- Skills loading mechanism: HIGH - Official documentation explicitly describes setting_sources requirement
- Pitfalls: HIGH - Verified through official docs and current project diagnostic analysis

**Research date:** 2026-01-28
**Valid until:** 2026-02-28 (30 days - SDK and API relatively stable)

**Key verification sources:**
- Current SDK version: 0.1.23 (verified via `pip show claude-agent-sdk`)
- MiniMax API compatibility: Verified via official documentation (supports tool_use protocol)
- Current code analysis: Verified missing `setting_sources` and wrong parameter name in `src/modules/agent_sdk.py`
- NotebookLM Skill: Verified working via subprocess in `TOOL_CALL_DIAGNOSIS.md`
