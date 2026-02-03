"""交易构建模块 - 构造未签名交易"""

import time
import hashlib
from . import tron_client
from . import validators


# USDT TRC20 合约地址
USDT_CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"


def _timestamp_ms() -> int:
    """获取当前时间戳（毫秒）"""
    return int(time.time() * 1000)


def _get_ref_block() -> tuple:
    """
    获取参考区块信息
    返回 (ref_block_bytes, ref_block_hash)
    """
    block_info = tron_client.get_latest_block_info()
    block_num = block_info["number"]
    block_hash = block_info["hash"]
    
    ref_block_bytes = hex(block_num & 0xFFFF)[2:].zfill(4)
    ref_block_hash = block_hash[16:32] if len(block_hash) >= 32 else block_hash[:8]
    
    return (ref_block_bytes, ref_block_hash)


def _encode_transfer(to: str, amount: int) -> str:
    """编码 TRC20 transfer 函数调用"""
    method_sig = "a9059cbb"
    addr_hex = to.zfill(64)
    amount_hex = hex(amount)[2:].zfill(64)
    return method_sig + addr_hex + amount_hex


def _trigger_smart_contract(to: str, amount: float, from_addr: str, token: str) -> dict:
    """构建 TRC20 转账交易"""
    timestamp = _timestamp_ms()
    ref_block_bytes, ref_block_hash = _get_ref_block()
    amount_raw = int(amount * 1_000_000)
    
    raw_data = {
        "contract": [
            {
                "parameter": {
                    "value": {
                        "data": _encode_transfer(to, amount_raw),
                        "owner_address": from_addr,
                        "contract_address": USDT_CONTRACT,
                    },
                    "type_url": "type.googleapis.com/protocol.TriggerSmartContract",
                },
                "type": "TriggerSmartContract",
            }
        ],
        "ref_block_bytes": ref_block_bytes,
        "ref_block_hash": ref_block_hash,
        "expiration": timestamp + 60 * 1000,
        "timestamp": timestamp,
    }
    
    tx_id = hashlib.sha256(str(raw_data).encode()).hexdigest()
    return {"txID": tx_id, "raw_data": raw_data}


def _build_trx_transfer(from_addr: str, to_addr: str, amount: float) -> dict:
    """构建 TRX 原生转账交易"""
    timestamp = _timestamp_ms()
    ref_block_bytes, ref_block_hash = _get_ref_block()
    amount_sun = int(amount * 1_000_000)
    
    raw_data = {
        "contract": [
            {
                "parameter": {
                    "value": {
                        "amount": amount_sun,
                        "owner_address": from_addr,
                        "to_address": to_addr,
                    },
                    "type_url": "type.googleapis.com/protocol.TransferContract",
                },
                "type": "TransferContract",
            }
        ],
        "ref_block_bytes": ref_block_bytes,
        "ref_block_hash": ref_block_hash,
        "expiration": timestamp + 60 * 1000,
        "timestamp": timestamp,
    }
    
    tx_id = hashlib.sha256(str(raw_data).encode()).hexdigest()
    return {"txID": tx_id, "raw_data": raw_data}


def build_unsigned_tx(
    from_address: str,
    to_address: str,
    amount: float,
    token: str = "USDT",
) -> dict:
    """
    构建未签名交易

    Args:
        from_address: 发送方地址
        to_address: 接收方地址
        amount: 转账金额
        token: 代币类型 (USDT 或 TRX)

    Returns:
        TRON 标准未签名交易结构 (txID + raw_data)

    Raises:
        ValueError: 参数无效时抛出
    """
    if not validators.is_positive_amount(amount):
        raise ValueError(f"金额必须为正数: {amount}")

    token_upper = token.upper()
    if token_upper not in ("USDT", "TRX"):
        raise ValueError(f"不支持的代币类型: {token}")

    if token_upper == "USDT":
        return _trigger_smart_contract(to_address, amount, from_address, token_upper)
    else:
        return _build_trx_transfer(from_address, to_address, amount)
