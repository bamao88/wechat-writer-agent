# Phase 3: OpenAI Agent SDK Migration - Research

**Researched:** 2026-01-28
**Domain:** Agent Framework Migration (Claude Agent SDK → OpenAI Agent SDK + LiteLLM)
**Confidence:** MEDIUM

## Summary

This research investigates migrating from Claude Agent SDK to OpenAI Agent SDK with LiteLLM for third-party API integration, specifically targeting MiniMax API compatibility. The OpenAI Agents SDK (v0.7.0, released January 2026) is a lightweight, provider-agnostic framework that supports 100+ LLMs through LiteLLM integration. Unlike Claude Agent SDK which was designed for sophisticated single-agent workflows with deep context management, OpenAI Agents SDK emphasizes multi-agent coordination with intelligent handoffs.

Key findings: LiteLLM has full MiniMax API support as of January 2026 (v1.80.15-stable), including both OpenAI-compatible and Anthropic-compatible endpoints with tool calling capabilities. The migration requires architectural changes to tool registration (from Skill-based to function decorator pattern), metrics collection (from hooks to context wrapper), and agent execution (from query() streaming to Runner.run() pattern).

**Primary recommendation:** Implement OpenAI Agent SDK as a parallel execution path alongside the existing Claude Agent SDK baseline, using LiteLLM's Anthropic-compatible endpoint (`litellm.anthropic.messages.acreate`) to minimize MiniMax API compatibility issues, and adapt the current NotebookLM subprocess-based tool to the `@function_tool` decorator pattern.

## Standard Stack

The established libraries/tools for OpenAI Agent SDK with third-party LLM integration:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| openai-agents | 0.7.0 | Agent framework | Official OpenAI agent orchestration SDK, released January 2026 |
| litellm | >=1.80.15 | LLM proxy layer | Unified interface for 100+ LLMs including MiniMax, industry standard for multi-provider support |
| pydantic | >=2.10, <3 | Data validation | Required by openai-agents for tool schema generation and type safety |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| griffe | >=1.5.6, <2 | Docstring parsing | Automatically extracts tool descriptions from function docstrings (google/sphinx/numpy formats) |
| typing-extensions | >=4.12.2, <5 | Type hints | Enhanced type annotations for Python <3.11 compatibility |
| websockets | >=15.0, <16 | Streaming | Required for realtime/voice features (optional unless using streaming events) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| OpenAI Agents SDK | Claude Agent SDK (current) | Claude SDK better for single-agent deep context tasks; OpenAI SDK better for multi-agent handoffs |
| LiteLLM | Direct MiniMax API calls | LiteLLM provides unified interface, automatic retries, cost tracking; direct calls give more control |
| @function_tool decorator | MCP server tools | MCP servers for production-grade tool sharing across clients; function tools for simple local tools |

**Installation:**
```bash
pip install "openai-agents[litellm]>=0.7.0"
pip install "litellm>=1.80.15"
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── modules/
│   ├── agent_sdk.py           # Existing Claude Agent SDK (baseline)
│   ├── openai_agent.py        # NEW: OpenAI Agent SDK runner
│   └── generator.py           # Updated to support both SDK paths
├── tools/
│   ├── notebooklm_tool.py     # NEW: @function_tool wrapper
│   └── __init__.py
└── hooks/
    └── openai_metrics.py      # NEW: Metrics collection for OpenAI agents
```

### Pattern 1: LiteLLM Model Configuration with MiniMax
**What:** Configure LiteLLM to use MiniMax API with Anthropic-compatible endpoint
**When to use:** When maintaining compatibility with existing MiniMax API setup (Anthropic-compatible base URL)
**Example:**
```python
# Source: https://docs.litellm.ai/docs/providers/minimax
import os
from litellm import anthropic

# Use Anthropic-compatible endpoint (recommended for MiniMax)
response = await litellm.anthropic.messages.acreate(
    model="minimax/MiniMax-M2.1",
    messages=[{"role": "user", "content": "Hello"}],
    api_key=os.getenv("MINIMAX_API_KEY"),
    max_tokens=4096,
    temperature=0.7,
    tools=tools  # Tool calling supported
)
```

### Pattern 2: Function Tool with Subprocess Integration
**What:** Wrap existing subprocess-based NotebookLM tool in @function_tool decorator
**When to use:** When you have external tool logic that needs to remain as subprocess (like NotebookLM Skill)
**Example:**
```python
# Source: https://openai.github.io/openai-agents-python/tools/
from agents import function_tool, RunContextWrapper
import subprocess
import json

@function_tool
async def query_notebooklm(question: str) -> str:
    """Query NotebookLM knowledge base for relevant information.

    Args:
        question: The question or keywords to search for

    Returns:
        Retrieved content from NotebookLM
    """
    # Call existing NotebookLM subprocess logic
    result = subprocess.run(
        ["python", "notebooklm_tool.py", "--question", question],
        capture_output=True,
        text=True,
        timeout=30
    )

    if result.returncode != 0:
        return f"Error: {result.stderr}"

    return result.stdout
```

### Pattern 3: Agent Initialization with Custom Context
**What:** Create agent with instructions, model, tools, and custom context for metrics
**When to use:** Standard agent setup pattern for OpenAI Agents SDK
**Example:**
```python
# Source: https://openai.github.io/openai-agents-python/agents/
from agents import Agent
from litellm import LitellmModel

# Create LiteLLM model wrapper
model = LitellmModel(
    model="minimax/MiniMax-M2.1",
    api_key=os.getenv("MINIMAX_API_KEY")
)

# Initialize agent
agent = Agent(
    name="ArticleWriter",
    instructions="You are a professional WeChat article writer...",
    model=model,
    tools=[query_notebooklm],  # List of @function_tool decorated functions
)
```

### Pattern 4: Async Execution with Streaming and Metrics
**What:** Run agent with streaming events and metrics collection
**When to use:** Production execution path requiring real-time output and token tracking
**Example:**
```python
# Source: https://openai.github.io/openai-agents-python/streaming/
from agents import Runner, ModelSettings

# Enable usage tracking for LiteLLM
agent.model_settings = ModelSettings(include_usage=True)

# Run with streaming
result = await Runner.run_streamed(agent, input=user_message)

# Stream events
async for event in result.stream_events():
    if event.type == "raw_response_event":
        # Handle streaming chunks
        pass
    elif event.type == "run_item_stream_event":
        # Handle completed items (tool calls, messages)
        pass

# Access metrics after completion
usage = result.context_wrapper.usage
print(f"Tokens: {usage.total_tokens}")
```

### Pattern 5: Custom Error Handling for Tool Failures
**What:** Provide graceful degradation when tools fail
**When to use:** Production agents where tool failures should not crash the agent
**Example:**
```python
# Source: https://openai.github.io/openai-agents-python/tools/
def custom_error_handler(ctx: RunContextWrapper[Any], error: Exception) -> str:
    """Custom error response for tool failures"""
    print(f"Tool error: {error}")
    return "The knowledge retrieval tool is temporarily unavailable. I'll answer based on my training knowledge."

@function_tool(failure_error_function=custom_error_handler)
async def query_notebooklm(question: str) -> str:
    """Query with graceful error handling"""
    # Tool implementation
    pass
```

### Anti-Patterns to Avoid
- **Using synchronous functions without async wrapper:** OpenAI Agents SDK runs in async context; blocking I/O will freeze execution
- **Mixing Claude and OpenAI SDK patterns:** Keep implementations separate; don't try to share hooks or metrics objects between SDKs
- **Forgetting ModelSettings(include_usage=True):** LiteLLM requires explicit configuration to report token metrics
- **Not setting OPENAI_AGENTS_ENABLE_LITELLM_SERIALIZER_PATCH=true:** Pydantic serializer warnings from LiteLLM responses will pollute logs

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-provider LLM interface | Custom API adapters for each provider | LiteLLM with unified interface | Handles authentication, retries, rate limiting, cost tracking for 100+ providers |
| Tool schema generation | Manual JSON schema writing | @function_tool decorator + Pydantic | Automatic schema from type hints and docstrings; supports complex types, validation |
| Streaming response parsing | Custom SSE/chunk parsers | Runner.run_streamed() with event types | Handles protocol differences across providers; unified event types |
| Token usage tracking | Manual response parsing | ModelSettings(include_usage=True) + context_wrapper.usage | Aggregates across tool calls and handoffs; consistent format |
| Tool error handling | Try-catch in every tool | failure_error_function parameter | Standardized error responses; prevents agent crashes |
| Async subprocess management | asyncio.create_subprocess_exec | anyio.to_thread.run_sync() for sync code | Better error handling; compatible with agent async context |

**Key insight:** OpenAI Agents SDK provides high-level abstractions that handle the complexity of agent orchestration, tool calling, and multi-turn conversations. LiteLLM handles the low-level complexity of provider API differences. Don't replicate these abstractions—use them.

## Common Pitfalls

### Pitfall 1: Assuming Direct Drop-in Replacement
**What goes wrong:** Attempting to replace Claude Agent SDK calls one-to-one without architectural changes
**Why it happens:** The two SDKs have fundamentally different architectures (hooks vs context wrapper, query() vs Runner.run(), Skills vs function tools)
**How to avoid:** Design parallel execution paths; maintain Claude SDK baseline; implement OpenAI SDK as new module
**Warning signs:** Import errors, type mismatches, missing metrics, tool registration failures

### Pitfall 2: LiteLLM Token Metrics Not Populating
**What goes wrong:** `result.context_wrapper.usage` is empty or None after agent run
**Why it happens:** LiteLLM providers don't report usage by default; requires explicit opt-in with ModelSettings
**How to avoid:** Always set `ModelSettings(include_usage=True)` when using LiteLLM models
**Warning signs:** Missing token counts, empty usage dict, metrics logging shows zero tokens

### Pitfall 3: Blocking I/O in Async Tools
**What goes wrong:** Agent hangs or times out during tool execution, especially with streaming
**Why it happens:** Using synchronous blocking operations (subprocess.run, open(), input()) in async function tools freezes the event loop
**How to avoid:** Use async equivalents (asyncio.create_subprocess_exec) or wrap with anyio.to_thread.run_sync()
**Warning signs:** Long delays before tool results, connection timeouts, "Task was destroyed but it is pending" errors

### Pitfall 4: MiniMax Endpoint URL Mismatch
**What goes wrong:** Authentication failures (HTTP 401) or "model not found" errors
**Why it happens:** MiniMax offers two endpoint styles (OpenAI-compatible and Anthropic-compatible); mixing them causes errors
**How to avoid:** Use `litellm.anthropic.messages.acreate()` with model="minimax/MiniMax-M2.1" for consistency with existing Anthropic-compatible base URL
**Warning signs:** 401 errors despite valid API key, model name errors, base URL conflicts

### Pitfall 5: Tool Schema Type Mismatches
**What goes wrong:** Model generates tool calls with invalid arguments; validation errors crash agent
**Why it happens:** Python type hints don't match actual expected types; Pydantic is strict about validation
**How to avoid:** Use Pydantic models for complex input types; test tool schema generation with `agent.tools[0].schema`
**Warning signs:** "validation error" exceptions, tool calls with wrong argument types, missing required fields

### Pitfall 6: Missing Conversation History Between Turns
**What goes wrong:** Agent forgets previous context; tool results not incorporated into next response
**Why it happens:** Not using Session management or manually maintaining messages list
**How to avoid:** For multi-turn conversations, use Session objects (SQLAlchemySession, RedisSession) or maintain message history explicitly
**Warning signs:** Agent asks for information already provided, ignores previous tool results, starts fresh each turn

## Code Examples

Verified patterns from official sources:

### Complete Agent Setup with LiteLLM and MiniMax
```python
# Source: https://openai.github.io/openai-agents-python/models/litellm/
import os
from agents import Agent, Runner, function_tool, ModelSettings
from litellm import LitellmModel

# Configure LiteLLM for MiniMax
model = LitellmModel(
    model="minimax/MiniMax-M2.1",
    api_key=os.getenv("MINIMAX_API_KEY")
)

# Define tool
@function_tool
async def query_notebooklm(question: str) -> str:
    """Query NotebookLM knowledge base.

    Args:
        question: Search query or question
    """
    # Tool implementation
    return "Retrieved content..."

# Create agent with usage tracking
agent = Agent(
    name="Writer",
    instructions="Professional article writer",
    model=model,
    tools=[query_notebooklm]
)

# Enable token tracking for LiteLLM
agent.model_settings = ModelSettings(include_usage=True)

# Run agent
result = await Runner.run(agent, input="Write about AI agents")

# Access metrics
usage = result.context_wrapper.usage
print(f"Total tokens: {usage.total_tokens}")
print(f"Input: {usage.input_tokens}, Output: {usage.output_tokens}")
```

### Async Streaming with Event Handling
```python
# Source: https://openai.github.io/openai-agents-python/streaming/
from agents import Runner
from openai.types.responses import ResponseTextDeltaEvent

# Stream agent execution
result = await Runner.run_streamed(agent, input="Your query")

# Process streaming events
async for event in result.stream_events():
    if event.type == "raw_response_event":
        # Handle token-by-token streaming
        if isinstance(event.data, ResponseTextDeltaEvent):
            print(event.data.delta, end="", flush=True)

    elif event.type == "run_item_stream_event":
        # Handle completed items (messages, tool calls)
        item = event.data
        if item.type == "tool_call":
            print(f"\n[Tool called: {item.name}]")

    elif event.type == "agent_updated_stream_event":
        # Handle agent handoffs
        print(f"\n[Agent switched to: {event.data.name}]")

# Final result available after stream completes
print(f"\nFinal output: {result.final_output}")
```

### Tool Error Handling with Custom Response
```python
# Source: https://openai.github.io/openai-agents-python/tools/
from agents import function_tool, RunContextWrapper
from typing import Any

def tool_error_handler(ctx: RunContextWrapper[Any], error: Exception) -> str:
    """Provide user-friendly error message instead of crash"""
    # Log error for debugging
    print(f"Tool error: {type(error).__name__}: {error}")

    # Return graceful message to LLM
    return "I encountered an issue accessing the knowledge base. Let me answer based on my understanding."

@function_tool(failure_error_function=tool_error_handler)
async def query_notebooklm(question: str) -> str:
    """Query with error handling"""
    # May raise exception
    result = await external_api_call(question)
    return result
```

### Metrics Collection Pattern
```python
# Source: https://openai.github.io/openai-agents-python/usage/
from dataclasses import dataclass
from typing import List, Dict, Any
import time

@dataclass
class OpenAIAgentMetrics:
    """Metrics structure compatible with existing logging"""
    start_time: float
    end_time: float
    tool_calls: List[Dict[str, Any]]
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int

    @property
    def runtime_seconds(self) -> float:
        return self.end_time - self.start_time

    @property
    def tool_call_count(self) -> int:
        return len(self.tool_calls)

# Collect metrics after agent run
async def generate_with_openai_sdk(topic: str, **kwargs):
    start = time.time()
    tool_calls_log = []

    # Run agent (with custom context for tool logging)
    result = await Runner.run(agent, input=topic)

    # Build metrics from result
    usage = result.context_wrapper.usage
    metrics = OpenAIAgentMetrics(
        start_time=start,
        end_time=time.time(),
        tool_calls=tool_calls_log,  # Collect from custom context
        total_tokens=usage.total_tokens if usage else 0,
        prompt_tokens=usage.input_tokens if usage else 0,
        completion_tokens=usage.output_tokens if usage else 0
    )

    return result.final_output, metrics
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Claude Code SDK | Claude Agent SDK | Sept 2025 (v0.1.0) | Breaking changes; renamed SDK with improved multi-turn context |
| Single-agent frameworks | Multi-agent handoffs | Jan 2026 (OpenAI 0.7.0) | Agent specialization via handoff patterns |
| Custom LLM adapters | LiteLLM unified interface | Ongoing (1.80.15+) | Reduced integration complexity; 100+ providers |
| Manual tool schemas | Auto-generation from types | Jan 2026 (OpenAI SDK) | Faster tool development; type-safe validation |
| Skill-based tool loading | MCP server protocol | Late 2025 | Standardized tool sharing across AI clients |

**Deprecated/outdated:**
- **Claude Code SDK**: Renamed to Claude Agent SDK in September 2025; old package no longer maintained
- **OpenAI Responses API without Agents SDK**: Direct API calls deprecated for agent workflows; SDK provides better abstractions
- **Manual message history management**: Session objects (SQLAlchemy, Redis) now standard for multi-turn conversations

## Open Questions

Things that couldn't be fully resolved:

1. **NotebookLM MCP Server Integration with OpenAI Agents**
   - What we know: Multiple NotebookLM MCP servers exist (PleasePrompto/notebooklm-mcp, jacob-bd/notebooklm-mcp), OpenAI Agents SDK supports MCP stdio and SSE transports
   - What's unclear: Current NotebookLM MCP servers target Claude-based tools; compatibility with OpenAI Agents SDK needs validation
   - Recommendation: Start with subprocess-based @function_tool wrapper (lowest risk); evaluate MCP server upgrade in Phase 4 if subprocess performance becomes bottleneck

2. **MiniMax API Thinking/Reasoning Token Accounting**
   - What we know: MiniMax-M2.1 supports "thinking" parameter like Claude; LiteLLM Anthropic endpoint supports this parameter
   - What's unclear: Whether thinking tokens are included in usage.total_tokens or reported separately; impact on cost tracking
   - Recommendation: Test with thinking enabled; compare token counts against MiniMax dashboard; document in API-04 requirement

3. **Tool Call Logging Granularity**
   - What we know: Claude Agent SDK provides PreToolUse/PostToolUse hooks for detailed logging; OpenAI SDK uses context_wrapper for results
   - What's unclear: How to capture per-tool-call timing and input/output details without hooks
   - Recommendation: Implement custom context object passed to tools; tools log to shared metrics structure; less elegant than hooks but achieves same result

4. **Feishu API Integration Point**
   - What we know: Current pipeline has four stages: retrieval → generation → documentation → table storage
   - What's unclear: Whether Feishu integration should be a tool (agent can decide when to save) or external pipeline step (always save after generation)
   - Recommendation: Keep as external pipeline step for Phase 3; agent complexity should focus on writing, not storage decisions

5. **LiteLLM Rate Limiting and Retry Behavior**
   - What we know: LiteLLM handles retries and rate limiting automatically
   - What's unclear: Default retry counts, backoff strategy for MiniMax API; whether existing 3000s timeout is compatible
   - Recommendation: Review LiteLLM retry configuration; test with intentional failures; document retry behavior for production deployment

## Sources

### Primary (HIGH confidence)
- [OpenAI Agents SDK Official Documentation](https://openai.github.io/openai-agents-python/) - Agent patterns, tool calling, streaming
- [LiteLLM MiniMax Provider Documentation](https://docs.litellm.ai/docs/providers/minimax) - MiniMax API integration via LiteLLM
- [LiteLLM Anthropic Provider Documentation](https://docs.litellm.ai/docs/providers/anthropic) - Anthropic-compatible endpoint usage
- [OpenAI Agents SDK Tools Documentation](https://openai.github.io/openai-agents-python/tools/) - Function tool implementation patterns
- [OpenAI Agents SDK Streaming Documentation](https://openai.github.io/openai-agents-python/streaming/) - Async streaming implementation

### Secondary (MEDIUM confidence)
- [LiteLLM Streaming + Async Documentation](https://docs.litellm.ai/docs/completion/stream) - Async streaming patterns verified with code examples
- [OpenAI Agents SDK Usage Documentation](https://openai.github.io/openai-agents-python/usage/) - Token metrics and usage tracking
- [OpenAI Agents SDK Context Management](https://openai.github.io/openai-agents-python/context/) - Context wrapper patterns
- [OpenAI Agents SDK Exceptions Documentation](https://openai.github.io/openai-agents-python/ref/exceptions/) - Error handling patterns
- [LiteLLM Release v1.80.15-stable](https://docs.litellm.ai/release_notes/v1-80-15) - MiniMax support added January 2026

### Tertiary (LOW confidence - requires validation)
- Community NotebookLM MCP servers ([PleasePrompto/notebooklm-mcp](https://github.com/PleasePrompto/notebooklm-mcp)) - Compatibility with OpenAI Agents SDK unverified
- [AI Framework Comparison 2025](https://enhancial.substack.com/p/choosing-the-right-ai-framework-a) - Claude vs OpenAI architectural comparison (opinion piece)
- [OpenAI AgentKit vs Claude SDK Comparison](https://blog.getbind.co/2025/10/07/openai-agentkit-vs-claude-agents-sdk-which-is-better/) - Framework tradeoffs (blog post)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official documentation and PyPI package info verified
- Architecture patterns: MEDIUM - Official examples verified, but MiniMax-specific patterns untested
- Pitfalls: MEDIUM - Based on documented issues and community reports, not direct experience with MiniMax

**Research date:** 2026-01-28
**Valid until:** 2026-02-28 (30 days for stable SDK, shorter if LiteLLM or OpenAI Agents SDK release major versions)

**Key assumptions:**
1. MiniMax API maintains Anthropic-compatible endpoint through Phase 3 implementation
2. Current NotebookLM subprocess-based tool can be wrapped in @function_tool without major refactoring
3. OpenAI Agents SDK v0.7.0 remains stable (no breaking changes in patch releases)
4. LiteLLM MiniMax support (v1.80.15+) includes all features needed for tool calling and streaming

**Migration risk assessment:**
- **LOW risk:** LiteLLM installation and basic completion calls (well-documented, stable APIs)
- **MEDIUM risk:** Tool calling with MiniMax via LiteLLM (documented but untested in this specific combination)
- **MEDIUM risk:** Metrics collection parity with Claude SDK hooks (requires custom implementation)
- **HIGH risk:** NotebookLM MCP server integration (unclear compatibility; fallback to subprocess wrapper available)
