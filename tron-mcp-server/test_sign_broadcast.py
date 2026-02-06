"""
测试签名与广播流程
=================

覆盖以下核心问题修复：

1. key_manager.py - 使用 tronpy 而非 eth_account
   - 地址生成返回 T 开头的 TRON Base58Check 地址
   - 签名交易 txID 哈希而非以太坊格式
   - 未配置私钥时的错误处理

2. tron_client.py - 广播逻辑
   - broadcast_transaction 发送 POST 请求
   - 广播失败时的错误处理

注意：sign_and_broadcast 路由和 tron_sign_and_broadcast_transaction 工具
已在工具精简中被删除，相关测试已移除。
"""

import unittest
from unittest.mock import patch, MagicMock, PropertyMock
import sys
import os
import json

# 强制 UTF-8 编码
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# 将项目目录加入 path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 模拟 mcp 依赖
sys.modules["mcp"] = MagicMock()
sys.modules["mcp.server"] = MagicMock()
sys.modules["mcp.server.fastmcp"] = MagicMock()


class TestKeyManager(unittest.TestCase):
    """测试 KeyManager 使用 tronpy 而非 eth_account"""

    @patch.dict(os.environ, {"TRON_PRIVATE_KEY": ""})
    def test_no_key_configured(self):
        """未配置私钥时 is_configured 应返回 False"""
        from tron_mcp_server.key_manager import KeyManager
        km = KeyManager()
        self.assertFalse(km.is_configured())
        self.assertIsNone(km.get_address())

    @patch.dict(os.environ, {"TRON_PRIVATE_KEY": ""})
    def test_sign_without_key_raises_error(self):
        """未配置私钥时签名应抛出 ValueError"""
        from tron_mcp_server.key_manager import KeyManager
        km = KeyManager()
        tx = {"txID": "abc123", "raw_data": {}}
        with self.assertRaises(ValueError) as cm:
            km.sign_transaction(tx)
        self.assertIn("私钥未配置", str(cm.exception))

    def test_address_starts_with_t(self):
        """使用 tronpy 生成的地址应以 T 开头（非 0x）"""
        from tronpy.keys import PrivateKey
        pk = PrivateKey.random()
        hex_key = pk.hex()

        with patch.dict(os.environ, {"TRON_PRIVATE_KEY": hex_key}):
            from tron_mcp_server.key_manager import KeyManager
            km = KeyManager()
            self.assertTrue(km.is_configured())
            addr = km.get_address()
            self.assertIsNotNone(addr)
            self.assertTrue(addr.startswith("T"), f"地址应以 T 开头，实际: {addr}")
            self.assertEqual(len(addr), 34, f"TRON 地址长度应为 34，实际: {len(addr)}")

    def test_sign_transaction_adds_signature(self):
        """签名后交易应包含 signature 字段"""
        from tronpy.keys import PrivateKey
        pk = PrivateKey.random()
        hex_key = pk.hex()

        with patch.dict(os.environ, {"TRON_PRIVATE_KEY": hex_key}):
            from tron_mcp_server.key_manager import KeyManager
            km = KeyManager()
            
            # 构造一个模拟的 txID（64 字符 hex 字符串）
            tx = {
                "txID": "a" * 64,
                "raw_data": {"contract": [], "ref_block_bytes": "1234"},
            }
            signed = km.sign_transaction(tx)
            self.assertIn("signature", signed)
            self.assertIsInstance(signed["signature"], list)
            self.assertEqual(len(signed["signature"]), 1)
            # 签名应为 hex 字符串
            self.assertTrue(all(c in '0123456789abcdef' for c in signed["signature"][0]))

    def test_sign_missing_txid_raises_error(self):
        """缺少 txID 时签名应抛出 ValueError"""
        from tronpy.keys import PrivateKey
        pk = PrivateKey.random()
        hex_key = pk.hex()

        with patch.dict(os.environ, {"TRON_PRIVATE_KEY": hex_key}):
            from tron_mcp_server.key_manager import KeyManager
            km = KeyManager()
            tx = {"raw_data": {}}
            with self.assertRaises(ValueError) as cm:
                km.sign_transaction(tx)
            self.assertIn("txID", str(cm.exception))

    def test_sign_missing_raw_data_raises_error(self):
        """缺少 raw_data 时签名应抛出 ValueError"""
        from tronpy.keys import PrivateKey
        pk = PrivateKey.random()
        hex_key = pk.hex()

        with patch.dict(os.environ, {"TRON_PRIVATE_KEY": hex_key}):
            from tron_mcp_server.key_manager import KeyManager
            km = KeyManager()
            tx = {"txID": "a" * 64}
            with self.assertRaises(ValueError) as cm:
                km.sign_transaction(tx)
            self.assertIn("raw_data", str(cm.exception))


class TestBroadcastTransaction(unittest.TestCase):
    """测试 tron_client.broadcast_transaction"""

    @patch('tron_mcp_server.tron_client.httpx.post')
    def test_broadcast_success(self, mock_post):
        """广播成功时返回 result=True 和 txid"""
        from tron_mcp_server import tron_client
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": True, "txid": "abc123"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        
        signed_tx = {
            "txID": "abc123",
            "raw_data": {},
            "signature": ["deadbeef"],
        }
        result = tron_client.broadcast_transaction(signed_tx)
        self.assertTrue(result["result"])
        self.assertEqual(result["txid"], "abc123")

    @patch('tron_mcp_server.tron_client.httpx.post')
    def test_broadcast_failure(self, mock_post):
        """广播失败时抛出 ValueError"""
        from tron_mcp_server import tron_client
        
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": False, "message": "Duplicate transaction"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        
        signed_tx = {
            "txID": "abc123",
            "raw_data": {},
            "signature": ["deadbeef"],
        }
        with self.assertRaises(ValueError) as cm:
            tron_client.broadcast_transaction(signed_tx)
        self.assertIn("广播失败", str(cm.exception))

    def test_broadcast_no_signature_raises(self):
        """未签名的交易不应广播"""
        from tron_mcp_server import tron_client
        
        tx = {"txID": "abc123", "raw_data": {}}
        with self.assertRaises(ValueError) as cm:
            tron_client.broadcast_transaction(tx)
        self.assertIn("signature", str(cm.exception))


if __name__ == '__main__':
    unittest.main()
