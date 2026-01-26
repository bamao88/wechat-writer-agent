"""模块C：飞书云文档写入"""

import os
import re
import time
from typing import Dict, List, Optional
import requests

from ..models import DocResult


# Token缓存（模块级）
_token_cache: Dict[str, any] = {
    "token": None,
    "expires_at": 0
}


class FeishuTokenManager:
    """飞书Token管理器"""

    def __init__(self, app_id: str, app_secret: str):
        """
        初始化Token管理器

        Args:
            app_id: 飞书应用ID
            app_secret: 飞书应用密钥
        """
        if not app_id or not app_secret:
            raise ValueError("app_id 和 app_secret 不能为空")

        self.app_id = app_id
        self.app_secret = app_secret
        self.token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"

    def get_token(self) -> str:
        """
        获取有效的tenant_access_token（含缓存）

        Returns:
            有效的access token

        Raises:
            RuntimeError: 认证失败或网络错误
        """
        global _token_cache

        # 检查缓存是否有效（预留100秒缓冲）
        current_time = time.time()
        if _token_cache["token"] and _token_cache["expires_at"] > current_time + 100:
            return _token_cache["token"]

        # 刷新token
        return self._refresh_token()

    def _refresh_token(self) -> str:
        """
        刷新access token

        Returns:
            新的access token

        Raises:
            RuntimeError: 认证失败或网络错误
        """
        global _token_cache

        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }

        max_retries = 1
        for attempt in range(max_retries + 1):
            try:
                response = requests.post(
                    self.token_url,
                    json=payload,
                    timeout=30
                )

                if response.status_code != 200:
                    raise RuntimeError(f"获取token失败，HTTP状态码: {response.status_code}")

                data = response.json()

                if data.get("code") != 0:
                    error_msg = data.get("msg", "未知错误")
                    raise RuntimeError(f"飞书认证失败: {error_msg}")

                token = data.get("tenant_access_token")
                expires_in = data.get("expire", 7200)  # 默认2小时

                if not token:
                    raise RuntimeError("响应中未包含tenant_access_token")

                # 更新缓存
                _token_cache["token"] = token
                _token_cache["expires_at"] = time.time() + expires_in

                return token

            except requests.exceptions.Timeout:
                if attempt < max_retries:
                    time.sleep(2)
                    continue
                raise RuntimeError("获取token超时")
            except requests.exceptions.RequestException as e:
                if attempt < max_retries:
                    time.sleep(2)
                    continue
                raise RuntimeError(f"网络请求失败: {str(e)}")


class MarkdownToBlockConverter:
    """Markdown到飞书Block格式转换器"""

    def convert(self, markdown_text: str) -> List[Dict]:
        """
        将Markdown文本转换为飞书Block数组

        支持的格式：
        - 一级标题: # 标题
        - 二级标题: ## 标题
        - 三级标题: ### 标题
        - 普通段落: 按双换行分割

        Args:
            markdown_text: Markdown文本

        Returns:
            飞书Block数组
        """
        if not markdown_text or not markdown_text.strip():
            return []

        blocks = []

        # 按双换行分割段落
        paragraphs = re.split(r'\n\s*\n', markdown_text.strip())

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # 检测标题级别
            heading_match = re.match(r'^(#{1,3})\s+(.+)$', para)
            if heading_match:
                level = len(heading_match.group(1))
                title_text = heading_match.group(2).strip()
                blocks.append(self._create_heading_block(title_text, level))
            else:
                # 普通段落
                blocks.append(self._create_text_block(para))

        return blocks

    def _create_heading_block(self, text: str, level: int) -> Dict:
        """
        创建标题Block

        Args:
            text: 标题文本
            level: 标题级别 (1-3)

        Returns:
            标题Block
        """
        return {
            "block_type": 2,  # 2表示text类型
            "text": {
                "style": {
                    "heading_level": level
                },
                "elements": [
                    {
                        "text_run": {
                            "content": text
                        }
                    }
                ]
            }
        }

    def _create_text_block(self, text: str) -> Dict:
        """
        创建普通段落Block

        Args:
            text: 段落文本

        Returns:
            段落Block
        """
        return {
            "block_type": 2,  # 2表示text类型
            "text": {
                "elements": [
                    {
                        "text_run": {
                            "content": text
                        }
                    }
                ]
            }
        }


def create_doc(
    title: str,
    content: str,
    folder_token: str
) -> DocResult:
    """
    创建飞书云文档并写入Markdown内容

    Args:
        title: 文档标题
        content: 文档内容（Markdown格式）
        folder_token: 文件夹Token

    Returns:
        文档结果（包含doc_id和doc_url）

    Raises:
        ValueError: 参数缺失或无效
        RuntimeError: 认证失败、网络错误或API调用失败
    """
    # 参数验证
    if not title or not title.strip():
        raise ValueError("文档标题不能为空")

    if not content or not content.strip():
        raise ValueError("文档内容不能为空")

    if not folder_token or not folder_token.strip():
        raise ValueError("folder_token不能为空")

    # 从环境变量读取配置
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    tenant_domain = os.getenv("FEISHU_TENANT_DOMAIN")

    if not app_id or not app_secret:
        raise ValueError("请在环境变量中配置 FEISHU_APP_ID 和 FEISHU_APP_SECRET")

    if not tenant_domain:
        raise ValueError("请在环境变量中配置 FEISHU_TENANT_DOMAIN")

    # 获取access token
    token_manager = FeishuTokenManager(app_id, app_secret)
    access_token = token_manager.get_token()

    # 创建文档
    doc_id = _create_document(access_token, title.strip(), folder_token.strip())

    # 转换Markdown为Block格式
    converter = MarkdownToBlockConverter()
    blocks = converter.convert(content)

    # 写入内容
    if blocks:
        _write_blocks(access_token, doc_id, blocks)

    # 构造访问URL
    doc_url = f"https://{tenant_domain}.feishu.cn/docx/{doc_id}"

    return DocResult(doc_id=doc_id, doc_url=doc_url)


def _create_document(access_token: str, title: str, folder_token: str) -> str:
    """
    调用飞书API创建文档

    Args:
        access_token: 访问令牌
        title: 文档标题
        folder_token: 文件夹Token

    Returns:
        文档ID

    Raises:
        RuntimeError: API调用失败
    """
    url = "https://open.feishu.cn/open-apis/docx/v1/documents"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "title": title,
        "folder_token": folder_token
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
                if attempt < 3:  # 限流时最多重试3次
                    wait_time = 2 ** attempt  # 指数退避
                    time.sleep(wait_time)
                    continue
                raise RuntimeError("飞书API限流，请稍后重试")

            if response.status_code == 403:
                raise RuntimeError("文件夹权限不足，请检查 folder_token 是否有效")

            if response.status_code != 200:
                raise RuntimeError(f"创建文档失败，HTTP状态码: {response.status_code}")

            data = response.json()

            if data.get("code") != 0:
                error_msg = data.get("msg", "未知错误")
                raise RuntimeError(f"创建文档失败: {error_msg}")

            doc_id = data.get("data", {}).get("document", {}).get("document_id")

            if not doc_id:
                raise RuntimeError("响应中未包含document_id")

            return doc_id

        except requests.exceptions.Timeout:
            if attempt < max_retries:
                time.sleep(2)
                continue
            raise RuntimeError("创建文档超时")
        except requests.exceptions.RequestException as e:
            if attempt < max_retries:
                time.sleep(2)
                continue
            raise RuntimeError(f"网络请求失败: {str(e)}")


def _write_blocks(access_token: str, document_id: str, blocks: List[Dict]) -> None:
    """
    写入Block内容到文档（支持分批写入）

    Args:
        access_token: 访问令牌
        document_id: 文档ID
        blocks: Block数组

    Raises:
        RuntimeError: API调用失败
    """
    if not blocks:
        return

    # 分批写入，每批20个blocks
    batch_size = 20
    total_blocks = len(blocks)

    for batch_start in range(0, total_blocks, batch_size):
        batch_end = min(batch_start + batch_size, total_blocks)
        batch_blocks = blocks[batch_start:batch_end]

        _write_blocks_single_batch(access_token, document_id, batch_blocks)


def _write_blocks_single_batch(access_token: str, document_id: str, blocks: List[Dict]) -> None:
    """
    写入单批Block内容到文档

    Args:
        access_token: 访问令牌
        document_id: 文档ID
        blocks: Block数组（单批）

    Raises:
        RuntimeError: API调用失败
    """
    url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks/{document_id}/children"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "children": blocks,
        "index": -1  # -1表示追加到末尾
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
                    raise RuntimeError(f"写入内容失败，HTTP状态码: {response.status_code}, 错误信息: {error_msg}")
                except:
                    raise RuntimeError(f"写入内容失败，HTTP状态码: {response.status_code}, 响应: {response.text[:200]}")

            data = response.json()

            if data.get("code") != 0:
                error_msg = data.get("msg", "未知错误")
                raise RuntimeError(f"写入内容失败: {error_msg}")

            return

        except requests.exceptions.Timeout:
            if attempt < max_retries:
                time.sleep(2)
                continue
            raise RuntimeError("写入内容超时")
        except requests.exceptions.RequestException as e:
            if attempt < max_retries:
                time.sleep(2)
                continue
            raise RuntimeError(f"网络请求失败: {str(e)}")
