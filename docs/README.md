# 微信公众号文章写作 Agent

基于 Claude Agent SDK 和 NotebookLM 的智能写作助手，能够在写作过程中动态调用知识库获取素材，生成高质量的公众号文章。

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## ✨ 核心特性

- 🤖 **模块化架构** - 清晰的职责分离，易于维护和扩展
- 🔍 **智能检索** - 集成 NotebookLM，动态获取知识库素材
- ✍️ **AI 生成** - 基于 Claude Agent，保持个人风格和观点
- 📊 **类型安全** - 使用 Dataclass，完整的类型注解
- 🧪 **测试完善** - 18+ 单元测试，≥85% 代码覆盖率
- 🔄 **可扩展** - 预留飞书集成接口，易于添加新功能

---

## 🚀 快速开始

### 1. 克隆仓库

```bash
git clone <repository-url>
cd wechat-writer-agent
```

### 2. 安装依赖

```bash
# 激活虚拟环境（推荐）
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

## API 配置

### 官方 Anthropic API (推荐)

1. 获取 API Key: https://platform.claude.com/settings/keys
2. 复制 `.env.example` 为 `.env`
3. 设置 `ANTHROPIC_API_KEY=your-api-key`

```bash
cp .env.example .env
# 编辑 .env 填入你的 API Key
```

### 验证配置

```bash
# 运行简单测试验证 API 连接
python -c "from anthropic import Anthropic; c = Anthropic(); print('API OK')"
```

### MiniMax API (备用)

如需使用 MiniMax API，参见 `.env.example` 中的 "备用配置" 部分

### 4. 运行

#### 方式 1: CLI 交互式

```bash
python cli.py
```

#### 方式 2: 编程式调用

```python
from src.main import run_pipeline
import os

result = run_pipeline(
    topic="AI 时代的内容创作",
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

print(result.article.title)
print(result.article.content)
```

---

## 📁 项目结构

```
wechat-writer-agent/
├── src/                    # 源代码
│   ├── models.py          # 数据模型
│   ├── main.py            # 流水线编排
│   └── modules/           # 功能模块
│       ├── retrieval.py   # 检索模块
│       ├── generator.py   # 生成模块
│       ├── feishu_doc.py  # 飞书文档（接口）
│       └── feishu_table.py # 飞书表格（接口）
├── tests/                  # 测试文件
├── docs/                   # 📚 文档目录
├── cli.py                  # CLI 入口
└── example.py              # 使用示例
```

---

## 📚 文档

完整文档请查看 [docs/](docs/) 目录：

### 核心文档
- **[docs/overview.md](docs/overview.md)** ⭐ **重点推荐** - 系统架构与项目进度综合文档

### 补充文档
- **[docs/README.md](docs/README.md)** - 文档导航索引
- **[docs/setup.md](docs/setup.md)** - 详细安装配置指南
- **[docs/development-guide.md](docs/development-guide.md)** - 开发规范和 API 使用
- **[docs/testing-guide.md](docs/testing-guide.md)** - 测试框架和用例

---

## 🔧 故障排查

### 工具调用为0的问题

如果您发现运行日志中 `tool_call_count=0`，请按以下步骤诊断：

#### 步骤1：快速诊断配置

运行诊断脚本检查配置状态：
```bash
python diagnose_notebooklm.py
```

该脚本会检查：
- ✅ 环境变量配置（NOTEBOOK_ID, NOTEBOOK_URL）
- ✅ NotebookLM skill安装状态
- ✅ 工具注册逻辑
- ✅ 认证配置
- ✅ Agent SDK模式

如果发现 ❌ 关键问题，按照提示修复配置。

#### 步骤2：测试工具调用

配置修复后，运行测试脚本验证：
```bash
python test_tool_calls.py
```

该脚本会：
- 使用多个测试场景（需要检索 vs 素材充分）
- 分析Agent的工具调用行为
- 判断是"配置问题"还是"智能决策"

#### 步骤3：查看详细日志

如果测试通过但实际使用中仍为0：
1. 检查飞书日志文档的"Configuration Summary"部分
2. 查看诊断提示：
   - ⚠️ "Notebook ID未设置" → 配置问题
   - ✅ "Agent智能决策" → 正常行为

### 常见问题

**Q: 为什么工具调用为0？**
A: 可能原因：
1. NOTEBOOK_ID未配置（运行 `diagnose_notebooklm.py` 检查）
2. 预检索结果已充分，Agent判断无需追加检索（正常行为）
3. NotebookLM笔记本为空或内容不相关

**Q: 如何区分配置问题和正常行为？**
A: 使用诊断和测试工具：
- `diagnose_notebooklm.py` → 发现配置问题
- `test_tool_calls.py` → 验证工具调用能力
- 查看日志的配置摘要 → 智能诊断提示

**Q: 日志中看不到Agent思考过程？**
A: 这是Claude API的技术限制。详见 [logging_limitations.md](logging_limitations.md)

### 更多帮助

- **技术限制文档**: [logging_limitations.md](logging_limitations.md)
- **完整实施文档**: [agent_log.md](agent_log.md)
- **项目状态**: [project-status.md](project-status.md)

---

## 🧪 运行测试

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行所有测试
pytest tests/test_models.py tests/test_retrieval.py tests/test_pipeline.py -v

# 生成覆盖率报告
pytest tests/ --cov=src --cov=cli --cov-report=html
open htmlcov/index.html
```

详细测试指南请参考 [docs/testing-guide.md](docs/testing-guide.md)

---

## 🎯 使用示例

### CLI 交互式

```bash
$ python cli.py

请输入文章主题: AI 产品经理的一天
是否启用飞书集成? (y/n): n

🚀 开始内容生产流水线
============================================================

📚 阶段 1/4: 检索素材
✅ 检索成功，获得 3 条结果

✍️  阶段 2/4: 生成文章
✅ 文章生成完成
   标题: AI 产品经理的一天
   字数: 2847 字符

📄 阶段 3/4: 创建飞书云文档
⏭️  飞书集成已禁用，跳过此步骤

📊 阶段 4/4: 插入多维表格记录
⏭️  飞书集成已禁用，跳过此步骤

🎉 流水线执行完成

文章已保存到: article_20260125_210530.md
```

### 编程式调用

```python
from src.main import run_pipeline

result = run_pipeline(
    topic="你的主题",
    api_key="your-api-key",
    notebook_id="your-notebook",
    enable_feishu=False
)

# 访问结果
print(f"标题: {result.article.title}")
print(f"正文: {result.article.content}")
print(f"来源: {result.article.source_summary}")
```

---

## 🔧 核心 API

### run_pipeline()

主流水线函数，编排整个内容生产过程。

```python
def run_pipeline(
    topic: str,                    # 文章主题
    api_key: str,                  # Anthropic API Key
    notebook_id: Optional[str] = None,    # NotebookLM 笔记本 ID
    notebook_url: Optional[str] = None,   # NotebookLM 笔记本 URL
    folder_token: Optional[str] = None,   # 飞书文件夹 Token
    enable_feishu: bool = False,   # 是否启用飞书集成
    max_retries: int = 1           # 失败重试次数
) -> PipelineResult
```

**返回**: `PipelineResult` 对象，包含生成的文章和飞书结果（如启用）

详细 API 文档请参考 [docs/development-guide.md](docs/development-guide.md)

---

## 📈 项目状态

- ✅ **阶段一：模块化重构** - 100% 完成
- ⏳ **测试完善** - 58% 完成（18/31 测试）
- 📅 **阶段二：飞书集成** - 15% 完成（接口已定义）

详细进度请查看 [docs/project-status.md](docs/project-status.md)

---

## 🤝 贡献

欢迎贡献！请查看相关文档：

- [开发指南](docs/development-guide.md)
- [测试指南](docs/testing-guide.md)

---

## 📄 许可证

[MIT License](LICENSE)

---

## 🔗 相关资源

- [Anthropic Claude 文档](https://docs.anthropic.com/)
- [Claude Agent SDK](https://github.com/anthropics/anthropic-sdk-python)
- [NotebookLM](https://notebooklm.google/)
- [项目文档](docs/)

---

**维护者**: 项目团队
**最后更新**: 2026-01-28（迁移到官方 Anthropic API）
