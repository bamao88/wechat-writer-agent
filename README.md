# 微信公众号文章写作 Agent

基于 Claude API 和 NotebookLM 的智能写作助手，能够在写作过程中动态调用知识库获取素材，生成高质量的公众号文章。

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

```bash
# 复制配置文件
cp .env.example .env

# 编辑 .env 文件
# 设置 ANTHROPIC_API_KEY=your-api-key-here
```

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

- [Claude API 文档](https://docs.anthropic.com/)
- [NotebookLM](https://notebooklm.google/)
- [项目文档](docs/)

---

**维护者**: 项目团队
**最后更新**: 2026-01-25
