"""TRON 客户端模块 - TRONSCAN REST API 封装"""

import os
import hashlib
from typing import Optional
import httpx

# USDT TRC20 合约地址
USDT_CONTRACT_BASE58 = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
USDT_CONTRACT_HEX = "0x41a614f803b6fd780986a42c78ec9c7f77e6ded13c"

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
    raw = bytes.fromhex(hex_addr)
    checksum = hashlib.sha256(hashlib.sha256(raw).digest()).digest()[:4]
    return _b58encode(raw + checksum)


def _b58encode(data: bytes) -> str:
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    num = int.from_bytes(data, "big")
    encoded = ""
    while num > 0:
        num, rem = divmod(num, 58)
        encoded = alphabet[rem] + encoded
    # leading zeros
    pad = 0
    for byte in data:
        if byte == 0:
            pad += 1
        else:
            break
    return "1" * pad + (encoded or "1")


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
    data = _get("chain/parameters")
    params = data.get("chainParameter") or data.get("chainParameters") or data
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
