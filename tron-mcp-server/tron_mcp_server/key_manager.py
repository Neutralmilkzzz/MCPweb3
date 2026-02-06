"""密钥管理模块 - 使用 tronpy 管理 TRON 私钥和签名

使用 tronpy.keys.PrivateKey 处理 TRON 链的地址生成和交易签名，
而非 eth_account（以太坊库，生成 0x 地址，签名格式不兼容 TRON）。
"""

import os
import logging

from tronpy.keys import PrivateKey


class KeyManager:
    """TRON 私钥管理器
    
    从环境变量 TRON_PRIVATE_KEY 加载私钥（十六进制字符串），
    生成 T 开头的 TRON Base58Check 地址，并提供交易签名功能。
    """

    def __init__(self):
        self._priv_key = None
        private_key_hex = os.getenv("TRON_PRIVATE_KEY", "")
        if private_key_hex:
            try:
                self._priv_key = PrivateKey(bytes.fromhex(private_key_hex))
            except (ValueError, Exception) as e:
                logging.error(f"无法加载私钥: {e}")

    def is_configured(self) -> bool:
        """检查私钥是否已配置"""
        return self._priv_key is not None

    def get_address(self) -> str | None:
        """获取 T 开头的 TRON Base58Check 地址"""
        if self._priv_key is None:
            return None
        return self._priv_key.public_key.to_base58check_address()

    def sign_transaction(self, tx_dict: dict) -> dict:
        """签名交易
        
        对 raw_data 的 txID 哈希进行签名，返回包含签名的完整交易字典。
        
        Args:
            tx_dict: 未签名交易字典，必须包含 'txID' 和 'raw_data' 字段
        
        Returns:
            签名后的交易字典（包含 signature 字段）
        
        Raises:
            ValueError: 私钥未配置或交易格式无效
        """
        if self._priv_key is None:
            raise ValueError("私钥未配置，请设置环境变量 TRON_PRIVATE_KEY")

        tx_id = tx_dict.get("txID")
        if not tx_id:
            raise ValueError("交易缺少 txID 字段")

        if "raw_data" not in tx_dict:
            raise ValueError("交易缺少 raw_data 字段")

        # 使用 tronpy PrivateKey 签名 txID 哈希
        sig = self._priv_key.sign_msg_hash(bytes.fromhex(tx_id))

        signed_tx = dict(tx_dict)
        signed_tx["signature"] = [sig.hex()]
        return signed_tx
