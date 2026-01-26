#!/bin/bash

# NotebookLM Skill 测试运行脚本
# 用法: ./run_tests.sh [选项]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}NotebookLM Skill 测试套件${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# 检查 Python 版本
echo -e "${YELLOW}检查 Python 版本...${NC}"
python3 --version || { echo -e "${RED}错误: Python 3 未安装${NC}"; exit 1; }
echo ""

# 检查虚拟环境
if [[ -z "${VIRTUAL_ENV}" ]]; then
    echo -e "${YELLOW}警告: 未检测到虚拟环境${NC}"
    echo -e "${YELLOW}建议使用虚拟环境运行测试:${NC}"
    echo -e "  python3 -m venv venv"
    echo -e "  source venv/bin/activate"
    echo -e "  pip install -r requirements.txt"
    echo ""
    read -p "继续运行测试？ (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

# 检查 pytest 是否安装
echo -e "${YELLOW}检查 pytest 安装...${NC}"
if ! python3 -c "import pytest" 2>/dev/null; then
    echo -e "${RED}错误: pytest 未安装${NC}"
    echo -e "${YELLOW}安装测试依赖:${NC}"
    echo -e "  pip install pytest pytest-timeout pytest-mock pytest-cov"
    exit 1
fi
echo -e "${GREEN}✓ pytest 已安装${NC}"
echo ""

# 检查环境变量
echo -e "${YELLOW}检查环境变量...${NC}"
if [[ -f .env ]]; then
    echo -e "${GREEN}✓ .env 文件存在${NC}"
else
    echo -e "${YELLOW}警告: .env 文件不存在${NC}"
    echo -e "某些测试可能需要 ANTHROPIC_API_KEY"
fi
echo ""

# 解析参数
TEST_TYPE="${1:-all}"

case "$TEST_TYPE" in
    p0)
        echo -e "${BLUE}运行 P0 测试（必须通过）${NC}"
        echo -e "${BLUE}--------------------------------------------${NC}"
        python3 -m pytest tests/test_notebooklm_tool.py tests/test_e2e.py -v
        ;;

    p1)
        echo -e "${BLUE}运行 P1 测试（重要）${NC}"
        echo -e "${BLUE}--------------------------------------------${NC}"
        python3 -m pytest tests/test_external_skill.py tests/test_writer_agent.py tests/test_error_handling.py -v
        ;;

    unit)
        echo -e "${BLUE}运行单元测试${NC}"
        echo -e "${BLUE}--------------------------------------------${NC}"
        python3 -m pytest tests/test_notebooklm_tool.py -v
        ;;

    integration)
        echo -e "${BLUE}运行集成测试${NC}"
        echo -e "${BLUE}--------------------------------------------${NC}"
        python3 -m pytest tests/ -v -m integration
        ;;

    coverage)
        echo -e "${BLUE}运行测试并生成覆盖率报告${NC}"
        echo -e "${BLUE}--------------------------------------------${NC}"
        python3 -m pytest tests/ --cov=. --cov-report=html --cov-report=term-missing -v
        echo ""
        echo -e "${GREEN}覆盖率报告已生成: htmlcov/index.html${NC}"
        ;;

    quick)
        echo -e "${BLUE}快速测试（跳过集成测试）${NC}"
        echo -e "${BLUE}--------------------------------------------${NC}"
        python3 -m pytest tests/ -v -m "not integration" --tb=short
        ;;

    all)
        echo -e "${BLUE}运行所有测试${NC}"
        echo -e "${BLUE}--------------------------------------------${NC}"
        python3 -m pytest tests/ -v
        ;;

    help|--help|-h)
        echo "用法: ./run_tests.sh [选项]"
        echo ""
        echo "选项:"
        echo "  all          运行所有测试（默认）"
        echo "  p0           运行 P0 测试（必须通过）"
        echo "  p1           运行 P1 测试（重要）"
        echo "  unit         运行单元测试"
        echo "  integration  运行集成测试"
        echo "  coverage     运行测试并生成覆盖率报告"
        echo "  quick        快速测试（跳过集成测试）"
        echo "  help         显示此帮助信息"
        echo ""
        echo "示例:"
        echo "  ./run_tests.sh p0        # 运行 P0 测试"
        echo "  ./run_tests.sh coverage  # 生成覆盖率报告"
        exit 0
        ;;

    *)
        echo -e "${RED}错误: 未知选项 '$TEST_TYPE'${NC}"
        echo "使用 './run_tests.sh help' 查看可用选项"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${GREEN}测试完成！${NC}"
echo -e "${BLUE}============================================${NC}"
