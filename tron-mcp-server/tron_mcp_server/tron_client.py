"""TRON 客户端模块 - TRONSCAN REST API 封装"""

import logging
import os
import hashlib
from typing import Optional
import httpx
import base58

# USDT TRC20 合约地址
# Default to Mainnet if not set
USDT_CONTRACT_BASE58 = os.getenv("USDT_CONTRACT_ADDRESS", "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t")
USDT_CONTRACT_HEX = os.getenv("USDT_CONTRACT_ADDRESS_HEX", "0x41a614f803b6fd780986a42c78ec9c7f77e6ded13c")

# 默认 TRONSCAN API URL
DEFAULT_API_URL = "https://apilist.tronscan.org/api"

# 超时设置
TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "10.0"))


def _get_api_url() -> str:
    """获取 TRONSCAN API URL"""
    base_url = os.getenv("TRONSCAN_API_URL", "") or DEFAULT_API_URL
    base_url = base_url.rstrip("/")
    if not base_url:
        raise ValueError("未配置 TRONSCAN_API_URL")
    return base_url


def _get_headers() -> dict:
    """获取请求头"""
    headers = {"Accept": "application/json"}
    api_key = os.getenv("TRONSCAN_API_KEY", "")
    if api_key:
        headers["TRONSCAN-API-KEY"] = api_key
    return headers


def _get(path: str, params: Optional[dict] = None) -> dict:
    """发送 GET 请求"""
    url = f"{_get_api_url()}/{path.lstrip('/')}"
    response = httpx.get(url, params=params, headers=_get_headers(), timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()
    if data is None:
        raise ValueError("TRONSCAN 响应为空")
    return data


def _to_int(value) -> int:
    if value is None:
        raise ValueError("缺少数值字段")
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        value = value.strip()
        if value.startswith("0x"):
            return int(value, 16)
        return int(value)
    raise ValueError(f"无法解析数值: {value}")


def _first_not_none(*values):
    for value in values:
        if value is not None:
            return value
    return None


def _get_account(address: str) -> dict:
    return _get("account", {"address": _normalize_address(address)})


def _normalize_address(address: str) -> str:
    if address.startswith("0x") and len(address) == 44:
        return _hex_to_base58(address[2:])
    if address.startswith("41") and len(address) == 42:
        return _hex_to_base58(address)
    return address


def _normalize_txid(txid: str) -> str:
    return txid[2:] if txid.startswith("0x") else txid


def _hex_to_base58(hex_addr: str) -> str:
    """将十六进制地址转换为 Base58Check 格式"""
    raw = bytes.fromhex(hex_addr)
    return base58.b58encode_check(raw).decode('utf-8')


def get_usdt_balance(address: str) -> float:
    """
    查询地址的 USDT 余额
    调用 TRONSCAN account 接口
    """
    data = _get_account(address)
    token_balances = _first_not_none(
        data.get("trc20token_balances"),
        data.get("trc20TokenBalances"),
        data.get("tokenBalances"),
        [],
    )

    for entry in token_balances:
        token_id = (
            entry.get("tokenId")
            or entry.get("token_id")
            or entry.get("contractAddress")
            or entry.get("contract_address")
            or entry.get("tokenAddress")
        )
        if token_id in (USDT_CONTRACT_BASE58, USDT_CONTRACT_HEX):
            balance_raw = _to_int(
                _first_not_none(
                    entry.get("balance"),
                    entry.get("tokenBalance"),
                    entry.get("quantity"),
                    entry.get("token_balance"),
                )
            )
            decimals = _first_not_none(
                entry.get("tokenDecimal"),
                entry.get("token_decimals"),
                entry.get("decimals"),
            )
            decimals = int(decimals) if decimals is not None else 6
            return balance_raw / (10 ** decimals)

    return 0.0


def get_balance_trx(address: str) -> float:
    """
    查询地址的 TRX 余额
    TRONSCAN 返回 SUN
    """
    data = _get_account(address)
    balance_sun = _to_int(
        _first_not_none(
            data.get("balance"),
            data.get("balanceSun"),
            data.get("totalBalance"),
            data.get("total_balance"),
        )
    )
    return balance_sun / 1_000_000


def get_gas_parameters() -> int:
    """
    获取当前网络 Gas 价格 (SUN)
    """
    data = _get("chainparameters")
    params = (
        data.get("tronParameters")
        or data.get("chainParameter")
        or data.get("chainParameters")
        or data
    )
    if not isinstance(params, list):
        raise ValueError("TRONSCAN 响应缺少 chainParameter")

    def _find_param(key: str):
        for item in params:
            if item.get("key") == key or item.get("name") == key:
                return item.get("value") or item.get("valueStr")
        return None

    value = _find_param("getEnergyFee")
    if value is None:
        value = _find_param("getTransactionFee")
    if value is None:
        raise ValueError("TRONSCAN 响应缺少能量费用参数")
    return _to_int(value)


def get_transaction_status(txid: str) -> tuple:
    """
    查询交易状态
    返回 (success: bool, block_number: int)
    """
    data = _get("transaction-info", {"hash": _normalize_txid(txid)})
    if not data:
        raise ValueError("交易不存在或尚未确认")

    contract_ret = data.get("contractRet") or data.get("contract_result")
    success = contract_ret == "SUCCESS"

    block_number = _to_int(
        data.get("block")
        or data.get("blockNumber")
        or data.get("block_number")
        or 0
    )

    return success, block_number


def get_network_status() -> int:
    """
    获取当前网络区块高度
    """
    data = _get("block", {"sort": "-number", "limit": 1, "start": 0})
    blocks = data.get("data") if isinstance(data, dict) else None
    if not blocks:
        raise KeyError("TRONSCAN 响应缺少区块数据")
    return _to_int(blocks[0].get("number") or blocks[0].get("blockNumber"))


def get_latest_block_info() -> dict:
    """
    获取最新区块信息（用于构建交易）
    """
    data = _get("block", {"sort": "-number", "limit": 1, "start": 0})
    blocks = data.get("data") if isinstance(data, dict) else None
    if not blocks:
        raise ValueError("TRONSCAN 未返回最新区块")
    block = blocks[0]
    return {
        "number": _to_int(block.get("number") or block.get("blockNumber")),
        "hash": block.get("hash") or block.get("blockHash") or block.get("blockID"),
    }


def check_account_risk(address: str) -> dict:
    """
    Checks if a wallet address is flagged with a 'redTag' on TRONSCAN.
    Source Endpoint: https://apilist.tronscanapi.com/api/multiple/chain/query
    
    Args:
        address: TRON 地址 (Base58Check 格式)
    
    Returns:
        包含风险信息的字典:
        - is_risky: 地址是否被标记为恶意
        - risk_type: 风险类型 (e.g. "Scam", "Phishing") 或 "Safe"/"Unknown"
        - detail: 详细说明 (仅当 is_risky=True 时)
    """
    url = "https://apilist.tronscanapi.com/api/multiple/chain/query"
    params = {"address": _normalize_address(address)}
    headers = {"accept": "application/json"}
    
    try:
        response = httpx.get(url, params=params, headers=headers, timeout=TIMEOUT)
        data = response.json()
        
        # 核心判断逻辑
        red_tag = data.get("redTag", "")
        
        if red_tag:
            return {
                "is_risky": True,
                "risk_type": red_tag,  # e.g. "Scam", "Phishing"
                "detail": f"TRONSCAN flagged this address as {red_tag}",
            }
        else:
            return {"is_risky": False, "risk_type": "Safe"}
            
    except Exception as e:
        logging.warning(f"Risk check API failed: {e}")
        return {"is_risky": False, "risk_type": "Unknown"}


def get_account_status(address: str) -> dict:
    """
    检查账户激活状态
    
    返回账户状态信息:
    - is_activated: 账户是否已激活（有过交易历史）
    - has_trx: 账户是否持有 TRX
    - trx_balance: TRX 余额 (SUN)
    - total_transactions: 交易总数
    
    用途：
    1. 向未激活地址转账 TRC20 会消耗更多 Energy（SSTORE 指令）
    2. 如果接收方没有 TRX，可能无法转出代币
    """
    data = _get_account(_normalize_address(address))
    
    # 获取 TRX 余额 (SUN)
    trx_balance = _to_int(
        _first_not_none(
            data.get("balance"),
            data.get("balanceSun"),
            data.get("totalBalance"),
            data.get("total_balance"),
            0,
        )
    )
    
    # 获取交易次数
    total_transactions = _to_int(
        _first_not_none(
            data.get("transactions"),
            data.get("totalTransactionCount"),
            data.get("total_transaction_count"),
            data.get("transactionCount"),
            0,
        )
    )
    
    # 账户是否已激活（有过交易历史或有余额）
    is_activated = total_transactions > 0 or trx_balance > 0
    
    # 是否持有 TRX
    has_trx = trx_balance > 0
    
    return {
        "address": _normalize_address(address),
        "is_activated": is_activated,
        "has_trx": has_trx,
        "trx_balance_sun": trx_balance,
        "trx_balance": trx_balance / 1_000_000,
        "total_transactions": total_transactions,
    }
