"""
测试 trongrid_client.py - TronGrid API 交易构建与广播
=====================================================

覆盖以下功能的集成测试（使用 mock HTTP 响应）：
- _base58_to_hex: 地址格式转换
- build_trx_transfer: 构建 TRX 原生转账
- build_trc20_transfer: 构建 TRC20 代币转账
- broadcast_transaction: 广播已签名交易
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

from tron_mcp_server import trongrid_client


class TestBase58ToHex(unittest.TestCase):
    """测试 _base58_to_hex 地址格式转换"""

    def test_already_hex_with_0x_prefix(self):
        """0x41... 格式应去掉 0x 前缀"""
        addr = "0x41" + "a" * 40
        result = trongrid_client._base58_to_hex(addr)
        self.assertEqual(result, "41" + "a" * 40)

    def test_already_hex_without_prefix(self):
        """41... 格式应原样返回"""
        addr = "41" + "b" * 40
        result = trongrid_client._base58_to_hex(addr)
        self.assertEqual(result, addr)

    def test_valid_base58_address(self):
        """有效 Base58 地址应转换为 Hex"""
        addr = "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"
        result = trongrid_client._base58_to_hex(addr)
        self.assertTrue(result.startswith("41"))
        self.assertEqual(len(result), 42)

    def test_invalid_address_raises(self):
        """无效地址应抛出 ValueError"""
        with self.assertRaises(ValueError):
            trongrid_client._base58_to_hex("invalid_address")


class TestBuildTrxTransfer(unittest.TestCase):
    """测试 build_trx_transfer"""

    @patch('tron_mcp_server.trongrid_client._post')
    def test_successful_build(self, mock_post):
        """正常构建 TRX 转账交易"""
        mock_post.return_value = {
            "txID": "a" * 64,
            "raw_data": {"contract": []},
            "raw_data_hex": "0000",
        }
        result = trongrid_client.build_trx_transfer(
            "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            10.0,
        )
        self.assertIn("txID", result)
        self.assertEqual(result["txID"], "a" * 64)

    @patch('tron_mcp_server.trongrid_client._post')
    def test_amount_conversion_to_sun(self, mock_post):
        """金额应正确转换为 SUN"""
        mock_post.return_value = {"txID": "a" * 64, "raw_data": {}}
        trongrid_client.build_trx_transfer(
            "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            1.5,
        )
        call_data = mock_post.call_args[0][1]
        self.assertEqual(call_data["amount"], 1500000)

    @patch('tron_mcp_server.trongrid_client._post')
    def test_error_response_raises(self, mock_post):
        """TronGrid 返回 Error 应抛出 ValueError"""
        mock_post.return_value = {"Error": "Invalid address"}
        with self.assertRaises(ValueError):
            trongrid_client.build_trx_transfer(
                "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
                "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
                10.0,
            )

    @patch('tron_mcp_server.trongrid_client._post')
    def test_missing_txid_raises(self, mock_post):
        """缺少 txID 应抛出 ValueError"""
        mock_post.return_value = {"raw_data": {}}
        with self.assertRaises(ValueError):
            trongrid_client.build_trx_transfer(
                "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
                "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
                10.0,
            )


class TestBuildTrc20Transfer(unittest.TestCase):
    """测试 build_trc20_transfer"""

    @patch('tron_mcp_server.trongrid_client._post')
    def test_successful_build(self, mock_post):
        """正常构建 TRC20 转账交易"""
        mock_post.return_value = {
            "result": {"result": True},
            "transaction": {
                "txID": "b" * 64,
                "raw_data": {"contract": []},
            },
        }
        result = trongrid_client.build_trc20_transfer(
            "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            100.0,
        )
        self.assertIn("txID", result)

    @patch('tron_mcp_server.trongrid_client._post')
    def test_uses_default_usdt_contract(self, mock_post):
        """默认使用 USDT 合约地址"""
        mock_post.return_value = {
            "result": {"result": True},
            "transaction": {"txID": "c" * 64, "raw_data": {}},
        }
        trongrid_client.build_trc20_transfer(
            "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            50.0,
        )
        call_data = mock_post.call_args[0][1]
        self.assertEqual(call_data["function_selector"], "transfer(address,uint256)")

    @patch('tron_mcp_server.trongrid_client._post')
    def test_custom_contract_address(self, mock_post):
        """使用自定义合约地址"""
        mock_post.return_value = {
            "result": {"result": True},
            "transaction": {"txID": "d" * 64, "raw_data": {}},
        }
        trongrid_client.build_trc20_transfer(
            "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            50.0,
            contract_address="TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
        )
        mock_post.assert_called_once()

    @patch('tron_mcp_server.trongrid_client._post')
    def test_failed_result_raises(self, mock_post):
        """result.result=False 应抛出 ValueError"""
        mock_post.return_value = {
            "result": {"result": False, "message": "REVERT"},
        }
        with self.assertRaises(ValueError):
            trongrid_client.build_trc20_transfer(
                "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
                "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
                50.0,
            )

    @patch('tron_mcp_server.trongrid_client._post')
    def test_missing_transaction_raises(self, mock_post):
        """缺少 transaction 字段应抛出 ValueError"""
        mock_post.return_value = {
            "result": {"result": True},
        }
        with self.assertRaises(ValueError):
            trongrid_client.build_trc20_transfer(
                "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
                "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
                50.0,
            )

    @patch('tron_mcp_server.trongrid_client._post')
    def test_custom_fee_limit(self, mock_post):
        """自定义 fee_limit"""
        mock_post.return_value = {
            "result": {"result": True},
            "transaction": {"txID": "e" * 64, "raw_data": {}},
        }
        trongrid_client.build_trc20_transfer(
            "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            50.0,
            fee_limit=200000000,
        )
        call_data = mock_post.call_args[0][1]
        self.assertEqual(call_data["fee_limit"], 200000000)

    @patch('tron_mcp_server.trongrid_client._post')
    def test_custom_decimals(self, mock_post):
        """自定义代币精度"""
        mock_post.return_value = {
            "result": {"result": True},
            "transaction": {"txID": "f" * 64, "raw_data": {}},
        }
        trongrid_client.build_trc20_transfer(
            "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            1.0,
            decimals=18,
        )
        mock_post.assert_called_once()


class TestBroadcastTransaction(unittest.TestCase):
    """测试 broadcast_transaction"""

    @patch('tron_mcp_server.trongrid_client._post')
    def test_successful_broadcast(self, mock_post):
        """成功广播应返回 result=True"""
        mock_post.return_value = {"result": True}
        
        signed_tx = {
            "txID": "a" * 64,
            "raw_data": {"contract": []},
            "signature": ["sig123"],
        }
        result = trongrid_client.broadcast_transaction(signed_tx)
        self.assertTrue(result["result"])
        self.assertEqual(result["txid"], "a" * 64)

    @patch('tron_mcp_server.trongrid_client._post')
    def test_missing_txid_raises(self, mock_post):
        """缺少 txID 应抛出 ValueError"""
        with self.assertRaises(ValueError):
            trongrid_client.broadcast_transaction({
                "raw_data": {}, "signature": ["sig"]
            })

    @patch('tron_mcp_server.trongrid_client._post')
    def test_missing_signature_raises(self, mock_post):
        """缺少 signature 应抛出 ValueError"""
        with self.assertRaises(ValueError):
            trongrid_client.broadcast_transaction({
                "txID": "a" * 64, "raw_data": {},
            })

    @patch('tron_mcp_server.trongrid_client._post')
    def test_empty_signature_raises(self, mock_post):
        """空 signature 列表应抛出 ValueError"""
        with self.assertRaises(ValueError):
            trongrid_client.broadcast_transaction({
                "txID": "a" * 64, "raw_data": {}, "signature": [],
            })

    @patch('tron_mcp_server.trongrid_client._post')
    def test_missing_raw_data_raises(self, mock_post):
        """缺少 raw_data 和 raw_data_hex 应抛出 ValueError"""
        with self.assertRaises(ValueError):
            trongrid_client.broadcast_transaction({
                "txID": "a" * 64, "signature": ["sig"],
            })

    @patch('tron_mcp_server.trongrid_client._post')
    def test_raw_data_hex_accepted(self, mock_post):
        """raw_data_hex 也应被接受"""
        mock_post.return_value = {"result": True}
        signed_tx = {
            "txID": "a" * 64,
            "raw_data_hex": "0000",
            "signature": ["sig123"],
        }
        result = trongrid_client.broadcast_transaction(signed_tx)
        self.assertTrue(result["result"])

    @patch('tron_mcp_server.trongrid_client._post')
    def test_failed_broadcast_raises(self, mock_post):
        """广播失败应抛出 ValueError"""
        mock_post.return_value = {"result": False, "code": "SIGERROR", "message": ""}
        signed_tx = {
            "txID": "a" * 64,
            "raw_data": {},
            "signature": ["sig123"],
        }
        with self.assertRaises(ValueError):
            trongrid_client.broadcast_transaction(signed_tx)

    @patch('tron_mcp_server.trongrid_client._post')
    def test_hex_encoded_error_message(self, mock_post):
        """Hex 编码的错误消息应被解码"""
        hex_msg = "7472616e73616374696f6e2065787069726564"  # "transaction expired"
        mock_post.return_value = {"result": False, "code": "TRANSACTION_EXPIRATION_ERROR", "message": hex_msg}
        signed_tx = {
            "txID": "a" * 64,
            "raw_data": {},
            "signature": ["sig123"],
        }
        with self.assertRaises(ValueError) as ctx:
            trongrid_client.broadcast_transaction(signed_tx)
        self.assertIn("transaction expired", str(ctx.exception))


class TestGetTrongridUrl(unittest.TestCase):
    """测试 _get_trongrid_url"""

    def test_default_url(self):
        """默认 URL"""
        with patch.dict(os.environ, {}, clear=False):
            # Remove any existing env var
            os.environ.pop("TRONGRID_API_URL", None)
            os.environ.pop("TRON_NETWORK", None)
            result = trongrid_client._get_trongrid_url()
            self.assertEqual(result, "https://api.trongrid.io")

    def test_custom_url(self):
        """自定义 URL"""
        with patch.dict(os.environ, {"TRONGRID_API_URL": "https://custom.trongrid.io/"}):
            result = trongrid_client._get_trongrid_url()
            self.assertEqual(result, "https://custom.trongrid.io")

    def test_trailing_slash_removed(self):
        """尾部斜杠应被移除"""
        with patch.dict(os.environ, {"TRONGRID_API_URL": "https://api.test.io///"}):
            result = trongrid_client._get_trongrid_url()
            self.assertFalse(result.endswith("/"))


class TestGetHeaders(unittest.TestCase):
    """测试 _get_headers"""

    def test_default_headers(self):
        """默认 headers"""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TRONGRID_API_KEY", None)
            os.environ.pop("TRONSCAN_API_KEY", None)
            result = trongrid_client._get_headers()
            self.assertIn("Accept", result)
            self.assertIn("Content-Type", result)

    def test_with_trongrid_api_key(self):
        """TRONGRID_API_KEY 应添加到 headers"""
        with patch.dict(os.environ, {"TRONGRID_API_KEY": "test-key-123"}):
            result = trongrid_client._get_headers()
            self.assertEqual(result["TRON-PRO-API-KEY"], "test-key-123")


if __name__ == "__main__":
    unittest.main()
