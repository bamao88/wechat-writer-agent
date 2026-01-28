# 故障排除指南

本指南提供工具调用和 Agent SDK 集成的常见问题诊断和解决方案。

## 快速诊断

遇到问题时,首先运行诊断脚本快速定位问题根源:

```bash
python scripts/diagnose_sdk_tool_calling.py --verbose
```

诊断脚本会系统性地检查四个阶段:

1. **技能发现** - 验证 NotebookLM 技能目录和配置是否正确
2. **环境变量** - 检查所有必需的环境变量是否已设置
3. **独立技能调用** - 直接测试技能脚本执行是否成功
4. **Agent SDK 配置** - 验证 SDK 设置和工具注册是否正确

诊断脚本会输出明确的 `[PASS]` 或 `[FAIL]` 标记,帮助快速定位问题所在阶段。

## 常见问题

### 1. "Command failed with exit code 1"

**症状:**
Agent SDK 调用工具时返回以下错误:
```
Exception: Command failed with exit code 1 (exit code: 1)
Error output: Check stderr output for details
```

**可能原因:**
- NotebookLM skill 未正确安装或目录结构不完整
- 环境变量未传递给子进程 (如 `NOTEBOOK_ID`, `ANTHROPIC_API_KEY`)
- skill 脚本内部错误 (如 Python 依赖缺失、认证失败)
- 执行权限问题

**诊断步骤:**

1. 运行完整诊断脚本:
   ```bash
   python scripts/diagnose_sdk_tool_calling.py --verbose
   ```

2. 检查诊断输出,查找 `[FAIL]` 标记的具体阶段:
   - **Phase 1 失败:** skill 目录或配置文件问题
   - **Phase 2 失败:** 环境变量缺失
   - **Phase 3 失败:** skill 脚本执行错误
   - **Phase 4 失败:** SDK 配置问题

3. 检查必需的环境变量是否已设置:
   ```bash
   echo $NOTEBOOK_ID
   echo $ANTHROPIC_API_KEY
   ```

4. 手动执行技能脚本验证:
   ```bash
   python ~/.claude/skills/notebooklm/scripts/run.py ask_question.py \
     --notebook_id "$NOTEBOOK_ID" \
     --question "测试问题"
   ```

**解决方案:**

- **目录问题:** 确保 `~/.claude/skills/notebooklm/` 目录存在且结构完整
  ```bash
  ls -la ~/.claude/skills/notebooklm/
  # 应包含: config.toml, scripts/, 等文件
  ```

- **环境变量问题:** 确保 `.env` 文件包含所有必需变量
  ```bash
  # .env 文件中
  NOTEBOOK_ID=your-notebook-id
  ANTHROPIC_API_KEY=sk-ant-...
  ```

- **依赖问题:** 检查并安装 skill 所需的 Python 包
  ```bash
  cd ~/.claude/skills/notebooklm/
  pip install -r requirements.txt
  ```

- **权限问题:** 确保脚本有执行权限
  ```bash
  chmod +x ~/.claude/skills/notebooklm/scripts/run.py
  ```

### 2. "NotebookLM 未认证"

**症状:**
查询 NotebookLM 时返回认证错误或未登录提示:
```
Error: NotebookLM authentication required
Please run authentication setup
```

**可能原因:**
- NotebookLM 浏览器自动化凭证未配置
- 认证会话已过期
- 浏览器 profile 损坏或缺失

**解决方案:**

1. 运行认证设置向导:
   ```bash
   python ~/.claude/skills/notebooklm/scripts/run.py auth_manager.py setup
   ```

2. 按照向导提示完成浏览器登录流程

3. 验证认证状态:
   ```bash
   python ~/.claude/skills/notebooklm/scripts/run.py auth_manager.py status
   ```

4. 如果问题持续,尝试清理并重新认证:
   ```bash
   # 清理现有认证
   python ~/.claude/skills/notebooklm/scripts/run.py auth_manager.py clear

   # 重新设置
   python ~/.claude/skills/notebooklm/scripts/run.py auth_manager.py setup
   ```

### 3. "tool_call_count 始终为 0"

**症状:**
Agent 运行完成,但 `metrics.tool_call_count` 始终为 0,表示工具从未被调用。

**可能原因:**
- `allowed_tools` 配置未包含 `"Skill"` 类别
- `setting_sources` 未包含 `"user"` (导致无法发现 `~/.claude/skills/`)
- 提示词未触发工具调用需求
- Agent 认为无需调用工具即可完成任务

**诊断步骤:**

1. 检查 SDK 配置 (`src/modules/agent_sdk.py`):
   ```python
   options = ClaudeAgentOptions(
       setting_sources=["user"],  # 必须包含 "user"
       allowed_tools=["Skill"]    # 必须包含 "Skill"
   )
   ```

2. 检查环境变量:
   ```bash
   # NOTEBOOK_ID 必须设置,否则 allowed_tools 返回空列表
   echo $NOTEBOOK_ID
   ```

3. 检查提示词是否创造了明确的工具调用需求:
   ```python
   # 强制触发工具调用的示例
   user_message = "选题：{topic}\n\n未检索到相关素材,请使用工具追加检索。"
   ```

**解决方案:**

- **配置检查:** 确保 `agent_sdk.py` 中的 `_get_allowed_tools()` 返回 `["Skill"]`

- **环境变量:** 设置 `NOTEBOOK_ID` 在 `.env` 文件中

- **强制工具调用:** 使用空的 `search_results` 列表:
  ```python
  # 在测试或特定场景下
  result = await runner.generate(
      topic=topic,
      search_results=[],  # 空列表强制 Agent 调用工具
      system_prompt=system_prompt
  )
  ```

- **验证工具注册:** 检查日志中是否有工具注册消息:
  ```
  [INFO] Enabling Skill discovery (notebook_id=...)
  ```

### 4. "查询超时"

**症状:**
工具调用执行时间超过预期,最终超时失败:
```
Timeout: Tool execution exceeded 180 seconds
```

**可能原因:**
- NotebookLM 浏览器自动化缓慢 (网页加载、元素定位)
- 网络连接问题 (访问 NotebookLM 服务缓慢)
- NotebookLM 笔记本内容量大,查询处理时间长
- API 超时配置过短

**诊断步骤:**

1. 检查网络连接:
   ```bash
   curl -I https://notebooklm.google.com
   ```

2. 手动测试 NotebookLM 查询时间:
   ```bash
   time python ~/.claude/skills/notebooklm/scripts/run.py ask_question.py \
     --notebook_id "$NOTEBOOK_ID" \
     --question "测试查询"
   ```

3. 检查当前超时配置:
   ```bash
   echo $API_TIMEOUT_MS
   ```

**解决方案:**

- **增加超时时间:**
  ```bash
  # .env 文件中
  API_TIMEOUT_MS=300000  # 5 分钟
  ```

- **使用 MiniMax API (更长超时):**
  ```bash
  # MiniMax API 自动使用 3000 秒超时
  ANTHROPIC_BASE_URL=https://api.minimaxi.com
  ```

- **优化笔记本大小:**
  - 减少笔记本中的文档数量
  - 分割大型笔记本为多个小笔记本
  - 使用更具体的查询减少处理时间

- **检查 NotebookLM 服务状态:**
  - 访问 https://notebooklm.google.com 确认服务可用
  - 查看是否有维护公告

- **调整 Hook 超时:**
  ```python
  # 在 agent_sdk.py 中调整
  "Stop": [
      HookMatcher(
          hooks=[...],
          timeout=300  # 从 180 秒增加到 300 秒
      )
  ]
  ```

### 5. API 认证失败 (401 Unauthorized)

**症状:**
调用 API 时返回 401 认证错误:
```
HTTP 401: Invalid API key
anthropic.AuthenticationError: Invalid API key
```

**可能原因:**
- API Key 错误、过期或无效
- API Key 格式不正确
- API Key 权限不足
- 官方 API vs MiniMax API 配置混淆

**诊断步骤:**

1. 检查 API Key 是否正确设置:
   ```bash
   echo $ANTHROPIC_API_KEY
   # 官方 API: 应以 sk-ant- 开头
   ```

2. 验证 API 连接:
   ```bash
   # 官方 API
   python -c "from anthropic import Anthropic; c = Anthropic(); print('API OK')"

   # MiniMax API (如果使用)
   curl -H "Authorization: Bearer $ANTHROPIC_API_KEY" \
     "$ANTHROPIC_BASE_URL/v1/messages"
   ```

3. 检查 API 类型配置:
   ```bash
   echo $ANTHROPIC_BASE_URL
   # 官方 API: 应该为空或 api.anthropic.com
   # MiniMax API: 应该为 api.minimaxi.com
   ```

**解决方案:**

- **官方 Anthropic API:**
  1. 访问 https://platform.claude.com/settings/keys
  2. 创建新的 API Key
  3. 更新 `.env`:
     ```bash
     ANTHROPIC_API_KEY=sk-ant-your-new-key
     # 不设置 ANTHROPIC_BASE_URL (使用默认)
     ```

- **MiniMax API:**
  1. 确认 MiniMax API Key 有效
  2. 确保设置了正确的 BASE_URL:
     ```bash
     ANTHROPIC_API_KEY=your-minimax-key
     ANTHROPIC_BASE_URL=https://api.minimaxi.com
     ```

- **检查 API Key 权限:**
  - 确保 API Key 有调用 Messages API 的权限
  - 检查 API Key 的使用限制和配额

- **格式检查:**
  ```bash
  # 确保没有多余的空格或换行
  ANTHROPIC_API_KEY=$(echo $ANTHROPIC_API_KEY | tr -d ' \n\r')
  ```

### 6. 环境变量未传递给子进程

**症状:**
- 诊断脚本 Phase 2 (环境变量检查) 通过
- 但 Phase 3 (独立技能调用) 显示环境变量缺失
- 或工具调用失败,显示 "NOTEBOOK_ID not set"

**可能原因:**
- 子进程调用时未继承环境变量
- `subprocess.run()` 未传递 `env` 参数
- Docker/容器环境变量隔离

**解决方案:**

1. 确保 `.env` 文件加载到进程环境:
   ```python
   from dotenv import load_dotenv
   load_dotenv()  # 必须在子进程创建前调用
   ```

2. 检查子进程调用方式 (`src/tools/subprocess_runner.py`):
   ```python
   import os

   result = subprocess.run(
       command,
       env=os.environ.copy(),  # 继承所有环境变量
       ...
   )
   ```

3. 显式传递关键环境变量:
   ```python
   env = os.environ.copy()
   env['NOTEBOOK_ID'] = os.getenv('NOTEBOOK_ID')
   env['ANTHROPIC_API_KEY'] = os.getenv('ANTHROPIC_API_KEY')

   result = subprocess.run(command, env=env, ...)
   ```

### 7. "Skill not found" 或技能未注册

**症状:**
Agent 运行时日志显示:
```
[WARNING] notebook_id not set, NotebookLM tool not registered
Hint: Set NOTEBOOK_ID in .env to enable tool calling
```

**可能原因:**
- `NOTEBOOK_ID` 环境变量未设置
- Skill 目录结构不符合预期
- `config.toml` 文件缺失或格式错误

**解决方案:**

1. 设置 `NOTEBOOK_ID`:
   ```bash
   # .env 文件
   NOTEBOOK_ID=your-notebook-id
   ```

2. 验证 Skill 目录结构:
   ```bash
   tree ~/.claude/skills/notebooklm/
   # 应包含:
   # ├── config.toml
   # ├── scripts/
   # │   ├── run.py
   # │   ├── ask_question.py
   # │   └── ...
   # └── ...
   ```

3. 检查 `config.toml` 格式:
   ```toml
   [skill]
   name = "notebooklm"
   description = "Query NotebookLM notebooks"

   [skill.parameters]
   notebook_id = { type = "string", description = "Notebook ID" }
   question = { type = "string", description = "Question to ask" }
   ```

4. 运行诊断脚本验证:
   ```bash
   python scripts/diagnose_sdk_tool_calling.py --verbose
   # 检查 Phase 1 是否通过
   ```

## 日志解读

### 工具调用生命周期日志

Agent SDK 集成了完整的工具调用生命周期日志,帮助追踪每次工具调用的状态:

```
[TOOL-LIFECYCLE] NotebookLM | Phase: registration | Status: discovered
  # 工具被 SDK 发现并注册

[TOOL-LIFECYCLE] NotebookLM | Phase: call_start | Input: {"question": "..."}
  # Agent 决定调用工具,记录输入参数

[TOOL-LIFECYCLE] NotebookLM | Phase: execution | Command: python ~/.claude/skills/...
  # 子进程开始执行

[TOOL-LIFECYCLE] NotebookLM | Phase: response | Success: true | Duration: 15.3s
  # 工具调用成功,返回结果

[TOOL-LIFECYCLE] NotebookLM | Phase: error | Error: Command failed with exit code 1
  # (如果失败) 记录错误信息
```

**日志关键字段:**

- **Phase:** 当前生命周期阶段 (registration, call_start, execution, response, error)
- **Status:** 状态标记 (discovered, running, success, failed)
- **Input:** 工具调用输入参数
- **Duration:** 执行时长 (秒)
- **Error:** 错误信息 (如果失败)

### 诊断脚本输出解读

运行 `python scripts/diagnose_sdk_tool_calling.py --verbose` 后,输出格式如下:

```
=== Phase 1: Skill Discovery ===
[PASS] NotebookLM skill directory exists
[PASS] config.toml is valid
[PASS] Required scripts present

=== Phase 2: Environment Variables ===
[PASS] NOTEBOOK_ID is set
[FAIL] ANTHROPIC_API_KEY not found in environment
  → 请在 .env 文件中设置 ANTHROPIC_API_KEY

=== Phase 3: Standalone Skill Execution ===
[SKIP] Skipping due to Phase 2 failure

=== Phase 4: Agent SDK Configuration ===
[SKIP] Skipping due to Phase 2 failure
```

**标记说明:**

- **[PASS]** - 检查通过,该部分配置正确
- **[FAIL]** - 检查失败,需要修复
- **[WARN]** - 警告,可能影响功能但不致命
- **[SKIP]** - 跳过,因为前置检查失败

**诊断策略:**

1. **从上到下修复:** 从 Phase 1 开始,依次修复每个失败的检查
2. **关注第一个 [FAIL]:** 通常后续失败都是由第一个问题引起的
3. **使用 --verbose 标志:** 获取更详细的错误信息和建议

### 性能日志

监控工具调用性能,识别瓶颈:

```
[PERFORMANCE] Tool call completed in 23.5s (NotebookLM)
[PERFORMANCE] Total tokens: 1500 (prompt: 800, completion: 700)
[PERFORMANCE] Agent runtime: 45.2s (2 tool calls)
```

**性能基准:**

- **快速查询:** < 10 秒
- **正常查询:** 10-30 秒
- **慢速查询:** > 30 秒 (考虑优化)

如果工具调用持续超过 60 秒,参考 [问题 4: 查询超时](#4-查询超时) 进行优化。

## 获取更多帮助

如果以上步骤无法解决问题:

1. **运行完整诊断:**
   ```bash
   python scripts/diagnose_sdk_tool_calling.py --verbose
   ```
   保存输出结果以便分析。

2. **检查完整目录结构:**
   ```bash
   tree ~/.claude/skills/notebooklm/
   ```

3. **收集日志信息:**
   - Agent 运行日志 (包含 [TOOL-LIFECYCLE] 标记)
   - 诊断脚本输出
   - 错误堆栈信息

4. **查看相关文档:**
   - **API 差异文档:** `docs/api-differences.md` - 了解不同 API 的差异
   - **Skills 使用说明:** `docs/skills.md` - Skill 开发和配置指南
   - **项目主文档:** `docs/README.md` - 项目整体说明

5. **检查代码关键位置:**
   - `src/modules/agent_sdk.py` - SDK 配置和工具注册
   - `src/tools/subprocess_runner.py` - 子进程调用逻辑
   - `src/hooks/logging_hooks.py` - 工具调用生命周期 hooks

## 预防性措施

### 开发环境检查清单

在开始开发或部署前,执行以下检查:

- [ ] `.env` 文件存在且包含所有必需变量
- [ ] `NOTEBOOK_ID` 已设置且有效
- [ ] `ANTHROPIC_API_KEY` 已设置且有效
- [ ] NotebookLM skill 已正确安装
- [ ] 诊断脚本四个阶段全部通过
- [ ] 基础测试套件通过 (`pytest tests/`)

### 部署前验证

部署到生产环境前:

```bash
# 1. 运行诊断
python scripts/diagnose_sdk_tool_calling.py --verbose

# 2. 运行集成测试
pytest tests/test_tool_calling.py -v

# 3. 验证 API 连接
python -c "from anthropic import Anthropic; c = Anthropic(); print('API OK')"

# 4. 测试完整流程
python src/main.py --topic "测试主题" --notebook_id "$NOTEBOOK_ID"
```

### 监控建议

生产环境建议监控:

- 工具调用成功率 (`metrics.tool_call_count` vs 预期)
- 工具调用平均耗时 (识别性能下降)
- API 认证失败次数 (检测 Key 过期)
- 超时次数 (调整超时配置)

---

**文档版本:** 1.0
**最后更新:** 2026-01-28
**相关阶段:** Phase 03 (错误处理与 API 差异文档化)
**相关工具:** `scripts/diagnose_sdk_tool_calling.py`
