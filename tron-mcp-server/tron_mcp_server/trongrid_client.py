"""TronGrid API 客户端 — 交易构建与广播

与 tron_client.py (TRONSCAN) 的区别:
- TRONSCAN: 用于数据查询（余额、交易状态、Gas 参数、安全检查）
- TronGrid: 用于交易操作（构建真实交易、广播签名交易）

TronGrid 返回的交易包含 protobuf 序列化的 raw_data_hex 和正确的 txID,
可直接用于签名和广播。
"""

import os
import logging
from decimal import Decimal
from typing import Optional

import httpx
import base58

from . import config

logger = logging.getLogger(__name__)


# ============ 配置 ============

TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "15.0"))

# USDT TRC20 合约地址 — 根据 TRON_NETWORK 自动切换
USDT_CONTRACT_BASE58 = config.get_usdt_contract()

# TRC20 转账的 fee_limit (SUN), 默认 100 TRX
DEFAULT_FEE_LIMIT = int(os.getenv("TRONGRID_FEE_LIMIT", "100000000"))

# SUN 与 TRX 的转换倍数
SUN_PER_TRX = 1_000_000


def _get_trongrid_url() -> str:
    """获取 TronGrid API URL"""
    return config.get_trongrid_url()


def _get_headers() -> dict:
    """获取请求头, 支持 TronGrid API Key"""
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    api_key = config.get_trongrid_api_key()
    if api_key:
        headers["TRON-PRO-API-KEY"] = api_key
    return headers


def _post(path: str, data: dict) -> dict:
    """发送 POST 请求到 TronGrid"""
    url = f"{_get_trongrid_url()}/{path.lstrip('/')}"
    response = httpx.post(url, json=data, headers=_get_headers(), timeout=TIMEOUT)
    response.raise_for_status()
    result = response.json()
    if result is None:
        raise ValueError("TronGrid 响应为空")
    return result


# ============ 地址转换 ============

def _base58_to_hex(address: str) -> str:
    """
    将 Base58Check 地址转换为 Hex 格式 (不含 0x 前缀)

    例: TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf → 41a614f803b6fd780986a42c78ec9c7f77e6ded13c
    """
    if address.startswith("0x") and len(address) == 44:
        # 已经是 0x41... Hex 格式, 去掉 0x
        return address[2:]

    if address.startswith("41") and len(address) == 42:
        # 已经是 41... Hex 格式
        return address

    # Base58Check → Hex
    try:
        raw = base58.b58decode_check(address)
        return raw.hex()
    except Exception as e:
        raise ValueError(f"无效的 TRON 地址: {address}") from e


# ============ 交易构建 ============

def build_trx_transfer(
    owner_address: str,
    to_address: str,
    amount_trx: float,
    extra_data: Optional[str] = None,
) -> dict:
    """
    通过 TronGrid API 构建 TRX 原生转账交易

    Args:
        owner_address: 发送方地址 (Base58 或 Hex)
        to_address: 接收方地址 (Base58 或 Hex)
        amount_trx: 转账金额 (TRX)
        extra_data: 交易备注的十六进制编码（可选）。
                    对应 Transaction.raw.data 字段 (Proto field 10)。
                    例如 "hello".encode("utf-8").hex() → "68656c6c6f"

    Returns:
        TronGrid 返回的完整未签名交易:
        {
            "txID": "...",
            "raw_data": {...},
            "raw_data_hex": "..."
        }

    Raises:
        ValueError: 参数无效或 API 返回错误
    """
    amount_sun = int(Decimal(str(amount_trx)) * SUN_PER_TRX)

    data = {
        "owner_address": _base58_to_hex(owner_address),
        "to_address": _base58_to_hex(to_address),
        "amount": amount_sun,
        "visible": False,
    }
    
    # 添加 memo（备注）
    if extra_data:
        data["extra_data"] = extra_data

    result = _post("wallet/createtransaction", data)

    # 检查 TronGrid 返回
    if "Error" in result:
        raise ValueError(f"TronGrid 构建交易失败: {result.get('Error')}")
    if "txID" not in result:
        raise ValueError(f"TronGrid 返回缺少 txID: {result}")

    return result


def build_trc20_transfer(
    owner_address: str,
    to_address: str,
    amount: float,
    contract_address: Optional[str] = None,
    decimals: int = 6,
    fee_limit: Optional[int] = None,
    extra_data: Optional[str] = None,
) -> dict:
    """
    通过 TronGrid API 构建 TRC20 代币转账交易

    Args:
        owner_address: 发送方地址
        to_address: 接收方地址
        amount: 转账金额 (代币单位, 如 100.5 USDT)
        contract_address: TRC20 合约地址, 默认 USDT
        decimals: 代币小数位, 默认 6 (USDT)
        fee_limit: 费用上限 (SUN), 默认 100 TRX
        extra_data: 交易备注的十六进制编码（可选）。
                    对应 Transaction.raw.data 字段 (Proto field 10)。

    Returns:
        TronGrid 返回的完整未签名交易

    Raises:
        ValueError: 参数无效或 API 返回错误
    """
    if contract_address is None:
        contract_address = USDT_CONTRACT_BASE58
    if fee_limit is None:
        fee_limit = DEFAULT_FEE_LIMIT

    # 编码 transfer(address,uint256) 参数
    to_hex = _base58_to_hex(to_address)
    # 去掉 41 前缀，补齐到 64 字符
    to_hex_no_prefix = to_hex[2:] if to_hex.startswith("41") else to_hex
    to_padded = to_hex_no_prefix.zfill(64)

    # 金额转换为最小单位
    amount_raw = int(Decimal(str(amount)) * (10 ** decimals))
    amount_padded = hex(amount_raw)[2:].zfill(64)

    parameter = to_padded + amount_padded

    data = {
        "owner_address": _base58_to_hex(owner_address),
        "contract_address": _base58_to_hex(contract_address),
        "function_selector": "transfer(address,uint256)",
        "parameter": parameter,
        "fee_limit": fee_limit,
        "call_value": 0,
        "visible": False,
    }

    # 添加 memo（备注）
    if extra_data:
        data["extra_data"] = extra_data

    result = _post("wallet/triggersmartcontract", data)

    # 检查结果
    if not result.get("result", {}).get("result", False):
        error_msg = result.get("result", {}).get("message", "Unknown error")
        # TronGrid 返回的 message 可能是 hex 编码
        if isinstance(error_msg, str) and all(c in "0123456789abcdefABCDEF" for c in error_msg):
            try:
                error_msg = bytes.fromhex(error_msg).decode("utf-8", errors="ignore")
            except Exception:
                pass
        raise ValueError(f"TronGrid 构建 TRC20 交易失败: {error_msg}")

    transaction = result.get("transaction")
    if not transaction or "txID" not in transaction:
        raise ValueError(f"TronGrid 响应缺少 transaction 或 txID: {result}")

    return transaction


# ============ 交易广播 ============

def broadcast_transaction(signed_tx: dict) -> dict:
    """
    广播已签名的交易到 TRON 网络

    Args:
        signed_tx: 已签名的交易对象, 必须包含:
            - txID
            - raw_data 或 raw_data_hex
            - signature (列表)

    Returns:
        广播结果:
        {
            "result": True/False,
            "txid": "...",
            "code": "...",       # 仅失败时
            "message": "...",    # 仅失败时
        }

    Raises:
        ValueError: 交易格式无效或广播失败
    """
    # 校验交易完整性
    if "txID" not in signed_tx:
        raise ValueError("签名交易缺少 txID")
    if "signature" not in signed_tx or not signed_tx["signature"]:
        raise ValueError("签名交易缺少 signature")
    if "raw_data" not in signed_tx and "raw_data_hex" not in signed_tx:
        raise ValueError("签名交易缺少 raw_data")

    result = _post("wallet/broadcasttransaction", signed_tx)

    # 检查广播结果
    if not result.get("result", False):
        code = result.get("code", "UNKNOWN")
        message = result.get("message", "")
        # TronGrid 的 message 可能是 hex 编码
        if isinstance(message, str) and len(message) > 0 and all(c in "0123456789abcdefABCDEF" for c in message):
            try:
                message = bytes.fromhex(message).decode("utf-8", errors="ignore")
            except Exception:
                pass
        raise ValueError(f"交易广播失败 [{code}]: {message}")

    return {
        "result": True,
        "txid": signed_tx["txID"],
    }


# ============ 资源查询 ============

def get_account_resource(address: str) -> dict:
    """
    查询账户资源（Energy + Bandwidth）
    
    通过 TronGrid 全节点 API /wallet/getaccountresource 获取真实链上数据。
    
    Args:
        address: TRON 地址（Base58 或 Hex 格式）
    
    Returns:
        TronGrid 返回的原始资源数据字典
    
    Raises:
        ValueError: 地址无效或 API 返回错误
    """
    data = {
        "address": _base58_to_hex(address),
        "visible": False,
    }
    result = _post("wallet/getaccountresource", data)
    
    # 检查错误
    if "Error" in result:
        raise ValueError(f"TronGrid 查询账户资源失败: {result.get('Error')}")
    
    return result
