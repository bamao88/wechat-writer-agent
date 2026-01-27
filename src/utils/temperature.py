"""MiniMax temperature 参数验证工具"""


def validate_temperature(temp: float) -> float:
    """
    验证并调整 temperature 参数以符合 MiniMax 要求

    MiniMax 要求 temperature 在 (0.0, 1.0] 范围内（开区间）

    Args:
        temp: 原始 temperature 值

    Returns:
        调整后的 temperature 值

    Examples:
        >>> validate_temperature(0.0)
        0.001
        >>> validate_temperature(0.7)
        0.7
        >>> validate_temperature(1.5)
        1.0
    """
    if temp <= 0.0:
        # MiniMax 不允许 0.0，使用最小值
        return 0.001
    elif temp > 1.0:
        # 限制到最大值
        return 1.0
    return temp
