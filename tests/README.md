# NotebookLM Skill 测试套件

这是 NotebookLM Skill 的综合测试套件，包含单元测试、集成测试和端到端测试。

## 测试文件结构

```
tests/
├── __init__.py                     # 测试包初始化
├── test_notebooklm_tool.py        # P0: NotebookLMTool 单元测试
├── test_e2e.py                    # P0: 端到端测试
├── test_external_skill.py         # P1: 外部 Skill 集成测试
├── test_writer_agent.py           # P1: WechatWriterAgent 测试
├── test_error_handling.py         # P1: 错误处理测试
└── README.md                      # 本文件
```

## 测试优先级

### P0 (必须通过)
- `test_notebooklm_tool.py` - NotebookLMTool 核心功能
- `test_e2e.py` - 基本的端到端工作流

### P1 (重要)
- `test_external_skill.py` - 外部 Skill 集成
- `test_writer_agent.py` - Agent 集成
- `test_error_handling.py` - 错误处理

### P2 (可选)
- 性能测试
- 交互式测试

## 环境准备

### 1. 安装依赖

由于系统使用外部管理的 Python 环境，建议使用虚拟环境：

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

或者使用 `--break-system-packages` 标志（不推荐）：

```bash
pip3 install -r requirements.txt --break-system-packages
```

### 2. 配置环境变量

创建 `.env` 文件（如果还没有）：

```bash
cp .env.example .env
```

编辑 `.env` 文件，设置：

```
ANTHROPIC_API_KEY=your-api-key-here
```

### 3. 安装 NotebookLM Skill（可选）

大部分测试使用 mock，不需要真实的 Skill。但如果要运行集成测试：

```bash
mkdir -p ~/.claude/skills
cd ~/.claude/skills
git clone https://github.com/PleasePrompto/notebooklm-skill notebooklm
```

## 运行测试

### 运行所有测试

```bash
pytest tests/ -v
```

### 运行特定测试文件

```bash
# P0 测试
pytest tests/test_notebooklm_tool.py -v
pytest tests/test_e2e.py -v

# P1 测试
pytest tests/test_external_skill.py -v
pytest tests/test_writer_agent.py -v
pytest tests/test_error_handling.py -v
```

### 运行特定测试类或方法

```bash
# 运行特定测试类
pytest tests/test_notebooklm_tool.py::TestNotebookLMToolInitialization -v

# 运行特定测试方法
pytest tests/test_notebooklm_tool.py::TestNotebookLMToolInitialization::test_default_initialization -v
```

### 跳过集成测试

集成测试需要真实的环境（API Key、NotebookLM Skill 等），默认会被跳过：

```bash
# 跳过所有 integration 标记的测试
pytest tests/ -v -m "not integration"
```

### 运行集成测试

如果你有完整的环境设置：

```bash
pytest tests/ -v -m integration
```

### 生成覆盖率报告

```bash
# HTML 报告
pytest tests/ --cov=. --cov-report=html

# 在浏览器中打开报告
open htmlcov/index.html  # macOS
# 或
xdg-open htmlcov/index.html  # Linux
```

### 并行运行测试（需要 pytest-xdist）

```bash
pip install pytest-xdist
pytest tests/ -n auto
```

## 测试覆盖范围

### test_notebooklm_tool.py (P0)

测试 `NotebookLMTool` 类的核心功能：

- ✅ 初始化（默认、notebook_id、notebook_url）
- ✅ Tool Definition 格式和内容
- ✅ Query 功能（正常查询、空查询、特殊字符、超时）
- ✅ 错误处理（未认证、笔记本不存在）
- ✅ 参数传递（notebook_id、notebook_url 优先级）

### test_e2e.py (P0)

测试端到端工作流：

- ✅ 程序化调用（默认、自定义 notebook）
- ✅ 文章生成流程
- ✅ Tool call 集成
- ✅ 多轮对话
- ✅ 错误处理（缺失 API Key、缺失 Skill）

### test_external_skill.py (P1)

测试与外部 Skill 的集成：

- ✅ Subprocess 调用结构
- ✅ 参数传递
- ✅ 输出解析（标准格式、多行、follow-up reminder）
- ✅ 认证错误处理
- ✅ 笔记本参数（默认、ID、URL 优先级）

### test_writer_agent.py (P1)

测试 WechatWriterAgent：

- ✅ Agent 初始化（默认、自定义参数）
- ✅ Tool call 处理
- ✅ 多轮对话
- ✅ 系统提示词
- ✅ 消息构造
- ✅ 不同 stop_reason 处理

### test_error_handling.py (P1)

测试错误场景：

- ✅ API Key 错误（缺失、无效）
- ✅ Skill 错误（未安装、未认证、无笔记本）
- ✅ 网络错误（超时、连接错误）
- ✅ 输入边界（空输入、超长输入、特殊字符）
- ✅ 无效参数（无效 ID、无效 URL）
- ✅ 畸形响应处理
- ✅ 错误恢复

## 成功标准

NotebookLM Skill 被认为正常工作，当且仅当：

1. ✅ 所有 P0 测试通过
2. ✅ 至少 80% 的 P1 测试通过
3. ✅ Tool definition 符合 Claude API 规范
4. ✅ 错误处理清晰且有帮助
5. ✅ 无严重的崩溃或挂起

## 故障排除

### 问题: `ModuleNotFoundError: No module named 'pytest'`

**解决**: 安装 pytest

```bash
pip install pytest pytest-timeout pytest-mock pytest-cov
```

### 问题: `ValueError: NotebookLM skill 未安装`

**解决**: 这是正常的，测试使用 mock。如果要运行集成测试，需要安装真实的 Skill。

### 问题: `ValueError: 请设置 ANTHROPIC_API_KEY`

**解决**: 设置环境变量

```bash
export ANTHROPIC_API_KEY=your-key
# 或在 .env 文件中设置
```

### 问题: 测试超时

**解决**: 增加超时时间或检查网络连接

```bash
pytest tests/ -v --timeout=600
```

### 问题: 导入错误

**解决**: 确保在项目根目录运行测试

```bash
cd /Volumes/ExtSSD2601/IP_ZH/wechat-writer-agent
pytest tests/ -v
```

## 持续集成

这些测试可以集成到 CI/CD 流程中：

```yaml
# .github/workflows/test.yml 示例
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.8'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest tests/ -v -m "not integration"
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

## 贡献

添加新测试时，请：

1. 遵循现有的命名约定
2. 为复杂测试添加注释
3. 使用适当的 pytest 标记（`@pytest.mark.integration` 等）
4. 更新本 README

## 参考资料

- [Pytest 文档](https://docs.pytest.org/)
- [测试计划](/Users/xpw/.claude/plans/rippling-chasing-metcalfe.md)
- [项目 README](../README.md)
