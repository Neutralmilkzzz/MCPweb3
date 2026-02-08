"""
测试 tx_builder.py - 交易构建模块集成测试
==========================================

覆盖以下功能的端到端集成测试：
- check_sender_balance: 发送方余额检查（USDT 和 TRX）
- check_recipient_status: 接收方账户状态检查
- check_recipient_security: 接收方安全检查
- build_unsigned_tx: 完整构建流程（安全检查 + 余额检查 + 接收方检查 + 交易构建）
- InsufficientBalanceError: 自定义异常
- _encode_transfer: TRC20 函数编码
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

from tron_mcp_server import tx_builder
from tron_mcp_server.tx_builder import InsufficientBalanceError

TEST_FROM = "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"
TEST_TO = "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf"


class TestInsufficientBalanceError(unittest.TestCase):
    """测试自定义 InsufficientBalanceError 异常"""

    def test_error_has_error_code(self):
        """异常应包含 error_code"""
        error = InsufficientBalanceError("余额不足", error_code="insufficient_usdt")
        self.assertEqual(error.error_code, "insufficient_usdt")
        self.assertEqual(str(error), "余额不足")

    def test_error_has_details(self):
        """异常应包含 details"""
        details = {"required": 100, "available": 50}
        error = InsufficientBalanceError("余额不足", error_code="insufficient_trx", details=details)
        self.assertEqual(error.details["required"], 100)

    def test_error_default_details(self):
        """未提供 details 时应为空字典"""
        error = InsufficientBalanceError("msg", error_code="code")
        self.assertEqual(error.details, {})

    def test_is_value_error(self):
        """应是 ValueError 的子类"""
        error = InsufficientBalanceError("msg", error_code="code")
        self.assertIsInstance(error, ValueError)


class TestCheckSenderBalance(unittest.TestCase):
    """测试 check_sender_balance"""

    @patch('tron_mcp_server.tron_client.get_usdt_balance')
    @patch('tron_mcp_server.tron_client.get_balance_trx')
    def test_usdt_sufficient_balance(self, mock_trx, mock_usdt):
        """USDT 余额充足应返回 sufficient=True"""
        mock_trx.return_value = 100.0  # 100 TRX (足够 Gas)
        mock_usdt.return_value = 200.0  # 200 USDT
        
        result = tx_builder.check_sender_balance(TEST_FROM, 50.0, "USDT")
        self.assertTrue(result["checked"])
        self.assertTrue(result["sufficient"])
        self.assertEqual(result["errors"], [])

    @patch('tron_mcp_server.tron_client.get_usdt_balance')
    @patch('tron_mcp_server.tron_client.get_balance_trx')
    def test_usdt_insufficient_balance(self, mock_trx, mock_usdt):
        """USDT 余额不足应抛出 InsufficientBalanceError"""
        mock_trx.return_value = 100.0  # 足够 Gas
        mock_usdt.return_value = 10.0  # 只有 10 USDT
        
        with self.assertRaises(InsufficientBalanceError) as ctx:
            tx_builder.check_sender_balance(TEST_FROM, 100.0, "USDT")
        self.assertEqual(ctx.exception.error_code, "insufficient_usdt")

    @patch('tron_mcp_server.tron_client.get_usdt_balance')
    @patch('tron_mcp_server.tron_client.get_balance_trx')
    def test_usdt_insufficient_gas(self, mock_trx, mock_usdt):
        """TRX 不足以支付 Gas 应抛出 InsufficientBalanceError"""
        mock_trx.return_value = 0.001  # 只有 0.001 TRX，不够 Gas
        mock_usdt.return_value = 1000.0  # USDT 充足
        
        with self.assertRaises(InsufficientBalanceError) as ctx:
            tx_builder.check_sender_balance(TEST_FROM, 100.0, "USDT")
        self.assertEqual(ctx.exception.error_code, "insufficient_trx_for_gas")

    @patch('tron_mcp_server.tron_client.get_balance_trx')
    def test_trx_sufficient_balance(self, mock_trx):
        """TRX 余额充足应返回 sufficient=True"""
        mock_trx.return_value = 100.0
        
        result = tx_builder.check_sender_balance(TEST_FROM, 10.0, "TRX")
        self.assertTrue(result["checked"])
        self.assertTrue(result["sufficient"])

    @patch('tron_mcp_server.tron_client.get_balance_trx')
    def test_trx_insufficient_balance(self, mock_trx):
        """TRX 余额不足应抛出 InsufficientBalanceError"""
        mock_trx.return_value = 5.0  # 只有 5 TRX
        
        with self.assertRaises(InsufficientBalanceError) as ctx:
            tx_builder.check_sender_balance(TEST_FROM, 100.0, "TRX")
        self.assertEqual(ctx.exception.error_code, "insufficient_trx")

    @patch('tron_mcp_server.tron_client.get_balance_trx')
    def test_trx_query_failure_returns_unchecked(self, mock_trx):
        """TRX 余额查询失败应返回 checked=False（保守策略，不阻止交易）"""
        mock_trx.side_effect = Exception("Network error")
        
        result = tx_builder.check_sender_balance(TEST_FROM, 10.0, "USDT")
        self.assertFalse(result["checked"])
        self.assertIsNone(result["sufficient"])

    @patch('tron_mcp_server.tron_client.get_usdt_balance')
    @patch('tron_mcp_server.tron_client.get_balance_trx')
    def test_usdt_query_failure_returns_unchecked(self, mock_trx, mock_usdt):
        """USDT 余额查询失败应返回 checked=False"""
        mock_trx.return_value = 100.0
        mock_usdt.side_effect = Exception("Network error")
        
        result = tx_builder.check_sender_balance(TEST_FROM, 10.0, "USDT")
        self.assertFalse(result["checked"])


class TestCheckRecipientStatus(unittest.TestCase):
    """测试 check_recipient_status"""

    @patch('tron_mcp_server.tron_client.get_account_status')
    def test_activated_account_no_warnings(self, mock_status):
        """已激活且有 TRX 的账户不应有预警"""
        mock_status.return_value = {
            "is_activated": True,
            "has_trx": True,
            "trx_balance": 100.0,
        }
        result = tx_builder.check_recipient_status(TEST_TO)
        self.assertTrue(result["checked"])
        self.assertEqual(result["warnings"], [])

    @patch('tron_mcp_server.tron_client.get_account_status')
    def test_unactivated_account_warning(self, mock_status):
        """未激活账户应产生预警"""
        mock_status.return_value = {
            "is_activated": False,
            "has_trx": False,
        }
        result = tx_builder.check_recipient_status(TEST_TO)
        self.assertTrue(result["checked"])
        self.assertTrue(len(result["warnings"]) >= 1)
        self.assertIn("unactivated_recipient", [w["code"] for w in result["warnings"]])

    @patch('tron_mcp_server.tron_client.get_account_status')
    def test_no_trx_warning(self, mock_status):
        """没有 TRX 的账户应产生预警"""
        mock_status.return_value = {
            "is_activated": True,
            "has_trx": False,
        }
        result = tx_builder.check_recipient_status(TEST_TO)
        self.assertIn("no_trx_balance", [w["code"] for w in result["warnings"]])

    @patch('tron_mcp_server.tron_client.get_account_status')
    def test_query_failure_returns_unchecked(self, mock_status):
        """查询失败应返回 checked=False"""
        mock_status.side_effect = Exception("Network error")
        result = tx_builder.check_recipient_status(TEST_TO)
        self.assertFalse(result["checked"])
        self.assertEqual(result["warnings"], [])

    @patch('tron_mcp_server.tron_client.get_account_status')
    def test_warning_message_format(self, mock_status):
        """预警消息应以 ⚠️ 开头"""
        mock_status.return_value = {
            "is_activated": False,
            "has_trx": False,
        }
        result = tx_builder.check_recipient_status(TEST_TO)
        self.assertIsNotNone(result["warning_message"])
        self.assertTrue(result["warning_message"].startswith("⚠️"))


class TestCheckRecipientSecurity(unittest.TestCase):
    """测试 check_recipient_security"""

    @patch('tron_mcp_server.tron_client.check_account_risk')
    def test_safe_address(self, mock_risk):
        """安全地址应返回 is_risky=False"""
        mock_risk.return_value = {
            "is_risky": False,
            "risk_type": "Safe",
        }
        result = tx_builder.check_recipient_security(TEST_TO)
        self.assertTrue(result["checked"])
        self.assertFalse(result["is_risky"])
        self.assertIsNone(result["security_warning"])

    @patch('tron_mcp_server.tron_client.check_account_risk')
    def test_risky_address(self, mock_risk):
        """风险地址应返回 is_risky=True 和安全警告"""
        mock_risk.return_value = {
            "is_risky": True,
            "risk_type": "Scam",
            "detail": "Known scam address",
        }
        result = tx_builder.check_recipient_security(TEST_TO)
        self.assertTrue(result["checked"])
        self.assertTrue(result["is_risky"])
        self.assertIsNotNone(result["security_warning"])
        self.assertIn("⛔", result["security_warning"])

    @patch('tron_mcp_server.tron_client.check_account_risk')
    def test_api_failure_returns_degraded(self, mock_risk):
        """API 失败应返回降级状态"""
        mock_risk.side_effect = Exception("Network error")
        result = tx_builder.check_recipient_security(TEST_TO)
        self.assertFalse(result["checked"])
        self.assertFalse(result["is_risky"])
        self.assertIn("degradation_warning", result)

    @patch('tron_mcp_server.tron_client.check_account_risk')
    def test_risk_type_sanitized(self, mock_risk):
        """risk_type 应被安全清理（防止注入）"""
        mock_risk.return_value = {
            "is_risky": True,
            "risk_type": "Scam<script>alert(1)</script>",
        }
        result = tx_builder.check_recipient_security(TEST_TO)
        self.assertNotIn("<script>", result["risk_type"])
        self.assertNotIn(">", result["risk_type"])


class TestBuildUnsignedTx(unittest.TestCase):
    """测试 build_unsigned_tx 完整构建流程"""

    @patch('tron_mcp_server.tron_client.check_account_risk')
    @patch('tron_mcp_server.tron_client.get_account_status')
    @patch('tron_mcp_server.tron_client.get_usdt_balance')
    @patch('tron_mcp_server.tron_client.get_balance_trx')
    @patch('tron_mcp_server.tron_client.get_latest_block_info')
    def test_usdt_transfer_success(self, mock_block, mock_trx, mock_usdt, mock_status, mock_risk):
        """正常 USDT 转账构建应成功"""
        mock_block.return_value = {"number": 12345, "hash": "0" * 64}
        mock_trx.return_value = 100.0
        mock_usdt.return_value = 200.0
        mock_status.return_value = {"is_activated": True, "has_trx": True}
        mock_risk.return_value = {"is_risky": False, "risk_type": "Safe"}
        
        result = tx_builder.build_unsigned_tx(TEST_FROM, TEST_TO, 50.0, "USDT")
        self.assertIn("txID", result)
        self.assertIn("raw_data", result)
        self.assertNotIn("blocked", result)

    @patch('tron_mcp_server.tron_client.check_account_risk')
    @patch('tron_mcp_server.tron_client.get_balance_trx')
    @patch('tron_mcp_server.tron_client.get_latest_block_info')
    def test_trx_transfer_success(self, mock_block, mock_trx, mock_risk):
        """正常 TRX 转账构建应成功"""
        mock_block.return_value = {"number": 12345, "hash": "0" * 64}
        mock_trx.return_value = 100.0
        mock_risk.return_value = {"is_risky": False, "risk_type": "Safe"}
        
        result = tx_builder.build_unsigned_tx(TEST_FROM, TEST_TO, 10.0, "TRX")
        self.assertIn("txID", result)
        self.assertIn("raw_data", result)

    def test_invalid_amount_raises(self):
        """无效金额应抛出 ValueError"""
        with self.assertRaises(ValueError):
            tx_builder.build_unsigned_tx(TEST_FROM, TEST_TO, 0, "USDT")
        with self.assertRaises(ValueError):
            tx_builder.build_unsigned_tx(TEST_FROM, TEST_TO, -10, "USDT")

    def test_unsupported_token_raises(self):
        """不支持的代币应抛出 ValueError"""
        with self.assertRaises(ValueError):
            tx_builder.build_unsigned_tx(TEST_FROM, TEST_TO, 10, "ETH")

    @patch('tron_mcp_server.tron_client.check_account_risk')
    def test_risky_address_blocked(self, mock_risk):
        """风险地址应被熔断拦截"""
        mock_risk.return_value = {
            "is_risky": True,
            "risk_type": "Scam",
            "risk_reasons": ["🔴 高危标签"],
            "detail": "Scam address",
        }
        
        result = tx_builder.build_unsigned_tx(TEST_FROM, TEST_TO, 50.0, "USDT")
        self.assertTrue(result["blocked"])
        self.assertIn("🛑", result["summary"])

    @patch('tron_mcp_server.tron_client.check_account_risk')
    @patch('tron_mcp_server.tron_client.get_account_status')
    @patch('tron_mcp_server.tron_client.get_usdt_balance')
    @patch('tron_mcp_server.tron_client.get_balance_trx')
    @patch('tron_mcp_server.tron_client.get_latest_block_info')
    def test_force_execution_bypasses_risk(self, mock_block, mock_trx, mock_usdt, mock_status, mock_risk):
        """force_execution=True 应绕过风险拦截"""
        mock_block.return_value = {"number": 12345, "hash": "0" * 64}
        mock_trx.return_value = 100.0
        mock_usdt.return_value = 200.0
        mock_status.return_value = {"is_activated": True, "has_trx": True}
        mock_risk.return_value = {
            "is_risky": True,
            "risk_type": "Scam",
        }
        
        result = tx_builder.build_unsigned_tx(TEST_FROM, TEST_TO, 50.0, "USDT", force_execution=True)
        self.assertNotIn("blocked", result)
        self.assertIn("txID", result)

    @patch('tron_mcp_server.tron_client.check_account_risk')
    @patch('tron_mcp_server.tron_client.get_usdt_balance')
    @patch('tron_mcp_server.tron_client.get_balance_trx')
    def test_insufficient_balance_raises(self, mock_trx, mock_usdt, mock_risk):
        """余额不足应抛出 InsufficientBalanceError"""
        mock_risk.return_value = {"is_risky": False, "risk_type": "Safe"}
        mock_trx.return_value = 100.0
        mock_usdt.return_value = 10.0  # 不够
        
        with self.assertRaises(InsufficientBalanceError):
            tx_builder.build_unsigned_tx(TEST_FROM, TEST_TO, 1000.0, "USDT")

    @patch('tron_mcp_server.tron_client.check_account_risk')
    @patch('tron_mcp_server.tron_client.get_account_status')
    @patch('tron_mcp_server.tron_client.get_usdt_balance')
    @patch('tron_mcp_server.tron_client.get_balance_trx')
    @patch('tron_mcp_server.tron_client.get_latest_block_info')
    def test_skip_balance_check(self, mock_block, mock_trx, mock_usdt, mock_status, mock_risk):
        """check_balance=False 应跳过余额检查"""
        mock_block.return_value = {"number": 12345, "hash": "0" * 64}
        mock_risk.return_value = {"is_risky": False, "risk_type": "Safe"}
        mock_status.return_value = {"is_activated": True, "has_trx": True}
        # 不 mock USDT/TRX 余额 - 如果被调用会失败
        mock_trx.side_effect = Exception("Should not be called")
        mock_usdt.side_effect = Exception("Should not be called")
        
        result = tx_builder.build_unsigned_tx(
            TEST_FROM, TEST_TO, 50.0, "USDT",
            check_balance=False
        )
        self.assertIn("txID", result)

    @patch('tron_mcp_server.tron_client.check_account_risk')
    @patch('tron_mcp_server.tron_client.get_balance_trx')
    @patch('tron_mcp_server.tron_client.get_latest_block_info')
    def test_skip_recipient_check(self, mock_block, mock_trx, mock_risk):
        """check_recipient=False 应跳过接收方检查"""
        mock_block.return_value = {"number": 12345, "hash": "0" * 64}
        mock_trx.return_value = 100.0
        mock_risk.return_value = {"is_risky": False, "risk_type": "Safe"}
        
        result = tx_builder.build_unsigned_tx(
            TEST_FROM, TEST_TO, 10.0, "TRX",
            check_recipient=False
        )
        self.assertIn("txID", result)
        self.assertNotIn("recipient_check", result)

    @patch('tron_mcp_server.tron_client.get_balance_trx')
    @patch('tron_mcp_server.tron_client.get_latest_block_info')
    def test_skip_security_check(self, mock_block, mock_trx):
        """check_security=False 应跳过安全检查"""
        mock_block.return_value = {"number": 12345, "hash": "0" * 64}
        mock_trx.return_value = 100.0
        
        result = tx_builder.build_unsigned_tx(
            TEST_FROM, TEST_TO, 10.0, "TRX",
            check_security=False
        )
        self.assertIn("txID", result)
        self.assertNotIn("security_check", result)

    @patch('tron_mcp_server.tron_client.check_account_risk')
    @patch('tron_mcp_server.tron_client.get_account_status')
    @patch('tron_mcp_server.tron_client.get_usdt_balance')
    @patch('tron_mcp_server.tron_client.get_balance_trx')
    @patch('tron_mcp_server.tron_client.get_latest_block_info')
    def test_usdt_includes_recipient_check(self, mock_block, mock_trx, mock_usdt, mock_status, mock_risk):
        """USDT 转账应包含接收方检查"""
        mock_block.return_value = {"number": 12345, "hash": "0" * 64}
        mock_trx.return_value = 100.0
        mock_usdt.return_value = 200.0
        mock_status.return_value = {"is_activated": False, "has_trx": False}
        mock_risk.return_value = {"is_risky": False, "risk_type": "Safe"}
        
        result = tx_builder.build_unsigned_tx(TEST_FROM, TEST_TO, 50.0, "USDT")
        self.assertIn("recipient_check", result)
        self.assertTrue(len(result["recipient_check"]["warnings"]) > 0)

    @patch('tron_mcp_server.tron_client.check_account_risk')
    @patch('tron_mcp_server.tron_client.get_balance_trx')
    @patch('tron_mcp_server.tron_client.get_latest_block_info')
    def test_security_check_degradation_warning(self, mock_block, mock_trx, mock_risk):
        """安全检查降级应添加 degradation_warning"""
        mock_block.return_value = {"number": 12345, "hash": "0" * 64}
        mock_trx.return_value = 100.0
        mock_risk.side_effect = Exception("API unavailable")
        
        result = tx_builder.build_unsigned_tx(TEST_FROM, TEST_TO, 10.0, "TRX")
        self.assertIn("degradation_warning", result)

    @patch('tron_mcp_server.tron_client.check_account_risk')
    @patch('tron_mcp_server.tron_client.get_account_status')
    @patch('tron_mcp_server.tron_client.get_usdt_balance')
    @patch('tron_mcp_server.tron_client.get_balance_trx')
    @patch('tron_mcp_server.tron_client.get_latest_block_info')
    def test_includes_sender_check(self, mock_block, mock_trx, mock_usdt, mock_status, mock_risk):
        """应包含发送方余额检查结果"""
        mock_block.return_value = {"number": 12345, "hash": "0" * 64}
        mock_trx.return_value = 100.0
        mock_usdt.return_value = 200.0
        mock_status.return_value = {"is_activated": True, "has_trx": True}
        mock_risk.return_value = {"is_risky": False, "risk_type": "Safe"}
        
        result = tx_builder.build_unsigned_tx(TEST_FROM, TEST_TO, 50.0, "USDT")
        self.assertIn("sender_check", result)
        self.assertTrue(result["sender_check"]["sufficient"])


class TestEncodeTransfer(unittest.TestCase):
    """测试 _encode_transfer TRC20 函数编码"""

    def test_encode_transfer_format(self):
        """编码结果应以 a9059cbb 开头（transfer 方法签名）"""
        result = tx_builder._encode_transfer(TEST_TO, 100000000)
        self.assertTrue(result.startswith("a9059cbb"))
        # method_sig (8) + address (64) + amount (64) = 136 chars
        self.assertEqual(len(result), 136)

    def test_invalid_address_raises(self):
        """无效地址应抛出 ValueError"""
        with self.assertRaises(ValueError):
            tx_builder._encode_transfer("invalid_address", 100)


if __name__ == "__main__":
    unittest.main()
