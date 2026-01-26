# 模块 D：飞书多维表格 - 实施计划（测试驱动开发）

> 📋 **计划要点总结**
>
> **核心特点**
> - 测试驱动开发：先写 10 个测试用例，再实现代码
> - 复用模块 C：直接复用 `FeishuTokenManager`，节省开发时间
> - 完整验证：包含字段验证、类型检查、枚举值校验
>
> **实施步骤（7 步）**
> 1. 先写测试 - 10 个测试用例（D-01、D-02、D-03 + 7 个边界测试）
> 2. 运行测试 - 验证全部失败（功能未实现）
> 3. 实现代码 - 按测试需求实现最小可行功能
> 4. 再次测试 - 逐步让测试通过
> 5. 检查覆盖率 - 目标 ≥ 80%
> 6. 集成验证 - 与 main.py 流程集成
> 7. 真实 API - 可选的真实环境测试
>
> **关键文件**
> - `tests/test_feishu_table.py` - 10 个单元测试
> - `src/modules/feishu_table.py` - 完整实现（~150 行）
> - `test_feishu_table_real.py` - 真实 API 验证脚本
>
> **预计时间**：1.5-2 小时（包括测试编写、代码实现、验证）

---

## 一、目标

实现"模块 D：飞书多维表格"功能，向飞书多维表格插入内容生产记录，支持字段验证和错误处理。

---

## 二、核心功能

### 接口定义

```python
def insert_record(fields: dict) -> str:
    """
    插入多维表格记录

    Args:
        fields: 字段字典，必填字段包括：
            - 选题名称: str
            - 文章链接: str
            - 创建时间: int (毫秒时间戳)
            - 状态: str ("草稿" / "待审核" / "已发布")

    Returns:
        记录 ID (字符串)

    Raises:
        ValueError: 必填字段缺失或无效
        RuntimeError: API调用失败
    """
```

### 验收标准

| 编号 | 描述 |
|------|------|
| D-01 | 正常插入时返回非空 `record_id` |
| D-02 | 字段值正确写入（通过 Mock 验证） |
| D-03 | 必填字段缺失时抛出 `ValueError` |

---

## 三、技术实现方案

### 3.1 飞书多维表格 API 调用流程

```
1. 获取 tenant_access_token
   └─ 复用模块 C 的 FeishuTokenManager

2. 验证必填字段
   └─ 选题名称、文章链接、创建时间、状态
   └─ 验证字段类型和枚举值

3. 插入记录
   └─ POST /open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records
   └─ Headers: Authorization: Bearer {access_token}
   └─ Body: {"fields": {...}}

4. 返回 record_id
   └─ 从响应中提取 data.record.record_id
```

### 3.2 模块架构

**文件**: `src/modules/feishu_table.py`

**核心组件**：

1. **复用 FeishuTokenManager**
   - 从 `feishu_doc.py` 导入
   - 无需重复实现

2. **字段验证函数**
   - `_validate_required_fields(fields: dict)`: 检查必填字段
   - `_validate_field_types(fields: dict)`: 检查字段类型
   - `_validate_field_values(fields: dict)`: 检查枚举值

3. **API 调用函数**
   - `_insert_record_api(access_token, app_token, table_id, fields)`: 调用飞书 API

4. **公共接口**
   - `insert_record(fields: dict) -> str`: 主函数

### 3.3 环境变量配置

需要在 `.env` 中配置：

```bash
# 已有（可复用）
FEISHU_APP_ID=cli_a80711ecf739501c
FEISHU_APP_SECRET=OAn5WYMgPMCNF7uwipPYDS5s5GvMid1k

# 多维表格专用
FEISHU_BITABLE_APP_TOKEN=JlaybPSbia92u8sNZ7UcRBJdnec
FEISHU_BITABLE_TABLE_ID=your-table-id-here  # 需要获取
```

### 3.4 错误处理策略

| 异常类型 | 触发条件 | 处理方式 | 重试 |
|----------|----------|----------|------|
| `ValueError` | 必填字段缺失 | 立即抛出 | ❌ |
| `ValueError` | 字段类型错误 | 立即抛出 | ❌ |
| `ValueError` | 枚举值无效 | 立即抛出 | ❌ |
| `RuntimeError` | 认证失败 | 抛出明确错误信息 | ❌ |
| `TimeoutError` | 请求超时(>30s) | 日志 + 重试 | ✅ 1次 |
| `RuntimeError` | 网络错误 | 日志 + 重试 | ✅ 1次 |
| `RuntimeError` | API限流(429) | 等待后重试 | ✅ 3次 |

---

## 四、测试驱动开发（TDD）实施步骤

### Step 1: 编写单元测试（先写测试）⭐

**文件**: `tests/test_feishu_table.py`

#### 1.1 测试结构

```python
import os
import pytest
from unittest.mock import Mock, patch

from src.modules.feishu_table import insert_record


class TestInsertRecord:
    """insert_record 核心验收测试"""

    def setup_method(self):
        """每个测试前准备环境变量"""
        pass
```

#### 1.2 编写验收测试（D-01、D-02、D-03）

**D-01: 正常插入返回非空 record_id**

```python
@patch.dict(os.environ, {
    "FEISHU_APP_ID": "test_app_id",
    "FEISHU_APP_SECRET": "test_app_secret",
    "FEISHU_BITABLE_APP_TOKEN": "test_app_token",
    "FEISHU_BITABLE_TABLE_ID": "test_table_id"
})
@patch('src.modules.feishu_table.requests.post')
def test_insert_record_returns_valid_record_id(self, mock_post):
    """D-01: 正常插入时返回非空 record_id"""
    # Mock token 响应
    mock_token_response = Mock()
    mock_token_response.status_code = 200
    mock_token_response.json.return_value = {
        "code": 0,
        "tenant_access_token": "test_token",
        "expire": 7200
    }

    # Mock 插入响应
    mock_insert_response = Mock()
    mock_insert_response.status_code = 200
    mock_insert_response.json.return_value = {
        "code": 0,
        "data": {
            "record": {
                "record_id": "rec_test_123"
            }
        }
    }

    mock_post.side_effect = [mock_token_response, mock_insert_response]

    fields = {
        "选题名称": "测试选题",
        "文章链接": "https://example.com/doc",
        "创建时间": 1704067200000,
        "状态": "草稿"
    }

    record_id = insert_record(fields)

    assert record_id is not None
    assert record_id != ""
    assert record_id == "rec_test_123"
```

**D-02: 字段值正确写入（Mock 验证）**

```python
@patch.dict(os.environ, {...})
@patch('src.modules.feishu_table.requests.post')
def test_insert_record_writes_fields_correctly(self, mock_post):
    """D-02: 字段值正确写入"""
    # Setup mocks...

    test_fields = {
        "选题名称": "AI产品经理复盘",
        "文章链接": "https://feishu.cn/docs/xxx",
        "创建时间": 1704067200000,
        "状态": "草稿"
    }

    insert_record(test_fields)

    # 验证 API 调用
    insert_call = mock_post.call_args_list[1]
    insert_payload = insert_call[1]['json']

    assert 'fields' in insert_payload
    fields_data = insert_payload['fields']

    assert fields_data["选题名称"] == "AI产品经理复盘"
    assert fields_data["文章链接"] == "https://feishu.cn/docs/xxx"
    assert fields_data["创建时间"] == 1704067200000
    assert fields_data["状态"] == "草稿"
```

**D-03: 必填字段缺失时抛出错误**

```python
def test_insert_record_raises_on_missing_required_field(self):
    """D-03: 必填字段缺失时抛出 ValueError"""
    # 缺少"选题名称"
    fields = {
        "文章链接": "https://example.com",
        "创建时间": 1704067200000,
        "状态": "草稿"
    }

    with pytest.raises(ValueError, match="必填字段缺失"):
        insert_record(fields)

    # 缺少"文章链接"
    fields = {
        "选题名称": "测试",
        "创建时间": 1704067200000,
        "状态": "草稿"
    }

    with pytest.raises(ValueError, match="必填字段缺失"):
        insert_record(fields)
```

#### 1.3 其他测试用例

**字段类型验证**

```python
def test_insert_record_validates_field_types(self):
    """创建时间必须是整数"""
    fields = {
        "选题名称": "测试",
        "文章链接": "https://example.com",
        "创建时间": "invalid_timestamp",  # 应该是 int
        "状态": "草稿"
    }

    with pytest.raises(ValueError, match="创建时间必须是整数"):
        insert_record(fields)
```

**枚举值验证**

```python
def test_insert_record_validates_enum_values(self):
    """状态必须是有效枚举值"""
    fields = {
        "选题名称": "测试",
        "文章链接": "https://example.com",
        "创建时间": 1704067200000,
        "状态": "无效状态"  # 应该是 "草稿"/"待审核"/"已发布"
    }

    with pytest.raises(ValueError, match="无效的状态值"):
        insert_record(fields)
```

**环境变量缺失**

```python
@patch.dict(os.environ, {}, clear=True)
def test_insert_record_raises_on_missing_env_vars(self):
    """环境变量缺失时抛出错误"""
    fields = {
        "选题名称": "测试",
        "文章链接": "https://example.com",
        "创建时间": 1704067200000,
        "状态": "草稿"
    }

    with pytest.raises(ValueError, match="请在环境变量中配置"):
        insert_record(fields)
```

**认证失败处理**

```python
@patch.dict(os.environ, {...})
@patch('src.modules.feishu_table.requests.post')
def test_insert_record_raises_on_auth_failure(self, mock_post):
    """认证失败时抛出 RuntimeError"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "code": 99991663,
        "msg": "app access token invalid"
    }

    mock_post.return_value = mock_response

    fields = {...}

    with pytest.raises(RuntimeError, match="飞书认证失败"):
        insert_record(fields)
```

**网络错误重试**

```python
@patch.dict(os.environ, {...})
@patch('src.modules.feishu_table.requests.post')
def test_insert_record_retries_on_network_error(self, mock_post):
    """网络错误时重试机制"""
    import requests

    # 第一次失败，第二次成功
    mock_post.side_effect = [
        mock_token_response,
        requests.exceptions.RequestException("Network error"),
        mock_insert_response
    ]

    fields = {...}
    record_id = insert_record(fields)

    assert record_id == "rec_test_123"
```

**超时处理**

```python
@patch.dict(os.environ, {...})
@patch('src.modules.feishu_table.requests.post')
def test_insert_record_timeout_handling(self, mock_post):
    """请求超时处理"""
    import requests

    mock_post.side_effect = requests.exceptions.Timeout("Request timeout")

    fields = {...}

    with pytest.raises(RuntimeError, match="请求超时"):
        insert_record(fields)
```

> 📝 **预期测试数量**: 10 个测试用例

---

### Step 2: 运行测试（应该全部失败）✅

```bash
source .venv/bin/activate
pytest tests/test_feishu_table.py -v
```

**预期结果**: 所有测试失败（因为功能尚未实现）

---

### Step 3: 实现最小可行代码（让测试通过）⭐

**文件**: `src/modules/feishu_table.py`

#### 3.1 导入和常量定义

```python
"""模块D：飞书多维表格"""

import os
import time
from typing import Dict
import requests

# 复用模块 C 的 Token Manager
from .feishu_doc import FeishuTokenManager


# 必填字段定义
REQUIRED_FIELDS = ["选题名称", "文章链接", "创建时间", "状态"]

# 状态枚举值
VALID_STATUSES = ["草稿", "待审核", "已发布"]
```

#### 3.2 字段验证函数

```python
def _validate_required_fields(fields: dict) -> None:
    """
    验证必填字段

    Args:
        fields: 字段字典

    Raises:
        ValueError: 必填字段缺失
    """
    for field in REQUIRED_FIELDS:
        if field not in fields or not fields[field]:
            raise ValueError(f"必填字段缺失: {field}")


def _validate_field_types(fields: dict) -> None:
    """
    验证字段类型

    Args:
        fields: 字段字典

    Raises:
        ValueError: 字段类型错误
    """
    # 创建时间必须是整数
    if not isinstance(fields.get("创建时间"), int):
        raise ValueError("创建时间必须是整数（毫秒级时间戳）")


def _validate_field_values(fields: dict) -> None:
    """
    验证字段值（枚举值）

    Args:
        fields: 字段字典

    Raises:
        ValueError: 枚举值无效
    """
    status = fields.get("状态")
    if status not in VALID_STATUSES:
        raise ValueError(f"无效的状态值: {status}，有效值为: {', '.join(VALID_STATUSES)}")
```

#### 3.3 API 调用函数

```python
def _insert_record_api(
    access_token: str,
    app_token: str,
    table_id: str,
    fields: dict
) -> str:
    """
    调用飞书 API 插入记录

    Args:
        access_token: 访问令牌
        app_token: 多维表格 app_token
        table_id: 表格 table_id
        fields: 字段数据

    Returns:
        记录 ID

    Raises:
        RuntimeError: API 调用失败
    """
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "fields": fields
    }

    max_retries = 1
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=30
            )

            if response.status_code == 429:
                # API限流
                if attempt < 3:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
                raise RuntimeError("飞书API限流，请稍后重试")

            if response.status_code != 200:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("msg", "未知错误")
                    raise RuntimeError(f"插入记录失败，HTTP状态码: {response.status_code}, 错误信息: {error_msg}")
                except:
                    raise RuntimeError(f"插入记录失败，HTTP状态码: {response.status_code}")

            data = response.json()

            if data.get("code") != 0:
                error_msg = data.get("msg", "未知错误")
                raise RuntimeError(f"插入记录失败: {error_msg}")

            # 提取 record_id
            record_id = data.get("data", {}).get("record", {}).get("record_id")

            if not record_id:
                raise RuntimeError("响应中未包含 record_id")

            return record_id

        except requests.exceptions.Timeout:
            if attempt < max_retries:
                time.sleep(2)
                continue
            raise RuntimeError("请求超时")
        except requests.exceptions.RequestException as e:
            if attempt < max_retries:
                time.sleep(2)
                continue
            raise RuntimeError(f"网络请求失败: {str(e)}")
```

#### 3.4 公共接口函数

```python
def insert_record(fields: dict) -> str:
    """
    插入多维表格记录

    Args:
        fields: 字段字典，必填字段包括：
            - 选题名称: str
            - 文章链接: str
            - 创建时间: int (毫秒时间戳)
            - 状态: str ("草稿" / "待审核" / "已发布")

    Returns:
        记录 ID

    Raises:
        ValueError: 必填字段缺失或无效
        RuntimeError: 认证失败、网络错误或API调用失败
    """
    # 1. 验证字段
    _validate_required_fields(fields)
    _validate_field_types(fields)
    _validate_field_values(fields)

    # 2. 读取环境变量
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    app_token = os.getenv("FEISHU_BITABLE_APP_TOKEN")
    table_id = os.getenv("FEISHU_BITABLE_TABLE_ID")

    if not app_id or not app_secret:
        raise ValueError("请在环境变量中配置 FEISHU_APP_ID 和 FEISHU_APP_SECRET")

    if not app_token:
        raise ValueError("请在环境变量中配置 FEISHU_BITABLE_APP_TOKEN")

    if not table_id:
        raise ValueError("请在环境变量中配置 FEISHU_BITABLE_TABLE_ID")

    # 3. 获取 token
    token_manager = FeishuTokenManager(app_id, app_secret)
    access_token = token_manager.get_token()

    # 4. 调用 API 插入记录
    record_id = _insert_record_api(access_token, app_token, table_id, fields)

    return record_id
```

---

### Step 4: 运行测试（逐步让测试通过）✅

```bash
source .venv/bin/activate
pytest tests/test_feishu_table.py -v
```

**预期结果**: 所有 10 个测试通过

---

### Step 5: 检查测试覆盖率

```bash
pytest tests/test_feishu_table.py --cov=src.modules.feishu_table --cov-report=term-missing
```

**目标**: 覆盖率 ≥ 80%

---

### Step 6: 集成到主流程（验证）

**文件**: `src/main.py`

验证第 135-159 行的调用逻辑是否正确：

```python
record_id = feishu_table.insert_record({
    "选题名称": topic,
    "文章链接": doc_result.doc_url,
    "创建时间": int(time.time() * 1000),
    "状态": "草稿"
})
```

> ✅ 无需修改，接口已对齐。

---

### Step 7: 真实 API 验证（可选）

创建测试脚本验证真实 API：

**文件**: `test_feishu_table_real.py`

```python
#!/usr/bin/env python3
"""测试飞书多维表格真实 API"""

import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

from src.modules.feishu_table import insert_record

def main():
    print("=" * 70)
    print("飞书多维表格写入模块 - 真实测试")
    print("=" * 70)

    # 检查环境变量
    app_token = os.getenv("FEISHU_BITABLE_APP_TOKEN")
    table_id = os.getenv("FEISHU_BITABLE_TABLE_ID")

    print(f"\n🔧 环境配置:")
    print(f"   APP_TOKEN: {'✅' if app_token else '❌'}")
    print(f"   TABLE_ID: {'✅' if table_id else '❌'}")

    if not table_id or table_id == "your-table-id-here":
        print("\n❌ 请先配置 FEISHU_BITABLE_TABLE_ID")
        return 1

    # 测试数据
    fields = {
        "选题名称": "测试选题 - API验证",
        "文章链接": "https://izux3goqsa.feishu.cn/docx/test123",
        "创建时间": int(time.time() * 1000),
        "状态": "草稿"
    }

    print(f"\n📝 测试数据:")
    for key, value in fields.items():
        print(f"   {key}: {value}")

    try:
        print(f"\n🚀 开始插入记录...")
        record_id = insert_record(fields)

        print(f"\n✅ 记录插入成功！")
        print(f"   记录ID: {record_id}")
        print(f"\n请在飞书多维表格中查看新记录")

        return 0

    except ValueError as e:
        print(f"\n❌ 参数错误: {e}")
        return 1
    except RuntimeError as e:
        print(f"\n❌ API调用失败: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ 未知错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
```

---

## 五、关键文件清单

### 需要创建的文件

| 文件 | 说明 |
|------|------|
| `tests/test_feishu_table.py` | 单元测试（10 个测试用例） |
| `test_feishu_table_real.py` | 真实 API 验证脚本（可选） |

### 需要修改的文件

| 文件 | 说明 |
|------|------|
| `src/modules/feishu_table.py` | 完整实现（当前只有接口） |
| `.env` | 可能需要配置 `FEISHU_BITABLE_TABLE_ID` |

### 无需修改的文件

- `src/models.py` (无需新增数据结构)
- `src/main.py` (已有调用逻辑)
- `src/modules/feishu_doc.py` (复用 `FeishuTokenManager`)

---

## 六、验证方案

### 6.1 单元测试验证

```bash
# 运行所有测试
pytest tests/test_feishu_table.py -v

# 运行特定测试
pytest tests/test_feishu_table.py::TestInsertRecord::test_insert_record_returns_valid_record_id -v

# 查看覆盖率
pytest tests/test_feishu_table.py --cov=src.modules.feishu_table --cov-report=term-missing
```

### 6.2 真实 API 验证（可选）

```bash
# 前提：需要先获取并配置 FEISHU_BITABLE_TABLE_ID
python test_feishu_table_real.py
```

### 6.3 端到端流程验证

```bash
# 使用 CLI 运行完整流程
python cli.py

# 启用飞书集成，验证：
# 1. 文章生成成功
# 2. 文档创建成功
# 3. 表格记录插入成功
```

---

## 七、获取 TABLE_ID 的方法

由于 `.env` 中的 `FEISHU_BITABLE_TABLE_ID` 尚未配置，需要通过以下方式获取：

### 方法 1: 通过飞书 API 获取

```bash
# 使用 curl 获取表格列表
curl -X GET \
  'https://open.feishu.cn/open-apis/bitable/v1/apps/JlaybPSbia92u8sNZ7UcRBJdnec/tables' \
  -H 'Authorization: Bearer {your_token}'
```

### 方法 2: 从飞书网页获取

1. 在飞书中打开多维表格
2. 点击表格标签页
3. 从 URL 中提取 `table_id`
4. 更新到 `.env` 文件

---

## 八、潜在风险与应对

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| TABLE_ID 未配置 | 无法运行 | 提供获取方法 + 明确错误提示 |
| 飞书 API 限流 | 频繁插入时触发 429 | 实现指数退避重试 + 请求日志 |
| Token 过期 | 长运行任务失效 | 复用模块 C 的缓存机制 |
| 网络超时 | API 调用失败 | 30 秒超时 + 重试 1 次 |
| 字段类型不匹配 | 插入失败 | 预先验证字段类型 |

---

## 九、成功标准

- ✅ 所有单元测试通过（10/10，覆盖率 ≥ 80%）
- ✅ 3 个验收用例（D-01 至 D-03）全部通过
- ✅ 与 `main.py` 集成成功，流水线可运行
- ✅ 错误处理清晰，异常有明确提示
- ✅ 代码风格符合项目规范（参考 `feishu_doc.py`）

---

## 十、预计时间

| 任务 | 预计时间 |
|------|----------|
| Step 1: 编写测试 | 40 分钟 |
| Step 2: 运行测试（失败） | 5 分钟 |
| Step 3: 实现代码 | 30 分钟 |
| Step 4: 运行测试（通过） | 10 分钟 |
| Step 5: 检查覆盖率 | 5 分钟 |
| Step 6: 集成验证 | 10 分钟 |
| Step 7: 真实 API 验证 | 15 分钟（可选） |
| **总计** | **1.5-2 小时** |

---

## 十一、后续优化方向（可选）

1. **批量插入**
   - 支持一次插入多条记录
   - 优化性能

2. **字段扩展**
   - 支持可选字段（素材来源摘要、目标平台等）
   - 动态字段映射

3. **记录更新**
   - 实现 `update_record()` 函数
   - 支持修改已有记录

4. **记录查询**
   - 实现 `query_records()` 函数
   - 根据条件查询记录
