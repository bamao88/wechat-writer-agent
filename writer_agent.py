"""
公众号文章写作 Agent
基于 Claude Agent SDK 和 NotebookLM 实现的智能写作助手
"""
import os
from anthropic import Anthropic
from typing import Optional, List, Dict, Any
from notebooklm_tool import create_notebooklm_tool


class WechatWriterAgent:
    """公众号文章写作 Agent"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "MiniMax-M2.1",
        notebook_id: Optional[str] = None,
        notebook_url: Optional[str] = None
    ):
        """
        初始化写作 Agent

        Args:
            api_key: Anthropic API Key，如果不提供则从环境变量读取
            model: 使用的模型，默认 MiniMax-M2.1
            notebook_id: NotebookLM 笔记本 ID（从库中获取）
            notebook_url: NotebookLM 笔记本 URL（直接指定）
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("请设置 ANTHROPIC_API_KEY 环境变量或传入 api_key 参数")

        self.model = model

        # 支持自定义 base_url
        base_url = os.getenv("ANTHROPIC_BASE_URL")
        if base_url:
            self.client = Anthropic(api_key=self.api_key, base_url=base_url)
        else:
            self.client = Anthropic(api_key=self.api_key)

        self.notebooklm = create_notebooklm_tool(
            notebook_id=notebook_id,
            notebook_url=notebook_url
        )

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一个专业的公众号文章写作助手。你的任务是帮助用户撰写高质量的公众号文章。

核心要求：
1. **动态检索知识库**：在写作过程中，当你需要以下内容时，主动使用 query_notebooklm 工具：
   - 具体的案例或数据
   - 之前表达过的观点
   - 专业的背景知识
   - 个人经验和见解

2. **保持个人风格**：
   - 不要写成通识科普，要有明确的个人观点
   - 结合从知识库中检索到的个人经验和案例
   - 保持真实性和独特性

3. **文章结构**：
   - 吸引人的标题和开头
   - 清晰的逻辑结构
   - 具体的案例支撑观点
   - 启发性的结论

4. **工作流程**：
   - 先分析选题，理解核心要表达的内容
   - 规划文章大纲
   - 逐段写作，主动判断何时需要查询知识库
   - 整合检索内容，保持文章连贯性

记住：你可以自主决定何时调用知识库，不需要每次都询问用户。当你觉得需要更多信息、案例或观点时，就主动查询。"""

    def write_article(
        self,
        topic: str,
        reference: Optional[str] = None,
        max_turns: int = 10
    ) -> str:
        """
        写作文章

        Args:
            topic: 文章选题
            reference: 可选的参考资料
            max_turns: 最大对话轮次

        Returns:
            生成的文章内容
        """
        # 构建初始消息
        user_message = f"选题：{topic}"
        if reference:
            user_message += f"\n\n参考资料：{reference}"

        messages = [{"role": "user", "content": user_message}]

        # 工具定义
        tools = [self.notebooklm.get_tool_definition()]

        # Agent 循环
        for turn in range(max_turns):
            print(f"\n{'='*50}")
            print(f"轮次 {turn + 1}/{max_turns}")
            print(f"{'='*50}")

            # 调用 Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self._get_system_prompt(),
                tools=tools,
                messages=messages
            )

            print(f"\n停止原因: {response.stop_reason}")

            # 检查是否需要工具调用
            if response.stop_reason == "tool_use":
                # 添加助手消息
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })

                # 处理工具调用
                tool_results = []
                for content_block in response.content:
                    if content_block.type == "tool_use":
                        tool_name = content_block.name
                        tool_input = content_block.input

                        print(f"\n🔧 调用工具: {tool_name}")
                        print(f"   查询: {tool_input.get('question', '')}")

                        if tool_name == "query_notebooklm":
                            # 调用 NotebookLM
                            result = self.notebooklm.query(tool_input["question"])
                            print(f"   结果: {result[:100]}...")

                            # 收集工具结果
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": content_block.id,
                                "content": result
                            })

                # 添加工具结果
                messages.append({
                    "role": "user",
                    "content": tool_results
                })

            elif response.stop_reason == "end_turn":
                # Agent 完成任务
                print("\n✅ 文章生成完成")

                # 提取文本内容
                text_content = ""
                for content_block in response.content:
                    if hasattr(content_block, "text"):
                        text_content += content_block.text

                return text_content

            else:
                # 其他停止原因
                print(f"\n⚠️ 意外的停止原因: {response.stop_reason}")
                # 尝试返回当前内容
                text_content = ""
                for content_block in response.content:
                    if hasattr(content_block, "text"):
                        text_content += content_block.text
                if text_content:
                    return text_content
                break

        # 如果达到最大轮次，返回最后的内容
        print("\n⚠️ 达到最大轮次限制")
        return ""

    def interactive_write(self):
        """交互式写作模式"""
        print("\n" + "="*60)
        print("🤖 公众号文章写作 Agent（基于 NotebookLM）")
        print("="*60)

        # 获取选题
        print("\n📝 请输入文章选题:")
        topic = input("> ").strip()

        if not topic:
            print("❌ 选题不能为空")
            return

        # 获取参考资料（可选）
        print("\n📚 是否有参考资料？（可选，直接回车跳过）:")
        reference = input("> ").strip()

        print("\n" + "-"*60)
        print("🚀 开始写作...")
        print("-"*60)

        # 生成文章
        article = self.write_article(
            topic=topic,
            reference=reference if reference else None
        )

        # 输出结果
        print("\n" + "="*60)
        print("📄 生成的文章")
        print("="*60)
        print(article)

        # 保存到文件
        filename = f"article_{topic[:20].replace(' ', '_')}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# {topic}\n\n")
            f.write(article)

        print(f"\n💾 文章已保存到: {filename}")


def create_writer_agent(
    api_key: Optional[str] = None,
    model: str = "claude-3-5-sonnet-20241022",
    notebook_id: Optional[str] = None,
    notebook_url: Optional[str] = None
) -> WechatWriterAgent:
    """
    创建写作 Agent 实例

    Args:
        api_key: Anthropic API Key
        model: 使用的模型，默认 claude-3-5-sonnet-20241022
        notebook_id: NotebookLM 笔记本 ID（从库中获取）
        notebook_url: NotebookLM 笔记本 URL（直接指定）

    Returns:
        WechatWriterAgent 实例
    """
    return WechatWriterAgent(
        api_key=api_key,
        model=model,
        notebook_id=notebook_id,
        notebook_url=notebook_url
    )
