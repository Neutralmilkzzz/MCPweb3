# TRON MCP Server
# 渐进式披露架构实现

from tron_mcp_server.logging_config import setup_logging

# 初始化统一日志配置
setup_logging()

from tron_mcp_server import skills
from tron_mcp_server import validators
from tron_mcp_server import formatters
from tron_mcp_server import tron_client
from tron_mcp_server import tx_builder
from tron_mcp_server import key_manager
from tron_mcp_server import call_router
from tron_mcp_server import address_book
from tron_mcp_server import qrcode_generator

# server 模块延迟导入，避免在测试环境中因缺少 mcp 包报错
# from tron_mcp_server.server import mcp

__all__ = [
    "skills",
    "validators",
    "formatters",
    "tron_client",
    "tx_builder",
    "key_manager",
    "call_router",
    "address_book",
    "qrcode_generator",
]
