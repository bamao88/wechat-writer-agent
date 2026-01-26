"""测试 CLI 交互层"""

import pytest
from unittest.mock import patch, MagicMock, mock_open, call
from cli import interactive_mode, main
from src.models import Article, PipelineResult


class TestInteractiveMode:
    """测试 interactive_mode 函数"""

    @patch('cli.run_pipeline')
    @patch('cli.input')
    @patch('cli.os.getenv')
    @patch('builtins.open', new_callable=mock_open)
    def test_interactive_mode_basic_flow(self, mock_file, mock_getenv, mock_input, mock_pipeline):
        """测试基本交互流程"""
        # Mock 环境变量
        mock_getenv.return_value = "test-api-key"

        # Mock 用户输入: 选题, 不启用飞书
        mock_input.side_effect = ["测试选题", "n"]

        # Mock pipeline 返回
        mock_article = Article(
            title="测试标题",
            content="# 测试标题\n\n这是测试内容",
            source_summary="基于 3 条检索结果生成"
        )
        mock_pipeline.return_value = PipelineResult(article=mock_article)

        # 执行
        interactive_mode()

        # 验证 run_pipeline 调用参数
        mock_pipeline.assert_called_once()
        call_kwargs = mock_pipeline.call_args[1]
        assert call_kwargs['topic'] == "测试选题"
        assert call_kwargs['api_key'] == "test-api-key"
        assert call_kwargs['enable_feishu'] is False
        assert call_kwargs['folder_token'] is None

        # 验证文件保存
        mock_file.assert_called_once_with("article_测试选题.md", "w", encoding="utf-8")
        mock_file().write.assert_called_once_with("# 测试标题\n\n这是测试内容")

    @patch('cli.input')
    @patch('cli.os.getenv')
    def test_interactive_mode_without_api_key(self, mock_getenv, mock_input):
        """测试缺少 API Key 时的错误处理"""
        # Mock 环境变量返回 None
        mock_getenv.return_value = None

        # Mock 用户输入
        mock_input.side_effect = ["测试选题", "n"]

        # 执行（使用 capsys 捕获输出）
        with patch('sys.stdout'):
            interactive_mode()

        # 验证：函数应该提前返回，不抛出异常
        # 由于提前返回，不会有更多的 input() 调用

    @patch('cli.input')
    @patch('cli.os.getenv')
    def test_interactive_mode_empty_topic(self, mock_getenv, mock_input):
        """测试空选题的错误处理"""
        # Mock 环境变量
        mock_getenv.return_value = "test-api-key"

        # Mock 用户输入空字符串
        mock_input.return_value = ""

        # 执行
        with patch('sys.stdout'):
            interactive_mode()

        # 验证：只调用一次 input（获取选题后就返回）
        assert mock_input.call_count == 1

    @patch('cli.run_pipeline')
    @patch('cli.input')
    @patch('cli.os.getenv')
    @patch('builtins.open', new_callable=mock_open)
    def test_interactive_mode_enable_feishu(self, mock_file, mock_getenv, mock_input, mock_pipeline):
        """测试启用飞书功能"""
        # Mock 环境变量
        mock_getenv.return_value = "test-api-key"

        # Mock 用户输入: 选题, 启用飞书, folder_token
        mock_input.side_effect = ["测试选题", "y", "test-folder-token"]

        # Mock pipeline 返回
        mock_article = Article(
            title="测试标题",
            content="# 测试标题\n\n内容",
            source_summary="摘要"
        )
        mock_pipeline.return_value = PipelineResult(article=mock_article)

        # 执行
        interactive_mode()

        # 验证 run_pipeline 调用参数
        call_kwargs = mock_pipeline.call_args[1]
        assert call_kwargs['enable_feishu'] is True
        assert call_kwargs['folder_token'] == "test-folder-token"

    @patch('cli.run_pipeline')
    @patch('cli.input')
    @patch('cli.os.getenv')
    @patch('builtins.open', new_callable=mock_open)
    def test_interactive_mode_enable_feishu_without_folder_token(
        self, mock_file, mock_getenv, mock_input, mock_pipeline
    ):
        """测试启用飞书但不提供 folder_token"""
        # Mock 环境变量
        mock_getenv.return_value = "test-api-key"

        # Mock 用户输入: 选题, 启用飞书, 空 folder_token
        mock_input.side_effect = ["测试选题", "y", ""]

        # Mock pipeline 返回
        mock_article = Article(
            title="测试标题",
            content="# 测试标题\n\n内容",
            source_summary="摘要"
        )
        mock_pipeline.return_value = PipelineResult(article=mock_article)

        # 执行
        interactive_mode()

        # 验证 folder_token 为 None
        call_kwargs = mock_pipeline.call_args[1]
        assert call_kwargs['folder_token'] is None

    @patch('cli.run_pipeline')
    @patch('cli.input')
    @patch('cli.os.getenv')
    def test_interactive_mode_handles_exception(self, mock_getenv, mock_input, mock_pipeline):
        """测试异常处理"""
        # Mock 环境变量
        mock_getenv.return_value = "test-api-key"

        # Mock 用户输入
        mock_input.side_effect = ["测试选题", "n"]

        # Mock run_pipeline 抛出异常
        mock_pipeline.side_effect = RuntimeError("测试错误")

        # 执行（应该捕获异常，不崩溃）
        with patch('sys.stdout'):
            interactive_mode()

        # 验证 run_pipeline 被调用
        mock_pipeline.assert_called_once()

    @patch('cli.run_pipeline')
    @patch('cli.input')
    @patch('cli.os.getenv')
    @patch('builtins.open', new_callable=mock_open)
    def test_interactive_mode_with_feishu_result(
        self, mock_file, mock_getenv, mock_input, mock_pipeline
    ):
        """测试飞书结果的输出"""
        # Mock 环境变量
        mock_getenv.return_value = "test-api-key"

        # Mock 用户输入
        mock_input.side_effect = ["测试选题", "n"]

        # Mock pipeline 返回（包含飞书结果）
        from src.models import DocResult
        mock_article = Article(
            title="测试标题",
            content="# 测试标题\n\n内容",
            source_summary="摘要"
        )
        mock_doc_result = DocResult(
            doc_id="doc123",
            doc_url="https://feishu.cn/doc123"
        )
        mock_pipeline.return_value = PipelineResult(
            article=mock_article,
            doc_result=mock_doc_result,
            record_id="record456"
        )

        # 执行
        with patch('sys.stdout'):
            interactive_mode()

        # 验证文件保存
        mock_file.assert_called_once()


class TestMain:
    """测试 main 函数"""

    @patch('cli.load_dotenv')
    @patch('cli.os.getenv')
    @patch('sys.exit')
    def test_main_without_api_key(self, mock_exit, mock_getenv, mock_load_dotenv):
        """测试 main 函数在缺少 API Key 时的行为"""
        # Mock 环境变量返回 None
        mock_getenv.return_value = None

        # Mock sys.exit to raise SystemExit (like real exit)
        mock_exit.side_effect = SystemExit(1)

        # 执行并捕获 SystemExit
        with patch('sys.stdout'):
            with pytest.raises(SystemExit) as excinfo:
                main()

        # 验证退出码为 1
        assert excinfo.value.code == 1

        # 验证调用了 load_dotenv
        mock_load_dotenv.assert_called_once()

        # 验证调用了 sys.exit(1)
        mock_exit.assert_called_once_with(1)

    @patch('cli.interactive_mode')
    @patch('cli.load_dotenv')
    @patch('cli.os.getenv')
    def test_main_with_api_key(self, mock_getenv, mock_load_dotenv, mock_interactive):
        """测试 main 函数在有 API Key 时的行为"""
        # Mock 环境变量
        mock_getenv.return_value = "test-api-key"

        # 执行
        main()

        # 验证调用了 load_dotenv
        mock_load_dotenv.assert_called_once()

        # 验证调用了 interactive_mode
        mock_interactive.assert_called_once()
