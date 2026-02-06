"""
错误消息优化与结构统一测试
============================

覆盖以下改进项：

1. key_manager.py: load_private_key() 错误消息精简化
   - 未配置私钥的错误消息应简洁但信息完整
   - 私钥长度无效的错误消息应简洁
   - 私钥含非法字符的错误消息应简洁

2. tx_builder.py: check_sender_balance 错误对象结构统一
   - USDT 余额不足的错误对象应含 required/available 字段
   - Gas 不足的错误对象应含 required/available 字段（而非仅 required_sun/available_sun）
   - TRX 余额不足的错误对象应含 required/available 字段（而非仅 required_sun/available_sun）
   - 所有错误对象都应含统一的 code/message/severity/required/available 字段
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

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

from tron_mcp_server.key_manager import load_private_key
from tron_mcp_server.tx_builder import (
    check_sender_balance,
    InsufficientBalanceError,
)


# ============================================================================
# 第一部分：key_manager.py 错误消息测试
# ============================================================================

class TestKeyManagerErrorMessages(unittest.TestCase):
    """
    load_private_key() 的错误消息应精简：
    - 每条消息应为单行（不含换行符）
    - 信息仍然完整（含关键提示）
    """

    @patch.dict(os.environ, {"TRON_PRIVATE_KEY": ""})
    def test_missing_key_error_single_line(self):
        """未配置私钥的错误消息应为单行"""
        with self.assertRaises(ValueError) as cm:
            load_private_key()
        msg = str(cm.exception)
        self.assertNotIn("\n", msg, "错误消息应为单行")
        self.assertIn("TRON_PRIVATE_KEY", msg, "应提及环境变量名")

    @patch.dict(os.environ, {"TRON_PRIVATE_KEY": "abcd1234"})
    def test_invalid_length_error_concise(self):
        """私钥长度无效的错误消息应简洁"""
        with self.assertRaises(ValueError) as cm:
            load_private_key()
        msg = str(cm.exception)
        self.assertIn("64", msg, "应提及期望长度 64")
        self.assertIn("8", msg, "应提及实际长度 8")

    @patch.dict(os.environ, {"TRON_PRIVATE_KEY": "xyz" + "0" * 61})
    def test_invalid_hex_error_concise(self):
        """私钥含非法字符的错误消息应简洁"""
        with self.assertRaises(ValueError) as cm:
            load_private_key()
        msg = str(cm.exception)
        self.assertIn("十六进制", msg, "应提及十六进制")


# ============================================================================
# 第二部分：tx_builder.py 错误对象结构统一测试
# ============================================================================

class TestCheckSenderBalanceErrorStructure(unittest.TestCase):
    """
    check_sender_balance 的错误对象应有统一结构：
    每个错误项都应含 code, message, severity, required, available
    """

    @patch('tron_mcp_server.tron_client.get_balance_trx')
    @patch('tron_mcp_server.tron_client.get_usdt_balance')
    def test_usdt_insufficient_error_has_unified_fields(self, mock_usdt, mock_trx):
        """USDT 余额不足的错误对象应含 required 和 available"""
        mock_trx.return_value = 100.0
        mock_usdt.return_value = 5.0

        with self.assertRaises(InsufficientBalanceError) as cm:
            check_sender_balance("TAddress", 20.0, "USDT")

        errors = cm.exception.details["errors"]
        usdt_error = next(e for e in errors if e["code"] == "insufficient_usdt")
        self.assertIn("required", usdt_error)
        self.assertIn("available", usdt_error)
        self.assertIn("code", usdt_error)
        self.assertIn("message", usdt_error)
        self.assertIn("severity", usdt_error)

    @patch('tron_mcp_server.tron_client.get_balance_trx')
    @patch('tron_mcp_server.tron_client.get_usdt_balance')
    def test_gas_insufficient_error_has_unified_fields(self, mock_usdt, mock_trx):
        """Gas 不足的错误对象应含 required 和 available（除了 required_sun/available_sun）"""
        mock_trx.return_value = 1.0  # 太少，不够 gas
        mock_usdt.return_value = 100.0

        with self.assertRaises(InsufficientBalanceError) as cm:
            check_sender_balance("TAddress", 10.0, "USDT")

        errors = cm.exception.details["errors"]
        gas_error = next(e for e in errors if e["code"] == "insufficient_trx_for_gas")
        # 应有统一的 required/available 字段
        self.assertIn("required", gas_error)
        self.assertIn("available", gas_error)

    @patch('tron_mcp_server.tron_client.get_balance_trx')
    def test_trx_insufficient_error_has_unified_fields(self, mock_trx):
        """TRX 余额不足的错误对象应含 required 和 available（除了 required_sun/available_sun）"""
        mock_trx.return_value = 1.0

        with self.assertRaises(InsufficientBalanceError) as cm:
            check_sender_balance("TAddress", 100.0, "TRX")

        errors = cm.exception.details["errors"]
        trx_error = next(e for e in errors if e["code"] == "insufficient_trx")
        # 应有统一的 required/available 字段
        self.assertIn("required", trx_error)
        self.assertIn("available", trx_error)

    @patch('tron_mcp_server.tron_client.get_balance_trx')
    @patch('tron_mcp_server.tron_client.get_usdt_balance')
    def test_all_error_types_share_same_field_set(self, mock_usdt, mock_trx):
        """所有错误类型共享相同的字段集合 (code, message, severity, required, available)"""
        required_fields = {"code", "message", "severity", "required", "available"}

        # 测试 USDT 不足
        mock_trx.return_value = 100.0
        mock_usdt.return_value = 5.0
        with self.assertRaises(InsufficientBalanceError) as cm:
            check_sender_balance("TAddr", 20.0, "USDT")
        for err in cm.exception.details["errors"]:
            self.assertTrue(
                required_fields.issubset(set(err.keys())),
                f"错误 {err['code']} 缺少字段: {required_fields - set(err.keys())}"
            )

        # 测试 Gas 不足
        mock_trx.return_value = 0.5
        mock_usdt.return_value = 100.0
        with self.assertRaises(InsufficientBalanceError) as cm:
            check_sender_balance("TAddr", 10.0, "USDT")
        for err in cm.exception.details["errors"]:
            self.assertTrue(
                required_fields.issubset(set(err.keys())),
                f"错误 {err['code']} 缺少字段: {required_fields - set(err.keys())}"
            )

        # 测试 TRX 不足
        mock_trx.return_value = 1.0
        with self.assertRaises(InsufficientBalanceError) as cm:
            check_sender_balance("TAddr", 100.0, "TRX")
        for err in cm.exception.details["errors"]:
            self.assertTrue(
                required_fields.issubset(set(err.keys())),
                f"错误 {err['code']} 缺少字段: {required_fields - set(err.keys())}"
            )


if __name__ == '__main__':
    unittest.main()
