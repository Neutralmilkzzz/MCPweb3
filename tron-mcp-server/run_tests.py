#!/usr/bin/env python3
"""运行测试套件并生成报告

使用 pytest 自动发现并运行 tests/ 目录下的所有测试。
支持按类别运行、HTML报告、覆盖率报告。
"""

import sys
import os
import subprocess
import argparse

def run_tests(category=None, coverage=False, html_report=False, verbose=False):
    """运行测试

    Args:
        category: 测试类别 (unit, integration, functional, regression, stress)
        coverage: 是否生成覆盖率报告
        html_report: 是否生成 HTML 报告
        verbose: 详细输出
    """

    # 压力测试是独立脚本，不是pytest格式
    if category == "stress":
        print(f"\n{'='*60}")
        print("运行压力测试 (独立脚本)")
        print(f"{'='*60}\n")
        result = subprocess.run([sys.executable, "tests/stress/stress_test.py"])
        return result.returncode

    # 构建 pytest 命令
    cmd = ["pytest"]

    # 设置测试路径
    test_path = "tests"
    if category:
        test_path = f"tests/{category}"
        cmd.append(f"tests/{category}")

    # 输出选项
    if verbose:
        cmd.append("-vv")
    else:
        cmd.append("-v")

    # 添加标记
    if category:
        cmd.extend(["-m", category])

    # 覆盖率
    if coverage:
        cmd.extend([
            "--cov=tron_mcp_server",
            "--cov-report=term-missing",
            "--cov-report=html"
        ])

    # HTML 报告
    if html_report:
        cmd.extend([
            "--html=test_report.html",
            "--self-contained-html"
        ])

    # JUnit XML (CI/CD 友好)
    cmd.append("--junitxml=test_results.xml")

    print(f"\n{'='*60}")
    print(f"运行测试: {test_path}")
    print(f"命令: {' '.join(cmd)}")
    print(f"{'='*60}\n")

    # 运行 pytest
    result = subprocess.run(cmd)

    return result.returncode


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="TRON MCP Server 测试运行器")
    parser.add_argument(
        "--category", "-c",
        choices=["unit", "integration", "functional", "regression", "stress"],
        help="只运行指定类别的测试"
    )
    parser.add_argument(
        "--coverage", "-C",
        action="store_true",
        help="生成覆盖率报告"
    )
    parser.add_argument(
        "--html", "-H",
        action="store_true",
        help="生成 HTML 测试报告"
    )
    parser.add_argument(
        "--verbose", "-V",
        action="store_true",
        help="详细输出"
    )

    args = parser.parse_args()

    # 检查 pytest 是否安装
    try:
        import pytest
    except ImportError:
        print("错误: pytest 未安装")
        print("请运行: pip install pytest pytest-asyncio")
        sys.exit(1)

    # 运行测试
    exit_code = run_tests(
        category=args.category,
        coverage=args.coverage,
        html_report=args.html,
        verbose=args.verbose
    )

    sys.exit(exit_code)