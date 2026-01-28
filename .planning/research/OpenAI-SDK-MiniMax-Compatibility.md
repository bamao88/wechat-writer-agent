# OpenAI SDK & MiniMax API Compatibility Research

**Research Date:** 2026-01-28
**Target:** Assess compatibility between OpenAI Agents SDK and MiniMax API

---

## Executive Summary

MiniMax provides **full OpenAI-compatible API support** via endpoint `https://api.minimax.io/v1`, enabling direct integration with the OpenAI Python SDK. However, there are **critical internal format differences** and **known compatibility issues** that require careful configuration.

**Key Findings:**
- ✅ OpenAI-compatible endpoint fully supported
- ✅ Standard SSE streaming protocol compatible
- ✅ Tool calling supported with automatic conversion
- ⚠️ Requires XML-to-OpenAI format conversion for tool calls
- ⚠️ Known reasoning content handling issues
- ⚠️ Special parameter `reasoning_split=True` needed for optimal performance

---

## 1. OpenAI Compatibility Endpoint

### Endpoint Details

| Aspect | Details |
|--------|---------|
| **Base URL** | `https://api.minimax.io/v1` (International)<br>`https://api.minimaxi.com/v1` (China) |
| **Endpoint Path** | `/chat/completions` (Standard OpenAI format) |
| **Protocol** | HTTPS POST requests |
| **Authentication** | `Authorization: Bearer <API_KEY>` |
| **Status** | ✅ Fully compatible with OpenAI SDK |

### Usage Example

```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_MINIMAX_API_KEY",
    base_url="https://api.minimax.io/v1"
)

response = client.chat.completions.create(
    model="MiniMax-M2.1",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ]
)
```

### Environment Variables

```bash
export OPENAI_BASE_URL=https://api.minimax.io/v1
export OPENAI_API_KEY=${YOUR_MINIMAX_API_KEY}
```

---

## 2. Streaming Protocol

### SSE Compatibility

| Feature | Status | Notes |
|---------|--------|-------|
| **SSE Format** | ✅ Compatible | Standard `data: {...}` format |
| **Event Structure** | ✅ Compatible | Uses `chat.completion.chunk` objects |
| **Termination** | ✅ Compatible | Ends with `[DONE]` signal |
| **Delta Content** | ✅ Compatible | Standard `delta` field structure |
| **Real-time Output** | ✅ Supported | Optimized for low latency |

### Streaming Example

```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_MINIMAX_API_KEY",
    base_url="https://api.minimax.io/v1"
)

response = client.chat.completions.create(
    model="MiniMax-M2.1",
    messages=[{"role": "user", "content": "Tell me a story"}],
    stream=True
)

for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

### Known Streaming Issues

**No timeout-specific issues found** in documentation or GitHub issues. Standard OpenAI SDK timeout configuration should work.

---

## 3. Tool Calling

### Internal Format vs OpenAI Format

**Critical Difference:** MiniMax-M2 internally uses **XML tags** for tool calling, not JSON.

#### Internal XML Format

```xml
<minimax:tool_call>
  <invoke name="get_weather">
    <parameter name="location">San Francisco, CA</parameter>
    <parameter name="unit">celsius</parameter>
  </invoke>
</minimax:tool_call>
```

#### OpenAI Expected Format

```json
{
  "tool_calls": [
    {
      "id": "call_abc123",
      "type": "function",
      "function": {
        "name": "get_weather",
        "arguments": "{\"location\": \"San Francisco, CA\", \"unit\": \"celsius\"}"
      }
    }
  ]
}
```

### Automatic Conversion

**Solution:** MiniMax API endpoint handles conversion automatically when using:

1. **vLLM deployment** with `--tool-call-parser minimax_m2` flag
2. **SGLang deployment** with `--tool-call-parser minimax-m2` flag
3. **MiniMax hosted API** at `https://api.minimax.io/v1` (conversion built-in)

### Tool Definition Compatibility

MiniMax **fully supports** OpenAI's `tools` parameter format:

```python
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get the current weather in a given location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City and state, e.g., 'San Francisco, CA'"
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"]
                }
            },
            "required": ["location", "unit"]
        }
    }
}]

response = client.chat.completions.create(
    model="MiniMax-M2.1",
    messages=[{"role": "user", "content": "What's the weather in SF?"}],
    tools=tools,
    tool_choice="auto"
)
```

### Tool Call Response Format

When using MiniMax API endpoint, responses follow standard OpenAI format:

```python
tool_call = response.choices[0].message.tool_calls[0]
print(f"Function: {tool_call.function.name}")
print(f"Arguments: {tool_call.function.arguments}")
```

---

## 4. Known Issues & Caveats

### Issue #1: Reasoning Content Handling (Critical)

**Problem:** MiniMax-M2 reasoning content not properly handled in OpenAI-compatible mode without explicit configuration.

**Symptoms:**
- Reasoning wrapped in `<think>` tags appears in `delta.content`
- Should appear in `delta.reasoning_content` instead
- Causes parsing issues in downstream applications

**Solution:** Use `reasoning_split=True` parameter

```python
response = client.chat.completions.create(
    model="MiniMax-M2.1",
    messages=[{"role": "user", "content": "Solve this problem..."}],
    extra_body={"reasoning_split": True}  # Critical for proper reasoning handling
)
```

**With streaming:**
```python
for chunk in response:
    # Reasoning appears separately
    if hasattr(chunk.choices[0].delta, 'reasoning_details'):
        print(f"Thinking: {chunk.choices[0].delta.reasoning_details}")

    # Content appears clean
    if chunk.choices[0].delta.content:
        print(f"Content: {chunk.choices[0].delta.content}")
```

**Reference:** [GitHub Issue #3555](https://github.com/sst/opencode/issues/3555)

### Issue #2: Multi-turn Conversation Context

**Problem:** Model performance degrades without proper reasoning chain preservation.

**Solution:** Always include `tool_calls` field in conversation history:

```python
# Initial request
response = client.chat.completions.create(
    model="MiniMax-M2.1",
    messages=[{"role": "user", "content": "What's the weather in SF?"}],
    tools=tools,
    extra_body={"reasoning_split": True}
)

# Add complete response to history (including tool_calls)
messages.append(response.choices[0].message)

# Add tool result
messages.append({
    "role": "tool",
    "tool_call_id": tool_call.id,
    "content": tool_result
})

# Continue conversation with full context
next_response = client.chat.completions.create(
    model="MiniMax-M2.1",
    messages=messages,
    tools=tools
)
```

### Issue #3: vLLM Deployment Issues (Self-hosting)

**Problem:** Text degeneration and repetition loops with expert parallelism.

**Symptoms:**
- Model enters infinite repetition loops
- Reasoning inside `<think>` blocks never completes
- No proper answer produced

**Impact:** Only affects self-hosted vLLM deployments, not MiniMax API endpoint.

**Reference:** [GitHub Issue #31856](https://github.com/vllm-project/vllm/issues/31856)

### Issue #4: Manual Parsing Required (Non-vLLM/SGLang)

**Problem:** If using transformers, TGI, or other frameworks without built-in parsers, you must manually parse XML tags.

**Impact:** Requires custom parsing code to convert XML format to OpenAI format.

**Recommendation:** Use MiniMax hosted API or vLLM/SGLang to avoid manual parsing.

---

## 5. Authentication

### API Key Format

| Aspect | Details |
|--------|---------|
| **Key Source** | Dashboard → Settings → API Keys |
| **Format** | Standard Bearer token |
| **Header** | `Authorization: Bearer <API_KEY>` |
| **Environment** | `OPENAI_API_KEY` (when using OpenAI SDK) |
| **Security** | Never expose in client-side code |

### Best Practices

```python
import os
from openai import OpenAI

# Load from environment
client = OpenAI(
    api_key=os.getenv("MINIMAX_API_KEY"),
    base_url="https://api.minimax.io/v1"
)
```

---

## 6. Configuration Recommendations

### Required Configuration

```python
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_MINIMAX_API_KEY",
    base_url="https://api.minimax.io/v1",
    timeout=60.0,  # Recommended for longer generations
)

# For tool calling & reasoning tasks
response = client.chat.completions.create(
    model="MiniMax-M2.1",
    messages=messages,
    tools=tools,
    tool_choice="auto",
    extra_body={
        "reasoning_split": True,  # Critical for proper reasoning handling
    }
)
```

### Recommended Settings

| Parameter | Value | Reason |
|-----------|-------|--------|
| `reasoning_split` | `True` | Separates reasoning from content |
| `timeout` | `60-120s` | MiniMax models can take longer for reasoning |
| `max_tokens` | `4096+` | Allow space for reasoning + content |
| `temperature` | `0.7-1.0` | Optimal for M2 models |

---

## 7. Model Availability

### Supported Models via OpenAI API

| Model | Description | Speed | Best For |
|-------|-------------|-------|----------|
| **MiniMax-M2.1** | Enhanced programming experience | ~60 tps | Code refactoring, programming |
| **MiniMax-M2.1-lightning** | Faster, more agile | ~100 tps | Quick responses, real-time |
| **MiniMax-M2** | Advanced reasoning, agentic | ~60 tps | Complex reasoning, tool use |

### Pricing (via OpenAI Endpoint)

| Model | Input | Output | Prompt Cache Read | Prompt Cache Write |
|-------|-------|--------|-------------------|-------------------|
| M2.1 | $0.3/M | $1.2/M | $0.03/M | $0.375/M |
| M2.1-lightning | $0.3/M | $2.4/M | $0.03/M | $0.375/M |
| M2 | $0.3/M | $1.2/M | $0.03/M | $0.375/M |

---

## 8. Alternative: Anthropic-Compatible API

### Why Consider It?

MiniMax **recommends** their Anthropic-compatible interface for **full support of advanced features**.

### Endpoint

```
https://api.minimax.io/anthropic/v1/messages
```

### Advantages

- Native support for `<think>` tags
- Better reasoning content handling
- No need for `reasoning_split` parameter
- More aligned with M2's internal format

### Usage

```python
import anthropic

client = anthropic.Anthropic(
    api_key="YOUR_MINIMAX_API_KEY",
    base_url="https://api.minimax.io/anthropic"
)

response = client.messages.create(
    model="MiniMax-M2.1",
    messages=[{"role": "user", "content": "Hello!"}],
    max_tokens=1000
)
```

---

## 9. Risk Assessment: OpenAI SDK vs Claude SDK

### OpenAI SDK Approach

**Pros:**
- ✅ Familiar OpenAI API format
- ✅ Existing tooling and libraries
- ✅ Standard SSE streaming
- ✅ Wide ecosystem support

**Cons:**
- ⚠️ Requires `reasoning_split=True` configuration
- ⚠️ XML-to-JSON conversion overhead (hidden)
- ⚠️ Potential reasoning content issues if misconfigured
- ⚠️ Less aligned with MiniMax's native format

**Risk Level:** **Medium** - Works well but requires careful configuration

### Claude SDK Approach (Current Implementation)

**Pros:**
- ✅ Direct Claude API support
- ✅ Native streaming implementation
- ✅ Better integration with Anthropic's tool calling
- ✅ No format conversion needed for Claude models

**Cons:**
- ❌ Cannot use MiniMax models (no compatibility layer)
- ❌ Locked into Claude ecosystem
- ❌ Would require separate implementation for MiniMax

**Risk Level:** **Low** for Claude, **High** for multi-model support

### Hybrid Approach (Recommended)

**Strategy:** Use model-specific SDKs based on provider

```python
# For Claude models
from anthropic import Anthropic
claude_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# For MiniMax models
from openai import OpenAI
minimax_client = OpenAI(
    api_key=os.getenv("MINIMAX_API_KEY"),
    base_url="https://api.minimax.io/v1"
)

# Unified abstraction layer
def generate(model, messages, tools=None):
    if model.startswith("claude-"):
        return claude_client.messages.create(...)
    elif model.startswith("MiniMax-"):
        return minimax_client.chat.completions.create(
            ...,
            extra_body={"reasoning_split": True}
        )
```

**Risk Level:** **Low** - Best of both worlds

---

## 10. Recommendations

### For Production Use

1. **Use MiniMax Hosted API** (`https://api.minimax.io/v1`)
   - Handles XML-to-OpenAI conversion automatically
   - No deployment complexity
   - Official support

2. **Always Set `reasoning_split=True`**
   - Critical for proper reasoning handling
   - Prevents content parsing issues
   - Recommended by MiniMax

3. **Preserve Full Context in Multi-turn**
   - Include complete `tool_calls` in history
   - Maintains reasoning chain
   - Prevents performance degradation

4. **Configure Appropriate Timeouts**
   - Set 60-120s timeout for reasoning tasks
   - MiniMax models take longer than standard LLMs
   - Prevents premature disconnection

5. **Consider Anthropic API for Advanced Features**
   - Better aligned with M2's internal format
   - Native `<think>` tag support
   - Recommended by MiniMax

### For Development/Testing

1. **Use LiteLLM for Multi-Provider**
   - Unified interface for OpenAI, Claude, MiniMax
   - Automatic format conversion
   - Easier testing across providers

2. **Monitor for Known Issues**
   - Watch for reasoning content in wrong field
   - Check for XML tags in content
   - Validate tool call format

3. **Test Streaming Thoroughly**
   - Verify reasoning_details separation
   - Check for incomplete chunks
   - Validate [DONE] signal

---

## 11. Sources & References

### Official Documentation
- [Compatible OpenAI API - MiniMax API Docs](https://platform.minimax.io/docs/api-reference/text-openai-api)
- [MiniMax Tool Calling Guide](https://huggingface.co/MiniMaxAI/MiniMax-M2/blob/main/docs/tool_calling_guide.md)
- [MiniMax | LiteLLM Documentation](https://docs.litellm.ai/docs/providers/minimax)
- [M2.1 for AI Coding Tools - MiniMax API Docs](https://platform.minimax.io/docs/guides/text-ai-coding-tools)

### Integration Guides
- [How to Access the MiniMax M2.1 API](https://apidog.com/blog/minimax-m21-api/)
- [Deploying MiniMax M2.1 with vLLM: Complete Guide](https://docs.jarvislabs.ai/blog/minimax-m21-vllm-deployment-guide)
- [Community Providers: MiniMax - AI SDK](https://ai-sdk.dev/providers/community-providers/minimax)

### Known Issues
- [MiniMax-M2 reasoning content not properly handled - Issue #3555](https://github.com/sst/opencode/issues/3555)
- [Text degeneration / repetition loops - Issue #31856](https://github.com/vllm-project/vllm/issues/31856)
- [MiniMax-M2.1 NVFP4 fails on Blackwell - Issue #32826](https://github.com/vllm-project/vllm/issues/32826)

### Additional Resources
- [MiniMax on OpenRouter](https://openrouter.ai/minimax/minimax-m2)
- [MiniMax-M2 Review](https://mslinn.com/llm/7997-mini-agent.html)
- [MiniMax MCP Server](https://github.com/MiniMax-AI/MiniMax-MCP)

---

## Conclusion

**OpenAI SDK + MiniMax API is fully compatible** with the following requirements:

1. **Use hosted API** (`https://api.minimax.io/v1`)
2. **Set `reasoning_split=True`** for all requests
3. **Configure appropriate timeouts** (60-120s)
4. **Preserve full context** in multi-turn conversations

**Risk Assessment:** **Medium-Low** with proper configuration.

**Recommended Approach:** Implement unified abstraction supporting both Claude SDK (for Claude models) and OpenAI SDK (for MiniMax models), with model-specific optimizations (e.g., `reasoning_split` for MiniMax).

This provides maximum flexibility for multi-model support while maintaining optimal performance for each provider.
