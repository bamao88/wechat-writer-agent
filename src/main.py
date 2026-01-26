"""编排层 - 内容生产流水线"""

import time
from typing import Optional
from .modules import retrieval, generator, feishu_doc, feishu_table
from .models import PipelineResult


def run_pipeline(
    topic: str,
    api_key: str,
    notebook_id: Optional[str] = None,
    notebook_url: Optional[str] = None,
    folder_token: Optional[str] = None,
    enable_feishu: bool = False,
    max_retries: int = 1
) -> PipelineResult:
    """
    执行内容生产流水线

    Args:
        topic: 文章主题
        api_key: Anthropic API Key
        notebook_id: NotebookLM 笔记本 ID（可选）
        notebook_url: NotebookLM 笔记本 URL（可选）
        folder_token: 飞书文件夹 Token（可选）
        enable_feishu: 是否启用飞书集成（默认 False）
        max_retries: 失败重试次数（默认 1 次）

    Returns:
        流水线结果

    Raises:
        RuntimeError: 检索或生成失败
        ValueError: 参数错误

    Note:
        异常处理策略：
        - 检索失败：重试 max_retries 次，仍失败则抛异常
        - 检索无结果：继续，source_summary 标注"无检索结果"
        - 云文档失败：重试 max_retries 次，仍失败则记录日志但不抛异常
        - 表格失败：记录日志，返回 record_id=None
    """
    # 前置验证参数
    if not api_key or not api_key.strip():
        raise ValueError("请提供 API Key")

    if not topic or not topic.strip():
        raise ValueError("请提供文章主题")

    print(f"\n{'='*60}")
    print(f"🚀 开始内容生产流水线")
    print(f"{'='*60}")
    print(f"选题: {topic}")
    print(f"飞书集成: {'✅ 启用' if enable_feishu else '❌ 禁用'}")

    # 1. 检索阶段
    print(f"\n{'—'*60}")
    print("📚 阶段 1/4: 检索素材")
    print(f"{'—'*60}")

    search_results = None
    for attempt in range(max_retries + 1):
        try:
            search_results = retrieval.search(
                query=topic,
                notebook_id=notebook_id,
                notebook_url=notebook_url
            )
            print(f"✅ 检索成功，获得 {len(search_results)} 条结果")
            break
        except Exception as e:
            if attempt < max_retries:
                print(f"⚠️  检索失败（第 {attempt + 1} 次尝试），重试中...")
                time.sleep(2)
            else:
                print(f"❌ 检索失败: {str(e)}")
                # 继续流程，使用空结果
                search_results = []
                print("⏭️  继续流程，不使用检索结果")

    if search_results is None:
        search_results = []

    # 2. 生成阶段
    print(f"\n{'—'*60}")
    print("✍️  阶段 2/4: 生成文章")
    print(f"{'—'*60}")

    article = generator.generate(
        topic=topic,
        search_results=search_results,
        api_key=api_key,
        notebook_id=notebook_id,
        notebook_url=notebook_url
    )

    print(f"✅ 文章生成完成")
    print(f"   标题: {article.title}")
    print(f"   字数: {len(article.content)} 字符")
    print(f"   素材: {article.source_summary}")

    # 3. 飞书云文档阶段（可选）
    print(f"\n{'—'*60}")
    print("📄 阶段 3/4: 创建飞书云文档")
    print(f"{'—'*60}")

    doc_result = None
    if enable_feishu and folder_token:
        for attempt in range(max_retries + 1):
            try:
                doc_result = feishu_doc.create_doc(
                    title=article.title,
                    content=article.content,
                    folder_token=folder_token
                )
                print(f"✅ 文档创建成功: {doc_result.doc_url}")
                break
            except NotImplementedError:
                print("⚠️  飞书云文档功能暂未实现，跳过此步骤")
                break
            except Exception as e:
                if attempt < max_retries:
                    print(f"⚠️  文档创建失败（第 {attempt + 1} 次尝试），重试中...")
                    time.sleep(2)
                else:
                    print(f"❌ 文档创建失败: {str(e)}")
                    print("⏭️  继续流程，文章将不会上传到飞书")
    else:
        if enable_feishu:
            print("⚠️  未提供 folder_token，跳过文档创建")
        else:
            print("⏭️  飞书集成已禁用，跳过此步骤")

    # 4. 飞书多维表格阶段（可选）
    print(f"\n{'—'*60}")
    print("📊 阶段 4/4: 插入多维表格记录")
    print(f"{'—'*60}")

    record_id = None
    if enable_feishu and doc_result:
        try:
            record_id = feishu_table.insert_record({
                "选题名称": topic,
                "文章链接": doc_result.doc_url,
                "创建时间": int(time.time() * 1000),
                "状态": "草稿"
            })
            print(f"✅ 记录插入成功: {record_id}")
        except NotImplementedError:
            print("⚠️  飞书多维表格功能暂未实现，跳过此步骤")
        except Exception as e:
            print(f"❌ 记录插入失败: {str(e)}")
            print("⏭️  继续流程，记录不会保存到表格")
    else:
        if enable_feishu:
            print("⏭️  无文档结果，跳过表格记录")
        else:
            print("⏭️  飞书集成已禁用，跳过此步骤")

    # 返回结果
    print(f"\n{'='*60}")
    print("🎉 流水线执行完成")
    print(f"{'='*60}")

    return PipelineResult(
        article=article,
        doc_result=doc_result,
        record_id=record_id
    )
