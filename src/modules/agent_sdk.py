"""Claude Agent SDK 封装模块"""
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class AgentRunMetrics:
    """Agent 运行指标数据类"""

    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    errors: List[str] = field(default_factory=list)

    @property
    def runtime_seconds(self) -> float:
        """计算运行时长（秒）"""
        if self.end_time is not None:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    @property
    def tool_call_count(self) -> int:
        """返回工具调用次数"""
        return len(self.tool_calls)
