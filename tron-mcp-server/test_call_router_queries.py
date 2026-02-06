"""
测试 call_router.py 查询类路由
=============================

补齐 call_router 中所有查询类路由的测试：
- get_usdt_balance: 缺参数、无效地址、正常流程、RPC 异常
- get_balance: 缺参数、无效地址、正常流程、RPC 异常
- get_gas_parameters: 正常流程、超时、RPC 异常
- get_transaction_status: 缺参数、无效 txid、正常流程、pending、异常
- get_network_status: 正常流程、RPC 异常
- get_account_status: 缺参数、无效地址、正常流程
- check_account_safety: 缺参数、无效地址、正常流程
- build_tx: 缺参数、无效地址、无效金额、正常流程、force_execution、InsufficientBalanceError、blocked
- skills: 正常返回技能清单
"""

import unittest
import sys
import os

# 强制 UTF-8 编码
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# 将项目目录加入 path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from unittest.mock import patch, MagicMock

# 模拟 mcp 依赖
sys.modules["mcp"] = MagicMock()
sys.modules["mcp.server"] = MagicMock()
sys.modules["mcp.server.fastmcp"] = MagicMock()

from tron_mcp_server import call_router


class TestGetUsdtBalance(unittest.TestCase):
    """测试 get_usdt_balance 路由"""

    def test_missing_address_parameter(self):
        """缺少 address 参数应返回错误"""
        result = call_router.call("get_usdt_balance", {})
        self.assertIn("error", result)
        self.assertIn("address", result["summary"].lower())

    def test_invalid_address_format(self):
        """无效地址格式应返回错误"""
        result = call_router.call("get_usdt_balance", {"address": "invalid123"})
        self.assertIn("error", result)
        self.assertIn("无效", result["summary"])

    @patch('tron_mcp_server.call_router._get_usdt_balance')
    def test_successful_query(self, mock_get):
        """正常查询应返回格式化余额"""
        mock_get.return_value = {
            "address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "balance_usdt": 100.0,
            "balance_raw": 100000000,
            "summary": "地址 TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7 当前 USDT 余额为 100.000000 USDT。"
        }
        result = call_router.call("get_usdt_balance", {"address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"})
        self.assertNotIn("error", result)
        self.assertEqual(result["balance_usdt"], 100.0)
        mock_get.assert_called_once_with("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")

    @patch('tron_mcp_server.call_router._get_usdt_balance')
    def test_rpc_error_handling(self, mock_get):
        """RPC 异常应返回错误响应"""
        mock_get.side_effect = Exception("Network error")
        result = call_router.call("get_usdt_balance", {"address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"})
        self.assertIn("error", result)
        self.assertIn("rpc_error", result["error"])


class TestGetBalance(unittest.TestCase):
    """测试 get_balance 路由 (TRX)"""

    def test_missing_address_parameter(self):
        """缺少 address 参数应返回错误"""
        result = call_router.call("get_balance", {})
        self.assertIn("error", result)
        self.assertIn("address", result["summary"].lower())

    def test_invalid_address_format(self):
        """无效地址格式应返回错误"""
        result = call_router.call("get_balance", {"address": "bad_address"})
        self.assertIn("error", result)
        self.assertIn("无效", result["summary"])

    @patch('tron_mcp_server.call_router._get_balance')
    def test_successful_query(self, mock_get):
        """正常查询应返回格式化余额"""
        mock_get.return_value = {
            "address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "balance_trx": 50.0,
            "balance_sun": 50000000,
            "summary": "地址 TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7 当前 TRX 余额为 50.000000 TRX。"
        }
        result = call_router.call("get_balance", {"address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"})
        self.assertNotIn("error", result)
        self.assertEqual(result["balance_trx"], 50.0)

    @patch('tron_mcp_server.call_router._get_balance')
    def test_rpc_error_handling(self, mock_get):
        """RPC 异常应返回错误响应"""
        mock_get.side_effect = Exception("Connection timeout")
        result = call_router.call("get_balance", {"address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"})
        self.assertIn("error", result)


class TestGetGasParameters(unittest.TestCase):
    """测试 get_gas_parameters 路由"""

    @patch('tron_mcp_server.call_router._get_gas_parameters')
    def test_successful_query(self, mock_get):
        """正常查询应返回 gas 参数"""
        mock_get.return_value = {
            "gas_price_sun": 1000,
            "gas_price_trx": 0.001,
            "summary": "当前网络 Gas 价格为 1000 SUN（约 0.001000 TRX）。"
        }
        result = call_router.call("get_gas_parameters", {})
        self.assertNotIn("error", result)
        self.assertEqual(result["gas_price_sun"], 1000)

    @patch('tron_mcp_server.call_router._get_gas_parameters')
    def test_timeout_error_handling(self, mock_get):
        """超时异常应返回 timeout 错误"""
        mock_get.side_effect = TimeoutError("Request timeout")
        result = call_router.call("get_gas_parameters", {})
        self.assertIn("error", result)
        self.assertIn("timeout", result["error"])

    @patch('tron_mcp_server.call_router._get_gas_parameters')
    def test_rpc_error_handling(self, mock_get):
        """RPC 异常应返回错误响应"""
        mock_get.side_effect = Exception("API error")
        result = call_router.call("get_gas_parameters", {})
        self.assertIn("error", result)


class TestGetTransactionStatus(unittest.TestCase):
    """测试 get_transaction_status 路由"""

    def test_missing_txid_parameter(self):
        """缺少 txid 参数应返回错误"""
        result = call_router.call("get_transaction_status", {})
        self.assertIn("error", result)
        self.assertIn("txid", result["summary"].lower())

    def test_invalid_txid_format(self):
        """无效 txid 格式应返回错误"""
        result = call_router.call("get_transaction_status", {"txid": "short"})
        self.assertIn("error", result)
        self.assertIn("无效", result["summary"])

    @patch('tron_mcp_server.call_router._get_transaction_status')
    def test_successful_confirmed_transaction(self, mock_get):
        """已确认交易应返回状态"""
        mock_get.return_value = {
            "txid": "a" * 64,
            "status": "成功",
            "success": True,
            "block_number": 12345678,
            "confirmations": 10,
            "summary": "交易 aaaaaaaaaaaaaaaa... 状态：成功，所在区块 12,345,678，已确认 10 次。"
        }
        result = call_router.call("get_transaction_status", {"txid": "a" * 64})
        self.assertNotIn("error", result)
        self.assertEqual(result["success"], True)

    @patch('tron_mcp_server.call_router._get_transaction_status')
    def test_pending_transaction(self, mock_get):
        """未确认交易应返回 pending 状态"""
        mock_get.side_effect = ValueError("尚未确认")
        result = call_router.call("get_transaction_status", {"txid": "b" * 64})
        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["confirmed"], False)

    @patch('tron_mcp_server.call_router._get_transaction_status')
    def test_nonexistent_transaction(self, mock_get):
        """不存在的交易应返回 pending 状态"""
        mock_get.side_effect = ValueError("不存在")
        result = call_router.call("get_transaction_status", {"txid": "c" * 64})
        self.assertEqual(result["status"], "pending")

    @patch('tron_mcp_server.call_router._get_transaction_status')
    def test_other_error_handling(self, mock_get):
        """其他异常应返回错误响应"""
        mock_get.side_effect = Exception("Unexpected error")
        result = call_router.call("get_transaction_status", {"txid": "d" * 64})
        self.assertIn("error", result)


class TestGetNetworkStatus(unittest.TestCase):
    """测试 get_network_status 路由"""

    @patch('tron_mcp_server.call_router._get_network_status')
    def test_successful_query(self, mock_get):
        """正常查询应返回网络状态"""
        mock_get.return_value = {
            "latest_block": 12345678,
            "chain": "TRON Mainnet",
            "summary": "TRON 主网当前区块高度为 12,345,678。"
        }
        result = call_router.call("get_network_status", {})
        self.assertNotIn("error", result)
        self.assertEqual(result["latest_block"], 12345678)

    @patch('tron_mcp_server.call_router._get_network_status')
    def test_rpc_error_handling(self, mock_get):
        """RPC 异常应返回错误响应"""
        mock_get.side_effect = Exception("Network unavailable")
        result = call_router.call("get_network_status", {})
        self.assertIn("error", result)


class TestGetAccountStatus(unittest.TestCase):
    """测试 get_account_status 路由"""

    def test_missing_address_parameter(self):
        """缺少 address 参数应返回错误"""
        result = call_router.call("get_account_status", {})
        self.assertIn("error", result)
        self.assertIn("address", result["summary"].lower())

    def test_invalid_address_format(self):
        """无效地址格式应返回错误"""
        result = call_router.call("get_account_status", {"address": "xyz"})
        self.assertIn("error", result)
        self.assertIn("无效", result["summary"])

    @patch('tron_mcp_server.tron_client.get_account_status')
    @patch('tron_mcp_server.formatters.format_account_status')
    def test_successful_query(self, mock_format, mock_get):
        """正常查询应返回账户状态"""
        mock_get.return_value = {
            "address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "is_activated": True,
            "has_trx": True,
            "trx_balance": 100.0,
            "total_transactions": 50
        }
        mock_format.return_value = {
            "is_activated": True,
            "warnings": [],
            "summary": "账户已激活"
        }
        result = call_router.call("get_account_status", {"address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"})
        self.assertNotIn("error", result)
        mock_get.assert_called_once()


class TestCheckAccountSafety(unittest.TestCase):
    """测试 check_account_safety 路由"""

    def test_missing_address_parameter(self):
        """缺少 address 参数应返回错误"""
        result = call_router.call("check_account_safety", {})
        self.assertIn("error", result)
        self.assertIn("address", result["summary"].lower())

    def test_invalid_address_format(self):
        """无效地址格式应返回错误"""
        result = call_router.call("check_account_safety", {"address": "bad"})
        self.assertIn("error", result)
        self.assertIn("无效", result["summary"])

    @patch('tron_mcp_server.call_router._check_account_safety')
    def test_safe_address(self, mock_check):
        """安全地址应返回安全状态"""
        mock_check.return_value = {
            "address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "is_safe": True,
            "is_risky": False,
            "risk_type": "Safe",
            "safety_status": "安全",
            "warnings": [],
            "summary": "地址安全"
        }
        result = call_router.call("check_account_safety", {"address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"})
        self.assertNotIn("error", result)
        self.assertEqual(result["is_safe"], True)

    @patch('tron_mcp_server.call_router._check_account_safety')
    def test_risky_address(self, mock_check):
        """风险地址应返回风险信息"""
        mock_check.return_value = {
            "address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "is_safe": False,
            "is_risky": True,
            "risk_type": "Scam",
            "safety_status": "危险",
            "warnings": ["⛔ 该地址被标记为诈骗"],
            "summary": "地址危险"
        }
        result = call_router.call("check_account_safety", {"address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"})
        self.assertNotIn("error", result)
        self.assertEqual(result["is_risky"], True)


class TestBuildTx(unittest.TestCase):
    """测试 build_tx 路由"""

    def test_missing_from_parameter(self):
        """缺少 from 参数应返回错误"""
        result = call_router.call("build_tx", {"to": "TAddr", "amount": 10})
        self.assertIn("error", result)
        self.assertIn("from", result["summary"].lower())

    def test_missing_to_parameter(self):
        """缺少 to 参数应返回错误"""
        result = call_router.call("build_tx", {"from": "TAddr", "amount": 10})
        self.assertIn("error", result)
        self.assertIn("to", result["summary"].lower())

    def test_missing_amount_parameter(self):
        """缺少 amount 参数应返回错误"""
        result = call_router.call("build_tx", {"from": "TAddr", "to": "TAddr2"})
        self.assertIn("error", result)
        self.assertIn("amount", result["summary"].lower())

    def test_invalid_from_address(self):
        """无效发送方地址应返回错误"""
        result = call_router.call("build_tx", {
            "from": "invalid",
            "to": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "amount": 10
        })
        self.assertIn("error", result)
        self.assertIn("无效", result["summary"])

    def test_invalid_to_address(self):
        """无效接收方地址应返回错误"""
        result = call_router.call("build_tx", {
            "from": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "to": "bad",
            "amount": 10
        })
        self.assertIn("error", result)
        self.assertIn("无效", result["summary"])

    def test_invalid_amount_zero(self):
        """零金额应返回错误"""
        result = call_router.call("build_tx", {
            "from": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "to": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            "amount": 0
        })
        self.assertIn("error", result)
        self.assertIn("正数", result["summary"])

    def test_invalid_amount_negative(self):
        """负金额应返回错误"""
        result = call_router.call("build_tx", {
            "from": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "to": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            "amount": -10
        })
        self.assertIn("error", result)

    @patch('tron_mcp_server.call_router._build_unsigned_tx')
    def test_successful_build(self, mock_build):
        """正常构建应返回未签名交易"""
        mock_build.return_value = {
            "unsigned_tx": {"txID": "a" * 64, "raw_data": {}},
            "summary": "已生成交易"
        }
        result = call_router.call("build_tx", {
            "from": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "to": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            "amount": 10,
            "token": "USDT"
        })
        self.assertNotIn("error", result)
        self.assertIn("unsigned_tx", result)

    @patch('tron_mcp_server.call_router._build_unsigned_tx')
    def test_force_execution_parameter(self, mock_build):
        """force_execution 参数应正确传递"""
        mock_build.return_value = {"unsigned_tx": {}, "summary": "已生成交易"}
        call_router.call("build_tx", {
            "from": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "to": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            "amount": 10,
            "force_execution": True
        })
        # 验证 force_execution=True 被传递
        call_args = mock_build.call_args[0]
        self.assertEqual(call_args[4], True)  # force_execution is 5th arg

    @patch('tron_mcp_server.call_router._build_unsigned_tx')
    def test_insufficient_balance_error(self, mock_build):
        """余额不足应返回详细错误"""
        from tron_mcp_server.tx_builder import InsufficientBalanceError
        error = InsufficientBalanceError(
            "余额不足",
            error_code="insufficient_usdt",
            details={"required": 100, "available": 50}
        )
        mock_build.side_effect = error
        result = call_router.call("build_tx", {
            "from": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "to": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            "amount": 100
        })
        self.assertIn("error", result)
        self.assertIn("error_type", result)
        self.assertEqual(result["error_type"], "insufficient_usdt")

    @patch('tron_mcp_server.call_router._build_unsigned_tx')
    def test_blocked_by_risk_check(self, mock_build):
        """风险熔断应返回拦截信息"""
        mock_build.return_value = {
            "blocked": True,
            "reason": "接收方地址有风险",
            "summary": "交易已被拦截"
        }
        result = call_router.call("build_tx", {
            "from": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "to": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            "amount": 10
        })
        self.assertEqual(result["blocked"], True)


class TestSkills(unittest.TestCase):
    """测试 skills 路由"""

    @patch('tron_mcp_server.call_router._get_skills')
    def test_returns_skills_list(self, mock_get):
        """应返回技能清单"""
        mock_get.return_value = {
            "skills": ["get_balance", "transfer"],
            "summary": "可用技能列表"
        }
        result = call_router.call("skills", {})
        self.assertNotIn("error", result)
        self.assertIn("skills", result)


if __name__ == "__main__":
    unittest.main()
