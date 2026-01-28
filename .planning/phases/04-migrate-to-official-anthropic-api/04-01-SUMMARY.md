---
phase: 04-migrate-to-official-anthropic-api
plan: 01
subsystem: api
tags: [anthropic, minimax, api-client, backward-compatibility, temperature-validation, timeout]

# Dependency graph
requires:
  - phase: 02-tool-call-validation-session-history
    provides: Tool calling infrastructure and logging hooks
provides:
  - Dual-mode API client factory (official Anthropic / MiniMax)
  - Adaptive timeout configuration (120s official, 3000s MiniMax)
  - Conditional temperature validation (MiniMax-specific constraints)
  - Backward-compatible configuration for existing MiniMax users
affects: [04-02-migrate-to-official-model, testing, deployment]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "API mode detection via ANTHROPIC_BASE_URL pattern matching"
    - "Factory function for client creation with automatic configuration"
    - "Environment-aware validation (conditional constraints)"

key-files:
  created: []
  modified:
    - src/modules/generator.py
    - src/modules/agent_sdk.py
    - src/utils/temperature.py

key-decisions:
  - "Detect API mode via 'minimaxi.com' pattern in ANTHROPIC_BASE_URL"
  - "Official API uses standard authentication (api_key only)"
  - "MiniMax API requires custom Authorization header (backward compatible)"
  - "Official API timeout: 120s (vs 3000s for MiniMax reasoning model)"
  - "Temperature=0.0 allowed for official API, converted to 0.001 for MiniMax"

patterns-established:
  - "Factory function pattern: _create_anthropic_client() encapsulates API mode detection"
  - "Helper function pattern: _get_api_timeout_ms() returns adaptive configuration"
  - "API detection function: is_minimax_api() for reusable backend checking"

# Metrics
duration: 4min
completed: 2026-01-28
---

# Phase 04-01: Dual-Mode API Support Summary

**Automatic API mode detection with backward-compatible MiniMax fallback: factory functions for client creation, adaptive timeouts (120s/3000s), and conditional temperature validation**

## Performance

- **Duration:** 4 minutes
- **Started:** 2026-01-28T06:16:37Z
- **Completed:** 2026-01-28T06:20:27Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Created `_create_anthropic_client()` factory with automatic API detection (official/MiniMax/other)
- Implemented adaptive timeout configuration: 120s for official API, 3000s for MiniMax reasoning model
- Made temperature validation conditional: official API allows 0.0, MiniMax converts to 0.001
- Maintained 100% backward compatibility with existing MiniMax configurations
- All 27 existing tests pass with updated dual-mode behavior

## Task Commits

Each task was committed atomically:

1. **Task 1: Add dual-mode client factory to generator.py** - `5f72978` (feat)
2. **Task 2: Add adaptive timeout to agent_sdk.py** - `4c9a3b3` (feat)
3. **Task 3: Make temperature validation conditional** - `ab7d62a` (feat)

**Test updates:** `1e1fc50` (test: update tests for dual-mode API support)

## Files Created/Modified
- `src/modules/generator.py` - Factory function `_create_anthropic_client()` with API mode detection
- `src/modules/agent_sdk.py` - Adaptive timeout method `_get_api_timeout_ms()`
- `src/utils/temperature.py` - Conditional validation with `is_minimax_api()` helper

## Decisions Made

**1. API mode detection strategy**
- Use `"minimaxi.com" in ANTHROPIC_BASE_URL` as detection pattern
- Three modes: official (no base_url), MiniMax (minimaxi.com), other (third-party)
- Official API is default when ANTHROPIC_BASE_URL is not set

**2. Authentication configuration**
- Official API: simple `Anthropic(api_key=key)` - standard SDK authentication
- MiniMax API: requires `default_headers={"Authorization": "Bearer {key}"}` for compatibility
- Other APIs: basic `Anthropic(api_key, base_url)` without special headers

**3. Timeout configuration**
- Official API: 120s (120000ms) - sufficient for standard Claude models
- MiniMax API: 3000s (3000000ms) - required for M2.1 reasoning model deep thinking
- Rationale: MiniMax M2.1 can take extended time for complex reasoning tasks

**4. Temperature validation**
- Official API: Allow full [0.0, 1.0] range including 0.0 for deterministic output
- MiniMax API: Convert 0.0 to 0.001 to satisfy API constraint (0.0, 1.0] exclusive range
- Backward compatible: existing MiniMax users see no behavior change

**5. Backward compatibility guarantee**
- Default model remains "MiniMax-M2.1" (Plan 04-02 will change to official model)
- Existing `.env` files with `ANTHROPIC_BASE_URL` continue working unchanged
- No breaking changes to function signatures or behavior

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**1. Test failure: temperature validation**
- **Issue:** Existing test expected temperature=0.0 → 0.001 conversion without MiniMax context
- **Resolution:** Updated test to set `ANTHROPIC_BASE_URL` with MiniMax pattern, validating dual-mode behavior
- **Outcome:** Test now verifies conditional validation works correctly for both API modes

**2. Test failure: MiniMax client creation**
- **Issue:** Test expected client creation without Authorization header (old behavior)
- **Resolution:** Updated test to expect `default_headers` parameter in MiniMax mode
- **Outcome:** Test now validates that MiniMax API includes required authentication header

All tests pass after updates (27/27 passing).

## Verification Results

**Factory function test:**
```
Official mode: base_url=https://api.anthropic.com
```
✓ Official API detected and configured correctly

**Timeout detection test:**
```
Official timeout: 120000ms
MiniMax timeout: 3000000ms
```
✓ Adaptive timeout configuration works for both backends

**Temperature validation test:**
```
Official API detected: False
Official temp=0.0: 0.0
MiniMax API detected: True
MiniMax temp=0.0: 0.001
```
✓ Conditional validation respects API backend constraints

**Test suite:**
All 27 generator tests pass with dual-mode configuration.

## User Setup Required

None - no external service configuration required.

Users with existing MiniMax configurations continue working unchanged.
Users without `ANTHROPIC_BASE_URL` will use official Anthropic API (requires valid ANTHROPIC_API_KEY).

## Next Phase Readiness

**Ready for Plan 04-02:**
- Dual-mode infrastructure complete
- Backward compatibility preserved
- Can safely change default model to official Claude model

**No blockers identified:**
- All tests passing
- API detection working correctly
- Timeout and temperature handling verified

**Note for Plan 04-02:**
Changing default model from "MiniMax-M2.1" to official Claude model (e.g., "claude-sonnet-4.5") will complete the migration. Users without ANTHROPIC_BASE_URL will then use official API with official models automatically.

---
*Phase: 04-migrate-to-official-anthropic-api*
*Completed: 2026-01-28*
