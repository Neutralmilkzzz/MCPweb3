"""TRON MCP Server - 入口模块

遵循 MCP 最佳实践：
- 工具命名: tron_{action}_{resource}
- 服务前缀: tron_
- 支持 JSON 和 Markdown 格式输出
"""

import json

from mcp.server.fastmcp import FastMCP
from . import call_router
from . import config  # 触发 load_dotenv()，确保 API Key 等环境变量被加载

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
    查询交易的详细状态信息。
    
    Args:
        txid: 交易哈希，64 位十六进制字符串
    
    Returns:
        包含 status, success, block_number, token_type, amount, from_address, to_address, fee_trx, time, summary 的结果
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
    token: str = "USDT",
    force_execution: bool = False
) -> dict:
    """
    构建未签名的转账交易。仅构建交易，不执行签名和广播。
    
    重要安全说明：
    此工具会对接收方地址进行安全扫描。如果检测到接收方存在风险，
    默认会拒绝构建交易（零容忍熔断机制）。
    
    如需强制执行（用户明确知晓风险后坚持转账），请设置 force_execution=True。
    
    Args:
        from_address: 发送方地址
        to_address: 接收方地址
        amount: 转账金额（正数）
        token: 代币类型，USDT 或 TRX，默认 USDT
        force_execution: 强制执行开关。当接收方存在风险时，只有设置为 True 才能继续构建交易。
                        仅在用户明确说"我知道有风险，但我就是要转"时才设置为 True。
    
    Returns:
        包含 unsigned_tx, summary 的结果。
        如果接收方有风险且 force_execution=False，返回拦截信息。
    """
    return call_router.call("build_tx", {
        "from": from_address,
        "to": to_address,
        "amount": amount,
        "token": token,
        "force_execution": force_execution,
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


# ============ 转账闭环工具（签名 / 广播 / 一键转账）============

@mcp.tool()
def tron_sign_tx(unsigned_tx_json: str) -> dict:
    """
    对未签名交易进行本地签名。不广播。
    
    接受 tron_build_tx 返回的 unsigned_tx JSON 字符串，
    使用本地私钥进行 ECDSA secp256k1 签名。
    
    签名在本地完成，私钥永远不会通过网络传输。
    
    前置条件：需设置环境变量 TRON_PRIVATE_KEY。
    
    Args:
        unsigned_tx_json: tron_build_tx 返回的未签名交易 JSON 字符串
    
    Returns:
        包含 signed_tx, signed_tx_json, txID, summary 的签名结果。
        使用 tron_broadcast_tx 广播签名后的交易。
    """
    return call_router.call("sign_tx", {"unsigned_tx_json": unsigned_tx_json})


@mcp.tool()
def tron_broadcast_tx(signed_tx_json: str) -> dict:
    """
    广播已签名的交易到 TRON 网络。
    
    接受 tron_sign_tx 返回的 signed_tx JSON 字符串。
    
    Args:
        signed_tx_json: 已签名交易的 JSON 字符串
    
    Returns:
        包含 result, txid, summary 的广播结果
    """
    return call_router.call("broadcast_tx", {
        "signed_tx_json": signed_tx_json,
    })


@mcp.tool()
def tron_transfer(
    to_address: str,
    amount: float,
    token: str = "USDT",
    force_execution: bool = False,
) -> dict:
    """
    一键转账闭环：安全检查 → 构建交易 → 签名 → 广播。
    
    这是完整的转账工具，自动完成全部流程。
    发送方地址自动从本地私钥派生。
    
    安全机制（与 tron_build_tx 相同）：
    - Anti-Fraud: 检查接收方是否为恶意地址
    - Gas Guard: 检查发送方余额是否充足
    - Recipient Check: 检查接收方账户状态
    
    前置条件：需设置环境变量 TRON_PRIVATE_KEY。
    
    Args:
        to_address: 接收方地址
        amount: 转账金额（正数）
        token: 代币类型，USDT 或 TRX，默认 USDT
        force_execution: 强制执行开关。当接收方存在风险时，
                        只有设置为 True 才能继续转账。
    
    Returns:
        包含 txid, result, summary 的转账结果
    """
    return call_router.call("transfer", {
        "to": to_address,
        "amount": amount,
        "token": token,
        "force_execution": force_execution,
    })


@mcp.tool()
def tron_get_wallet_info() -> dict:
    """
    查看当前配置的钱包信息。
    
    返回本地私钥对应的地址及其 TRX / USDT 余额。
    不会暴露私钥本身。
    
    前置条件：需设置环境变量 TRON_PRIVATE_KEY。
    
    Returns:
        包含 address, trx_balance, usdt_balance, summary 的结果
    """
    return call_router.call("get_wallet_info", {})


@mcp.tool()
def tron_get_transaction_history(
    address: str,
    limit: int = 10,
    start: int = 0,
    token: str = None,
) -> dict:
    """
    查询指定地址的交易历史记录。

    支持自定义返回条数和按代币类型筛选。

    Args:
        address: TRON 地址（Base58 格式以 T 开头，或 Hex 格式以 0x41 开头）
        limit: 返回交易条数，默认 10，最大 50
        start: 偏移量（用于分页），默认 0
        token: 代币筛选条件，可选值：
               - None: 查询所有类型的交易（默认）
               - "TRX": 仅查询 TRX 原生转账
               - "USDT": 仅查询 USDT (TRC20) 转账
               - TRC20 合约地址: 查询指定 TRC20 代币的转账记录
               - TRC10 代币名称: 查询指定 TRC10 代币的转账记录

    Returns:
        包含 address, total, displayed, token_filter, transfers 列表和 summary 的结果
    """
    return call_router.call("get_transaction_history", {
        "address": address,
        "limit": limit,
        "start": start,
        "token": token,
    })


@mcp.tool()
def tron_get_internal_transactions(
    address: str,
    limit: int = 20,
    start: int = 0,
) -> dict:
    """
    查询地址的内部交易（合约内部调用产生的转账）。
    
    内部交易是智能合约执行过程中产生的转账，不同于普通的直接转账。
    常见于 DeFi 操作（如 DEX swap）、合约间调用等场景。
    
    Args:
        address: TRON 地址
        limit: 返回条数，默认 20，最大 50
        start: 偏移量（分页），默认 0
    
    Returns:
        包含内部交易列表和统计摘要的结果
    """
    return call_router.call("get_internal_transactions", {
        "address": address,
        "limit": limit,
        "start": start,
    })


@mcp.tool()
def tron_get_account_tokens(address: str) -> dict:
    """
    查询地址持有的所有代币列表（TRX + TRC20 + TRC10）。
    
    返回完整的代币持仓信息，包括代币名称、缩写、余额等。
    适用于资产概览、异常代币检测等场景。
    
    Args:
        address: TRON 地址
    
    Returns:
        包含 token_count, tokens 列表和 summary 的结果
    """
    return call_router.call("get_account_tokens", {"address": address})


@mcp.tool()
def tron_addressbook_add(alias: str, address: str, note: str = "") -> dict:
    """
    添加或更新地址簿联系人。将别名与 TRON 地址映射保存到本地。

    使用场景：
    - "帮我把 TKyPzHiXW4Zms4txUxfWjXBidGzZpiCchn 记成小明"
    - "保存地址，别名叫老板"

    Args:
        alias: 联系人别名（如 "小明"、"老板"、"Binance热钱包"）
        address: TRON 地址（Base58 格式以 T 开头）
        note: 备注信息（可选，如 "大学同学"、"公司财务"）

    Returns:
        包含 alias, address, is_update, total_contacts, summary 的结果
    """
    return call_router.call("addressbook_add", {
        "alias": alias,
        "address": address,
        "note": note,
    })


@mcp.tool()
def tron_addressbook_remove(alias: str) -> dict:
    """
    从地址簿中删除联系人。

    Args:
        alias: 要删除的联系人别名

    Returns:
        包含 alias, found, removed_address, summary 的结果
    """
    return call_router.call("addressbook_remove", {"alias": alias})


@mcp.tool()
def tron_addressbook_lookup(alias: str) -> dict:
    """
    通过别名查找 TRON 地址。支持模糊搜索。

    使用场景：
    - "小明的地址是什么"
    - 在转账前将别名解析为实际地址

    重要：当用户说"给小明转 1 USDT"时，应先调用此工具获取小明的地址，
    然后再调用 tron_transfer 进行转账。

    Args:
        alias: 联系人别名

    Returns:
        包含 alias, found, address, note, summary 的结果。
        如果未精确匹配，会返回 similar_matches 相似联系人列表。
    """
    return call_router.call("addressbook_lookup", {"alias": alias})


@mcp.tool()
def tron_addressbook_list() -> dict:
    """
    列出地址簿中所有联系人。

    Returns:
        包含 total, contacts 列表和 summary 的结果。
        每个 contact 包含 alias, address, note, created_at。
    """
    return call_router.call("addressbook_list", {})


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
