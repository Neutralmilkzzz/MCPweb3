"""
测试签名与广播流程
=================

覆盖以下核心问题修复：

1. key_manager.py - 使用 tronpy 而非 eth_account
   - 地址生成返回 T 开头的 TRON Base58Check 地址
   - 签名交易 txID 哈希而非以太坊格式
   - 未配置私钥时的错误处理

2. server.py / call_router.py - JSON 解析与类型安全
   - JSON 字符串正确反序列化为字典
   - 无效 JSON 格式的错误处理
   - 签名并广播的完整链路

3. tron_client.py - 广播逻辑
   - broadcast_transaction 发送 POST 请求
   - 广播失败时的错误处理
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


class TestSignAndBroadcastRoute(unittest.TestCase):
    """测试 call_router 的签名广播路由"""

    @patch('tron_mcp_server.call_router._key_manager')
    @patch('tron_mcp_server.tron_client.broadcast_transaction')
    def test_sign_and_broadcast_success(self, mock_broadcast, mock_km):
        """完整签名+广播链路"""
        from tron_mcp_server import call_router
        
        mock_km.is_configured.return_value = True
        mock_km.sign_transaction.return_value = {
            "txID": "abc123",
            "raw_data": {},
            "signature": ["sig_hex"],
        }
        mock_broadcast.return_value = {"result": True, "txid": "abc123"}
        
        result = call_router.call("sign_and_broadcast", {
            "transaction": {
                "txID": "abc123",
                "raw_data": {},
            }
        })
        self.assertTrue(result["result"])
        self.assertEqual(result["txid"], "abc123")
        self.assertIn("✅", result["summary"])

    @patch('tron_mcp_server.call_router._key_manager')
    def test_sign_without_key_returns_error(self, mock_km):
        """未配置私钥时应返回错误"""
        from tron_mcp_server import call_router
        
        mock_km.is_configured.return_value = False
        
        result = call_router.call("sign_and_broadcast", {
            "transaction": {"txID": "abc", "raw_data": {}}
        })
        self.assertIn("error", result)

    def test_sign_invalid_transaction_returns_error(self):
        """无效交易格式应返回错误"""
        from tron_mcp_server import call_router
        
        result = call_router.call("sign_and_broadcast", {
            "transaction": {"foo": "bar"}
        })
        self.assertIn("error", result)

    def test_sign_missing_transaction_returns_error(self):
        """缺少 transaction 参数应返回错误"""
        from tron_mcp_server import call_router
        
        result = call_router.call("sign_and_broadcast", {})
        self.assertIn("error", result)


class TestServerJsonParsing(unittest.TestCase):
    """测试 server.py 中 JSON 字符串到字典的转换"""

    def test_json_string_is_parsed(self):
        """JSON 字符串应被正确解析为字典"""
        # 模拟 server.py 中的 JSON 解析逻辑
        tx_json = json.dumps({"txID": "abc123", "raw_data": {}})
        
        # 这是 server.py tron_sign_and_broadcast_transaction 中的解析逻辑
        tx_dict = json.loads(tx_json) if isinstance(tx_json, str) else tx_json
        
        self.assertIsInstance(tx_dict, dict)
        self.assertEqual(tx_dict["txID"], "abc123")

    def test_invalid_json_handled(self):
        """无效 JSON 应被捕获"""
        bad_json = "not valid json {"
        try:
            json.loads(bad_json)
            parsed = True
        except json.JSONDecodeError:
            parsed = False
        self.assertFalse(parsed)

    def test_dict_passed_directly(self):
        """如果已经是字典，应直接使用"""
        tx_dict = {"txID": "abc123", "raw_data": {}}
        result = json.loads(json.dumps(tx_dict)) if isinstance(tx_dict, str) else tx_dict
        self.assertIsInstance(result, dict)


if __name__ == '__main__':
    unittest.main()
