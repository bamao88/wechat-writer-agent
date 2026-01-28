# Prompt 系统使用指南

## 概述

系统支持从 `write_prompt/` 目录加载不同版本的 System Prompt，方便管理和切换写作风格。

---

## 📁 目录结构

```
wechat-writer-agent/
└── write_prompt/           # Prompt 文件目录
    ├── V1.md              # 版本1（默认）
    ├── V2.md              # 版本2（可选）
    ├── V3.md              # 版本3（可选）
    └── experimental.md    # 实验版本（可选）
```

---

## 🔍 版本选择逻辑

### 优先级（从高到低）

1. **函数参数** `version`
2. **环境变量** `PROMPT_VERSION`
3. **默认值** `"V1"`

### 降级策略

```
指定版本（如 V2）
    ↓
文件存在？
    ├─ 是 → 使用该版本
    └─ 否 → 尝试降级到 V1.md
              ↓
          V1.md 存在？
              ├─ 是 → 使用 V1.md
              └─ 否 → 使用内置默认 prompt
```

---

## 📝 使用方法

### 方法1: 使用默认版本（V1）

**不需要任何配置**，系统自动使用 `write_prompt/V1.md`

```bash
# 直接运行
python cli.py
```

---

### 方法2: 环境变量切换版本

**场景**：长期使用某个版本

**步骤**：

1. 在 `.env` 文件中设置：
```bash
PROMPT_VERSION=V2
```

2. 运行程序：
```bash
python cli.py
```

**输出**：
```
✅ 使用 Prompt 版本: V2 (V2.md)
```

---

### 方法3: 临时切换版本

**场景**：临时测试某个版本

**命令行设置**：
```bash
# macOS/Linux
export PROMPT_VERSION=V3
python cli.py

# 或一行搞定
PROMPT_VERSION=V3 python cli.py
```

**Windows (PowerShell)**：
```powershell
$env:PROMPT_VERSION="V3"
python cli.py
```

---

### 方法4: 代码中指定版本

**场景**：编程调用时指定版本

```python
from src.modules.generator import generate_with_sdk

# 使用 V2 版本的 prompt
article, metrics = await generate_with_sdk(
    topic="产品经理要参与技术选型",
    search_results=[...],
    api_key=api_key,
    # 注意：当前需要修改 generator.py 才能传递 version 参数
)
```

---

## 🆕 创建新版本 Prompt

### 步骤1: 创建新文件

```bash
cd /Volumes/ExtSSD2601/IP_ZH/wechat-writer-agent/write_prompt/
cp V1.md V2.md
```

### 步骤2: 编辑新文件

```bash
# 使用你喜欢的编辑器
vim V2.md
# 或
code V2.md
```

### 步骤3: 测试新版本

```bash
PROMPT_VERSION=V2 python test_prompt_version.py
```

### 步骤4: 使用新版本

```bash
# 方式1: 设置环境变量
export PROMPT_VERSION=V2
python cli.py

# 方式2: 修改 .env 文件
echo "PROMPT_VERSION=V2" >> .env
python cli.py
```

---

## 🧪 测试和验证

### 查看当前配置

```bash
# 查看环境变量
echo $PROMPT_VERSION

# 查看 .env 文件
cat .env | grep PROMPT_VERSION
```

### 测试版本选择

```bash
# 运行测试脚本
python test_prompt_version.py
```

**输出示例**：
```
📁 write_prompt 目录下的文件:
   - V1.md (2460 字节)
   - V2.md (3200 字节)

测试1: 默认行为
------------------------------------------------------------
✅ 使用 Prompt 版本: V1 (V1.md)
   结果长度: 2460 字符

测试2: 环境变量 PROMPT_VERSION=V2
------------------------------------------------------------
✅ 使用 Prompt 版本: V2 (V2.md)
   结果长度: 3200 字符
```

---

## 📋 当前可用版本

### V1.md（默认）

**特点**：
- 张和的个人写作风格
- 8年AI产品经理经验背景
- 详细的4步工作流程
- 完整的禁止清单（避免AI痕迹）
- 第一人称写作要求

**适用场景**：
- 个人IP内容创作
- AI产品经理经验分享
- 训练营课程相关文章

**文件大小**：2460 字符

---

## ❓ 常见问题

### Q1: 如果指定的版本不存在会怎样？

**A**: 系统会自动降级到 V1.md，如果 V1.md 也不存在，则使用内置的简化默认 prompt。

**示例**：
```bash
PROMPT_VERSION=V999 python cli.py
```

**输出**：
```
⚠️ 警告：未找到 prompt 文件 .../write_prompt/V999.md
   降级使用: V1.md
✅ 使用 Prompt 版本: V1 (V1.md)
```

---

### Q2: 如何查看当前使用的是哪个版本？

**A**: 运行程序时会显示：

```
✅ 使用 Prompt 版本: V2 (V2.md)
```

或查看生成的日志，System Prompt 会完整记录在日志中。

---

### Q3: 可以同时使用多个版本吗？

**A**: 不可以。每次运行只能使用一个版本。但你可以：
- 保存多个版本的 .md 文件
- 通过环境变量快速切换
- 或者创建不同的 .env 文件（如 .env.v1, .env.v2）

---

### Q4: 如何备份或分享 Prompt？

**A**: 直接复制 `write_prompt/` 目录下的 .md 文件：

```bash
# 备份
cp write_prompt/V1.md write_prompt/V1_backup_20260127.md

# 分享
scp write_prompt/V2.md user@server:/path/to/project/write_prompt/
```

---

### Q5: Prompt 修改后需要重启程序吗？

**A**: 是的。Prompt 在程序启动时加载，修改后需要重新运行程序。

```bash
# 修改 V1.md
vim write_prompt/V1.md

# 重新运行
python cli.py  # 会加载新的 prompt
```

---

## 🎯 最佳实践

### 1. 版本命名规范

```
V1.md          # 主版本
V2.md          # 主版本
V1_short.md    # V1 的简化版
V1_formal.md   # V1 的正式版
experimental.md # 实验性版本
```

### 2. 版本控制

建议使用 Git 管理 prompt 版本：

```bash
# 提交新版本
git add write_prompt/V2.md
git commit -m "feat: 添加 V2 prompt - 增强技术内容"

# 查看历史
git log -- write_prompt/
```

### 3. 测试流程

```bash
# 1. 创建新版本
cp write_prompt/V1.md write_prompt/V2.md

# 2. 编辑修改
vim write_prompt/V2.md

# 3. 测试加载
PROMPT_VERSION=V2 python test_prompt_version.py

# 4. 实际测试
PROMPT_VERSION=V2 python test_integration.py

# 5. 确认无误后设为默认
echo "PROMPT_VERSION=V2" >> .env
```

---

## 📚 相关文档

- [PROMPT_UPDATE.md](../PROMPT_UPDATE.md) - Prompt 系统更新说明
- [write_prompt/V1.md](../write_prompt/V1.md) - 默认 Prompt 内容
- [agent_log.md](agent_log.md) - Agent 日志系统文档
- [logging_limitations.md](logging_limitations.md) - 日志系统技术限制

---

## 🔧 故障排查

### 问题：提示 "未找到 prompt 文件"

**原因**：文件不存在或路径错误

**解决**：
```bash
# 检查文件是否存在
ls -la write_prompt/

# 检查环境变量
echo $PROMPT_VERSION

# 重置为默认
unset PROMPT_VERSION
```

### 问题：Prompt 内容没有更新

**原因**：修改后没有重启程序

**解决**：
```bash
# 确保重新运行程序
python cli.py
```

### 问题：不知道用的哪个版本

**原因**：环境变量冲突或 .env 文件设置

**解决**：
```bash
# 查看所有相关配置
cat .env | grep PROMPT
echo $PROMPT_VERSION

# 运行测试查看
python test_prompt_version.py
```
