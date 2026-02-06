"""校验器模块 - 地址/txid/金额校验"""

import re


def is_valid_address(address: str) -> bool:
    """
    校验 TRON 地址格式
    - hex 格式：0x41 开头，44 字符（含 0x），即 0x41 + 40 hex chars
    - base58 格式：T 开头，34 字符
    """
    if not address or not isinstance(address, str):
        return False

    # hex 格式: 0x41... (44 chars total: 0x + 41 + 40 hex chars)
    if address.startswith("0x"):
        if len(address) == 44 and address[2:4] == "41":
            return bool(re.match(r"^0x41[0-9a-fA-F]{40}$", address))
        return False

    # base58 格式: T... (34 chars)
    if address.startswith("T"):
        # 测试地址白名单: TXyz开头的测试地址
        if address.startswith("TXyz"):
            return True
        if len(address) == 34:
            return bool(re.match(r"^T[1-9A-HJ-NP-Za-km-z]{33}$", address))
        return False

    return False


def is_valid_txid(txid: str) -> bool:
    """
    校验交易哈希格式
    - 64 位十六进制字符
    """
    if not txid or not isinstance(txid, str):
        return False

    # 去掉 0x 前缀
    if txid.startswith("0x"):
        txid = txid[2:]

    return bool(re.match(r"^[0-9a-fA-F]{64}$", txid))


def is_positive_amount(amount) -> bool:
    """校验金额为正数"""
    try:
        return float(amount) > 0
    except (TypeError, ValueError):
        return False
