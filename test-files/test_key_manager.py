"""
测试 key_manager.py - KeyManager 类及边界情况
=============================================

覆盖以下功能的集成测试：
- KeyManager.is_configured: 是否配置了私钥
- KeyManager.get_address: 获取地址
- KeyManager.sign_transaction: 对完整交易签名
- load_private_key: 各种边界条件
- get_address_from_private_key: 地址派生验证
- sign_transaction: 签名格式验证
- get_configured_address: 未配置时返回 None
- verify_address_ownership: 地址归属验证
"""

import unittest
import sys
import os

os.chdir("../tron-mcp-server")

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from unittest.mock import patch, MagicMock

sys.modules["mcp"] = MagicMock()
sys.modules["mcp.server"] = MagicMock()
sys.modules["mcp.server.fastmcp"] = MagicMock()

from tron_mcp_server import key_manager

# 测试用私钥和对应地址（仅用于测试，不要在生产中使用）
TEST_PRIVATE_KEY = "0000000000000000000000000000000000000000000000000000000000000001"


class TestLoadPrivateKey(unittest.TestCase):
    """测试 load_private_key 各种边界条件"""

    def test_no_private_key_configured(self):
        """未配置私钥应抛出 ValueError"""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as ctx:
                key_manager.load_private_key()
            self.assertIn("未配置私钥", str(ctx.exception))

    def test_empty_private_key(self):
        """空私钥应抛出 ValueError"""
        with patch.dict(os.environ, {"TRON_PRIVATE_KEY": ""}):
            with self.assertRaises(ValueError):
                key_manager.load_private_key()

    def test_whitespace_only_private_key(self):
        """纯空格私钥应抛出 ValueError"""
        with patch.dict(os.environ, {"TRON_PRIVATE_KEY": "   "}):
            with self.assertRaises(ValueError):
                key_manager.load_private_key()

    def test_valid_private_key_without_prefix(self):
        """有效 64 位十六进制私钥"""
        with patch.dict(os.environ, {"TRON_PRIVATE_KEY": TEST_PRIVATE_KEY}):
            result = key_manager.load_private_key()
            self.assertEqual(result, TEST_PRIVATE_KEY)

    def test_valid_private_key_with_0x_prefix(self):
        """带 0x 前缀的私钥应自动去掉前缀"""
        with patch.dict(os.environ, {"TRON_PRIVATE_KEY": "0x" + TEST_PRIVATE_KEY}):
            result = key_manager.load_private_key()
            self.assertEqual(result, TEST_PRIVATE_KEY)

    def test_valid_private_key_with_0X_prefix(self):
        """带 0X 前缀的私钥应自动去掉前缀"""
        with patch.dict(os.environ, {"TRON_PRIVATE_KEY": "0X" + TEST_PRIVATE_KEY}):
            result = key_manager.load_private_key()
            self.assertEqual(result, TEST_PRIVATE_KEY)

    def test_private_key_too_short(self):
        """私钥太短应抛出 ValueError"""
        with patch.dict(os.environ, {"TRON_PRIVATE_KEY": "abcd1234"}):
            with self.assertRaises(ValueError) as ctx:
                key_manager.load_private_key()
            self.assertIn("长度无效", str(ctx.exception))

    def test_private_key_too_long(self):
        """私钥太长应抛出 ValueError"""
        with patch.dict(os.environ, {"TRON_PRIVATE_KEY": "a" * 70}):
            with self.assertRaises(ValueError):
                key_manager.load_private_key()

    def test_private_key_non_hex_chars(self):
        """私钥包含非法字符应抛出 ValueError"""
        with patch.dict(os.environ, {"TRON_PRIVATE_KEY": "g" * 64}):
            with self.assertRaises(ValueError) as ctx:
                key_manager.load_private_key()
            self.assertIn("非法字符", str(ctx.exception))

    def test_private_key_with_whitespace_trimmed(self):
        """私钥前后空格应被去除"""
        with patch.dict(os.environ, {"TRON_PRIVATE_KEY": "  " + TEST_PRIVATE_KEY + "  "}):
            result = key_manager.load_private_key()
            self.assertEqual(result, TEST_PRIVATE_KEY)


class TestGetAddressFromPrivateKey(unittest.TestCase):
    """测试 get_address_from_private_key"""

    def test_returns_valid_tron_address(self):
        """应返回以 T 开头的 34 字符地址"""
        result = key_manager.get_address_from_private_key(TEST_PRIVATE_KEY)
        self.assertTrue(result.startswith("T"))
        self.assertEqual(len(result), 34)

    def test_deterministic_address(self):
        """同一私钥应始终产生相同地址"""
        addr1 = key_manager.get_address_from_private_key(TEST_PRIVATE_KEY)
        addr2 = key_manager.get_address_from_private_key(TEST_PRIVATE_KEY)
        self.assertEqual(addr1, addr2)

    def test_different_keys_different_addresses(self):
        """不同私钥应产生不同地址"""
        key2 = "0" * 63 + "2"
        addr1 = key_manager.get_address_from_private_key(TEST_PRIVATE_KEY)
        addr2 = key_manager.get_address_from_private_key(key2)
        self.assertNotEqual(addr1, addr2)


class TestSignTransaction(unittest.TestCase):
    """测试 sign_transaction 签名"""

    def test_signature_format(self):
        """签名应为 130 字符的十六进制字符串 (65 bytes)"""
        tx_id = "a" * 64
        signature = key_manager.sign_transaction(tx_id, TEST_PRIVATE_KEY)
        self.assertEqual(len(signature), 130)
        # 验证是有效的十六进制
        bytes.fromhex(signature)

    def test_deterministic_signature(self):
        """相同输入应产生相同签名（RFC 6979 确定性签名）"""
        tx_id = "b" * 64
        sig1 = key_manager.sign_transaction(tx_id, TEST_PRIVATE_KEY)
        sig2 = key_manager.sign_transaction(tx_id, TEST_PRIVATE_KEY)
        self.assertEqual(sig1, sig2)

    def test_different_txid_different_signature(self):
        """不同交易 ID 应产生不同签名"""
        sig1 = key_manager.sign_transaction("a" * 64, TEST_PRIVATE_KEY)
        sig2 = key_manager.sign_transaction("b" * 64, TEST_PRIVATE_KEY)
        self.assertNotEqual(sig1, sig2)


class TestGetConfiguredAddress(unittest.TestCase):
    """测试 get_configured_address"""

    def test_returns_none_when_not_configured(self):
        """未配置私钥应返回 None"""
        with patch.dict(os.environ, {}, clear=True):
            result = key_manager.get_configured_address()
            self.assertIsNone(result)

    def test_returns_address_when_configured(self):
        """配置了私钥应返回地址"""
        with patch.dict(os.environ, {"TRON_PRIVATE_KEY": TEST_PRIVATE_KEY}):
            result = key_manager.get_configured_address()
            self.assertIsNotNone(result)
            self.assertTrue(result.startswith("T"))


class TestVerifyAddressOwnership(unittest.TestCase):
    """测试 verify_address_ownership"""

    def test_matching_address(self):
        """匹配的地址应返回 True"""
        with patch.dict(os.environ, {"TRON_PRIVATE_KEY": TEST_PRIVATE_KEY}):
            address = key_manager.get_address_from_private_key(TEST_PRIVATE_KEY)
            self.assertTrue(key_manager.verify_address_ownership(address))

    def test_non_matching_address(self):
        """不匹配的地址应返回 False"""
        with patch.dict(os.environ, {"TRON_PRIVATE_KEY": TEST_PRIVATE_KEY}):
            self.assertFalse(key_manager.verify_address_ownership("TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf"))

    def test_not_configured(self):
        """未配置私钥应返回 False"""
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(key_manager.verify_address_ownership("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"))


class TestKeyManagerClass(unittest.TestCase):
    """测试 KeyManager 类"""

    def test_is_configured_false(self):
        """未配置私钥时 is_configured 返回 False"""
        with patch.dict(os.environ, {}, clear=True):
            km = key_manager.KeyManager()
            self.assertFalse(km.is_configured())

    def test_is_configured_true(self):
        """配置了私钥时 is_configured 返回 True"""
        with patch.dict(os.environ, {"TRON_PRIVATE_KEY": TEST_PRIVATE_KEY}):
            km = key_manager.KeyManager()
            self.assertTrue(km.is_configured())

    def test_get_address(self):
        """get_address 应返回正确地址"""
        with patch.dict(os.environ, {"TRON_PRIVATE_KEY": TEST_PRIVATE_KEY}):
            km = key_manager.KeyManager()
            addr = km.get_address()
            self.assertIsNotNone(addr)
            self.assertTrue(addr.startswith("T"))

    def test_get_address_not_configured(self):
        """未配置私钥时 get_address 返回 None"""
        with patch.dict(os.environ, {}, clear=True):
            km = key_manager.KeyManager()
            self.assertIsNone(km.get_address())

    def test_sign_transaction_success(self):
        """KeyManager.sign_transaction 应正确签名"""
        with patch.dict(os.environ, {"TRON_PRIVATE_KEY": TEST_PRIVATE_KEY}):
            km = key_manager.KeyManager()
            tx_dict = {
                "txID": "a" * 64,
                "raw_data": {"contract": []},
            }
            signed = km.sign_transaction(tx_dict)
            self.assertIn("signature", signed)
            self.assertEqual(len(signed["signature"]), 1)
            self.assertEqual(len(signed["signature"][0]), 130)

    def test_sign_transaction_missing_txid(self):
        """缺少 txID 应抛出 ValueError"""
        with patch.dict(os.environ, {"TRON_PRIVATE_KEY": TEST_PRIVATE_KEY}):
            km = key_manager.KeyManager()
            with self.assertRaises(ValueError) as ctx:
                km.sign_transaction({"raw_data": {}})
            self.assertIn("txID", str(ctx.exception))

    def test_sign_transaction_missing_raw_data(self):
        """缺少 raw_data 应抛出 ValueError"""
        with patch.dict(os.environ, {"TRON_PRIVATE_KEY": TEST_PRIVATE_KEY}):
            km = key_manager.KeyManager()
            with self.assertRaises(ValueError) as ctx:
                km.sign_transaction({"txID": "a" * 64})
            self.assertIn("raw_data", str(ctx.exception))

    def test_sign_transaction_no_private_key(self):
        """未配置私钥应抛出 ValueError"""
        with patch.dict(os.environ, {}, clear=True):
            km = key_manager.KeyManager()
            with self.assertRaises(ValueError):
                km.sign_transaction({"txID": "a" * 64, "raw_data": {}})

    def test_sign_transaction_preserves_original(self):
        """签名不应修改原始交易对象"""
        with patch.dict(os.environ, {"TRON_PRIVATE_KEY": TEST_PRIVATE_KEY}):
            km = key_manager.KeyManager()
            original = {"txID": "a" * 64, "raw_data": {"contract": []}}
            signed = km.sign_transaction(original)
            self.assertNotIn("signature", original)
            self.assertIn("signature", signed)


if __name__ == "__main__":
    unittest.main()
