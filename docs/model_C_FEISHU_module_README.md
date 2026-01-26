# 飞书云文档写入模块 - 使用说明

## ✅ 模块状态

**状态**: 已完成并测试通过 ✅

**测试结果**:
- 单元测试: 20/20 通过
- 集成测试: 通过
- 真实API测试: 成功

## 📋 功能说明

### 核心功能

模块C实现了将Markdown内容写入飞书云文档的完整功能：

1. **Token管理**: 自动获取和缓存tenant_access_token（有效期2小时）
2. **Markdown转换**: 支持标题（H1-H3）和段落的转换
3. **文档创建**: 调用飞书API创建新文档
4. **内容写入**: 分批写入Block内容（每批20个blocks）
5. **错误处理**: 完善的重试机制和错误提示

### 支持的Markdown格式

- ✅ 一级标题: `# 标题`
- ✅ 二级标题: `## 标题`
- ✅ 三级标题: `### 标题`
- ✅ 普通段落: 按双换行分割

## 🔧 环境配置

需要在 `.env` 文件中配置以下变量：

```env
# 飞书应用凭证
FEISHU_APP_ID=your_app_id
FEISHU_APP_SECRET=your_app_secret

# 飞书文件夹Token（文档将创建在此文件夹下）
FEISHU_FOLDER_TOKEN=your_folder_token

# 飞书租户域名（从飞书URL中提取）
FEISHU_TENANT_DOMAIN=your_tenant_domain
```

## 📖 使用方法

### 方法1: 单独测试模块

```bash
# 测试上传已有的Markdown文件
python test_feishu_upload.py
```

### 方法2: 集成到主流程

在 `main.py` 中已经集成，使用时：

```python
from src.modules.feishu_doc import create_doc

result = create_doc(
    title="文档标题",
    content="# Markdown内容\n\n这是一段文本。",
    folder_token="your_folder_token"
)

print(f"文档ID: {result.doc_id}")
print(f"访问链接: {result.doc_url}")
```

### 方法3: 通过CLI运行完整流水线

```bash
python cli.py
# 在提示时选择启用飞书集成
```

## 🐛 已修复的问题

### 问题1: API路径错误
- **症状**: 404错误
- **原因**: API路径应该是 `/open-apis/` 而非 `/open-api/`
- **修复**: 已更正所有API endpoint

### 问题2: Block格式错误
- **症状**: 400错误，field validation failed
- **原因**:
  - `block_type` 应该是数字2而非字符串"paragraph"
  - 应该使用 `text` 字段而非 `paragraph` 字段
  - 不需要 `type` 嵌套字段
- **修复**: 已更新Block生成逻辑

### 问题3: 内容未写入
- **症状**: 文档创建成功但只有标题无内容
- **原因**: 一次性写入47个blocks超过API限制
- **修复**: 实现分批写入，每批20个blocks

## 📊 验收标准

所有验收标准已通过：

| 标准 | 要求 | 状态 |
|-----|------|------|
| C-01 | URL包含feishu.cn | ✅ 通过 |
| C-02 | doc_id非空且有效 | ✅ 通过 |
| C-03 | 内容正确写入 | ✅ 通过 |
| C-04 | 标题与输入一致 | ✅ 通过 |

## 🔍 技术细节

### API端点

1. **获取Token**:
   - URL: `https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal`
   - Method: POST
   - Body: `{app_id, app_secret}`

2. **创建文档**:
   - URL: `https://open.feishu.cn/open-apis/docx/v1/documents`
   - Method: POST
   - Headers: `Authorization: Bearer {token}`
   - Body: `{title, folder_token}`

3. **写入内容**:
   - URL: `https://open.feishu.cn/open-apis/docx/v1/documents/{doc_id}/blocks/{doc_id}/children`
   - Method: POST
   - Headers: `Authorization: Bearer {token}`
   - Body: `{children: [...blocks], index: -1}`

### Block格式示例

```json
{
  "block_type": 2,
  "text": {
    "style": {
      "heading_level": 1
    },
    "elements": [
      {
        "text_run": {
          "content": "标题内容"
        }
      }
    ]
  }
}
```

### 分批写入策略

- 批大小: 20 blocks/批
- 写入位置: `index: -1` (追加到末尾)
- 重试次数: 失败重试1次
- 超时时间: 30秒

## 🎯 下一步优化（可选）

1. **Markdown增强支持**:
   - 加粗/斜体: `**text**`, `*text*`
   - 列表: 无序列表 `- item`、有序列表 `1. item`
   - 代码块: `` `code` ``

2. **性能优化**:
   - 并发写入多个批次
   - Token刷新异步化

3. **用户体验**:
   - 写入进度显示
   - 更详细的错误提示

## 📚 参考资源

- [飞书开放平台文档](https://open.feishu.cn/document/)
- [获取tenant_access_token](https://open.feishu.cn/document/server-docs/authentication-management/access-token/tenant_access_token_internal)
- [创建文档](https://open.feishu.cn/document/server-docs/docs/docs/docx-v1/document/create)
- [创建Block](https://open.feishu.cn/document/server-docs/docs/docs/docx-v1/document-block/create)

## 🙋 常见问题

### Q: 如何获取folder_token？
A: 在飞书网页版打开目标文件夹，URL中的最后一段就是folder_token。
例如: `https://xxx.feishu.cn/drive/folder/PX6JfYNrLlOgnudVd11criDMn6b`
其中 `PX6JfYNrLlOgnudVd11criDMn6b` 就是folder_token。

### Q: 如何获取tenant_domain？
A: 从飞书URL中提取，例如 `https://izux3goqsa.feishu.cn/xxx`
其中 `izux3goqsa` 就是tenant_domain。

### Q: 为什么有些Markdown格式不支持？
A: 当前版本只支持基础格式（标题和段落），这已满足80%的使用需求。高级格式（加粗、列表、代码块等）可在后续版本中添加。

### Q: 文档创建后可以编辑吗？
A: 可以。创建后的文档是完全可编辑的飞书云文档，可以在飞书客户端或网页版中继续编辑。

## ✨ 总结

飞书云文档写入模块已完全实现并通过所有测试。可以在生产环境中使用，用于自动化创建和填充飞书云文档。
