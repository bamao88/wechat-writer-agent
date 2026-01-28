# Anthropic API 差异文档

## 概述

本项目同时支持官方 Anthropic API 和 MiniMax API 兼容层。本文档记录两者之间的关键差异,帮助开发者理解配置选择。

## 推荐配置

**官方 Anthropic API (推荐)**

官方 Anthropic API 是本项目的推荐选择,提供完整的功能支持和最佳兼容性:
- 无需设置 `ANTHROPIC_BASE_URL` (使用默认值 `api.anthropic.com`)
- 标准认证方式 (仅需 `ANTHROPIC_API_KEY`)
- 完整的 SDK 功能支持
- 稳定的 API 响应时间
- 推荐模型: `claude-sonnet-4-20250514`

## API 差异对照表

| 特性 | 官方 Anthropic API | MiniMax API |
|------|-------------------|-------------|
| **基础 URL** | `api.anthropic.com` (默认) | `api.minimaxi.com` (需配置) |
| **认证方式** | 标准 API Key | 自定义 Authorization Header |
| **推荐超时** | 120 秒 | 3000 秒 (推理模型) |
| **Temperature 范围** | [0.0, 1.0] (支持 0.0) | (0.0, 1.0] (最小 0.001) |
| **工具调用协议** | JSON (原生支持) | XML (内部转换) |
| **mcp_servers** | ✅ 支持 | ❌ 不支持 |
| **context_management** | ✅ 支持 | ❌ 不支持 |
| **streaming_options** | ✅ 完整支持 | ⚠️ 有限支持 |
| **模型可用性** | 官方 Claude 模型 | MiniMax 兼容模型 |

## 不支持的参数

### MiniMax API 不支持的参数

#### 1. mcp_servers

**官方 API 支持:**
- 通过 Model Context Protocol (MCP) 连接外部服务
- 动态加载工具和资源
- 标准化的工具集成方式

**MiniMax API 限制:**
- 不支持 `mcp_servers` 参数
- 无法使用 MCP 协议连接外部服务

**替代方案:**
- **推荐:** 使用 Skills 机制 (`~/.claude/skills/`)
  ```python
  # 在 ClaudeAgentOptions 中配置
  options = ClaudeAgentOptions(
      setting_sources=["user"],  # 加载 ~/.claude/skills/
      allowed_tools=["Skill"]    # 启用 Skills 发现
  )
  ```
- **备选:** 使用直接子进程调用 (参考 `src/tools/subprocess_runner.py`)

#### 2. context_management

**官方 API 支持:**
- 自动管理上下文窗口长度
- 智能截断历史消息
- 优化 token 使用

**MiniMax API 限制:**
- 不支持 `context_management` 参数
- 需手动管理上下文长度

**替代方案:**
- 手动管理 `max_tokens` 参数
- 自行截断消息历史以保持在上下文窗口内
- 实现自定义的消息历史管理策略

#### 3. streaming_options

**官方 API 支持:**
- 完整的流式输出配置
- 支持 `thinking` 流式输出
- 灵活的流式控制选项

**MiniMax API 限制:**
- 有限的流式配置支持
- 某些高级流式选项可能不可用

**替代方案:**
- 使用默认流式配置
- 避免使用高级流式选项
- 依赖基本的流式输出功能

## 代码中的条件处理

本项目通过 `ANTHROPIC_BASE_URL` 环境变量自动检测 API 类型:

```python
# 在 src/modules/agent_sdk.py 和 src/utils/temperature.py 中
base_url = os.getenv("ANTHROPIC_BASE_URL", "")

if "minimaxi.com" in base_url:
    # MiniMax 模式
    # - 使用 3000 秒超时 (推理模型)
    # - Temperature 最小值为 0.001
    # - 自定义认证头
else:
    # 官方 API 模式
    # - 使用 120 秒超时
    # - Temperature 支持 0.0
    # - 标准认证方式
```

### 关键代码位置

- **API 检测:** `src/modules/agent_sdk.py` (L183-188, `_get_api_timeout_ms` 方法)
- **超时配置:** `src/modules/agent_sdk.py` (L176-188)
- **Temperature 验证:** `src/utils/temperature.py` (L8-41)
  - `is_minimax_api()` - API 类型检测
  - `validate_temperature()` - 条件温度验证

## 环境配置示例

### 官方 Anthropic API (推荐)

```bash
# .env 文件
ANTHROPIC_API_KEY=sk-ant-...
MODEL_NAME=claude-sonnet-4-20250514
TEMPERATURE=0.0
# ANTHROPIC_BASE_URL 不设置,使用默认值
```

### MiniMax API (备用)

```bash
# .env 文件
ANTHROPIC_API_KEY=your-minimax-api-key
ANTHROPIC_BASE_URL=https://api.minimaxi.com
MODEL_NAME=your-minimax-model
TEMPERATURE=0.001  # 不能为 0.0
```

## 功能特性支持矩阵

| 功能 | 官方 API | MiniMax API | 说明 |
|------|----------|-------------|------|
| Skills 集成 | ✅ 完全支持 | ✅ 完全支持 | 两者均支持 `~/.claude/skills/` |
| 工具调用 | ✅ 原生 JSON | ✅ XML 转换 | 协议不同但功能等效 |
| 流式输出 | ✅ 完全支持 | ✅ 基本支持 | MiniMax 不支持高级选项 |
| Temperature=0.0 | ✅ 支持 | ❌ 不支持 | MiniMax 最小 0.001 |
| 长推理任务 | ✅ 120s 超时 | ✅ 3000s 超时 | MiniMax 适合推理模型 |
| MCP 协议 | ✅ 支持 | ❌ 不支持 | 仅官方 API |
| 上下文管理 | ✅ 自动 | ❌ 手动 | MiniMax 需自行管理 |

## 迁移建议

### 从 MiniMax 迁移到官方 API

**步骤:**

1. 获取官方 API 密钥:
   - 访问 https://platform.claude.com/settings/keys
   - 创建新的 API Key

2. 更新 `.env` 文件:
   ```bash
   # 移除或注释 ANTHROPIC_BASE_URL
   # ANTHROPIC_BASE_URL=https://api.minimaxi.com

   # 使用官方 API Key
   ANTHROPIC_API_KEY=sk-ant-...

   # 使用推荐模型
   MODEL_NAME=claude-sonnet-4-20250514
   ```

3. 验证配置:
   ```bash
   python -c "from anthropic import Anthropic; c = Anthropic(); print('API OK')"
   ```

4. 运行测试:
   ```bash
   pytest tests/test_api_migration.py -v
   ```

**注意事项:**
- 官方 API 使用 120 秒超时,大多数任务足够
- 如果任务需要更长时间,可以在代码中调整 `API_TIMEOUT_MS`
- Temperature 参数可以设置为 0.0 (完全确定性输出)

### 保留 MiniMax 作为备用

如果需要同时支持两种 API,建议:

1. 使用环境变量切换:
   ```bash
   # 使用官方 API
   unset ANTHROPIC_BASE_URL

   # 使用 MiniMax API
   export ANTHROPIC_BASE_URL=https://api.minimaxi.com
   ```

2. 为不同环境创建不同的 `.env` 文件:
   - `.env.official` - 官方 API 配置
   - `.env.minimax` - MiniMax API 配置

3. 使用配置管理工具动态切换

## 常见问题

### Q: 为什么推荐官方 API?

**A:** 官方 API 提供:
- 更完整的功能支持 (MCP, context_management)
- 更好的兼容性和稳定性
- 标准化的认证流程
- 更快的响应时间 (大多数场景)
- 更新的模型版本

### Q: MiniMax API 还会继续支持吗?

**A:** 是的,本项目保持 100% 向后兼容性:
- 现有 MiniMax 配置继续正常工作
- 通过 `ANTHROPIC_BASE_URL` 自动检测
- 条件代码处理 API 差异
- 没有破坏性更改

### Q: Temperature=0.0 在 MiniMax 会怎样?

**A:** 系统会自动调整:
```python
# 如果设置 TEMPERATURE=0.0 且使用 MiniMax
# src/utils/temperature.py 会自动转换为 0.001
validate_temperature(0.0)  # 返回 0.001 (MiniMax)
validate_temperature(0.0)  # 返回 0.0 (官方 API)
```

### Q: 如何知道正在使用哪个 API?

**A:** 检查日志输出或环境变量:
```bash
# 查看当前 BASE_URL
echo $ANTHROPIC_BASE_URL

# 如果未设置或不包含 "minimaxi.com",则使用官方 API
```

## 测试支持

本项目包含专门的迁移测试套件 (`tests/test_api_migration.py`),验证:
- API 类型自动检测
- 条件超时配置
- 条件温度验证
- 向后兼容性

运行测试:
```bash
pytest tests/test_api_migration.py -v
```

## 相关文档

- **故障排除指南:** `docs/troubleshooting.md`
- **Skills 使用说明:** `docs/skills.md`
- **项目主文档:** `docs/README.md`

---

**文档版本:** 1.0
**最后更新:** 2026-01-28
**相关阶段:** Phase 03 (错误处理与 API 差异文档化), Phase 04 (迁移到官方 API)
