"""
测试 tron_client.py - TRONSCAN REST API 封装
=============================================

覆盖以下功能的集成测试（使用 mock HTTP 响应）：
- _normalize_address: 地址格式标准化
- _normalize_txid: 交易哈希标准化
- _hex_to_base58: 十六进制地址转 Base58Check
- _to_int: 数值解析
- _first_not_none: 工具函数
- get_usdt_balance: USDT 余额查询
- get_balance_trx: TRX 余额查询
- get_gas_parameters: Gas 参数查询
- get_transaction_status: 交易状态查询
- get_network_status: 网络状态查询
- get_latest_block_info: 最新区块信息
- check_account_risk: 深度风险扫描
- broadcast_transaction: 广播交易
- get_account_status: 账户激活状态
- get_transfer_history: TRX/TRC10 转账记录
- get_trc20_transfer_history: TRC20 转账记录
- get_internal_transactions: 内部交易查询
- get_account_tokens: 账户代币列表
"""

import unittest
import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from unittest.mock import patch, MagicMock

sys.modules["mcp"] = MagicMock()
sys.modules["mcp.server"] = MagicMock()
sys.modules["mcp.server.fastmcp"] = MagicMock()

from tron_mcp_server import tron_client


# ============ 工具函数测试 ============

class TestNormalizeAddress(unittest.TestCase):
    """测试 _normalize_address"""

    def test_base58_address_unchanged(self):
        """Base58 地址应原样返回"""
        addr = "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"
        self.assertEqual(tron_client._normalize_address(addr), addr)

    def test_hex_address_with_0x_prefix(self):
        """0x41... 格式应转换为 Base58"""
        # 41 + 40 hex chars = 42 hex digits total; with 0x prefix = 44 chars
        hex_addr = "0x41" + "a" * 40
        result = tron_client._normalize_address(hex_addr)
        self.assertTrue(result.startswith("T"))

    def test_hex_address_without_0x_prefix(self):
        """41... 格式（42 字符）应转换为 Base58"""
        hex_addr = "41" + "a" * 40
        result = tron_client._normalize_address(hex_addr)
        self.assertTrue(result.startswith("T"))

    def test_other_format_unchanged(self):
        """其他格式应原样返回"""
        addr = "someaddress"
        self.assertEqual(tron_client._normalize_address(addr), addr)


class TestNormalizeTxid(unittest.TestCase):
    """测试 _normalize_txid"""

    def test_with_0x_prefix(self):
        """0x 前缀应被移除"""
        txid = "0x" + "a" * 64
        self.assertEqual(tron_client._normalize_txid(txid), "a" * 64)

    def test_without_prefix(self):
        """无前缀应原样返回"""
        txid = "b" * 64
        self.assertEqual(tron_client._normalize_txid(txid), txid)


class TestToInt(unittest.TestCase):
    """测试 _to_int 数值解析"""

    def test_none_raises(self):
        """None 应抛出 ValueError"""
        with self.assertRaises(ValueError):
            tron_client._to_int(None)

    def test_int_value(self):
        """整数直接返回"""
        self.assertEqual(tron_client._to_int(42), 42)

    def test_float_value(self):
        """浮点数截断为整数"""
        self.assertEqual(tron_client._to_int(3.7), 3)

    def test_string_decimal(self):
        """十进制字符串"""
        self.assertEqual(tron_client._to_int("100"), 100)

    def test_string_hex(self):
        """十六进制字符串"""
        self.assertEqual(tron_client._to_int("0xff"), 255)

    def test_bool_value(self):
        """布尔值转换"""
        self.assertEqual(tron_client._to_int(True), 1)
        self.assertEqual(tron_client._to_int(False), 0)

    def test_invalid_string_raises(self):
        """无法解析的字符串应抛出异常"""
        with self.assertRaises(ValueError):
            tron_client._to_int("abc")

    def test_unsupported_type_raises(self):
        """不支持的类型应抛出 ValueError"""
        with self.assertRaises(ValueError):
            tron_client._to_int([1, 2, 3])

    def test_string_with_whitespace(self):
        """含空格字符串"""
        self.assertEqual(tron_client._to_int("  42  "), 42)


class TestFirstNotNone(unittest.TestCase):
    """测试 _first_not_none"""

    def test_first_value_not_none(self):
        self.assertEqual(tron_client._first_not_none(1, 2, 3), 1)

    def test_first_is_none(self):
        self.assertEqual(tron_client._first_not_none(None, 2, 3), 2)

    def test_all_none(self):
        self.assertIsNone(tron_client._first_not_none(None, None))

    def test_zero_is_not_none(self):
        """0 应被视为有效值"""
        self.assertEqual(tron_client._first_not_none(0, 1), 0)

    def test_empty_string_is_not_none(self):
        """空字符串应被视为有效值"""
        self.assertEqual(tron_client._first_not_none("", "a"), "")


class TestHexToBase58(unittest.TestCase):
    """测试 _hex_to_base58"""

    def test_valid_hex_address(self):
        """有效十六进制地址应转换为 Base58"""
        # 41 prefix + 20 bytes = 42 hex chars
        hex_addr = "41" + "00" * 20
        result = tron_client._hex_to_base58(hex_addr)
        self.assertIsInstance(result, str)
        self.assertTrue(result.startswith("T"))


# ============ API 查询测试（mock HTTP 响应）============

class TestGetUsdtBalance(unittest.TestCase):
    """测试 get_usdt_balance"""

    @patch('tron_mcp_server.tron_client._get')
    def test_usdt_balance_found(self, mock_get):
        """能从 trc20token_balances 中找到 USDT 余额"""
        mock_get.return_value = {
            "trc20token_balances": [
                {
                    "tokenId": tron_client.USDT_CONTRACT_BASE58,
                    "balance": "100000000",
                    "tokenDecimal": "6",
                }
            ]
        }
        result = tron_client.get_usdt_balance("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertEqual(result, 100.0)

    @patch('tron_mcp_server.tron_client._get')
    def test_usdt_balance_zero_when_no_usdt(self, mock_get):
        """没有 USDT 持仓时返回 0.0"""
        mock_get.return_value = {"trc20token_balances": []}
        result = tron_client.get_usdt_balance("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertEqual(result, 0.0)

    @patch('tron_mcp_server.tron_client._get')
    def test_usdt_balance_alternate_field_names(self, mock_get):
        """兼容不同的字段名格式"""
        mock_get.return_value = {
            "trc20TokenBalances": [
                {
                    "contract_address": tron_client.USDT_CONTRACT_BASE58,
                    "token_balance": "50000000",
                    "token_decimals": "6",
                }
            ]
        }
        result = tron_client.get_usdt_balance("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertEqual(result, 50.0)

    @patch('tron_mcp_server.tron_client._get')
    def test_usdt_balance_hex_contract(self, mock_get):
        """通过 Hex 合约地址匹配 USDT"""
        mock_get.return_value = {
            "trc20token_balances": [
                {
                    "tokenId": tron_client.USDT_CONTRACT_HEX,
                    "balance": "25000000",
                    "tokenDecimal": "6",
                }
            ]
        }
        result = tron_client.get_usdt_balance("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertEqual(result, 25.0)

    @patch('tron_mcp_server.tron_client._get')
    def test_usdt_balance_with_no_token_balances_field(self, mock_get):
        """所有 token_balances 字段都不存在时返回 0.0"""
        mock_get.return_value = {}
        result = tron_client.get_usdt_balance("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertEqual(result, 0.0)


class TestGetBalanceTrx(unittest.TestCase):
    """测试 get_balance_trx"""

    @patch('tron_mcp_server.tron_client._get')
    def test_normal_balance(self, mock_get):
        """正常余额返回"""
        mock_get.return_value = {"balance": 50000000}
        result = tron_client.get_balance_trx("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertEqual(result, 50.0)

    @patch('tron_mcp_server.tron_client._get')
    def test_zero_balance(self, mock_get):
        """零余额"""
        mock_get.return_value = {"balance": 0}
        result = tron_client.get_balance_trx("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertEqual(result, 0.0)

    @patch('tron_mcp_server.tron_client._get')
    def test_alternate_balance_field(self, mock_get):
        """兼容 balanceSun 字段"""
        mock_get.return_value = {"balanceSun": 1000000}
        result = tron_client.get_balance_trx("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertEqual(result, 1.0)

    @patch('tron_mcp_server.tron_client._get')
    def test_fallback_to_zero(self, mock_get):
        """所有余额字段都不存在时返回 0"""
        mock_get.return_value = {}
        result = tron_client.get_balance_trx("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertEqual(result, 0.0)


class TestGetGasParameters(unittest.TestCase):
    """测试 get_gas_parameters"""

    @patch('tron_mcp_server.tron_client._get')
    def test_energy_fee_found(self, mock_get):
        """找到 getEnergyFee 参数"""
        mock_get.return_value = {
            "tronParameters": [
                {"key": "getEnergyFee", "value": 420},
            ]
        }
        result = tron_client.get_gas_parameters()
        self.assertEqual(result, 420)

    @patch('tron_mcp_server.tron_client._get')
    def test_fallback_to_transaction_fee(self, mock_get):
        """fallback 到 getTransactionFee"""
        mock_get.return_value = {
            "tronParameters": [
                {"key": "getTransactionFee", "value": 1000},
            ]
        }
        result = tron_client.get_gas_parameters()
        self.assertEqual(result, 1000)

    @patch('tron_mcp_server.tron_client._get')
    def test_missing_fee_param_raises(self, mock_get):
        """缺少费用参数应抛出 ValueError"""
        mock_get.return_value = {
            "tronParameters": [
                {"key": "otherParam", "value": 100},
            ]
        }
        with self.assertRaises(ValueError):
            tron_client.get_gas_parameters()

    @patch('tron_mcp_server.tron_client._get')
    def test_non_list_params_raises(self, mock_get):
        """参数不是列表时应抛出 ValueError"""
        mock_get.return_value = {"something": "wrong"}
        with self.assertRaises(ValueError):
            tron_client.get_gas_parameters()

    @patch('tron_mcp_server.tron_client._get')
    def test_chain_parameter_field(self, mock_get):
        """兼容 chainParameter 字段"""
        mock_get.return_value = {
            "chainParameter": [
                {"key": "getEnergyFee", "value": 280},
            ]
        }
        result = tron_client.get_gas_parameters()
        self.assertEqual(result, 280)


class TestGetNetworkStatus(unittest.TestCase):
    """测试 get_network_status"""

    @patch('tron_mcp_server.tron_client._get')
    def test_successful_query(self, mock_get):
        """正常查询应返回区块高度"""
        mock_get.return_value = {
            "data": [{"number": 55555555}]
        }
        result = tron_client.get_network_status()
        self.assertEqual(result, 55555555)

    @patch('tron_mcp_server.tron_client._get')
    def test_empty_blocks_raises(self, mock_get):
        """空区块数据应抛出 KeyError"""
        mock_get.return_value = {"data": []}
        with self.assertRaises(KeyError):
            tron_client.get_network_status()

    @patch('tron_mcp_server.tron_client._get')
    def test_missing_data_field_raises(self, mock_get):
        """缺少 data 字段应抛出 KeyError"""
        mock_get.return_value = {"other": "field"}
        with self.assertRaises(KeyError):
            tron_client.get_network_status()


class TestGetLatestBlockInfo(unittest.TestCase):
    """测试 get_latest_block_info"""

    @patch('tron_mcp_server.tron_client._get')
    def test_successful_query(self, mock_get):
        """正常查询应返回区块号和哈希"""
        mock_get.return_value = {
            "data": [{"number": 12345, "hash": "abc123" * 11}]
        }
        result = tron_client.get_latest_block_info()
        self.assertEqual(result["number"], 12345)
        self.assertIn("hash", result)

    @patch('tron_mcp_server.tron_client._get')
    def test_empty_response_raises(self, mock_get):
        """空响应应抛出 ValueError"""
        mock_get.return_value = {"data": []}
        with self.assertRaises(ValueError):
            tron_client.get_latest_block_info()


class TestCheckAccountRisk(unittest.TestCase):
    """测试 check_account_risk 深度风险扫描"""

    @patch('httpx.get')
    def test_safe_address(self, mock_httpx_get):
        """安全地址应返回 is_risky=False"""
        # Mock both API calls (AccountV2 and Security)
        mock_response_v2 = MagicMock()
        mock_response_v2.json.return_value = {
            "redTag": "", "greyTag": "", "blueTag": "Binance",
            "publicTag": "", "feedbackRisk": False,
        }
        mock_response_sec = MagicMock()
        mock_response_sec.json.return_value = {
            "is_black_list": False, "has_fraud_transaction": False,
            "fraud_token_creator": False, "send_ad_by_memo": False,
        }
        mock_httpx_get.side_effect = [mock_response_v2, mock_response_sec]
        
        result = tron_client.check_account_risk("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertFalse(result["is_risky"])
        self.assertEqual(result["risk_type"], "Safe")
        self.assertEqual(result["tags"]["Blue"], "Binance")

    @patch('httpx.get')
    def test_red_tag_risky(self, mock_httpx_get):
        """红标地址应返回 is_risky=True"""
        mock_response_v2 = MagicMock()
        mock_response_v2.json.return_value = {
            "redTag": "Scam", "greyTag": "", "blueTag": "",
            "publicTag": "", "feedbackRisk": False,
        }
        mock_response_sec = MagicMock()
        mock_response_sec.json.return_value = {
            "is_black_list": False, "has_fraud_transaction": False,
            "fraud_token_creator": False, "send_ad_by_memo": False,
        }
        mock_httpx_get.side_effect = [mock_response_v2, mock_response_sec]
        
        result = tron_client.check_account_risk("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertTrue(result["is_risky"])
        self.assertEqual(result["risk_type"], "Scam")

    @patch('httpx.get')
    def test_blacklisted_address(self, mock_httpx_get):
        """黑名单地址应返回 is_risky=True"""
        mock_response_v2 = MagicMock()
        mock_response_v2.json.return_value = {
            "redTag": "", "greyTag": "", "blueTag": "",
            "publicTag": "", "feedbackRisk": False,
        }
        mock_response_sec = MagicMock()
        mock_response_sec.json.return_value = {
            "is_black_list": True, "has_fraud_transaction": False,
            "fraud_token_creator": False, "send_ad_by_memo": False,
        }
        mock_httpx_get.side_effect = [mock_response_v2, mock_response_sec]
        
        result = tron_client.check_account_risk("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertTrue(result["is_risky"])
        self.assertEqual(result["risk_type"], "Blacklisted")

    @patch('httpx.get')
    def test_feedback_risk(self, mock_httpx_get):
        """用户投诉地址应返回 is_risky=True"""
        mock_response_v2 = MagicMock()
        mock_response_v2.json.return_value = {
            "redTag": "", "greyTag": "", "blueTag": "",
            "publicTag": "", "feedbackRisk": True,
        }
        mock_response_sec = MagicMock()
        mock_response_sec.json.return_value = {
            "is_black_list": False, "has_fraud_transaction": False,
            "fraud_token_creator": False, "send_ad_by_memo": False,
        }
        mock_httpx_get.side_effect = [mock_response_v2, mock_response_sec]
        
        result = tron_client.check_account_risk("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertTrue(result["is_risky"])
        self.assertEqual(result["risk_type"], "User Reported")

    @patch('httpx.get')
    def test_grey_tag_risky(self, mock_httpx_get):
        """灰标地址应返回 is_risky=True"""
        mock_response_v2 = MagicMock()
        mock_response_v2.json.return_value = {
            "redTag": "", "greyTag": "Suspicious", "blueTag": "",
            "publicTag": "", "feedbackRisk": False,
        }
        mock_response_sec = MagicMock()
        mock_response_sec.json.return_value = {
            "is_black_list": False, "has_fraud_transaction": False,
            "fraud_token_creator": False, "send_ad_by_memo": False,
        }
        mock_httpx_get.side_effect = [mock_response_v2, mock_response_sec]
        
        result = tron_client.check_account_risk("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertTrue(result["is_risky"])
        self.assertIn("Grey", result["risk_type"])

    @patch('httpx.get')
    def test_fraud_token_creator(self, mock_httpx_get):
        """假币创建者应返回 is_risky=True"""
        mock_response_v2 = MagicMock()
        mock_response_v2.json.return_value = {
            "redTag": "", "greyTag": "", "blueTag": "",
            "publicTag": "", "feedbackRisk": False,
        }
        mock_response_sec = MagicMock()
        mock_response_sec.json.return_value = {
            "is_black_list": False, "has_fraud_transaction": False,
            "fraud_token_creator": True, "send_ad_by_memo": False,
        }
        mock_httpx_get.side_effect = [mock_response_v2, mock_response_sec]
        
        result = tron_client.check_account_risk("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertTrue(result["is_risky"])
        self.assertEqual(result["risk_type"], "Fraud Token Creator")

    @patch('httpx.get')
    def test_spam_account(self, mock_httpx_get):
        """垃圾广告账号应返回 is_risky=True"""
        mock_response_v2 = MagicMock()
        mock_response_v2.json.return_value = {
            "redTag": "", "greyTag": "", "blueTag": "",
            "publicTag": "", "feedbackRisk": False,
        }
        mock_response_sec = MagicMock()
        mock_response_sec.json.return_value = {
            "is_black_list": False, "has_fraud_transaction": False,
            "fraud_token_creator": False, "send_ad_by_memo": True,
        }
        mock_httpx_get.side_effect = [mock_response_v2, mock_response_sec]
        
        result = tron_client.check_account_risk("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertTrue(result["is_risky"])
        self.assertEqual(result["risk_type"], "Spam Account")

    @patch('httpx.get')
    def test_both_apis_fail(self, mock_httpx_get):
        """两个 API 都失败应返回 Unknown 类型"""
        mock_httpx_get.side_effect = Exception("Network error")
        
        result = tron_client.check_account_risk("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertEqual(result["risk_type"], "Unknown")
        self.assertIn("Unable to verify", result["detail"])

    @patch('httpx.get')
    def test_v2_api_fails_only(self, mock_httpx_get):
        """仅 V2 API 失败应返回 Partially Verified"""
        mock_response_sec = MagicMock()
        mock_response_sec.json.return_value = {
            "is_black_list": False, "has_fraud_transaction": False,
            "fraud_token_creator": False, "send_ad_by_memo": False,
        }
        # First call (V2) fails, second call (Security) succeeds
        mock_httpx_get.side_effect = [Exception("V2 API timeout"), mock_response_sec]
        
        result = tron_client.check_account_risk("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertEqual(result["risk_type"], "Partially Verified")

    @patch('httpx.get')
    def test_has_fraud_transaction(self, mock_httpx_get):
        """有欺诈交易记录应返回 is_risky=True"""
        mock_response_v2 = MagicMock()
        mock_response_v2.json.return_value = {
            "redTag": "", "greyTag": "", "blueTag": "",
            "publicTag": "", "feedbackRisk": False,
        }
        mock_response_sec = MagicMock()
        mock_response_sec.json.return_value = {
            "is_black_list": False, "has_fraud_transaction": True,
            "fraud_token_creator": False, "send_ad_by_memo": False,
        }
        mock_httpx_get.side_effect = [mock_response_v2, mock_response_sec]
        
        result = tron_client.check_account_risk("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertTrue(result["is_risky"])
        self.assertEqual(result["risk_type"], "Fraud Transaction")

    @patch('httpx.get')
    def test_suspicious_public_tag(self, mock_httpx_get):
        """publicTag 包含 suspicious 应标记为 risky"""
        mock_response_v2 = MagicMock()
        mock_response_v2.json.return_value = {
            "redTag": "", "greyTag": "", "blueTag": "",
            "publicTag": "suspicious activity detected", "feedbackRisk": False,
        }
        mock_response_sec = MagicMock()
        mock_response_sec.json.return_value = {
            "is_black_list": False, "has_fraud_transaction": False,
            "fraud_token_creator": False, "send_ad_by_memo": False,
        }
        mock_httpx_get.side_effect = [mock_response_v2, mock_response_sec]
        
        result = tron_client.check_account_risk("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertTrue(result["is_risky"])

    @patch('httpx.get')
    def test_raw_info_field(self, mock_httpx_get):
        """raw_info 字段应包含所有风险指标"""
        mock_response_v2 = MagicMock()
        mock_response_v2.json.return_value = {
            "redTag": "", "greyTag": "", "blueTag": "",
            "publicTag": "", "feedbackRisk": False,
        }
        mock_response_sec = MagicMock()
        mock_response_sec.json.return_value = {
            "is_black_list": False, "has_fraud_transaction": False,
            "fraud_token_creator": False, "send_ad_by_memo": False,
        }
        mock_httpx_get.side_effect = [mock_response_v2, mock_response_sec]
        
        result = tron_client.check_account_risk("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertIn("raw_info", result)
        self.assertIn("redTag", result["raw_info"])
        self.assertIn("is_black_list", result["raw_info"])


class TestBroadcastTransaction(unittest.TestCase):
    """测试 broadcast_transaction"""

    @patch('httpx.post')
    def test_missing_signature_raises(self, mock_post):
        """缺少 signature 应抛出 ValueError"""
        with self.assertRaises(ValueError):
            tron_client.broadcast_transaction({"txID": "a" * 64, "raw_data": {}})

    @patch('httpx.post')
    def test_empty_signature_raises(self, mock_post):
        """空 signature 列表应抛出 ValueError"""
        with self.assertRaises(ValueError):
            tron_client.broadcast_transaction({"txID": "a" * 64, "raw_data": {}, "signature": []})

    @patch('httpx.post')
    def test_successful_broadcast(self, mock_post):
        """成功广播应返回 result=True"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": True, "txid": "a" * 64}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        
        signed_tx = {"txID": "a" * 64, "raw_data": {}, "signature": ["sig123"]}
        result = tron_client.broadcast_transaction(signed_tx)
        self.assertTrue(result["result"])
        self.assertEqual(result["txid"], "a" * 64)

    @patch('httpx.post')
    def test_failed_broadcast_raises(self, mock_post):
        """广播失败应抛出 ValueError"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": False, "message": "SIGERROR"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        
        signed_tx = {"txID": "a" * 64, "raw_data": {}, "signature": ["sig123"]}
        with self.assertRaises(ValueError):
            tron_client.broadcast_transaction(signed_tx)


class TestGetAccountStatus(unittest.TestCase):
    """测试 get_account_status"""

    @patch('tron_mcp_server.tron_client._get')
    def test_activated_account(self, mock_get):
        """已激活账户应返回 is_activated=True"""
        mock_get.return_value = {
            "balance": 50000000,
            "transactions": 100,
        }
        result = tron_client.get_account_status("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertTrue(result["is_activated"])
        self.assertTrue(result["has_trx"])
        self.assertEqual(result["trx_balance"], 50.0)

    @patch('tron_mcp_server.tron_client._get')
    def test_unactivated_account(self, mock_get):
        """未激活账户应返回 is_activated=False"""
        mock_get.return_value = {
            "balance": 0,
            "transactions": 0,
        }
        result = tron_client.get_account_status("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertFalse(result["is_activated"])
        self.assertFalse(result["has_trx"])

    @patch('tron_mcp_server.tron_client._get')
    def test_account_with_balance_no_transactions(self, mock_get):
        """有余额但无交易记录的账户也算激活"""
        mock_get.return_value = {
            "balance": 1000000,
            "transactions": 0,
        }
        result = tron_client.get_account_status("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertTrue(result["is_activated"])


class TestGetTransferHistory(unittest.TestCase):
    """测试 get_transfer_history"""

    @patch('tron_mcp_server.tron_client._get')
    def test_basic_query(self, mock_get):
        """基本查询应正确传递参数"""
        mock_get.return_value = {"data": [], "total": 0}
        tron_client.get_transfer_history("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        self.assertEqual(call_args[0][0], "transfer")

    @patch('tron_mcp_server.tron_client._get')
    def test_with_token_filter(self, mock_get):
        """带 token 筛选的查询"""
        mock_get.return_value = {"data": [], "total": 0}
        tron_client.get_transfer_history("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7", token="_")
        call_args = mock_get.call_args
        # _get 使用位置参数: _get(path, params)
        params = call_args[0][1]
        self.assertEqual(params["token"], "_")

    @patch('tron_mcp_server.tron_client._get')
    def test_custom_limit_and_start(self, mock_get):
        """自定义 limit 和 start"""
        mock_get.return_value = {"data": [], "total": 0}
        tron_client.get_transfer_history("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7", limit=20, start=5)
        call_args = mock_get.call_args
        params = call_args[0][1]
        self.assertEqual(params["limit"], 20)
        self.assertEqual(params["start"], 5)


class TestGetTrc20TransferHistory(unittest.TestCase):
    """测试 get_trc20_transfer_history"""

    @patch('tron_mcp_server.tron_client._get')
    def test_basic_query(self, mock_get):
        """基本查询"""
        mock_get.return_value = {"token_transfers": [], "total": 0}
        tron_client.get_trc20_transfer_history("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        call_args = mock_get.call_args
        self.assertEqual(call_args[0][0], "token_trc20/transfers")

    @patch('tron_mcp_server.tron_client._get')
    def test_with_contract_address(self, mock_get):
        """带合约地址筛选"""
        mock_get.return_value = {"token_transfers": [], "total": 0}
        tron_client.get_trc20_transfer_history(
            "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            contract_address="TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
        )
        call_args = mock_get.call_args
        params = call_args[0][1]
        self.assertEqual(
            params["contract_address"],
            "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
        )


class TestGetInternalTransactions(unittest.TestCase):
    """测试 get_internal_transactions"""

    @patch('tron_mcp_server.tron_client._get')
    def test_basic_query(self, mock_get):
        """基本查询"""
        mock_get.return_value = {"data": [], "total": 0}
        tron_client.get_internal_transactions("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        call_args = mock_get.call_args
        self.assertEqual(call_args[0][0], "internal-transaction")

    @patch('tron_mcp_server.tron_client._get')
    def test_custom_pagination(self, mock_get):
        """自定义分页参数"""
        mock_get.return_value = {"data": [], "total": 0}
        tron_client.get_internal_transactions("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7", limit=5, start=10)
        call_args = mock_get.call_args
        params = call_args[0][1]
        self.assertEqual(params["limit"], 5)
        self.assertEqual(params["start"], 10)


class TestGetAccountTokens(unittest.TestCase):
    """测试 get_account_tokens"""

    @patch('tron_mcp_server.tron_client._get')
    def test_account_with_multiple_tokens(self, mock_get):
        """持有多种代币的账户"""
        mock_get.return_value = {
            "balance": 50000000,
            "trc20token_balances": [
                {
                    "tokenId": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
                    "tokenName": "Tether USD",
                    "tokenAbbr": "USDT",
                    "balance": "100000000",
                    "tokenDecimal": "6",
                }
            ],
            "tokenBalances": [
                {"tokenName": "BitTorrent", "tokenAbbr": "BTT", "balance": 1000, "tokenDecimal": 0}
            ],
        }
        result = tron_client.get_account_tokens("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertGreater(result["token_count"], 1)
        # TRX should always be first
        self.assertEqual(result["tokens"][0]["token_name"], "TRX")
        self.assertEqual(result["tokens"][0]["balance"], 50.0)

    @patch('tron_mcp_server.tron_client._get')
    def test_account_with_only_trx(self, mock_get):
        """只有 TRX 的账户"""
        mock_get.return_value = {
            "balance": 1000000,
        }
        result = tron_client.get_account_tokens("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertEqual(result["token_count"], 1)
        self.assertEqual(result["tokens"][0]["token_name"], "TRX")

    @patch('tron_mcp_server.tron_client._get')
    def test_trx_entry_skipped_in_token_balances(self, mock_get):
        """tokenBalances 中的 TRX/_ 条目应被跳过"""
        mock_get.return_value = {
            "balance": 1000000,
            "tokenBalances": [
                {"tokenName": "_", "balance": 1000000},
                {"tokenName": "TRX", "balance": 1000000},
                {"tokenName": "", "balance": 0},
                {"tokenName": "SomeToken", "tokenAbbr": "ST", "balance": 500, "tokenDecimal": 2}
            ],
        }
        result = tron_client.get_account_tokens("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        token_names = [t["token_name"] for t in result["tokens"]]
        # Should have TRX (from balance) + SomeToken (from tokenBalances)
        self.assertIn("TRX", token_names)
        self.assertIn("SomeToken", token_names)
        # _ and empty should be skipped
        self.assertNotIn("_", token_names)


if __name__ == "__main__":
    unittest.main()
