"""TRON MCP CLI — 统一命令行入口

用法:
    tronmcp onboard    交互式引导配置
    tronmcp --help     查看帮助
"""

import sys


USAGE = """\
🐙 TRONMCP CLI

用法:
    tronmcp <command>

可用命令:
    onboard     交互式引导配置（私钥 / API Key / .env）

选项:
    --help, -h  显示此帮助信息
"""


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("--help", "-h"):
        print(USAGE)
        sys.exit(0)

    command = args[0].lower()

    if command == "onboard":
        from tron_mcp_server.onboard import main as onboard_main
        onboard_main()
    else:
        print(f"❌ 未知命令: {command}")
        print(USAGE)
        sys.exit(1)


if __name__ == "__main__":
    main()
