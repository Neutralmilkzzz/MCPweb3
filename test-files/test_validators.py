"""
测试 validators.py 模块
=====================

覆盖以下验证函数：
- is_valid_address: 各种地址格式的验证（T开头34字符、Hex格式、0x41开头）
- is_valid_txid: 交易哈希格式验证（64位hex、带0x前缀、过短、非hex）
- is_positive_amount: 金额验证（正数、零、负数、字符串数字、None）
"""

import unittest
import sys
import os

os.chdir("../tron-mcp-server")

# 强制 UTF-8 编码
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# 将项目目录加入 path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from unittest.mock import MagicMock

# 模拟 mcp 依赖
sys.modules["mcp"] = MagicMock()
sys.modules["mcp.server"] = MagicMock()
sys.modules["mcp.server.fastmcp"] = MagicMock()

from tron_mcp_server import validators


class TestIsValidAddress(unittest.TestCase):
    """测试 is_valid_address 函数"""

    def test_valid_base58_address(self):
        """T开头的34字符Base58地址应该有效"""
        valid_addresses = [
            "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            "TMVQGm1qAQYVdetCeGRRkTWYYrLXuHK2HC",
        ]
        for addr in valid_addresses:
            with self.subTest(addr=addr):
                self.assertTrue(validators.is_valid_address(addr))

    def test_valid_hex_address(self):
        """0x41开头的44字符Hex地址应该有效"""
        valid_hex = "0x410000000000000000000000000000000000000000"
        self.assertTrue(validators.is_valid_address(valid_hex))

    def test_invalid_address_no_prefix(self):
        """没有正确前缀的地址应该无效"""
        invalid_addresses = [
            "ALa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",  # 以A开头
            "1La2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",   # 以1开头（比特币格式）
            "0x400000000000000000000000000000000000000000",  # 0x40开头（非0x41）
        ]
        for addr in invalid_addresses:
            with self.subTest(addr=addr):
                self.assertFalse(validators.is_valid_address(addr))

    def test_invalid_address_wrong_length(self):
        """长度不正确的地址应该无效"""
        self.assertFalse(validators.is_valid_address("T123"))  # 太短
        # Bug Fix: 移除宽松校验，严格要求 34 字符
        self.assertFalse(validators.is_valid_address("T" + "a" * 100))  # 长度错误
        self.assertFalse(validators.is_valid_address("T" + "a" * 20))   # 长度错误
        self.assertFalse(validators.is_valid_address("0x41" + "0" * 30))  # Hex太短

    def test_invalid_address_lenient_validation_bug(self):
        """测试修复：以 T 开头但格式错误的地址应该被拦截"""
        # Bug 修复前会通过宽松校验（len >= 20）的无效地址
        invalid_addresses = [
            "Thisisnot_a_valid_address!!",  # 包含非法字符
            "T" + "0" * 33,  # 包含数字 0（Base58 不允许）
            "T" + "O" * 33,  # 包含字母 O（Base58 不允许）
            "T" + "I" * 33,  # 包含字母 I（Base58 不允许）
            "T" + "l" * 33,  # 包含字母 l（Base58 不允许）
        ]
        for addr in invalid_addresses:
            with self.subTest(addr=addr):
                self.assertFalse(validators.is_valid_address(addr),
                                 f"地址 {addr} 应该被校验为无效")


    def test_empty_address(self):
        """空字符串应该无效"""
        self.assertFalse(validators.is_valid_address(""))

    def test_none_address(self):
        """None应该无效"""
        self.assertFalse(validators.is_valid_address(None))

    def test_non_string_address(self):
        """非字符串类型应该无效"""
        self.assertFalse(validators.is_valid_address(12345))
        self.assertFalse(validators.is_valid_address([]))
        self.assertFalse(validators.is_valid_address({}))


class TestIsValidTxid(unittest.TestCase):
    """测试 is_valid_txid 函数"""

    def test_valid_txid_64_chars(self):
        """64位hex字符串应该有效"""
        valid_txids = [
            "a" * 64,
            "1234567890abcdef" * 4,
            "ABCDEF0123456789" * 4,
        ]
        for txid in valid_txids:
            with self.subTest(txid=txid):
                self.assertTrue(validators.is_valid_txid(txid))

    def test_valid_txid_with_0x_prefix(self):
        """带0x前缀的64位hex字符串应该有效"""
        txid = "0x" + "a" * 64
        self.assertTrue(validators.is_valid_txid(txid))

    def test_invalid_txid_too_short(self):
        """少于64位的hex字符串应该无效"""
        self.assertFalse(validators.is_valid_txid("a" * 63))
        self.assertFalse(validators.is_valid_txid("abc123"))

    def test_invalid_txid_too_long(self):
        """多于64位的hex字符串应该无效"""
        self.assertFalse(validators.is_valid_txid("a" * 65))

    def test_invalid_txid_non_hex(self):
        """包含非hex字符的字符串应该无效"""
        invalid_txids = [
            "g" * 64,  # g不是hex字符
            "xyz" + "0" * 61,
            "abcdefgh" * 8,
        ]
        for txid in invalid_txids:
            with self.subTest(txid=txid):
                self.assertFalse(validators.is_valid_txid(txid))

    def test_empty_txid(self):
        """空字符串应该无效"""
        self.assertFalse(validators.is_valid_txid(""))

    def test_none_txid(self):
        """None应该无效"""
        self.assertFalse(validators.is_valid_txid(None))

    def test_non_string_txid(self):
        """非字符串类型应该无效"""
        self.assertFalse(validators.is_valid_txid(12345))
        self.assertFalse(validators.is_valid_txid([]))


class TestIsPositiveAmount(unittest.TestCase):
    """测试 is_positive_amount 函数"""

    def test_positive_number(self):
        """正数应该有效"""
        valid_amounts = [1, 0.1, 100, 1000.5, 0.000001]
        for amount in valid_amounts:
            with self.subTest(amount=amount):
                self.assertTrue(validators.is_positive_amount(amount))

    def test_zero(self):
        """零应该无效"""
        self.assertFalse(validators.is_positive_amount(0))
        self.assertFalse(validators.is_positive_amount(0.0))

    def test_negative_number(self):
        """负数应该无效"""
        invalid_amounts = [-1, -0.1, -1000]
        for amount in invalid_amounts:
            with self.subTest(amount=amount):
                self.assertFalse(validators.is_positive_amount(amount))

    def test_string_number(self):
        """字符串形式的数字"""
        self.assertTrue(validators.is_positive_amount("1"))
        self.assertTrue(validators.is_positive_amount("100.5"))
        self.assertFalse(validators.is_positive_amount("0"))
        self.assertFalse(validators.is_positive_amount("-1"))

    def test_invalid_string(self):
        """非数字字符串应该无效"""
        self.assertFalse(validators.is_positive_amount("abc"))
        self.assertFalse(validators.is_positive_amount(""))

    def test_none(self):
        """None应该无效"""
        self.assertFalse(validators.is_positive_amount(None))

    def test_non_numeric_types(self):
        """非数字类型应该无效"""
        self.assertFalse(validators.is_positive_amount([]))
        self.assertFalse(validators.is_positive_amount({}))
        self.assertFalse(validators.is_positive_amount([1, 2, 3]))


if __name__ == "__main__":
    unittest.main()
