"""
测试 server.py MCP 工具层
========================

覆盖 server.py 中所有 MCP tool 函数（精简后的 11 个），验证：
- 每个工具正确调用 call_router.call() 并传入正确的 action 和参数
- 参数映射正确（如 from_address → from）
- 通过 mock call_router.call 来验证，不需要真实 API 调用

精简后的 11 个 MCP 工具：
1. tron_get_usdt_balance
2. tron_get_balance
3. tron_get_gas_parameters
4. tron_get_transaction_status
5. tron_get_network_status
6. tron_check_account_safety
7. tron_build_tx
8. tron_sign_and_broadcast_transaction
9. tron_broadcast_tx
10. tron_transfer
11. tron_get_wallet_info
12. tron_get_transaction_history
13. call (兼容模式单入口)
"""

import unittest
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

from unittest.mock import patch, MagicMock

# 创建一个正确的 FastMCP mock，让装饰器返回原函数
class MockFastMCP:
    """Mock FastMCP that returns the original function from decorator"""
    def __init__(self, name):
        self.name = name
    
    def tool(self):
        # 返回一个直接返回原函数的装饰器
        def decorator(func):
            return func
        return decorator

# 模拟 mcp 依赖
sys.modules["mcp"] = MagicMock()
sys.modules["mcp.server"] = MagicMock()
sys.modules["mcp.server.fastmcp"] = MagicMock()
sys.modules["mcp.server.fastmcp"].FastMCP = MockFastMCP

from tron_mcp_server import server


class TestTronGetUsdtBalance(unittest.TestCase):
    """测试 tron_get_usdt_balance 工具"""

    @patch('tron_mcp_server.call_router.call')
    def test_calls_router_with_correct_action(self, mock_call):
        """验证正确调用 call_router.call 并传入 get_usdt_balance action"""
        mock_call.return_value = {"balance_usdt": 100.0}
        
        result = server.tron_get_usdt_balance("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        
        mock_call.assert_called_once_with(
            "get_usdt_balance",
            {"address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"}
        )
        self.assertEqual(result, {"balance_usdt": 100.0})

    @patch('tron_mcp_server.call_router.call')
    def test_parameter_mapping(self, mock_call):
        """验证参数正确传递"""
        mock_call.return_value = {}
        
        server.tron_get_usdt_balance("TestAddress123")
        
        args = mock_call.call_args
        self.assertEqual(args[0][0], "get_usdt_balance")
        self.assertEqual(args[0][1]["address"], "TestAddress123")


class TestTronGetBalance(unittest.TestCase):
    """测试 tron_get_balance 工具"""

    @patch('tron_mcp_server.call_router.call')
    def test_calls_router_with_correct_action(self, mock_call):
        """验证正确调用 call_router.call 并传入 get_balance action"""
        mock_call.return_value = {"balance_trx": 50.0}
        
        result = server.tron_get_balance("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        
        mock_call.assert_called_once_with(
            "get_balance",
            {"address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"}
        )
        self.assertEqual(result, {"balance_trx": 50.0})


class TestTronGetGasParameters(unittest.TestCase):
    """测试 tron_get_gas_parameters 工具"""

    @patch('tron_mcp_server.call_router.call')
    def test_calls_router_with_correct_action(self, mock_call):
        """验证正确调用 call_router.call 并传入 get_gas_parameters action"""
        mock_call.return_value = {"gas_price_sun": 1000}
        
        result = server.tron_get_gas_parameters()
        
        mock_call.assert_called_once_with("get_gas_parameters", {})
        self.assertEqual(result, {"gas_price_sun": 1000})


class TestTronGetTransactionStatus(unittest.TestCase):
    """测试 tron_get_transaction_status 工具"""

    @patch('tron_mcp_server.call_router.call')
    def test_calls_router_with_correct_action(self, mock_call):
        """验证正确调用 call_router.call 并传入 get_transaction_status action"""
        mock_call.return_value = {"status": "成功", "success": True}
        
        result = server.tron_get_transaction_status("a" * 64)
        
        mock_call.assert_called_once_with(
            "get_transaction_status",
            {"txid": "a" * 64}
        )
        self.assertEqual(result["success"], True)


class TestTronGetNetworkStatus(unittest.TestCase):
    """测试 tron_get_network_status 工具"""

    @patch('tron_mcp_server.call_router.call')
    def test_calls_router_with_correct_action(self, mock_call):
        """验证正确调用 call_router.call 并传入 get_network_status action"""
        mock_call.return_value = {"latest_block": 12345678}
        
        result = server.tron_get_network_status()
        
        mock_call.assert_called_once_with("get_network_status", {})
        self.assertEqual(result, {"latest_block": 12345678})


class TestTronCheckAccountSafety(unittest.TestCase):
    """测试 tron_check_account_safety 工具"""

    @patch('tron_mcp_server.call_router.call')
    def test_calls_router_with_correct_action(self, mock_call):
        """验证正确调用 call_router.call 并传入 check_account_safety action"""
        mock_call.return_value = {"is_safe": True, "is_risky": False}
        
        result = server.tron_check_account_safety("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        
        mock_call.assert_called_once_with(
            "check_account_safety",
            {"address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"}
        )
        self.assertEqual(result["is_safe"], True)


class TestTronBuildTx(unittest.TestCase):
    """测试 tron_build_tx 工具"""

    @patch('tron_mcp_server.call_router.call')
    def test_calls_router_with_correct_action(self, mock_call):
        """验证正确调用 call_router.call 并传入 build_tx action"""
        mock_call.return_value = {"unsigned_tx": {}}
        
        result = server.tron_build_tx(
            from_address="TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            to_address="TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            amount=100.0,
            token="USDT",
            force_execution=False
        )
        
        mock_call.assert_called_once()
        args = mock_call.call_args
        self.assertEqual(args[0][0], "build_tx")
        self.assertEqual(args[0][1]["from"], "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertEqual(args[0][1]["to"], "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf")
        self.assertEqual(args[0][1]["amount"], 100.0)
        self.assertEqual(args[0][1]["token"], "USDT")
        self.assertEqual(args[0][1]["force_execution"], False)

    @patch('tron_mcp_server.call_router.call')
    def test_parameter_mapping_from_to_from_address(self, mock_call):
        """验证 from_address 参数映射为 from"""
        mock_call.return_value = {}
        
        server.tron_build_tx(
            from_address="FromAddr",
            to_address="ToAddr",
            amount=10.0
        )
        
        args = mock_call.call_args[0][1]
        self.assertEqual(args["from"], "FromAddr")
        self.assertNotIn("from_address", args)

    @patch('tron_mcp_server.call_router.call')
    def test_default_token_usdt(self, mock_call):
        """验证默认 token 为 USDT"""
        mock_call.return_value = {}
        
        server.tron_build_tx(
            from_address="FromAddr",
            to_address="ToAddr",
            amount=10.0
        )
        
        args = mock_call.call_args[0][1]
        self.assertEqual(args["token"], "USDT")

    @patch('tron_mcp_server.call_router.call')
    def test_default_force_execution_false(self, mock_call):
        """验证默认 force_execution 为 False"""
        mock_call.return_value = {}
        
        server.tron_build_tx(
            from_address="FromAddr",
            to_address="ToAddr",
            amount=10.0
        )
        
        args = mock_call.call_args[0][1]
        self.assertEqual(args["force_execution"], False)


class TestTronSignAndBroadcastTransaction(unittest.TestCase):
    """测试 tron_sign_and_broadcast_transaction 工具"""

    @patch('tron_mcp_server.call_router.call')
    def test_calls_router_with_correct_action(self, mock_call):
        """验证正确调用 call_router.call 并传入 sign_and_broadcast action"""
        mock_call.return_value = {"result": True, "txid": "a" * 64}
        
        tx_json = json.dumps({"txID": "a" * 64, "raw_data": {}})
        result = server.tron_sign_and_broadcast_transaction(tx_json)
        
        mock_call.assert_called_once()
        args = mock_call.call_args
        self.assertEqual(args[0][0], "sign_and_broadcast")
        self.assertIsInstance(args[0][1]["transaction"], dict)
        self.assertEqual(result["result"], True)

    @patch('tron_mcp_server.call_router.call')
    def test_json_string_deserialization(self, mock_call):
        """验证 JSON 字符串正确反序列化为字典"""
        mock_call.return_value = {}
        
        tx_dict = {"txID": "b" * 64, "raw_data": {"test": "data"}}
        tx_json = json.dumps(tx_dict)
        
        server.tron_sign_and_broadcast_transaction(tx_json)
        
        args = mock_call.call_args[0][1]
        self.assertEqual(args["transaction"], tx_dict)

    @patch('tron_mcp_server.call_router.call')
    def test_dict_input_accepted(self, mock_call):
        """验证接受字典输入"""
        mock_call.return_value = {}
        
        tx_dict = {"txID": "c" * 64, "raw_data": {}}
        
        server.tron_sign_and_broadcast_transaction(tx_dict)
        
        args = mock_call.call_args[0][1]
        self.assertEqual(args["transaction"], tx_dict)

    def test_invalid_json_returns_error(self):
        """验证无效 JSON 返回错误"""
        result = server.tron_sign_and_broadcast_transaction("invalid json {")
        
        self.assertIn("error", result)
        self.assertIn("JSON", result["summary"])


class TestTronBroadcastTx(unittest.TestCase):
    """测试 tron_broadcast_tx 工具"""

    @patch('tron_mcp_server.call_router.call')
    def test_calls_router_with_correct_action(self, mock_call):
        """验证正确调用 call_router.call 并传入 broadcast_tx action"""
        mock_call.return_value = {"result": True, "txid": "a" * 64}
        
        signed_tx = json.dumps({"txID": "a" * 64, "signature": ["sig"]})
        result = server.tron_broadcast_tx(signed_tx)
        
        mock_call.assert_called_once_with(
            "broadcast_tx",
            {"signed_tx_json": signed_tx}
        )
        self.assertEqual(result["result"], True)


class TestTronTransfer(unittest.TestCase):
    """测试 tron_transfer 工具"""

    @patch('tron_mcp_server.call_router.call')
    def test_calls_router_with_correct_action(self, mock_call):
        """验证正确调用 call_router.call 并传入 transfer action"""
        mock_call.return_value = {"result": True, "txid": "a" * 64}
        
        result = server.tron_transfer(
            to_address="TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            amount=100.0,
            token="USDT",
            force_execution=False
        )
        
        mock_call.assert_called_once()
        args = mock_call.call_args
        self.assertEqual(args[0][0], "transfer")
        self.assertEqual(args[0][1]["to"], "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf")
        self.assertEqual(args[0][1]["amount"], 100.0)
        self.assertEqual(args[0][1]["token"], "USDT")
        self.assertEqual(args[0][1]["force_execution"], False)

    @patch('tron_mcp_server.call_router.call')
    def test_default_token_usdt(self, mock_call):
        """验证默认 token 为 USDT"""
        mock_call.return_value = {}
        
        server.tron_transfer(
            to_address="ToAddr",
            amount=10.0
        )
        
        args = mock_call.call_args[0][1]
        self.assertEqual(args["token"], "USDT")

    @patch('tron_mcp_server.call_router.call')
    def test_default_force_execution_false(self, mock_call):
        """验证默认 force_execution 为 False"""
        mock_call.return_value = {}
        
        server.tron_transfer(
            to_address="ToAddr",
            amount=10.0
        )
        
        args = mock_call.call_args[0][1]
        self.assertEqual(args["force_execution"], False)


class TestTronGetWalletInfo(unittest.TestCase):
    """测试 tron_get_wallet_info 工具"""

    @patch('tron_mcp_server.call_router.call')
    def test_calls_router_with_correct_action(self, mock_call):
        """验证正确调用 call_router.call 并传入 get_wallet_info action"""
        mock_call.return_value = {
            "address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "trx_balance": 100.0,
            "usdt_balance": 50.0
        }
        
        result = server.tron_get_wallet_info()
        
        mock_call.assert_called_once_with("get_wallet_info", {})
        self.assertIn("address", result)


class TestTronGetTransactionHistory(unittest.TestCase):
    """测试 tron_get_transaction_history 工具"""

    @patch('tron_mcp_server.call_router.call')
    def test_calls_router_with_correct_action(self, mock_call):
        """验证正确调用 call_router.call 并传入 get_transaction_history action"""
        mock_call.return_value = {"transfers": [], "total": 0}
        
        result = server.tron_get_transaction_history(
            address="TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            limit=10,
            start=0,
            token=None
        )
        
        mock_call.assert_called_once_with(
            "get_transaction_history",
            {
                "address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
                "limit": 10,
                "start": 0,
                "token": None
            }
        )

    @patch('tron_mcp_server.call_router.call')
    def test_default_parameters(self, mock_call):
        """验证默认参数"""
        mock_call.return_value = {}
        
        server.tron_get_transaction_history(
            address="TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"
        )
        
        args = mock_call.call_args[0][1]
        self.assertEqual(args["limit"], 10)
        self.assertEqual(args["start"], 0)
        self.assertIsNone(args["token"])


class TestCallCompatibilityMode(unittest.TestCase):
    """测试 call 兼容模式单入口"""

    @patch('tron_mcp_server.call_router.call')
    def test_calls_router_directly(self, mock_call):
        """验证直接调用 call_router.call"""
        mock_call.return_value = {"result": "success"}
        
        result = server.call("get_balance", {"address": "TestAddr"})
        
        mock_call.assert_called_once_with(
            "get_balance",
            {"address": "TestAddr"}
        )
        self.assertEqual(result, {"result": "success"})

    @patch('tron_mcp_server.call_router.call')
    def test_none_params_converted_to_empty_dict(self, mock_call):
        """验证 None params 转换为空字典"""
        mock_call.return_value = {}
        
        server.call("get_network_status", None)
        
        mock_call.assert_called_once_with("get_network_status", {})

    @patch('tron_mcp_server.call_router.call')
    def test_missing_params_defaults_to_empty_dict(self, mock_call):
        """验证缺省 params 默认为空字典"""
        mock_call.return_value = {}
        
        server.call("skills")
        
        mock_call.assert_called_once_with("skills", {})


if __name__ == "__main__":
    unittest.main()
