"""
测试 formatters.py 模块
======================

覆盖以下格式化函数：
- format_usdt_balance: USDT余额格式化
- format_trx_balance: TRX余额格式化
- format_gas_parameters: Gas参数格式化
- format_tx_status: 交易状态格式化
- format_network_status: 网络状态格式化
- format_account_status: 账户状态格式化
- format_account_safety: 账户安全检查格式化
- format_error: 错误消息格式化
- format_signed_tx: 已签名交易格式化
- format_broadcast_result: 广播结果格式化
- format_transfer_result: 转账结果格式化
- format_wallet_info: 钱包信息格式化
- format_transaction_history: 交易历史格式化
"""

import unittest
import sys
import os
import json

# 强制 UTF-8 编码
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# 将项目目录加入 path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from unittest.mock import MagicMock

# 模拟 mcp 依赖
sys.modules["mcp"] = MagicMock()
sys.modules["mcp.server"] = MagicMock()
sys.modules["mcp.server.fastmcp"] = MagicMock()

from tron_mcp_server import formatters


class TestFormatUsdtBalance(unittest.TestCase):
    """测试 format_usdt_balance 函数"""

    def test_basic_formatting(self):
        """测试基本USDT余额格式化"""
        result = formatters.format_usdt_balance(
            "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            1000000
        )
        self.assertEqual(result["balance_raw"], 1000000)
        self.assertEqual(result["balance_usdt"], 1.0)
        self.assertIn("summary", result)
        self.assertIn("USDT", result["summary"])

    def test_zero_balance(self):
        """测试零余额"""
        result = formatters.format_usdt_balance(
            "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            0
        )
        self.assertEqual(result["balance_usdt"], 0.0)

    def test_large_balance(self):
        """测试大额余额"""
        result = formatters.format_usdt_balance(
            "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            123456789000000
        )
        self.assertEqual(result["balance_usdt"], 123456789.0)


class TestFormatTrxBalance(unittest.TestCase):
    """测试 format_trx_balance 函数"""

    def test_basic_formatting(self):
        """测试基本TRX余额格式化"""
        result = formatters.format_trx_balance(
            "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            1000000
        )
        self.assertEqual(result["balance_sun"], 1000000)
        self.assertEqual(result["balance_trx"], 1.0)
        self.assertIn("summary", result)
        self.assertIn("TRX", result["summary"])

    def test_zero_balance(self):
        """测试零余额"""
        result = formatters.format_trx_balance(
            "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            0
        )
        self.assertEqual(result["balance_trx"], 0.0)


class TestFormatGasParameters(unittest.TestCase):
    """测试 format_gas_parameters 函数"""

    def test_basic_formatting(self):
        """测试基本Gas参数格式化"""
        result = formatters.format_gas_parameters(1000)
        self.assertEqual(result["gas_price_sun"], 1000)
        self.assertEqual(result["gas_price_trx"], 0.001)
        self.assertIn("summary", result)
        self.assertIn("Gas", result["summary"])

    def test_with_energy_price(self):
        """测试包含能量价格"""
        result = formatters.format_gas_parameters(1000, 420)
        self.assertEqual(result["gas_price_sun"], 1000)
        self.assertEqual(result["energy_price_sun"], 420)


class TestFormatTxStatus(unittest.TestCase):
    """测试 format_tx_status 函数"""

    def test_successful_transaction(self):
        """测试成功的交易状态"""
        result = formatters.format_tx_status(
            "a" * 64,
            True,
            12345678,
            10
        )
        self.assertEqual(result["success"], True)
        self.assertEqual(result["status"], "成功")
        self.assertEqual(result["block_number"], 12345678)
        self.assertEqual(result["confirmations"], 10)
        self.assertIn("summary", result)

    def test_failed_transaction(self):
        """测试失败的交易状态"""
        result = formatters.format_tx_status(
            "b" * 64,
            False,
            12345678,
            5
        )
        self.assertEqual(result["success"], False)
        self.assertEqual(result["status"], "失败")


class TestFormatNetworkStatus(unittest.TestCase):
    """测试 format_network_status 函数"""

    def test_basic_formatting(self):
        """测试网络状态格式化"""
        result = formatters.format_network_status(12345678)
        self.assertEqual(result["latest_block"], 12345678)
        self.assertEqual(result["chain"], "TRON Mainnet")
        self.assertIn("summary", result)
        self.assertIn("12,345,678", result["summary"])


class TestFormatAccountStatus(unittest.TestCase):
    """测试 format_account_status 函数"""

    def test_activated_account(self):
        """测试已激活账户"""
        account_status = {
            "address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "is_activated": True,
            "has_trx": True,
            "trx_balance": 100.0,
            "total_transactions": 50,
        }
        result = formatters.format_account_status(account_status)
        self.assertEqual(result["is_activated"], True)
        self.assertEqual(result["warnings"], [])
        self.assertIn("summary", result)

    def test_unactivated_account(self):
        """测试未激活账户"""
        account_status = {
            "address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "is_activated": False,
            "has_trx": False,
            "trx_balance": 0.0,
            "total_transactions": 0,
        }
        result = formatters.format_account_status(account_status)
        self.assertEqual(result["is_activated"], False)
        self.assertEqual(len(result["warnings"]), 2)
        self.assertIn("未激活", result["warnings"][0])
        self.assertIn("没有 TRX", result["warnings"][1])


class TestFormatAccountSafety(unittest.TestCase):
    """测试 format_account_safety 函数"""

    def test_safe_address(self):
        """测试安全地址"""
        risk_info = {
            "is_risky": False,
            "risk_type": "Safe",
            "detail": "",
            "risk_reasons": [],
            "tags": {},
        }
        result = formatters.format_account_safety(
            "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            risk_info
        )
        self.assertEqual(result["is_safe"], True)
        self.assertEqual(result["is_risky"], False)
        self.assertEqual(result["safety_status"], "安全")
        self.assertIn("summary", result)

    def test_risky_address(self):
        """测试风险地址"""
        risk_info = {
            "is_risky": True,
            "risk_type": "Scam",
            "detail": "Known scam address",
            "risk_reasons": ["该地址被标记为诈骗"],
            "tags": {"Red": "Scam"},
        }
        result = formatters.format_account_safety(
            "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            risk_info
        )
        self.assertEqual(result["is_safe"], False)
        self.assertEqual(result["is_risky"], True)
        self.assertEqual(result["safety_status"], "危险（Scam）")
        self.assertGreater(len(result["warnings"]), 0)

    def test_unknown_address(self):
        """测试无法验证的地址"""
        risk_info = {
            "is_risky": False,
            "risk_type": "Unknown",
            "detail": "",
            "risk_reasons": [],
            "tags": {},
        }
        result = formatters.format_account_safety(
            "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            risk_info
        )
        self.assertEqual(result["is_safe"], False)
        self.assertEqual(result["safety_status"], "无法验证")


class TestFormatError(unittest.TestCase):
    """测试 format_error 函数"""

    def test_basic_error(self):
        """测试基本错误格式化"""
        result = formatters.format_error("missing_param", "缺少必填参数")
        self.assertEqual(result["error"], "missing_param")
        self.assertIn("summary", result)
        self.assertIn("缺少必填参数", result["summary"])
        self.assertIn("skills", result["summary"])


class TestFormatSignedTx(unittest.TestCase):
    """测试 format_signed_tx 函数"""

    def test_basic_formatting(self):
        """测试已签名交易格式化"""
        signed_tx = {
            "txID": "a" * 64,
            "raw_data": {},
            "signature": ["b" * 128],
        }
        result = formatters.format_signed_tx(
            signed_tx,
            "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            100.0,
            "USDT"
        )
        self.assertIn("signed_tx", result)
        self.assertIn("signed_tx_json", result)
        self.assertIn("txID", result)
        self.assertIn("summary", result)
        # 验证JSON字符串可以被反序列化
        json.loads(result["signed_tx_json"])


class TestFormatBroadcastResult(unittest.TestCase):
    """测试 format_broadcast_result 函数"""

    def test_successful_broadcast(self):
        """测试成功的广播结果"""
        broadcast_result = {
            "result": True,
            "txid": "a" * 64,
        }
        result = formatters.format_broadcast_result(broadcast_result)
        self.assertEqual(result["result"], True)
        self.assertEqual(result["txid"], "a" * 64)
        self.assertIn("summary", result)
        self.assertIn("✅", result["summary"])


class TestFormatTransferResult(unittest.TestCase):
    """测试 format_transfer_result 函数"""

    def test_basic_transfer(self):
        """测试基本转账结果"""
        broadcast_result = {"txid": "a" * 64}
        result = formatters.format_transfer_result(
            broadcast_result,
            "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            100.0,
            "USDT"
        )
        self.assertEqual(result["result"], True)
        self.assertEqual(result["from"], "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertEqual(result["to"], "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf")
        self.assertEqual(result["amount"], 100.0)
        self.assertEqual(result["token"], "USDT")
        self.assertIn("summary", result)

    def test_transfer_with_security_check(self):
        """测试包含安全检查的转账结果"""
        broadcast_result = {"txid": "a" * 64}
        security_check = {"is_safe": True}
        result = formatters.format_transfer_result(
            broadcast_result,
            "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            100.0,
            "USDT",
            security_check=security_check
        )
        self.assertIn("security_check", result)


class TestFormatWalletInfo(unittest.TestCase):
    """测试 format_wallet_info 函数"""

    def test_basic_formatting(self):
        """测试钱包信息格式化"""
        result = formatters.format_wallet_info(
            "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            100.5,
            50.25
        )
        self.assertEqual(result["address"], "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertEqual(result["trx_balance"], 100.5)
        self.assertEqual(result["usdt_balance"], 50.25)
        self.assertIn("summary", result)
        self.assertIn("💰", result["summary"])


class TestFormatTransactionHistory(unittest.TestCase):
    """测试 format_transaction_history 函数"""

    def test_empty_history(self):
        """测试空交易历史"""
        result = formatters.format_transaction_history(
            "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            [],
            0,
            None,
            10
        )
        self.assertEqual(result["address"], "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["displayed"], 0)
        self.assertEqual(result["transfers"], [])
        self.assertIn("summary", result)

    def test_trx_transfer(self):
        """测试TRX转账记录"""
        transfers = [
            {
                "transactionHash": "a" * 64,
                "transferFromAddress": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
                "transferToAddress": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
                "amount": 1000000,
                "tokenName": "_",
                "timestamp": 1640000000000,
            }
        ]
        result = formatters.format_transaction_history(
            "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            transfers,
            1,
            "TRX",
            10
        )
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["displayed"], 1)
        self.assertEqual(len(result["transfers"]), 1)
        tx = result["transfers"][0]
        self.assertEqual(tx["token"], "TRX")
        self.assertEqual(tx["direction"], "OUT")
        self.assertEqual(tx["amount"], 1.0)

    def test_trc20_transfer(self):
        """测试TRC20转账记录"""
        transfers = [
            {
                "transaction_id": "b" * 64,
                "from_address": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
                "to_address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
                "quant": 100000000,
                "tokenInfo": {
                    "tokenAbbr": "USDT",
                    "tokenDecimal": 6,
                },
                "timestamp": 1640000000000,
            }
        ]
        result = formatters.format_transaction_history(
            "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            transfers,
            1,
            "USDT",
            10
        )
        self.assertEqual(len(result["transfers"]), 1)
        tx = result["transfers"][0]
        self.assertEqual(tx["token"], "USDT")
        self.assertEqual(tx["direction"], "IN")
        self.assertEqual(tx["amount"], 100.0)

    def test_self_transfer(self):
        """测试自转账记录"""
        transfers = [
            {
                "transactionHash": "c" * 64,
                "transferFromAddress": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
                "transferToAddress": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
                "amount": 1000000,
                "tokenName": "_",
                "timestamp": 1640000000000,
            }
        ]
        result = formatters.format_transaction_history(
            "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            transfers,
            1,
            None,
            10
        )
        tx = result["transfers"][0]
        self.assertEqual(tx["direction"], "SELF")


if __name__ == "__main__":
    unittest.main()
