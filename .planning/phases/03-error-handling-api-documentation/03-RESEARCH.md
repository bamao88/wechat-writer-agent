# 阶段 3: 错误处理与 API 差异文档化 - 研究报告

**研究日期:** 2026-01-28
**领域:** Agent SDK 子进程错误处理与调试
**置信度:** MEDIUM-HIGH

## 摘要

本研究针对 Claude Agent SDK 与官方 Anthropic API 集成中的工具调用失败问题(错误代码 1),系统性调查了 Python 子进程错误处理最佳实践、Agent SDK 技能发现机制、以及生产级 LLM Agent 错误处理模式。

核心发现:已知正常状态(传统模式正常、NotebookLM 技能独立运行正常)表明问题不在工具本身,而是在 Agent SDK 调用技能时的环境传递、配置注入或 API 兼容性层面。Python subprocess.run() 提供了完善的错误捕获机制(capture_output=True, text=True),结合 CalledProcessError 可以捕获退出码、stderr 和 stdout。Agent SDK 技能发现机制要求显式配置 setting_sources=['user', 'project'] 和 allowed_tools=['Skill'],Linux 系统存在路径硬编码问题(Issue #268)。

**核心建议:** 采用**调试优先**策略,通过增强型日志、环境变量验证、以及系统性诊断步骤定位根本原因。修复根本问题后,仅在必要时添加优雅降级机制。使用结构化日志记录工具调用生命周期(注册、调用、执行、响应、错误),为生产部署建立可观测性基础。

## 标准技术栈

Python 子进程错误处理与 Agent SDK 集成的成熟工具:

### 核心库
| 库名 | 版本 | 用途 | 为何标准 |
|---------|---------|---------|--------------|
| subprocess | Python 3.13+ 内置 | 子进程管理 | Python 官方推荐的子进程接口,提供完整的错误处理和流控制 |
| claude-agent-sdk | 已安装版本 | Agent 框架 | Anthropic 官方 Agent SDK,支持技能发现和工具调用 |
| structlog | >=24.4.0 | 结构化日志 | 生产级结构化日志库,支持上下文变量和 JSON 输出 |

### 支持库
| 库名 | 版本 | 用途 | 使用场景 |
|---------|---------|---------|-------------|
| loguru | >=0.7.2 | 简化日志 | 需要更简单的日志接口时(相比 structlog) |
| python-json-logger | >=2.0.7 | JSON 日志格式化 | 与标准 logging 模块集成 JSON 输出 |
| psutil | >=6.1.1 | 进程监控 | 需要监控子进程资源使用时 |

### 替代方案对比
| 替代 | 可选方案 | 权衡 |
|------------|-----------|----------|
| subprocess.run() | asyncio.create_subprocess_exec | asyncio 版本适合纯异步环境,但 SDK 支持同步工具 |
| structlog | 标准 logging + json-logger | structlog 性能更好且专为结构化设计,logging 更通用 |
| 手动环境传递 | dotenv + explicit env dict | dotenv 简化配置管理,显式传递更清晰可控 |

**安装命令:**
```bash
pip install structlog>=24.4.0
pip install loguru>=0.7.2  # 如果选择 loguru
pip install psutil>=6.1.1  # 如果需要进程监控
```

## 架构模式

### 推荐项目结构
```
src/
├── modules/
│   ├── agent_sdk.py           # 现有 Claude Agent SDK 运行器
│   └── subprocess_utils.py    # 新增: 子进程错误处理工具
├── hooks/
│   ├── logging_hooks.py       # 现有 hooks
│   └── diagnostic_hooks.py    # 新增: 诊断专用 hooks
├── utils/
│   ├── env_validator.py       # 新增: 环境变量验证
│   └── skill_discovery.py     # 新增: 技能发现诊断
└── config/
    └── logging_config.py      # 新增: 结构化日志配置
```

### 模式 1: 增强型子进程错误捕获
**用途:** 捕获详细的子进程失败信息(退出码、stderr、stdout、环境)
**使用场景:** NotebookLM 技能调用、任何外部工具集成
**示例:**
```python
# 来源: https://docs.python.org/3/library/subprocess.html
import subprocess
import logging

def run_skill_subprocess(script_path: str, args: list, timeout: int = 30) -> dict:
    """
    执行技能子进程,捕获完整错误信息

    Returns:
        dict with keys: success, stdout, stderr, returncode, error_message
    """
    try:
        result = subprocess.run(
            ["python", script_path] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True  # 非零退出码时抛出异常
        )

        return {
            "success": True,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "error_message": None
        }

    except subprocess.CalledProcessError as e:
        # 进程以非零退出码退出
        error_msg = f"进程退出码 {e.returncode}"
        logging.error(
            f"子进程失败: {error_msg}",
            extra={
                "returncode": e.returncode,
                "stderr": e.stderr,
                "stdout": e.stdout,
                "cmd": e.cmd
            }
        )
        return {
            "success": False,
            "stdout": e.stdout,
            "stderr": e.stderr,
            "returncode": e.returncode,
            "error_message": error_msg
        }

    except subprocess.TimeoutExpired as e:
        # 超时
        error_msg = f"进程超时(>{timeout}秒)"
        logging.error(
            f"子进程超时: {error_msg}",
            extra={
                "timeout": timeout,
                "stderr": e.stderr if hasattr(e, 'stderr') else None,
                "stdout": e.stdout if hasattr(e, 'stdout') else None
            }
        )
        return {
            "success": False,
            "stdout": None,
            "stderr": None,
            "returncode": -1,
            "error_message": error_msg
        }

    except FileNotFoundError as e:
        # 命令不存在
        error_msg = f"命令未找到: {e.filename}"
        logging.error(f"子进程启动失败: {error_msg}")
        return {
            "success": False,
            "stdout": None,
            "stderr": None,
            "returncode": -1,
            "error_message": error_msg
        }
```

### 模式 2: Agent SDK 技能发现诊断
**用途:** 验证技能是否被 Agent SDK 正确发现和配置
**使用场景:** 调试"退出码 1"时的首要步骤
**示例:**
```python
# 来源: https://platform.claude.com/docs/en/agent-sdk/skills
import os
from pathlib import Path
from claude_agent_sdk import query, ClaudeAgentOptions

def diagnose_skill_discovery(notebook_id: str) -> dict:
    """
    诊断技能发现状态

    Returns:
        dict with keys: skills_dir_exists, skill_found, config_valid, errors
    """
    diagnostics = {
        "skills_dir_exists": False,
        "skill_found": False,
        "config_valid": False,
        "errors": []
    }

    # 1. 检查技能目录是否存在
    user_skills_dir = Path.home() / ".claude" / "skills" / "notebooklm"
    project_skills_dir = Path.cwd() / ".claude" / "skills" / "notebooklm"

    if user_skills_dir.exists():
        diagnostics["skills_dir_exists"] = True
        diagnostics["skills_dir_path"] = str(user_skills_dir)
    elif project_skills_dir.exists():
        diagnostics["skills_dir_exists"] = True
        diagnostics["skills_dir_path"] = str(project_skills_dir)
    else:
        diagnostics["errors"].append(
            f"技能目录不存在: {user_skills_dir} 或 {project_skills_dir}"
        )

    # 2. 检查 SKILL.md 是否存在
    if diagnostics["skills_dir_exists"]:
        skill_md = Path(diagnostics["skills_dir_path"]) / "SKILL.md"
        if skill_md.exists():
            diagnostics["skill_found"] = True
            diagnostics["skill_md_size"] = skill_md.stat().st_size
        else:
            diagnostics["errors"].append(f"SKILL.md 不存在: {skill_md}")

    # 3. 检查必要的配置
    if notebook_id:
        diagnostics["config_valid"] = True
        diagnostics["notebook_id"] = notebook_id[:20] + "..."
    else:
        diagnostics["errors"].append("notebook_id 未设置")

    # 4. 测试 SDK 配置是否会加载技能
    try:
        options = ClaudeAgentOptions(
            setting_sources=["user", "project"],
            allowed_tools=["Skill"]
        )
        diagnostics["sdk_config_valid"] = True
    except Exception as e:
        diagnostics["sdk_config_valid"] = False
        diagnostics["errors"].append(f"SDK 配置失败: {str(e)}")

    return diagnostics
```

### 模式 3: 环境变量传递验证
**用途:** 确保子进程继承正确的环境变量(尤其是 NOTEBOOK_ID、NOTEBOOK_URL)
**使用场景:** 技能需要配置参数时
**示例:**
```python
# 来源: Python subprocess 最佳实践
import os
import subprocess

def run_with_validated_env(
    script_path: str,
    args: list,
    required_env_vars: list[str]
) -> dict:
    """
    运行子进程前验证必需的环境变量
    """
    # 验证环境变量
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        return {
            "success": False,
            "error_message": f"缺少必需环境变量: {', '.join(missing_vars)}"
        }

    # 显式传递环境变量(可选:也可以继承当前进程的 env)
    env = os.environ.copy()

    # 打印调试信息
    print(f"[ENV DEBUG] NOTEBOOK_ID: {env.get('NOTEBOOK_ID', 'NOT SET')[:20]}...")
    print(f"[ENV DEBUG] NOTEBOOK_URL: {env.get('NOTEBOOK_URL', 'NOT SET')}")

    result = subprocess.run(
        ["python", script_path] + args,
        capture_output=True,
        text=True,
        env=env,  # 显式传递
        timeout=30
    )

    return {
        "success": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode
    }
```

### 模式 4: 超时处理与进程终止
**用途:** NotebookLM 查询超时时正确终止子进程
**使用场景:** ERR-02 需求 - 超时检测与处理
**示例:**
```python
# 来源: https://docs.python.org/3/library/subprocess.html
import subprocess
import signal

def run_with_timeout_handling(
    script_path: str,
    args: list,
    timeout: int = 10
) -> dict:
    """
    带超时处理的子进程执行(先 terminate,再 kill)
    """
    try:
        result = subprocess.run(
            ["python", script_path] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True
        )

        return {
            "success": True,
            "stdout": result.stdout,
            "timeout_occurred": False
        }

    except subprocess.TimeoutExpired as e:
        # 注意: subprocess.run() 超时时已自动 kill 进程
        # 如果使用 Popen,需要手动处理:
        # proc.terminate()  # 发送 SIGTERM
        # try:
        #     proc.wait(timeout=5)
        # except subprocess.TimeoutExpired:
        #     proc.kill()  # 强制 SIGKILL

        return {
            "success": False,
            "stdout": e.stdout if hasattr(e, 'stdout') else None,
            "stderr": e.stderr if hasattr(e, 'stderr') else None,
            "timeout_occurred": True,
            "error_message": f"查询超时(>{timeout}秒),进程已终止"
        }
```

### 模式 5: 结构化日志记录工具调用生命周期
**用途:** 满足 ERR-04 需求 - 完整的工具调用生命周期记录
**使用场景:** 生产环境可观测性
**示例:**
```python
# 来源: https://www.dash0.com/guides/logging-in-python + structlog 文档
import structlog
import time
from typing import Any, Dict

# 配置 structlog(仅一次,在应用启动时)
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

log = structlog.get_logger()

class ToolCallLogger:
    """工具调用生命周期日志记录器"""

    def __init__(self, tool_name: str, tool_input: Dict[str, Any]):
        self.tool_name = tool_name
        self.tool_input = tool_input
        self.start_time = time.time()
        self.tool_use_id = None

    def log_registration(self, tool_use_id: str):
        """阶段 1: 工具注册"""
        self.tool_use_id = tool_use_id
        log.info(
            "tool_registered",
            tool_name=self.tool_name,
            tool_use_id=tool_use_id,
            phase="registration"
        )

    def log_call_start(self):
        """阶段 2: 调用开始"""
        log.info(
            "tool_call_started",
            tool_name=self.tool_name,
            tool_use_id=self.tool_use_id,
            input=self.tool_input,
            phase="call_start"
        )

    def log_execution(self, subprocess_result: Dict[str, Any]):
        """阶段 3: 工具执行(子进程结果)"""
        duration_ms = (time.time() - self.start_time) * 1000

        log.info(
            "tool_executed",
            tool_name=self.tool_name,
            tool_use_id=self.tool_use_id,
            success=subprocess_result["success"],
            returncode=subprocess_result.get("returncode"),
            duration_ms=duration_ms,
            phase="execution"
        )

    def log_response(self, result: Any, success: bool):
        """阶段 4: 响应返回"""
        duration_ms = (time.time() - self.start_time) * 1000

        log.info(
            "tool_response_returned",
            tool_name=self.tool_name,
            tool_use_id=self.tool_use_id,
            success=success,
            result_length=len(str(result)),
            total_duration_ms=duration_ms,
            phase="response"
        )

    def log_error(self, error: Exception):
        """阶段 5: 错误捕获"""
        duration_ms = (time.time() - self.start_time) * 1000

        log.error(
            "tool_call_error",
            tool_name=self.tool_name,
            tool_use_id=self.tool_use_id,
            error_type=type(error).__name__,
            error_message=str(error),
            duration_ms=duration_ms,
            phase="error"
        )

# 使用示例
def execute_tool_with_logging(tool_name: str, tool_input: dict):
    logger = ToolCallLogger(tool_name, tool_input)

    # 注册
    logger.log_registration("tool_123")

    # 调用开始
    logger.log_call_start()

    try:
        # 执行子进程
        result = run_skill_subprocess("script.py", ["--arg", "value"])
        logger.log_execution(result)

        # 返回响应
        logger.log_response(result["stdout"], result["success"])

        return result

    except Exception as e:
        logger.log_error(e)
        raise
```

### 反模式(避免使用)
- **盲目捕获所有异常**: 不要用 `except Exception: pass` 隐藏错误,应该记录并重新抛出或优雅降级
- **不记录 stderr**: 不捕获 stderr 就无法诊断子进程内部错误
- **超时后不清理进程**: 使用 Popen 时必须在超时后手动 terminate/kill,否则僵尸进程会泄漏资源
- **硬编码路径**: 不要假设技能在固定路径(macOS vs Linux 差异,Issue #268)
- **忽略环境变量传递**: 子进程默认继承环境,但 SDK 环境可能受限,需要显式验证

## 不要手动实现

看似简单但已有成熟解决方案的问题:

| 问题 | 不要自己构建 | 应该使用 | 原因 |
|---------|-------------|-------------|-----|
| 结构化日志 | 手动拼接 JSON 字符串 | structlog 或 loguru | 自动类型转换、上下文变量、性能优化、与日志聚合工具集成 |
| 进程超时管理 | 手动 threading.Timer + proc.kill() | subprocess.run(timeout=N) | 自动清理、跨平台兼容、边缘情况处理(进程组、子进程) |
| 错误重试逻辑 | 手写 for 循环 + sleep | tenacity 库的 @retry 装饰器 | 指数退避、抖动、条件重试、统计记录 |
| 环境变量管理 | 手动 os.environ 修改 | python-dotenv + 显式 env dict | .env 文件支持、类型验证、不污染全局环境 |
| 子进程输出解析 | 手写正则表达式 | 让工具输出 JSON,用 json.loads() | 健壮性、可扩展性、避免编码问题 |

**关键洞察:** Python 标准库的 subprocess 模块已经非常成熟,大多数"改进"实际上会引入新问题。专注于正确使用标准接口,而不是重新发明轮子。

## 常见陷阱

### 陷阱 1: check=True 但不捕获异常
**问题描述:** 使用 `subprocess.run(check=True)` 但没有 try-except,导致异常传播到顶层
**原因:** check=True 会在非零退出码时抛出 CalledProcessError,如果不捕获,整个 Agent 崩溃
**避免方法:** 始终用 try-except 包裹 check=True 调用,或者使用 check=False 并手动检查 returncode
**预警信号:** Agent 中途崩溃、日志显示未捕获的 CalledProcessError、用户看到栈追踪

### 陷阱 2: 技能发现配置缺失
**问题描述:** Agent SDK 未加载技能,工具调用返回"工具未找到"错误
**原因:**
- 未设置 `setting_sources=["user", "project"]` (最常见,来源: [Agent Skills in the SDK](https://platform.claude.com/docs/en/agent-sdk/skills))
- 未在 `allowed_tools` 中添加 "Skill"
- Linux 系统路径硬编码问题 ([Issue #268](https://github.com/anthropics/claude-agent-sdk-python/issues/268))
**避免方法:**
1. 始终显式设置 setting_sources
2. 使用诊断函数验证技能目录和 SKILL.md 存在
3. 打印 Agent 发现的工具列表以确认
**预警信号:** 日志显示"工具调用为 0"、询问 Agent 可用工具时回答为空、退出码 127(命令未找到)

### 陷阱 3: 环境变量未传递给子进程
**问题描述:** NotebookLM 技能启动时缺少 NOTEBOOK_ID 或 NOTEBOOK_URL 配置
**原因:**
- 子进程未继承父进程环境(使用了空的 env dict)
- 环境变量在 SDK 启动后设置(时机问题)
- Electron/打包应用环境受限 ([Issue #1093](https://github.com/AndyMik90/Auto-Claude/issues/1093))
**避免方法:**
1. 显式传递 `env=os.environ.copy()` 给 subprocess
2. 在启动前验证环境变量是否设置
3. 记录传递给子进程的环境变量(调试模式)
**预警信号:** 技能脚本内部报告配置缺失、退出码 1 伴随"配置错误"stderr、相同命令在终端运行正常但 SDK 调用失败

### 陷阱 4: 超时值设置不当
**问题描述:** NotebookLM 查询需要 15-20 秒,但超时设置为 10 秒,导致频繁超时
**原因:** 对 I/O 密集型操作(浏览器自动化、API 调用)的实际耗时估计不足
**避免方法:**
1. 基于实际测量设置超时(不是猜测)
2. 提供可配置的超时参数(环境变量或配置文件)
3. 区分快速操作(5s)和慢速操作(30s+)
**预警信号:** 频繁超时错误、成功率低但手动测试正常、日志显示接近超时限制时失败

### 陷阱 5: stderr 内容未记录或截断
**问题描述:** 子进程失败时只记录"退出码 1",不记录 stderr,无法定位问题
**原因:**
- 未使用 capture_output=True
- stderr 很长时被日志系统截断
- stderr 使用非 UTF-8 编码导致解码失败
**避免方法:**
1. 始终使用 `capture_output=True, text=True`
2. 完整记录 stderr(至少前 2000 字符)到日志
3. 使用 `errors='replace'` 处理编码问题
**预警信号:** 日志显示"退出码 1"但无其他信息、开发者需要手动复现才能看到错误、stderr 字段为空或 None

### 陷阱 6: 忘记优雅降级
**问题描述:** 工具调用失败时 Agent 崩溃或返回空响应,无法完成任务
**原因:** 没有 fallback 策略,把工具当作必需而非可选
**避免方法:**
1. 工具失败时返回友好错误消息而非抛出异常
2. Agent 提示词中说明"工具不可用时基于训练知识回答"
3. 关键功能(如检索)失败时提示用户而非静默失败
**预警信号:** 工具失败导致 Agent 停止响应、用户收到技术性错误消息、无法在工具不可用时使用 Agent

## 代码示例

基于官方文档和最佳实践的验证模式:

### 完整的子进程错误处理包装器
```python
# 来源: https://docs.python.org/3/library/subprocess.html + 生产实践
import subprocess
import logging
from typing import Dict, Any, Optional

class SubprocessExecutor:
    """生产级子进程执行器"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    def run(
        self,
        cmd: list[str],
        timeout: int = 30,
        env: Optional[Dict[str, str]] = None,
        log_output: bool = True
    ) -> Dict[str, Any]:
        """
        执行子进程并返回详细结果

        Args:
            cmd: 命令及参数列表
            timeout: 超时秒数
            env: 环境变量字典(None 表示继承当前进程)
            log_output: 是否记录 stdout/stderr 到日志

        Returns:
            包含 success, stdout, stderr, returncode, error_message 的字典
        """
        self.logger.info(f"执行子进程: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                errors='replace'  # 处理编码问题
            )

            success = result.returncode == 0

            # 记录输出
            if log_output:
                if result.stdout:
                    self.logger.debug(f"stdout: {result.stdout[:500]}")
                if result.stderr:
                    level = logging.WARNING if success else logging.ERROR
                    self.logger.log(level, f"stderr: {result.stderr[:500]}")

            # 构建返回结果
            return {
                "success": success,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "error_message": None if success else f"退出码 {result.returncode}",
                "timeout_occurred": False
            }

        except subprocess.TimeoutExpired as e:
            self.logger.error(f"子进程超时: {timeout}秒")
            return {
                "success": False,
                "stdout": e.stdout.decode('utf-8', errors='replace') if e.stdout else None,
                "stderr": e.stderr.decode('utf-8', errors='replace') if e.stderr else None,
                "returncode": -1,
                "error_message": f"超时(>{timeout}秒)",
                "timeout_occurred": True
            }

        except FileNotFoundError as e:
            self.logger.error(f"命令未找到: {cmd[0]}")
            return {
                "success": False,
                "stdout": None,
                "stderr": None,
                "returncode": -1,
                "error_message": f"命令未找到: {cmd[0]}",
                "timeout_occurred": False
            }

        except Exception as e:
            self.logger.error(f"子进程异常: {type(e).__name__}: {e}")
            return {
                "success": False,
                "stdout": None,
                "stderr": None,
                "returncode": -1,
                "error_message": f"异常: {type(e).__name__}: {e}",
                "timeout_occurred": False
            }

# 使用示例
executor = SubprocessExecutor()
result = executor.run(
    ["python", "~/.claude/skills/notebooklm/scripts/run.py", "ask_question.py",
     "--question", "测试问题"],
    timeout=30
)

if result["success"]:
    print(f"成功: {result['stdout']}")
else:
    print(f"失败: {result['error_message']}")
    print(f"stderr: {result['stderr']}")
```

### Agent SDK 技能调用诊断流程
```python
# 来源: https://platform.claude.com/docs/en/agent-sdk/skills + 诊断最佳实践
import os
from pathlib import Path
from claude_agent_sdk import ClaudeAgentOptions

def diagnose_and_fix_skill_issues(notebook_id: str) -> Dict[str, Any]:
    """
    系统性诊断技能调用问题的完整流程
    """
    diagnostics = {
        "checks": [],
        "errors": [],
        "fixes_applied": [],
        "ready_for_agent": False
    }

    # 检查 1: 技能目录存在性
    user_skills_dir = Path.home() / ".claude" / "skills" / "notebooklm"
    if user_skills_dir.exists():
        diagnostics["checks"].append("✓ 用户技能目录存在")
        skill_md = user_skills_dir / "SKILL.md"
        if skill_md.exists():
            diagnostics["checks"].append("✓ SKILL.md 文件存在")
        else:
            diagnostics["errors"].append("✗ SKILL.md 文件缺失")
    else:
        diagnostics["errors"].append("✗ 用户技能目录不存在")

    # 检查 2: 环境变量配置
    if notebook_id:
        os.environ['NOTEBOOK_ID'] = notebook_id
        diagnostics["checks"].append(f"✓ NOTEBOOK_ID 已设置: {notebook_id[:20]}...")
    else:
        diagnostics["errors"].append("✗ NOTEBOOK_ID 未提供")

    if os.getenv('NOTEBOOK_URL'):
        diagnostics["checks"].append("✓ NOTEBOOK_URL 已设置")
    else:
        diagnostics["errors"].append("⚠ NOTEBOOK_URL 未设置(可选)")

    # 检查 3: SDK 配置正确性
    try:
        options = ClaudeAgentOptions(
            setting_sources=["user", "project"],  # 必需!
            allowed_tools=["Skill"]               # 必需!
        )
        diagnostics["checks"].append("✓ SDK 配置正确(setting_sources 和 allowed_tools)")
    except Exception as e:
        diagnostics["errors"].append(f"✗ SDK 配置失败: {e}")

    # 检查 4: Python 路径可访问性(PATH 问题检测)
    python_path = subprocess.run(
        ["which", "python"],
        capture_output=True,
        text=True
    ).stdout.strip()

    if python_path:
        diagnostics["checks"].append(f"✓ Python 可执行文件: {python_path}")
    else:
        diagnostics["errors"].append("✗ Python 未在 PATH 中")

    # 检查 5: 技能脚本可执行性(模拟调用)
    if user_skills_dir.exists():
        run_script = user_skills_dir / "scripts" / "run.py"
        if run_script.exists():
            diagnostics["checks"].append("✓ run.py 脚本存在")
            # 尝试执行帮助命令
            test_result = subprocess.run(
                ["python", str(run_script), "auth_manager.py", "status"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if test_result.returncode == 0:
                diagnostics["checks"].append("✓ 技能脚本可执行(测试调用成功)")
            else:
                diagnostics["errors"].append(
                    f"✗ 技能脚本执行失败: {test_result.stderr[:200]}"
                )
        else:
            diagnostics["errors"].append("✗ run.py 脚本不存在")

    # 总结
    if not diagnostics["errors"]:
        diagnostics["ready_for_agent"] = True
        diagnostics["summary"] = "所有检查通过,可以启动 Agent"
    else:
        diagnostics["ready_for_agent"] = False
        diagnostics["summary"] = f"发现 {len(diagnostics['errors'])} 个问题需要修复"

    return diagnostics

# 使用示例
result = diagnose_and_fix_skill_issues(notebook_id="your-notebook-id")
print(f"诊断结果: {result['summary']}")
for check in result['checks']:
    print(check)
for error in result['errors']:
    print(error)
```

### 优雅降级模式
```python
# 来源: https://markaicode.com/implement-graceful-degradation-llm-frameworks/
from typing import Optional, Callable

class GracefulToolExecutor:
    """带优雅降级的工具执行器"""

    def __init__(
        self,
        tool_fn: Callable,
        fallback_fn: Optional[Callable] = None,
        max_retries: int = 2
    ):
        self.tool_fn = tool_fn
        self.fallback_fn = fallback_fn
        self.max_retries = max_retries

    async def execute(self, *args, **kwargs) -> Dict[str, Any]:
        """
        执行工具,失败时尝试重试,最终回退到 fallback

        Returns:
            {
                "success": bool,
                "result": Any,
                "used_fallback": bool,
                "error": Optional[str]
            }
        """
        last_error = None

        # 尝试执行主工具(带重试)
        for attempt in range(self.max_retries):
            try:
                result = await self.tool_fn(*args, **kwargs)
                return {
                    "success": True,
                    "result": result,
                    "used_fallback": False,
                    "error": None
                }
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))  # 指数退避

        # 主工具失败,尝试 fallback
        if self.fallback_fn:
            try:
                fallback_result = await self.fallback_fn(*args, **kwargs)
                return {
                    "success": True,
                    "result": fallback_result,
                    "used_fallback": True,
                    "error": f"主工具失败(使用了备选方案): {last_error}"
                }
            except Exception as fb_error:
                return {
                    "success": False,
                    "result": None,
                    "used_fallback": False,
                    "error": f"主工具和备选方案均失败: {last_error}, {fb_error}"
                }

        # 无 fallback,返回失败
        return {
            "success": False,
            "result": None,
            "used_fallback": False,
            "error": f"工具执行失败(已重试 {self.max_retries} 次): {last_error}"
        }

# 使用示例:定义主工具和 fallback
async def query_notebooklm_tool(question: str) -> str:
    """主工具:查询 NotebookLM"""
    result = subprocess.run(
        ["python", "notebooklm/scripts/run.py", "ask_question.py", "--question", question],
        capture_output=True,
        text=True,
        timeout=30,
        check=True
    )
    return result.stdout

async def fallback_search(question: str) -> str:
    """备选方案:使用提示词生成(无工具)"""
    return f"[NotebookLM 不可用] 基于训练知识的回答:关于'{question}'..."

# 创建带降级的执行器
executor = GracefulToolExecutor(
    tool_fn=query_notebooklm_tool,
    fallback_fn=fallback_search,
    max_retries=2
)

# 执行
result = await executor.execute(question="测试问题")
if result["success"]:
    print(result["result"])
    if result["used_fallback"]:
        print("(使用了备选方案)")
```

## 技术现状

| 旧方法 | 当前方法 | 变更时间 | 影响 |
|--------------|------------------|--------------|--------|
| subprocess.call() | subprocess.run() | Python 3.5+ | run() 提供更好的错误处理和返回值,是官方推荐 |
| 手动拼接日志消息 | 结构化日志(structlog, loguru) | 2024-2025 | 机器可读日志,与可观测性平台集成,更好的查询和分析 |
| 隐式环境变量继承 | 显式 env 参数传递 | 持续演进 | 解决打包应用和容器化环境中的变量传递问题 |
| 单次工具调用 | 重试 + 优雅降级 | LLM Agent 最佳实践 2025+ | 提高生产环境可靠性,避免单点故障 |
| Claude Code SDK | Claude Agent SDK | 2025年9月 | SDK 重命名,改进多轮对话上下文管理 |

**已弃用/过时:**
- **subprocess.call/check_call/check_output**: 使用 subprocess.run() 替代(Python 3.5+)
- **logging.basicConfig() 用于生产日志**: 使用 structlog 或 loguru 实现结构化日志
- **硬编码超时值**: 使用环境变量或配置文件实现可调整超时
- **忽略 stderr**: 现代实践要求完整捕获 stdout 和 stderr 用于调试

## 待解决问题

无法完全解决的事项:

1. **NotebookLM 技能"退出码 1"的根本原因**
   - 已知信息: 传统模式正常、技能独立运行正常、Agent SDK 调用失败
   - 不确定: 是环境变量传递问题、技能发现问题、还是 API 兼容性问题
   - 建议: 实施系统性诊断流程(模式 2),逐项排查并记录发现,修复根本原因而非添加错误处理

2. **Linux 系统技能路径硬编码问题影响范围**
   - 已知信息: Issue #268 报告 Linux 系统技能未发现,SDK 使用硬编码 macOS 路径
   - 不确定: 此问题是否已在最新 SDK 版本修复、是否影响当前项目(运行环境是 macOS)
   - 建议: 检查当前 SDK 版本,如果是 Linux 环境需要验证技能路径解析逻辑

3. **MiniMax API 与官方 Anthropic API 的工具调用行为差异**
   - 已知信息: 两者均支持工具调用,但内部实现可能不同(MiniMax 使用 XML,官方使用 JSON)
   - 不确定: 差异是否导致 Agent SDK 行为不一致、是否需要特殊配置
   - 建议: 文档化测试结果(API-04 需求),记录差异和配置建议

4. **工具调用超时的合理阈值**
   - 已知信息: NotebookLM 浏览器自动化耗时较长(15-20秒)
   - 不确定: 在不同网络条件、不同查询复杂度下的实际耗时分布
   - 建议: 收集实际运行数据,基于 P95 延迟设置超时(不是猜测),提供可配置的超时参数

5. **优雅降级策略的用户体验影响**
   - 已知信息: 工具失败时可以回退到基于提示词的生成
   - 不确定: 用户是否需要知道工具失败了、质量差异是否可接受、是否应该提示用户重试
   - 建议: A/B 测试不同降级策略的用户满意度,平衡透明度和用户体验

## 信息来源

### 主要来源(高置信度)
- [Python subprocess 官方文档](https://docs.python.org/3/library/subprocess.html) - subprocess.run()、CalledProcessError、超时处理
- [Agent Skills in the SDK - Claude API 文档](https://platform.claude.com/docs/en/agent-sdk/skills) - 技能发现、setting_sources 配置、allowed_tools 设置
- [Python Subprocess Run Stdout Stderr - CS Atlas](https://csatlas.com/python-subprocess-run-stdout-stderr/) - 错误捕获最佳实践
- [Logging in Python - Dash0 指南](https://www.dash0.com/guides/logging-in-python) - 结构化日志配置

### 次要来源(中等置信度)
- [Graceful Degradation in LLM Frameworks - Markaicode](https://markaicode.com/implement-graceful-degradation-llm-frameworks/) - 优雅降级模式
- [Python Logging Best Practices - SigNoz](https://signoz.io/guides/python-logging-best-practices/) - 结构化日志、上下文变量
- [Agent Error Handling & Recovery - APXml](https://apxml.com/courses/langchain-production-llm/chapter-2-sophisticated-agents-tools/agent-error-handling) - LLM Agent 错误处理模式
- [Subprocess Timeout Python - Alexandra Zaharia](https://alexandra-zaharia.github.io/posts/kill-subprocess-and-its-children-on-timeout-python/) - 超时和进程终止

### 第三来源(低置信度 - 需要验证)
- [Issue #268 - Skills not working on Linux](https://github.com/anthropics/claude-agent-sdk-python/issues/268) - 路径硬编码问题(需确认当前版本状态)
- [Issue #1093 - Command failed exit code 127](https://github.com/AndyMik90/Auto-Claude/issues/1093) - PATH 问题(Electron 应用特定)
- [Issue #214 - CLI path from ClaudeAgentOptions](https://github.com/anthropics/claude-agent-sdk-python/issues/214) - 自定义 CLI 路径支持

## 元数据

**置信度细分:**
- 子进程错误处理: HIGH - Python 官方文档,成熟稳定的 API
- Agent SDK 技能发现: MEDIUM-HIGH - 官方文档 + 已知 Issue,但当前项目具体环境未验证
- 优雅降级策略: MEDIUM - 基于通用最佳实践,但具体实现需结合项目需求

**研究日期:** 2026-01-28
**有效期至:** 2026-02-28(30 天,稳定技术栈,除非 Agent SDK 发布重大更新)

**关键假设:**
1. 当前运行环境是 macOS(Linux 路径问题不影响)
2. Claude Agent SDK 版本支持 setting_sources 和 allowed_tools 配置
3. NotebookLM 技能的 SKILL.md 格式正确且位于标准路径
4. Python 3.13+ 环境,subprocess 模块 API 稳定

**风险评估:**
- **低风险:** 子进程错误捕获实现(标准库,文档完善)
- **低风险:** 结构化日志配置(成熟库,清晰文档)
- **中风险:** 技能发现问题诊断(需要实际测试验证)
- **中风险:** 根本原因定位(问题可能在多个层面)
- **低风险:** 优雅降级实现(设计模式明确)
