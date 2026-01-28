#!/usr/bin/env python3
"""Standalone MiniMax API connectivity diagnostic - no SDK dependencies

This script validates MiniMax API connectivity by making direct HTTP requests
using httpx, completely bypassing the Claude Agent SDK. This helps isolate
whether API issues are network/configuration related or SDK-specific.

Tests performed:
1. Basic API call without tools (baseline connectivity)
2. API call with tool definitions (validates tool schema compatibility)

Each test includes detailed diagnostic output to help identify the root cause
of any connectivity issues.
"""
import asyncio
import httpx
import json
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
API_KEY = os.getenv("ANTHROPIC_API_KEY")
BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.minimaxi.com/anthropic")
MODEL = os.getenv("ANTHROPIC_MODEL", "MiniMax-M2.1")

# Test configuration
TIMEOUT_SECONDS = 30
REQUEST_HEADERS = {
    "Content-Type": "application/json",
    "anthropic-version": "2023-06-01",
}


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def print_result(passed: bool, message: str):
    """Print test result with color coding"""
    status = "PASS" if passed else "FAIL"
    symbol = "✓" if passed else "✗"
    print(f"\n[{symbol}] {status}: {message}\n")


async def test_basic_connectivity():
    """Test 1: Basic API call without tools

    This test validates basic connectivity to the MiniMax API endpoint
    without any tool definitions. Success here confirms:
    - Network can reach the API endpoint
    - API key is valid
    - API accepts basic message requests
    """
    print_section("Test 1: Basic API Connectivity (No Tools)")

    if not API_KEY:
        print_result(False, "ANTHROPIC_API_KEY not set in environment")
        return False

    endpoint = f"{BASE_URL.rstrip('/')}/v1/messages"

    print(f"API Endpoint: {endpoint}")
    print(f"Model: {MODEL}")
    print(f"Timeout: {TIMEOUT_SECONDS}s")
    print(f"API Key: {API_KEY[:10]}...{API_KEY[-4:] if len(API_KEY) > 14 else '***'}")

    # Construct request payload
    payload = {
        "model": MODEL,
        "max_tokens": 100,
        "messages": [
            {
                "role": "user",
                "content": "Say 'API connection successful' and nothing else."
            }
        ]
    }

    print(f"\nRequest payload:")
    print(json.dumps(payload, indent=2))

    headers = {
        **REQUEST_HEADERS,
        "x-api-key": API_KEY
    }

    try:
        start_time = time.time()

        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            print(f"\nSending request... (timeout: {TIMEOUT_SECONDS}s)")

            response = await client.post(
                endpoint,
                json=payload,
                headers=headers
            )

            elapsed = time.time() - start_time

            print(f"Response time: {elapsed:.2f}s")
            print(f"Status code: {response.status_code}")

            # Parse response
            try:
                response_data = response.json()
                response_text = json.dumps(response_data, indent=2)[:500]
                print(f"\nResponse body (first 500 chars):")
                print(response_text)
                if len(json.dumps(response_data)) > 500:
                    print("... (truncated)")
            except json.JSONDecodeError:
                print(f"\nResponse body (not JSON):")
                print(response.text[:500])

            # Determine success
            success = 200 <= response.status_code < 300

            if success:
                print_result(True, f"API connection successful (HTTP {response.status_code}, {elapsed:.2f}s)")
            else:
                print_result(False, f"API returned error status {response.status_code}")

            return success

    except asyncio.TimeoutError:
        print_result(False, f"Request timed out after {TIMEOUT_SECONDS}s")
        print("\nPossible causes:")
        print("  - Network/firewall blocking access to MiniMax")
        print("  - API endpoint unreachable")
        print("  - DNS resolution issues")
        return False

    except httpx.ConnectError as e:
        print_result(False, f"Connection error: {e}")
        print("\nPossible causes:")
        print("  - Invalid ANTHROPIC_BASE_URL")
        print("  - Network connectivity issues")
        print("  - Firewall blocking outbound connections")
        return False

    except Exception as e:
        print_result(False, f"Unexpected error: {type(e).__name__}: {e}")
        return False


async def test_with_tool_definitions():
    """Test 2: API call with tool definitions

    This test validates that the MiniMax API correctly accepts and parses
    tool definitions in the request. Success here confirms:
    - API supports tool definitions (not all Anthropic-compatible APIs do)
    - Tool schema format is compatible
    - No parsing errors for tool definitions
    """
    print_section("Test 2: API Call with Tool Definitions")

    if not API_KEY:
        print_result(False, "ANTHROPIC_API_KEY not set in environment")
        return False

    endpoint = f"{BASE_URL.rstrip('/')}/v1/messages"

    # Mock tool definition (similar to what SDK would send)
    mock_tool = {
        "name": "query_knowledge_base",
        "description": "Query the NotebookLM knowledge base for relevant information",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to execute"
                }
            },
            "required": ["query"]
        }
    }

    payload = {
        "model": MODEL,
        "max_tokens": 100,
        "tools": [mock_tool],
        "messages": [
            {
                "role": "user",
                "content": "You have access to a knowledge base. Confirm you can see the tools available."
            }
        ]
    }

    print(f"API Endpoint: {endpoint}")
    print(f"Model: {MODEL}")
    print(f"\nRequest payload (with tools):")
    print(json.dumps(payload, indent=2)[:1000])
    if len(json.dumps(payload)) > 1000:
        print("... (truncated)")

    headers = {
        **REQUEST_HEADERS,
        "x-api-key": API_KEY
    }

    try:
        start_time = time.time()

        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            print(f"\nSending request with tool definitions... (timeout: {TIMEOUT_SECONDS}s)")

            response = await client.post(
                endpoint,
                json=payload,
                headers=headers
            )

            elapsed = time.time() - start_time

            print(f"Response time: {elapsed:.2f}s")
            print(f"Status code: {response.status_code}")

            # Parse response
            try:
                response_data = response.json()

                # Check for tool-related errors
                error_indicators = []
                response_str = json.dumps(response_data).lower()

                if "tool" in response_str and "error" in response_str:
                    error_indicators.append("Response contains 'tool' + 'error'")
                if "invalid" in response_str and "schema" in response_str:
                    error_indicators.append("Response contains 'invalid' + 'schema'")
                if "unsupported" in response_str:
                    error_indicators.append("Response contains 'unsupported'")

                response_text = json.dumps(response_data, indent=2)[:500]
                print(f"\nResponse body (first 500 chars):")
                print(response_text)
                if len(json.dumps(response_data)) > 500:
                    print("... (truncated)")

                if error_indicators:
                    print(f"\nWarning: Potential tool-related errors detected:")
                    for indicator in error_indicators:
                        print(f"  - {indicator}")

            except json.JSONDecodeError:
                print(f"\nResponse body (not JSON):")
                print(response.text[:500])

            # Determine success
            success = 200 <= response.status_code < 300

            if success:
                print_result(True, f"API accepted tool definitions (HTTP {response.status_code}, {elapsed:.2f}s)")
                if not error_indicators:
                    print("No tool-related error indicators found in response.")
                else:
                    print("Note: Error indicators detected - manual review recommended.")
            else:
                print_result(False, f"API returned error status {response.status_code}")

            return success

    except asyncio.TimeoutError:
        print_result(False, f"Request timed out after {TIMEOUT_SECONDS}s")
        print("\nNote: Timeout with tools may indicate tool parsing issues on API side")
        return False

    except httpx.ConnectError as e:
        print_result(False, f"Connection error: {e}")
        return False

    except Exception as e:
        print_result(False, f"Unexpected error: {type(e).__name__}: {e}")
        return False


async def main():
    """Run all diagnostic tests"""
    print_section("MiniMax API Connectivity Diagnostic")

    print("Configuration:")
    print(f"  ANTHROPIC_BASE_URL: {BASE_URL}")
    print(f"  ANTHROPIC_MODEL: {MODEL}")
    print(f"  ANTHROPIC_API_KEY: {'Set' if API_KEY else 'NOT SET'}")

    if not API_KEY:
        print("\nERROR: ANTHROPIC_API_KEY environment variable not set")
        print("Please set it in your .env file or environment")
        return

    # Run tests
    results = {}

    results["basic"] = await test_basic_connectivity()

    # Only run tool test if basic connectivity works
    if results["basic"]:
        results["tools"] = await test_with_tool_definitions()
    else:
        print_section("Test 2: Skipped")
        print("Skipping tool definition test because basic connectivity failed.")
        print("Fix basic connectivity issues first, then re-run this diagnostic.")
        results["tools"] = None

    # Final summary
    print_section("Diagnostic Summary")

    print("Test Results:")
    print(f"  1. Basic Connectivity: {'PASS' if results['basic'] else 'FAIL'}")

    if results["tools"] is None:
        print(f"  2. Tool Definitions: SKIPPED")
    else:
        print(f"  2. Tool Definitions: {'PASS' if results['tools'] else 'FAIL'}")

    # Overall verdict
    print("\nOverall Verdict:")

    if results["basic"] and results["tools"]:
        print("✓ MiniMax API is fully operational and accepts tool definitions")
        print("  - API-01 VERIFIED: MiniMax API accepts tool-enabled requests")
        print("  - API-02 VERIFIED: Tool definition format compatible")
        print("\nNext steps:")
        print("  - Run integration tests: pytest tests/test_tool_registration.py -v -s")

    elif results["basic"] and not results["tools"]:
        print("⚠ Basic connectivity works, but tool definitions may have issues")
        print("  - API-01 PARTIAL: Basic API works")
        print("  - API-02 UNCLEAR: Tool definition compatibility needs investigation")
        print("\nNext steps:")
        print("  - Review tool-related error messages above")
        print("  - Check if MiniMax API supports Anthropic tool format")

    elif not results["basic"]:
        print("✗ Cannot connect to MiniMax API")
        print("  - API-01 BLOCKED: Basic connectivity failed")
        print("  - API-02 BLOCKED: Cannot test without connectivity")
        print("\nNext steps:")
        print("  - Verify ANTHROPIC_BASE_URL is correct")
        print("  - Verify ANTHROPIC_API_KEY is valid")
        print("  - Check network/firewall settings")
        print("  - Try accessing API from browser/curl")


if __name__ == "__main__":
    asyncio.run(main())
