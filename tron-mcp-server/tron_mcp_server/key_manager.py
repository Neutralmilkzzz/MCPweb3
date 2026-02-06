"""本地私钥管理模块 — 签名与地址派生

安全设计原则:
1. 私钥仅从环境变量 TRON_PRIVATE_KEY 加载，不存储在代码或配置文件中
2. 私钥永远不通过 MCP 工具返回给 AI Agent
3. 签名操作在本地完成，私钥不离开本机
4. 每次使用后建议清除环境变量
"""

import os
import logging
from typing import Optional

import ecdsa
import base58
from Crypto.Hash import keccak as _keccak_mod


# ============ 底层工具 ============

def _keccak256(data: bytes) -> bytes:
    """计算 Keccak-256 哈希"""
    k = _keccak_mod.new(digest_bits=256)
    k.update(data)
    return k.digest()


# ============ 私钥管理 ============

def load_private_key() -> str:
    """
    从环境变量加载私钥

    Returns:
        私钥的十六进制字符串（64 字符, 不含 0x 前缀）

    Raises:
        ValueError: 未配置私钥或格式无效
    """
    pk = os.getenv("TRON_PRIVATE_KEY", "").strip()
    if not pk:
        raise ValueError(
            "未配置私钥。请设置环境变量 TRON_PRIVATE_KEY。"
            "格式: 64 位十六进制字符串（不含 0x 前缀）"
        )

    # 去掉 0x 前缀
    if pk.startswith(("0x", "0X")):
        pk = pk[2:]

    # 校验长度
    if len(pk) != 64:
        raise ValueError(f"私钥长度无效: 期望 64 位十六进制字符，实际 {len(pk)} 位")

    # 校验内容
    try:
        bytes.fromhex(pk)
    except ValueError:
        raise ValueError("私钥包含非法字符，应为纯十六进制字符串")

    return pk


def get_address_from_private_key(private_key_hex: str) -> str:
    """
    从私钥派生 TRON 地址 (Base58Check 格式)

    流程:
    1. 私钥 → secp256k1 公钥 (未压缩, 64 bytes)
    2. 公钥 → Keccak256
    3. 取哈希后 20 bytes → 加 0x41 前缀
    4. Base58Check 编码

    Args:
        private_key_hex: 64 位十六进制私钥字符串

    Returns:
        TRON 地址 (Base58Check 格式, T 开头, 34 字符)
    """
    # 1. 私钥 → 公钥
    sk = ecdsa.SigningKey.from_string(
        bytes.fromhex(private_key_hex),
        curve=ecdsa.SECP256k1,
    )
    vk = sk.get_verifying_key()
    # vk.to_string() 返回 64 bytes (x + y, 不含 04 前缀)
    pub_key_bytes = vk.to_string()

    # 2. Keccak256 哈希
    addr_hash = _keccak256(pub_key_bytes)

    # 3. 取后 20 bytes, 加 41 前缀 (TRON 主网)
    addr_bytes = b"\x41" + addr_hash[-20:]

    # 4. Base58Check 编码
    return base58.b58encode_check(addr_bytes).decode("utf-8")


def sign_transaction(tx_id_hex: str, private_key_hex: str) -> str:
    """
    对交易 ID 进行 ECDSA secp256k1 签名

    TRON 签名格式: r(32 bytes) + s(32 bytes) + recovery_id(1 byte) = 65 bytes

    Args:
        tx_id_hex: 交易 ID (64 位十六进制, 即 raw_data 的 SHA256)
        private_key_hex: 64 位十六进制私钥

    Returns:
        签名的十六进制字符串 (130 字符 = 65 bytes)
    """
    sk = ecdsa.SigningKey.from_string(
        bytes.fromhex(private_key_hex),
        curve=ecdsa.SECP256k1,
    )
    vk = sk.get_verifying_key()
    tx_id_bytes = bytes.fromhex(tx_id_hex)

    # 使用 RFC 6979 确定性签名（防止随机数泄露私钥）
    signature = sk.sign_digest_deterministic(
        tx_id_bytes,
        sigencode=ecdsa.util.sigencode_string,
    )

    # 确定 recovery_id (v)
    # 尝试 recovery_id = 0 和 1, 找到能恢复出原始公钥的那个
    recovery_id = 0
    try:
        recovered_keys = ecdsa.VerifyingKey.from_public_key_recovery_with_digest(
            signature,
            tx_id_bytes,
            curve=ecdsa.SECP256k1,
        )
        for i, recovered_vk in enumerate(recovered_keys):
            if recovered_vk.to_string() == vk.to_string():
                recovery_id = i
                break
    except Exception as e:
        logging.warning(f"recovery_id 推导失败，使用默认值 0: {e}")

    # TRON 签名: r(32) + s(32) + recovery_id(1)
    full_signature = signature + bytes([recovery_id])
    return full_signature.hex()


def get_configured_address() -> Optional[str]:
    """
    获取当前配置的私钥对应的 TRON 地址

    Returns:
        TRON 地址 (Base58Check), 未配置私钥则返回 None
    """
    try:
        pk = load_private_key()
        return get_address_from_private_key(pk)
    except ValueError:
        return None


def verify_address_ownership(address: str) -> bool:
    """
    验证给定地址是否属于当前配置的私钥

    Args:
        address: 待验证的 TRON 地址

    Returns:
        True 表示地址匹配, False 表示不匹配或未配置私钥
    """
    configured = get_configured_address()
    if not configured:
        return False
    return configured == address
