"""
测试 call_router.py - 补全剩余路由的集成测试
=============================================

补齐 call_router 中 test_call_router_queries.py 未覆盖的路由：
- sign_tx: 签名路由（缺参数、无效 JSON、缺 txID、缺 raw_data、正常签名）
- broadcast_tx: 广播路由（缺参数、无效 JSON、正常广播、广播失败）
- transfer: 完整转账路由（缺参数、无效地址、无效金额、无私钥、不支持的代币、
           安全拦截、余额不足、正常 USDT 转账、正常 TRX 转账、force_execution）
- get_wallet_info: 钱包信息路由（正常流程、无私钥、余额查询失败）
- get_internal_transactions: 内部交易路由（缺参数、无效地址、正常流程、无效 limit）
- get_account_tokens: 代币列表路由（缺参数、无效地址、正常流程）
- unknown_action: 未知动作路由
"""

import unittest
import sys
import os
import json

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

from tron_mcp_server import call_router

# 测试用私钥（仅用于测试）
TEST_PRIVATE_KEY = "0000000000000000000000000000000000000000000000000000000000000001"
TEST_ADDRESS = "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"
TEST_TO = "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf"


class TestUnknownAction(unittest.TestCase):
    """测试未知动作路由"""

    def test_unknown_action_returns_error(self):
        """未知动作应返回错误"""
        result = call_router.call("nonexistent_action", {})
        self.assertIn("error", result)
        self.assertIn("未知", result["summary"])

    def test_none_params_handled(self):
        """params 为 None 应正常处理"""
        result = call_router.call("get_usdt_balance", None)
        self.assertIn("error", result)


class TestSignTxRoute(unittest.TestCase):
    """测试 sign_tx 路由"""

    def test_missing_unsigned_tx_json(self):
        """缺少 unsigned_tx_json 参数应返回错误"""
        result = call_router.call("sign_tx", {})
        self.assertIn("error", result)
        self.assertIn("unsigned_tx_json", result["summary"])

    def test_invalid_json_string(self):
        """无效 JSON 字符串应返回错误"""
        result = call_router.call("sign_tx", {"unsigned_tx_json": "not valid json"})
        self.assertIn("error", result)
        self.assertIn("invalid_json", result["error"])

    def test_missing_txid_field(self):
        """缺少 txID 字段应返回错误"""
        tx = json.dumps({"raw_data": {}})
        result = call_router.call("sign_tx", {"unsigned_tx_json": tx})
        self.assertIn("error", result)
        self.assertIn("txID", result["summary"])

    def test_missing_raw_data_field(self):
        """缺少 raw_data 字段应返回错误"""
        tx = json.dumps({"txID": "a" * 64})
        result = call_router.call("sign_tx", {"unsigned_tx_json": tx})
        self.assertIn("error", result)
        self.assertIn("raw_data", result["summary"])

    @patch.dict(os.environ, {"TRON_PRIVATE_KEY": TEST_PRIVATE_KEY})
    def test_successful_signing(self):
        """正常签名应返回签名后的交易"""
        unsigned_tx = {
            "txID": "a" * 64,
            "raw_data": {
                "contract": [{
                    "parameter": {
                        "value": {
                            "amount": 10000000,
                            "owner_address": TEST_ADDRESS,
                            "to_address": TEST_TO,
                        }
                    },
                    "type": "TransferContract",
                }],
            },
        }
        result = call_router.call("sign_tx", {"unsigned_tx_json": json.dumps(unsigned_tx)})
        self.assertNotIn("error", result)
        self.assertIn("signed_tx", result)
        self.assertIn("signature", result["signed_tx"])

    @patch.dict(os.environ, {"TRON_PRIVATE_KEY": TEST_PRIVATE_KEY})
    def test_signing_with_dict_input(self):
        """支持 dict 类型输入"""
        unsigned_tx = {
            "txID": "b" * 64,
            "raw_data": {"contract": []},
        }
        result = call_router.call("sign_tx", {"unsigned_tx_json": unsigned_tx})
        self.assertNotIn("error", result)
        self.assertIn("signed_tx", result)

    def test_signing_no_private_key(self):
        """未配置私钥应返回错误"""
        with patch.dict(os.environ, {}, clear=True):
            unsigned_tx = json.dumps({"txID": "c" * 64, "raw_data": {}})
            result = call_router.call("sign_tx", {"unsigned_tx_json": unsigned_tx})
            self.assertIn("error", result)


class TestBroadcastTxRoute(unittest.TestCase):
    """测试 broadcast_tx 路由"""

    def test_missing_signed_tx_json(self):
        """缺少 signed_tx_json 参数应返回错误"""
        result = call_router.call("broadcast_tx", {})
        self.assertIn("error", result)
        self.assertIn("signed_tx_json", result["summary"])

    def test_invalid_json_string(self):
        """无效 JSON 字符串应返回错误"""
        result = call_router.call("broadcast_tx", {"signed_tx_json": "bad json"})
        self.assertIn("error", result)

    @patch('tron_mcp_server.trongrid_client.broadcast_transaction')
    def test_successful_broadcast(self, mock_broadcast):
        """正常广播应返回成功结果"""
        mock_broadcast.return_value = {"result": True, "txid": "a" * 64}
        
        signed_tx = {
            "txID": "a" * 64,
            "raw_data": {},
            "signature": ["sig123"],
        }
        result = call_router.call("broadcast_tx", {"signed_tx_json": json.dumps(signed_tx)})
        self.assertNotIn("error", result)
        self.assertTrue(result["result"])
        self.assertEqual(result["txid"], "a" * 64)

    @patch('tron_mcp_server.trongrid_client.broadcast_transaction')
    def test_broadcast_with_dict_input(self, mock_broadcast):
        """支持 dict 类型输入"""
        mock_broadcast.return_value = {"result": True, "txid": "b" * 64}
        
        signed_tx = {
            "txID": "b" * 64,
            "raw_data": {},
            "signature": ["sig123"],
        }
        result = call_router.call("broadcast_tx", {"signed_tx_json": signed_tx})
        self.assertNotIn("error", result)
        self.assertTrue(result["result"])

    @patch('tron_mcp_server.trongrid_client.broadcast_transaction')
    def test_broadcast_value_error(self, mock_broadcast):
        """广播 ValueError 应返回 broadcast_error"""
        mock_broadcast.side_effect = ValueError("交易过期")
        
        signed_tx = json.dumps({"txID": "c" * 64, "raw_data": {}, "signature": ["sig"]})
        result = call_router.call("broadcast_tx", {"signed_tx_json": signed_tx})
        self.assertIn("error", result)
        self.assertIn("broadcast_error", result["error"])

    @patch('tron_mcp_server.trongrid_client.broadcast_transaction')
    def test_broadcast_general_error(self, mock_broadcast):
        """广播一般异常应返回 broadcast_error"""
        mock_broadcast.side_effect = Exception("Network error")
        
        signed_tx = json.dumps({"txID": "d" * 64, "raw_data": {}, "signature": ["sig"]})
        result = call_router.call("broadcast_tx", {"signed_tx_json": signed_tx})
        self.assertIn("error", result)


class TestTransferRoute(unittest.TestCase):
    """测试 transfer 路由 - 完整转账闭环"""

    def test_missing_to_parameter(self):
        """缺少 to 参数应返回错误"""
        result = call_router.call("transfer", {"amount": 10})
        self.assertIn("error", result)
        self.assertIn("to", result["summary"].lower())

    def test_missing_amount_parameter(self):
        """缺少 amount 参数应返回错误"""
        result = call_router.call("transfer", {"to": TEST_TO})
        self.assertIn("error", result)
        self.assertIn("amount", result["summary"].lower())

    def test_invalid_to_address(self):
        """无效接收方地址应返回错误"""
        result = call_router.call("transfer", {"to": "bad_addr", "amount": 10})
        self.assertIn("error", result)
        self.assertIn("无效", result["summary"])

    def test_invalid_amount_zero(self):
        """零金额应返回错误"""
        result = call_router.call("transfer", {"to": TEST_TO, "amount": 0})
        self.assertIn("error", result)
        self.assertIn("正数", result["summary"])

    def test_invalid_amount_negative(self):
        """负金额应返回错误"""
        result = call_router.call("transfer", {"to": TEST_TO, "amount": -5})
        self.assertIn("error", result)

    def test_no_private_key(self):
        """未配置私钥应返回 wallet_error"""
        with patch.dict(os.environ, {}, clear=True):
            result = call_router.call("transfer", {"to": TEST_TO, "amount": 10})
            self.assertIn("error", result)
            self.assertIn("wallet_error", result["error"])

    @patch('tron_mcp_server.key_manager.load_private_key')
    @patch('tron_mcp_server.key_manager.get_address_from_private_key')
    def test_unsupported_token(self, mock_get_addr, mock_load_pk):
        """不支持的代币应返回 invalid_token"""
        mock_load_pk.return_value = TEST_PRIVATE_KEY
        mock_get_addr.return_value = TEST_ADDRESS
        
        result = call_router.call("transfer", {"to": TEST_TO, "amount": 10, "token": "ETH"})
        self.assertIn("error", result)
        self.assertIn("invalid_token", result["error"])

    @patch('tron_mcp_server.trongrid_client.broadcast_transaction')
    @patch('tron_mcp_server.key_manager.sign_transaction')
    @patch('tron_mcp_server.trongrid_client.build_trc20_transfer')
    @patch('tron_mcp_server.tx_builder.build_unsigned_tx')
    @patch('tron_mcp_server.key_manager.get_address_from_private_key')
    @patch('tron_mcp_server.key_manager.load_private_key')
    def test_successful_usdt_transfer(self, mock_load_pk, mock_get_addr, mock_preview,
                                       mock_build, mock_sign, mock_broadcast):
        """正常 USDT 转账应返回成功结果"""
        mock_load_pk.return_value = TEST_PRIVATE_KEY
        mock_get_addr.return_value = TEST_ADDRESS
        mock_preview.return_value = {
            "txID": "a" * 64,
            "raw_data": {},
        }
        mock_build.return_value = {
            "txID": "b" * 64,
            "raw_data": {},
        }
        mock_sign.return_value = "sig" * 43 + "s"  # 130 chars
        mock_broadcast.return_value = {"result": True, "txid": "b" * 64}
        
        result = call_router.call("transfer", {"to": TEST_TO, "amount": 100, "token": "USDT"})
        self.assertNotIn("error", result)
        self.assertTrue(result["result"])
        self.assertIn("txid", result)

    @patch('tron_mcp_server.trongrid_client.broadcast_transaction')
    @patch('tron_mcp_server.key_manager.sign_transaction')
    @patch('tron_mcp_server.trongrid_client.build_trx_transfer')
    @patch('tron_mcp_server.tx_builder.build_unsigned_tx')
    @patch('tron_mcp_server.key_manager.get_address_from_private_key')
    @patch('tron_mcp_server.key_manager.load_private_key')
    def test_successful_trx_transfer(self, mock_load_pk, mock_get_addr, mock_preview,
                                      mock_build, mock_sign, mock_broadcast):
        """正常 TRX 转账应返回成功结果"""
        mock_load_pk.return_value = TEST_PRIVATE_KEY
        mock_get_addr.return_value = TEST_ADDRESS
        mock_preview.return_value = {
            "txID": "c" * 64,
            "raw_data": {},
        }
        mock_build.return_value = {
            "txID": "d" * 64,
            "raw_data": {},
        }
        mock_sign.return_value = "sig" * 43 + "s"  # 130 chars
        mock_broadcast.return_value = {"result": True, "txid": "d" * 64}
        
        result = call_router.call("transfer", {"to": TEST_TO, "amount": 10, "token": "TRX"})
        self.assertNotIn("error", result)
        self.assertTrue(result["result"])

    @patch('tron_mcp_server.tx_builder.build_unsigned_tx')
    @patch('tron_mcp_server.key_manager.get_address_from_private_key')
    @patch('tron_mcp_server.key_manager.load_private_key')
    def test_transfer_blocked_by_risk(self, mock_load_pk, mock_get_addr, mock_preview):
        """安全拦截应返回 blocked"""
        mock_load_pk.return_value = TEST_PRIVATE_KEY
        mock_get_addr.return_value = TEST_ADDRESS
        mock_preview.return_value = {
            "blocked": True,
            "summary": "🛑 交易已拦截",
        }
        
        result = call_router.call("transfer", {"to": TEST_TO, "amount": 100})
        self.assertTrue(result["blocked"])

    @patch('tron_mcp_server.tx_builder.build_unsigned_tx')
    @patch('tron_mcp_server.key_manager.get_address_from_private_key')
    @patch('tron_mcp_server.key_manager.load_private_key')
    def test_transfer_insufficient_balance(self, mock_load_pk, mock_get_addr, mock_preview):
        """余额不足应返回错误详情"""
        from tron_mcp_server.tx_builder import InsufficientBalanceError
        mock_load_pk.return_value = TEST_PRIVATE_KEY
        mock_get_addr.return_value = TEST_ADDRESS
        mock_preview.side_effect = InsufficientBalanceError(
            "余额不足", error_code="insufficient_usdt",
            details={"required": 100, "available": 10}
        )
        
        result = call_router.call("transfer", {"to": TEST_TO, "amount": 100})
        self.assertTrue(result["error"])
        self.assertEqual(result["error_type"], "insufficient_usdt")

    @patch('tron_mcp_server.tx_builder.build_unsigned_tx')
    @patch('tron_mcp_server.key_manager.get_address_from_private_key')
    @patch('tron_mcp_server.key_manager.load_private_key')
    def test_transfer_validation_error(self, mock_load_pk, mock_get_addr, mock_preview):
        """验证错误应返回 validation_error"""
        mock_load_pk.return_value = TEST_PRIVATE_KEY
        mock_get_addr.return_value = TEST_ADDRESS
        mock_preview.side_effect = ValueError("金额无效")
        
        result = call_router.call("transfer", {"to": TEST_TO, "amount": 10})
        self.assertIn("error", result)
        self.assertIn("validation_error", result["error"])

    @patch('tron_mcp_server.trongrid_client.build_trc20_transfer')
    @patch('tron_mcp_server.tx_builder.build_unsigned_tx')
    @patch('tron_mcp_server.key_manager.get_address_from_private_key')
    @patch('tron_mcp_server.key_manager.load_private_key')
    def test_transfer_build_error(self, mock_load_pk, mock_get_addr, mock_preview, mock_build):
        """TronGrid 构建失败应返回 build_error"""
        mock_load_pk.return_value = TEST_PRIVATE_KEY
        mock_get_addr.return_value = TEST_ADDRESS
        mock_preview.return_value = {"txID": "a" * 64, "raw_data": {}}
        mock_build.side_effect = Exception("TronGrid error")
        
        result = call_router.call("transfer", {"to": TEST_TO, "amount": 100, "token": "USDT"})
        self.assertIn("error", result)
        self.assertIn("build_error", result["error"])

    @patch('tron_mcp_server.key_manager.sign_transaction')
    @patch('tron_mcp_server.trongrid_client.build_trc20_transfer')
    @patch('tron_mcp_server.tx_builder.build_unsigned_tx')
    @patch('tron_mcp_server.key_manager.get_address_from_private_key')
    @patch('tron_mcp_server.key_manager.load_private_key')
    def test_transfer_sign_error(self, mock_load_pk, mock_get_addr, mock_preview, mock_build, mock_sign):
        """签名失败应返回 sign_error"""
        mock_load_pk.return_value = TEST_PRIVATE_KEY
        mock_get_addr.return_value = TEST_ADDRESS
        mock_preview.return_value = {"txID": "a" * 64, "raw_data": {}}
        mock_build.return_value = {"txID": "b" * 64, "raw_data": {}}
        mock_sign.side_effect = Exception("Signing failed")
        
        result = call_router.call("transfer", {"to": TEST_TO, "amount": 100, "token": "USDT"})
        self.assertIn("error", result)
        self.assertIn("sign_error", result["error"])

    @patch('tron_mcp_server.trongrid_client.broadcast_transaction')
    @patch('tron_mcp_server.key_manager.sign_transaction')
    @patch('tron_mcp_server.trongrid_client.build_trc20_transfer')
    @patch('tron_mcp_server.tx_builder.build_unsigned_tx')
    @patch('tron_mcp_server.key_manager.get_address_from_private_key')
    @patch('tron_mcp_server.key_manager.load_private_key')
    def test_transfer_broadcast_error(self, mock_load_pk, mock_get_addr, mock_preview,
                                       mock_build, mock_sign, mock_broadcast):
        """广播失败应返回 broadcast_error"""
        mock_load_pk.return_value = TEST_PRIVATE_KEY
        mock_get_addr.return_value = TEST_ADDRESS
        mock_preview.return_value = {"txID": "a" * 64, "raw_data": {}}
        mock_build.return_value = {"txID": "b" * 64, "raw_data": {}}
        mock_sign.return_value = "sig" * 43 + "s"
        mock_broadcast.side_effect = Exception("Broadcast failed")
        
        result = call_router.call("transfer", {"to": TEST_TO, "amount": 100, "token": "USDT"})
        self.assertIn("error", result)
        self.assertIn("broadcast_error", result["error"])


class TestGetWalletInfoRoute(unittest.TestCase):
    """测试 get_wallet_info 路由"""

    def test_no_private_key(self):
        """未配置私钥应返回 wallet_error"""
        with patch.dict(os.environ, {}, clear=True):
            result = call_router.call("get_wallet_info", {})
            self.assertIn("error", result)
            self.assertIn("wallet_error", result["error"])

    @patch('tron_mcp_server.tron_client.get_usdt_balance')
    @patch('tron_mcp_server.tron_client.get_balance_trx')
    @patch('tron_mcp_server.key_manager.get_address_from_private_key')
    @patch('tron_mcp_server.key_manager.load_private_key')
    def test_successful_wallet_info(self, mock_load_pk, mock_get_addr, mock_trx, mock_usdt):
        """正常流程应返回钱包信息"""
        mock_load_pk.return_value = TEST_PRIVATE_KEY
        mock_get_addr.return_value = TEST_ADDRESS
        mock_trx.return_value = 50.0
        mock_usdt.return_value = 100.0
        
        result = call_router.call("get_wallet_info", {})
        self.assertNotIn("error", result)
        self.assertEqual(result["address"], TEST_ADDRESS)
        self.assertEqual(result["trx_balance"], 50.0)
        self.assertEqual(result["usdt_balance"], 100.0)

    @patch('tron_mcp_server.tron_client.get_usdt_balance')
    @patch('tron_mcp_server.tron_client.get_balance_trx')
    @patch('tron_mcp_server.key_manager.get_address_from_private_key')
    @patch('tron_mcp_server.key_manager.load_private_key')
    def test_balance_query_failure_graceful(self, mock_load_pk, mock_get_addr, mock_trx, mock_usdt):
        """余额查询失败应优雅降级（仍返回地址）"""
        mock_load_pk.return_value = TEST_PRIVATE_KEY
        mock_get_addr.return_value = TEST_ADDRESS
        mock_trx.side_effect = Exception("Network error")
        mock_usdt.side_effect = Exception("Network error")
        
        result = call_router.call("get_wallet_info", {})
        self.assertNotIn("error", result)
        self.assertEqual(result["address"], TEST_ADDRESS)
        # 余额应为 0（查询失败时默认值）
        self.assertEqual(result["trx_balance"], 0.0)
        self.assertEqual(result["usdt_balance"], 0.0)


class TestGetInternalTransactionsRoute(unittest.TestCase):
    """测试 get_internal_transactions 路由"""

    def test_missing_address(self):
        """缺少 address 应返回错误"""
        result = call_router.call("get_internal_transactions", {})
        self.assertIn("error", result)
        self.assertIn("address", result["summary"].lower())

    def test_invalid_address(self):
        """无效地址应返回错误"""
        result = call_router.call("get_internal_transactions", {"address": "bad"})
        self.assertIn("error", result)
        self.assertIn("无效", result["summary"])

    def test_invalid_limit_too_large(self):
        """limit 过大应返回错误"""
        result = call_router.call("get_internal_transactions", {
            "address": TEST_ADDRESS,
            "limit": 100,
        })
        self.assertIn("error", result)

    def test_invalid_limit_too_small(self):
        """limit 过小应返回错误"""
        result = call_router.call("get_internal_transactions", {
            "address": TEST_ADDRESS,
            "limit": 0,
        })
        self.assertIn("error", result)

    def test_invalid_limit_not_int(self):
        """limit 非整数应返回错误"""
        result = call_router.call("get_internal_transactions", {
            "address": TEST_ADDRESS,
            "limit": "abc",
        })
        self.assertIn("error", result)

    def test_negative_start_corrected(self):
        """负 start 应被修正为 0"""
        with patch('tron_mcp_server.tron_client.get_internal_transactions') as mock_get:
            mock_get.return_value = {"data": [], "total": 0}
            call_router.call("get_internal_transactions", {
                "address": TEST_ADDRESS,
                "start": -5,
            })
            # 应被修正为 0
            call_args = mock_get.call_args
            self.assertEqual(call_args[0][2], 0)  # start parameter

    @patch('tron_mcp_server.tron_client.get_internal_transactions')
    def test_successful_query(self, mock_get):
        """正常查询应返回格式化结果"""
        mock_get.return_value = {
            "data": [
                {
                    "hash": "a" * 64,
                    "callerAddress": TEST_ADDRESS,
                    "transferToAddress": TEST_TO,
                    "callValueInfo": [{"callValue": 1000000}],
                    "timestamp": 1700000000000,
                }
            ],
            "total": 1,
        }
        result = call_router.call("get_internal_transactions", {"address": TEST_ADDRESS})
        self.assertNotIn("error", result)
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["displayed"], 1)

    @patch('tron_mcp_server.tron_client.get_internal_transactions')
    def test_rpc_error_handling(self, mock_get):
        """RPC 异常应返回错误"""
        mock_get.side_effect = Exception("Network error")
        result = call_router.call("get_internal_transactions", {"address": TEST_ADDRESS})
        self.assertIn("error", result)


class TestGetAccountTokensRoute(unittest.TestCase):
    """测试 get_account_tokens 路由"""

    def test_missing_address(self):
        """缺少 address 应返回错误"""
        result = call_router.call("get_account_tokens", {})
        self.assertIn("error", result)
        self.assertIn("address", result["summary"].lower())

    def test_invalid_address(self):
        """无效地址应返回错误"""
        result = call_router.call("get_account_tokens", {"address": "bad"})
        self.assertIn("error", result)
        self.assertIn("无效", result["summary"])

    @patch('tron_mcp_server.tron_client.get_account_tokens')
    def test_successful_query(self, mock_get):
        """正常查询应返回代币列表"""
        mock_get.return_value = {
            "address": TEST_ADDRESS,
            "token_count": 2,
            "tokens": [
                {"token_name": "TRX", "token_abbr": "TRX", "balance": 50.0},
                {"token_name": "Tether USD", "token_abbr": "USDT", "balance": 100.0},
            ],
        }
        result = call_router.call("get_account_tokens", {"address": TEST_ADDRESS})
        self.assertNotIn("error", result)
        self.assertEqual(result["token_count"], 2)

    @patch('tron_mcp_server.tron_client.get_account_tokens')
    def test_rpc_error_handling(self, mock_get):
        """RPC 异常应返回错误"""
        mock_get.side_effect = Exception("Network error")
        result = call_router.call("get_account_tokens", {"address": TEST_ADDRESS})
        self.assertIn("error", result)


class TestGetTransactionHistoryRoute(unittest.TestCase):
    """测试 get_transaction_history 路由补充"""

    def test_missing_address(self):
        """缺少 address 应返回错误"""
        result = call_router.call("get_transaction_history", {})
        self.assertIn("error", result)

    def test_invalid_address(self):
        """无效地址应返回错误"""
        result = call_router.call("get_transaction_history", {"address": "bad"})
        self.assertIn("error", result)

    def test_invalid_limit_too_large(self):
        """limit > 50 应返回错误"""
        result = call_router.call("get_transaction_history", {
            "address": TEST_ADDRESS,
            "limit": 100,
        })
        self.assertIn("error", result)

    def test_invalid_limit_non_integer(self):
        """非整数 limit 应返回错误"""
        result = call_router.call("get_transaction_history", {
            "address": TEST_ADDRESS,
            "limit": "abc",
        })
        self.assertIn("error", result)

    def test_invalid_start_non_integer(self):
        """非整数 start 应返回错误"""
        result = call_router.call("get_transaction_history", {
            "address": TEST_ADDRESS,
            "start": "xyz",
        })
        self.assertIn("error", result)

    @patch('tron_mcp_server.tron_client.get_trc20_transfer_history')
    @patch('tron_mcp_server.tron_client.get_transfer_history')
    def test_no_token_filter_merges_results(self, mock_trx, mock_trc20):
        """无 token 筛选应合并 TRX 和 TRC20 结果"""
        mock_trx.return_value = {"data": [{"timestamp": 2}], "total": 1}
        mock_trc20.return_value = {"token_transfers": [{"block_ts": 1}], "total": 1}
        
        result = call_router.call("get_transaction_history", {"address": TEST_ADDRESS})
        self.assertNotIn("error", result)
        self.assertEqual(result["total"], 2)

    @patch('tron_mcp_server.tron_client.get_trc20_transfer_history')
    def test_usdt_token_filter(self, mock_trc20):
        """USDT 筛选应查询 TRC20"""
        mock_trc20.return_value = {"token_transfers": [], "total": 0}
        
        result = call_router.call("get_transaction_history", {
            "address": TEST_ADDRESS,
            "token": "USDT",
        })
        self.assertNotIn("error", result)
        mock_trc20.assert_called_once()

    @patch('tron_mcp_server.tron_client.get_transfer_history')
    def test_trx_token_filter(self, mock_trx):
        """TRX 筛选应查询 transfer"""
        mock_trx.return_value = {"data": [], "total": 0}
        
        result = call_router.call("get_transaction_history", {
            "address": TEST_ADDRESS,
            "token": "TRX",
        })
        self.assertNotIn("error", result)
        mock_trx.assert_called_once()

    @patch('tron_mcp_server.tron_client.get_trc20_transfer_history')
    def test_trc20_contract_address_filter(self, mock_trc20):
        """TRC20 合约地址筛选"""
        contract_addr = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
        mock_trc20.return_value = {"token_transfers": [], "total": 0}
        
        result = call_router.call("get_transaction_history", {
            "address": TEST_ADDRESS,
            "token": contract_addr,
        })
        self.assertNotIn("error", result)

    @patch('tron_mcp_server.tron_client.get_transfer_history')
    def test_trc10_token_name_filter(self, mock_trx):
        """TRC10 代币名称筛选"""
        mock_trx.return_value = {"data": [], "total": 0}
        
        result = call_router.call("get_transaction_history", {
            "address": TEST_ADDRESS,
            "token": "BitTorrent",
        })
        self.assertNotIn("error", result)

    @patch('tron_mcp_server.tron_client.get_trc20_transfer_history')
    @patch('tron_mcp_server.tron_client.get_transfer_history')
    def test_partial_api_failure_graceful(self, mock_trx, mock_trc20):
        """部分 API 失败应优雅降级"""
        mock_trx.side_effect = Exception("TRX API failed")
        mock_trc20.return_value = {"token_transfers": [], "total": 0}
        
        result = call_router.call("get_transaction_history", {"address": TEST_ADDRESS})
        self.assertNotIn("error", result)

    @patch('tron_mcp_server.tron_client.get_trc20_transfer_history')
    @patch('tron_mcp_server.tron_client.get_transfer_history')
    def test_rpc_error_handling(self, mock_trx, mock_trc20):
        """两个 API 都失败不应崩溃"""
        mock_trx.side_effect = Exception("API 1 failed")
        mock_trc20.side_effect = Exception("API 2 failed")
        
        # 不应抛出异常 - 应优雅降级
        result = call_router.call("get_transaction_history", {"address": TEST_ADDRESS})
        # 仍然应该有结果（可能为空列表）
        self.assertIn("total", result)


if __name__ == "__main__":
    unittest.main()
