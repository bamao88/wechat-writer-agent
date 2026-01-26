# 模块C：飞书云文档写入 - 实施计划

## 一、目标

实现"模块C：飞书云文档写入"功能，创建飞书云文档并写入Markdown内容，返回文档链接。

## 二、核心功能

### 接口定义
```python
def create_doc(
    title: str,
    content: str,
    folder_token: str
) -> DocResult  # 包含 doc_id 和 doc_url
```

### 验收标准
- C-01: 返回的 URL 包含 feishu.cn
- C-02: 返回的 doc_id 非空且有效
- C-03: 文档内容包含输入的内容
- C-04: 文档标题与输入一致

## 三、技术实现方案

### 3.1 飞书API调用流程

```
1. 获取 tenant_access_token
   └─ POST /auth/v3/tenant_access_token/internal
   └─ 有效期2小时，需缓存

2. 创建文档
   └─ POST /docx/v1/documents
   └─ 参数: title, folder_token
   └─ 返回: document_id

3. 写入内容
   └─ POST /docx/v1/documents/{document_id}/blocks
   └─ 参数: Block数组（Markdown转换后的格式）

4. 构造访问URL
   └─ https://{tenant_domain}.feishu.cn/docs/{document_id}
```

### 3.2 模块架构

**文件**: `/Volumes/ExtSSD2601/IP_ZH/wechat-writer-agent/src/modules/feishu_doc.py`

三个核心组件：

1. **FeishuTokenManager** - Token管理
   - `get_token()`: 获取有效token（含缓存）
   - `_refresh_token()`: 刷新过期token
   - 模块级缓存: `_token_cache = {"token": None, "expires_at": 0}`

2. **MarkdownToBlockConverter** - 格式转换
   - `convert(markdown_text: str) -> List[Dict]`: 主转换方法
   - `_create_heading_block()`: 创建标题Block
   - `_create_text_block()`: 创建段落Block

   **支持的格式**（第一阶段）：
   - 一级标题: `# 标题` → heading_level=1
   - 二级标题: `## 标题` → heading_level=2
   - 三级标题: `### 标题` → heading_level=3
   - 普通段落: 按双换行分割

3. **create_doc()** - 公共接口
   - 参数验证
   - Token获取
   - 创建文档
   - 转换并写入内容
   - 返回 DocResult

### 3.3 环境变量配置

需要在 `.env` 中添加：
```env
# 已有
FEISHU_APP_ID=cli_a80711ecf739501c
FEISHU_APP_SECRET=OAn5WYMgPMCNF7uwipPYDS5s5GvMid1k
FEISHU_FOLDER_TOKEN=PX6JfYNrLlOgnudVd11criDMn6b

# 新增
FEISHU_TENANT_DOMAIN=izux3goqsa
```

### 3.4 错误处理策略

| 异常类型 | 触发条件 | 处理方式 | 重试 |
|---------|---------|---------|------|
| ValueError | 参数缺失/无效 | 立即抛出 | ❌ |
| RuntimeError | 认证失败 | 抛出明确错误信息 | ❌ |
| TimeoutError | 请求超时(>30s) | 日志 + 重试 | ✅ 1次 |
| RuntimeError | 网络错误 | 日志 + 重试 | ✅ 1次 |
| RuntimeError | API限流(429) | 等待后重试 | ✅ 3次 |

## 四、实施步骤

### Step 1: 更新依赖 (5分钟)
- [ ] 在 `requirements.txt` 添加 `requests>=2.31.0`
- [ ] 运行 `pip install -r requirements.txt`

### Step 2: 更新环境配置 (2分钟)
- [ ] 在 `.env` 添加 `FEISHU_TENANT_DOMAIN=izux3goqsa`

### Step 3: 实现核心代码 (2-3小时)
- [ ] 实现 `FeishuTokenManager` 类
  - Token获取和缓存逻辑
  - 过期自动刷新
  - 错误处理（认证失败、网络错误）

- [ ] 实现 `MarkdownToBlockConverter` 类
  - 按双换行分割段落
  - 检测标题级别（`^#+\s`）
  - 生成飞书Block格式
  - 处理空内容

- [ ] 实现 `create_doc()` 函数
  - 参数验证（非空检查）
  - 从环境变量读取配置
  - 调用飞书API创建文档
  - 转换并写入内容
  - 构造访问URL
  - 异常处理和重试逻辑

### Step 4: 编写单元测试 (2-3小时)
**文件**: `/Volumes/ExtSSD2601/IP_ZH/wechat-writer-agent/tests/test_feishu_doc.py`

- [ ] `TestFeishuTokenManager` 类
  - `test_get_token_uses_cache` - 验证缓存机制
  - `test_token_refresh_on_expiry` - 验证自动刷新
  - `test_get_token_raises_on_auth_failure` - 认证失败
  - `test_get_token_with_network_retry` - 网络重试

- [ ] `TestMarkdownToBlockConverter` 类
  - `test_convert_simple_paragraph` - 普通段落
  - `test_convert_heading_levels` - 标题转换
  - `test_convert_multiline_content` - 多行内容
  - `test_convert_empty_content` - 空内容
  - `test_convert_preserves_paragraph_breaks` - 段落分割

- [ ] `TestCreateDoc` 类（核心验收测试）
  - `test_create_doc_returns_valid_url` - C-01验收
  - `test_create_doc_returns_valid_doc_id` - C-02验收
  - `test_create_doc_writes_content_correctly` - C-03验收（mock验证）
  - `test_create_doc_sets_title_correctly` - C-04验收（mock验证）
  - `test_create_doc_raises_on_missing_params` - 参数验证
  - `test_create_doc_raises_on_auth_failure` - 认证失败
  - `test_create_doc_retries_on_network_error` - 重试机制
  - `test_create_doc_timeout_handling` - 超时处理

**Mock策略**: 使用 `@patch('src.modules.feishu_doc.requests.post')` 和 `@patch.dict(os.environ, {...})` 来模拟飞书API调用和环境变量。

### Step 5: 运行测试 (30分钟)
- [ ] 运行单元测试: `pytest tests/test_feishu_doc.py -v`
- [ ] 确保所有测试通过
- [ ] 检查测试覆盖率

### Step 6: 集成到主流程 (30分钟)
- [ ] 验证 `src/main.py` 中的调用逻辑（已存在，无需修改）
- [ ] 运行端到端流程测试
- [ ] 验证错误处理和重试逻辑

### Step 7: 集成测试准备（可选，后续执行）
- [ ] 创建 `tests/integration/test_feishu_integration.py`
- [ ] 实现真实环境测试脚本
- [ ] 提供测试指南文档

## 五、关键文件清单

### 需要修改的文件
1. **requirements.txt** - 添加 requests 依赖
2. **.env** - 添加 FEISHU_TENANT_DOMAIN
3. **src/modules/feishu_doc.py** - 完整实现（当前只有接口）

### 需要创建的文件
4. **tests/test_feishu_doc.py** - 单元测试

### 无需修改的文件
- src/models.py (DocResult已定义，满足需求)
- src/main.py (已有调用逻辑和错误处理)

## 六、飞书Block格式示例

### 输入 Markdown
```markdown
# AI产品经理的复盘

2024年，我在AI领域学到了很多。

## 关键收获

最重要的是理解了Prompt Engineering的价值。
```

### 输出 Block数组
```json
[
  {
    "block_type": "paragraph",
    "paragraph": {
      "style": {"heading_level": 1},
      "elements": [
        {"type": "text_run", "text_run": {"content": "AI产品经理的复盘"}}
      ]
    }
  },
  {
    "block_type": "paragraph",
    "paragraph": {
      "elements": [
        {"type": "text_run", "text_run": {"content": "2024年，我在AI领域学到了很多。"}}
      ]
    }
  },
  {
    "block_type": "paragraph",
    "paragraph": {
      "style": {"heading_level": 2},
      "elements": [
        {"type": "text_run", "text_run": {"content": "关键收获"}}
      ]
    }
  },
  {
    "block_type": "paragraph",
    "paragraph": {
      "elements": [
        {"type": "text_run", "text_run": {"content": "最重要的是理解了Prompt Engineering的价值。"}}
      ]
    }
  }
]
```

## 七、验证方案

### 7.1 单元测试验证
```bash
# 运行所有测试
pytest tests/test_feishu_doc.py -v

# 运行特定测试
pytest tests/test_feishu_doc.py::TestCreateDoc::test_create_doc_returns_valid_url -v

# 查看覆盖率
pytest tests/test_feishu_doc.py --cov=src.modules.feishu_doc --cov-report=term-missing
```

### 7.2 集成测试验证（手动，后续执行）
```bash
# 创建测试脚本
python -c "
from src.modules.feishu_doc import create_doc

result = create_doc(
    title='测试文档',
    content='# 测试标题\n\n这是测试内容。',
    folder_token='PX6JfYNrLlOgnudVd11criDMn6b'
)

print(f'文档ID: {result.doc_id}')
print(f'访问链接: {result.doc_url}')
"

# 手动访问 result.doc_url 验证文档是否创建成功
```

### 7.3 端到端流程验证
```bash
# 使用CLI运行完整流程
python cli.py

# 输入选题时启用飞书集成
# 验证文档是否创建并写入表格
```

## 八、潜在风险与应对

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 飞书API限流 | 频繁创建时触发429 | 实现指数退避重试 + 请求日志 |
| Token过期 | 长运行任务失效 | 缓存机制 + 自动刷新（预留100秒缓冲） |
| 网络超时 | API调用失败 | 30秒超时 + 重试1次 |
| 文件夹权限 | folder_token无效 | 捕获403错误，明确提示 |
| Markdown复杂格式 | 高级格式丢失 | 第一阶段只支持基础格式，满足80%需求 |

## 九、成功标准

- ✅ 所有单元测试通过（覆盖率 > 90%）
- ✅ 4个验收用例（C-01至C-04）全部通过
- ✅ 与 main.py 集成成功，流水线可运行
- ✅ 错误处理清晰，异常有明确提示
- ✅ 代码风格符合项目规范（参考 retrieval.py 和 generator.py）

## 十、后续优化方向（第二阶段，可选）

1. **Markdown增强支持**
   - 加粗/斜体: `**text**`, `*text*`
   - 列表: 无序列表 `- item`、有序列表 `1. item`
   - 代码块: `` `code` ``

2. **性能优化**
   - 大文档分块写入
   - Token刷新异步化

3. **集成测试**
   - 自动化集成测试脚本
   - CI/CD集成

4. **错误恢复**
   - 部分写入失败时的增量重试
   - 文档创建成功但写入失败时的恢复机制
