# GitHub 仓库设置建议

## 1. 仓库描述和标签

建议在 GitHub 仓库页面添加：

**Description**:
```
微信公众号文章自动生成系统 - 基于 NotebookLM + Claude 的 AI 写作助手
```

**Topics (标签)**:
```
ai, claude, notebooklm, article-generator, wechat, python, automation
```

## 2. 创建 GitHub Issues 模板

可以创建以下标签：
- `enhancement` - 功能增强
- `bug` - Bug 报告
- `documentation` - 文档改进
- `optimization` - 效果优化

## 3. 添加 GitHub Actions

建议添加 CI/CD 配置：

**.github/workflows/tests.yml**:
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run tests
        run: |
          pytest tests/ -v
```

## 4. 设置分支保护

建议设置：
- 禁止直接推送到 main
- 要求 Pull Request 审查
- 要求测试通过才能合并

## 5. 项目徽章

可以在 README.md 添加：
```markdown
![Tests](https://github.com/bamao88/wechat-writer-agent/workflows/Tests/badge.svg)
![Python Version](https://img.shields.io/badge/python-3.13-blue)
![License](https://img.shields.io/badge/license-MIT-green)
```
