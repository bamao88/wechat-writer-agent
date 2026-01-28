"""Temperature parameter validation with API-aware behavior.

MiniMax API requires temperature > 0.0, official Anthropic API allows = 0.0.
"""
import os


def is_minimax_api() -> bool:
    """Check if using MiniMax API based on ANTHROPIC_BASE_URL."""
    base_url = os.getenv("ANTHROPIC_BASE_URL", "")
    return "minimaxi.com" in base_url


def validate_temperature(temp: float) -> float:
    """
    Validate and adjust temperature parameter.

    MiniMax API: Requires temperature in (0.0, 1.0] range (exclusive of 0.0)
    Official API: Allows full [0.0, 1.0] range (inclusive)

    Args:
        temp: Original temperature value

    Returns:
        Adjusted temperature value (unchanged for official API)

    Examples:
        # With MiniMax API:
        >>> validate_temperature(0.0)  # Returns 0.001

        # With official API:
        >>> validate_temperature(0.0)  # Returns 0.0
    """
    # Clamp to valid range first
    temp = max(0.0, min(1.0, temp))

    # MiniMax-specific: don't allow exactly 0.0
    if is_minimax_api() and temp <= 0.0:
        return 0.001

    return temp
