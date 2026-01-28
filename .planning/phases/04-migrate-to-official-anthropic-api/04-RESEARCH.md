# Phase 4: 迁移到官方 Anthropic API - Research

**Researched:** 2026-01-28
**Domain:** API Migration / Claude Agent SDK Integration
**Confidence:** HIGH

## Summary

The codebase currently uses MiniMax API as an Anthropic-compatible third-party endpoint. Migration to official Anthropic API involves removing MiniMax-specific adaptations while preserving the Claude Agent SDK integration. The official API has simpler requirements: standard base URL, x-api-key authentication, and no special parameters.

**Key findings:**
- MiniMax adaptations are isolated to 5 specific areas: base URL, authentication headers, temperature validation, timeout configuration, and documentation
- Official Anthropic API uses standard REST endpoint at `https://api.anthropic.com/v1/messages`
- Claude Agent SDK natively supports official API with `ANTHROPIC_API_KEY` environment variable
- Tool calling mechanism remains unchanged (Skills loaded via `setting_sources=['user']`)
- Migration can be phased with backward compatibility via environment variable detection

**Primary recommendation:** Implement a dual-mode configuration that detects whether official or MiniMax API is configured, removing MiniMax-specific code only when official API is active. This ensures zero-downtime migration and allows testing before full cutover.

## Standard Stack

### Official Anthropic API

| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| **Anthropic Python SDK** | 0.44.0+ (Jan 2026) | Official client library | Handles authentication, streaming, error handling automatically |
| **Claude Agent SDK** | Latest | Agentic workflow with tools | Official agent framework from Anthropic, supports Skills/hooks/sessions |
| **Environment Variables** | N/A | Configuration | `ANTHROPIC_API_KEY` is the standard authentication method |

### Current MiniMax Stack (To Remove)

| Component | Purpose | Removal Strategy |
|-----------|---------|------------------|
| `ANTHROPIC_BASE_URL` | Points to MiniMax endpoint | Remove or detect to disable MiniMax adaptations |
| `validate_temperature()` | Ensures temperature > 0.0 for MiniMax | Make conditional on MiniMax mode |
| `default_headers` | Custom `Authorization: Bearer` header | Remove - SDK handles x-api-key automatically |
| `API_TIMEOUT_MS=3000000` | 3000s timeout for MiniMax reasoning | Reduce to standard timeout (60-120s) for official API |
| MiniMax-specific docs | `.env.example`, README sections | Archive or move to legacy section |

**Installation:**
```bash
# Already installed in project
pip install anthropic claude-agent-sdk

# No additional dependencies needed for migration
```

## Architecture Patterns

### Recommended Migration Strategy

```
Phase A: Add Detection Logic
├── Detect ANTHROPIC_BASE_URL presence
├── If MiniMax: use existing adaptations
└── If official: use standard configuration

Phase B: Remove MiniMax Code
├── Delete temperature validation
├── Remove custom headers
├── Simplify timeout configuration
└── Update documentation

Phase C: Clean Environment
├── Update .env.example
├── Remove MiniMax references
└── Add migration guide
```

### Pattern 1: Dual-Mode Configuration

**What:** Environment-based detection to support both official and MiniMax APIs during transition
**When to use:** When you need zero-downtime migration with rollback capability

**Example:**
```python
# src/modules/generator.py
def _create_anthropic_client(api_key: str) -> Anthropic:
    """
    Create Anthropic client with automatic mode detection.

    Official API: Uses standard authentication via api_key parameter
    MiniMax API: Uses custom base_url and Authorization header
    """
    base_url = os.getenv("ANTHROPIC_BASE_URL")

    if base_url and "minimaxi.com" in base_url:
        # MiniMax mode: requires special authentication
        return Anthropic(
            api_key=api_key,
            base_url=base_url,
            default_headers={"Authorization": f"Bearer {api_key}"}
        )
    elif base_url:
        # Other third-party API
        return Anthropic(api_key=api_key, base_url=base_url)
    else:
        # Official Anthropic API: standard configuration
        return Anthropic(api_key=api_key)
```

### Pattern 2: Conditional Temperature Validation

**What:** Only apply MiniMax temperature constraints when using MiniMax API
**When to use:** When official API supports full [0.0, 1.0] range

**Example:**
```python
# src/modules/generator.py
def _prepare_temperature(temp: float) -> float:
    """
    Prepare temperature parameter based on API backend.

    MiniMax requires: (0.0, 1.0] exclusive of 0.0
    Official Anthropic allows: [0.0, 1.0] inclusive
    """
    base_url = os.getenv("ANTHROPIC_BASE_URL", "")

    if "minimaxi.com" in base_url:
        # MiniMax mode: validate temperature
        from ..utils import validate_temperature
        return validate_temperature(temp)

    # Official API: allow full range
    return max(0.0, min(1.0, temp))
```

### Pattern 3: Adaptive Timeout Configuration

**What:** Use appropriate timeout based on API characteristics
**When to use:** Different APIs have different reasoning speeds

**Example:**
```python
# src/modules/agent_sdk.py
def _get_api_timeout_ms(self) -> str:
    """
    Get appropriate API timeout based on backend.

    MiniMax M2.1: 3000s (reasoning model needs long timeout)
    Official API: 120s (standard timeout sufficient)
    """
    base_url = os.getenv("ANTHROPIC_BASE_URL", "")

    if "minimaxi.com" in base_url:
        return "3000000"  # 3000s for MiniMax reasoning

    return "120000"  # 120s for official API
```

### Anti-Patterns to Avoid

- **Don't hardcode base URLs**: Always use environment variables for flexibility
- **Don't assume model names**: MiniMax uses "MiniMax-M2.1", official uses "claude-sonnet-4-5" etc.
- **Don't mix authentication methods**: Either custom headers OR api_key parameter, not both
- **Don't remove MiniMax code without detection**: Support both modes during transition

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| API authentication | Custom header management | Anthropic SDK built-in | SDK handles x-api-key, anthropic-version, content-type headers automatically |
| Streaming handling | Custom SSE parser | SDK `.messages.stream()` | SDK manages connection, parsing, error recovery |
| Tool calling loop | Manual tool execution loop | Claude Agent SDK `query()` | Agent SDK handles tool execution, session management, hooks automatically |
| Environment config | Custom config loader | `os.getenv()` + SDK defaults | SDK automatically reads `ANTHROPIC_API_KEY` from environment |
| Retry logic | Custom backoff implementation | SDK built-in retry | SDK includes exponential backoff for rate limits and transient errors |

**Key insight:** The Anthropic SDK is designed for official API - custom adaptations for third-party APIs add complexity. Official API works "out of the box" with minimal configuration.

## Common Pitfalls

### Pitfall 1: Forgetting to Remove MiniMax-Specific Environment Variables

**What goes wrong:** After migration, leftover `ANTHROPIC_BASE_URL` pointing to MiniMax causes requests to fail with 401
**Why it happens:** Environment variables persist across sessions, `.env` file not updated
**How to avoid:**
1. Document all environment variables that must change
2. Provide migration checklist
3. Add startup validation that detects conflicting configuration

**Warning signs:**
- Error: "Invalid API key" despite correct `ANTHROPIC_API_KEY`
- Requests going to wrong endpoint (check logs)
- Tool calling fails after migration

**Prevention:**
```python
# Add to startup validation
base_url = os.getenv("ANTHROPIC_BASE_URL")
api_key = os.getenv("ANTHROPIC_API_KEY")

if base_url and "minimaxi.com" not in base_url and "anthropic.com" not in base_url:
    print(f"⚠️  WARNING: ANTHROPIC_BASE_URL is set to {base_url}")
    print("   This may interfere with official API. Unset it to use official endpoint.")
```

### Pitfall 2: Model Name Mismatch

**What goes wrong:** Code defaults to "MiniMax-M2.1" model name, which doesn't exist on official API
**Why it happens:** Model names are hardcoded in multiple files
**How to avoid:**
1. Grep for all "MiniMax" references
2. Update default model to official Claude model
3. Make model name configurable via environment variable

**Warning signs:**
- Error: "model: Input should be 'claude-3-5-sonnet-20241022' or similar"
- 404 Not Found errors from API

**Prevention:**
```python
# src/modules/generator.py - Update defaults
def generate(
    topic: str,
    search_results: List[SearchResult],
    api_key: str,
    model: str = os.getenv("MODEL_NAME", "claude-sonnet-4-5"),  # Official default
    ...
):
```

### Pitfall 3: Timeout Too Long for Official API

**What goes wrong:** 3000s timeout causes hung connections on official API, wastes resources
**Why it happens:** MiniMax's reasoning model needed extreme timeout, official API doesn't
**How to avoid:**
1. Use adaptive timeout based on detected backend
2. Official API: 60-120s is sufficient
3. Document timeout expectations

**Warning signs:**
- Connections stay open for minutes after response complete
- Resource exhaustion under load
- Slow test suite execution

### Pitfall 4: Temperature Validation Breaking Official API

**What goes wrong:** Forcing temperature > 0.0 prevents using exact temperature=0.0 for deterministic output
**Why it happens:** MiniMax requires (0.0, 1.0] exclusive range, official allows [0.0, 1.0] inclusive
**How to avoid:**
1. Make validation conditional on backend
2. Official API: allow full [0.0, 1.0] range
3. Keep validation for MiniMax mode

**Warning signs:**
- Cannot get deterministic output even with temperature=0.0
- Tests fail expecting exact temperature values

### Pitfall 5: Custom Headers Conflicting with SDK

**What goes wrong:** Setting both `default_headers={"Authorization": ...}` and `api_key` parameter causes authentication errors
**Why it happens:** SDK sends x-api-key header, custom Authorization header conflicts
**How to avoid:**
1. Official API: only use `api_key` parameter, no custom headers
2. Let SDK handle all authentication headers
3. Remove all `default_headers` for official API

**Warning signs:**
- 401 Unauthorized despite valid API key
- Double authentication headers in request logs

## Code Examples

Verified patterns from official sources:

### Official API Authentication (Standard)

```python
# Source: https://platform.claude.com/docs/en/api/getting-started
import os
from anthropic import Anthropic

# Official API: reads ANTHROPIC_API_KEY automatically
client = Anthropic()

# Or explicit:
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello, Claude"}]
)
```

### Claude Agent SDK with Official API

```python
# Source: https://platform.claude.com/docs/en/agent-sdk/overview
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

async def main():
    # SDK reads ANTHROPIC_API_KEY automatically
    # No need to set ANTHROPIC_BASE_URL
    async for message in query(
        prompt="Find and fix the bug in auth.py",
        options=ClaudeAgentOptions(
            model="claude-sonnet-4-5",  # Official model name
            allowed_tools=["Read", "Edit", "Bash"],
            setting_sources=["user"]  # Load Skills from ~/.claude/skills/
        )
    ):
        if hasattr(message, "result"):
            print(message.result)

asyncio.run(main())
```

### Streaming with Official API

```python
# Source: https://docs.anthropic.com/en/api/messages-streaming
from anthropic import Anthropic

client = Anthropic()

with client.messages.stream(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello"}],
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
```

### Migration-Safe Client Factory

```python
# Recommended pattern for smooth migration
def create_client(api_key: str) -> Anthropic:
    """
    Create Anthropic client with backward compatibility.

    Detects ANTHROPIC_BASE_URL to support both:
    - Official API (no base_url)
    - MiniMax API (custom base_url + headers)
    """
    base_url = os.getenv("ANTHROPIC_BASE_URL")

    if not base_url:
        # Official API: standard configuration
        print("✅ Using official Anthropic API")
        return Anthropic(api_key=api_key)

    # Third-party API detected
    print(f"⚠️  Using third-party API: {base_url}")

    if "minimaxi.com" in base_url:
        # MiniMax requires custom Authorization header
        return Anthropic(
            api_key=api_key,
            base_url=base_url,
            default_headers={"Authorization": f"Bearer {api_key}"}
        )

    # Other third-party
    return Anthropic(api_key=api_key, base_url=base_url)
```

## State of the Art

| Old Approach (MiniMax) | Current Approach (Official) | Impact |
|------------------------|----------------------------|--------|
| `ANTHROPIC_BASE_URL=https://api.minimaxi.com/anthropic` | No `ANTHROPIC_BASE_URL` set | Simpler configuration, uses official endpoint |
| Custom `Authorization: Bearer` header | SDK automatic `x-api-key` header | No custom header code needed |
| Temperature validation: `(0.0, 1.0]` exclusive | Temperature range: `[0.0, 1.0]` inclusive | Can use exact 0.0 for deterministic output |
| `API_TIMEOUT_MS=3000000` (3000s) | Standard timeout 60-120s | Faster failure detection, less resource waste |
| Model: `MiniMax-M2.1` | Model: `claude-sonnet-4-5`, `claude-opus-4-5` | Use latest Claude models |
| `reasoning_split=True` parameter | Not needed - native thinking support | Simpler request structure |

**Deprecated/outdated:**
- `validate_temperature()` utility: Only needed for MiniMax, official API allows full range
- Custom `default_headers`: SDK handles authentication automatically
- Extreme timeout configuration: Official API doesn't need 3000s timeout
- MiniMax-specific environment variables: `MINIMAX_REASONING_SPLIT`, `MINIMAX_MASK_SENSITIVE_INFO`

## Migration Path

### Phase 1: Add Detection & Dual-Mode Support (Safe Migration)

**Goal:** Support both APIs simultaneously, allow testing official API without breaking MiniMax users

**Changes:**
1. Add `_create_anthropic_client()` factory function with MiniMax detection
2. Make temperature validation conditional
3. Make timeout configuration adaptive
4. Add startup warnings for configuration issues

**Risk:** LOW - Backward compatible, no breaking changes

### Phase 2: Update Defaults to Official API

**Goal:** Make official API the default, keep MiniMax as fallback

**Changes:**
1. Update `.env.example` to show official API as primary
2. Change default model from "MiniMax-M2.1" to "claude-sonnet-4-5"
3. Update README with official API setup instructions
4. Add migration guide for MiniMax users

**Risk:** LOW - Users must explicitly opt into MiniMax mode

### Phase 3: Remove MiniMax-Specific Code

**Goal:** Clean up codebase, remove unused adaptations

**Changes:**
1. Remove `src/utils/temperature.py` (or archive)
2. Remove MiniMax detection logic
3. Remove custom header handling
4. Simplify timeout configuration
5. Remove MiniMax documentation

**Risk:** MEDIUM - Breaking change for MiniMax users, requires communication

**Prerequisites:**
- All users confirmed migrated to official API
- MiniMax integration documented separately (if still needed)
- Tests updated to use official API

## Testing Strategy

### Pre-Migration Testing (Verify Current State)

```bash
# 1. Verify MiniMax configuration still works
export ANTHROPIC_BASE_URL=https://api.minimaxi.com/anthropic/v1/messages
export ANTHROPIC_API_KEY=your-minimax-key
pytest tests/test_minimax_integration.py -v

# 2. Verify tool calling works with MiniMax
python test_tool_calls.py
```

### Migration Testing (Dual-Mode Verification)

```bash
# 1. Test official API with new detection logic
unset ANTHROPIC_BASE_URL
export ANTHROPIC_API_KEY=your-anthropic-key
pytest tests/test_e2e.py -v

# 2. Verify MiniMax still works (backward compat)
export ANTHROPIC_BASE_URL=https://api.minimaxi.com/anthropic/v1/messages
export ANTHROPIC_API_KEY=your-minimax-key
pytest tests/test_e2e.py -v

# 3. Test temperature handling both modes
pytest tests/test_temperature_validation.py -v
```

### Post-Migration Testing (Official API Only)

```bash
# 1. Verify official API integration
export ANTHROPIC_API_KEY=your-anthropic-key
pytest tests/test_e2e_tool_calling.py -v

# 2. Verify tool calling works on official API
python -c "from claude_agent_sdk import query, ClaudeAgentOptions; import asyncio; asyncio.run(query('What files are in this directory?', ClaudeAgentOptions(allowed_tools=['Bash'])))"

# 3. Run full test suite
pytest tests/ -v --tb=short
```

### Success Criteria Validation

After migration, verify:
1. ✅ System uses `https://api.anthropic.com` (check logs)
2. ✅ No MiniMax-specific environment variables set
3. ✅ Tool calling works (tool_call_count > 0)
4. ✅ All integration tests pass
5. ✅ Documentation updated

## Configuration Changes

### Environment Variables (Before → After)

```bash
# BEFORE (MiniMax API)
ANTHROPIC_API_KEY=your-minimax-api-key
ANTHROPIC_BASE_URL=https://api.minimaxi.com/anthropic/v1/messages
API_TIMEOUT_MS=3000000
ANTHROPIC_REQUEST_TIMEOUT=3000
MODEL_NAME=MiniMax-M2.1
MINIMAX_REASONING_SPLIT=true
MINIMAX_MASK_SENSITIVE_INFO=false

# AFTER (Official Anthropic API)
ANTHROPIC_API_KEY=your-anthropic-api-key
# ANTHROPIC_BASE_URL not set (or removed)
# API_TIMEOUT_MS not needed (SDK uses sane defaults)
MODEL_NAME=claude-sonnet-4-5
# MiniMax-specific vars removed
```

### .env.example Changes

```diff
-# =====================================================
-# API 配置 - 选择使用官方 API 或 MiniMax API
-# =====================================================
+# =====================================================
+# API 配置 - 使用官方 Anthropic API
+# =====================================================

-# 选项 1: 使用官方 Anthropic API（推荐）
+# 官方 Anthropic API 配置
 # ---------------------------------------------------
 ANTHROPIC_API_KEY=your-anthropic-api-key
-# 注意：使用官方 API 时，不要设置 ANTHROPIC_BASE_URL
-
-# 选项 2: 使用 MiniMax API（兼容 Claude 协议）
-# ---------------------------------------------------
-# 如需使用 MiniMax，取消注释以下行：
-# MINIMAX_API_KEY=your-minimax-api-key
-# ANTHROPIC_BASE_URL=https://api.minimaxi.com/anthropic/v1/messages

-# =====================================================
-# MiniMax 专用配置（仅在使用 MiniMax API 时生效）
-# =====================================================
-
-# API 超时设置（3000秒 = 50分钟）
-# 解决推理模型深思时的流停顿问题
-API_TIMEOUT_MS=3000000
-
-# Anthropic SDK 请求超时（秒）
-ANTHROPIC_REQUEST_TIMEOUT=3000
-
-# 减少非必要流量，降低流解析压力
-CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
-
-# 启用思维拆分（reasoning_split）
-# 将思考内容与最终答案物理隔离
-MINIMAX_REASONING_SPLIT=true
-
-# 禁用敏感信息掩码（代码生成场景）
-MINIMAX_MASK_SENSITIVE_INFO=false
+# 获取 API Key: https://platform.claude.com/settings/keys

 # =====================================================
 # 模型配置
 # =====================================================

 # 默认模型名称
-# 官方 API 使用: claude-sonnet-4-5-20250514, claude-3-5-sonnet-latest 等
-# MiniMax 使用: MiniMax-M2.1
 MODEL_NAME=claude-sonnet-4-20250514
```

### Code Files to Modify

| File | Changes | Reason |
|------|---------|--------|
| `src/modules/generator.py` | Remove custom `default_headers`, simplify client creation | Official API doesn't need custom headers |
| `src/modules/agent_sdk.py` | Remove or reduce `API_TIMEOUT_MS` config | Official API doesn't need 3000s timeout |
| `src/utils/temperature.py` | Archive or make conditional | Official API allows temperature=0.0 |
| `.env.example` | Remove MiniMax section, update comments | Simplify configuration documentation |
| `README.md` / `docs/` | Update API setup instructions | Guide users to official API |
| `tests/test_minimax_integration.py` | Archive or mark as legacy | No longer testing primary path |

## Risk Assessment

### Low Risk (Can Do Anytime)

- ✅ Add dual-mode detection logic (backward compatible)
- ✅ Update `.env.example` documentation
- ✅ Add migration guide for users
- ✅ Test official API in parallel with MiniMax

### Medium Risk (Requires Coordination)

- ⚠️ Change default model name to Claude (breaking for MiniMax users)
- ⚠️ Remove temperature validation (affects deterministic output)
- ⚠️ Update timeout configuration (may expose latency issues)

### High Risk (Breaking Change)

- ❌ Remove MiniMax detection code (no fallback)
- ❌ Delete `validate_temperature()` utility (breaks MiniMax)
- ❌ Remove custom header handling (MiniMax authentication fails)

**Mitigation:** Use phased rollout with feature flags, maintain MiniMax compatibility branch if needed

## Open Questions

1. **Should we maintain MiniMax support long-term?**
   - What we know: MiniMax adaptations add complexity, official API is simpler
   - What's unclear: Are there users depending on MiniMax API?
   - Recommendation: Phase out MiniMax support after all users migrate, or maintain as separate branch

2. **What's the official API's actual timeout behavior?**
   - What we know: Documentation suggests 60-120s is typical
   - What's unclear: Does official API support extended thinking like MiniMax M2.1?
   - Recommendation: Test with complex reasoning tasks, adjust timeout if needed

3. **Should temperature validation be removed or just conditional?**
   - What we know: Official API allows [0.0, 1.0], MiniMax requires (0.0, 1.0]
   - What's unclear: Is there any benefit to keeping validation for official API?
   - Recommendation: Make conditional on backend, keep validation for MiniMax mode

## Sources

### Primary (HIGH confidence)

- [Anthropic API Overview](https://platform.claude.com/docs/en/api/getting-started) - Official base URL, authentication requirements
- [Anthropic Messages API](https://docs.anthropic.com/en/api/messages) - Request/response format
- [Claude Agent SDK Overview](https://platform.claude.com/docs/en/agent-sdk/overview) - Setting sources, allowed_tools configuration
- [Anthropic Python SDK GitHub](https://github.com/anthropics/anthropic-sdk-python) - Authentication methods

### Secondary (MEDIUM confidence)

- [Anthropic API Messages Streaming](https://docs.anthropic.com/en/api/messages-streaming) - Streaming implementation details
- [Claude Agent SDK Python Reference](https://platform.claude.com/docs/en/agent-sdk/python) - Configuration options

### Tertiary (LOW confidence - project-specific research)

- `.planning/research/OpenAI-SDK-MiniMax-Compatibility.md` - MiniMax API differences (internal doc)
- `.planning/research/SDK与MiniMax流式传输实现的兼容性架构与工程解决方案深度报告.md` - MiniMax streaming issues (internal doc)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Official Anthropic documentation verified
- Architecture: HIGH - Migration patterns based on official SDK usage
- Pitfalls: HIGH - Identified from codebase analysis and documentation
- MiniMax specifics: HIGH - Verified from existing codebase implementation

**Research date:** 2026-01-28
**Valid until:** 60 days (official API stable, but SDK may update)

**Codebase analysis:**
- Files analyzed: 15+ (generator.py, agent_sdk.py, temperature.py, .env.example, tests/)
- MiniMax references found: 66 locations across codebase
- Adaptation areas identified: 5 (base URL, headers, temperature, timeout, docs)
