"""TRON MCP Server - 入口模块

遵循 MCP 最佳实践：
- 工具命名: tron_{action}_{resource}
- 服务前缀: tron_
- 支持 JSON 和 Markdown 格式输出
"""

from mcp.server.fastmcp import FastMCP
from . import call_router

# 创建 MCP Server 实例
mcp = FastMCP("tron-mcp-server")


# ============ 标准 MCP 工具（推荐使用）============

@mcp.tool()
def tron_get_usdt_balance(address: str) -> dict:
    """
    查询指定地址的 USDT (TRC20) 余额。
    
    Args:
        address: TRON 地址（Base58 格式以 T 开头，或 Hex 格式以 0x41 开头）
    
    Returns:
        包含 balance_usdt, balance_raw, summary 的结果
    """
    return call_router.call("get_usdt_balance", {"address": address})


@mcp.tool()
def tron_get_balance(address: str) -> dict:
    """
    查询指定地址的 TRX 原生代币余额。
    
    Args:
        address: TRON 地址
    
    Returns:
        包含 balance_trx, balance_sun, summary 的结果
    """
    return call_router.call("get_balance", {"address": address})


@mcp.tool()
def tron_get_gas_parameters() -> dict:
    """
    获取当前网络的 Gas/能量价格参数。
    
    Returns:
        包含 gas_price_sun, gas_price_trx, summary 的结果
    """
    return call_router.call("get_gas_parameters", {})


@mcp.tool()
def tron_get_transaction_status(txid: str) -> dict:
    """
    查询交易的确认状态。
    
    Args:
        txid: 交易哈希，64 位十六进制字符串
    
    Returns:
        包含 status, success, block_number, summary 的结果
    """
    return call_router.call("get_transaction_status", {"txid": txid})


@mcp.tool()
def tron_get_network_status() -> dict:
    """
    获取 TRON 网络当前状态（最新区块高度）。
    
    Returns:
        包含 latest_block, chain, summary 的结果
    """
    return call_router.call("get_network_status", {})


@mcp.tool()
def tron_build_tx(
    from_address: str,
    to_address: str,
    amount: float,
    token: str = "USDT"
) -> dict:
    """
    构建未签名的转账交易。仅构建交易，不执行签名和广播。
    
    Args:
        from_address: 发送方地址
        to_address: 接收方地址
        amount: 转账金额（正数）
        token: 代币类型，USDT 或 TRX，默认 USDT
    
    Returns:
        包含 unsigned_tx, summary 的结果
    """
    return call_router.call("build_tx", {
        "from": from_address,
        "to": to_address,
        "amount": amount,
        "token": token,
    })


@mcp.tool()
def tron_check_account_safety(address: str) -> dict:
    """
    检查指定地址是否为恶意地址（钓鱼、诈骗等）。
    
    使用 TRONSCAN 官方黑名单 API 检查地址是否被标记为恶意地址。
    建议在进行转账前调用此工具确认接收方地址的安全性。
    
    Args:
        address: TRON 地址（Base58 格式以 T 开头，或 Hex 格式以 0x41 开头）
    
    Returns:
        包含 is_safe, is_risky, risk_type, safety_status, warnings, summary 的结果
        - is_safe: 地址是否安全（True/False）
        - is_risky: 地址是否有风险标记（True/False）
        - risk_type: 风险类型（Safe/Scam/Phishing/Unknown 等）
        - safety_status: 安全状态描述
        - warnings: 警告信息列表
        - summary: 检查结果摘要
    """
    return call_router.call("check_account_safety", {"address": address})


# ============ 兼容模式：单入口（可选）============

@mcp.tool()
def call(action: str, params: dict = None) -> dict:
    """
    TRON 区块链操作单入口（兼容模式）。
    
    推荐直接使用 tron_* 系列工具，此接口保留用于兼容。

    Args:
        action: 动作名称 (get_usdt_balance, get_gas_parameters, 等)
        params: 动作参数

    Returns:
        操作结果
    """
    return call_router.call(action, params or {})


def main():
    """启动 MCP Server（支持 stdio 和 SSE 模式）"""
    import sys
    import os

    # 默认端口（可通过环境变量覆盖）
    port = int(os.getenv("MCP_PORT", "8765"))

    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--sse":
        # SSE 模式：用 uvicorn 启动 HTTP 服务
        try:
            import uvicorn
        except ImportError:
            print("❌ SSE 模式需要安装 uvicorn: pip install uvicorn")
            sys.exit(1)
        print(f"🚀 TRON MCP Server (SSE) 启动在 http://127.0.0.1:{port}/sse")
        app = mcp.sse_app()
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
    else:
        # 默认 stdio 模式
        mcp.run()


if __name__ == "__main__":
    main()
